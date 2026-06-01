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
    SelectTariffCallback,
    ToggleGiftCallback,
)
from keyboards.inline_keyboards import (
    back_keyboard,
    confirmation_keyboard,
    tariffs_keyboard,
    token_actions_keyboard,
    vip_management_keyboard,
)
from services.vip_service import VIPService
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


# ==================== GESTIÓN DE TARIFAS ====================


@router.callback_query(F.data == "manage_tariffs")
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


@router.callback_query(F.data == "create_tariff")
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


@router.message(TariffStates.waiting_name)
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


@router.message(TariffStates.waiting_days)
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


@router.message(TariffStates.waiting_price)
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


@router.callback_query(TokenStates.selecting_tariff, SelectTariffCallback.filter())
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


# ==================== LISTAR SUSCRIPTORES ====================


@router.callback_query(F.data == "list_subscribers")
async def list_subscribers(callback: CallbackQuery):
    """Lista suscriptores VIP activos"""
    vip_service = VIPService()
    try:
        subscriptions = vip_service.get_active_subscriptions()

        if not subscriptions:
            await callback.message.edit_text(
                "🎩 <b>Lucien:</b>\n\n"
                "<i>No hay miembros en El Diván actualmente...</i>\n\n"
                "Los selectos aún no han llegado.",
                reply_markup=vip_management_keyboard(),
                parse_mode="HTML",
            )
            await callback.answer()
            return

        text = f"""🎩 <b>Lucien:</b>

<i>Los privilegiados de El Diván...</i>

👑 <b>Suscriptores activos:</b> {len(subscriptions)}

"""

        for sub in subscriptions[:10]:  # Mostrar primeros 10
            username = (
                f"@{sub.user.username}" if sub.user and sub.user.username else f"ID:{sub.user_id}"
            )
            expiry = sub.end_date.strftime("%d/%m/%Y")
            text += f"• {username} - Vence: {expiry}\n"

        if len(subscriptions) > 10:
            text += f"\n<i>...y {len(subscriptions) - 10} más.</i>"

        await callback.message.edit_text(
            text, reply_markup=vip_management_keyboard(), parse_mode="HTML"
        )
    finally:
        vip_service.close()
    await callback.answer()
