"""
Handlers VIP para Usuarios - Lucien Bot

Handlers exclusivos para suscriptores VIP:
- Menú de El Diván
- Mensajes anónimos a Diana
"""

import html
import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from handlers.promotion_user_handlers import notify_admins_about_interest
from keyboards.callback_data import VipPromoDetailCallback, VipPromoInterestCallback
from keyboards.inline_keyboards import (
    admin_anonymous_notification_keyboard,
    back_keyboard,
    main_menu_keyboard,
)
from services import get_service
from services.anonymous_message_service import ANONYMOUS_MESSAGE_COST, AnonymousMessageService
from services.promotion_service import PromotionService
from services.vip_service import VIPService
from utils.admin import is_admin

logger = logging.getLogger(__name__)
router = Router()

# Estados para FSM
class AnonymousMessageStates(StatesGroup):
    waiting_message = State()
    confirming_send = State()


def vip_area_keyboard() -> InlineKeyboardMarkup:
    """Menú de El Diván VIP"""
    buttons = [
        [InlineKeyboardButton(text="🗺️ El Mapa del Deseo", callback_data="vip_map_of_desire")],
        [InlineKeyboardButton(text="💎 Trivia VIP", callback_data="game_trivia_vip")],
        [
            InlineKeyboardButton(
                text="💌 Mensajes anónimos a Diana", callback_data="send_anonymous_message"
            )
        ],
        [InlineKeyboardButton(text="🔙 Volver al menú principal", callback_data="back_to_main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def anonymous_message_confirm_keyboard() -> InlineKeyboardMarkup:
    """Teclado para confirmar envío de mensaje anónimo"""
    buttons = [
        [
            InlineKeyboardButton(text="✅ Enviar", callback_data="confirm_anonymous_send"),
            InlineKeyboardButton(text="❌ Cancelar", callback_data="cancel_anonymous"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ==================== MENÚ DE EL DIVÁN ====================


@router.callback_query(F.data == "vip_area", lambda cb: not is_admin(cb.from_user.id))
async def vip_area_menu(callback: CallbackQuery):
    """Muestra el menú exclusivo del círculo VIP"""
    user = callback.from_user

    # Verificar que sigue siendo VIP
    vip_service = VIPService()
    try:
        is_vip = vip_service.is_user_vip(user.id)
        if not is_vip:
            await callback.message.edit_text(
                "🎩 <b>Lucien:</b>\n\n"
                "<i>El Diván es solo para los privilegiados...</i>\n\n"
                "Su suscripción VIP no está activa.",
                reply_markup=main_menu_keyboard(is_vip=False),
                parse_mode="HTML",
            )
            await callback.answer()
            return

        await callback.message.edit_text(
            "🎩 <b>Lucien:</b>\n\n"
            "<i>Bienvenido a El Diván, donde los privilegiados "
            "tienen acceso a experiencias únicas...</i>\n\n"
            "💎 <b>El Diván</b>\n\n"
            "Aquí encontrará funciones reservadas solo para quienes "
            "han sido admitidos en la intimidad de Diana.",
            reply_markup=vip_area_keyboard(),
            parse_mode="HTML",
        )
        await callback.answer()
    finally:
        vip_service.close()


# ==================== EL MAPA DEL DESEO ====================


@router.callback_query(F.data == "vip_map_of_desire", lambda cb: not is_admin(cb.from_user.id))
async def show_map_of_desire(callback: CallbackQuery):
    """Muestra El Mapa del Deseo - promociones VIP exclusivas"""
    user = callback.from_user

    # Verificar que sigue siendo VIP
    vip_service = VIPService()
    try:
        is_vip = vip_service.is_user_vip(user.id)
        if not is_vip:
            await callback.message.edit_text(
                "🎩 <b>Lucien:</b>\n\n"
                "<i>El Mapa del Deseo solo se revela a quienes tienen acceso privilegiado...</i>\n\n"
                "Su suscripción VIP no está activa.",
                reply_markup=main_menu_keyboard(is_vip=False),
                parse_mode="HTML",
            )
            await callback.answer()
            return

        # Obtener promociones VIP exclusivas
        promotion_service = PromotionService()
        try:
            vip_promos = promotion_service.get_vip_exclusive_promotions()

            if not vip_promos:
                keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="🔙 Volver a El Diván", callback_data="vip_area"
                            )
                        ]
                    ]
                )
                text = (
                    "🎩 <b>Lucien:</b>\n\n"
                    "<i>El Mapa del Deseo está... momentáneamente en blanco.</i>\n\n"
                    "Diana está preparando nuevas experiencias exclusivas. "
                    "Las oportunidades más exquisitas requieren su tiempo..."
                )
                await callback.message.edit_text(text, reply_markup=keyboard)
                await callback.answer()
                return

            # Construir mensaje y botones
            text = (
                "🎩 <b>Lucien:</b>\n\n"
                "<i>Bienvenido al Mapa del Deseo...</i>\n\n"
                "Aquí se encuentran las experiencias más exclusivas que Diana "
                "ha reservado solo para quienes han demostrado su compromiso.\n\n"
                "Cada nivel ofrece una intimidad diferente con ella. "
                "Elija sabiamente..."
            )

            buttons = []
            for promo in vip_promos:
                buttons.append(
                    [
                        InlineKeyboardButton(
                            text=f"✨ {promo.name}",
                            callback_data=VipPromoDetailCallback(promo_id=promo.id).pack(),
                        )
                    ]
                )

            buttons.append(
                [InlineKeyboardButton(text="🔙 Volver a El Diván", callback_data="vip_area")]
            )

            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
            await callback.answer()

        finally:
            promotion_service.close()
    finally:
        vip_service.close()


@router.callback_query(VipPromoDetailCallback.filter(), lambda cb: not is_admin(cb.from_user.id))
async def view_vip_promotion_detail(callback: CallbackQuery, callback_data: VipPromoDetailCallback):
    """Muestra detalle de una promoción VIP exclusiva"""
    promo_id = callback_data.promo_id

    promotion_service = PromotionService()
    try:
        promo = promotion_service.get_promotion(promo_id)

        if not promo or not promo.is_vip_exclusive:
            await callback.answer("Esa oferta no está disponible.", show_alert=True)
            return

        user_id = callback.from_user.id
        has_interest = promotion_service.has_user_expressed_interest(user_id, promo_id)
        is_blocked = promotion_service.is_user_blocked(user_id)

        text = "🎩 <b>Lucien:</b>\n\n"
        text += f"✨ <b>{promo.name}</b>\n\n"

        if promo.description:
            text += f"{promo.description}\n\n"

        text += f"💰 <b>Inversión:</b> {promo.price_display}\n\n"

        buttons = []

        if has_interest:
            text += "<i>Ya ha expresado su interés en esta experiencia. "
            text += "Diana ha sido notificada...</i>\n"
        elif is_blocked:
            text += "<i>Su cuenta tiene ciertas... limitaciones.</i>\n"
        else:
            text += "<i>Si esta experiencia despierta su curiosidad...</i>\n"
            buttons.append(
                [
                    InlineKeyboardButton(
                        text="💕 Me interesa",
                        callback_data=VipPromoInterestCallback(promo_id=promo.id).pack(),
                    )
                ]
            )

        buttons.append(
            [InlineKeyboardButton(text="🔙 Volver al Mapa", callback_data="vip_map_of_desire")]
        )
        buttons.append([InlineKeyboardButton(text="🏠 El Diván", callback_data="vip_area")])

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
    finally:
        promotion_service.close()


@router.callback_query(VipPromoInterestCallback.filter(), lambda cb: not is_admin(cb.from_user.id))
async def express_vip_promo_interest(
    callback: CallbackQuery, bot: Bot, callback_data: VipPromoInterestCallback
):
    """Procesa interés en promoción VIP exclusiva"""
    promo_id = callback_data.promo_id

    promotion_service = PromotionService()
    user = callback.from_user

    try:
        # Verificar bloqueo
        if promotion_service.is_user_blocked(user.id):
            await callback.answer(
                "No puede expresar interés. Hay restricciones en su cuenta.", show_alert=True
            )
            return

        # Verificar si ya expresó interés
        if promotion_service.has_user_expressed_interest(user.id, promo_id):
            await callback.answer("Ya ha expresado interés en esta experiencia.", show_alert=True)
            return

        # Registrar interés
        success, message, interest = promotion_service.express_interest(
            user_id=user.id,
            promotion_id=promo_id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        )

        if not success:
            await callback.answer(message, show_alert=True)
            return

        promo = promotion_service.get_promotion(promo_id)
        promo_name = promo.name if promo else "Oferta"

        # Notificar a admins
        await notify_admins_about_interest(bot, interest, promo)

        # Mostrar confirmación
        from config.settings import bot_config

        creator_username = getattr(bot_config, "CREATOR_USERNAME", None)

        keyboard_buttons = [
            [InlineKeyboardButton(text="🔙 Volver al Mapa", callback_data="vip_map_of_desire")],
            [InlineKeyboardButton(text="🏠 El Diván", callback_data="vip_area")],
        ]

        if creator_username:
            keyboard_buttons.insert(
                0,
                [
                    InlineKeyboardButton(
                        text="💬 Contactar a Diana", url=f"https://t.me/{creator_username}"
                    )
                ],
            )

        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        text = (
            f"🎩 <b>Lucien:</b>\n\n"
            f"<i>Su interés ha sido... registrado.</i>\n\n"
            f"✨ <b>{promo_name}</b>\n\n"
            f"<i>Diana ha sido notificada de su curiosidad. "
            f"En breve se pondrá en contacto con usted...</i>"
        )

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer("Interés registrado")

    finally:
        promotion_service.close()


# ==================== MENSAJES ANÓNIMOS ====================


@router.callback_query(F.data == "send_anonymous_message", lambda cb: not is_admin(cb.from_user.id))
async def start_anonymous_message(callback: CallbackQuery, state: FSMContext):
    """Inicia el flujo de envío de mensaje anónimo"""
    user = callback.from_user

    # Verificar que sigue siendo VIP
    vip_service = VIPService()
    try:
        is_vip = vip_service.is_user_vip(user.id)
        if not is_vip:
            await callback.message.edit_text(
                "🎩 <b>Lucien:</b>\n\n"
                "<i>Esta función es exclusiva del círculo...</i>\n\n"
                "Su suscripción VIP no está activa.",
                reply_markup=main_menu_keyboard(is_vip=False),
                parse_mode="HTML",
            )
            await callback.answer()
            return

        await callback.message.edit_text(
            "🎩 <b>Lucien:</b>\n\n"
            "Este es uno de los pocos espacios donde puede dirigirse a Diana… sin ser visto.\n\n"
            "Su mensaje será completamente anónimo.\n"
            "Sin nombre. Sin rastro.\n\n"
            "Algo que debe saber:\n"
            "Diana <b>no</b> responde a todo.\n"
            "Solo a lo que… le interesa.\n\n"
            "📝 <i>Envíe su mensaje ahora</i>",
            reply_markup=back_keyboard("vip_area"),
            parse_mode="HTML",
        )
        await state.set_state(AnonymousMessageStates.waiting_message)
        await callback.answer()
    finally:
        vip_service.close()


@router.message(AnonymousMessageStates.waiting_message, lambda msg: not is_admin(msg.from_user.id))
async def process_anonymous_message(message: Message, state: FSMContext):
    """Procesa el mensaje anónimo ingresado"""
    content = (message.text or "").strip()
    if not content:
        return

    if len(content) < 3:
        await message.answer(
            "🎩 <b>Lucien:</b>\n\n"
            "<i>El mensaje es demasiado breve...</i>\n\n"
            "Por favor, escriba al menos unas palabras para Diana.",
            reply_markup=back_keyboard("vip_area"),
            parse_mode="HTML",
        )
        return

    if len(content) > 4000:
        await message.answer(
            "🎩 <b>Lucien:</b>\n\n"
            "<i>El mensaje excede el límite permitido...</i>\n\n"
            "Por favor, sea más conciso. Máximo 4000 caracteres.",
            reply_markup=back_keyboard("vip_area"),
            parse_mode="HTML",
        )
        return

    # Guardar en estado
    await state.update_data(message_content=content)

    # Mostrar preview para confirmar
    preview = content[:200] + "..." if len(content) > 200 else content
    safe_preview = html.escape(preview)

    await message.answer(
        f"🎩 <b>Lucien:</b>\n\n"
        f"Antes de enviarlo… léalo de nuevo.\n\n"
        f"Esto es lo que Diana recibirá:\n\n"
        f"<blockquote>{safe_preview}</blockquote>\n\n"
        f"💋 <b>Costo: {ANONYMOUS_MESSAGE_COST} besitos</b>\n\n"
        f"¿Está seguro de que esto… merece su atención?",
        reply_markup=anonymous_message_confirm_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(AnonymousMessageStates.confirming_send)


async def _reply_anonymous_send_failure(
    callback: CallbackQuery, state: FSMContext, result: str, user_id: int
) -> None:
    """Mapea result_code del servicio a mensaje user-facing."""
    if result == "not_vip":
        text = (
            "🎩 <b>Lucien:</b>\n\n"
            "<i>Su suscripción VIP ya no está activa...</i>\n\n"
            "El mensaje no pudo ser enviado."
        )
        markup = main_menu_keyboard(is_vip=False)
    elif result == "insufficient_balance":
        text = (
            f"🎩 <b>Lucien:</b>\n\n"
            f"<i>Los mensajes anónimos tienen un precio...</i>\n\n"
            f"Necesita <b>{ANONYMOUS_MESSAGE_COST} besitos</b> para enviar este susurro a Diana.\n\n"
            f"Participe en la comunidad, reaccione a las publicaciones de Diana "
            f"o reclame su regalo diario para acumular más."
        )
        markup = back_keyboard("vip_area")
    elif result == "invalid_content":
        text = (
            "🎩 <b>Lucien:</b>\n\n"
            "<i>El mensaje no cumple los requisitos...</i>\n\n"
            "Debe tener entre 3 y 4000 caracteres. Intente nuevamente."
        )
        markup = back_keyboard("vip_area")
    else:
        if result == "debit_failed":
            logger.error(f"Fallo al debitar besitos para mensaje anónimo: user={user_id}")
        elif result == "internal_error":
            logger.error(f"Error interno en mensaje anónimo: user={user_id}")
        text = (
            "🎩 <b>Lucien:</b>\n\n"
            "<i>Ha ocurrido un error inesperado...</i>\n\n"
            "No se pudo procesar el pago. Intente nuevamente."
        )
        markup = back_keyboard("vip_area")
    await callback.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    await state.clear()
    await callback.answer()


async def _reply_anonymous_send_success(
    callback: CallbackQuery, state: FSMContext, message_id: int
) -> None:
    """Confirma envío y notifica admins (best-effort post-commit)."""
    from config.settings import bot_config

    for admin_id in bot_config.ADMIN_IDS:
        try:
            await callback.bot.send_message(
                chat_id=admin_id,
                text="🎩 <b>Lucien:</b>\n\nAlguien ha buscado su atención de manera anónima",
                reply_markup=admin_anonymous_notification_keyboard(message_id),
                parse_mode="HTML",
            )
        except Exception as e:
            logger.warning(f"No se pudo notificar al admin {admin_id}: {e}")

    await callback.message.edit_text(
        f"🎩 <b>Lucien:</b>\n\n"
        f"Listo.\n"
        f"Su mensaje ha sido entregado.\n\n"
        f"Se han debitado <b>{ANONYMOUS_MESSAGE_COST} besitos</b> de su cuenta.\n\n"
        f"Ahora queda en manos de Diana… decidir si responde, ignora…\n"
        f"o simplemente recuerda.\n\n"
        f"<i>Le sugiero no obsesionarse con la respuesta.</i>",
        reply_markup=back_keyboard("vip_area"),
        parse_mode="HTML",
    )
    await state.clear()
    await callback.answer()


@router.callback_query(AnonymousMessageStates.confirming_send, F.data == "confirm_anonymous_send", lambda cb: not is_admin(cb.from_user.id))
async def confirm_anonymous_send(callback: CallbackQuery, state: FSMContext):
    """Confirma y envía el mensaje anónimo, debitando besitos primero"""
    user = callback.from_user
    content = (await state.get_data()).get("message_content")

    if not content:
        await callback.message.edit_text(
            "🎩 <b>Lucien:</b>\n\n"
            "<i>Ha ocurrido un error...</i>\n\n"
            "No se encontró el contenido del mensaje.",
            reply_markup=back_keyboard("vip_area"),
            parse_mode="HTML",
        )
        await state.clear()
        await callback.answer()
        return

    with get_service(AnonymousMessageService) as anon_service:
        success, result, message = anon_service.send_paid_anonymous_message(user.id, content)

    if not success:
        await _reply_anonymous_send_failure(callback, state, result, user.id)
        return

    logger.info(
        f"Mensaje anónimo enviado: id={message.id}, sender={user.id}, cost={ANONYMOUS_MESSAGE_COST}"
    )
    await _reply_anonymous_send_success(callback, state, message.id)


@router.callback_query(F.data == "cancel_anonymous", lambda cb: not is_admin(cb.from_user.id))
async def cancel_anonymous_message(callback: CallbackQuery, state: FSMContext):
    """Cancela el envío del mensaje anónimo"""
    await state.clear()
    await callback.message.edit_text(
        "🎩 <b>Lucien:</b>\n\n"
        "<i>El mensaje ha sido descartado...</i>\n\n"
        "Diana no recibirá nada. Puede escribir otro mensaje cuando lo desee.",
        reply_markup=vip_area_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer("Mensaje cancelado")
