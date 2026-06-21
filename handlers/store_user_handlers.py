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
            [InlineKeyboardButton(text="🔍 Buscar productos", callback_data="store_search")],
            [InlineKeyboardButton(text="📁 Ver por categorias", callback_data="store_categories")],
            [
                InlineKeyboardButton(
                    text=LucienVoice.store_tier_menu_button(),
                    callback_data="store_tiers",
                )
            ],
            [InlineKeyboardButton(text="🛍️ Ver catalogo completo", callback_data="store_catalog")],
            [
                InlineKeyboardButton(
                    text="📜 Historial de compras", callback_data="purchase_history"
                )
            ],
            [InlineKeyboardButton(text="🔙 Volver", callback_data="back_to_main")],
        ]
    )

    await callback.message.edit_text(
        f"🎩 Lucien:\n\n"
        f"Bienvenido a la tienda de Diana...\n\n"
        f"💋 Tu saldo: {balance} besitos\n\n"
        f"Que deseas hacer?",
        reply_markup=keyboard,
    )
    await callback.answer()


# ==================== CATALOGO ====================


@router.callback_query(F.data == "store_tiers", lambda cb: not is_admin(cb.from_user.id))
async def store_tiers_menu(callback: CallbackQuery):
    """Menú de tiers del catálogo."""
    with get_service(StoreService) as store_service:
        tiers = store_service.get_all_tiers()
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
    buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="shop")])
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
        await callback.answer("Tier no encontrado", show_alert=True)
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
            "🎩 Lucien:\n\n"
            "La tienda esta vacia en este momento...\n\n"
            "Vuelve mas tarde para ver nuevos productos.",
            reply_markup=back_keyboard("shop"),
        )
        await callback.answer()
        return

    text = "🎩 Lucien:\n\nCatalogo de productos:\n\n"

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

    buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="shop")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "store_categories", lambda cb: not is_admin(cb.from_user.id))
async def store_categories(callback: CallbackQuery):
    """Muestra categorias disponibles"""
    with get_service(StoreService) as store_service:
        categories = store_service.get_categories_for_shop(active_only=True)

    if not categories:
        await callback.message.edit_text(
            "🎩 <b>Lucien:</b>\n\n"
            "<i>El catalogo aun no tiene secciones...</i>\n\n"
            "Explora todos los productos disponibles.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🛍️ Ver catalogo completo", callback_data="store_catalog"
                        )
                    ],
                    [InlineKeyboardButton(text="🔙 Volver", callback_data="shop")],
                ]
            ),
        )
        await callback.answer()
        return

    text = "🎩 <b>Lucien:</b>\n\n<i>Las estanterias de Diana...</i>\n\nSelecciona una categoria:"

    buttons = []
    for category in categories:
        package_count = (
            len([p for p in category.packages if p.is_active]) if category.packages else 0
        )
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"📁 {category.name} ({package_count})",
                    callback_data=StoreCategoryCallback(category_id=category.id).pack(),
                )
            ]
        )

    buttons.append([InlineKeyboardButton(text="🛍️ Ver todo", callback_data="store_catalog")])
    buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="shop")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(StoreCategoryCallback.filter(), lambda cb: not is_admin(cb.from_user.id))
async def store_category_products(callback: CallbackQuery, callback_data: StoreCategoryCallback):
    """Muestra productos de una categoria con botones minimalistas"""
    category_id = callback_data.category_id

    with get_service(StoreService) as store_service:
        category = store_service.get_category_for_shop(category_id)
        if not category:
            await callback.answer("Categoria no encontrada", show_alert=True)
            return
        products = store_service.filter_products(category_id=category_id, active_only=True)

    if not products:
        await callback.message.edit_text(
            f"🎩 <b>Lucien:</b>\n\n"
            f"<i>La estanteria '{category.name}' esta vacia...</i>\n\n"
            f"Vuelve mas tarde para ver nuevos productos.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="📁 Otras categorias", callback_data="store_categories"
                        )
                    ],
                    [InlineKeyboardButton(text="🔙 Volver", callback_data="shop")],
                ]
            ),
        )
        await callback.answer()
        return

    text = f"🎩 <b>Lucien:</b>\n\n<i>{category.name}...</i>\n\n"

    if category.description:
        text += f"{category.description}\n\n"

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
        [InlineKeyboardButton(text="📁 Otras categorias", callback_data="store_categories")]
    )
    buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="shop")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(ProductDetailCallback.filter(), lambda cb: not is_admin(cb.from_user.id))
async def product_detail(callback: CallbackQuery, callback_data: ProductDetailCallback):
    """Muestra detalle de un producto sin preview automatico"""
    product_id = callback_data.product_id

    with get_service(StoreService) as store_service:
        ctx = store_service.get_product_detail_context(product_id, callback.from_user.id)
        if not ctx:
            await callback.answer("Producto no encontrado", show_alert=True)
            return
    product = ctx["product"]
    balance = ctx["balance"]
    effective_price = ctx.get("effective_price", product.price)
    file_count = ctx["file_count"]
    stock_text = "∞" if product.stock == -1 else str(product.stock)
    is_available = product.is_available and ctx.get("monthly_cap_available", True)
    text = LucienVoice.store_product_detail(
        product.name,
        product.description or "",
        effective_price if effective_price != product.price else product.price,
        ctx.get("tier_name", ""),
    )
    if effective_price < product.price:
        text += f"\n🏷️ <b>Precio lista:</b> {product.price} besitos · <i>descuento activo</i>"
    text += f"\n📊 <b>Stock:</b> {stock_text}\n📦 <b>Contenido:</b> {file_count} archivo(s)"
    text += f"\n\n💋 Tu saldo: {balance} besitos"
    if not ctx.get("monthly_cap_available", True):
        text += f"\n\n⚠️ {LucienVoice.store_monthly_cap_reached(product.name)}"

    # Add guidance on earning besitos if balance is insufficient
    if balance < effective_price:
        text += LucienVoice.store_need_more_besitos_hint()
        text += "• Reclama tu regalo diario\n"
        text += "• Reacciona a publicaciones\n"
        text += "• Completa misiones\n"
        text += "• Subscribete VIP para mas beneficios"

    # Build keyboard
    buttons = []
    row = []

    # First row: Preview button and Buy button (if available)
    row.append(
        InlineKeyboardButton(
            text="👁️ Preview", callback_data=ProductPreviewCallback(product_id=product.id).pack()
        )
    )

    if is_available:
        if balance >= effective_price:
            row.append(
                InlineKeyboardButton(
                    text="💋 Comprar ahora",
                    callback_data=DirectBuyCallback(product_id=product.id).pack(),
                )
            )
        else:
            row.append(
                InlineKeyboardButton(
                    text=f"❌ Necesitas {effective_price - balance} besitos mas",
                    callback_data="#",
                )
            )
    else:
        row.append(InlineKeyboardButton(text="🔒 Agotado", callback_data="#"))

    buttons.append(row)

    # Navigation row
    buttons.append(
        [InlineKeyboardButton(text="🛍️ Ver mas productos", callback_data="store_catalog")]
    )
    buttons.append(
        [InlineKeyboardButton(text="📁 Por categorias", callback_data="store_categories")]
    )
    buttons.append([InlineKeyboardButton(text="🔙 Volver a la tienda", callback_data="shop")])

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
            await callback.answer("Producto no encontrado", show_alert=True)
            return
        preview_files = store_service.get_preview_files_for_product(product_id, limit=1)
    product = ctx["product"]
    balance = ctx["balance"]
    effective_price = ctx.get("effective_price", product.price)
    file_count = ctx["file_count"]
    stock_text = "∞" if product.stock == -1 else str(product.stock)
    is_available = product.is_available and ctx.get("monthly_cap_available", True)

    # Enviar preview si hay archivos
    preview_errors = []
    if preview_files:
        for file_entry in preview_files:
            try:
                if file_entry.file_type == "photo":
                    await callback.message.answer_photo(
                        photo=file_entry.file_id,
                        caption="<i>Preview del contenido...</i>",
                        parse_mode="HTML",
                    )
                elif file_entry.file_type == "video":
                    await callback.message.answer_video(
                        video=file_entry.file_id,
                        caption="<i>Preview del contenido...</i>",
                        parse_mode="HTML",
                    )
            except Exception as e:
                error_msg = f"Error enviando preview (file_id={file_entry.file_id[:20]}..., type={file_entry.file_type}): {e}"
                logger.error(error_msg)
                preview_errors.append(file_entry.file_type)
                continue

    # Construir mensaje con la tarjeta del producto y botones
    text = f"""🎩 <b>Lucien:</b>

<i>{product.name}</i>

📝 {product.description or "Un tesoro del reino..."}

💰 <b>Precio:</b> {effective_price} besitos
📊 <b>Stock:</b> {stock_text}
📦 <b>Contenido:</b> {file_count} archivo(s)

💋 Tu saldo: {balance} besitos"""

    if balance < effective_price:
        text += LucienVoice.store_need_more_besitos_hint()
        text += "• Reclama tu regalo diario\n"
        text += "• Reacciona a publicaciones\n"
        text += "• Completa misiones\n"
        text += "• Subscribete VIP para mas beneficios"

    buttons = []
    row = []
    if is_available:
        if balance >= effective_price:
            row.append(
                InlineKeyboardButton(
                    text=LucienVoice.store_acquire_button(),
                    callback_data=DirectBuyCallback(product_id=product.id).pack(),
                )
            )
        else:
            row.append(
                InlineKeyboardButton(
                    text=f"❌ Necesitas {effective_price - balance} besitos mas",
                    callback_data="#",
                )
            )
    else:
        row.append(InlineKeyboardButton(text="🔒 Agotado", callback_data="#"))
    buttons.append(row)
    buttons.append([InlineKeyboardButton(text="🛍️ Ver mas productos", callback_data="store_tiers")])
    buttons.append([InlineKeyboardButton(text="🔙 Volver a la tienda", callback_data="shop")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer("Preview enviado!", show_alert=False)


# ==================== COMPRA DIRECTA ====================


@router.callback_query(DirectBuyCallback.filter(), lambda cb: not is_admin(cb.from_user.id))
async def direct_buy(callback: CallbackQuery, callback_data: DirectBuyCallback):
    """Muestra confirmacion de compra directa"""
    product_id = callback_data.product_id

    with get_service(StoreService) as store_service:
        product = store_service.get_product(product_id)
        if not product:
            await callback.answer("Producto no encontrado", show_alert=True)
            return
        user_id = callback.from_user.id
        cap_err = store_service._check_monthly_cap_for_product(product_id)
        if cap_err:
            await callback.answer(cap_err, show_alert=True)
            return
        balance = store_service.get_shop_balance_display(user_id)
        effective_price = store_service.get_effective_price(user_id, product.price)

    if balance < effective_price:
        await callback.answer("Saldo insuficiente", show_alert=True)
        return

    text = (
        f"🎩 <b>Lucien:</b>\n\n"
        f"{LucienVoice.store_confirm_purchase_prompt()}"
        f"📦 <b>{product.name}</b>\n"
        f"💰 <b>Precio:</b> {effective_price} besitos\n\n"
        f"💋 Tu saldo: {balance} besitos\n"
        f"{LucienVoice.store_after_purchase_balance_line(balance - effective_price)}"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Confirmar",
                    callback_data=ConfirmDirectBuyCallback(product_id=product_id).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Cancelar",
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
                [InlineKeyboardButton(text="🔙 Menu principal", callback_data="back_to_main")],
            ]
        ),
        parse_mode="HTML",
    )
    await callback.answer("Compra exitosa!")

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
            "🎩 Lucien:\n\n"
            "Aun no tienes compras registradas...\n\n"
            "Visita la tienda para hacer tu primera compra.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🛍️ Ir a la tienda", callback_data="shop")],
                    [InlineKeyboardButton(text="🔙 Volver", callback_data="shop")],
                ]
            ),
        )
        await callback.answer()
        return

    text = "🎩 Lucien:\n\nTu historial de compras:\n\n"

    for order in orders:
        status_emoji = {"completed": "✅", "pending": "⏳", "cancelled": "❌"}.get(
            order.status.value, "❓"
        )

        date_str = order.created_at.strftime("%d/%m/%Y") if order.created_at else "?"

        text += f"{status_emoji} Orden #{order.id} - {date_str}\n"
        text += f"   Items: {order.total_items} | Total: {order.total_price} besitos\n\n"

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🛍️ Ir a la tienda", callback_data="shop")],
                [InlineKeyboardButton(text="🔙 Volver", callback_data="shop")],
            ]
        ),
    )
    await callback.answer()


# ==================== BUSQUEDA Y FILTROS ====================


@router.callback_query(F.data == "store_search", lambda cb: not is_admin(cb.from_user.id))
async def store_search_start(callback: CallbackQuery, state: FSMContext):
    """Inicia busqueda de productos"""
    await callback.message.edit_text(
        "🎩 <b>Lucien:</b>\n\n"
        f"{LucienVoice.store_search_prompt()}"
        "Escribe el nombre o una palabra clave del producto:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="❌ Cancelar", callback_data="shop")]]
        ),
    )
    await state.set_state(SearchStates.waiting_query)
    await callback.answer()


@router.message(SearchStates.waiting_query, F.text, lambda msg: not is_admin(msg.from_user.id))
async def process_search_query(message: Message, state: FSMContext):
    """Procesa busqueda de productos"""
    query = message.text.strip()
    if len(query) < 2:
        await message.answer(
            "Por favor escribe al menos 2 caracteres para buscar.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="❌ Cancelar", callback_data="shop")]]
            ),
        )
        return

    with get_service(StoreService) as store_service:
        products = store_service.search_products(query, active_only=True)

    if not products:
        await message.answer(
            f"🎩 <b>Lucien:</b>\n\n"
            f"<i>No encontre tesoros para '{query}'...</i>\n\n"
            f"Intenta con otra palabra o explora el catalogo.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🛍️ Ver catalogo", callback_data="store_catalog")],
                    [InlineKeyboardButton(text="🔙 Volver", callback_data="shop")],
                ]
            ),
        )
        await state.clear()
        return

    # Show search results
    text = (
        f"🎩 <b>Lucien:</b>\n\n"
        f"<i>Resultados para '{query}':</i>\n\n"
        f"{len(products)} tesoro(s) encontrado(s)\n\n"
    )

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

    buttons.append([InlineKeyboardButton(text="🔍 Nueva busqueda", callback_data="store_search")])
    buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="shop")])

    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await state.clear()


@router.callback_query(F.data == "store_filters", lambda cb: not is_admin(cb.from_user.id))
async def store_filters(callback: CallbackQuery):
    """Muestra opciones de filtrado"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💰 Por precio: Menor a mayor", callback_data="filter_price_asc"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💰 Por precio: Mayor a menor", callback_data="filter_price_desc"
                )
            ],
            [InlineKeyboardButton(text="📦 Solo disponibles", callback_data="filter_in_stock")],
            [InlineKeyboardButton(text="🆕 Mas recientes", callback_data="filter_recent")],
            [InlineKeyboardButton(text="🔙 Volver", callback_data="shop")],
        ]
    )

    await callback.message.edit_text(
        "🎩 <b>Lucien:</b>\n\n<i>Filtrar tesoros...</i>\n\nSelecciona como ordenar los productos:",
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(F.data == "filter_price_asc", lambda cb: not is_admin(cb.from_user.id))
async def filter_price_asc(callback: CallbackQuery):
    """Muestra productos ordenados por precio ascendente"""
    with get_service(StoreService) as store_service:
        products = store_service.get_all_products(active_only=True)
        products.sort(key=lambda p: p.price)

        await show_filtered_products(callback, products, "Precio: menor a mayor")


@router.callback_query(F.data == "filter_price_desc", lambda cb: not is_admin(cb.from_user.id))
async def filter_price_desc(callback: CallbackQuery):
    """Muestra productos ordenados por precio descendente"""
    with get_service(StoreService) as store_service:
        products = store_service.get_all_products(active_only=True)
        products.sort(key=lambda p: p.price, reverse=True)

        await show_filtered_products(callback, products, "Precio: mayor a menor")


@router.callback_query(F.data == "filter_in_stock", lambda cb: not is_admin(cb.from_user.id))
async def filter_in_stock(callback: CallbackQuery):
    """Muestra solo productos disponibles"""
    with get_service(StoreService) as store_service:
        products = store_service.get_available_products()

        await show_filtered_products(callback, products, "Solo disponibles")


@router.callback_query(F.data == "filter_recent", lambda cb: not is_admin(cb.from_user.id))
async def filter_recent(callback: CallbackQuery):
    """Muestra productos mas recientes"""
    with get_service(StoreService) as store_service:
        products = store_service.get_all_products(active_only=True)
        # Already sorted by created_at desc from service

        await show_filtered_products(callback, products, "Mas recientes")


async def show_filtered_products(callback: CallbackQuery, products: list, filter_name: str):
    """Helper para mostrar productos filtrados"""
    if not products:
        await callback.message.edit_text(
            "🎩 <b>Lucien:</b>\n\n<i>No hay tesoros que coincidan...</i>",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="🔙 Volver", callback_data="shop")]]
            ),
        )
        await callback.answer()
        return

    text = f"🎩 <b>Lucien:</b>\n\n<i>Filtrado: {filter_name}</i>\n\n{len(products)} tesoro(s)\n\n"

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

    if len(products) > 10:
        text += f"<i>...y {len(products) - 10} mas</i>\n\n"

    buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="shop")])

    await callback.message.edit_text(
        text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()
