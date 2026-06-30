"""
Handlers de Tienda para Usuarios - Lucien Bot

Catalogo y compra directa de productos.
"""

import logging
import random

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from keyboards.callback_data import (
    ConfirmDirectBuyCallback,
    DirectBuyCallback,
    ProductDetailCallback,
    ProductPreviewCallback,
    StoreCategoryCallback,
    StoreTierCallback,
)
from keyboards.inline_keyboards import back_keyboard
from services import get_service
from handlers.states.store_fulfillment_states import PurchaseInputStates
from services.store_service import StoreService
from utils.admin import is_admin
from utils.lucien_voice import LucienVoice

logger = logging.getLogger(__name__)
router = Router()

# Emojis para botones del catálogo (se asignan aleatoriamente)
CATALOG_EMOJI_LIST = ["✨", "💫", "❤️", "💋", "👅", "👄", "🫦", "🌟"]


def get_random_emoji() -> str:
    """Retorna un emoji aleatorio de la lista"""
    return random.choice(CATALOG_EMOJI_LIST)


def _build_product_buttons(
    product,
    balance: int,
    effective_price: int,
    is_available: bool,
    *,
    include_preview: bool = True,
    more_products_callback: str = "store_catalog",
    tier_unlocked: bool = True,
    tier_lock_remaining: int = 0,
) -> list[list[InlineKeyboardButton]]:
    """Construye filas de botones para detalle/preview de producto."""
    row = []
    if include_preview:
        row.append(
            InlineKeyboardButton(
                text=LucienVoice.store_button_preview(),
                callback_data=ProductPreviewCallback(product_id=product.id).pack(),
            )
        )
    if not tier_unlocked:
        row.append(
            InlineKeyboardButton(
                text=LucienVoice.store_button_tier_locked(tier_lock_remaining),
                callback_data=DirectBuyCallback(product_id=product.id).pack(),
            )
        )
    elif is_available:
        if balance >= effective_price:
            row.append(
                InlineKeyboardButton(
                    text=LucienVoice.store_button_buy(),
                    callback_data=DirectBuyCallback(product_id=product.id).pack(),
                )
            )
        else:
            row.append(
                InlineKeyboardButton(
                    text=LucienVoice.store_button_insufficient(effective_price - balance),
                    callback_data="#",
                )
            )
    else:
        row.append(InlineKeyboardButton(text=LucienVoice.store_button_sold_out(), callback_data="#"))
    buttons = [row]
    if include_preview:
        buttons.append(
            [InlineKeyboardButton(text=LucienVoice.store_button_more_products(), callback_data=more_products_callback)]
        )
        buttons.append(
            [InlineKeyboardButton(text=LucienVoice.store_button_by_categories(), callback_data="store_tiers")]
        )
    else:
        buttons.append(
            [InlineKeyboardButton(text=LucienVoice.store_button_more_products(), callback_data=more_products_callback)]
        )
    buttons.append(
        [InlineKeyboardButton(text=LucienVoice.store_button_back_to_shop(), callback_data="shop")]
    )
    return buttons


def _product_detail_card_and_buttons(
    ctx: dict,
    *,
    include_preview: bool = True,
    more_products_callback: str = "store_catalog",
) -> tuple[str, list[list[InlineKeyboardButton]]]:
    """Construye tarjeta y botones de detalle desde contexto unificado del servicio."""
    product = ctx["product"]
    balance = ctx["balance"]
    effective_price = ctx.get("effective_price", product.price)
    stock_text = "∞" if product.stock == -1 else str(product.stock)
    is_available = product.is_available and ctx.get("monthly_cap_available", True)
    display_price = effective_price if effective_price != product.price else product.price
    list_price = product.price if effective_price < product.price else None
    text = LucienVoice.store_product_detail_card(
        product.name,
        product.description or "",
        display_price,
        balance,
        stock_text,
        ctx["file_count"],
        ctx.get("tier_name", ""),
        list_price=list_price,
        monthly_cap_available=ctx.get("monthly_cap_available", True),
        tier_lock_message=ctx.get("tier_lock_message"),
    )
    buttons = _build_product_buttons(
        product,
        balance,
        effective_price,
        is_available,
        include_preview=include_preview,
        more_products_callback=more_products_callback,
        tier_unlocked=ctx.get("tier_unlocked", True),
        tier_lock_remaining=ctx.get("tier_lock_remaining", 0),
    )
    return text, buttons


class SearchStates(StatesGroup):
    waiting_query = State()


@router.callback_query(F.data == "shop", lambda cb: not is_admin(cb.from_user.id))
async def shop_menu(callback: CallbackQuery):
    """Menu principal de la tienda"""
    user_id = callback.from_user.id
    with get_service(StoreService) as store_service:
        balance = store_service.get_shop_balance_display(user_id)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=LucienVoice.store_button_search(), callback_data="store_search")],
            [InlineKeyboardButton(text=LucienVoice.store_button_categories(), callback_data="store_tiers")],
            [InlineKeyboardButton(text=LucienVoice.store_button_catalog(), callback_data="store_catalog")],
            [
                InlineKeyboardButton(
                    text=LucienVoice.store_button_history(), callback_data="purchase_history"
                )
            ],
            [InlineKeyboardButton(text=LucienVoice.store_button_back(), callback_data="back_to_main")],
        ]
    )

    await callback.message.edit_text(
        LucienVoice.store_menu_intro(balance),
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    await callback.answer()


# ==================== CATALOGO ====================


@router.callback_query(F.data == "store_tiers", lambda cb: not is_admin(cb.from_user.id))
async def store_tiers_menu(callback: CallbackQuery):
    """Menú de tiers del catálogo (estanterías Kinky: IMPULSO → MÍTICO)."""
    with get_service(StoreService) as store_service:
        tiers = store_service.get_tiers_for_shop(active_only=True)
    if not tiers:
        await callback.answer(LucienVoice.store_catalog_unavailable(), show_alert=True)
        return
    buttons = [
        [
            InlineKeyboardButton(
                text=f"{t.name} ({t.price_min}-{t.price_max} 💋)",
                callback_data=StoreTierCallback(tier_id=t.id).pack(),
            )
        ]
        for t in tiers
    ]
    buttons.append([InlineKeyboardButton(text=LucienVoice.store_button_back(), callback_data="shop")])
    await callback.message.edit_text(
        LucienVoice.store_tier_menu_intro(),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(StoreTierCallback.filter(), lambda cb: not is_admin(cb.from_user.id))
async def store_tier_products(callback: CallbackQuery, callback_data: StoreTierCallback):
    """Lista productos de un tier."""
    with get_service(StoreService) as store_service:
        tiers = {t.id: t for t in store_service.get_all_tiers()}
        tier = tiers.get(callback_data.tier_id)
        products = store_service.get_products_by_tier(callback_data.tier_id)
    if not tier:
        await callback.answer(LucienVoice.store_tier_not_found(), show_alert=True)
        return
    intro_fn = getattr(LucienVoice, f"store_tier_{tier.slug}_intro", None)
    intro = intro_fn() if intro_fn else LucienVoice.store_tier_intro_for_slug(tier.slug)
    buttons = []
    for product in products:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{product.name} — {product.price} 💋",
                    callback_data=ProductDetailCallback(product_id=product.id).pack(),
                )
            ]
        )
    buttons.append(
        [
            InlineKeyboardButton(
                text=LucienVoice.store_back_to_tier_button("TIENDA"),
                callback_data="store_tiers",
            )
        ]
    )
    await callback.message.edit_text(
        intro,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "store_catalog", lambda cb: not is_admin(cb.from_user.id))
async def store_catalog(callback: CallbackQuery):
    """Muestra el catalogo de productos con botones minimalistas"""
    with get_service(StoreService) as store_service:
        products = store_service.get_all_products(active_only=True)

    if not products:
        await callback.message.edit_text(
            LucienVoice.store_catalog_empty(),
            reply_markup=back_keyboard("shop"),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    text = LucienVoice.store_catalog_intro()

    buttons = []
    row = []
    for product in products:
        emoji = get_random_emoji()
        btn_text = f"{emoji} {product.name[:20]}"
        row.append(
            InlineKeyboardButton(
                text=btn_text, callback_data=ProductDetailCallback(product_id=product.id).pack()
            )
        )

        # 2 botones por fila
        if len(row) == 2:
            buttons.append(row)
            row = []

    # Agregar fila incompleta si existe
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton(text=LucienVoice.store_button_back(), callback_data="shop")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "store_categories", lambda cb: not is_admin(cb.from_user.id))
async def store_categories(callback: CallbackQuery):
    """Backward compat: callback antiguo redirige al menú de tiers del catálogo."""
    await store_tiers_menu(callback)


@router.callback_query(StoreCategoryCallback.filter(), lambda cb: not is_admin(cb.from_user.id))
async def store_category_products(callback: CallbackQuery, callback_data: StoreCategoryCallback):
    """Muestra productos de una categoria con botones minimalistas"""
    category_id = callback_data.category_id

    with get_service(StoreService) as store_service:
        category = store_service.get_category_for_shop(category_id)
        if not category:
            await callback.answer(LucienVoice.store_category_not_found(), show_alert=True)
            return
        products = store_service.filter_products(category_id=category_id, active_only=True)

    if not products:
        await callback.message.edit_text(
            LucienVoice.store_category_empty(category.name),
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=LucienVoice.store_button_other_categories(),
                            callback_data="store_tiers",
                        )
                    ],
                    [InlineKeyboardButton(text=LucienVoice.store_button_back(), callback_data="shop")],
                ]
            ),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    text = LucienVoice.store_category_header(category.name, category.description or "")

    buttons = []
    row = []
    for product in products:
        emoji = get_random_emoji()
        btn_text = f"{emoji} {product.name[:20]}"
        row.append(
            InlineKeyboardButton(
                text=btn_text, callback_data=ProductDetailCallback(product_id=product.id).pack()
            )
        )

        # 2 botones por fila
        if len(row) == 2:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    buttons.append(
        [InlineKeyboardButton(text=LucienVoice.store_button_other_categories(), callback_data="store_tiers")]
    )
    buttons.append([InlineKeyboardButton(text=LucienVoice.store_button_back(), callback_data="shop")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(ProductDetailCallback.filter(), lambda cb: not is_admin(cb.from_user.id))
async def product_detail(callback: CallbackQuery, callback_data: ProductDetailCallback):
    """Muestra detalle de un producto sin preview automatico"""
    product_id = callback_data.product_id

    with get_service(StoreService) as store_service:
        ctx = store_service.get_product_detail_context(product_id, callback.from_user.id)
        if not ctx:
            await callback.answer(LucienVoice.store_product_not_found(), show_alert=True)
            return
    can_preview = ctx.get("can_preview", False)
    text, buttons = _product_detail_card_and_buttons(ctx, include_preview=can_preview)
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(ProductPreviewCallback.filter(), lambda cb: not is_admin(cb.from_user.id))
async def product_preview(callback: CallbackQuery, callback_data: ProductPreviewCallback):
    """Envía el preview del producto bajo demanda y vuelve a mostrar la tarjeta"""
    product_id = callback_data.product_id

    with get_service(StoreService) as store_service:
        ctx = store_service.get_product_detail_context(product_id, callback.from_user.id)
        if not ctx:
            await callback.answer(LucienVoice.store_product_not_found(), show_alert=True)
            return
        if not ctx.get("can_preview", False):
            await callback.answer(LucienVoice.store_no_preview(), show_alert=True)
            return
        preview_files = store_service.get_preview_files_for_product(product_id, limit=1)
    if preview_files:
        for file_entry in preview_files:
            try:
                if file_entry.file_type == "photo":
                    await callback.message.answer_photo(
                        photo=file_entry.file_id,
                        caption=LucienVoice.store_preview_caption(),
                        parse_mode="HTML",
                    )
                elif file_entry.file_type == "video":
                    await callback.message.answer_video(
                        video=file_entry.file_id,
                        caption=LucienVoice.store_preview_caption(),
                        parse_mode="HTML",
                    )
            except Exception as e:
                error_msg = (
                    f"Error enviando preview (file_id={file_entry.file_id[:20]}..., "
                    f"type={file_entry.file_type}): {e}"
                )
                logger.error(error_msg)
                continue

    text, buttons = _product_detail_card_and_buttons(
        ctx,
        include_preview=False,
        more_products_callback="store_tiers",
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer(LucienVoice.store_preview_sent_alert(), show_alert=False)


# ==================== COMPRA DIRECTA ====================


@router.callback_query(DirectBuyCallback.filter(), lambda cb: not is_admin(cb.from_user.id))
async def direct_buy(callback: CallbackQuery, callback_data: DirectBuyCallback):
    """Muestra confirmacion de compra directa"""
    product_id = callback_data.product_id

    with get_service(StoreService) as store_service:
        product = store_service.get_product(product_id)
        if not product:
            await callback.answer(LucienVoice.store_product_not_found(), show_alert=True)
            return
        user_id = callback.from_user.id
        cap_err = store_service._check_monthly_cap_for_product(product_id)
        if cap_err:
            await callback.answer(cap_err, show_alert=True)
            return
        tier_err = store_service.check_tier_purchase_gate(user_id, product_id)
        if tier_err:
            await callback.answer(tier_err, show_alert=True)
            return
        balance = store_service.get_shop_balance_display(user_id)
        effective_price = store_service.get_effective_price(user_id, product.price)

    if balance < effective_price:
        await callback.answer(LucienVoice.store_balance_insufficient_alert(), show_alert=True)
        return

    text = LucienVoice.store_confirm_purchase_message(
        product.name, effective_price, balance, balance - effective_price
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=LucienVoice.store_button_confirm(),
                    callback_data=ConfirmDirectBuyCallback(product_id=product_id).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=LucienVoice.store_button_cancel(),
                    callback_data=ProductDetailCallback(product_id=product_id).pack(),
                )
            ],
        ]
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(ConfirmDirectBuyCallback.filter(), lambda cb: not is_admin(cb.from_user.id))
async def confirm_direct_buy(
    callback: CallbackQuery,
    callback_data: ConfirmDirectBuyCallback,
    bot: Bot,
    state: FSMContext,
):
    """Procesa la compra directa"""
    product_id = callback_data.product_id

    with get_service(StoreService) as store_service:
        user_id = callback.from_user.id
        order, summaries, error = await store_service.purchase_and_complete(
            bot, user_id, product_id
        )
        if error:
            await callback.answer(error, show_alert=True)
            return
        charge_amount = store_service._get_order_charge_amount(user_id, order)

    post_msg = LucienVoice.store_purchase_completed(charge_amount)
    if summaries:
        summary = summaries[0]
        kind = summary.get("kind", "package")
        status = summary.get("status", "")
        if kind == "vip_grant":
            if status == "failed" or (
                status == "auto_running" and summary.get("vip_activated")
            ):
                post_msg = LucienVoice.store_vip_purchase_pending_backpack()
            else:
                post_msg = LucienVoice.store_purchase_completed(charge_amount)
        else:
            post_msg = LucienVoice.fulfillment_post_purchase_message_for_kind(
                kind, summary.get("product_name", "")
            )

    await callback.message.edit_text(
        post_msg,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=LucienVoice.store_go_backpack_button(),
                        callback_data="backpack_purchases",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=LucienVoice.store_continue_shopping_button(),
                        callback_data="store_tiers",
                    )
                ],
                [InlineKeyboardButton(text=LucienVoice.store_button_back_main(), callback_data="back_to_main")],
            ]
        ),
        parse_mode="HTML",
    )
    await callback.answer(LucienVoice.store_purchase_success_alert())

    pending = next(
        (s for s in summaries if s.get("status") == "pending_input" and s.get("fulfillment_id")),
        None,
    )
    if pending:
        await state.set_state(PurchaseInputStates.awaiting_input)
        await state.update_data(fulfillment_id=pending["fulfillment_id"])


@router.message(PurchaseInputStates.awaiting_input, F.text == "/cancel")
async def cancel_purchase_input(message: Message, state: FSMContext):
    """Cancela captura de input de compra."""
    await state.clear()
    await message.answer(LucienVoice.fulfillment_input_cancelled(), parse_mode="HTML")


@router.message(PurchaseInputStates.awaiting_input, lambda m: not is_admin(m.from_user.id))
async def process_purchase_input(message: Message, state: FSMContext):
    """Captura input del visitante para USER_INPUT_THEN_MANUAL."""
    data = await state.get_data()
    fulfillment_id = data.get("fulfillment_id")
    if not fulfillment_id:
        await state.clear()
        await message.answer(LucienVoice.store_order_not_found(), parse_mode="HTML")
        return
    await state.set_state(PurchaseInputStates.validating)
    with get_service(StoreService) as store_service:
        ok, msg = await store_service.submit_purchase_input(
            message.bot, fulfillment_id, message.from_user.id, message.text or ""
        )
    if ok:
        await state.clear()
    elif msg in (
        LucienVoice.fulfillment_input_already_submitted(),
        LucienVoice.store_order_not_found(),
    ):
        await state.clear()
    else:
        await state.set_state(PurchaseInputStates.awaiting_input)
    await message.answer(msg, parse_mode="HTML")


# ==================== HISTORIAL DE COMPRAS ====================


@router.callback_query(F.data == "purchase_history", lambda cb: not is_admin(cb.from_user.id))
async def purchase_history(callback: CallbackQuery):
    """Muestra el historial de compras del usuario"""
    with get_service(StoreService) as store_service:
        user_id = callback.from_user.id

        orders = store_service.get_user_orders(user_id, limit=10)

    if not orders:
        await callback.message.edit_text(
            LucienVoice.store_purchase_history_empty(),
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=LucienVoice.store_button_go_shop(), callback_data="shop")],
                    [InlineKeyboardButton(text=LucienVoice.store_button_back(), callback_data="shop")],
                ]
            ),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    text = LucienVoice.store_purchase_history_header() + "\n\n"
    for order in orders:
        status_emoji = {"completed": "✅", "pending": "⏳", "cancelled": "❌"}.get(
            order.status.value, "❓"
        )
        date_str = order.created_at.strftime("%d/%m/%Y") if order.created_at else "?"
        text += LucienVoice.store_purchase_history_item(
            order.id, date_str, order.total_items, order.total_price, status_emoji
        )

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=LucienVoice.store_button_go_shop(), callback_data="shop")],
                [InlineKeyboardButton(text=LucienVoice.store_button_back(), callback_data="shop")],
            ]
        ),
        parse_mode="HTML",
    )
    await callback.answer()


# ==================== BUSQUEDA Y FILTROS ====================


@router.callback_query(F.data == "store_search", lambda cb: not is_admin(cb.from_user.id))
async def store_search_start(callback: CallbackQuery, state: FSMContext):
    """Inicia busqueda de productos"""
    await callback.message.edit_text(
        LucienVoice.store_search_start_message(),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=LucienVoice.store_button_cancel(), callback_data="shop")]
            ]
        ),
        parse_mode="HTML",
    )
    await state.set_state(SearchStates.waiting_query)
    await callback.answer()


@router.message(SearchStates.waiting_query, F.text, lambda msg: not is_admin(msg.from_user.id))
async def process_search_query(message: Message, state: FSMContext):
    """Procesa busqueda de productos"""
    query = message.text.strip()
    if len(query) < 2:
        await message.answer(
            LucienVoice.store_search_min_chars(),
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=LucienVoice.store_button_cancel(), callback_data="shop")]
                ]
            ),
        )
        return

    with get_service(StoreService) as store_service:
        products = store_service.search_products(query, active_only=True)

    if not products:
        await message.answer(
            LucienVoice.store_search_no_results(query),
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=LucienVoice.store_button_catalog(), callback_data="store_catalog")],
                    [InlineKeyboardButton(text=LucienVoice.store_button_back(), callback_data="shop")],
                ]
            ),
            parse_mode="HTML",
        )
        await state.clear()
        return

    text = LucienVoice.store_search_results(query, len(products)) + "\n\n"

    buttons = []
    row = []
    for product in products:
        emoji = get_random_emoji()
        btn_text = f"{emoji} {product.name[:20]}"
        row.append(
            InlineKeyboardButton(
                text=btn_text, callback_data=ProductDetailCallback(product_id=product.id).pack()
            )
        )

        if len(row) == 2:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton(text=LucienVoice.store_button_new_search(), callback_data="store_search")])
    buttons.append([InlineKeyboardButton(text=LucienVoice.store_button_back(), callback_data="shop")])

    await message.answer(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML",
    )
    await state.clear()


@router.callback_query(F.data == "store_filters", lambda cb: not is_admin(cb.from_user.id))
async def store_filters(callback: CallbackQuery):
    """Muestra opciones de filtrado"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=LucienVoice.store_filter_price_asc(), callback_data="filter_price_asc"
                )
            ],
            [
                InlineKeyboardButton(
                    text=LucienVoice.store_filter_price_desc(), callback_data="filter_price_desc"
                )
            ],
            [InlineKeyboardButton(text=LucienVoice.store_filter_in_stock(), callback_data="filter_in_stock")],
            [InlineKeyboardButton(text=LucienVoice.store_filter_recent(), callback_data="filter_recent")],
            [InlineKeyboardButton(text=LucienVoice.store_button_back(), callback_data="shop")],
        ]
    )

    await callback.message.edit_text(
        LucienVoice.store_filters_intro(),
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "filter_price_asc", lambda cb: not is_admin(cb.from_user.id))
async def filter_price_asc(callback: CallbackQuery):
    """Muestra productos ordenados por precio ascendente"""
    with get_service(StoreService) as store_service:
        products = store_service.get_all_products(active_only=True)
        products.sort(key=lambda p: p.price)

        await show_filtered_products(callback, products, LucienVoice.store_filter_label_price_asc())


@router.callback_query(F.data == "filter_price_desc", lambda cb: not is_admin(cb.from_user.id))
async def filter_price_desc(callback: CallbackQuery):
    """Muestra productos ordenados por precio descendente"""
    with get_service(StoreService) as store_service:
        products = store_service.get_all_products(active_only=True)
        products.sort(key=lambda p: p.price, reverse=True)

        await show_filtered_products(callback, products, LucienVoice.store_filter_label_price_desc())


@router.callback_query(F.data == "filter_in_stock", lambda cb: not is_admin(cb.from_user.id))
async def filter_in_stock(callback: CallbackQuery):
    """Muestra solo productos disponibles"""
    with get_service(StoreService) as store_service:
        products = store_service.get_available_products()

        await show_filtered_products(callback, products, LucienVoice.store_filter_label_in_stock())


@router.callback_query(F.data == "filter_recent", lambda cb: not is_admin(cb.from_user.id))
async def filter_recent(callback: CallbackQuery):
    """Muestra productos mas recientes"""
    with get_service(StoreService) as store_service:
        products = store_service.get_all_products(active_only=True)
        # Already sorted by created_at desc from service

        await show_filtered_products(callback, products, LucienVoice.store_filter_label_recent())


async def show_filtered_products(callback: CallbackQuery, products: list, filter_name: str):
    """Helper para mostrar productos filtrados"""
    if not products:
        await callback.message.edit_text(
            LucienVoice.store_filter_empty(),
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text=LucienVoice.store_button_back(), callback_data="shop")]]
            ),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    overflow = max(0, len(products) - 10)
    text = LucienVoice.store_filter_results(filter_name, min(len(products), 10), overflow) + "\n\n"

    buttons = []
    row = []
    for product in products[:10]:  # Limit to 10 for display
        emoji = get_random_emoji()
        btn_text = f"{emoji} {product.name[:20]}"
        row.append(
            InlineKeyboardButton(
                text=btn_text, callback_data=ProductDetailCallback(product_id=product.id).pack()
            )
        )

        if len(row) == 2:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton(text=LucienVoice.store_button_back(), callback_data="shop")])

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML",
    )
    await callback.answer()
