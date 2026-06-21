"""
Backpack Handler - Sistema de Mochila (Inventario de Usuario)

Maneja el comando /mochila y callbacks relacionados.
"""

import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from keyboards.callback_data import (
    BackpackActivateVipCallback,
    BackpackDeliverCallback,
    BackpackFulfillmentRetryCallback,
    BackpackPurchaseDetailCallback,
    BackpackPurchasesPageCallback,
    BackpackReadChapterCallback,
    BackpackSubmitInputCallback,
    BackpackRewardDetailCallback,
    BackpackRewardsPageCallback,
    BackpackViewWaitlistCallback,
)
from keyboards.inline_keyboards import vip_access_keyboard
from services import get_service
from handlers.states.store_fulfillment_states import BackpackInputStates
from services.backpack_service import BackpackService
from services.story_service import StoryService
from utils.admin import is_admin
from utils.lucien_voice import LucienVoice

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
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"🎁 Mis Recompensas ({summary['rewards_count']})",
                    callback_data="backpack_rewards",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"🛒 Mis Compras ({summary['purchases_count']})",
                    callback_data="backpack_purchases",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"👑 Membresías VIP ({summary['vip_count']})", callback_data="backpack_vip"
                )
            ],
            [InlineKeyboardButton(text="🔙 Volver al menú", callback_data="back_to_main")],
        ]
    )


def build_rewards_keyboard(rewards: list, page: int = 0) -> InlineKeyboardMarkup:
    """Construye el keyboard de lista de recompensas con paginación"""
    items_per_page = 10
    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(rewards))
    page_rewards = rewards[start_idx:end_idx]

    keyboard_buttons = []

    for reward in page_rewards:
        reward_type_emoji = {"BESITOS": "💋", "PACKAGE": "📦", "VIP_ACCESS": "👑"}.get(
            reward["reward_type"], "🎁"
        )

        text = f"{reward_type_emoji} {reward['reward_name'][:25]}"
        callback_data = BackpackRewardDetailCallback(history_id=reward["history_id"]).pack()
        keyboard_buttons.append([InlineKeyboardButton(text=text, callback_data=callback_data)])

    # Navigation buttons
    nav_buttons = []
    total_pages = (len(rewards) + items_per_page - 1) // items_per_page
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(
                text="◀️", callback_data=BackpackRewardsPageCallback(page=page - 1).pack()
            )
        )
    if page < total_pages - 1:
        nav_buttons.append(
            InlineKeyboardButton(
                text="▶️", callback_data=BackpackRewardsPageCallback(page=page + 1).pack()
            )
        )

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
        price = purchase.get("total_price", 0)
        text = f"📦 {purchase['product_name'][:20]} - {price} 💋"
        callback_data = BackpackPurchaseDetailCallback(
            order_id=purchase["order_id"], product_id=purchase["product_id"]
        ).pack()
        keyboard_buttons.append([InlineKeyboardButton(text=text, callback_data=callback_data)])

    # Navigation buttons
    nav_buttons = []
    total_pages = (len(purchases) + items_per_page - 1) // items_per_page
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(
                text="◀️", callback_data=BackpackPurchasesPageCallback(page=page - 1).pack()
            )
        )
    if page < total_pages - 1:
        nav_buttons.append(
            InlineKeyboardButton(
                text="▶️", callback_data=BackpackPurchasesPageCallback(page=page + 1).pack()
            )
        )

    if nav_buttons:
        keyboard_buttons.append(nav_buttons)

    keyboard_buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="backpack_main")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


def build_vip_keyboard(subscriptions: list) -> InlineKeyboardMarkup:
    """Construye el keyboard de lista de membresías VIP"""
    keyboard_buttons = []

    for sub in subscriptions:
        end_str = sub["end_date"].strftime("%d/%m/%Y") if sub.get("end_date") else "??/??"
        text = f"👑 {sub.get('tariff_name', 'VIP')} - Vence: {end_str}"
        callback_data = f"backpack_vip_{sub['subscription_id']}"
        keyboard_buttons.append([InlineKeyboardButton(text=text, callback_data=callback_data)])

    keyboard_buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="backpack_main")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


def build_reward_detail_keyboard(reward: dict) -> InlineKeyboardMarkup:
    """Construye el keyboard de detalle de recompensa"""
    keyboard_buttons = []

    if reward.get("reward_type") == "PACKAGE" and reward.get("package_id"):
        keyboard_buttons.append(
            [
                InlineKeyboardButton(
                    text="📂 Ver Contenido",
                    callback_data=BackpackDeliverCallback(package_id=reward["package_id"]).pack(),
                )
            ]
        )

    keyboard_buttons.append(
        [InlineKeyboardButton(text="🔙 Volver", callback_data="backpack_rewards")]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


def build_purchase_detail_keyboard(purchase: dict) -> InlineKeyboardMarkup:
    """Construye el keyboard de detalle de compra"""
    keyboard_buttons = []
    actions = purchase.get("actions_available") or []
    fulfillment_id = purchase.get("fulfillment_id")

    if "retry_delivery" in actions and fulfillment_id:
        keyboard_buttons.append(
            [
                InlineKeyboardButton(
                    text=LucienVoice.backpack_fulfillment_retry_button(),
                    callback_data=BackpackFulfillmentRetryCallback(
                        fulfillment_id=fulfillment_id
                    ).pack(),
                )
            ]
        )
    if "resend_vip_invite" in actions and fulfillment_id:
        keyboard_buttons.append(
            [
                InlineKeyboardButton(
                    text=LucienVoice.backpack_fulfillment_resend_vip_invite_button(),
                    callback_data=BackpackActivateVipCallback(
                        fulfillment_id=fulfillment_id
                    ).pack(),
                )
            ]
        )
    package_kinds = {"package", "package_deferred"}
    if (
        purchase.get("fulfillment_kind") in package_kinds
        and purchase.get("fulfillment_status") == "fulfilled"
    ):
        package_id = purchase.get("package_id") or (purchase.get("auto_result") or {}).get(
            "package_id"
        )
        if package_id:
            keyboard_buttons.append(
                [
                    InlineKeyboardButton(
                        text="📂 Ver Contenido",
                        callback_data=BackpackDeliverCallback(package_id=package_id).pack(),
                    )
                ]
            )
    if "submit_input" in actions and fulfillment_id:
        keyboard_buttons.append(
            [
                InlineKeyboardButton(
                    text=LucienVoice.fulfillment_input_submit_button(),
                    callback_data=BackpackSubmitInputCallback(
                        fulfillment_id=fulfillment_id
                    ).pack(),
                )
            ]
        )
    if "read_chapter" in actions and fulfillment_id:
        keyboard_buttons.append(
            [
                InlineKeyboardButton(
                    text=LucienVoice.backpack_fulfillment_read_chapter_button(),
                    callback_data=BackpackReadChapterCallback(
                        fulfillment_id=fulfillment_id
                    ).pack(),
                )
            ]
        )
    if "view_waitlist" in actions and fulfillment_id:
        keyboard_buttons.append(
            [
                InlineKeyboardButton(
                    text=LucienVoice.backpack_fulfillment_waitlist_button(),
                    callback_data=BackpackViewWaitlistCallback(
                        fulfillment_id=fulfillment_id
                    ).pack(),
                )
            ]
        )
    keyboard_buttons.append(
        [InlineKeyboardButton(text="🔙 Volver", callback_data="backpack_purchases")]
    )
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


# ==================== COMMAND ====================


@router.message(Command("mochila"), lambda m: not is_admin(m.from_user.id))
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


@router.callback_query(F.data == "backpack_menu", lambda cb: not is_admin(cb.from_user.id))
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


@router.callback_query(F.data == "backpack_main", lambda cb: not is_admin(cb.from_user.id))
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


@router.callback_query(F.data == "backpack_rewards", lambda cb: not is_admin(cb.from_user.id))
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
        logger.info(
            f"backpack_handler | callback_rewards | user_id={user_id} | result=shown: {len(rewards)}"
        )

    except Exception as e:
        logger.error(f"backpack_handler | callback_rewards | user_id={user_id} | error={e}")
        await callback.answer("Error al cargar recompensas", show_alert=True)


@router.callback_query(BackpackRewardsPageCallback.filter(), lambda cb: not is_admin(cb.from_user.id))
async def callback_rewards_page(
    callback: CallbackQuery, callback_data: BackpackRewardsPageCallback
):
    """Muestra página de recompensas"""
    user_id = callback.from_user.id
    page = callback_data.page

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
        await callback.answer(LucienVoice.backpack_page_load_error(), show_alert=True)


@router.callback_query(F.data == "backpack_purchases", lambda cb: not is_admin(cb.from_user.id))
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
        logger.info(
            f"backpack_handler | callback_purchases | user_id={user_id} | result=shown: {len(purchases)}"
        )

    except Exception as e:
        logger.error(f"backpack_handler | callback_purchases | user_id={user_id} | error={e}")
        await callback.answer("Error al cargar compras", show_alert=True)


@router.callback_query(BackpackPurchasesPageCallback.filter(), lambda cb: not is_admin(cb.from_user.id))
async def callback_purchases_page(
    callback: CallbackQuery, callback_data: BackpackPurchasesPageCallback
):
    """Muestra página de compras"""
    user_id = callback.from_user.id
    page = callback_data.page

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
        await callback.answer(LucienVoice.backpack_page_load_error(), show_alert=True)


@router.callback_query(F.data == "backpack_vip", lambda cb: not is_admin(cb.from_user.id))
async def callback_vip(callback: CallbackQuery, bot: Bot):
    """Muestra membresías VIP activas"""
    user_id = callback.from_user.id

    try:
        with get_service(BackpackService) as backpack_service:
            result = backpack_service.get_vip_subscriptions_for_backpack(user_id)

        text = LucienVoice.backpack_vip_list(result)
        keyboard = build_vip_keyboard(result)

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
        logger.info(
            f"backpack_handler | callback_vip | user_id={user_id} | result=shown: {len(result)}"
        )

    except Exception as e:
        logger.error(f"backpack_handler | callback_vip | user_id={user_id} | error={e}")
        await callback.answer("Error al cargar VIP", show_alert=True)


@router.callback_query(BackpackRewardDetailCallback.filter(), lambda cb: not is_admin(cb.from_user.id))
async def callback_reward_detail(
    callback: CallbackQuery, callback_data: BackpackRewardDetailCallback
):
    """Muestra detalle de una recompensa"""
    user_id = callback.from_user.id
    history_id = callback_data.history_id

    try:
        backpack_service = BackpackService()
        rewards = backpack_service.get_user_rewards(user_id, limit=100)
        backpack_service.close()

        # Find the specific reward
        reward = None
        for r in rewards:
            if r["history_id"] == history_id:
                reward = r
                break

        if not reward:
            await callback.answer("Recompensa no encontrada", show_alert=True)
            return

        text = LucienVoice.backpack_reward_detail(reward)
        keyboard = build_reward_detail_keyboard(reward)

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
        logger.info(
            f"backpack_handler | callback_reward_detail | user_id={user_id} | reward_id={history_id}"
        )

    except Exception as e:
        logger.error(f"backpack_handler | callback_reward_detail | user_id={user_id} | error={e}")
        await callback.answer("Error al cargar detalle", show_alert=True)


@router.callback_query(BackpackPurchaseDetailCallback.filter(), lambda cb: not is_admin(cb.from_user.id))
async def callback_purchase_detail(
    callback: CallbackQuery, callback_data: BackpackPurchaseDetailCallback
):
    """Muestra detalle de una compra"""
    user_id = callback.from_user.id
    order_id = callback_data.order_id
    product_id = callback_data.product_id

    try:
        backpack_service = BackpackService()
        purchases = backpack_service.get_user_purchases(user_id, limit=100)
        backpack_service.close()

        # Find the specific purchase
        purchase = None
        for p in purchases:
            if p["order_id"] == order_id and p["product_id"] == product_id:
                purchase = p
                break

        if not purchase:
            await callback.answer("Compra no encontrada", show_alert=True)
            return

        text = LucienVoice.backpack_purchase_detail(purchase)

        keyboard = build_purchase_detail_keyboard(purchase)

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
        logger.info(
            f"backpack_handler | callback_purchase_detail | user_id={user_id} | order_id={order_id}"
        )

    except Exception as e:
        logger.error(f"backpack_handler | callback_purchase_detail | user_id={user_id} | error={e}")
        await callback.answer("Error al cargar detalle", show_alert=True)


@router.callback_query(
    BackpackFulfillmentRetryCallback.filter(), lambda cb: not is_admin(cb.from_user.id)
)
async def callback_fulfillment_retry(
    callback: CallbackQuery, callback_data: BackpackFulfillmentRetryCallback
):
    """Reintenta entrega PACKAGE desde mochila."""
    with get_service(BackpackService) as backpack_service:
        ok, msg = await backpack_service.retry_fulfillment_delivery(
            callback.bot, callback.from_user.id, callback_data.fulfillment_id
        )
    toast = LucienVoice.backpack_fulfillment_toast_success(msg)
    await callback.answer(toast[:200], show_alert=not ok)


@router.callback_query(
    BackpackActivateVipCallback.filter(), lambda cb: not is_admin(cb.from_user.id)
)
async def callback_resend_vip_invite(
    callback: CallbackQuery, callback_data: BackpackActivateVipCallback
):
    """Reenvía enlace nativo de acceso VIP."""
    with get_service(BackpackService) as backpack_service:
        ok, msg = await backpack_service.resend_vip_invite_for_fulfillment(
            callback.bot, callback.from_user.id, callback_data.fulfillment_id
        )
    if ok:
        await callback.message.answer(
            msg, reply_markup=vip_access_keyboard(), parse_mode="HTML"
        )
        await callback.answer()
    else:
        await callback.answer(msg, show_alert=True)


@router.callback_query(
    BackpackSubmitInputCallback.filter(), lambda cb: not is_admin(cb.from_user.id)
)
async def callback_submit_input_start(
    callback: CallbackQuery, callback_data: BackpackSubmitInputCallback, state: FSMContext
):
    """Inicia FSM para enviar input pendiente desde mochila."""
    with get_service(BackpackService) as backpack_service:
        ok, msg = backpack_service.get_fulfillment_input_prompt(
            callback.from_user.id, callback_data.fulfillment_id
        )
    if not ok:
        await callback.answer(msg, show_alert=True)
        return
    await state.set_state(BackpackInputStates.awaiting_input)
    await state.update_data(fulfillment_id=callback_data.fulfillment_id)
    await callback.message.answer(msg, parse_mode="HTML")
    await callback.answer()


@router.message(BackpackInputStates.awaiting_input, F.text == "/cancel")
async def cancel_backpack_input(message: Message, state: FSMContext):
    """Cancela captura de input desde mochila."""
    await state.clear()
    await message.answer(LucienVoice.fulfillment_input_cancelled(), parse_mode="HTML")


@router.message(BackpackInputStates.awaiting_input, lambda m: not is_admin(m.from_user.id))
async def process_backpack_input(message: Message, state: FSMContext):
    """Captura input del visitante para USER_INPUT_THEN_MANUAL desde mochila."""
    data = await state.get_data()
    fulfillment_id = data.get("fulfillment_id")
    if not fulfillment_id:
        await state.clear()
        await message.answer(LucienVoice.store_order_not_found(), parse_mode="HTML")
        return
    await state.set_state(BackpackInputStates.validating)
    with get_service(BackpackService) as backpack_service:
        ok, msg = await backpack_service.submit_fulfillment_input(
            message.bot, message.from_user.id, fulfillment_id, message.text or ""
        )
    if ok:
        await state.clear()
    elif msg in (
        LucienVoice.fulfillment_input_already_submitted(),
        LucienVoice.store_order_not_found(),
    ):
        await state.clear()
    else:
        await state.set_state(BackpackInputStates.awaiting_input)
    await message.answer(msg, parse_mode="HTML")


@router.callback_query(
    BackpackReadChapterCallback.filter(), lambda cb: not is_admin(cb.from_user.id)
)
async def callback_read_chapter(
    callback: CallbackQuery, callback_data: BackpackReadChapterCallback
):
    """Abre el nodo narrativo desbloqueado por STORY_UNLOCK."""
    with get_service(BackpackService) as backpack_service:
        detail = backpack_service.get_fulfillment_detail(
            callback.from_user.id, callback_data.fulfillment_id
        )
    if not detail:
        await callback.answer("Compra no encontrada", show_alert=True)
        return
    node_id = (detail.get("auto_result") or {}).get("node_id")
    if not node_id:
        await callback.answer(LucienVoice.story_fragment_unavailable(), show_alert=True)
        return
    from handlers.story_user_handlers import show_node

    with get_service(StoryService) as story_service:
        await show_node(callback, node_id, story_service)


@router.callback_query(
    BackpackViewWaitlistCallback.filter(), lambda cb: not is_admin(cb.from_user.id)
)
async def callback_view_waitlist(
    callback: CallbackQuery, callback_data: BackpackViewWaitlistCallback
):
    """Muestra posición en lista de espera."""
    with get_service(BackpackService) as backpack_service:
        detail = backpack_service.get_fulfillment_detail(
            callback.from_user.id, callback_data.fulfillment_id
        )
    if not detail:
        await callback.answer("Compra no encontrada", show_alert=True)
        return
    position = (detail.get("auto_result") or {}).get("position", "?")
    await callback.message.answer(
        LucienVoice.backpack_fulfillment_waitlist_position(position),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(BackpackDeliverCallback.filter(), lambda cb: not is_admin(cb.from_user.id))
async def callback_deliver_package(callback: CallbackQuery, callback_data: BackpackDeliverCallback):
    """Entrega contenido de un paquete como álbum"""
    user_id = callback.from_user.id
    package_id = callback_data.package_id

    try:
        backpack_service = BackpackService()
        success, message = await backpack_service.deliver_package_content(
            callback.bot, user_id, package_id
        )
        backpack_service.close()

        if success:
            await callback.answer("Contenido entregado", show_alert=False)
        else:
            await callback.answer(message, show_alert=True)

        logger.info(
            f"backpack_handler | callback_deliver_package | user_id={user_id} | package_id={package_id} | result={success}"
        )

    except Exception as e:
        logger.error(f"backpack_handler | callback_deliver_package | user_id={user_id} | error={e}")
        await callback.answer("Error al entregar contenido", show_alert=True)


@router.callback_query(F.data == "backpack_balance", lambda cb: not is_admin(cb.from_user.id))
async def callback_balance(callback: CallbackQuery, bot: Bot):
    """Muestra información del balance de besitos"""
    user_id = callback.from_user.id

    try:
        backpack_service = BackpackService()
        summary = backpack_service.get_backpack_summary(user_id)
        backpack_service.close()

        text = LucienVoice.backpack_besitos_balance_message(summary["besitos_balance"])

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Volver", callback_data="backpack_main")]
            ]
        )

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
        logger.info(
            f"backpack_handler | callback_balance | user_id={user_id} | balance={summary['besitos_balance']}"
        )

    except Exception as e:
        logger.error(f"backpack_handler | callback_balance | user_id={user_id} | error={e}")
        await callback.answer("Error al cargar balance", show_alert=True)
