"""
Handlers VIP para Usuarios - Lucien Bot

Handlers exclusivos para suscriptores VIP:
- Menú del círculo exclusivo
- Mensajes anónimos a Diana
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from services.vip_service import VIPService
from services.anonymous_message_service import AnonymousMessageService
from keyboards.inline_keyboards import back_keyboard, main_menu_keyboard
from utils.lucien_voice import LucienVoice
import logging

logger = logging.getLogger(__name__)
router = Router()


# Estados para FSM
class AnonymousMessageStates(StatesGroup):
    waiting_message = State()
    confirming_send = State()


def vip_area_keyboard() -> InlineKeyboardMarkup:
    """Menú del círculo exclusivo VIP"""
    buttons = [
        [InlineKeyboardButton(
            text="💌 Enviar mensaje a Diana",
            callback_data="send_anonymous_message"
        )],
        [InlineKeyboardButton(
            text="🔙 Volver al menú principal",
            callback_data="back_to_main"
        )]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def anonymous_message_confirm_keyboard() -> InlineKeyboardMarkup:
    """Teclado para confirmar envío de mensaje anónimo"""
    buttons = [
        [
            InlineKeyboardButton(text="✅ Enviar", callback_data="confirm_anonymous_send"),
            InlineKeyboardButton(text="❌ Cancelar", callback_data="cancel_anonymous")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ==================== MENÚ DEL CÍRCULO EXCLUSIVO ====================

@router.callback_query(F.data == "vip_area")
async def vip_area_menu(callback: CallbackQuery):
    """Muestra el menú exclusivo del círculo VIP"""
    user = callback.from_user

    # Verificar que sigue siendo VIP
    vip_service = VIPService()
    try:
        is_vip = vip_service.is_user_vip(user.id)
        if not is_vip:
            await callback.message.edit_text(
                f"🎩 <b>Lucien:</b>\n\n"
                f"<i>El círculo exclusivo es solo para los privilegiados...</i>\n\n"
                f"Su suscripción VIP no está activa.",
                reply_markup=main_menu_keyboard(is_vip=False),
                parse_mode="HTML"
            )
            await callback.answer()
            return

        await callback.message.edit_text(
            f"🎩 <b>Lucien:</b>\n\n"
            f"<i>Bienvenido al círculo exclusivo, donde los privilegiados "
            f"tienen acceso a experiencias únicas...</i>\n\n"
            f"💎 <b>El Círculo Exclusivo de Diana</b>\n\n"
            f"Aquí encontrará funciones reservadas solo para quienes "
            f"han sido admitidos en la intimidad de Diana.",
            reply_markup=vip_area_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer()
    finally:
        vip_service.close()


# ==================== MENSAJES ANÓNIMOS ====================

@router.callback_query(F.data == "send_anonymous_message")
async def start_anonymous_message(callback: CallbackQuery, state: FSMContext):
    """Inicia el flujo de envío de mensaje anónimo"""
    user = callback.from_user

    # Verificar que sigue siendo VIP
    vip_service = VIPService()
    try:
        is_vip = vip_service.is_user_vip(user.id)
        if not is_vip:
            await callback.message.edit_text(
                f"🎩 <b>Lucien:</b>\n\n"
                f"<i>Esta función es exclusiva del círculo...</i>\n\n"
                f"Su suscripción VIP no está activa.",
                reply_markup=main_menu_keyboard(is_vip=False),
                parse_mode="HTML"
            )
            await callback.answer()
            return

        await callback.message.edit_text(
            f"🎩 <b>Lucien:</b>\n\n"
            f"<i>¿Desea enviar un susurro anónimo a Diana?</i>\n\n"
            f"💌 <b>Mensaje a Diana</b>\n\n"
            f"Escriba su mensaje con total libertad. Diana lo recibirá "
            f"sin saber quién lo envió, a menos que sea necesario revelarlo "
            f"por alguna cuestión delicada.\n\n"
            f"<i>Escriba su mensaje a continuación...</i>",
            reply_markup=back_keyboard("vip_area"),
            parse_mode="HTML"
        )
        await state.set_state(AnonymousMessageStates.waiting_message)
        await callback.answer()
    finally:
        vip_service.close()


@router.message(AnonymousMessageStates.waiting_message)
async def process_anonymous_message(message: Message, state: FSMContext):
    """Procesa el mensaje anónimo ingresado"""
    content = message.text.strip()

    if len(content) < 3:
        await message.answer(
            f"🎩 <b>Lucien:</b>\n\n"
            f"<i>El mensaje es demasiado breve...</i>\n\n"
            f"Por favor, escriba al menos unas palabras para Diana.",
            reply_markup=back_keyboard("vip_area"),
            parse_mode="HTML"
        )
        return

    if len(content) > 4000:
        await message.answer(
            f"🎩 <b>Lucien:</b>\n\n"
            f"<i>El mensaje excede el límite permitido...</i>\n\n"
            f"Por favor, sea más conciso. Máximo 4000 caracteres.",
            reply_markup=back_keyboard("vip_area"),
            parse_mode="HTML"
        )
        return

    # Guardar en estado
    await state.update_data(message_content=content)

    # Mostrar preview para confirmar
    preview = content[:200] + "..." if len(content) > 200 else content

    await message.answer(
        f"🎩 <b>Lucien:</b>\n\n"
        f"<i>Permítame mostrarle lo que será enviado...</i>\n\n"
        f"💌 <b>Su mensaje anónimo:</b>\n"
        f"<blockquote>{preview}</blockquote>\n\n"
        f"<i>¿Desea enviar este mensaje a Diana?</i>",
        reply_markup=anonymous_message_confirm_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(AnonymousMessageStates.confirming_send)


@router.callback_query(AnonymousMessageStates.confirming_send, F.data == "confirm_anonymous_send")
async def confirm_anonymous_send(callback: CallbackQuery, state: FSMContext):
    """Confirma y envía el mensaje anónimo"""
    user = callback.from_user
    data = await state.get_data()
    content = data.get("message_content")

    if not content:
        await callback.message.edit_text(
            f"🎩 <b>Lucien:</b>\n\n"
            f"<i>Ha ocurrido un error...</i>\n\n"
            f"No se encontró el contenido del mensaje.",
            reply_markup=back_keyboard("vip_area"),
            parse_mode="HTML"
        )
        await state.clear()
        await callback.answer()
        return

    # Verificar que sigue siendo VIP
    vip_service = VIPService()
    try:
        is_vip = vip_service.is_user_vip(user.id)
        if not is_vip:
            await callback.message.edit_text(
                f"🎩 <b>Lucien:</b>\n\n"
                f"<i>Su suscripción VIP ya no está activa...</i>\n\n"
                f"El mensaje no pudo ser enviado.",
                reply_markup=main_menu_keyboard(is_vip=False),
                parse_mode="HTML"
            )
            await state.clear()
            await callback.answer()
            return

        # Enviar mensaje anónimo
        anon_service = AnonymousMessageService()
        try:
            message = anon_service.send_message(user.id, content)

            logger.info(f"Mensaje anónimo enviado: id={message.id}, sender={user.id}")

            await callback.message.edit_text(
                f"🎩 <b>Lucien:</b>\n\n"
                f"<i>Su susurro ha sido enviado a Diana...</i>\n\n"
                f"✅ <b>Mensaje anónimo enviado</b>\n\n"
                f"Diana lo recibirá pronto. Si desea responder, "
                f"lo hará a través de este mismo canal.\n\n"
                f"<i>Gracias por confiar en el círculo exclusivo.</i>",
                reply_markup=back_keyboard("vip_area"),
                parse_mode="HTML"
            )
        finally:
            anon_service.close()
    finally:
        vip_service.close()

    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "cancel_anonymous")
async def cancel_anonymous_message(callback: CallbackQuery, state: FSMContext):
    """Cancela el envío del mensaje anónimo"""
    await state.clear()
    await callback.message.edit_text(
        f"🎩 <b>Lucien:</b>\n\n"
        f"<i>El mensaje ha sido descartado...</i>\n\n"
        f"Diana no recibirá nada. Puede escribir otro mensaje cuando lo desee.",
        reply_markup=vip_area_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer("Mensaje cancelado")
