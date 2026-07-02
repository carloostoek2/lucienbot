"""
Handlers VIP - Lucien Bot

Gestión de tarifas, tokens y suscripciones VIP.
"""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from keyboards.callback_data import (
    CopyTokenCallback,
    ForwardActionCallback,
    ForwardCancelCallback,
    ForwardConfirmCallback,
    SelectTariffCallback,
    ToggleGiftCallback,
)
from keyboards.inline_keyboards import (
    back_keyboard,
    forward_action_keyboard,
    forward_cancel_keyboard,
    forward_confirm_keyboard,
    tariffs_keyboard,
    token_actions_keyboard,
    vip_access_keyboard,
    vip_management_keyboard,
)
from services import BesitoService, VIPService, get_service
from services.besito_service import MAX_ADMIN_BESITO_GRANT
from utils.admin import is_admin
from utils.lucien_voice import LucienVoice

logger = logging.getLogger(__name__)
router = Router()


# Estados para FSM
class TariffStates(StatesGroup):
    waiting_name = State()
    waiting_days = State()
    waiting_price = State()
    confirming = State()


class TokenStates(StatesGroup):
    selecting_tariff = State()


class AdminForwardStates(StatesGroup):
    selecting_action = State()
    vip_selecting_tariff = State()
    vip_confirming = State()
    besitos_waiting_amount = State()
    besitos_confirming = State()


def extract_forwarded_candidate(message: Message) -> tuple[int | None, str]:
    """Extrae ID y nombre/display del usuario original reenviado para activación VIP. Función pura (sin estado ni side-effects)."""
    from aiogram.types import MessageOriginUser

    if message.forward_from:
        u = message.forward_from
        display = u.full_name or (f"@{u.username}" if getattr(u, "username", None) else str(u.id))
        return u.id, display
    if message.forward_origin and isinstance(message.forward_origin, MessageOriginUser):
        u = message.forward_origin.sender_user
        display = u.full_name or (f"@{u.username}" if getattr(u, "username", None) else str(u.id))
        return u.id, display
    return None, "desconocido"


def build_forward_manual_delivery_notify(
    invite_link: str, bot_access_link: str | None = None, delivery_code: str | None = None
) -> str:
    """Construye fallback admin cuando VIP ya está activo pero el DM falló. Función pura."""
    reason_map = {
        "permanent:bot_blocked": "el visitante bloqueó al bot",
        "permanent:no_private_chat": "no hay chat privado abierto con el bot",
        "permanent:user_deactivated": "la cuenta del visitante está desactivada",
        "permanent:chat_not_found": "no encontré el chat privado del visitante",
    }
    reason = reason_map.get(delivery_code or "", "no pude enviarle el mensaje directamente")
    bot_line = (
        f"\n\n<i>O bien, pídale que abra:</i>\n<code>{bot_access_link}</code>"
        if bot_access_link
        else ""
    )
    return (
        f"🎩 <b>Lucien:</b>\n\n"
        f"<i>Activación VIP completada, pero {reason}.</i>\n\n"
        f"Entregue este enlace de acceso al canal:\n<code>{invite_link}</code>"
        f"{bot_line}"
    )


def build_forward_blocked_notify(deep_link: str) -> str:
    """Legacy: fallback con deep link de token (evitar si el token ya fue canjeado). Función pura."""
    return f"🎩 <b>Lucien:</b>\n\n<i>Activación completada para el visitante, pero no pude notificarle directamente (posible bloqueo).</i>\n\nProporcione enlace manual: <code>{deep_link}</code>"


def build_forward_success_text() -> str:
    """Construye texto de éxito para admin tras forward grant. Función pura (sin estado ni side-effects)."""
    return "🎩 <b>Lucien:</b>\n\n<i>Activación VIP forward completada. Acceso directo enviado al candidato.</i>"


def build_forward_error_text(access_msg: str) -> str:
    """Construye texto de error/fallo para admin tras grant no exitoso. Función pura (sin estado ni side-effects)."""
    return f"🎩 <b>Lucien:</b>\n\n<i>{access_msg}</i>"


def build_forward_deep_link(bot_username: str | None, token_code: str | None) -> str:
    """Construye deep link manual para fallback en bloqueo de candidato. Función pura (sin estado ni side-effects)."""
    if token_code and bot_username:
        return f"https://t.me/{bot_username}?start={token_code}"
    return "contacta a Lucien para link"


def build_forward_bot_access_link(bot_username: str | None) -> str | None:
    """Deep link para que un VIP activo reciba su invite desde /start. Función pura."""
    if bot_username:
        return f"https://t.me/{bot_username}?start=acceso_vip"
    return None


async def try_deliver_vip_forward_message(bot, target_user_id: int, access_msg: str) -> tuple[bool, str | None]:
    """Intenta DM al candidato; reintenta sin teclado si el primer envío falla."""
    from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
    from utils.telegram_delivery import classify_bad_request_error, classify_forbidden_error

    for with_keyboard in (True, False):
        try:
            kwargs = {"chat_id": target_user_id, "text": access_msg, "parse_mode": "HTML"}
            if with_keyboard:
                kwargs["reply_markup"] = vip_access_keyboard()
            await bot.send_message(**kwargs)
            return True, None
        except TelegramForbiddenError as exc:
            _, code = classify_forbidden_error(exc)
            return False, code or "forbidden"
        except TelegramBadRequest as exc:
            _, code = classify_bad_request_error(exc)
            if with_keyboard and not code:
                continue
            return False, code or str(exc)
        except Exception as exc:
            if with_keyboard:
                continue
            return False, str(exc)
    return False, "send_failed"


def build_forward_action_menu_text(display: str, candidate_id: int) -> str:
    """Construye texto del menú de acción tras reenvío admin. Función pura (sin estado ni side-effects)."""
    return (
        f"🎩 <b>Lucien:</b>\n\n"
        f"<i>Reenvío detectado de {display} (ID {candidate_id}).</i>\n\n"
        f"¿Qué desea hacer con este visitante?"
    )


def build_forward_besitos_amount_prompt(display: str, candidate_id: int) -> str:
    """Construye prompt para cantidad de besitos en forward admin. Función pura (sin estado ni side-effects)."""
    return (
        f"🎩 <b>Lucien:</b>\n\n"
        f"Indique cuántos besitos otorgará Diana a {display} (ID {candidate_id}):\n\n"
        f"Ejemplo: 50"
    )


def build_forward_besitos_confirm_text(display: str, candidate_id: int, amount: int) -> str:
    """Construye texto de confirmación de besitos forward. Función pura (sin estado ni side-effects)."""
    return (
        f"🎩 <b>Lucien:</b>\n\n"
        f"<i>¿Confirmar otorgamiento de {amount} besitos a {display} (ID {candidate_id})?</i>"
    )


def build_forward_besitos_success_text(amount: int, new_balance: int) -> str:
    """Construye texto de éxito admin tras grant besitos forward. Función pura (sin estado ni side-effects)."""
    return (
        f"🎩 <b>Lucien:</b>\n\n"
        f"<i>Otorgamiento completado: {amount} besitos acreditados.</i>\n\n"
        f"Saldo actual del visitante: {new_balance} besitos."
    )


def build_forward_besitos_visitor_notify(amount: int, balance: int) -> str:
    """Construye notificación al visitante tras grant besitos. Función pura (sin estado ni side-effects)."""
    return LucienVoice.admin_besitos_granted_visitor_notify(amount, balance)


def parse_positive_telegram_user_id(text: str) -> int | None:
    """Parsea ID de Telegram positivo para grant admin. Función pura (sin estado ni side-effects)."""
    raw = (text or "").strip()
    if not raw.isdigit():
        return None
    user_id = int(raw)
    if user_id <= 0:
        return None
    return user_id


def build_forward_besitos_error_text(reason: str) -> str:
    """Construye texto de error admin tras fallo grant besitos. Función pura (sin estado ni side-effects)."""
    return f"🎩 <b>Lucien:</b>\n\n<i>{reason}</i>"


def build_forward_besitos_blocked_notify() -> str:
    """Construye aviso admin si visitante bloqueó al bot tras grant besitos. Función pura (sin estado ni side-effects)."""
    return (
        "🎩 <b>Lucien:</b>\n\n"
        "<i>Los besitos fueron acreditados, pero no pude notificar al visitante "
        "(posible bloqueo).</i>"
    )


def parse_positive_besito_amount(text: str) -> int | None:
    """Parsea cantidad entera positiva de besitos para grant admin. Función pura (sin estado ni side-effects)."""
    raw = (text or "").strip()
    if not raw.isdigit():
        return None
    amount = int(raw)
    if amount <= 0 or amount > MAX_ADMIN_BESITO_GRANT:
        return None
    return amount


async def _answer_forward_vip_manual_fallback(
    bot, target_message, invite_link: str | None, delivery_code: str | None
) -> None:
    """Envía al admin el invite del canal (y deep link acceso_vip) tras fallo de DM."""
    await target_message.edit_text(
        build_forward_success_text(),
        reply_markup=vip_management_keyboard(),
        parse_mode="HTML",
    )
    if not invite_link:
        await target_message.answer(
            build_forward_error_text(
                "VIP activado, pero no pude generar el enlace de acceso. Reintente desde el panel."
            ),
            parse_mode="HTML",
        )
        return
    bot_username = (await bot.get_me()).username
    await target_message.answer(
        build_forward_manual_delivery_notify(
            invite_link,
            build_forward_bot_access_link(bot_username),
            delivery_code,
        ),
        parse_mode="HTML",
    )


async def notify_forward_vip_result(
    bot, target_message, target_user_id: int, ok: bool, access_msg: str, meta: dict, admin_id: int
) -> None:
    """Notifica resultado del grant forward (directo al candidato o fallback al admin que reenvió)."""
    if ok:
        delivered, delivery_code = await try_deliver_vip_forward_message(
            bot, target_user_id, access_msg
        )
        if delivered:
            logger.info(
                f"{__name__} | notificar_directo_vip_forward | user_id={admin_id} | "
                f"target={target_user_id} | resultado=enviado"
            )
            await target_message.edit_text(
                build_forward_success_text(),
                reply_markup=vip_management_keyboard(),
                parse_mode="HTML",
            )
            return
        logger.warning(
            f"{__name__} | notificar_directo_vip_forward_fallo | user_id={admin_id} | "
            f"target={target_user_id} | delivery_code={delivery_code} | vip_activated=True"
        )
        await _answer_forward_vip_manual_fallback(
            bot, target_message, meta.get("invite_link"), delivery_code
        )
        return
    if meta.get("vip_activated") and meta.get("invite_link"):
        await _answer_forward_vip_manual_fallback(
            bot, target_message, meta["invite_link"], "invite_generation_partial"
        )
        return
    await target_message.edit_text(
        build_forward_error_text(access_msg),
        reply_markup=vip_management_keyboard(),
        parse_mode="HTML",
    )


async def notify_forward_besitos_result(
    bot,
    target_message,
    target_user_id: int,
    ok: bool,
    amount: int,
    balance: int,
    admin_id: int,
    *,
    success_keyboard=None,
) -> None:
    """Notifica resultado del grant besitos (visitante o fallback admin). Thin helper (0 svc)."""
    admin_keyboard = success_keyboard or vip_management_keyboard()
    if ok:
        try:
            await bot.send_message(
                chat_id=target_user_id,
                text=build_forward_besitos_visitor_notify(amount, balance),
                parse_mode="HTML",
            )
            logger.info(
                f"{__name__} | notificar_directo_besitos_forward | user_id={admin_id} | "
                f"target={target_user_id} | amount={amount} | resultado=enviado"
            )
            await target_message.edit_text(
                build_forward_besitos_success_text(amount, balance),
                reply_markup=admin_keyboard,
                parse_mode="HTML",
            )
        except Exception as e:
            if "bot was blocked by the user" in str(e):
                logger.warning(
                    f"{__name__} | notificar_directo_besitos_forward_bloqueado | user_id={admin_id} | "
                    f"target={target_user_id}"
                )
            else:
                logger.error(
                    f"{__name__} | notificar_directo_besitos_forward_error | user_id={admin_id} | "
                    f"target={target_user_id} | error={e}"
                )
            await target_message.answer(build_forward_besitos_blocked_notify(), parse_mode="HTML")
    else:
        await target_message.edit_text(
            build_forward_besitos_error_text("No pude acreditar los besitos. Intente de nuevo."),
            reply_markup=admin_keyboard,
            parse_mode="HTML",
        )


# ==================== GESTIÓN DE TARIFAS ====================


@router.callback_query(F.data == "manage_tariffs", lambda cb: is_admin(cb.from_user.id))
async def manage_tariffs(callback: CallbackQuery):
    """Gestión de tarifas VIP"""
    vip_service = VIPService()
    try:
        tariffs = vip_service.get_all_tariffs(active_only=False)

        await callback.message.edit_text(
            LucienVoice.admin_tariff_list(tariffs),
            reply_markup=tariffs_keyboard(tariffs, for_selection=False),
            parse_mode="HTML",
        )
    finally:
        vip_service.close()
    await callback.answer()


@router.callback_query(F.data == "create_tariff", lambda cb: is_admin(cb.from_user.id))
async def create_tariff_start(callback: CallbackQuery, state: FSMContext):
    """Inicia creación de tarifa"""
    await callback.message.edit_text(
        "🎩 <b>Lucien:</b>\n\n"
        "<i>Vamos a calibrar una nueva tarifa para El Diván...</i>\n\n"
        "📋 <b>Paso 1 de 3:</b> Nombre de la tarifa\n"
        "Ejemplos: <code>Mensual</code>, <code>Trimestral</code>, <code>Anual</code>",
        reply_markup=back_keyboard("manage_tariffs"),
        parse_mode="HTML",
    )
    await state.set_state(TariffStates.waiting_name)
    await callback.answer()


@router.message(TariffStates.waiting_name, lambda msg: is_admin(msg.from_user.id))
async def process_tariff_name(message: Message, state: FSMContext):
    """Procesa nombre de tarifa"""
    await state.update_data(name=message.text.strip())

    await message.answer(
        "🎩 <b>Lucien:</b>\n\n"
        "<i>Excelente. Ahora, la duración...</i>\n\n"
        "📋 <b>Paso 2 de 3:</b> Duración en días\n"
        "Ejemplos: <code>30</code> (mensual), <code>90</code> (trimestral), <code>365</code> (anual)",
        reply_markup=back_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(TariffStates.waiting_days)


@router.message(TariffStates.waiting_days, lambda msg: is_admin(msg.from_user.id))
async def process_tariff_days(message: Message, state: FSMContext):
    """Procesa duración de tarifa"""
    try:
        days = int(message.text.strip())
        if days <= 0:
            raise ValueError("Duración debe ser positiva")

        await state.update_data(days=days)

        await message.answer(
            "🎩 <b>Lucien:</b>\n\n"
            "<i>Perfecto. Finalmente, el valor...</i>\n\n"
            "📋 <b>Paso 3 de 3:</b> Precio de la tarifa\n"
            "Ejemplo: <code>29.99 USD</code> o <code>500 MXN</code>",
            reply_markup=back_keyboard(),
            parse_mode="HTML",
        )
        await state.set_state(TariffStates.waiting_price)

    except ValueError:
        await message.answer(
            "🎩 <b>Lucien:</b>\n\n<i>Por favor, indique un número válido de días...</i>",
            reply_markup=back_keyboard(),
            parse_mode="HTML",
        )


@router.message(TariffStates.waiting_price, lambda msg: is_admin(msg.from_user.id))
async def process_tariff_price(message: Message, state: FSMContext):
    """Procesa precio y confirma tarifa"""
    price_text = message.text.strip()

    await state.update_data(price=price_text)
    data = await state.get_data()

    await message.answer(
        f"🎩 <b>Lucien:</b>\n\n"
        f"<i>Permítame confirmar los detalles de esta tarifa...</i>\n\n"
        f"📋 <b>Resumen:</b>\n"
        f"   • Nombre: <b>{data['name']}</b>\n"
        f"   • Duración: <b>{data['days']} días</b>\n"
        f"   • Precio: <b>{data['price']}</b>\n\n"
        f"<i>¿Desea crear esta tarifa?</i>",
        reply_markup=confirmation_keyboard("confirm_tariff", "manage_tariffs"),
        parse_mode="HTML",
    )
    await state.set_state(TariffStates.confirming)


@router.callback_query(TariffStates.confirming, F.data == "confirm_tariff")
async def confirm_tariff(callback: CallbackQuery, state: FSMContext):
    """Crea la tarifa"""
    data = await state.get_data()
    vip_service = VIPService()

    try:
        vip_service.create_tariff(
            name=data["name"], duration_days=data["days"], price=data["price"]
        )

        await callback.message.edit_text(
            LucienVoice.admin_tariff_created(data["name"], data["days"], data["price"]),
            reply_markup=back_keyboard("manage_tariffs"),
            parse_mode="HTML",
        )

    except Exception as e:
        logger.error(f"Error creando tarifa: {e}")
        await callback.message.edit_text(
            LucienVoice.error_message("la creación de la tarifa"),
            reply_markup=back_keyboard("manage_tariffs"),
            parse_mode="HTML",
        )
    finally:
        vip_service.close()

    await state.clear()
    await callback.answer()


# ==================== GENERACIÓN DE TOKENS ====================


@router.callback_query(F.data == "generate_token")
async def generate_token_start(callback: CallbackQuery, state: FSMContext):
    """Inicia generación de token"""
    vip_service = VIPService()
    try:
        tariffs = vip_service.get_all_tariffs(active_only=True)

        if not tariffs:
            await callback.message.edit_text(
                "🎩 <b>Lucien:</b>\n\n"
                "<i>No hay tarifas activas para generar tokens...</i>\n\n"
                "👉 <i>Cree una tarifa primero en 'Gestionar tarifas'.</i>",
                reply_markup=vip_management_keyboard(),
                parse_mode="HTML",
            )
            await callback.answer()
            return

        await callback.message.edit_text(
            "🎩 <b>Lucien:</b>\n\n"
            "<i>Seleccione la tarifa para la cual desea forjar un token de acceso...</i>",
            reply_markup=tariffs_keyboard(tariffs, for_selection=True),
            parse_mode="HTML",
        )
        await state.set_state(TokenStates.selecting_tariff)
    finally:
        vip_service.close()
    await callback.answer()


@router.callback_query(
    TokenStates.selecting_tariff,
    SelectTariffCallback.filter(),
    lambda cb: is_admin(cb.from_user.id),
)
async def generate_token(
    callback: CallbackQuery, state: FSMContext, callback_data: SelectTariffCallback
):
    """Genera el token para la tarifa seleccionada"""
    tariff_id = callback_data.tariff_id
    logger.info(
        f"{__name__} | generar_token | user_id={callback.from_user.id} | tariff_id={tariff_id}"
    )

    vip_service = VIPService()
    try:
        tariff = vip_service.get_tariff(tariff_id)

        if not tariff:
            await callback.answer("Tarifa no encontrada", show_alert=True)
            return

        try:
            token = vip_service.generate_token(tariff_id)
            token_url = (
                f"https://t.me/{(await callback.bot.get_me()).username}?start={token.token_code}"
            )

            await callback.message.edit_text(
                LucienVoice.token_generated(token_url, tariff.name, token.is_gift),
                reply_markup=token_actions_keyboard(token.id, token.is_gift),
                parse_mode="HTML",
            )

        except Exception as e:
            logger.error(f"Error generando token: {e}")
            await callback.message.edit_text(
                LucienVoice.error_message("la generación del token"),
                reply_markup=vip_management_keyboard(),
                parse_mode="HTML",
            )
    finally:
        vip_service.close()

    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "generate_another_token")
async def generate_another_token(callback: CallbackQuery, state: FSMContext):
    """Reinicia el flujo para generar otro token"""
    vip_service = VIPService()
    try:
        tariffs = vip_service.get_all_tariffs(active_only=True)

        if not tariffs:
            await callback.message.edit_text(
                "🎩 <b>Lucien:</b>\n\n"
                "<i>No hay tarifas activas para generar tokens...</i>\n\n"
                "👉 <i>Cree una tarifa primero en 'Gestionar tarifas'.</i>",
                reply_markup=vip_management_keyboard(),
                parse_mode="HTML",
            )
            await callback.answer()
            return

        await callback.message.edit_text(
            "🎩 <b>Lucien:</b>\n\n"
            "<i>Seleccione la tarifa para la cual desea forjar un token de acceso...</i>",
            reply_markup=tariffs_keyboard(tariffs, for_selection=True),
            parse_mode="HTML",
        )
        await state.set_state(TokenStates.selecting_tariff)
    finally:
        vip_service.close()
    await callback.answer()


# ==================== LISTAR TOKENS ====================


@router.callback_query(F.data == "list_tokens")
async def list_tokens(callback: CallbackQuery):
    """Lista tokens generados"""
    vip_service = VIPService()
    try:
        tokens = vip_service.get_all_tokens()[:20]  # Limitar a 20 recientes

        if not tokens:
            await callback.message.edit_text(
                "🎩 <b>Lucien:</b>\n\n<i>No hay tokens registrados en los archivos...</i>",
                reply_markup=vip_management_keyboard(),
                parse_mode="HTML",
            )
            await callback.answer()
            return

        text = """🎩 <b>Lucien:</b>

<i>Los accesos forjados para El Diván...</i>

📋 <b>Tokens recientes:</b>

"""

        buttons = []
        for token in tokens:
            status_emoji = {"active": "🟢", "used": "🔴", "expired": "⚫"}.get(
                token.status.value, "⚪"
            )
            gift_tag = " 🎁" if token.is_gift else ""

            text += f"{status_emoji}{gift_tag} <code>{token.token_code[:16]}...</code> - {token.tariff.name}\n"

            if token.status.value == "active":
                gift_label = "🎁 " if token.is_gift else ""
                buttons.append(
                    [
                        InlineKeyboardButton(
                            text=f"{gift_label}{status_emoji} {token.tariff.name} - Copiar",
                            callback_data=CopyTokenCallback(token_id=token.id).pack(),
                        )
                    ]
                )

        buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="admin_vip")])

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    finally:
        vip_service.close()
    await callback.answer()


@router.callback_query(CopyTokenCallback.filter())
async def copy_token(callback: CallbackQuery, callback_data: CopyTokenCallback):
    """Copia el enlace del token"""
    token_id = callback_data.token_id
    logger.info(f"{__name__} | copy_token | user_id={callback.from_user.id} | token_id={token_id}")

    vip_service = VIPService()
    try:
        token = vip_service.get_token(token_id)

        if not token:
            await callback.answer("Token no encontrado", show_alert=True)
            return

        bot_info = await callback.bot.get_me()
        token_url = f"https://t.me/{bot_info.username}?start={token.token_code}"

        await callback.message.answer(
            f"🔗 <b>Enlace del token:</b>\n<code>{token_url}</code>", parse_mode="HTML"
        )
    finally:
        vip_service.close()
    await callback.answer("Enlace copiado")


@router.callback_query(ToggleGiftCallback.filter())
async def toggle_gift(callback: CallbackQuery, callback_data: ToggleGiftCallback):
    """Marca/desmarca un token como regalo"""
    token_id = callback_data.token_id
    new_gift_status = callback_data.is_gift
    logger.info(
        f"{__name__} | toggle_gift | user_id={callback.from_user.id} | "
        f"token_id={token_id} | is_gift={new_gift_status}"
    )

    vip_service = VIPService()
    try:
        ok = vip_service.set_gift_status(token_id, new_gift_status)
        if not ok:
            await callback.answer("Token no encontrado", show_alert=True)
            return

        token = vip_service.get_token(token_id)
        bot_info = await callback.bot.get_me()
        token_url = f"https://t.me/{bot_info.username}?start={token.token_code}"

        await callback.message.edit_text(
            LucienVoice.token_generated(token_url, token.tariff.name, token.is_gift),
            reply_markup=token_actions_keyboard(token.id, token.is_gift),
            parse_mode="HTML",
        )
        label = "marcado como regalo" if new_gift_status else "marcado como regular"
        await callback.answer(f"✅ Token {label}")
    finally:
        vip_service.close()


# list_subscribers → vip_subscriber_admin_handlers (phase 36)


# ==================== ACCIÓN ADMIN POR REENVÍO (VIP | besitos) ====================


@router.message(
    lambda msg: (
        bool(getattr(msg, "forward_from", None) or getattr(msg, "forward_origin", None))
        and is_admin(msg.from_user.id)
    )
)
async def process_forwarded_admin_candidate(message: Message, state: FSMContext):
    """Procesa reenvío admin: extrae visitante (puro) y muestra menú acción (0 svc)."""
    candidate_id, display = extract_forwarded_candidate(message)
    if not candidate_id:
        await message.answer(
            "🎩 <b>Lucien:</b>\n\n<i>No pude identificar al visitante del reenvío...</i>",
            parse_mode="HTML",
        )
        return
    admin_id = message.from_user.id
    logger.info(
        f"{__name__} | detectar_candidato_reenviado | user_id={admin_id} | "
        f"forwarded_user_id={candidate_id} | display={display}"
    )
    await message.answer(
        build_forward_action_menu_text(display, candidate_id),
        reply_markup=forward_action_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(AdminForwardStates.selecting_action)
    await state.update_data(forward_target_user_id=candidate_id, forward_target_display=display)


@router.callback_query(
    AdminForwardStates.selecting_action,
    ForwardActionCallback.filter(F.action == "vip"),
    lambda cb: is_admin(cb.from_user.id),
)
async def select_forward_action_vip(callback: CallbackQuery, state: FSMContext):
    """Elige activar VIP: 1 svc para tarifas activas."""
    data = await state.get_data()
    target_id = data.get("forward_target_user_id")
    display = data.get("forward_target_display", str(target_id))
    admin_id = callback.from_user.id
    logger.info(
        f"{__name__} | elegir_accion_vip_forward | user_id={admin_id} | target_user_id={target_id}"
    )
    tariffs = []
    with get_service(VIPService) as vip_service:
        tariffs = vip_service.get_all_tariffs(active_only=True)
    if not tariffs:
        await callback.message.edit_text(
            "🎩 <b>Lucien:</b>\n\n"
            "<i>No hay tarifas activas para activar VIP por reenvío...</i>\n\n"
            "👉 <i>Cree una tarifa primero en 'Gestionar tarifas'.</i>",
            reply_markup=vip_management_keyboard(),
            parse_mode="HTML",
        )
        await state.clear()
        await callback.answer()
        return
    await callback.message.edit_text(
        f"🎩 <b>Lucien:</b>\n\n"
        f"<i>Seleccione tarifa para activar/renovar VIP de {display} (ID {target_id})...</i>",
        reply_markup=tariffs_keyboard(tariffs, for_selection=True),
        parse_mode="HTML",
    )
    await state.set_state(AdminForwardStates.vip_selecting_tariff)
    await callback.answer()


@router.callback_query(
    AdminForwardStates.selecting_action,
    ForwardActionCallback.filter(F.action == "besitos"),
    lambda cb: is_admin(cb.from_user.id),
)
async def select_forward_action_besitos(callback: CallbackQuery, state: FSMContext):
    """Elige otorgar besitos: pide cantidad (0 svc)."""
    data = await state.get_data()
    target_id = data.get("forward_target_user_id")
    display = data.get("forward_target_display", str(target_id))
    admin_id = callback.from_user.id
    logger.info(
        f"{__name__} | elegir_accion_besitos_forward | user_id={admin_id} | target_user_id={target_id}"
    )
    await callback.message.edit_text(
        build_forward_besitos_amount_prompt(display, target_id),
        reply_markup=forward_cancel_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(AdminForwardStates.besitos_waiting_amount)
    await callback.answer()


@router.callback_query(ForwardCancelCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def cancel_forward_action(callback: CallbackQuery, state: FSMContext):
    """Cancela flujo forward admin (VIP o besitos)."""
    await state.clear()
    await callback.message.edit_text(
        "🎩 <b>Lucien:</b>\n\n<i>Acción por reenvío cancelada.</i>",
        reply_markup=vip_management_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(
    AdminForwardStates.vip_selecting_tariff,
    SelectTariffCallback.filter(),
    lambda cb: is_admin(cb.from_user.id),
)
async def select_tariff_for_forward_vip(
    callback: CallbackQuery, state: FSMContext, callback_data: SelectTariffCallback
):
    """Selecciona tarifa para forward VIP (transiciona a confirm; 0 svc)."""
    tariff_id = callback_data.tariff_id
    data = await state.get_data()
    target_id = data.get("forward_target_user_id")
    display = data.get("forward_target_display", str(target_id))
    admin_id = callback.from_user.id
    logger.info(
        f"{__name__} | seleccionar_tarifa_vip_forward | user_id={admin_id} | "
        f"tariff_id={tariff_id} | target_user_id={target_id}"
    )
    await callback.message.edit_text(
        f"🎩 <b>Lucien:</b>\n\n"
        f"<i>¿Activar/renovar VIP con esta tarifa para {display} (ID {target_id})?</i>\n\n"
        f"Confirme para proceder vía token interno.",
        reply_markup=forward_confirm_keyboard("vip"),
        parse_mode="HTML",
    )
    await state.update_data(selected_tariff_id=tariff_id)
    await state.set_state(AdminForwardStates.vip_confirming)
    await callback.answer()


@router.message(AdminForwardStates.besitos_waiting_amount, lambda m: is_admin(m.from_user.id))
async def process_besitos_amount_for_forward(message: Message, state: FSMContext):
    """Recibe cantidad de besitos y muestra confirmación (0 svc)."""
    amount = parse_positive_besito_amount(message.text)
    if amount is None:
        await message.answer(
            f"🎩 <b>Lucien:</b>\n\n"
            f"<i>Cantidad inválida. Indique un entero entre 1 y {MAX_ADMIN_BESITO_GRANT}.</i>",
            parse_mode="HTML",
        )
        return
    data = await state.get_data()
    target_id = data.get("forward_target_user_id")
    display = data.get("forward_target_display", str(target_id))
    admin_id = message.from_user.id
    logger.info(
        f"{__name__} | capturar_cantidad_besitos_forward | user_id={admin_id} | "
        f"target_user_id={target_id} | amount={amount}"
    )
    await message.answer(
        build_forward_besitos_confirm_text(display, target_id, amount),
        reply_markup=forward_confirm_keyboard("besitos"),
        parse_mode="HTML",
    )
    await state.update_data(besito_amount=amount)
    await state.set_state(AdminForwardStates.besitos_confirming)


@router.callback_query(
    AdminForwardStates.besitos_confirming,
    ForwardConfirmCallback.filter(F.action == "besitos"),
    lambda cb: is_admin(cb.from_user.id),
)
async def confirm_forward_besitos_grant(callback: CallbackQuery, state: FSMContext):
    """Confirma y ejecuta grant besitos (EXACTLY 1 svc) + notificación visitante."""
    data = await state.get_data()
    target_user_id = data.get("forward_target_user_id")
    amount = data.get("besito_amount")
    admin_id = callback.from_user.id
    logger.info(
        f"{__name__} | confirmar_besitos_forward | user_id={admin_id} | "
        f"target_user_id={target_user_id} | amount={amount}"
    )
    if not target_user_id or not amount:
        await callback.answer("Datos incompletos", show_alert=True)
        await state.clear()
        return
    ok, balance = False, 0
    with get_service(BesitoService) as besito_service:
        ok, balance = besito_service.grant_manual_admin_besitos(target_user_id, amount, admin_id)
    await notify_forward_besitos_result(
        callback.bot, callback.message, target_user_id, ok, amount, balance, admin_id
    )
    await state.clear()
    await callback.answer()


@router.callback_query(
    AdminForwardStates.vip_confirming,
    ForwardConfirmCallback.filter(F.action == "vip"),
    lambda cb: is_admin(cb.from_user.id),
)
async def confirm_forward_vip_activation(callback: CallbackQuery, state: FSMContext):
    """Confirma y ejecuta grant (EXACTLY 1 svc) + directo o fallback admin."""
    data = await state.get_data()
    target_user_id = data.get("forward_target_user_id")
    tariff_id = data.get("selected_tariff_id")
    admin_id = callback.from_user.id
    logger.info(
        f"{__name__} | activar_vip_forward_confirm | user_id={admin_id} | target_user_id={target_user_id} | tariff_id={tariff_id}"
    )
    if not target_user_id or not tariff_id:
        await callback.answer("Datos incompletos", show_alert=True)
        await state.clear()
        return
    ok, access_msg, meta = False, "", {}
    with get_service(VIPService) as vip_service:
        ok, access_msg, meta = await vip_service.grant_vip_from_tariff(
            callback.bot, target_user_id, tariff_id
        )
    await notify_forward_vip_result(
        callback.bot, callback.message, target_user_id, ok, access_msg, meta, admin_id
    )
    await state.clear()
    await callback.answer()
