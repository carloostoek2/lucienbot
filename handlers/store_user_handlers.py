"""
Handlers de Tienda para Usuarios - Lucien Bot

Catalogo y compra directa de productos.
"""
import random
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from services.store_service import StoreService
from services.besito_service import BesitoService
from services.package_service import PackageService
from keyboards.inline_keyboards import back_keyboard
import logging

logger = logging.getLogger(__name__)
router = Router()

# Emojis para botones del catálogo (se asignan aleatoriamente)
CATALOG_EMOJI_LIST = ["✨", "💫", "❤️", "💋", "👅", "👄", "🫦", "🌟"]


def get_random_emoji() -> str:
    """Retorna un emoji aleatorio de la lista"""
    return random.choice(CATALOG_EMOJI_LIST)


class SearchStates(StatesGroup):
    waiting_query = State()


@router.callback_query(F.data == "shop")
async def shop_menu(callback: CallbackQuery):
    """Menu principal de la tienda"""
    besito_service = BesitoService()

    user_id = callback.from_user.id
    balance = besito_service.get_balance(user_id)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🔍 Buscar productos",
            callback_data="store_search"
        )],
        [InlineKeyboardButton(
            text="📁 Ver por categorias",
            callback_data="store_categories"
        )],
        [InlineKeyboardButton(
            text="🛍️ Ver catalogo completo",
            callback_data="store_catalog"
        )],
        [InlineKeyboardButton(
            text="📜 Historial de compras",
            callback_data="purchase_history"
        )],
        [InlineKeyboardButton(
            text="🔙 Volver",
            callback_data="back_to_main"
        )]
    ])

    await callback.message.edit_text(
        f"🎩 Lucien:\n\n"
        f"Bienvenido a la tienda de Diana...\n\n"
        f"💋 Tu saldo: {balance} besitos\n\n"
        f"Que deseas hacer?",
        reply_markup=keyboard
    )
    await callback.answer()


# ==================== CATALOGO ====================

@router.callback_query(F.data == "store_catalog")
async def store_catalog(callback: CallbackQuery):
    """Muestra el catalogo de productos con botones minimalistas"""
    store_service = StoreService()
    products = store_service.get_all_products(active_only=True)

    if not products:
        await callback.message.edit_text(
            "🎩 Lucien:\n\n"
            "La tienda esta vacia en este momento...\n\n"
            "Vuelve mas tarde para ver nuevos productos.",
            reply_markup=back_keyboard("shop")
        )
        await callback.answer()
        return

    text = "🎩 Lucien:\n\n" \
           "Catalogo de productos:\n\n"

    buttons = []
    row = []
    for product in products:
        emoji = get_random_emoji()
        btn_text = f"{emoji} {product.name[:20]}"
        row.append(InlineKeyboardButton(
            text=btn_text,
            callback_data=f"product_detail_{product.id}"
        ))

        # 2 botones por fila
        if len(row) == 2:
            buttons.append(row)
            row = []

    # Agregar fila incompleta si existe
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton(
        text="🔙 Volver",
        callback_data="shop"
    )])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "store_categories")
async def store_categories(callback: CallbackQuery):
    """Muestra categorias disponibles"""
    package_service = PackageService()
    categories = package_service.get_all_categories(active_only=True)

    if not categories:
        await callback.message.edit_text(
            "🎩 <b>Lucien:</b>\n\n"
            "<i>El catalogo aun no tiene secciones...</i>\n\n"
            "Explora todos los productos disponibles.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🛍️ Ver catalogo completo", callback_data="store_catalog")],
                [InlineKeyboardButton(text="🔙 Volver", callback_data="shop")]
            ])
        )
        await callback.answer()
        return

    text = "🎩 <b>Lucien:</b>\n\n" \
           "<i>Las estanterias de Diana...</i>\n\n" \
           "Selecciona una categoria:"

    buttons = []
    for category in categories:
        package_count = len([p for p in category.packages if p.is_active]) if category.packages else 0
        buttons.append([InlineKeyboardButton(
            text=f"📁 {category.name} ({package_count})",
            callback_data=f"store_category_{category.id}"
        )])

    buttons.append([InlineKeyboardButton(
        text="🛍️ Ver todo",
        callback_data="store_catalog"
    )])
    buttons.append([InlineKeyboardButton(
        text="🔙 Volver",
        callback_data="shop"
    )])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("store_category_"))
async def store_category_products(callback: CallbackQuery):
    """Muestra productos de una categoria con botones minimalistas"""
    try:
        category_id = int(callback.data.replace("store_category_", ""))
    except ValueError:
        await callback.answer("Error: ID invalido", show_alert=True)
        return

    package_service = PackageService()
    store_service = StoreService()

    category = package_service.get_category(category_id)
    if not category:
        await callback.answer("Categoria no encontrada", show_alert=True)
        return

    # Get products in this category via service filter
    products = store_service.filter_products(category_id=category_id, active_only=True)

    if not products:
        await callback.message.edit_text(
            f"🎩 <b>Lucien:</b>\n\n"
            f"<i>La estanteria '{category.name}' esta vacia...</i>\n\n"
            f"Vuelve mas tarde para ver nuevos productos.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📁 Otras categorias", callback_data="store_categories")],
                [InlineKeyboardButton(text="🔙 Volver", callback_data="shop")]
            ])
        )
        await callback.answer()
        return

    text = f"🎩 <b>Lucien:</b>\n\n" \
           f"<i>{category.name}...</i>\n\n"

    if category.description:
        text += f"{category.description}\n\n"

    buttons = []
    row = []
    for product in products:
        emoji = get_random_emoji()
        btn_text = f"{emoji} {product.name[:20]}"
        row.append(InlineKeyboardButton(
            text=btn_text,
            callback_data=f"product_detail_{product.id}"
        ))

        # 2 botones por fila
        if len(row) == 2:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton(
        text="📁 Otras categorias",
        callback_data="store_categories"
    )])
    buttons.append([InlineKeyboardButton(
        text="🔙 Volver",
        callback_data="shop"
    )])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("product_detail_"))
async def product_detail(callback: CallbackQuery):
    """Muestra detalle de un producto sin preview automatico"""
    try:
        product_id = int(callback.data.replace("product_detail_", ""))
    except ValueError:
        await callback.answer("Error: ID invalido", show_alert=True)
        return

    store_service = StoreService()
    package_service = PackageService()
    besito_service = BesitoService()

    product = store_service.get_product(product_id)
    if not product:
        await callback.answer("Producto no encontrado", show_alert=True)
        return

    user_id = callback.from_user.id
    balance = besito_service.get_balance(user_id)

    # Get package files count for display
    package = product.package
    files = package_service.get_package_files(package.id) if package else []

    stock_text = "∞" if product.stock == -1 else str(product.stock)
    is_available = product.is_available

    text = f"""🎩 <b>Lucien:</b>

<i>{product.name}</i>

📝 {product.description or 'Un tesoro del reino...'}

💰 <b>Precio:</b> {product.price} besitos
📊 <b>Stock:</b> {stock_text}
📦 <b>Contenido:</b> {len(files)} archivo(s)

💋 Tu saldo: {balance} besitos"""

    # Add guidance on earning besitos if balance is insufficient
    if balance < product.price:
        text += f"\n\n<i>¿Necesitas mas besitos?</i>\n"
        text += f"• Reclama tu regalo diario\n"
        text += f"• Reacciona a publicaciones\n"
        text += f"• Completa misiones\n"
        text += f"• Subscribete VIP para mas beneficios"

    # Build keyboard
    buttons = []
    row = []

    # First row: Preview button and Buy button (if available)
    row.append(InlineKeyboardButton(
        text="👁️ Preview",
        callback_data=f"product_preview_{product.id}"
    ))

    if is_available:
        if balance >= product.price:
            row.append(InlineKeyboardButton(
                text="💋 Comprar ahora",
                callback_data=f"direct_buy_{product.id}"
            ))
        else:
            row.append(InlineKeyboardButton(
                text=f"❌ Necesitas {product.price - balance} besitos mas",
                callback_data="#"
            ))
    else:
        row.append(InlineKeyboardButton(
            text="🔒 Agotado",
            callback_data="#"
        ))

    buttons.append(row)

    # Navigation row
    buttons.append([InlineKeyboardButton(
        text="🛍️ Ver mas productos",
        callback_data="store_catalog"
    )])
    buttons.append([InlineKeyboardButton(
        text="📁 Por categorias",
        callback_data="store_categories"
    )])
    buttons.append([InlineKeyboardButton(
        text="🔙 Volver a la tienda",
        callback_data="shop"
    )])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("product_preview_"))
async def product_preview(callback: CallbackQuery):
    """Envía el preview del producto bajo demanda y vuelve a mostrar la tarjeta"""
    try:
        product_id = int(callback.data.replace("product_preview_", ""))
    except ValueError:
        await callback.answer("Error: ID invalido", show_alert=True)
        return

    store_service = StoreService()
    package_service = PackageService()
    besito_service = BesitoService()

    product = store_service.get_product(product_id)
    if not product:
        await callback.answer("Producto no encontrado", show_alert=True)
        return

    package = product.package
    files = package_service.get_package_files(package.id) if package else []
    preview_files = files[:3]

    user_id = callback.from_user.id
    balance = besito_service.get_balance(user_id)
    stock_text = "∞" if product.stock == -1 else str(product.stock)
    is_available = product.is_available

    # Enviar preview si hay archivos
    if preview_files:
        for file_entry in preview_files:
            try:
                if file_entry.file_type == "photo":
                    await callback.message.answer_photo(
                        photo=file_entry.file_id,
                        caption="<i>Preview del contenido...</i>",
                        parse_mode="HTML"
                    )
                elif file_entry.file_type == "video":
                    await callback.message.answer_video(
                        video=file_entry.file_id,
                        caption="<i>Preview del contenido...</i>",
                        parse_mode="HTML"
                    )
            except Exception as e:
                logger.error(f"Error enviando preview: {e}")
                continue

    # Construir mensaje con la tarjeta del producto y botones
    text = f"""🎩 <b>Lucien:</b>

<i>{product.name}</i>

📝 {product.description or 'Un tesoro del reino...'}

💰 <b>Precio:</b> {product.price} besitos
📊 <b>Stock:</b> {stock_text}
📦 <b>Contenido:</b> {len(files)} archivo(s)

💋 Tu saldo: {balance} besitos"""

    if balance < product.price:
        text += f"\n\n<i>¿Necesitas mas besitos?</i>\n"
        text += f"• Reclama tu regalo diario\n"
        text += f"• Reacciona a publicaciones\n"
        text += f"• Completa misiones\n"
        text += f"• Subscribete VIP para mas beneficios"

    buttons = []
    row = []

    # Botón de comprar
    if is_available:
        if balance >= product.price:
            row.append(InlineKeyboardButton(
                text="💋 Comprar ahora",
                callback_data=f"direct_buy_{product.id}"
            ))
        else:
            row.append(InlineKeyboardButton(
                text=f"❌ Necesitas {product.price - balance} besitos mas",
                callback_data="#"
            ))
    else:
        row.append(InlineKeyboardButton(
            text="🔒 Agotado",
            callback_data="#"
        ))

    buttons.append(row)

    buttons.append([InlineKeyboardButton(
        text="🛍️ Ver mas productos",
        callback_data="store_catalog"
    )])
    buttons.append([InlineKeyboardButton(
        text="🔙 Volver a la tienda",
        callback_data="shop"
    )])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.answer(
        text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer("Preview enviado!", show_alert=False)


# ==================== COMPRA DIRECTA ====================

@router.callback_query(F.data.startswith("direct_buy_"))
async def direct_buy(callback: CallbackQuery):
    """Muestra confirmacion de compra directa"""
    try:
        product_id = int(callback.data.replace("direct_buy_", ""))
    except ValueError:
        await callback.answer("Error: ID invalido", show_alert=True)
        return

    store_service = StoreService()
    besito_service = BesitoService()

    product = store_service.get_product(product_id)
    if not product:
        await callback.answer("Producto no encontrado", show_alert=True)
        return

    user_id = callback.from_user.id
    balance = besito_service.get_balance(user_id)

    if balance < product.price:
        await callback.answer("Saldo insuficiente", show_alert=True)
        return

    text = f"🎩 <b>Lucien:</b>\n\n" \
           f"<i>¿Confirmar compra?</i>\n\n" \
           f"📦 <b>{product.name}</b>\n" \
           f"💰 <b>Precio:</b> {product.price} besitos\n\n" \
           f"💋 Tu saldo: {balance} besitos\n" \
           f"📊 Después de compra: {balance - product.price} besitos"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="✅ Confirmar",
            callback_data=f"confirm_direct_buy_{product_id}"
        )],
        [InlineKeyboardButton(
            text="❌ Cancelar",
            callback_data=f"product_detail_{product_id}"
        )]
    ])

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_direct_buy_"))
async def confirm_direct_buy(callback: CallbackQuery, bot: Bot):
    """Procesa la compra directa"""
    try:
        product_id = int(callback.data.replace("confirm_direct_buy_", ""))
    except ValueError:
        await callback.answer("Error: ID invalido", show_alert=True)
        return

    store_service = StoreService()
    user_id = callback.from_user.id

    # Crear orden directa
    order, error = store_service.direct_purchase(user_id, product_id)

    if error:
        await callback.answer(error, show_alert=True)
        return

    # Completar orden
    success, message = await store_service.complete_order(bot, order.id)

    if success:
        await callback.message.edit_text(
            f"🎩 Lucien:\n\n"
            f"✅ Compra completada exitosamente!\n\n"
            f"{message}\n\n"
            f"Los productos han sido enviados a tu chat privado.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🛍️ Seguir comprando", callback_data="store_catalog")],
                [InlineKeyboardButton(text="📜 Ver historial", callback_data="purchase_history")],
                [InlineKeyboardButton(text="🔙 Menu principal", callback_data="back_to_main")]
            ])
        )
        await callback.answer("Compra exitosa!")
    else:
        await callback.answer(f"Error: {message}", show_alert=True)


# ==================== HISTORIAL DE COMPRAS ====================

@router.callback_query(F.data == "purchase_history")
async def purchase_history(callback: CallbackQuery):
    """Muestra el historial de compras del usuario"""
    store_service = StoreService()
    user_id = callback.from_user.id
    
    orders = store_service.get_user_orders(user_id, limit=10)
    
    if not orders:
        await callback.message.edit_text(
            "🎩 Lucien:\n\n"
            "Aun no tienes compras registradas...\n\n"
            "Visita la tienda para hacer tu primera compra.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🛍️ Ir a la tienda", callback_data="shop")],
                [InlineKeyboardButton(text="🔙 Volver", callback_data="shop")]
            ])
        )
        await callback.answer()
        return
    
    text = "🎩 Lucien:\n\n" \
           "Tu historial de compras:\n\n"
    
    for order in orders:
        status_emoji = {
            "completed": "✅",
            "pending": "⏳",
            "cancelled": "❌"
        }.get(order.status.value, "❓")
        
        date_str = order.created_at.strftime("%d/%m/%Y") if order.created_at else "?"
        
        text += f"{status_emoji} Orden #{order.id} - {date_str}\n"
        text += f"   Items: {order.total_items} | Total: {order.total_price} besitos\n\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛍️ Ir a la tienda", callback_data="shop")],
            [InlineKeyboardButton(text="🔙 Volver", callback_data="shop")]
        ])
    )
    await callback.answer()


# ==================== BUSQUEDA Y FILTROS ====================

@router.callback_query(F.data == "store_search")
async def store_search_start(callback: CallbackQuery, state: FSMContext):
    """Inicia busqueda de productos"""
    await callback.message.edit_text(
        "🎩 <b>Lucien:</b>\n\n"
        "<i>¿Que tesoro buscas?</i>\n\n"
        "Escribe el nombre o una palabra clave del producto:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="shop")]
        ])
    )
    await state.set_state(SearchStates.waiting_query)
    await callback.answer()


@router.message(SearchStates.waiting_query, F.text)
async def process_search_query(message: Message, state: FSMContext):
    """Procesa busqueda de productos"""
    query = message.text.strip()
    if len(query) < 2:
        await message.answer(
            "Por favor escribe al menos 2 caracteres para buscar.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Cancelar", callback_data="shop")]
            ])
        )
        return

    store_service = StoreService()
    products = store_service.search_products(query, active_only=True)

    if not products:
        await message.answer(
            f"🎩 <b>Lucien:</b>\n\n"
            f"<i>No encontre tesoros para '{query}'...</i>\n\n"
            f"Intenta con otra palabra o explora el catalogo.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🛍️ Ver catalogo", callback_data="store_catalog")],
                [InlineKeyboardButton(text="🔙 Volver", callback_data="shop")]
            ])
        )
        await state.clear()
        return

    # Show search results
    text = f"🎩 <b>Lucien:</b>\n\n" \
           f"<i>Resultados para '{query}':</i>\n\n" \
           f"{len(products)} tesoro(s) encontrado(s)\n\n"

    buttons = []
    row = []
    for product in products:
        emoji = get_random_emoji()
        btn_text = f"{emoji} {product.name[:20]}"
        row.append(InlineKeyboardButton(
            text=btn_text,
            callback_data=f"product_detail_{product.id}"
        ))

        if len(row) == 2:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton(
        text="🔍 Nueva busqueda",
        callback_data="store_search"
    )])
    buttons.append([InlineKeyboardButton(
        text="🔙 Volver",
        callback_data="shop"
    )])

    await message.answer(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await state.clear()


@router.callback_query(F.data == "store_filters")
async def store_filters(callback: CallbackQuery):
    """Muestra opciones de filtrado"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="💰 Por precio: Menor a mayor",
            callback_data="filter_price_asc"
        )],
        [InlineKeyboardButton(
            text="💰 Por precio: Mayor a menor",
            callback_data="filter_price_desc"
        )],
        [InlineKeyboardButton(
            text="📦 Solo disponibles",
            callback_data="filter_in_stock"
        )],
        [InlineKeyboardButton(
            text="🆕 Mas recientes",
            callback_data="filter_recent"
        )],
        [InlineKeyboardButton(text="🔙 Volver", callback_data="shop")]
    ])

    await callback.message.edit_text(
        "🎩 <b>Lucien:</b>\n\n"
        "<i>Filtrar tesoros...</i>\n\n"
        "Selecciona como ordenar los productos:",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "filter_price_asc")
async def filter_price_asc(callback: CallbackQuery):
    """Muestra productos ordenados por precio ascendente"""
    store_service = StoreService()
    products = store_service.get_all_products(active_only=True)
    products.sort(key=lambda p: p.price)

    await show_filtered_products(callback, products, "Precio: menor a mayor")


@router.callback_query(F.data == "filter_price_desc")
async def filter_price_desc(callback: CallbackQuery):
    """Muestra productos ordenados por precio descendente"""
    store_service = StoreService()
    products = store_service.get_all_products(active_only=True)
    products.sort(key=lambda p: p.price, reverse=True)

    await show_filtered_products(callback, products, "Precio: mayor a menor")


@router.callback_query(F.data == "filter_in_stock")
async def filter_in_stock(callback: CallbackQuery):
    """Muestra solo productos disponibles"""
    store_service = StoreService()
    products = store_service.get_available_products()

    await show_filtered_products(callback, products, "Solo disponibles")


@router.callback_query(F.data == "filter_recent")
async def filter_recent(callback: CallbackQuery):
    """Muestra productos mas recientes"""
    store_service = StoreService()
    products = store_service.get_all_products(active_only=True)
    # Already sorted by created_at desc from service

    await show_filtered_products(callback, products, "Mas recientes")


async def show_filtered_products(callback: CallbackQuery, products: list, filter_name: str):
    """Helper para mostrar productos filtrados"""
    if not products:
        await callback.message.edit_text(
            "🎩 <b>Lucien:</b>\n\n"
            "<i>No hay tesoros que coincidan...</i>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Volver", callback_data="shop")]
            ])
        )
        await callback.answer()
        return

    text = f"🎩 <b>Lucien:</b>\n\n" \
           f"<i>Filtrado: {filter_name}</i>\n\n" \
           f"{len(products)} tesoro(s)\n\n"

    buttons = []
    row = []
    for product in products[:10]:  # Limit to 10 for display
        emoji = get_random_emoji()
        btn_text = f"{emoji} {product.name[:20]}"
        row.append(InlineKeyboardButton(
            text=btn_text,
            callback_data=f"product_detail_{product.id}"
        ))

        if len(row) == 2:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    if len(products) > 10:
        text += f"<i>...y {len(products) - 10} mas</i>\n\n"

    buttons.append([InlineKeyboardButton(
        text="🔙 Volver",
        callback_data="shop"
    )])

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()
