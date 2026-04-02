"""
Handlers VIP - Lucien Bot

Gestión de tarifas, tokens y suscripciones VIP.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config.settings import bot_config
from services.vip_service import VIPService
from services.channel_service import ChannelService
from keyboards.inline_keyboards import (
    vip_management_keyboard, tariffs_keyboard,
    confirmation_keyboard, back_keyboard, token_actions_keyboard,
    vip_entry_continue_keyboard, vip_entry_ready_keyboard
)
from utils.lucien_voice import LucienVoice
import logging

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
    tariffs = vip_service.get_all_tariffs(active_only=False)

    await callback.message.edit_text(
        LucienVoice.admin_tariff_list(tariffs),
        reply_markup=tariffs_keyboard(tariffs, for_selection=False),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "create_tariff")
async def create_tariff_start(callback: CallbackQuery, state: FSMContext):
    """Inicia creación de tarifa"""
    await callback.message.edit_text(
        f"🎩 <b>Lucien:</b>\n\n"
        f"<i>Vamos a calibrar una nueva tarifa para el círculo exclusivo...</i>\n\n"
        f"📋 <b>Paso 1 de 3:</b> Nombre de la tarifa\n"
        f"Ejemplos: <code>Mensual</code>, <code>Trimestral</code>, <code>Anual</code>",
        reply_markup=back_keyboard("manage_tariffs"),
        parse_mode="HTML"
    )
    await state.set_state(TariffStates.waiting_name)
    await callback.answer()


@router.message(TariffStates.waiting_name)
async def process_tariff_name(message: Message, state: FSMContext):
    """Procesa nombre de tarifa"""
    await state.update_data(name=message.text.strip())

    await message.answer(
        f"🎩 <b>Lucien:</b>\n\n"
        f"<i>Excelente. Ahora, la duración...</i>\n\n"
        f"📋 <b>Paso 2 de 3:</b> Duración en días\n"
        f"Ejemplos: <code>30</code> (mensual), <code>90</code> (trimestral), <code>365</code> (anual)",
        reply_markup=back_keyboard(),
        parse_mode="HTML"
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
            f"🎩 <b>Lucien:</b>\n\n"
            f"<i>Perfecto. Finalmente, el valor...</i>\n\n"
            f"📋 <b>Paso 3 de 3:</b> Precio de la tarifa\n"
            f"Ejemplo: <code>29.99 USD</code> o <code>500 MXN</code>",
            reply_markup=back_keyboard(),
            parse_mode="HTML"
        )
        await state.set_state(TariffStates.waiting_price)

    except ValueError:
        await message.answer(
            f"🎩 <b>Lucien:</b>\n\n"
            f"<i>Por favor, indique un número válido de días...</i>",
            reply_markup=back_keyboard(),
            parse_mode="HTML"
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
        parse_mode="HTML"
    )
    await state.set_state(TariffStates.confirming)


@router.callback_query(TariffStates.confirming, F.data == "confirm_tariff")
async def confirm_tariff(callback: CallbackQuery, state: FSMContext):
    """Crea la tarifa"""
    data = await state.get_data()
    vip_service = VIPService()

    try:
        tariff = vip_service.create_tariff(
            name=data['name'],
            duration_days=data['days'],
            price=data['price']
        )

        await callback.message.edit_text(
            LucienVoice.admin_tariff_created(data['name'], data['days'], data['price']),
            reply_markup=back_keyboard("manage_tariffs"),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Error creando tarifa: {e}")
        await callback.message.edit_text(
            LucienVoice.error_message("la creación de la tarifa"),
            reply_markup=back_keyboard("manage_tariffs"),
            parse_mode="HTML"
        )

    await state.clear()
    await callback.answer()


# ==================== GENERACIÓN DE TOKENS ====================

@router.callback_query(F.data == "generate_token")
async def generate_token_start(callback: CallbackQuery, state: FSMContext):
    """Inicia generación de token"""
    vip_service = VIPService()
    tariffs = vip_service.get_all_tariffs(active_only=True)

    if not tariffs:
        await callback.message.edit_text(
            f"🎩 <b>Lucien:</b>\n\n"
            f"<i>No hay tarifas activas para generar tokens...</i>\n\n"
            f"👉 <i>Cree una tarifa primero en 'Gestionar tarifas'.</i>",
            reply_markup=vip_management_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        f"🎩 <b>Lucien:</b>\n\n"
        f"<i>Seleccione la tarifa para la cual desea forjar un token de acceso...</i>",
        reply_markup=tariffs_keyboard(tariffs, for_selection=True),
        parse_mode="HTML"
    )
    await state.set_state(TokenStates.selecting_tariff)
    await callback.answer()


@router.callback_query(TokenStates.selecting_tariff, F.data.startswith("select_tariff_"))
async def generate_token(callback: CallbackQuery, state: FSMContext):
    """Genera el token para la tarifa seleccionada"""
    tariff_id = int(callback.data.replace("select_tariff_", ""))

    vip_service = VIPService()
    tariff = vip_service.get_tariff(tariff_id)

    if not tariff:
        await callback.answer("Tarifa no encontrada", show_alert=True)
        return

    try:
        token = vip_service.generate_token(tariff_id)
        token_url = f"https://t.me/{(await callback.bot.get_me()).username}?start={token.token_code}"

        await callback.message.edit_text(
            LucienVoice.token_generated(token_url, tariff.name),
            reply_markup=token_actions_keyboard(token.id),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Error generando token: {e}")
        await callback.message.edit_text(
            LucienVoice.error_message("la generación del token"),
            reply_markup=vip_management_keyboard(),
            parse_mode="HTML"
        )

    await state.clear()
    await callback.answer()


# ==================== LISTAR TOKENS ====================

@router.callback_query(F.data == "list_tokens")
async def list_tokens(callback: CallbackQuery):
    """Lista tokens generados"""
    vip_service = VIPService()
    tokens = vip_service.get_all_tokens()[:20]  # Limitar a 20 recientes

    if not tokens:
        await callback.message.edit_text(
            f"🎩 <b>Lucien:</b>\n\n"
            f"<i>No hay tokens registrados en los archivos...</i>",
            reply_markup=vip_management_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    text = f"""🎩 <b>Lucien:</b>

<i>Los accesos forjados para el círculo exclusivo...</i>

📋 <b>Tokens recientes:</b>

"""

    buttons = []
    for token in tokens:
        status_emoji = {
            "active": "🟢",
            "used": "🔴",
            "expired": "⚫"
        }.get(token.status.value, "⚪")

        text += f"{status_emoji} <code>{token.token_code[:16]}...</code> - {token.tariff.name}\n"

        if token.status.value == "active":
            buttons.append([InlineKeyboardButton(
                text=f"{status_emoji} {token.tariff.name} - Copiar",
                callback_data=f"copy_token_{token.id}"
            )])

    buttons.append([InlineKeyboardButton(
        text="🔙 Volver",
        callback_data="admin_vip"
    )])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("copy_token_"))
async def copy_token(callback: CallbackQuery):
    """Copia el enlace del token"""
    token_id = int(callback.data.replace("copy_token_", ""))

    vip_service = VIPService()
    token = vip_service.get_token(token_id)

    if not token:
        await callback.answer("Token no encontrado", show_alert=True)
        return

    bot_info = await callback.bot.get_me()
    token_url = f"https://t.me/{bot_info.username}?start={token.token_code}"

    await callback.message.answer(
        f"🔗 <b>Enlace del token:</b>\n<code>{token_url}</code>",
        parse_mode="HTML"
    )
    await callback.answer("Enlace copiado")


# ==================== LISTAR SUSCRIPTORES ====================

@router.callback_query(F.data == "list_subscribers")
async def list_subscribers(callback: CallbackQuery):
    """Lista suscriptores VIP activos"""
    vip_service = VIPService()
    subscriptions = vip_service.get_active_subscriptions()

    if not subscriptions:
        await callback.message.edit_text(
            f"🎩 <b>Lucien:</b>\n\n"
            f"<i>No hay miembros en el círculo exclusivo actualmente...</i>\n\n"
            f"Los selectos aún no han llegado.",
            reply_markup=vip_management_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    text = f"""🎩 <b>Lucien:</b>

<i>Los privilegiados del círculo exclusivo...</i>

👑 <b>Suscriptores activos:</b> {len(subscriptions)}

"""

    for sub in subscriptions[:10]:  # Mostrar primeros 10
        username = f"@{sub.user.username}" if sub.user and sub.user.username else f"ID:{sub.user_id}"
        expiry = sub.end_date.strftime("%d/%m/%Y")
        text += f"• {username} - Vence: {expiry}\n"

    if len(subscriptions) > 10:
        text += f"\n<i>...y {len(subscriptions) - 10} más.</i>"

    await callback.message.edit_text(
        text,
        reply_markup=vip_management_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== RITUAL DE ENTRADA VIP (PHASE 10) ====================

@router.callback_query(F.data == "vip_entry_continue")
async def vip_entry_continue(callback: CallbackQuery):
    """Fase 1 → 2: Continuar ritual de entrada VIP"""
    user = callback.from_user
    vip_service = VIPService()
    try:
        # Guard against repeat clicks
        status, _ = vip_service.get_vip_entry_state(user.id)
        if status != "pending_entry":
            await callback.answer("El ritual ya ha sido completado.")
            return

        # Guard against expired subscriptions
        subscription = vip_service.get_active_subscription_for_entry(user.id)
        if not subscription:
            vip_service.clear_vip_entry_state(user.id)
            await callback.message.edit_text(
                LucienVoice.vip_entry_expired(),
                parse_mode="HTML"
            )
            await callback.answer()
            return

        # Advance to stage 2
        vip_service.advance_vip_entry_stage(user.id)

        await callback.message.edit_text(
            LucienVoice.vip_entry_stage_2(),
            reply_markup=vip_entry_ready_keyboard(),
            parse_mode="HTML"
        )
    finally:
        vip_service.close()
    await callback.answer()


@router.callback_query(F.data == "vip_entry_ready")
async def vip_entry_ready(callback: CallbackQuery):
    """Fase 2 → 3: Estoy listo - genera link y completa ritual"""
    user = callback.from_user
    vip_service = VIPService()
    try:
        # Guard against repeat clicks — use FOR UPDATE to prevent race condition
        # where two rapid clicks both see "pending_entry" and both create invite links
        status, _ = vip_service.get_vip_entry_state_for_update(user.id)
        if status != "pending_entry":
            await callback.answer("El ritual ya ha sido completado.")
            return

        # Guard against expired subscriptions
        subscription = vip_service.get_active_subscription_for_entry(user.id)
        if not subscription:
            vip_service.clear_vip_entry_state(user.id)
            await callback.message.edit_text(
                LucienVoice.vip_entry_expired(),
                parse_mode="HTML"
            )
            await callback.answer()
            return

        # Advance to stage 3 (reuses the same db session with FOR UPDATE lock held)
        vip_service.advance_vip_entry_stage(user.id)

        # Send stage 3 message
        await callback.message.edit_text(
            LucienVoice.vip_entry_stage_3(),
            parse_mode="HTML"
        )

        # Generate invite link
        vip_channel = vip_service.get_vip_channel()
        if vip_channel:
            try:
                invite_link = await callback.bot.create_chat_invite_link(
                    chat_id=vip_channel.channel_id,
                    name=f"VIP {user.id}",
                    creates_join_request=False,
                    member_limit=1
                )
                await callback.message.answer(
                    f"🔗 <b>Su enlace de acceso exclusivo:</b>\n\n"
                    f"{invite_link.invite_link}\n\n"
                    f"<i>Diana le espera en el círculo íntimo...</i>",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Error creando invite link: {e}")
                if vip_channel.invite_link:
                    await callback.message.answer(vip_channel.invite_link, parse_mode="HTML")

        # Complete the entry
        vip_service.complete_vip_entry(user.id)
    finally:
        vip_service.close()
    await callback.answer()
