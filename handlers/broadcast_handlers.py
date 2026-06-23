"""
Handlers de Broadcasting - Lucien Bot

Flujo conversacional completo para enviar mensajes con reacciones.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from keyboards.callback_data import (
    BroadcastChannelCallback,
    BroadcastProtectCallback,
    ReactionCallback,
    ToggleExtraButtonCallback,
    ToggleReactionCallback,
)
from keyboards.inline_keyboards import (
    back_keyboard,
    broadcast_back_keyboard,
    cancel_keyboard,
)
from services import get_service
from services.broadcast_service import BroadcastService
from services.channel_service import ChannelService
from utils.admin import is_admin

if TYPE_CHECKING:
    from models.models import BroadcastMessage

logger = logging.getLogger(__name__)
router = Router()


def build_send_reaction_markup(
    broadcast_id: int,
    selected_emoji_ids: list[int],
    get_emoji,
) -> InlineKeyboardMarkup | None:
    """Construye teclado de reacciones para envío de broadcast. Función pura."""
    buttons = []
    for emoji_id in selected_emoji_ids:
        emoji = get_emoji(emoji_id)
        if emoji:
            buttons.append(
                InlineKeyboardButton(
                    text=f"{emoji.emoji}",
                    callback_data=ReactionCallback(
                        broadcast_id=broadcast_id, emoji_id=emoji.id
                    ).pack(),
                )
            )
    if not buttons:
        return None
    return InlineKeyboardMarkup(inline_keyboard=[buttons])


def build_broadcast_send_markup(
    broadcast_id: int,
    selected_emoji_ids: list[int],
    extra_button,  # BroadcastButton | None
    get_emoji,
) -> InlineKeyboardMarkup | None:
    """Construye markup combinado: reacciones (si hay) + botón URL extra (si hay). Función pura (sin estado ni side-effects)."""
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    from keyboards.callback_data import ReactionCallback

    rows = []
    # reactions row
    if selected_emoji_ids:
        reaction_row = []
        for eid in selected_emoji_ids:
            em = get_emoji(eid)
            if em:
                reaction_row.append(
                    InlineKeyboardButton(
                        text=em.emoji,
                        callback_data=ReactionCallback(
                            broadcast_id=broadcast_id, emoji_id=em.id
                        ).pack(),
                    )
                )
        if reaction_row:
            rows.append(reaction_row)
    # extra button row
    if extra_button:
        rows.append([InlineKeyboardButton(text=extra_button.label, url=extra_button.url)])
    if not rows:
        return None
    return InlineKeyboardMarkup(inline_keyboard=rows)


def persist_broadcast_from_state(data: dict, admin_id: int, broadcast_service) -> BroadcastMessage:  # noqa: F821 - forward ref under TYPE_CHECKING + postponed annotations
    """Persiste BroadcastMessage desde estado FSM + extra_button_id. Delega a servicio."""
    selected_emojis = data.get("selected_emojis", [])
    extra_button_id = data.get("extra_button_id")
    selected_emoji_ids_str = ",".join(str(eid) for eid in selected_emojis)
    return broadcast_service.create_broadcast_message(
        message_id=0,
        channel_id=data.get("channel_id"),
        admin_id=admin_id,
        text=data.get("text", ""),
        has_attachment=data.get("has_attachment", False),
        attachment_type=data.get("attachment_type"),
        attachment_file_id=data.get("attachment_file_id"),
        has_reactions=len(selected_emojis) > 0,
        is_protected=data.get("is_protected", False),
        selected_emoji_ids=selected_emoji_ids_str,
        extra_button_id=extra_button_id,
    )


def build_broadcast_preview_text(data: dict, extra_button_info: str = "❌") -> str:
    """Construye el texto completo de preview/resumen del broadcast (incluye botón extra). Función pura (sin estado ni side-effects)."""
    preview_text = data.get("text", "")
    has_attachment = data.get("has_attachment", False)
    has_reactions = len(data.get("selected_emojis", [])) > 0
    is_protected = data.get("is_protected", False)

    return f"""🎩 <b>Lucien:</b>

<i>Así se verá su mensaje en el canal...</i>

📋 <b>Resumen:</b>
   • Canal: {data.get("channel_name", "Desconocido")}
   • Texto: {"✅" if preview_text else "❌"}
   • Adjunto: {"✅ " + data.get("attachment_type", "") if has_attachment else "❌"}
   • Reacciones: {"✅" if has_reactions else "❌"}
   • Botón extra: {extra_button_info}
   • Protección: {"🔒 Sí" if is_protected else "❌ No"}

---

<b>Preview del mensaje:</b>

{preview_text[:500]}{"..." if len(preview_text) > 500 else ""}

---

<i>¿Desea enviar este mensaje?</i>"""


def build_extra_button_selection_keyboard(
    buttons: list, selected_id: int | None
) -> InlineKeyboardMarkup:
    """Construye teclado single-choice para botones extra (+ 'Ninguno' + Continuar). Función pura (sin estado ni side-effects)."""
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    from keyboards.callback_data import ToggleExtraButtonCallback

    rows = []
    for btn in buttons:
        is_sel = selected_id == btn.id
        check = "✅ " if is_sel else "⬜ "
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{check}{btn.label}",
                    callback_data=ToggleExtraButtonCallback(button_id=btn.id).pack(),
                )
            ]
        )

    ninguno_sel = selected_id is None or selected_id == 0
    rows.append(
        [
            InlineKeyboardButton(
                text=f"{'✅ ' if ninguno_sel else '⬜ '}⏭️ Ninguno",
                callback_data=ToggleExtraButtonCallback(button_id=0).pack(),
            )
        ]
    )
    rows.append([InlineKeyboardButton(text="✅ Continuar", callback_data="extra_button_continue")])
    rows.append([InlineKeyboardButton(text="🔙 Volver", callback_data="broadcast_back_extra")])
    rows.append([InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_gamification")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# Estados para FSM
class BroadcastStates(StatesGroup):
    selecting_channel = State()
    waiting_text = State()
    waiting_attachment_decision = State()
    waiting_attachment = State()
    waiting_reaction_decision = State()
    selecting_reactions = State()
    waiting_extra_button_decision = State()
    selecting_extra_button = State()
    waiting_protection_decision = State()
    confirming = State()


# ==================== INICIAR BROADCAST ====================


@router.callback_query(F.data == "send_broadcast", lambda cb: is_admin(cb.from_user.id))
async def send_broadcast_start(callback: CallbackQuery, state: FSMContext):
    """Inicia el flujo de broadcast - seleccionar canal"""
    with get_service(ChannelService) as channel_service:
        channels = channel_service.get_all_channels()

    if not channels:
        await callback.message.edit_text(
            """🎩 <b>Lucien:</b>

<i>No hay dominios registrados para enviar mensajes...</i>

👉 <i>Registre un canal primero desde el panel de administración.</i>""",
            reply_markup=back_keyboard("admin_gamification"),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    # Crear botones para cada canal
    buttons = []
    for ch in channels:
        emoji = "🚪" if ch.channel_type.value == "free" else "👑"
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{emoji} {ch.channel_name or 'Sin nombre'}",
                    callback_data=BroadcastChannelCallback(channel_id=ch.channel_id).pack(),
                )
            ]
        )

    buttons.append([InlineKeyboardButton(text="🔙 Cancelar", callback_data="admin_gamification")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text(
        """🎩 <b>Lucien:</b>

<i>¿A qué dominio desea enviar su mensaje?</i>

📋 Seleccione el canal:""",
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    await state.set_state(BroadcastStates.selecting_channel)
    await callback.answer()


@router.callback_query(BroadcastStates.selecting_channel, BroadcastChannelCallback.filter())
async def select_channel_for_broadcast(
    callback: CallbackQuery, state: FSMContext, callback_data: BroadcastChannelCallback
):
    """Canal seleccionado, pedir texto"""
    channel_id = callback_data.channel_id

    with get_service(ChannelService) as channel_service:
        channel = channel_service.get_channel_by_id(channel_id)

    if not channel:
        await callback.answer("Canal no encontrado", show_alert=True)
        return

    await state.update_data(channel_id=channel_id, channel_name=channel.channel_name)

    try:
        await callback.message.edit_text(
            f"""🎩 <b>Lucien:</b>

<i>Preparando mensaje para <b>{channel.channel_name}</b>...</i>

📋 <b>Paso 1 de 7:</b> Texto del mensaje

Envíe el texto que desea publicar. Puede usar formato HTML:
• &lt;b&gt;negrita&lt;/b&gt;
• &lt;i&gt;cursiva&lt;/i&gt;
• &lt;code&gt;código&lt;/code&gt;""",
            reply_markup=broadcast_back_keyboard("waiting_text"),
            parse_mode="HTML",
        )
    except Exception as e:
        if "message is not modified" in str(e).lower():
            pass  # Ignorar error de mensaje no modificado
        else:
            raise
    await state.set_state(BroadcastStates.waiting_text)
    await callback.answer()


@router.message(BroadcastStates.waiting_text)
async def process_broadcast_text(message: Message, state: FSMContext):
    """Procesa el texto del mensaje"""
    text = message.text or message.caption or ""

    await state.update_data(text=text)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📎 Adjuntar foto/archivo", callback_data="attach_yes")],
            [InlineKeyboardButton(text="⏭️ Omitir adjunto", callback_data="attach_no")],
            [InlineKeyboardButton(text="🔙 Volver al texto", callback_data="broadcast_back_text")],
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_gamification")],
        ]
    )

    await message.answer(
        """🎩 <b>Lucien:</b>

<i>Texto recibido. ¿Desea incluir algún adjunto?</i>

📋 <b>Paso 2 de 7:</b> Adjunto

Puede agregar una foto, video o archivo al mensaje.""",
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    await state.set_state(BroadcastStates.waiting_attachment_decision)


@router.callback_query(BroadcastStates.waiting_attachment_decision, F.data == "broadcast_back_text")
async def back_to_text(callback: CallbackQuery, state: FSMContext):
    """Regresar a ingresar texto"""
    data = await state.get_data()
    try:
        await callback.message.edit_text(
            f"""🎩 <b>Lucien:</b>

<i>Preparando mensaje para <b>{data.get("channel_name", "Desconocido")}</b>...</i>

📋 <b>Paso 1 de 7:</b> Texto del mensaje

Envíe el texto que desea publicar. Puede usar formato HTML:
• &lt;b&gt;negrita&lt;/b&gt;
• &lt;i&gt;cursiva&lt;/i&gt;
• &lt;code&gt;código&lt;/code&gt;""",
            reply_markup=broadcast_back_keyboard("waiting_text"),
            parse_mode="HTML",
        )
    except Exception as e:
        if "message is not modified" in str(e).lower():
            pass
        else:
            raise
    await state.set_state(BroadcastStates.waiting_text)
    await callback.answer()


@router.callback_query(BroadcastStates.waiting_attachment_decision, F.data == "attach_yes")
async def want_attachment(callback: CallbackQuery, state: FSMContext):
    """Usuario quiere adjuntar algo"""
    try:
        await callback.message.edit_text(
            """🎩 <b>Lucien:</b>

<i>Envíe la foto o archivo que desea adjuntar...</i>

📋 <b>Paso 2 de 7:</b> Adjunto

Puede enviar:
• Foto
• Video
• Documento/Archivo""",
            reply_markup=broadcast_back_keyboard("waiting_attachment"),
            parse_mode="HTML",
        )
    except Exception as e:
        if "message is not modified" in str(e).lower():
            pass
        else:
            raise
    await state.set_state(BroadcastStates.waiting_attachment)
    await callback.answer()


@router.callback_query(BroadcastStates.waiting_attachment_decision, F.data == "attach_no")
async def skip_attachment(callback: CallbackQuery, state: FSMContext):
    """Usuario omite adjunto"""
    await state.update_data(has_attachment=False, attachment_type=None, attachment_file_id=None)
    await ask_for_reactions(callback, state)


@router.message(BroadcastStates.waiting_attachment)
async def process_attachment(message: Message, state: FSMContext):
    """Procesa el archivo adjunto"""
    file_id = None
    attachment_type = None

    if message.photo:
        file_id = message.photo[-1].file_id  # Mejor calidad
        attachment_type = "photo"
    elif message.video:
        file_id = message.video.file_id
        attachment_type = "video"
    elif message.document:
        file_id = message.document.file_id
        attachment_type = "document"
    elif message.animation:
        file_id = message.animation.file_id
        attachment_type = "animation"
    else:
        await message.answer(
            "🎩 <b>Lucien:</b>\n\n"
            "<i>No pude reconocer el tipo de archivo.\n"
            "Por favor envíe una foto, video o documento...</i>",
            reply_markup=cancel_keyboard(),
            parse_mode="HTML",
        )
        return

    await state.update_data(
        has_attachment=True, attachment_type=attachment_type, attachment_file_id=file_id
    )

    await ask_for_reactions(message, state)


async def ask_for_reactions(target, state: FSMContext):
    """Pregunta si quiere agregar reacciones"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💋 Mantener reacciones (predeterminado)", callback_data="reaction_yes")],
            [InlineKeyboardButton(text="⏭️ Deshabilitar reacciones", callback_data="reaction_no")],
            [InlineKeyboardButton(text="🔙 Volver", callback_data="broadcast_back_attachment")],
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_gamification")],
        ]
    )

    text = """🎩 <b>Lucien:</b>

<i>Las reacciones se incluyen por defecto (a menos que las deshabilite).</i>

📋 <b>Paso 3 de 7:</b> Reacciones

Los usuarios podrán reaccionar y recibir besitos. (Predeterminado: todos los emojis activos preseleccionados)."""

    try:
        if isinstance(target, CallbackQuery):
            await target.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        else:
            await target.answer(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        if "message is not modified" in str(e).lower():
            pass
        else:
            raise

    await state.set_state(BroadcastStates.waiting_reaction_decision)


@router.callback_query(
    BroadcastStates.waiting_reaction_decision, F.data == "broadcast_back_attachment"
)
async def back_to_attachment_decision(callback: CallbackQuery, state: FSMContext):
    """Regresar a decisión de adjunto"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📎 Adjuntar foto/archivo", callback_data="attach_yes")],
            [InlineKeyboardButton(text="⏭️ Omitir adjunto", callback_data="attach_no")],
            [InlineKeyboardButton(text="🔙 Volver al texto", callback_data="broadcast_back_text")],
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_gamification")],
        ]
    )

    try:
        await callback.message.edit_text(
            """🎩 <b>Lucien:</b>

<i>¿Desea incluir algún adjunto?</i>

📋 <b>Paso 2 de 7:</b> Adjunto

Puede agregar una foto, video o archivo al mensaje.""",
            reply_markup=keyboard,
            parse_mode="HTML",
        )
    except Exception as e:
        if "message is not modified" in str(e).lower():
            pass
        else:
            raise
    await state.set_state(BroadcastStates.waiting_attachment_decision)
    await callback.answer()


@router.callback_query(BroadcastStates.waiting_reaction_decision, F.data == "reaction_yes")
async def want_reactions(callback: CallbackQuery, state: FSMContext):
    """Usuario quiere reacciones - mostrar emojis disponibles (default predeterminado: todos los activos)"""
    with get_service(BroadcastService) as broadcast_service:
        emojis = broadcast_service.get_all_emojis(active_only=True)

    if not emojis:
        try:
            await callback.message.edit_text(
                """🎩 <b>Lucien:</b>

<i>No hay emojis configurados para reacciones...</i>

👉 <i>Configure emojis primero desde "Configurar besitos".</i>""",
                reply_markup=back_keyboard("admin_gamification"),
                parse_mode="HTML",
            )
        except Exception as e:
            if "message is not modified" in str(e).lower():
                pass
            else:
                raise
        await state.clear()
        await callback.answer()
        return

    # Default predeterminado: preseleccionar TODOS los emojis activos (a menos que admin deshabilite explícitamente)
    preselected = [emoji.id for emoji in emojis]
    await state.update_data(selected_emojis=preselected)

    await show_reaction_selection(callback, state)
    await callback.answer()


async def show_reaction_selection(callback: CallbackQuery, state: FSMContext):
    """Muestra la selección de emojis"""
    with get_service(BroadcastService) as broadcast_service:
        emojis = broadcast_service.get_all_emojis(active_only=True)
    data = await state.get_data()
    selected = data.get("selected_emojis", [])

    buttons = []
    for emoji in emojis:
        is_selected = emoji.id in selected
        check = "✅ " if is_selected else "⬜ "
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{check}{emoji.emoji} = {emoji.besito_value} besitos",
                    callback_data=ToggleReactionCallback(emoji_id=emoji.id).pack(),
                )
            ]
        )

    buttons.append([InlineKeyboardButton(text="✅ Continuar", callback_data="reactions_selected")])
    buttons.append([InlineKeyboardButton(text="⏭️ Deshabilitar reacciones", callback_data="reaction_no")])
    buttons.append(
        [InlineKeyboardButton(text="🔙 Volver", callback_data="broadcast_back_reactions")]
    )
    buttons.append([InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_gamification")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    try:
        await callback.message.edit_text(
            """🎩 <b>Lucien:</b>

<i>Seleccione los emojis para este mensaje...</i>

📋 <b>Paso 3 de 7:</b> Reacciones

Toque para seleccionar/deseleccionar:""",
            reply_markup=keyboard,
            parse_mode="HTML",
        )
    except Exception as e:
        if "message is not modified" in str(e).lower():
            pass
        else:
            raise
    await state.set_state(BroadcastStates.selecting_reactions)


@router.callback_query(BroadcastStates.selecting_reactions, F.data == "broadcast_back_reactions")
async def back_from_reaction_selection(callback: CallbackQuery, state: FSMContext):
    """Regresar desde selección de reacciones"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💋 Mantener reacciones (predeterminado)", callback_data="reaction_yes")],
            [InlineKeyboardButton(text="⏭️ Deshabilitar reacciones", callback_data="reaction_no")],
            [InlineKeyboardButton(text="🔙 Volver", callback_data="broadcast_back_attachment")],
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_gamification")],
        ]
    )

    try:
        await callback.message.edit_text(
            """🎩 <b>Lucien:</b>

<i>¿Desea incluir botones de reacción?</i>

📋 <b>Paso 3 de 7:</b> Reacciones

Los usuarios podrán reaccionar y recibir besitos.""",
            reply_markup=keyboard,
            parse_mode="HTML",
        )
    except Exception as e:
        if "message is not modified" in str(e).lower():
            pass
        else:
            raise
    await state.set_state(BroadcastStates.waiting_reaction_decision)
    await callback.answer()


@router.callback_query(BroadcastStates.selecting_reactions, ToggleReactionCallback.filter())
async def toggle_reaction_selection(
    callback: CallbackQuery, state: FSMContext, callback_data: ToggleReactionCallback
):
    """Toggle selección de emoji"""
    emoji_id = callback_data.emoji_id
    data = await state.get_data()
    selected = data.get("selected_emojis", [])

    if emoji_id in selected:
        selected.remove(emoji_id)
    else:
        selected.append(emoji_id)

    await state.update_data(selected_emojis=selected)
    await show_reaction_selection(callback, state)
    await callback.answer()


@router.callback_query(BroadcastStates.selecting_reactions, F.data == "reactions_selected")
async def reactions_selected(callback: CallbackQuery, state: FSMContext):
    """Emojis seleccionados, continuar"""
    data = await state.get_data()
    selected = data.get("selected_emojis", [])

    if not selected:
        await callback.answer("Seleccione al menos un emoji", show_alert=True)
        return

    await ask_for_extra_button(callback, state)
    await callback.answer()


@router.callback_query(BroadcastStates.waiting_reaction_decision, F.data == "reaction_no")
async def skip_reactions(callback: CallbackQuery, state: FSMContext):
    """Admin deshabilita reacciones explícitamente (opt-out del default predeterminado)"""
    await state.update_data(selected_emojis=[], has_reactions=False)
    await ask_for_extra_button(callback, state)
    await callback.answer()


async def ask_for_extra_button(target, state: FSMContext):
    """Pregunta si quiere agregar botón extra de enlace (single choice, default ninguno)."""
    with get_service(BroadcastService) as broadcast_service:
        buttons = broadcast_service.get_all_buttons(active_only=True)

    if not buttons:
        # Catálogo vacío: auto-skip (document gap: admin UI para crear botones está pendiente)
        await state.update_data(extra_button_id=None)
        await ask_for_protection(target, state)
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔗 Agregar botón de enlace", callback_data="extra_button_yes"
                )
            ],
            [InlineKeyboardButton(text="⏭️ Sin botón extra", callback_data="extra_button_no")],
            [InlineKeyboardButton(text="🔙 Volver", callback_data="broadcast_back_extra")],
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_gamification")],
        ]
    )

    text = """🎩 <b>Lucien:</b>

<i>¿Desea adjuntar un botón de enlace extra?</i>

📋 <b>Paso 4 de 7:</b> Botón extra

El botón aparecerá debajo de las reacciones (si las hay)."""

    try:
        if isinstance(target, CallbackQuery):
            await target.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        else:
            await target.answer(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        if "message is not modified" in str(e).lower():
            pass
        else:
            raise

    await state.set_state(BroadcastStates.waiting_extra_button_decision)


@router.callback_query(BroadcastStates.waiting_extra_button_decision, F.data == "extra_button_yes")
async def want_extra_button(callback: CallbackQuery, state: FSMContext):
    """Usuario quiere elegir botón extra - mostrar selección single choice."""
    await show_extra_button_selection(callback, state)
    await callback.answer()


@router.callback_query(BroadcastStates.waiting_extra_button_decision, F.data == "extra_button_no")
async def skip_extra_button(callback: CallbackQuery, state: FSMContext):
    """Usuario omite botón extra."""
    await state.update_data(extra_button_id=None)
    await ask_for_protection(callback, state)
    await callback.answer()


async def show_extra_button_selection(callback: CallbackQuery, state: FSMContext):
    """Muestra lista de botones activos para selección única (o 'ninguno')."""
    with get_service(BroadcastService) as broadcast_service:
        buttons = broadcast_service.get_all_buttons(active_only=True)
    data = await state.get_data()
    selected_id = data.get("extra_button_id")  # None o int

    keyboard = build_extra_button_selection_keyboard(buttons, selected_id)

    try:
        await callback.message.edit_text(
            """🎩 <b>Lucien:</b>

<i>Seleccione un botón de enlace (solo uno)...</i>

📋 <b>Paso 4 de 7:</b> Botón extra

Toque para seleccionar; "Ninguno" para omitir.""",
            reply_markup=keyboard,
            parse_mode="HTML",
        )
    except Exception as e:
        if "message is not modified" in str(e).lower():
            pass
        else:
            raise
    await state.set_state(BroadcastStates.selecting_extra_button)


@router.callback_query(BroadcastStates.selecting_extra_button, ToggleExtraButtonCallback.filter())
async def toggle_extra_button_selection(
    callback: CallbackQuery, state: FSMContext, callback_data: ToggleExtraButtonCallback
):
    """Selección single-choice: reemplaza cualquier elección previa."""
    button_id = callback_data.button_id
    if button_id == 0:
        await state.update_data(extra_button_id=None)
    else:
        await state.update_data(extra_button_id=button_id)
    await show_extra_button_selection(callback, state)
    await callback.answer()


@router.callback_query(BroadcastStates.selecting_extra_button, F.data == "extra_button_continue")
async def extra_button_selected(callback: CallbackQuery, state: FSMContext):
    """Continúa después de elegir (o ninguno)."""
    await ask_for_protection(callback, state)
    await callback.answer()


@router.callback_query(
    BroadcastStates.waiting_extra_button_decision, F.data == "broadcast_back_extra"
)
async def back_from_extra_decision(callback: CallbackQuery, state: FSMContext):
    """Volver desde decisión de botón extra a reacciones."""
    data = await state.get_data()
    has_reactions = len(data.get("selected_emojis", [])) > 0

    if has_reactions:
        await state.update_data(selected_emojis=[])  # mirror pattern
        await show_reaction_selection(callback, state)
    else:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="💋 Sí, agregar reacciones", callback_data="reaction_yes"
                    )
                ],
                [InlineKeyboardButton(text="⏭️ No, sin reacciones", callback_data="reaction_no")],
                [InlineKeyboardButton(text="🔙 Volver", callback_data="broadcast_back_attachment")],
                [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_gamification")],
            ]
        )
        try:
            await callback.message.edit_text(
                """🎩 <b>Lucien:</b>

<i>¿Desea incluir botones de reacción?</i>

📋 <b>Paso 3 de 7:</b> Reacciones

Los usuarios podrán reaccionar y recibir besitos.""",
                reply_markup=keyboard,
                parse_mode="HTML",
            )
        except Exception as e:
            if "message is not modified" in str(e).lower():
                pass
            else:
                raise
        await state.set_state(BroadcastStates.waiting_reaction_decision)
    await callback.answer()


@router.callback_query(BroadcastStates.selecting_extra_button, F.data == "broadcast_back_extra")
async def back_from_extra_selection(callback: CallbackQuery, state: FSMContext):
    """Volver desde selección de botón a la decisión sí/no."""
    await ask_for_extra_button(callback, state)
    await callback.answer()


async def ask_for_protection(target, state: FSMContext):
    """Pregunta por protección del mensaje"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔒 Proteger mensaje",
                    callback_data=BroadcastProtectCallback(action="yes").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⏭️ Sin protección",
                    callback_data=BroadcastProtectCallback(action="no").pack(),
                )
            ],
            [InlineKeyboardButton(text="🔙 Volver", callback_data="broadcast_back_protection")],
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_gamification")],
        ]
    )

    text = """🎩 <b>Lucien:</b>

<i>¿Desea proteger el mensaje?</i>

📋 <b>Paso 5 de 7:</b> Protección

🔒 <b>Proteger:</b> Impide copiar, reenviar y descargar el contenido.

⚠️ <b>Nota:</b> La protección solo funciona en canales con contenido protegido habilitado."""

    try:
        if isinstance(target, CallbackQuery):
            await target.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        else:
            await target.answer(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        if "message is not modified" in str(e).lower():
            pass
        else:
            raise

    await state.set_state(BroadcastStates.waiting_protection_decision)


@router.callback_query(
    BroadcastStates.waiting_protection_decision, BroadcastProtectCallback.filter()
)
async def set_protection(
    callback: CallbackQuery, state: FSMContext, callback_data: BroadcastProtectCallback
):
    """Establece protección y muestra preview"""
    is_protected = callback_data.action == "yes"
    await state.update_data(is_protected=is_protected)

    await show_broadcast_preview(callback, state)
    await callback.answer()


@router.callback_query(
    BroadcastStates.waiting_protection_decision, F.data == "broadcast_back_protection"
)
async def back_from_protection(callback: CallbackQuery, state: FSMContext):
    """Regresar desde protección: si hay botones extra activos → selección extra; si no, reacciones."""
    data = await state.get_data()
    has_reactions = len(data.get("selected_emojis", [])) > 0

    with get_service(BroadcastService) as broadcast_service:
        has_extra_buttons = len(broadcast_service.get_all_buttons(active_only=True)) > 0

    if has_extra_buttons:
        # Volver a selección de botón extra (muestra elección actual o "ninguno")
        await show_extra_button_selection(callback, state)
    elif has_reactions:
        # Si tiene reacciones, volver a selección
        await state.update_data(selected_emojis=[])
        await show_reaction_selection(callback, state)
    else:
        # Si no tiene reacciones, volver a decisión de reacciones
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="💋 Sí, agregar reacciones", callback_data="reaction_yes"
                    )
                ],
                [InlineKeyboardButton(text="⏭️ No, sin reacciones", callback_data="reaction_no")],
                [InlineKeyboardButton(text="🔙 Volver", callback_data="broadcast_back_attachment")],
                [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_gamification")],
            ]
        )

        try:
            await callback.message.edit_text(
                """🎩 <b>Lucien:</b>

<i>¿Desea incluir botones de reacción?</i>

📋 <b>Paso 3 de 7:</b> Reacciones

Los usuarios podrán reaccionar y recibir besitos.""",
                reply_markup=keyboard,
                parse_mode="HTML",
            )
        except Exception as e:
            if "message is not modified" in str(e).lower():
                pass
            else:
                raise
        await state.set_state(BroadcastStates.waiting_reaction_decision)
    await callback.answer()


async def show_broadcast_preview(callback: CallbackQuery, state: FSMContext):
    """Muestra preview del mensaje antes de enviar"""
    data = await state.get_data()

    # Resolver info de botón extra (side-effect mínimo, solo lectura)
    extra_button_id = data.get("extra_button_id")
    extra_info = "❌"
    if extra_button_id:
        with get_service(BroadcastService) as broadcast_service:
            btn = broadcast_service.get_broadcast_button(extra_button_id)
            if btn:
                extra_info = f"{btn.label} ({btn.url})"

    info_text = build_broadcast_preview_text(data, extra_info)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Confirmar", callback_data="confirm_broadcast")],
            [InlineKeyboardButton(text="🔙 Volver", callback_data="broadcast_back_preview")],
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_gamification")],
        ]
    )

    try:
        await callback.message.edit_text(info_text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        if "message is not modified" in str(e).lower():
            pass
        else:
            raise
    await state.set_state(BroadcastStates.confirming)


@router.callback_query(BroadcastStates.confirming, F.data == "broadcast_back_preview")
async def back_from_preview(callback: CallbackQuery, state: FSMContext):
    """Regresar desde preview a protección"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔒 Proteger mensaje",
                    callback_data=BroadcastProtectCallback(action="yes").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⏭️ Sin protección",
                    callback_data=BroadcastProtectCallback(action="no").pack(),
                )
            ],
            [InlineKeyboardButton(text="🔙 Volver", callback_data="broadcast_back_protection")],
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_gamification")],
        ]
    )

    try:
        await callback.message.edit_text(
            """🎩 <b>Lucien:</b>

<i>¿Desea proteger el mensaje?</i>

📋 <b>Paso 5 de 7:</b> Protección

🔒 <b>Proteger:</b> Impide copiar, reenviar y descargar el contenido.

⚠️ <b>Nota:</b> La protección solo funciona en canales con contenido protegido habilitado.""",
            reply_markup=keyboard,
            parse_mode="HTML",
        )
    except Exception as e:
        if "message is not modified" in str(e).lower():
            pass
        else:
            raise
    await state.set_state(BroadcastStates.waiting_protection_decision)
    await callback.answer()


@router.callback_query(BroadcastStates.confirming, F.data == "confirm_broadcast")
async def confirm_and_send_broadcast(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Envía el mensaje al canal"""
    data = await state.get_data()

    channel_id = data.get("channel_id")
    text = data.get("text", "")
    has_attachment = data.get("has_attachment", False)
    attachment_type = data.get("attachment_type")
    attachment_file_id = data.get("attachment_file_id")
    selected_emojis = data.get("selected_emojis", [])
    is_protected = data.get("is_protected", False)

    with get_service(BroadcastService) as broadcast_service:
        extra_button_id = data.get("extra_button_id")
        broadcast = persist_broadcast_from_state(data, callback.from_user.id, broadcast_service)

        extra_button = None
        if extra_button_id:
            extra_button = broadcast_service.get_broadcast_button(extra_button_id)

        reaction_markup = build_broadcast_send_markup(
            broadcast.id,
            selected_emojis,
            extra_button,
            broadcast_service.get_reaction_emoji,
        )

        # Sin botones de reacción en el envío inicial: se adjuntan tras fijar message_id
        send_markup = None
        protect_content = is_protected

        try:
            if has_attachment and attachment_file_id:
                if attachment_type == "photo":
                    sent_message = await bot.send_photo(
                        chat_id=channel_id,
                        photo=attachment_file_id,
                        caption=text,
                        reply_markup=send_markup,
                        protect_content=protect_content,
                    )
                elif attachment_type == "video":
                    sent_message = await bot.send_video(
                        chat_id=channel_id,
                        video=attachment_file_id,
                        caption=text,
                        reply_markup=send_markup,
                        protect_content=protect_content,
                    )
                elif attachment_type == "document":
                    sent_message = await bot.send_document(
                        chat_id=channel_id,
                        document=attachment_file_id,
                        caption=text,
                        reply_markup=send_markup,
                        protect_content=protect_content,
                    )
                elif attachment_type == "animation":
                    sent_message = await bot.send_animation(
                        chat_id=channel_id,
                        animation=attachment_file_id,
                        caption=text,
                        reply_markup=send_markup,
                        protect_content=protect_content,
                    )
                else:
                    sent_message = await bot.send_message(
                        chat_id=channel_id, text=text, reply_markup=send_markup
                    )
            else:
                sent_message = await bot.send_message(
                    chat_id=channel_id,
                    text=text,
                    reply_markup=send_markup,
                    protect_content=protect_content,
                )
        except Exception as e:
            broadcast_service.delete_broadcast(broadcast.id)
            logger.error(
                f"broadcast_handlers | confirm_and_send_broadcast | send_failed | broadcast_id={broadcast.id} | error={e}"
            )
            await callback.answer(
                "No pudimos enviar el mensaje al canal. Inténtelo de nuevo.", show_alert=True
            )
            return

        if not broadcast_service.update_broadcast_message_id(broadcast.id, sent_message.message_id):
            logger.error(
                f"broadcast_handlers | confirm_and_send_broadcast | message_id_update_failed | broadcast_id={broadcast.id}"
            )
            try:
                await bot.delete_message(chat_id=channel_id, message_id=sent_message.message_id)
            except Exception as cleanup_err:
                logger.warning(
                    f"broadcast_handlers | confirm_and_send_broadcast | cleanup_failed | broadcast_id={broadcast.id} | error={cleanup_err}"
                )
            broadcast_service.delete_broadcast(broadcast.id)
            await callback.answer(
                "El mensaje se envió pero no pudimos activar las reacciones. Inténtelo de nuevo.",
                show_alert=True,
            )
            return

        if reaction_markup:
            try:
                await bot.edit_message_reply_markup(
                    chat_id=channel_id,
                    message_id=sent_message.message_id,
                    reply_markup=reaction_markup,
                )
            except Exception as e:
                if "message is not modified" in str(e).lower():
                    pass
                else:
                    logger.error(
                        f"broadcast_handlers | attach_reaction_markup | broadcast_id={broadcast.id} | error={e}"
                    )
                    try:
                        await bot.delete_message(
                            chat_id=channel_id, message_id=sent_message.message_id
                        )
                    except Exception as cleanup_err:
                        logger.warning(
                            f"broadcast_handlers | attach_reaction_markup | cleanup_failed | broadcast_id={broadcast.id} | error={cleanup_err}"
                        )
                    broadcast_service.delete_broadcast(broadcast.id)
                    await callback.answer(
                        "El mensaje se envió pero no pudimos activar las reacciones. Inténtelo de nuevo.",
                        show_alert=True,
                    )
                    return

        try:
            await callback.message.edit_text(
                f"""🎩 <b>Lucien:</b>

<i>El mensaje ha sido transmitido a los dominios de Diana...</i>

✅ <b>Broadcast enviado exitosamente.</b>

📊 <b>Detalles:</b>
   • Canal: {data.get("channel_name")}
   • Mensaje ID: <code>{sent_message.message_id}</code>
   • Reacciones: {"Sí" if selected_emojis else "No"}

<i>Los visitantes podrán interactuar con él.</i>""",
                reply_markup=back_keyboard("admin_gamification"),
                parse_mode="HTML",
            )
        except Exception as e:
            if "message is not modified" in str(e).lower():
                pass
            else:
                raise

        logger.info(f"Broadcast enviado: channel={channel_id}, message={sent_message.message_id}")

    # Legacy outer try/except/finally for send error UI removed in F4 unification (with handles close on all paths;
    # errors will be caught by global error handler or bubble; main success path + close preserved).
    # (Custom error edit for send fail is now handled by outer if any.)

    await state.clear()
    await callback.answer()
