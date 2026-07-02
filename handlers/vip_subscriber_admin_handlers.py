"""
Handlers admin — lista paginada de suscriptores VIP + perfiles y acciones.

Phase 36: reemplaza list_subscribers plano en vip_handlers.py.
"""

import logging
import math
from datetime import UTC, datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from handlers.vip_handlers import (
    notify_forward_besitos_result,
    parse_positive_besito_amount,
)
from keyboards.callback_data import (
    ChannelDetailCallback,
    SubscriberActionCallback,
    SubscriberConfirmCallback,
    SubscriberExtendTariffCallback,
    SubscriberListCallback,
    SubscriberProfileCallback,
)
from keyboards.inline_keyboards import (
    cancel_keyboard,
    subscriber_confirm_keyboard,
    subscriber_extend_tariffs_keyboard,
    subscriber_list_keyboard,
    subscriber_profile_keyboard,
    vip_management_keyboard,
)
from services import BesitoService, VIPService, get_service
from services.besito_service import MAX_ADMIN_BESITO_GRANT
from utils.admin import is_admin
from utils.lucien_voice import LucienVoice

logger = logging.getLogger(__name__)
router = Router()

SUBSCRIBER_PAGE_SIZE = 8


class SubscriberAdminStates(StatesGroup):
    extend_confirming = State()
    besitos_grant_waiting_amount = State()
    besitos_grant_confirming = State()
    besitos_debit_waiting_amount = State()
    besitos_debit_confirming = State()
    kick_confirming = State()


def clamp_subscriber_page(page: int, total_count: int) -> int:
    """Función pura (sin estado ni side-effects)."""
    total_pages = max(1, math.ceil(total_count / SUBSCRIBER_PAGE_SIZE))
    return max(0, min(page, total_pages - 1))


def format_subscriber_display_name(sub) -> str:
    """Función pura (sin estado ni side-effects). Escape delegado a LucienVoice."""
    user = getattr(sub, "user", None)
    if user and user.username:
        return f"@{user.username}"
    if user and user.first_name:
        return user.first_name
    return f"ID:{sub.user_id}"


def compute_days_remaining(end_date) -> int:
    """Función pura (sin estado ni side-effects)."""
    if end_date is None:
        return 0
    now = datetime.now(UTC)
    if end_date.tzinfo is None:
        end_date = end_date.replace(tzinfo=UTC)
    return max(0, (end_date - now).days)


def build_subscriber_list_text(subs: list, page: int, total_count: int) -> str:
    """Función pura (sin estado ni side-effects)."""
    if total_count == 0:
        return LucienVoice.admin_subscriber_list_empty()
    total_pages = max(1, math.ceil(total_count / SUBSCRIBER_PAGE_SIZE))
    text = LucienVoice.admin_subscriber_list_header(total_count, page, total_pages)
    for i, sub in enumerate(subs, start=page * SUBSCRIBER_PAGE_SIZE + 1):
        display = format_subscriber_display_name(sub)
        expiry = sub.end_date.strftime("%d/%m/%Y") if sub.end_date else "—"
        text += LucienVoice.admin_subscriber_list_line(i, display, expiry)
    return text


def build_subscriber_profile_text(snapshot: dict) -> str:
    """Función pura (sin estado ni side-effects)."""
    return LucienVoice.admin_subscriber_profile(snapshot)


def build_tariff_map(tariffs: list) -> dict:
    """Función pura (sin estado ni side-effects)."""
    return {t.id: {"name": t.name, "days": t.duration_days} for t in tariffs}


def validate_fsm_subscription_id(fsm_data: dict, subscription_id: int) -> bool:
    """Función pura (sin estado ni side-effects)."""
    return fsm_data.get("target_subscription_id") == subscription_id


def resolve_list_back_callback(channel_id: int) -> str:
    """Función pura (sin estado ni side-effects)."""
    if channel_id:
        return ChannelDetailCallback(channel_id=channel_id).pack()
    return "admin_vip"


def _channel_filter(channel_id: int) -> int | None:
    """Función pura (sin estado ni side-effects)."""
    return channel_id if channel_id else None


async def _deny_non_admin_callback(callback: CallbackQuery) -> bool:
    """Retorna True si el custodio fue denegado."""
    if not is_admin(callback.from_user.id):
        await callback.answer("Acceso denegado", show_alert=True)
        return True
    return False


async def _deny_non_admin_message(message: Message, state: FSMContext) -> bool:
    """Retorna True si el usuario fue denegado."""
    if not is_admin(message.from_user.id):
        await message.answer("Acceso denegado", parse_mode="HTML")
        await state.clear()
        return True
    return False


async def _reject_fsm_mismatch(callback: CallbackQuery, state: FSMContext) -> None:
    """Limpia FSM y avisa si callback subscription_id no coincide con contexto."""
    await state.clear()
    await callback.answer("Contexto expirado. Vuelva al perfil.", show_alert=True)


async def _render_subscriber_list(
    callback: CallbackQuery, channel_id: int, page: int
) -> None:
    """Renderiza lista paginada de suscriptores activos."""
    channel_filter = _channel_filter(channel_id)
    with get_service(VIPService) as svc:
        subs, total = svc.get_subscriber_list_page(
            channel_filter, page, SUBSCRIBER_PAGE_SIZE
        )
    display_page = clamp_subscriber_page(page, total)
    text = build_subscriber_list_text(subs, display_page, total)
    keyboard = subscriber_list_keyboard(
        subs, channel_id, display_page, total, SUBSCRIBER_PAGE_SIZE
    )
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


async def _render_subscriber_profile(
    callback: CallbackQuery, subscription_id: int, channel_id: int, page: int
) -> None:
    """Renderiza perfil admin de un suscriptor."""
    with get_service(VIPService) as svc:
        snapshot = svc.get_subscriber_admin_snapshot(subscription_id)
    if not snapshot:
        await callback.answer("Suscriptor no encontrado", show_alert=True)
        return
    text = build_subscriber_profile_text(snapshot)
    keyboard = subscriber_profile_keyboard(subscription_id, channel_id, page)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


async def _save_profile_context(
    state: FSMContext,
    subscription_id: int,
    channel_id: int,
    page: int,
    snapshot: dict,
) -> None:
    """Guarda contexto FSM común para acciones sobre suscriptor."""
    await state.update_data(
        target_subscription_id=subscription_id,
        target_user_id=snapshot["user_id"],
        target_display=snapshot["display_name"],
        list_channel_id=channel_id,
        list_page=page,
    )


@router.callback_query(
    SubscriberListCallback.filter(),
    lambda cb: is_admin(cb.from_user.id),
)
async def open_subscriber_list(
    callback: CallbackQuery, callback_data: SubscriberListCallback
):
    """Abre lista paginada de suscriptores activos."""
    if await _deny_non_admin_callback(callback):
        return
    admin_id = callback.from_user.id
    logger.info(
        f"vip_subscriber_admin_handlers | abrir_lista | user_id={admin_id} | "
        f"channel_id={callback_data.channel_id} | page={callback_data.page}"
    )
    await _render_subscriber_list(
        callback, callback_data.channel_id, callback_data.page
    )


@router.callback_query(
    SubscriberProfileCallback.filter(),
    lambda cb: is_admin(cb.from_user.id),
)
async def open_subscriber_profile(
    callback: CallbackQuery,
    state: FSMContext,
    callback_data: SubscriberProfileCallback,
):
    """Abre perfil admin de un suscriptor (limpia FSM previo)."""
    if await _deny_non_admin_callback(callback):
        return
    await state.clear()
    admin_id = callback.from_user.id
    logger.info(
        f"vip_subscriber_admin_handlers | abrir_perfil | user_id={admin_id} | "
        f"subscription_id={callback_data.subscription_id}"
    )
    await _render_subscriber_profile(
        callback,
        callback_data.subscription_id,
        callback_data.channel_id,
        callback_data.page,
    )


@router.callback_query(
    SubscriberActionCallback.filter(F.action == "extend"),
    lambda cb: is_admin(cb.from_user.id),
)
async def start_subscriber_extend(
    callback: CallbackQuery, state: FSMContext, callback_data: SubscriberActionCallback
):
    """Inicia flujo extender VIP: muestra tarifas activas."""
    if await _deny_non_admin_callback(callback):
        return
    await state.clear()
    admin_id = callback.from_user.id
    sub_id = callback_data.subscription_id
    channel_id = callback_data.channel_id
    page = callback_data.page
    with get_service(VIPService) as svc:
        snapshot, tariffs = svc.get_subscriber_extend_context(sub_id)
    if not snapshot:
        await callback.answer("Suscriptor no encontrado", show_alert=True)
        return
    profile_kb = subscriber_profile_keyboard(sub_id, channel_id, page)
    if not tariffs:
        await callback.message.edit_text(
            LucienVoice.admin_subscriber_action_failed("No hay tarifas activas"),
            reply_markup=profile_kb,
            parse_mode="HTML",
        )
        await callback.answer()
        return
    await _save_profile_context(state, sub_id, channel_id, page, snapshot)
    await state.update_data(tariff_map=build_tariff_map(tariffs))
    logger.info(
        f"vip_subscriber_admin_handlers | iniciar_extend | user_id={admin_id} | "
        f"subscription_id={sub_id}"
    )
    await callback.message.edit_text(
        LucienVoice.admin_subscriber_extend_tariff_prompt(
            snapshot["display_name"], snapshot["user_id"]
        ),
        reply_markup=subscriber_extend_tariffs_keyboard(tariffs, sub_id, channel_id, page),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(
    SubscriberExtendTariffCallback.filter(),
    lambda cb: is_admin(cb.from_user.id),
)
async def select_extend_tariff(
    callback: CallbackQuery,
    state: FSMContext,
    callback_data: SubscriberExtendTariffCallback,
):
    """Selecciona tarifa para extender (0 svc — guarda en FSM)."""
    if await _deny_non_admin_callback(callback):
        return
    data = await state.get_data()
    if not validate_fsm_subscription_id(data, callback_data.subscription_id):
        await _reject_fsm_mismatch(callback, state)
        return
    tariff_map = data.get("tariff_map", {})
    if callback_data.tariff_id not in tariff_map:
        await callback.answer("Tarifa inválida", show_alert=True)
        return
    tariff_info = tariff_map[callback_data.tariff_id]
    display = data.get("target_display", "visitante")
    await state.update_data(
        selected_tariff_id=callback_data.tariff_id,
        selected_tariff_name=tariff_info["name"],
        selected_tariff_days=tariff_info["days"],
    )
    await callback.message.edit_text(
        LucienVoice.admin_subscriber_extend_confirm(
            display, tariff_info["name"], tariff_info["days"]
        ),
        reply_markup=subscriber_confirm_keyboard(
            "extend",
            callback_data.subscription_id,
            callback_data.channel_id,
            callback_data.page,
        ),
        parse_mode="HTML",
    )
    await state.set_state(SubscriberAdminStates.extend_confirming)
    await callback.answer()


@router.callback_query(
    SubscriberAdminStates.extend_confirming,
    SubscriberConfirmCallback.filter(F.action == "extend"),
    lambda cb: is_admin(cb.from_user.id),
)
async def confirm_subscriber_extend(
    callback: CallbackQuery, state: FSMContext, callback_data: SubscriberConfirmCallback
):
    """Confirma extensión VIP vía grant_internal_vip_access_for_subscription (1 svc)."""
    if await _deny_non_admin_callback(callback):
        return
    data = await state.get_data()
    if not validate_fsm_subscription_id(data, callback_data.subscription_id):
        await _reject_fsm_mismatch(callback, state)
        return
    tariff_id = data.get("selected_tariff_id")
    display = data.get("target_display", "visitante")
    tariff_name = data.get("selected_tariff_name", "tarifa")
    tariff_days = data.get("selected_tariff_days", 0)
    admin_id = callback.from_user.id
    if not tariff_id:
        await callback.answer("Datos incompletos", show_alert=True)
        await state.clear()
        return
    ok = False
    with get_service(VIPService) as svc:
        ok, _, _ = await svc.grant_internal_vip_access_for_subscription(
            callback_data.subscription_id, tariff_id
        )
    logger.info(
        f"vip_subscriber_admin_handlers | confirmar_extend | user_id={admin_id} | "
        f"subscription_id={callback_data.subscription_id} | tariff_id={tariff_id} | "
        f"resultado={'ok' if ok else 'fail'}"
    )
    profile_kb = subscriber_profile_keyboard(
        callback_data.subscription_id,
        callback_data.channel_id,
        callback_data.page,
    )
    await state.clear()
    if ok:
        await callback.message.edit_text(
            LucienVoice.admin_subscriber_extend_success(display, tariff_name, tariff_days),
            reply_markup=profile_kb,
            parse_mode="HTML",
        )
    else:
        await callback.message.edit_text(
            LucienVoice.admin_subscriber_action_failed("No se pudo extender VIP"),
            reply_markup=profile_kb,
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(
    SubscriberActionCallback.filter(F.action == "grant_besitos"),
    lambda cb: is_admin(cb.from_user.id),
)
async def start_subscriber_grant_besitos(
    callback: CallbackQuery, state: FSMContext, callback_data: SubscriberActionCallback
):
    """Inicia flujo otorgar besitos (0 svc)."""
    if await _deny_non_admin_callback(callback):
        return
    await state.clear()
    with get_service(VIPService) as svc:
        snapshot = svc.get_subscriber_admin_snapshot(callback_data.subscription_id)
    if not snapshot:
        await callback.answer("Suscriptor no encontrado", show_alert=True)
        return
    await _save_profile_context(
        state,
        callback_data.subscription_id,
        callback_data.channel_id,
        callback_data.page,
        snapshot,
    )
    display = snapshot["display_name"]
    cancel_cb = SubscriberProfileCallback(
        subscription_id=callback_data.subscription_id,
        channel_id=callback_data.channel_id,
        page=callback_data.page,
    ).pack()
    await callback.message.edit_text(
        LucienVoice.admin_subscriber_besitos_amount_prompt(display, "grant"),
        reply_markup=cancel_keyboard(cancel_cb),
        parse_mode="HTML",
    )
    await state.set_state(SubscriberAdminStates.besitos_grant_waiting_amount)
    await callback.answer()


@router.message(
    SubscriberAdminStates.besitos_grant_waiting_amount,
    lambda m: is_admin(m.from_user.id),
)
async def process_grant_besitos_amount(message: Message, state: FSMContext):
    """Recibe cantidad para otorgar besitos (0 svc — parse)."""
    if await _deny_non_admin_message(message, state):
        return
    amount = parse_positive_besito_amount(message.text)
    if amount is None:
        await message.answer(
            f"🎩 <b>Lucien:</b>\n\n"
            f"<i>Cantidad inválida. Indique un entero entre 1 y {MAX_ADMIN_BESITO_GRANT}.</i>",
            parse_mode="HTML",
        )
        return
    data = await state.get_data()
    display = data.get("target_display", "visitante")
    sub_id = data.get("target_subscription_id")
    channel_id = data.get("list_channel_id", 0)
    page = data.get("list_page", 0)
    await message.answer(
        LucienVoice.admin_subscriber_besitos_confirm(display, amount, "grant"),
        reply_markup=subscriber_confirm_keyboard("grant_besitos", sub_id, channel_id, page),
        parse_mode="HTML",
    )
    await state.update_data(besito_amount=amount)
    await state.set_state(SubscriberAdminStates.besitos_grant_confirming)


@router.callback_query(
    SubscriberAdminStates.besitos_grant_confirming,
    SubscriberConfirmCallback.filter(F.action == "grant_besitos"),
    lambda cb: is_admin(cb.from_user.id),
)
async def confirm_subscriber_grant_besitos(
    callback: CallbackQuery, state: FSMContext, callback_data: SubscriberConfirmCallback
):
    """Confirma otorgar besitos (1 svc) + notify best-effort."""
    if await _deny_non_admin_callback(callback):
        return
    data = await state.get_data()
    if not validate_fsm_subscription_id(data, callback_data.subscription_id):
        await _reject_fsm_mismatch(callback, state)
        return
    target_user_id = data.get("target_user_id")
    amount = data.get("besito_amount")
    admin_id = callback.from_user.id
    if not target_user_id or not amount:
        await callback.answer("Datos incompletos", show_alert=True)
        await state.clear()
        return
    ok, balance = False, 0
    with get_service(BesitoService) as svc:
        ok, balance = svc.grant_manual_admin_besitos(target_user_id, amount, admin_id)
    logger.info(
        f"vip_subscriber_admin_handlers | confirmar_grant_besitos | user_id={admin_id} | "
        f"target={target_user_id} | amount={amount} | resultado={'ok' if ok else 'fail'}"
    )
    back_kb = subscriber_profile_keyboard(
        callback_data.subscription_id,
        callback_data.channel_id,
        callback_data.page,
    )
    await notify_forward_besitos_result(
        callback.bot,
        callback.message,
        target_user_id,
        ok,
        amount,
        balance,
        admin_id,
        success_keyboard=back_kb,
    )
    await state.clear()
    await callback.answer()


@router.callback_query(
    SubscriberActionCallback.filter(F.action == "debit_besitos"),
    lambda cb: is_admin(cb.from_user.id),
)
async def start_subscriber_debit_besitos(
    callback: CallbackQuery, state: FSMContext, callback_data: SubscriberActionCallback
):
    """Inicia flujo debitar besitos (0 svc)."""
    if await _deny_non_admin_callback(callback):
        return
    await state.clear()
    with get_service(VIPService) as svc:
        snapshot = svc.get_subscriber_admin_snapshot(callback_data.subscription_id)
    if not snapshot:
        await callback.answer("Suscriptor no encontrado", show_alert=True)
        return
    await _save_profile_context(
        state,
        callback_data.subscription_id,
        callback_data.channel_id,
        callback_data.page,
        snapshot,
    )
    display = snapshot["display_name"]
    cancel_cb = SubscriberProfileCallback(
        subscription_id=callback_data.subscription_id,
        channel_id=callback_data.channel_id,
        page=callback_data.page,
    ).pack()
    await callback.message.edit_text(
        LucienVoice.admin_subscriber_besitos_amount_prompt(display, "debit"),
        reply_markup=cancel_keyboard(cancel_cb),
        parse_mode="HTML",
    )
    await state.set_state(SubscriberAdminStates.besitos_debit_waiting_amount)
    await callback.answer()


@router.message(
    SubscriberAdminStates.besitos_debit_waiting_amount,
    lambda m: is_admin(m.from_user.id),
)
async def process_debit_besitos_amount(message: Message, state: FSMContext):
    """Recibe cantidad para debitar besitos (0 svc — parse)."""
    if await _deny_non_admin_message(message, state):
        return
    amount = parse_positive_besito_amount(message.text)
    if amount is None:
        await message.answer(
            f"🎩 <b>Lucien:</b>\n\n"
            f"<i>Cantidad inválida. Indique un entero entre 1 y {MAX_ADMIN_BESITO_GRANT}.</i>",
            parse_mode="HTML",
        )
        return
    data = await state.get_data()
    display = data.get("target_display", "visitante")
    sub_id = data.get("target_subscription_id")
    channel_id = data.get("list_channel_id", 0)
    page = data.get("list_page", 0)
    await message.answer(
        LucienVoice.admin_subscriber_besitos_confirm(display, amount, "debit"),
        reply_markup=subscriber_confirm_keyboard("debit_besitos", sub_id, channel_id, page),
        parse_mode="HTML",
    )
    await state.update_data(besito_amount=amount)
    await state.set_state(SubscriberAdminStates.besitos_debit_confirming)


@router.callback_query(
    SubscriberAdminStates.besitos_debit_confirming,
    SubscriberConfirmCallback.filter(F.action == "debit_besitos"),
    lambda cb: is_admin(cb.from_user.id),
)
async def confirm_subscriber_debit_besitos(
    callback: CallbackQuery, state: FSMContext, callback_data: SubscriberConfirmCallback
):
    """Confirma debitar besitos (1 svc)."""
    if await _deny_non_admin_callback(callback):
        return
    data = await state.get_data()
    if not validate_fsm_subscription_id(data, callback_data.subscription_id):
        await _reject_fsm_mismatch(callback, state)
        return
    target_user_id = data.get("target_user_id")
    amount = data.get("besito_amount")
    display = data.get("target_display", "visitante")
    admin_id = callback.from_user.id
    if not target_user_id or not amount:
        await callback.answer("Datos incompletos", show_alert=True)
        await state.clear()
        return
    ok, balance = False, 0
    with get_service(BesitoService) as svc:
        ok, balance = svc.debit_manual_admin_besitos(target_user_id, amount, admin_id)
    logger.info(
        f"vip_subscriber_admin_handlers | confirmar_debit_besitos | user_id={admin_id} | "
        f"target={target_user_id} | amount={amount} | resultado={'ok' if ok else 'fail'}"
    )
    await state.clear()
    profile_kb = subscriber_profile_keyboard(
        callback_data.subscription_id,
        callback_data.channel_id,
        callback_data.page,
    )
    if ok:
        await callback.message.edit_text(
            LucienVoice.admin_subscriber_debit_success(display, amount, balance),
            reply_markup=profile_kb,
            parse_mode="HTML",
        )
    else:
        await callback.message.edit_text(
            LucienVoice.admin_subscriber_action_failed(
                "Saldo insuficiente o cantidad inválida"
            ),
            reply_markup=profile_kb,
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(
    SubscriberActionCallback.filter(F.action == "kick"),
    lambda cb: is_admin(cb.from_user.id),
)
async def start_subscriber_kick(
    callback: CallbackQuery, state: FSMContext, callback_data: SubscriberActionCallback
):
    """Inicia confirmación de expulsión (0 svc)."""
    if await _deny_non_admin_callback(callback):
        return
    await state.clear()
    with get_service(VIPService) as svc:
        snapshot = svc.get_subscriber_admin_snapshot(callback_data.subscription_id)
    if not snapshot:
        await callback.answer("Suscriptor no encontrado", show_alert=True)
        return
    await _save_profile_context(
        state,
        callback_data.subscription_id,
        callback_data.channel_id,
        callback_data.page,
        snapshot,
    )
    display = snapshot["display_name"]
    user_id = snapshot["user_id"]
    await callback.message.edit_text(
        LucienVoice.admin_subscriber_kick_confirm(display, user_id),
        reply_markup=subscriber_confirm_keyboard(
            "kick",
            callback_data.subscription_id,
            callback_data.channel_id,
            callback_data.page,
        ),
        parse_mode="HTML",
    )
    await state.set_state(SubscriberAdminStates.kick_confirming)
    await callback.answer()


@router.callback_query(
    SubscriberAdminStates.kick_confirming,
    SubscriberConfirmCallback.filter(F.action == "kick"),
    lambda cb: is_admin(cb.from_user.id),
)
async def confirm_subscriber_kick(
    callback: CallbackQuery, state: FSMContext, callback_data: SubscriberConfirmCallback
):
    """Confirma expulsión vía admin_revoke_subscription (1 svc)."""
    if await _deny_non_admin_callback(callback):
        return
    data = await state.get_data()
    if not validate_fsm_subscription_id(data, callback_data.subscription_id):
        await _reject_fsm_mismatch(callback, state)
        return
    display = data.get("target_display", "visitante")
    admin_id = callback.from_user.id
    ok, result_code, _meta = False, "error", {}
    with get_service(VIPService) as svc:
        ok, result_code, _meta = await svc.admin_revoke_subscription(
            callback.bot, callback_data.subscription_id, admin_id
        )
    logger.info(
        f"vip_subscriber_admin_handlers | confirmar_kick | user_id={admin_id} | "
        f"subscription_id={callback_data.subscription_id} | resultado={result_code}"
    )
    await state.clear()
    list_cb = SubscriberListCallback(
        channel_id=callback_data.channel_id, page=callback_data.page
    ).pack()
    if ok and result_code == "kicked":
        text = LucienVoice.admin_subscriber_kick_success(display)
    elif ok and result_code == "deactivated_only":
        text = LucienVoice.admin_subscriber_kick_deactivated_only(display)
    elif ok and result_code == "channel_inactive":
        text = LucienVoice.admin_subscriber_kick_channel_inactive(display)
    elif ok:
        text = LucienVoice.admin_subscriber_kick_success(display)
    else:
        text = LucienVoice.admin_subscriber_action_failed(result_code)
    if callback_data.channel_id:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Volver a lista", callback_data=list_cb)]
            ]
        )
    else:
        kb = vip_management_keyboard()
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()
