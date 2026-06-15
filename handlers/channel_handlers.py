"""
Handlers de Canales - Lucien Bot

Gestión de registro y configuración de canales.
"""

import html
import logging
import math

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from keyboards.callback_data import (
    ApproveAllCallback,
    ApproveOneCallback,
    ChannelDetailCallback,
    ChannelTypeCallback,
    ConfigInviteCallback,
    ConfigMessagesCallback,
    ConfigMessageTypeCallback,
    ConfigWaitCallback,
    ConfirmDeleteChannelCallback,
    ConfirmRejectCallback,
    DeleteChannelCallback,
    PendingPageCallback,
    PendingReqCallback,
    RejectOneCallback,
    RestoreMessagesCallback,
    ViewMessagesCallback,
    WaitTimeCallback,
)
from keyboards.inline_keyboards import (
    back_keyboard,
    channel_actions_keyboard,
    channel_management_keyboard,
    channel_type_keyboard,
    confirmation_keyboard,
    wait_time_keyboard,
)
from services import get_service
from services.channel_grant import is_valid_telegram_invite_link
from services.channel_service import ChannelService
from utils.admin import is_admin
from utils.lucien_voice import LucienVoice

logger = logging.getLogger(__name__)
router = Router()

PENDING_PAGE_SIZE = 8


class ChannelStates(StatesGroup):
    waiting_channel_message = State()
    confirming_channel = State()
    selecting_channel_type = State()
    configuring_wait_time = State()
    configuring_wait_time_custom = State()
    configuring_invite_link = State()
    configuring_messages_menu = State()
    configuring_approval_message = State()
    configuring_welcome_message = State()


# ==================== PURE HELPERS ====================


def parse_wait_minutes(text: str) -> int | None:
    """Parsea minutos custom (1–1440). None si inválido."""
    try:
        minutes = int(text.strip())
    except (ValueError, AttributeError):
        return None
    if 1 <= minutes <= 1440:
        return minutes
    return None


def truncate_message_preview(text: str, max_len: int = 120) -> str:
    """Trunca preview de mensaje para UI admin (HTML-escaped)."""
    if not text:
        return "<i>(default Lucien)</i>"
    clean = html.escape(text.strip())
    if len(clean) <= max_len:
        return clean
    return clean[: max_len - 3] + "..."


def format_display_name(req) -> str:
    """Nombre de display escapado para HTML admin."""
    if not req:
        return html.escape("visitante")
    if req.username:
        return html.escape(f"@{req.username}")
    return html.escape(req.first_name or "Anónimo")


def format_display_name_plain(req) -> str:
    """Nombre de display sin HTML para callback.answer toasts."""
    if not req:
        return "visitante"
    if req.username:
        return f"@{req.username}"
    return req.first_name or "Anónimo"


def _truncate_template_preview(text: str, max_len: int = 120) -> str:
    """Trunca preview de template Lucien sin escapar markup HTML."""
    clean = text.strip()
    if len(clean) <= max_len:
        return clean
    return clean[: max_len - 3] + "..."


def format_invite_link_display(invite_link: str | None) -> str:
    """Formatea invite_link para display admin (escaped)."""
    if not invite_link:
        return "No configurado"
    return html.escape(invite_link)


def format_pending_request_line(req, index: int) -> str:
    """Formatea una línea de solicitud pendiente (HTML-safe)."""
    display = format_display_name(req)
    wait_time = req.scheduled_approval_at.strftime("%H:%M")
    return f"{index}. 👤 <b>{display}</b> — Aprobación: {wait_time}\n"


def _clamp_page(page: int, total_count: int) -> int:
    total_pages = max(1, math.ceil(total_count / PENDING_PAGE_SIZE))
    return max(0, min(page, total_pages - 1))


def parse_custom_message_text(message: Message) -> str | None | bool:
    """str=guardar, None=default, False=entrada inválida (sin texto)."""
    raw = message.text
    if raw is None:
        return False
    text = raw.strip()
    if not text or text.lower() == "quitar":
        return None
    return text


def build_pending_request_rows(
    channel_db_id: int, requests: list, page: int
) -> list[list[InlineKeyboardButton]]:
    """Filas approve/reject por solicitud en la página actual."""
    rows: list[list[InlineKeyboardButton]] = []
    for req in requests:
        label = req.username or req.first_name or f"ID {req.user_id}"
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"✅ {label[:20]}",
                    callback_data=ApproveOneCallback(
                        request_id=req.id, channel_id=channel_db_id, page=page
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text="🚫",
                    callback_data=RejectOneCallback(
                        request_id=req.id, channel_id=channel_db_id, page=page
                    ).pack(),
                ),
            ]
        )
    return rows


def build_pending_nav_row(
    channel_db_id: int, page: int, total_count: int
) -> list[InlineKeyboardButton]:
    """Fila de navegación anterior/siguiente."""
    total_pages = max(1, math.ceil(total_count / PENDING_PAGE_SIZE))
    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(
                text="◀️ Anterior",
                callback_data=PendingPageCallback(channel_id=channel_db_id, page=page - 1).pack(),
            )
        )
    if page < total_pages - 1:
        nav.append(
            InlineKeyboardButton(
                text="Siguiente ▶️",
                callback_data=PendingPageCallback(channel_id=channel_db_id, page=page + 1).pack(),
            )
        )
    return nav


def build_pending_footer_rows(channel_db_id: int) -> list[list[InlineKeyboardButton]]:
    """Footer: aprobar todas + volver."""
    return [
        [
            InlineKeyboardButton(
                text="✅ Aprobar todas",
                callback_data=ApproveAllCallback(channel_id=channel_db_id).pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Volver",
                callback_data=ChannelDetailCallback(channel_id=channel_db_id).pack(),
            )
        ],
    ]


def build_pending_requests_keyboard(
    channel_db_id: int,
    requests: list,
    page: int,
    total_count: int,
) -> InlineKeyboardMarkup:
    """Teclado paginado con approve/reject por solicitud."""
    buttons = build_pending_request_rows(channel_db_id, requests, page)
    nav = build_pending_nav_row(channel_db_id, page, total_count)
    if nav:
        buttons.append(nav)
    buttons.extend(build_pending_footer_rows(channel_db_id))
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_pending_list_text(count: int, requests: list, page: int, total_pages: int) -> str:
    """Texto completo de lista paginada usando format_pending_request_line."""
    if count == 0:
        return LucienVoice.admin_pending_requests_empty()
    text = LucienVoice.admin_pending_requests_header(count, page, total_pages)
    for i, req in enumerate(requests, start=page * PENDING_PAGE_SIZE + 1):
        text += format_pending_request_line(req, i)
    return text


def build_messages_menu_keyboard(channel_db_id: int) -> InlineKeyboardMarkup:
    """Menú de configuración de mensajes custom."""
    buttons = [
        [
            InlineKeyboardButton(
                text="📨 Editar ritual",
                callback_data=ConfigMessageTypeCallback(
                    channel_id=channel_db_id, msg_type="approval"
                ).pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="👋 Editar bienvenida",
                callback_data=ConfigMessageTypeCallback(
                    channel_id=channel_db_id, msg_type="welcome"
                ).pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="👁 Ver actuales",
                callback_data=ViewMessagesCallback(channel_id=channel_db_id).pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="♻️ Restaurar defaults",
                callback_data=RestoreMessagesCallback(
                    channel_id=channel_db_id, msg_type="all"
                ).pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Volver",
                callback_data=ChannelDetailCallback(channel_id=channel_db_id).pack(),
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _resolve_message_preview(channel, field_name: str, default_fn) -> str:
    """Preview de mensaje custom o default (defaults sin double-escape de template)."""
    custom = getattr(channel, field_name, None)
    if custom and str(custom).strip():
        return truncate_message_preview(custom)
    channel_name = channel.channel_name or "Los Kinkys"
    return _truncate_template_preview(default_fn(channel_name))


async def _deny_non_admin_message(message: Message, state: FSMContext) -> bool:
    """Retorna True si el usuario fue denegado."""
    if not is_admin(message.from_user.id):
        await message.answer(LucienVoice.admin_channel_access_denied(), parse_mode="HTML")
        await state.clear()
        return True
    return False


async def _deny_non_admin_callback(callback: CallbackQuery) -> bool:
    """Retorna True si el custodio fue denegado."""
    if not is_admin(callback.from_user.id):
        await callback.answer("Acceso denegado", show_alert=True)
        return True
    return False


async def _render_pending_list(callback: CallbackQuery, channel_db_id: int, page: int = 0) -> None:
    """Renderiza lista paginada de solicitudes pendientes."""
    with get_service(ChannelService) as svc:
        all_requests = svc.get_pending_requests_by_channel(channel_db_id)
        total_count = len(all_requests)
        page = _clamp_page(page, total_count)
        start = page * PENDING_PAGE_SIZE
        page_requests = all_requests[start : start + PENDING_PAGE_SIZE]
        total_pages = max(1, math.ceil(total_count / PENDING_PAGE_SIZE))
        text = build_pending_list_text(total_count, page_requests, page, total_pages)
        keyboard = build_pending_requests_keyboard(channel_db_id, page_requests, page, total_count)

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


# ==================== REGISTRO DE CANAL ====================


@router.callback_query(F.data == "add_channel", lambda cb: is_admin(cb.from_user.id))
async def add_channel_start(callback: CallbackQuery, state: FSMContext):
    """Inicia el flujo de agregar canal"""
    await callback.message.edit_text(
        "🎩 <b>Lucien:</b>\n\n"
        "<i>Para registrar un nuevo dominio en los archivos de Diana,\n"
        "necesito que reenvíe cualquier mensaje del canal objetivo.</i>\n\n"
        "📋 <b>Instrucciones:</b>\n"
        "1. Vaya al canal que desea registrar\n"
        "2. Reenvíe cualquier mensaje de ese canal aquí\n"
        "3. Yo extraeré el ID automáticamente\n\n"
        "<i>Esto me permitirá identificar el dominio correctamente...</i>",
        reply_markup=back_keyboard("admin_channels"),
        parse_mode="HTML",
    )
    await state.set_state(ChannelStates.waiting_channel_message)
    await callback.answer()


@router.message(ChannelStates.waiting_channel_message, F.forward_from_chat)
async def process_channel_message(message: Message, state: FSMContext):
    """Procesa el mensaje reenviado del canal"""
    if await _deny_non_admin_message(message, state):
        return

    forwarded_chat = message.forward_from_chat
    if not forwarded_chat:
        await message.answer(
            "🎩 <b>Lucien:</b>\n\n"
            "<i>No pude identificar el origen de ese mensaje.\n"
            "Asegúrese de reenviar desde el canal directamente...</i>",
            parse_mode="HTML",
        )
        return

    await state.update_data(
        channel_id=forwarded_chat.id,
        channel_name=forwarded_chat.title or forwarded_chat.username or "Canal sin nombre",
    )

    await message.answer(
        f"🎩 <b>Lucien:</b>\n\n"
        f"<i>He detectado el siguiente dominio:</i>\n\n"
        f"📋 <b>Nombre:</b> {html.escape(forwarded_chat.title or 'Sin nombre')}\n"
        f"🆔 <b>ID:</b> <code>{forwarded_chat.id}</code>\n\n"
        f"<i>¿Desea registrar este canal en los archivos de Diana?</i>",
        reply_markup=confirmation_keyboard("confirm_channel", "admin_channels"),
        parse_mode="HTML",
    )
    await state.set_state(ChannelStates.confirming_channel)


@router.callback_query(
    ChannelStates.confirming_channel,
    F.data == "confirm_channel",
    lambda cb: is_admin(cb.from_user.id),
)
async def confirm_channel(callback: CallbackQuery, state: FSMContext):
    """Confirma el registro del canal y pide tipo"""
    await callback.message.edit_text(
        "🎩 <b>Lucien:</b>\n\n"
        "<i>Excelente. Ahora, ¿qué tipo de dominio es este?</i>\n\n"
        "🚪 <b>Vestíbulo (Free):</b> Acceso con tiempo de espera\n"
        "👑 <b>El Diván (VIP):</b> Acceso mediante tokens",
        reply_markup=channel_type_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(ChannelStates.selecting_channel_type)
    await callback.answer()


@router.callback_query(
    ChannelStates.selecting_channel_type,
    ChannelTypeCallback.filter(),
    lambda cb: is_admin(cb.from_user.id),
)
async def set_channel_type(
    callback: CallbackQuery, state: FSMContext, callback_data: ChannelTypeCallback
):
    """Establece el tipo de canal y registra"""
    channel_type = callback_data.action
    data = await state.get_data()
    admin_id = callback.from_user.id

    try:
        with get_service(ChannelService) as svc:
            channel = svc.create_channel(
                channel_id=data["channel_id"],
                channel_name=data["channel_name"],
                channel_type=channel_type,
            )

        logger.info(
            f"channel_handlers | register | user_id={admin_id} | "
            f"result=ok channel={channel.channel_name}"
        )
        await callback.message.edit_text(
            LucienVoice.admin_channel_registered(data["channel_name"], channel_type),
            reply_markup=channel_management_keyboard(),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"channel_handlers | register | user_id={admin_id} | result=error {e}")
        await callback.message.edit_text(
            LucienVoice.error_message("el registro del canal"),
            reply_markup=channel_management_keyboard(),
            parse_mode="HTML",
        )

    await state.clear()
    await callback.answer()


# ==================== LISTAR CANALES ====================


@router.callback_query(F.data == "list_channels", lambda cb: is_admin(cb.from_user.id))
async def list_channels(callback: CallbackQuery):
    """Lista todos los canales registrados"""
    if await _deny_non_admin_callback(callback):
        return

    with get_service(ChannelService) as svc:
        channels = svc.get_all_channels()

        if not channels:
            await callback.message.edit_text(
                LucienVoice.admin_channel_list([]),
                reply_markup=channel_management_keyboard(),
                parse_mode="HTML",
            )
            await callback.answer()
            return

        text = LucienVoice.admin_channel_list(channels)
        buttons = []
        for ch in channels:
            emoji = "🚪" if ch.channel_type.value == "free" else "👑"
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"{emoji} {ch.channel_name or 'Sin nombre'}",
                        callback_data=ChannelDetailCallback(channel_id=ch.id).pack(),
                    )
                ]
            )
        buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="admin_channels")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(ChannelDetailCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def channel_detail(callback: CallbackQuery, callback_data: ChannelDetailCallback):
    """Muestra detalles y acciones de un canal"""
    channel_id = callback_data.channel_id

    with get_service(ChannelService) as svc:
        channel = svc.get_channel_by_db_id(channel_id)
        if not channel:
            await callback.answer("Canal no encontrado", show_alert=True)
            return

        type_text = "Vestíbulo" if channel.channel_type.value == "free" else "Círculo VIP"
        type_emoji = "🚪" if channel.channel_type.value == "free" else "👑"
        pending_count = (
            svc.count_pending_requests(channel_id) if channel.channel_type.value == "free" else 0
        )

        text = f"""🎩 <b>Lucien:</b>

<i>Detalles del dominio seleccionado...</i>

{type_emoji} <b>{html.escape(channel.channel_name or "Sin nombre")}</b>
📋 <b>Tipo:</b> {type_text}
🆔 <b>ID:</b> <code>{channel.channel_id}</code>
"""
        if channel.channel_type.value == "free":
            text += f"⏱️ <b>Tiempo de espera:</b> {channel.wait_time_minutes} minutos\n"
            text += f"👥 <b>Solicitudes pendientes:</b> {pending_count}\n"
        text += "\n<i>¿Qué desea hacer con este dominio?</i>"

        await callback.message.edit_text(
            text,
            reply_markup=channel_actions_keyboard(channel_id, channel.channel_type.value),
            parse_mode="HTML",
        )
    await callback.answer()


# ==================== CONFIGURAR TIEMPO DE ESPERA ====================


@router.callback_query(ConfigWaitCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def config_wait_time(
    callback: CallbackQuery, state: FSMContext, callback_data: ConfigWaitCallback
):
    """Configura tiempo de espera para canal Free"""
    channel_id = callback_data.channel_id
    await state.update_data(channel_id=channel_id)

    await callback.message.edit_text(
        "🎩 <b>Lucien:</b>\n\n"
        "<i>¿Cuánta paciencia requerirán los visitantes de este vestíbulo?</i>\n\n"
        "Seleccione el tiempo de espera antes de la aceptación automática:",
        reply_markup=wait_time_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(ChannelStates.configuring_wait_time)
    await callback.answer()


@router.callback_query(
    ChannelStates.configuring_wait_time,
    WaitTimeCallback.filter(),
    lambda cb: is_admin(cb.from_user.id),
)
async def set_wait_time(
    callback: CallbackQuery, state: FSMContext, callback_data: WaitTimeCallback
):
    """Establece el tiempo de espera"""
    data = callback_data.minutes
    state_data = await state.get_data()
    channel_id = state_data["channel_id"]
    admin_id = callback.from_user.id

    if data == "custom":
        await callback.message.edit_text(
            "🎩 <b>Lucien:</b>\n\n"
            "<i>Indíqueme el tiempo de espera deseado en minutos...</i>\n\n"
            "Ejemplo: <code>7</code> para 7 minutos",
            reply_markup=back_keyboard(ChannelDetailCallback(channel_id=channel_id).pack()),
            parse_mode="HTML",
        )
        await state.set_state(ChannelStates.configuring_wait_time_custom)
        await callback.answer()
        return

    minutes = int(data)
    with get_service(ChannelService) as svc:
        svc.update_wait_time(channel_id, minutes)

    logger.info(f"channel_handlers | wait_time | user_id={admin_id} | result={minutes}min")
    await callback.message.edit_text(
        LucienVoice.admin_wait_time_updated(minutes),
        reply_markup=back_keyboard(ChannelDetailCallback(channel_id=channel_id).pack()),
        parse_mode="HTML",
    )
    await state.clear()
    await callback.answer()


@router.message(ChannelStates.configuring_wait_time_custom)
async def process_custom_wait_time(message: Message, state: FSMContext):
    """Procesa tiempo de espera custom ingresado por texto."""
    if await _deny_non_admin_message(message, state):
        return

    minutes = parse_wait_minutes(message.text or "")
    data = await state.get_data()
    channel_id = data["channel_id"]
    admin_id = message.from_user.id

    if minutes is None:
        await message.answer(LucienVoice.admin_wait_time_invalid(), parse_mode="HTML")
        return

    with get_service(ChannelService) as svc:
        svc.update_wait_time(channel_id, minutes)

    logger.info(f"channel_handlers | wait_time_custom | user_id={admin_id} | result={minutes}min")
    await message.answer(
        LucienVoice.admin_wait_time_updated(minutes),
        reply_markup=back_keyboard(ChannelDetailCallback(channel_id=channel_id).pack()),
        parse_mode="HTML",
    )
    await state.clear()


# ==================== CONFIGURAR ENLACE DE INVITACIÓN ====================


@router.callback_query(ConfigInviteCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def config_invite_link_start(
    callback: CallbackQuery, state: FSMContext, callback_data: ConfigInviteCallback
):
    """Inicia la configuración del enlace de invitación"""
    channel_id = callback_data.channel_id

    with get_service(ChannelService) as svc:
        channel = svc.get_channel_by_db_id(channel_id)
        current = (
            f"\n\n<i>Enlace actual:</i> <code>{format_invite_link_display(channel.invite_link)}</code>"
            if channel
            else ""
        )

    await state.update_data(channel_id=channel_id)
    await callback.message.edit_text(
        f"🎩 <b>Lucien:</b>\n\n"
        f"<i>Proporcione el enlace de invitación para este vestíbulo.</i>\n\n"
        f"<code>https://t.me/+ABC123xyz</code>\n"
        f"<code>https://t.me/srtakinky</code>{current}\n\n"
        f'<i>Envíe el enlace o escriba "quitar" para eliminarlo.</i>',
        reply_markup=back_keyboard(ChannelDetailCallback(channel_id=channel_id).pack()),
        parse_mode="HTML",
    )
    await state.set_state(ChannelStates.configuring_invite_link)
    await callback.answer()


@router.message(ChannelStates.configuring_invite_link)
async def process_invite_link(message: Message, state: FSMContext):
    """Procesa el enlace de invitación ingresado"""
    if await _deny_non_admin_message(message, state):
        return

    raw = (message.text or "").strip()
    if not raw:
        await message.answer(
            "🎩 <b>Lucien:</b>\n\n<i>Envíe un enlace de texto o escriba <code>quitar</code>.</i>",
            parse_mode="HTML",
        )
        return
    link = None if raw.lower() == "quitar" else raw
    if link and not is_valid_telegram_invite_link(link):
        await message.answer(
            "🎩 <b>Lucien:</b>\n\n"
            "<i>El enlace no es válido. Use formato <code>https://t.me/...</code></i>",
            parse_mode="HTML",
        )
        return

    data = await state.get_data()
    channel_id = data["channel_id"]

    with get_service(ChannelService) as svc:
        if not svc.update_invite_link(channel_id, link):
            await message.answer(
                "🎩 <b>Lucien:</b>\n\n"
                "<i>No pude guardar ese enlace. Verifique el formato.</i>",
                parse_mode="HTML",
            )
            return
        channel = svc.get_channel_by_db_id(channel_id)
        name = html.escape(channel.channel_name if channel else "este vestíbulo")

    if link:
        await message.answer(
            f"🎩 <b>Lucien:</b>\n\n"
            f"<i>El enlace de invitación para <b>{name}</b> ha sido actualizado.</i>\n\n"
            f"🔗 <code>{html.escape(link)}</code>",
            reply_markup=back_keyboard(ChannelDetailCallback(channel_id=channel_id).pack()),
            parse_mode="HTML",
        )
    else:
        await message.answer(
            f"🎩 <b>Lucien:</b>\n\n"
            f"<i>El enlace de invitación para <b>{name}</b> ha sido eliminado.</i>",
            reply_markup=back_keyboard(ChannelDetailCallback(channel_id=channel_id).pack()),
            parse_mode="HTML",
        )
    await state.clear()


# ==================== CONFIGURAR MENSAJES ====================


@router.callback_query(ConfigMessagesCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def config_messages_menu(
    callback: CallbackQuery, state: FSMContext, callback_data: ConfigMessagesCallback
):
    """Menú de configuración de mensajes custom."""
    channel_db_id = callback_data.channel_id
    await state.update_data(channel_id=channel_db_id)

    with get_service(ChannelService) as svc:
        channel = svc.get_channel_by_db_id(channel_db_id)
        if not channel:
            await callback.answer("Canal no encontrado", show_alert=True)
            return
        name = channel.channel_name or "Sin nombre"

    await callback.message.edit_text(
        LucienVoice.admin_messages_menu(name),
        reply_markup=build_messages_menu_keyboard(channel_db_id),
        parse_mode="HTML",
    )
    await state.set_state(ChannelStates.configuring_messages_menu)
    await callback.answer()


@router.callback_query(ConfigMessageTypeCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def config_message_type_select(
    callback: CallbackQuery, state: FSMContext, callback_data: ConfigMessageTypeCallback
):
    """Inicia edición de mensaje ritual o bienvenida."""
    channel_db_id = callback_data.channel_id
    msg_type = callback_data.msg_type
    await state.update_data(channel_id=channel_db_id, msg_type=msg_type)

    if msg_type == "approval":
        await state.set_state(ChannelStates.configuring_approval_message)
    else:
        await state.set_state(ChannelStates.configuring_welcome_message)

    await callback.message.edit_text(
        LucienVoice.admin_message_edit_prompt(msg_type),
        reply_markup=back_keyboard(ConfigMessagesCallback(channel_id=channel_db_id).pack()),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(ViewMessagesCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def view_current_messages(callback: CallbackQuery, callback_data: ViewMessagesCallback):
    """Muestra preview de mensajes actuales."""
    channel_db_id = callback_data.channel_id

    with get_service(ChannelService) as svc:
        channel = svc.get_channel_by_db_id(channel_db_id)
        if not channel:
            await callback.answer("Canal no encontrado", show_alert=True)
            return
        approval_preview = _resolve_message_preview(
            channel, "approval_message", LucienVoice.free_entry_ritual
        )
        welcome_preview = _resolve_message_preview(
            channel, "welcome_message", LucienVoice.free_entry_welcome
        )

    await callback.message.edit_text(
        LucienVoice.admin_message_preview(approval_preview, welcome_preview),
        reply_markup=build_messages_menu_keyboard(channel_db_id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(RestoreMessagesCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def restore_default_messages(callback: CallbackQuery, callback_data: RestoreMessagesCallback):
    """Restaura mensajes a default Lucien."""
    channel_db_id = callback_data.channel_id
    msg_type = callback_data.msg_type
    admin_id = callback.from_user.id

    with get_service(ChannelService) as svc:
        svc.clear_custom_messages(channel_db_id, msg_type)

    logger.info(f"channel_handlers | restore_messages | user_id={admin_id} | result={msg_type}")
    await callback.message.edit_text(
        LucienVoice.admin_message_restored(msg_type),
        reply_markup=build_messages_menu_keyboard(channel_db_id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(ChannelStates.configuring_approval_message)
async def save_approval_message(message: Message, state: FSMContext):
    """Guarda mensaje ritual custom."""
    if await _deny_non_admin_message(message, state):
        return

    data = await state.get_data()
    channel_id = data["channel_id"]
    text = parse_custom_message_text(message)
    if text is False:
        await message.answer(LucienVoice.admin_message_edit_prompt("approval"), parse_mode="HTML")
        return

    with get_service(ChannelService) as svc:
        svc.update_approval_message(channel_id, text)

    await message.answer(
        LucienVoice.admin_message_saved("approval"),
        reply_markup=build_messages_menu_keyboard(channel_id),
        parse_mode="HTML",
    )
    await state.set_state(ChannelStates.configuring_messages_menu)


@router.message(ChannelStates.configuring_welcome_message)
async def save_welcome_message(message: Message, state: FSMContext):
    """Guarda mensaje de bienvenida custom."""
    if await _deny_non_admin_message(message, state):
        return

    data = await state.get_data()
    channel_id = data["channel_id"]
    text = parse_custom_message_text(message)
    if text is False:
        await message.answer(LucienVoice.admin_message_edit_prompt("welcome"), parse_mode="HTML")
        return

    with get_service(ChannelService) as svc:
        svc.update_welcome_message(channel_id, text)

    await message.answer(
        LucienVoice.admin_message_saved("welcome"),
        reply_markup=build_messages_menu_keyboard(channel_id),
        parse_mode="HTML",
    )
    await state.set_state(ChannelStates.configuring_messages_menu)


# ==================== SOLICITUDES PENDIENTES ====================


@router.callback_query(PendingReqCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def view_pending_requests(callback: CallbackQuery, callback_data: PendingReqCallback):
    """Ver solicitudes pendientes de un canal (página 0)."""
    await _render_pending_list(callback, callback_data.channel_id, page=0)
    await callback.answer()


@router.callback_query(PendingPageCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def pending_page_nav(callback: CallbackQuery, callback_data: PendingPageCallback):
    """Navegación paginada de solicitudes pendientes."""
    with get_service(ChannelService) as svc:
        total_count = svc.count_pending_requests(callback_data.channel_id)
        page = _clamp_page(callback_data.page, total_count)
    await _render_pending_list(callback, callback_data.channel_id, page=page)
    await callback.answer()


@router.callback_query(ApproveOneCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def approve_one_request(callback: CallbackQuery, callback_data: ApproveOneCallback):
    """Aprueba una solicitud individual con grant real."""
    request_id = callback_data.request_id
    channel_db_id = callback_data.channel_id
    page = callback_data.page
    admin_id = callback.from_user.id

    with get_service(ChannelService) as svc:
        req = svc.get_valid_pending_request(request_id, channel_db_id)
        if not req:
            await callback.answer(LucienVoice.toast_approve_one_failed(), show_alert=True)
            return
        display_plain = format_display_name_plain(req)
        result = await svc.approve_request_now(request_id, channel_db_id, callback.bot)

    if result.success:
        logger.info(
            f"channel_handlers | approve_one | user_id={admin_id} | "
            f"result=ok request_id={request_id}"
        )
        toast = LucienVoice.toast_approve_one_success(display_plain)
    else:
        logger.warning(
            f"channel_handlers | approve_one | user_id={admin_id} | "
            f"result=fail request_id={request_id}"
        )
        toast = LucienVoice.toast_approve_one_failed()

    await _render_pending_list(callback, channel_db_id, page=page)
    await callback.answer(toast, show_alert=not result.success)


@router.callback_query(RejectOneCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def reject_one_request(callback: CallbackQuery, callback_data: RejectOneCallback):
    """Muestra confirmación de rechazo individual."""
    request_id = callback_data.request_id
    channel_db_id = callback_data.channel_id
    page = callback_data.page

    with get_service(ChannelService) as svc:
        req = svc.get_valid_pending_request(request_id, channel_db_id)
        if not req:
            await callback.answer(LucienVoice.toast_reject_failed(), show_alert=True)
            return
        display_name = format_display_name(req)

    await callback.message.edit_text(
        LucienVoice.admin_reject_confirm(display_name),
        reply_markup=confirmation_keyboard(
            ConfirmRejectCallback(
                request_id=request_id, channel_id=channel_db_id, page=page
            ).pack(),
            PendingPageCallback(channel_id=channel_db_id, page=page).pack(),
        ),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(ConfirmRejectCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def confirm_reject_request(callback: CallbackQuery, callback_data: ConfirmRejectCallback):
    """Confirma y ejecuta rechazo individual."""
    request_id = callback_data.request_id
    channel_db_id = callback_data.channel_id
    page = callback_data.page
    admin_id = callback.from_user.id

    with get_service(ChannelService) as svc:
        req = svc.get_valid_pending_request(request_id, channel_db_id)
        display_plain = format_display_name_plain(req)
        ok = await svc.reject_request_now(request_id, channel_db_id, callback.bot)

    logger.info(
        f"channel_handlers | reject_one | user_id={admin_id} | "
        f"result={'ok' if ok else 'fail'} request_id={request_id}"
    )

    await _render_pending_list(callback, channel_db_id, page=page)
    if not ok:
        await callback.answer(LucienVoice.toast_reject_failed(), show_alert=True)
        return
    await callback.answer(LucienVoice.toast_reject_success(display_plain))


@router.callback_query(ApproveAllCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def approve_all_requests(callback: CallbackQuery, callback_data: ApproveAllCallback):
    """Aprueba todas las solicitudes pendientes con grant real en Telegram."""
    channel_id = callback_data.channel_id
    admin_id = callback.from_user.id

    with get_service(ChannelService) as svc:
        pending_count = svc.count_pending_requests(channel_id)
        if pending_count == 0:
            await callback.message.edit_text(
                LucienVoice.admin_approve_all_empty(),
                reply_markup=back_keyboard(ChannelDetailCallback(channel_id=channel_id).pack()),
                parse_mode="HTML",
            )
            await callback.answer(LucienVoice.toast_approve_all_empty())
            return
        result = await svc.approve_all_pending_now(channel_id, callback.bot)

    logger.info(
        f"channel_handlers | approve_all | user_id={admin_id} | "
        f"result=approved={result.approved} failed={result.failed}"
    )
    await callback.message.edit_text(
        LucienVoice.admin_requests_cleared(result.approved, result.failed, result.errors or None),
        reply_markup=back_keyboard(ChannelDetailCallback(channel_id=channel_id).pack()),
        parse_mode="HTML",
    )
    if result.approved == 0 and result.failed > 0:
        await callback.answer(LucienVoice.toast_approve_all_failed(), show_alert=True)
    else:
        await callback.answer(LucienVoice.toast_approve_all_success(result.approved))


# ==================== ELIMINAR CANAL ====================


@router.callback_query(DeleteChannelCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def delete_channel_confirm(callback: CallbackQuery, callback_data: DeleteChannelCallback):
    """Confirma eliminación de canal"""
    channel_id = callback_data.channel_id

    await callback.message.edit_text(
        "🎩 <b>Lucien:</b>\n\n"
        "<i>¿Está seguro de que desea remover este dominio de los archivos de Diana?</i>\n\n"
        "⚠️ <b>Esta acción no se puede deshacer.</b>",
        reply_markup=confirmation_keyboard(
            ConfirmDeleteChannelCallback(channel_id=channel_id).pack(),
            ChannelDetailCallback(channel_id=channel_id).pack(),
        ),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(ConfirmDeleteChannelCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def delete_channel(callback: CallbackQuery, callback_data: ConfirmDeleteChannelCallback):
    """Elimina el canal"""
    channel_id = callback_data.channel_id
    admin_id = callback.from_user.id

    with get_service(ChannelService) as svc:
        channel = svc.get_channel_by_db_id(channel_id)
        if channel:
            channel_name = channel.channel_name
            svc.delete_channel(channel_id)
            logger.info(
                f"channel_handlers | delete | user_id={admin_id} | result=ok channel={channel_name}"
            )
            await callback.message.edit_text(
                LucienVoice.admin_channel_deleted(channel_name),
                reply_markup=channel_management_keyboard(),
                parse_mode="HTML",
            )
        else:
            await callback.message.edit_text(
                LucienVoice.error_message("la eliminación"),
                reply_markup=channel_management_keyboard(),
                parse_mode="HTML",
            )
    await callback.answer()
