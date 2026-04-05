"""
Handlers de Tienda para Usuarios - Lucien Bot

Catalogo, carrito, checkout y historial de compras.
"""
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from services.store_service import StoreService
from services.besito_service import BesitoService
from services.package_service import PackageService
from keyboards.inline_keyboards import back_keyboard
import logging

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "shop")
async def shop_menu(callback: CallbackQuery):
    """Menu principal de la tienda"""
    store_service = StoreService()
    besito_service = BesitoService()
    
    user_id = callback.from_user.id
    balance = besito_service.get_balance(user_id)
    cart_count = store_service.get_cart_items_count(user_id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🛍️ Ver catalogo",
            callback_data="store_catalog"
        )],
        [InlineKeyboardButton(
            text="📁 Ver por categorias",
            callback_data="store_categories"
        )],
        [InlineKeyboardButton(
            text=f"🛒 Mi carrito ({cart_count})",
            callback_data="view_cart"
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
        f"💋 Tu saldo: {balance} besitos\n"
        f"🛒 Items en carrito: {cart_count}\n\n"
        f"Que deseas hacer?",
        reply_markup=keyboard
    )
    await callback.answer()


# ==================== CATALOGO ====================

@router.callback_query(F.data == "store_catalog")
async def store_catalog(callback: CallbackQuery):
    """Muestra el catalogo de productos"""
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
    for product in products:
        is_available = product.is_available
        stock_text = "∞" if product.stock == -1 else f"Stock: {product.stock}"

        status_emoji = "📦" if is_available else "🔒"
        text += f"{status_emoji} <b>{product.name}</b>\n"
        text += f"   💰 {product.price} besitos | {stock_text}\n"

        if not is_available:
            text += f"   <i>Agotado temporalmente</i>\n"

        text += f"   {product.description or 'Sin descripcion'}\n\n"

        # Always show detail button
        buttons.append([InlineKeyboardButton(
            text=f"👁️ Ver: {product.name[:20]}",
            callback_data=f"product_detail_{product.id}"
        )])

        if is_available:
            buttons.append([InlineKeyboardButton(
                text=f"➕ Agregar al carrito",
                callback_data=f"add_to_cart_{product.id}"
            )])
        else:
            buttons.append([InlineKeyboardButton(
                text=f"🔒 No disponible",
                callback_data="#"
            )])

    buttons.append([InlineKeyboardButton(
        text="🛒 Ver carrito",
        callback_data="view_cart"
    )])
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
    """Muestra productos de una categoria"""
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

    # Get products that have packages in this category
    packages = package_service.get_packages_by_category(category_id, active_only=True)
    package_ids = [p.id for p in packages]

    # Get all active products and filter by category packages
    all_products = store_service.get_all_products(active_only=True)
    products = [p for p in all_products if p.package_id in package_ids]

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
    for product in products:
        stock_text = "∞" if product.stock == -1 else f"Stock: {product.stock}"
        text += f"📦 <b>{product.name}</b>\n"
        text += f"   💰 {product.price} besitos | {stock_text}\n"
        text += f"   {product.description or 'Sin descripcion'}\n\n"

        buttons.append([InlineKeyboardButton(
            text=f"👁️ Ver: {product.name[:20]}",
            callback_data=f"product_detail_{product.id}"
        )])
        buttons.append([InlineKeyboardButton(
            text=f"➕ Agregar al carrito",
            callback_data=f"add_to_cart_{product.id}"
        )])

    buttons.append([InlineKeyboardButton(
        text="📁 Otras categorias",
        callback_data="store_categories"
    )])
    buttons.append([InlineKeyboardButton(
        text="🛒 Ver carrito",
        callback_data="view_cart"
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
    """Muestra detalle de un producto con preview"""
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

    # Get package files for preview
    package = product.package
    files = package_service.get_package_files(package.id) if package else []
    preview_files = files[:3]  # Show first 3 files as preview

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

    # Check if product is available and user can afford it
    if is_available:
        if balance >= product.price:
            buttons.append([InlineKeyboardButton(
                text="🛒 Agregar al carrito",
                callback_data=f"add_to_cart_{product.id}"
            )])
        else:
            buttons.append([InlineKeyboardButton(
                text=f"❌ Necesitas {product.price - balance} besitos mas",
                callback_data="#"
            )])
    else:
        buttons.append([InlineKeyboardButton(
            text="🔒 Producto agotado",
            callback_data="#"
        )])

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

    # Send preview files if available
    if preview_files:
        await callback.message.delete()

        # Send text first
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")

        # Send preview files
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

        # Send closing message
        await callback.message.answer(
            "<i>...y mas contenido te espera al adquirir este tesoro.</i>",
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(text, reply_markup=keyboard)

    await callback.answer()


@router.callback_query(F.data.startswith("add_to_cart_"))
async def add_to_cart(callback: CallbackQuery):
    """Agrega un producto al carrito"""
    try:
        product_id = int(callback.data.replace("add_to_cart_", ""))
    except ValueError:
        await callback.answer("Error: ID invalido", show_alert=True)
        return

    store_service = StoreService()
    user_id = callback.from_user.id

    success, message = store_service.add_to_cart(user_id, product_id)

    if success:
        await callback.answer(message)
        # Return to product detail instead of catalog
        callback.data = f"product_detail_{product_id}"
        await product_detail(callback)
    else:
        await callback.answer(message, show_alert=True)


# ==================== CARRITO ====================

@router.callback_query(F.data == "view_cart")
async def view_cart(callback: CallbackQuery):
    """Muestra el contenido del carrito"""
    store_service = StoreService()
    besito_service = BesitoService()
    
    user_id = callback.from_user.id
    cart_items = store_service.get_cart_items(user_id)
    balance = besito_service.get_balance(user_id)
    cart_total = store_service.get_cart_total(user_id)
    
    if not cart_items:
        await callback.message.edit_text(
            "🎩 Lucien:\n\n"
            "Tu carrito esta vacio...\n\n"
            "Visita el catalogo para agregar productos.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🛍️ Ver catalogo", callback_data="store_catalog")],
                [InlineKeyboardButton(text="🔙 Volver", callback_data="shop")]
            ])
        )
        await callback.answer()
        return
    
    text = f"🎩 Lucien:\n\n" \
           f"Tu carrito de compras:\n\n" \
           f"💋 Tu saldo: {balance} besitos\n" \
           f"💰 Total: {cart_total} besitos\n\n"
    
    buttons = []
    for item in cart_items:
        product = item.product
        if product:
            text += f"📦 {product.name}\n"
            text += f"   Cantidad: {item.quantity}\n"
            text += f"   Precio: {product.price} besitos c/u\n"
            text += f"   Subtotal: {product.price * item.quantity} besitos\n\n"
            
            buttons.append([InlineKeyboardButton(
                text=f"🗑️ Quitar: {product.name[:20]}",
                callback_data=f"remove_from_cart_{item.id}"
            )])
    
    # Verificar si tiene saldo suficiente
    can_checkout = balance >= cart_total
    
    buttons.append([InlineKeyboardButton(
        text="✅ Proceder al pago" if can_checkout else "❌ Saldo insuficiente",
        callback_data="checkout" if can_checkout else "#"
    )])
    buttons.append([InlineKeyboardButton(
        text="🛍️ Seguir comprando",
        callback_data="store_catalog"
    )])
    buttons.append([InlineKeyboardButton(
        text="🔙 Volver",
        callback_data="shop"
    )])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("remove_from_cart_"))
async def remove_from_cart(callback: CallbackQuery):
    """Elimina un item del carrito"""
    try:
        cart_item_id = int(callback.data.replace("remove_from_cart_", ""))
    except ValueError:
        await callback.answer("Error: ID invalido", show_alert=True)
        return
    
    store_service = StoreService()
    user_id = callback.from_user.id
    
    success = store_service.remove_from_cart(user_id, cart_item_id)
    
    if success:
        await callback.answer("Producto eliminado del carrito")
        await view_cart(callback)
    else:
        await callback.answer("Error al eliminar", show_alert=True)


# ==================== CHECKOUT ====================

@router.callback_query(F.data == "checkout")
async def checkout(callback: CallbackQuery):
    """Muestra resumen antes de confirmar compra"""
    store_service = StoreService()
    besito_service = BesitoService()
    
    user_id = callback.from_user.id
    cart_items = store_service.get_cart_items(user_id)
    balance = besito_service.get_balance(user_id)
    cart_total = store_service.get_cart_total(user_id)
    
    if not cart_items:
        await callback.answer("Tu carrito esta vacio", show_alert=True)
        return
    
    if balance < cart_total:
        await callback.answer("Saldo insuficiente", show_alert=True)
        return
    
    text = "🎩 Lucien:\n\n" \
           "Resumen de tu compra:\n\n"
    
    for item in cart_items:
        product = item.product
        if product:
            text += f"📦 {product.name} x{item.quantity}\n"
            text += f"   {product.price * item.quantity} besitos\n\n"
    
    text += f"💰 Total a pagar: {cart_total} besitos\n"
    text += f"💋 Tu saldo: {balance} besitos\n\n"
    text += "Confirmas la compra?"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Confirmar compra", callback_data="confirm_checkout")],
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="view_cart")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "confirm_checkout")
async def confirm_checkout(callback: CallbackQuery, bot: Bot):
    """Procesa la compra"""
    store_service = StoreService()
    user_id = callback.from_user.id
    
    # Crear orden
    order, error = store_service.create_order(user_id)
    
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
