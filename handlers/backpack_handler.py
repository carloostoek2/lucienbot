"""
Backpack Handler - Sistema de Mochila (Inventario de Usuario)

Maneja el comando /mochila y callbacks relacionados.
"""
from typing import Dict
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram import Bot

from services.backpack_service import BackpackService
from services.vip_service import VIPService
from utils.lucien_voice import LucienVoice
import logging

logger = logging.getLogger(__name__)

router = Router()


class BackpackStates(StatesGroup):
    """Estados para el flujo de mochila"""
    main_menu = State()
    rewards_list = State()
    purchases_list = State()
    vip_list = State()
    reward_detail = State()


def build_backpack_summary_keyboard(summary: dict) -> InlineKeyboardMarkup:
    """Construye el keyboard del menú principal de mochila"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"🎁 Mis Recompensas ({summary['rewards_count']})",
            callback_data="backpack_rewards"
        )],
        [InlineKeyboardButton(
            text=f"🛒 Mis Compras ({summary['purchases_count']})",
            callback_data="backpack_purchases"
        )],
        [InlineKeyboardButton(
            text=f"👑 Membresías VIP ({summary['vip_count']})",
            callback_data="backpack_vip"
        )],
        [InlineKeyboardButton(
            text="🔙 Volver al menú",
            callback_data="back_to_main"
        )]
    ])


def build_rewards_keyboard(rewards: list, page: int = 0) -> InlineKeyboardMarkup:
    """Construye el keyboard de lista de recompensas con paginación"""
    items_per_page = 10
    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(rewards))
    page_rewards = rewards[start_idx:end_idx]

    keyboard_buttons = []

    for reward in page_rewards:
        reward_type_emoji = {
            'BESITOS': '💋',
            'PACKAGE': '📦',
            'VIP_ACCESS': '👑'
        }.get(reward['reward_type'], '🎁')

        text = f"{reward_type_emoji} {reward['reward_name'][:25]}"
        callback_data = f"backpack_reward_{reward['history_id']}"
        keyboard_buttons.append([InlineKeyboardButton(text=text, callback_data=callback_data)])

    # Navigation buttons
    nav_buttons = []
    total_pages = (len(rewards) + items_per_page - 1) // items_per_page
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"backpack_rewards_page_{page - 1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"backpack_rewards_page_{page + 1}"))

    if nav_buttons:
        keyboard_buttons.append(nav_buttons)

    keyboard_buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="backpack_main")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


def build_purchases_keyboard(purchases: list, page: int = 0) -> InlineKeyboardMarkup:
    """Construye el keyboard de lista de compras con paginación"""
    items_per_page = 10
    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(purchases))
    page_purchases = purchases[start_idx:end_idx]

    keyboard_buttons = []

    for purchase in page_purchases:
        price = purchase.get('total_price', 0)
        text = f"📦 {purchase['product_name'][:20]} - {price} 💋"
        callback_data = f"backpack_purchase_{purchase['order_id']}_{purchase['product_id']}"
        keyboard_buttons.append([InlineKeyboardButton(text=text, callback_data=callback_data)])

    # Navigation buttons
    nav_buttons = []
    total_pages = (len(purchases) + items_per_page - 1) // items_per_page
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"backpack_purchases_page_{page - 1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"backpack_purchases_page_{page + 1}"))

    if nav_buttons:
        keyboard_buttons.append(nav_buttons)

    keyboard_buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="backpack_main")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


def build_vip_keyboard(subscriptions: list) -> InlineKeyboardMarkup:
    """Construye el keyboard de lista de membresías VIP"""
    keyboard_buttons = []

    for sub in subscriptions:
        end_str = sub['end_date'].strftime("%d/%m/%Y") if sub.get('end_date') else "??/??"
        text = f"👑 {sub.get('tariff_name', 'VIP')} - Vence: {end_str}"
        callback_data = f"backpack_vip_{sub['subscription_id']}"
        keyboard_buttons.append([InlineKeyboardButton(text=text, callback_data=callback_data)])

    keyboard_buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="backpack_main")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


def build_reward_detail_keyboard(reward: dict) -> InlineKeyboardMarkup:
    """Construye el keyboard de detalle de recompensa"""
    keyboard_buttons = []

    if reward.get('reward_type') == 'PACKAGE' and reward.get('package_id'):
        keyboard_buttons.append([
            InlineKeyboardButton(text="📂 Ver Contenido", callback_data=f"backpack_deliver_{reward['package_id']}")
        ])

    keyboard_buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="backpack_rewards")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


def build_purchase_detail_keyboard(purchase: dict) -> InlineKeyboardMarkup:
    """Construye el keyboard de detalle de compra"""
    keyboard_buttons = []

    if purchase.get('package_id'):
        keyboard_buttons.append([
            InlineKeyboardButton(text="📂 Ver Contenido", callback_data=f"backpack_deliver_{purchase['package_id']}")
        ])

    keyboard_buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="backpack_purchases")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


# ==================== COMMAND ====================

@router.message(Command("mochila"))
async def cmd_mochila(message: Message, bot: Bot):
    """Muestra el menú principal de la mochila"""
    user_id = message.from_user.id

    try:
        backpack_service = BackpackService()
        summary = backpack_service.get_backpack_summary(user_id)
        backpack_service.close()

        text = LucienVoice.backpack_summary(summary)
        keyboard = build_backpack_summary_keyboard(summary)

        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
        logger.info(f"backpack_handler | cmd_mochila | user_id={user_id} | result=shown")

    except Exception as e:
        logger.error(f"backpack_handler | cmd_mochila | user_id={user_id} | error={e}")
        await message.answer(LucienVoice.error_message("mostrar la mochila"))


# ==================== CALLBACKS ====================

@router.callback_query(F.data == "backpack_menu")
async def callback_backpack_menu(callback: CallbackQuery, bot: Bot):
    """Accede al menú de la mochila desde el menú principal"""
    user_id = callback.from_user.id

    try:
        backpack_service = BackpackService()
        summary = backpack_service.get_backpack_summary(user_id)
        backpack_service.close()

        text = LucienVoice.backpack_summary(summary)
        keyboard = build_backpack_summary_keyboard(summary)

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
        logger.info(f"backpack_handler | callback_backpack_menu | user_id={user_id} | result=shown")

    except Exception as e:
        logger.error(f"backpack_handler | callback_backpack_menu | user_id={user_id} | error={e}")
        await callback.answer("Error al cargar la mochila", show_alert=True)


@router.callback_query(F.data == "backpack_main")
async def callback_backpack_main(callback: CallbackQuery, bot: Bot):
    """Vuelve al menú principal de la mochila"""
    user_id = callback.from_user.id

    try:
        backpack_service = BackpackService()
        summary = backpack_service.get_backpack_summary(user_id)
        backpack_service.close()

        text = LucienVoice.backpack_summary(summary)
        keyboard = build_backpack_summary_keyboard(summary)

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
        logger.info(f"backpack_handler | callback_backpack_main | user_id={user_id} | result=shown")

    except Exception as e:
        logger.error(f"backpack_handler | callback_backpack_main | user_id={user_id} | error={e}")
        await callback.answer("Error al cargar la mochila", show_alert=True)


@router.callback_query(F.data == "backpack_rewards")
async def callback_rewards(callback: CallbackQuery, bot: Bot):
    """Muestra lista de recompensas del usuario"""
    user_id = callback.from_user.id

    try:
        backpack_service = BackpackService()
        rewards = backpack_service.get_user_rewards(user_id)
        backpack_service.close()

        text = LucienVoice.backpack_rewards_list(rewards)
        keyboard = build_rewards_keyboard(rewards)

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
        logger.info(f"backpack_handler | callback_rewards | user_id={user_id} | result=shown: {len(rewards)}")

    except Exception as e:
        logger.error(f"backpack_handler | callback_rewards | user_id={user_id} | error={e}")
        await callback.answer("Error al cargar recompensas", show_alert=True)


@router.callback_query(F.data.startswith("backpack_rewards_page_"))
async def callback_rewards_page(callback: CallbackQuery, bot: Bot):
    """Muestra página de recompensas"""
    user_id = callback.from_user.id
    page = int(callback.data.split("_")[-1])

    try:
        backpack_service = BackpackService()
        rewards = backpack_service.get_user_rewards(user_id, limit=50)
        backpack_service.close()

        text = LucienVoice.backpack_rewards_list(rewards)
        keyboard = build_rewards_keyboard(rewards, page=page)

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
        logger.info(f"backpack_handler | callback_rewards_page | user_id={user_id} | page={page}")

    except Exception as e:
        logger.error(f"backpack_handler | callback_rewards_page | user_id={user_id} | error={e}")
        await callback.answer("Error al cargar página", show_alert=True)


@router.callback_query(F.data == "backpack_purchases")
async def callback_purchases(callback: CallbackQuery, bot: Bot):
    """Muestra lista de compras del usuario"""
    user_id = callback.from_user.id

    try:
        backpack_service = BackpackService()
        purchases = backpack_service.get_user_purchases(user_id)
        backpack_service.close()

        text = LucienVoice.backpack_purchases_list(purchases)
        keyboard = build_purchases_keyboard(purchases)

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
        logger.info(f"backpack_handler | callback_purchases | user_id={user_id} | result=shown: {len(purchases)}")

    except Exception as e:
        logger.error(f"backpack_handler | callback_purchases | user_id={user_id} | error={e}")
        await callback.answer("Error al cargar compras", show_alert=True)


@router.callback_query(F.data.startswith("backpack_purchases_page_"))
async def callback_purchases_page(callback: CallbackQuery, bot: Bot):
    """Muestra página de compras"""
    user_id = callback.from_user.id
    page = int(callback.data.split("_")[-1])

    try:
        backpack_service = BackpackService()
        purchases = backpack_service.get_user_purchases(user_id, limit=50)
        backpack_service.close()

        text = LucienVoice.backpack_purchases_list(purchases)
        keyboard = build_purchases_keyboard(purchases, page=page)

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
        logger.info(f"backpack_handler | callback_purchases_page | user_id={user_id} | page={page}")

    except Exception as e:
        logger.error(f"backpack_handler | callback_purchases_page | user_id={user_id} | error={e}")
        await callback.answer("Error al cargar página", show_alert=True)


@router.callback_query(F.data == "backpack_vip")
async def callback_vip(callback: CallbackQuery, bot: Bot):
    """Muestra membresías VIP activas"""
    user_id = callback.from_user.id

    try:
        # Get VIP subscriptions via VIPService
        vip_service = VIPService()
        subscriptions = vip_service.get_active_subscriptions()
        vip_service.close()

        # Filter to user's subscriptions
        user_subs = [s for s in subscriptions if s.user_id == user_id]

        result = []
        for sub in user_subs:
            tariff_name = sub.token.tariff.name if sub.token and sub.token.tariff else "VIP"
            result.append({
                'subscription_id': sub.id,
                'tariff_name': tariff_name,
                'start_date': sub.start_date,
                'end_date': sub.end_date,
                'is_active': sub.is_active
            })

        text = LucienVoice.backpack_vip_list(result)
        keyboard = build_vip_keyboard(result)

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
        logger.info(f"backpack_handler | callback_vip | user_id={user_id} | result=shown: {len(result)}")

    except Exception as e:
        logger.error(f"backpack_handler | callback_vip | user_id={user_id} | error={e}")
        await callback.answer("Error al cargar VIP", show_alert=True)


@router.callback_query(F.data.startswith("backpack_reward_"))
async def callback_reward_detail(callback: CallbackQuery, bot: Bot):
    """Muestra detalle de una recompensa"""
    user_id = callback.from_user.id
    history_id = int(callback.data.split("_")[-1])

    try:
        backpack_service = BackpackService()
        rewards = backpack_service.get_user_rewards(user_id, limit=100)
        backpack_service.close()

        # Find the specific reward
        reward = None
        for r in rewards:
            if r['history_id'] == history_id:
                reward = r
                break

        if not reward:
            await callback.answer("Recompensa no encontrada", show_alert=True)
            return

        text = LucienVoice.backpack_reward_detail(reward)
        keyboard = build_reward_detail_keyboard(reward)

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
        logger.info(f"backpack_handler | callback_reward_detail | user_id={user_id} | reward_id={history_id}")

    except Exception as e:
        logger.error(f"backpack_handler | callback_reward_detail | user_id={user_id} | error={e}")
        await callback.answer("Error al cargar detalle", show_alert=True)


@router.callback_query(F.data.startswith("backpack_purchase_"))
async def callback_purchase_detail(callback: CallbackQuery, bot: Bot):
    """Muestra detalle de una compra"""
    user_id = callback.from_user.id
    parts = callback.data.split("_")
    order_id = int(parts[2])
    product_id = int(parts[3])

    try:
        backpack_service = BackpackService()
        purchases = backpack_service.get_user_purchases(user_id, limit=100)
        backpack_service.close()

        # Find the specific purchase
        purchase = None
        for p in purchases:
            if p['order_id'] == order_id and p['product_id'] == product_id:
                purchase = p
                break

        if not purchase:
            await callback.answer("Compra no encontrada", show_alert=True)
            return

        text = f"""🎩 <b>Lucien:</b>

<i>El tesoro adquirido espera por usted...</i>

📦 <b>Detalle de Compra</b>

🏷️ Producto: {purchase['product_name']}
📅 Fecha: {purchase['purchased_at'].strftime("%d/%m/%Y") if purchase.get('purchased_at') else 'N/A'}
💰 Total: {purchase['total_price']} besitos

<i>Un tesoro valioso del reino de Diana.</i>"""

        keyboard = build_purchase_detail_keyboard(purchase)

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
        logger.info(f"backpack_handler | callback_purchase_detail | user_id={user_id} | order_id={order_id}")

    except Exception as e:
        logger.error(f"backpack_handler | callback_purchase_detail | user_id={user_id} | error={e}")
        await callback.answer("Error al cargar detalle", show_alert=True)


@router.callback_query(F.data.startswith("backpack_deliver_"))
async def callback_deliver_package(callback: CallbackQuery, bot: Bot):
    """Entrega contenido de un paquete como álbum"""
    user_id = callback.from_user.id
    package_id = int(callback.data.split("_")[-1])

    try:
        backpack_service = BackpackService()
        success, message = await backpack_service.deliver_package_content(bot, user_id, package_id)
        backpack_service.close()

        if success:
            await callback.answer("Contenido entregado", show_alert=False)
        else:
            await callback.answer(message, show_alert=True)

        logger.info(f"backpack_handler | callback_deliver_package | user_id={user_id} | package_id={package_id} | result={success}")

    except Exception as e:
        logger.error(f"backpack_handler | callback_deliver_package | user_id={user_id} | error={e}")
        await callback.answer("Error al entregar contenido", show_alert=True)


@router.callback_query(F.data == "backpack_balance")
async def callback_balance(callback: CallbackQuery, bot: Bot):
    """Muestra información del balance de besitos"""
    user_id = callback.from_user.id

    try:
        backpack_service = BackpackService()
        summary = backpack_service.get_backpack_summary(user_id)
        backpack_service.close()

        text = f"""🎩 <b>Lucien:</b>

<i>Los besitos son la moneda del reino de Diana...</i>

💋 <b>Su Balance</b>

💰 <b>Besitos disponibles:</b> {summary['besitos_balance']}

<i>Use sus besitos para adquirir tesoros en la tienda
o completar misiones para ganar más.</i>"""

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Volver", callback_data="backpack_main")]
        ])

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
        logger.info(f"backpack_handler | callback_balance | user_id={user_id} | balance={summary['besitos_balance']}")

    except Exception as e:
        logger.error(f"backpack_handler | callback_balance | user_id={user_id} | error={e}")
        await callback.answer("Error al cargar balance", show_alert=True)
