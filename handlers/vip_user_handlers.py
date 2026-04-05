"""
Handlers VIP para Usuarios - Lucien Bot

Handlers exclusivos para suscriptores VIP:
- Menú de El Diván
- Mensajes anónimos a Diana
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from services.vip_service import VIPService
from services.anonymous_message_service import AnonymousMessageService
from services.besito_service import BesitoService
from models.models import TransactionSource
from keyboards.inline_keyboards import back_keyboard, main_menu_keyboard
from utils.lucien_voice import LucienVoice
import logging

logger = logging.getLogger(__name__)
router = Router()

# Costo en besitos para mensajes anónimos VIP
ANONYMOUS_MESSAGE_COST = 50


# Estados para FSM
class AnonymousMessageStates(StatesGroup):
    waiting_message = State()
    confirming_send = State()


def vip_area_keyboard() -> InlineKeyboardMarkup:
    """Menú de El Diván VIP"""
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


# ==================== MENÚ DE EL DIVÁN ====================

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
                f"<i>El Diván es solo para los privilegiados...</i>\n\n"
                f"Su suscripción VIP no está activa.",
                reply_markup=main_menu_keyboard(is_vip=False),
                parse_mode="HTML"
            )
            await callback.answer()
            return

        await callback.message.edit_text(
            f"🎩 <b>Lucien:</b>\n\n"
            f"<i>Bienvenido a El Diván, donde los privilegiados "
            f"tienen acceso a experiencias únicas...</i>\n\n"
            f"💎 <b>El Diván</b>\n\n"
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
            f"Este es uno de los pocos espacios donde puede dirigirse a Diana… sin ser visto.\n\n"
            f"Su mensaje será completamente anónimo.\n"
            f"Sin nombre. Sin rastro.\n\n"
            f"Algo que debe saber:\n"
            f"Diana <b>no</b> responde a todo.\n"
            f"Solo a lo que… le interesa.",
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
        f"Antes de enviarlo… léalo de nuevo.\n\n"
        f"Esto es lo que Diana recibirá:\n\n"
        f"<blockquote>{preview}</blockquote>\n\n"
        f"💋 <b>Costo: {ANONYMOUS_MESSAGE_COST} besitos</b>\n\n"
        f"¿Está seguro de que esto… merece su atención?",
        reply_markup=anonymous_message_confirm_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(AnonymousMessageStates.confirming_send)


@router.callback_query(AnonymousMessageStates.confirming_send, F.data == "confirm_anonymous_send")
async def confirm_anonymous_send(callback: CallbackQuery, state: FSMContext):
    """Confirma y envía el mensaje anónimo, debitando besitos primero"""
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
    besito_service = BesitoService()
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

        # Verificar saldo suficiente
        has_balance = besito_service.has_sufficient_balance(user.id, ANONYMOUS_MESSAGE_COST)
        if not has_balance:
            current_balance = besito_service.get_balance(user.id)
            await callback.message.edit_text(
                f"🎩 <b>Lucien:</b>\n\n"
                f"<i>Los mensajes anónimos tienen un precio...</i>\n\n"
                f"Necesita <b>{ANONYMOUS_MESSAGE_COST} besitos</b> para enviar este susurro a Diana.\n\n"
                f"Su saldo actual: <b>{current_balance} besitos</b>\n\n"
                f"Participe en la comunidad, reaccione a las publicaciones de Diana "
                f"o reclame su regalo diario para acumular más.",
                reply_markup=back_keyboard("vip_area"),
                parse_mode="HTML"
            )
            await state.clear()
            await callback.answer()
            return

        # Debitar besitos antes de enviar el mensaje
        debit_success = besito_service.debit_besitos(
            user_id=user.id,
            amount=ANONYMOUS_MESSAGE_COST,
            source=TransactionSource.ANONYMOUS_MESSAGE,
            description="Envío de mensaje anónimo a Diana",
            commit=True
        )

        if not debit_success:
            logger.error(f"Fallo al debitar besitos para mensaje anónimo: user={user.id}")
            await callback.message.edit_text(
                f"🎩 <b>Lucien:</b>\n\n"
                f"<i>Ha ocurrido un error inesperado...</i>\n\n"
                f"No se pudo procesar el pago. Intente nuevamente.",
                reply_markup=back_keyboard("vip_area"),
                parse_mode="HTML"
            )
            await state.clear()
            await callback.answer()
            return

        # Enviar mensaje anónimo
        anon_service = AnonymousMessageService()
        try:
            message = anon_service.send_message(user.id, content)

            logger.info(f"Mensaje anónimo enviado: id={message.id}, sender={user.id}, cost={ANONYMOUS_MESSAGE_COST}")

            await callback.message.edit_text(
                f"🎩 <b>Lucien:</b>\n\n"
                f"Listo.\n"
                f"Su mensaje ha sido entregado.\n\n"
                f"Se han debitado <b>{ANONYMOUS_MESSAGE_COST} besitos</b> de su cuenta.\n\n"
                f"Ahora queda en manos de Diana… decidir si responde, ignora…\n"
                f"o simplemente recuerda.\n\n"
                f"<i>Le sugiero no obsesionarse con la respuesta.</i>",
                reply_markup=back_keyboard("vip_area"),
                parse_mode="HTML"
            )
        finally:
            anon_service.close()
    finally:
        vip_service.close()
        besito_service.close()

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
