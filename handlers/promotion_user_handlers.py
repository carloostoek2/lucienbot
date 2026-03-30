"""
Handlers de Promociones para Usuarios - Lucien Bot

Catalogo de promociones, sistema "Me Interesa" y notificaciones.
Con la voz caracteristica de Lucien.
"""
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from services.promotion_service import PromotionService
from config.settings import bot_config
import logging

logger = logging.getLogger(__name__)
router = Router()


# ==================== MENU PRINCIPAL ====================

@router.callback_query(F.data == "offers")
async def offers_menu(callback: CallbackQuery):
    """Menu principal de ofertas/promociones - Voz de Lucien"""
    promotion_service = PromotionService()

    # Contar promociones disponibles
    available_promos = promotion_service.get_available_promotions()
    user_interests = promotion_service.get_user_interest_history(callback.from_user.id)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"✨ Ver las ofertas exclusivas ({len(available_promos)})",
            callback_data="offers_catalog"
        )],
        [InlineKeyboardButton(
            text=f"📜 Sus expresiones de interes ({len(user_interests)})",
            callback_data="my_offers_history"
        )],
        [InlineKeyboardButton(
            text="🔙 Volver",
            callback_data="back_to_main"
        )]
    ])

    text = ("🎩 <b>Lucien:</b>\n\n"
            "<i>Ah... el Gabinete de Oportunidades.</i>\n\n"
            "Diana ha seleccionado ciertas... experiencias exclusivas "
            "que solo unos pocos podran apreciar en su totalidad.\n\n"
            "Cada oferta tiene su precio en la moneda del mundo exterior, "
            "pero el verdadero valor... bueno, eso depende de quien lo perciba.")

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


# ==================== CATALOGO DE PROMOCIONES ====================

@router.callback_query(F.data == "offers_catalog")
async def offers_catalog(callback: CallbackQuery):
    """Muestra el catalogo de promociones disponibles - Voz de Lucien"""
    promotion_service = PromotionService()
    promos = promotion_service.get_available_promotions()

    if not promos:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Volver", callback_data="offers")]
        ])
        text = ("🎩 <b>Lucien:</b>\n\n"
                "<i>El Gabinete esta... momentaneamente vacio.</i>\n\n"
                "Diana esta preparando nuevas experiencias. "
                "Las oportunidades mas exquisitas requieren su tiempo, ya sabe...")
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        return

    # Verificar si el usuario esta bloqueado
    user_id = callback.from_user.id
    is_blocked = promotion_service.is_user_blocked(user_id)

    text = "🎩 <b>Lucien:</b>\n\n"
    text += "<i>Las ofertas que Diana ha preparado para usted:</i>\n\n"

    buttons = []
    for promo in promos:
        file_count = promo.file_count
        text += f"✨ <b>{promo.name}</b>\n"
        text += f"   💰 {promo.price_display}\n"
        text += f"   📁 {file_count} archivo{'s' if file_count != 1 else ''}\n"
        if promo.description:
            desc = promo.description[:50] + '...' if len(promo.description) > 50 else promo.description
            text += f"   <i>{desc}</i>\n"
        text += "\n"

        buttons.append([InlineKeyboardButton(
            text=f"👁️ Examinar: {promo.name[:25]}",
            callback_data=f"view_offer_{promo.id}"
        )])

    if is_blocked:
        text += "\n<i>...hay ciertas restricciones en su cuenta que impiden nuevas expresiones de interes.</i>\n"

    buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="offers")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await callback.answer()


@router.callback_query(F.data.startswith("view_offer_"))
async def view_offer_detail(callback: CallbackQuery):
    """Muestra detalle de una promocion - Voz de Lucien"""
    try:
        promo_id = int(callback.data.replace("view_offer_", ""))
    except ValueError:
        await callback.answer("Hmm... algo inesperado ha ocurrido.", show_alert=True)
        return

    promotion_service = PromotionService()
    promo = promotion_service.get_promotion(promo_id)

    if not promo:
        await callback.answer("Esa oferta parece haberse... desvanecido.", show_alert=True)
        return

    if not promo.is_available:
        await callback.answer("Esa oportunidad ya no esta disponible.", show_alert=True)
        return

    user_id = callback.from_user.id
    has_interest = promotion_service.has_user_expressed_interest(user_id, promo_id)
    is_blocked = promotion_service.is_user_blocked(user_id)
    file_count = promo.file_count

    text = f"🎩 <b>Lucien:</b>\n\n"
    text += f"✨ <b>{promo.name}</b>\n\n"

    if promo.description:
        text += f"<i>{promo.description}</i>\n\n"

    text += f"💰 <b>Inversion:</b> {promo.price_display}\n"
    text += f"📁 <b>Contenido:</b> {file_count} archivo{'s' if file_count != 1 else ''}\n\n"

    buttons = []

    if has_interest:
        text += ("<i>Ya ha expresado su interes en esta experiencia. "
                 "Diana ha sido notificada y se pondra en contacto con usted...</i>\n")
        buttons.append([InlineKeyboardButton(
            text="📜 Ver sus expresiones de interes",
            callback_data="my_offers_history"
        )])
    elif is_blocked:
        text += ("<i>Su cuenta tiene ciertas... limitaciones que impiden expresar interes. "
                 "Permitame consultar con Diana sobre este inconveniente.</i>\n")
    else:
        text += "<i>Si esta experiencia despierta su curiosidad, puede expresarlo...</i>\n"
        buttons.append([InlineKeyboardButton(
            text="💕 Me interesa",
            callback_data=f"offer_interest_{promo.id}"
        )])

    buttons.append([InlineKeyboardButton(text="🔙 Volver al Gabinete", callback_data="offers_catalog")])
    buttons.append([InlineKeyboardButton(text="🏠 Menu principal", callback_data="back_to_main")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await callback.answer()


# ==================== SISTEMA "ME INTERESA" ====================

@router.callback_query(F.data.startswith("offer_interest_"))
async def express_interest(callback: CallbackQuery, bot: Bot):
    """Procesa el interes del usuario en una promocion - Voz de Lucien"""
    try:
        promo_id = int(callback.data.replace("offer_interest_", ""))
    except ValueError:
        await callback.answer("Hmm... algo inesperado ha ocurrido.", show_alert=True)
        return

    promotion_service = PromotionService()
    user = callback.from_user

    # Verificar si el usuario esta bloqueado
    if promotion_service.is_user_blocked(user.id):
        await callback.answer(
            "No puede expresar interes. Hay restricciones en su cuenta.",
            show_alert=True
        )
        return

    # Verificar si ya expreso interes
    if promotion_service.has_user_expressed_interest(user.id, promo_id):
        await callback.answer(
            "Ya ha expresado interes en esta experiencia.",
            show_alert=True
        )
        return

    # Registrar el interes
    success, message, interest = promotion_service.express_interest(
        user_id=user.id,
        promotion_id=promo_id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )

    if not success:
        await callback.answer(message, show_alert=True)
        return

    promo = promotion_service.get_promotion(promo_id)
    promo_name = promo.name if promo else "Oferta"

    # Notificar a todos los administradores
    await notify_admins_about_interest(bot, interest, promo)

    # Mostrar confirmacion al usuario con link a Diana
    creator_username = getattr(bot_config, 'CREATOR_USERNAME', None)

    keyboard_buttons = [
        [InlineKeyboardButton(text="🔙 Volver al Gabinete", callback_data="offers_catalog")],
        [InlineKeyboardButton(text="🏠 Menu principal", callback_data="back_to_main")]
    ]

    # Agregar boton de contacto si hay username configurado
    if creator_username:
        keyboard_buttons.insert(0, [InlineKeyboardButton(
            text="💬 Contactar a Diana",
            url=f"https://t.me/{creator_username}"
        )])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    text = (f"🎩 <b>Lucien:</b>\n\n"
            f"<i>Su interes ha sido... registrado.</i>\n\n"
            f"✨ <b>{promo_name}</b>\n\n"
            f"<i>Diana ha sido notificada de su curiosidad. "
            f"En breve se pondra en contacto con usted...</i>\n\n"
            f"<i>Si lo prefiere, tambien puede iniciar la conversacion. "
            f"Diana aprecia la... iniciativa.</i> 🌸")

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await callback.answer("Interes registrado")


async def notify_admins_about_interest(bot: Bot, interest, promo):
    """Notifica a todos los administradores sobre un nuevo interes - Voz de Lucien"""

    # Construir informacion del usuario
    user_display = interest.username or interest.first_name or f"Visitante {interest.user_id}"
    if interest.first_name and interest.last_name:
        user_display = f"{interest.first_name} {interest.last_name}"
    elif interest.first_name:
        user_display = interest.first_name

    user_link = f"tg://user?id={interest.user_id}"
    promo_name = promo.name if promo else "Desconocida"
    promo_price = promo.price_display if promo else "N/A"

    # Mensaje para admins - Voz de Lucien
    notification_text = (
        f"🎩 <b>Lucien - Notificacion del Gabinete</b>\n\n"
        f"🔔 <b>Nueva expresion de interes</b>\n\n"
        f"👤 <b>Visitante:</b> {user_display}\n"
        f"   ID: <code>{interest.user_id}</code>\n"
        f"   Username: @{interest.username or 'N/A'}\n\n"
        f"✨ <b>Experiencia:</b> {promo_name}\n"
        f"💰 <b>Inversion:</b> {promo_price}\n\n"
        f"📅 <b>Fecha:</b> {interest.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
        f"<i>Un alma inquieta ha mostrado interes. Diana estara... atenta.</i>"
    )

    # Teclado con acciones para el admin
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="💬 Contactar al visitante",
            url=user_link
        )],
        [InlineKeyboardButton(
            text="✅ Marcar como atendido",
            callback_data=f"mark_attended_{interest.id}"
        )],
        [InlineKeyboardButton(
            text="🚫 Bloquear visitante",
            callback_data=f"block_interest_user_{interest.id}"
        )]
    ])

    # Enviar notificacion a todos los admins
    for admin_id in bot_config.ADMIN_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=notification_text,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            logger.info(f"Notificacion enviada al custodio {admin_id}")
        except Exception as e:
            logger.error(f"Error notificando al custodio {admin_id}: {e}")


# ==================== HISTORIAL DE INTERESES ====================

@router.callback_query(F.data == "my_offers_history")
async def my_offers_history(callback: CallbackQuery):
    """Muestra el historial de intereses del usuario - Voz de Lucien"""
    promotion_service = PromotionService()
    user_id = callback.from_user.id

    interests = promotion_service.get_user_interest_history(user_id)

    if not interests:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✨ Ver el Gabinete", callback_data="offers_catalog")],
            [InlineKeyboardButton(text="🔙 Volver", callback_data="offers")]
        ])
        text = ("🎩 <b>Lucien:</b>\n\n"
                "<i>Aun no ha expresado interes en ninguna experiencia...</i>\n\n"
                "El Gabinete de Oportunidades espera su visita. "
                "Diana tiene selecciones que podrian... despertar su curiosidad.")
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        return

    text = "🎩 <b>Lucien:</b>\n\n"
    text += "<i>Su historial de expresiones de interes:</i>\n\n"

    for interest in interests:
        promo = interest.promotion
        promo_name = promo.name if promo else "Desconocida"

        status_emoji = {
            "pending": "⏳",
            "attended": "✅",
            "blocked": "🚫"
        }.get(interest.status.value, "❓")

        date_str = interest.created_at.strftime("%d/%m/%Y") if interest.created_at else "?"

        text += f"{status_emoji} <b>{promo_name}</b>\n"
        text += f"   <i>Fecha: {date_str}</i>\n"
        text += f"   <i>Estado: {interest.status.value.title()}</i>\n\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✨ Ver el Gabinete", callback_data="offers_catalog")],
        [InlineKeyboardButton(text="🔙 Volver", callback_data="offers")]
    ])

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await callback.answer()
