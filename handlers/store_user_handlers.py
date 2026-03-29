"""
Handlers de Tienda para Usuarios - Lucien Bot

Catalogo, carrito, checkout y historial de compras.
"""
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from services.store_service import StoreService
from services.besito_service import BesitoService
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
    products = store_service.get_available_products()
    
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
        stock_text = "∞" if product.stock == -1 else f"Stock: {product.stock}"
        text += f"📦 {product.name}\n"
        text += f"   💰 {product.price} besitos | {stock_text}\n"
        text += f"   {product.description or 'Sin descripcion'}\n\n"
        
        buttons.append([InlineKeyboardButton(
            text=f"➕ Agregar: {product.name[:25]}",
            callback_data=f"add_to_cart_{product.id}"
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
        # Volver al catalogo
        await store_catalog(callback)
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
