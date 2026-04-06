"""
Handlers de Tienda para Administradores - Lucien Bot

Gestion de productos y estadisticas de la tienda.
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config.settings import bot_config
from services.store_service import StoreService
from services.package_service import PackageService
import logging

logger = logging.getLogger(__name__)
router = Router()


# Estados para FSM
class ProductWizardStates(StatesGroup):
    waiting_name = State()
    waiting_description = State()
    selecting_package = State()
    waiting_price = State()
    waiting_stock = State()
    confirming = State()


class ProductRestockStates(StatesGroup):
    waiting_amount = State()
    waiting_threshold = State()


def is_admin(user_id: int) -> bool:
    return user_id in bot_config.ADMIN_IDS


# ==================== MENU PRINCIPAL ====================

@router.callback_query(F.data == "admin_store", lambda cb: is_admin(cb.from_user.id))
async def admin_store_menu(callback: CallbackQuery):
    """Menu de administracion de tienda"""
    store_service = StoreService()
    stats = store_service.get_store_stats()
    low_stock = store_service.get_low_stock_products()
    out_of_stock = store_service.get_out_of_stock_products()

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Crear producto", callback_data="create_product")],
        [InlineKeyboardButton(text="📋 Ver productos", callback_data="list_products")],
        [InlineKeyboardButton(text="⚠️ Alertas de stock", callback_data="stock_alerts")],
        [InlineKeyboardButton(text="📊 Estadisticas", callback_data="store_stats")],
        [InlineKeyboardButton(text="📁 Gestionar categorías", callback_data="manage_categories")],
        [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_gamification")]
    ])

    text = (
        f"🎩 Lucien:\n\n"
        f"Administracion de la tienda...\n\n"
        f"📊 Resumen:\n"
        f"   • Productos activos: {stats['available_products']}\n"
        f"   • Total productos: {stats['total_products']}\n"
        f"   • Ordenes completadas: {stats['completed_orders']}\n"
        f"   • Besitos gastados: {stats['total_besitos_spent']}\n"
    )

    if low_stock:
        text += f"   ⚠️ Stock bajo: {len(low_stock)} productos\n"
    if out_of_stock:
        text += f"   🚨 Agotados: {len(out_of_stock)} productos\n"

    text += f"\nQue deseas hacer?"

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


# ==================== ALERTAS DE STOCK ====================

@router.callback_query(F.data == "stock_alerts", lambda cb: is_admin(cb.from_user.id))
async def stock_alerts(callback: CallbackQuery):
    """Muestra alertas de stock"""
    store_service = StoreService()

    low_stock = store_service.get_low_stock_products()
    out_of_stock = store_service.get_out_of_stock_products()

    if not low_stock and not out_of_stock:
        await callback.message.edit_text(
            "🎩 <b>Lucien:</b>\n\n"
            "<i>Todos los tesoros están bien abastecidos...</i>\n\n"
            "No hay alertas de stock.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_store")]
            ])
        )
        await callback.answer()
        return

    text = "🎩 <b>Lucien:</b>\n\n<i>Alertas de inventario...</i>\n\n"
    buttons = []

    if out_of_stock:
        text += "🚨 <b>Productos agotados:</b>\n"
        for product in out_of_stock:
            text += f"   ❌ {product.name}\n"
            buttons.append([InlineKeyboardButton(
                text=f"📝 Reabastecer: {product.name[:25]}",
                callback_data=f"restock_product_{product.id}"
            )])
        text += "\n"

    if low_stock:
        text += "⚠️ <b>Stock bajo:</b>\n"
        for product in low_stock:
            stock_status = f"{product.stock}/{product.low_stock_threshold}"
            text += f"   ⚠️ {product.name} ({stock_status})\n"
            buttons.append([InlineKeyboardButton(
                text=f"📝 Reabastecer: {product.name[:25]}",
                callback_data=f"restock_product_{product.id}"
            )])

    buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="admin_store")])

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()


@router.callback_query(F.data.startswith("restock_product_"), lambda cb: is_admin(cb.from_user.id))
async def restock_product(callback: CallbackQuery, state: FSMContext):
    """Inicia reabastecimiento de producto"""
    try:
        product_id = int(callback.data.replace("restock_product_", ""))
    except ValueError:
        await callback.answer("ID invalido", show_alert=True)
        return

    store_service = StoreService()
    product = store_service.get_product(product_id)

    if not product:
        await callback.answer("Producto no encontrado", show_alert=True)
        return

    await state.update_data(product_id=product_id, product_name=product.name)

    stock_text = "Ilimitado" if product.stock == -1 else str(product.stock)

    await callback.message.edit_text(
        f"🎩 <b>Lucien:</b>\n\n"
        f"<i>Reabastecer tesoro...</i>\n\n"
        f"📦 <b>{product.name}</b>\n"
        f"📊 Stock actual: {stock_text}\n\n"
        f"Indica la cantidad a agregar:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="♾️ Ilimitado", callback_data="restock_unlimited")],
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="stock_alerts")]
        ])
    )
    await state.set_state(ProductRestockStates.waiting_amount)
    await callback.answer()


@router.callback_query(ProductRestockStates.waiting_amount, F.data == "restock_unlimited")
async def restock_unlimited(callback: CallbackQuery, state: FSMContext):
    """Establece stock ilimitado"""
    data = await state.get_data()
    product_id = data.get('product_id')

    store_service = StoreService()
    store_service.update_product(product_id, stock=-1)

    await callback.message.edit_text(
        f"🎩 <b>Lucien:</b>\n\n"
        f"✅ Stock actualizado a ilimitado.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Volver a alertas", callback_data="stock_alerts")]
        ])
    )
    await state.clear()
    await callback.answer()


@router.message(ProductRestockStates.waiting_amount)
async def process_restock_amount(message: Message, state: FSMContext):
    """Procesa cantidad de reabastecimiento"""
    try:
        amount = int(message.text.strip())
        if amount < 0:
            raise ValueError("Debe ser 0 o mayor")
    except ValueError:
        await message.answer("Indica un numero valido (0 o mayor).")
        return

    data = await state.get_data()
    product_id = data.get('product_id')
    product_name = data.get('product_name')

    store_service = StoreService()
    product = store_service.get_product(product_id)

    if not product:
        await message.answer("Producto no encontrado.")
        await state.clear()
        return

    # Calcular nuevo stock
    current_stock = 0 if product.stock == -1 else product.stock
    new_stock = current_stock + amount

    store_service.update_product(product_id, stock=new_stock)

    await message.answer(
        f"🎩 <b>Lucien:</b>\n\n"
        f"✅ <b>{product_name}</b> reabastecido.\n\n"
        f"📊 Stock anterior: {current_stock}\n"
        f"📦 Cantidad agregada: {amount}\n"
        f"📊 Nuevo stock: {new_stock}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Volver a alertas", callback_data="stock_alerts")]
        ])
    )
    await state.clear()


# ==================== WIZARD CREAR PRODUCTO ====================

@router.callback_query(F.data == "create_product", lambda cb: is_admin(cb.from_user.id))
async def create_product_start(callback: CallbackQuery, state: FSMContext):
    """Inicia wizard de creacion de producto"""
    await callback.message.edit_text(
        "🎩 Lucien:\n\n"
        "Vamos a crear un nuevo producto...\n\n"
        "Paso 1 de 5: Nombre del producto\n\n"
        "Indica un nombre descriptivo:\n"
        "Ejemplo: Pack Fotos Exclusivas Marzo",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_store")]
        ])
    )
    await state.set_state(ProductWizardStates.waiting_name)
    await callback.answer()


@router.message(ProductWizardStates.waiting_name)
async def process_product_name(message: Message, state: FSMContext):
    """Procesa nombre del producto"""
    name = message.text.strip()
    if len(name) < 3:
        await message.answer("El nombre debe tener al menos 3 caracteres.")
        return

    await state.update_data(name=name)
    await message.answer(
        "🎩 Lucien:\n\n"
        "Paso 2 de 5: Descripcion\n\n"
        "Escribe una descripcion (opcional):\n"
        "Ejemplo: Un pack de 10 fotos exclusivas\n\n"
        "O envia /skip para omitir.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_store")]
        ])
    )
    await state.set_state(ProductWizardStates.waiting_description)


@router.message(ProductWizardStates.waiting_description)
async def process_product_description(message: Message, state: FSMContext):
    """Procesa descripcion del producto"""
    description = None if message.text == "/skip" else message.text.strip()
    await state.update_data(description=description)

    # Mostrar paquetes disponibles
    package_service = PackageService()
    packages = package_service.get_available_packages_for_store()

    if not packages:
        await message.answer(
            "🎩 Lucien:\n\n"
            "No hay paquetes disponibles para la tienda.\n\n"
            "Crea un paquete primero desde 'Gestionar paquetes'.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_store")]
            ])
        )
        await state.clear()
        return

    buttons = []
    for pkg in packages:
        stock_text = "∞" if pkg.store_stock == -1 else str(pkg.store_stock)
        buttons.append([InlineKeyboardButton(
            text=f"{pkg.name} ({pkg.file_count} archivos, stock: {stock_text})",
            callback_data=f"select_pkg_product_{pkg.id}"
        )])

    buttons.append([InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_store")])

    await message.answer(
        "🎩 Lucien:\n\n"
        "Paso 3 de 5: Seleccionar paquete\n\n"
        "Elige el paquete que se vendera:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await state.set_state(ProductWizardStates.selecting_package)


@router.callback_query(ProductWizardStates.selecting_package, F.data.startswith("select_pkg_product_"))
async def select_package_for_product(callback: CallbackQuery, state: FSMContext):
    """Selecciona paquete para el producto"""
    try:
        package_id = int(callback.data.replace("select_pkg_product_", ""))
    except ValueError:
        await callback.answer("ID invalido", show_alert=True)
        return

    await state.update_data(package_id=package_id)

    await callback.message.edit_text(
        "🎩 Lucien:\n\n"
        "Paso 4 de 5: Precio\n\n"
        "Indica el precio en besitos:\n"
        "Ejemplo: 100",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_store")]
        ])
    )
    await state.set_state(ProductWizardStates.waiting_price)
    await callback.answer()


@router.message(ProductWizardStates.waiting_price)
async def process_product_price(message: Message, state: FSMContext):
    """Procesa precio del producto"""
    try:
        price = int(message.text.strip())
        if price < 1:
            raise ValueError("Debe ser mayor a 0")
    except ValueError:
        await message.answer("Por favor indica un numero valido mayor a 0.")
        return

    await state.update_data(price=price)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="♾️ Ilimitado", callback_data="product_stock_unlimited")],
        [InlineKeyboardButton(text="📦 Limitado", callback_data="product_stock_limited")],
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_store")]
    ])

    await message.answer(
        "🎩 Lucien:\n\n"
        "Paso 5 de 5: Stock\n\n"
        "Configura el stock disponible:",
        reply_markup=keyboard
    )
    await state.set_state(ProductWizardStates.waiting_stock)


@router.callback_query(ProductWizardStates.waiting_stock, F.data == "product_stock_unlimited")
async def product_stock_unlimited(callback: CallbackQuery, state: FSMContext):
    """Stock ilimitado"""
    await state.update_data(stock=-1)
    await show_product_confirmation(callback, state)
    await callback.answer()


@router.callback_query(ProductWizardStates.waiting_stock, F.data == "product_stock_limited")
async def product_stock_limited(callback: CallbackQuery, state: FSMContext):
    """Pide cantidad limitada"""
    await callback.message.edit_text(
        "🎩 Lucien:\n\n"
        "Indica la cantidad de unidades disponibles:\n"
        "Ejemplo: 50",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_store")]
        ])
    )
    await callback.answer()


@router.message(ProductWizardStates.waiting_stock)
async def process_product_stock(message: Message, state: FSMContext):
    """Procesa stock del producto"""
    try:
        stock = int(message.text.strip())
        if stock < 0:
            raise ValueError("Debe ser 0 o mayor")
    except ValueError:
        await message.answer("Indica un numero valido (0 o mayor).")
        return

    await state.update_data(stock=stock)
    await show_product_confirmation(message, state)


async def show_product_confirmation(target, state: FSMContext):
    """Muestra confirmacion del producto"""
    data = await state.get_data()

    name = data.get('name', '')
    description = data.get('description', 'Sin descripcion')
    price = data.get('price', 0)
    stock = data.get('stock', -1)
    stock_text = "Ilimitado" if stock == -1 else str(stock)

    text = f"🎩 Lucien:\n\n" \
           f"Resumen del producto:\n\n" \
           f"📦 {name}\n" \
           f"📝 {description}\n" \
           f"💰 Precio: {price} besitos\n" \
           f"📊 Stock: {stock_text}\n\n" \
           f"Crear este producto?"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Crear", callback_data="confirm_create_product")],
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_store")]
    ])

    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=keyboard)
    else:
        await target.answer(text, reply_markup=keyboard)

    await state.set_state(ProductWizardStates.confirming)


@router.callback_query(ProductWizardStates.confirming, F.data == "confirm_create_product")
async def confirm_create_product(callback: CallbackQuery, state: FSMContext):
    """Crea el producto"""
    data = await state.get_data()
    store_service = StoreService()

    try:
        product = store_service.create_product(
            name=data.get('name'),
            description=data.get('description'),
            package_id=data.get('package_id'),
            price=data.get('price'),
            stock=data.get('stock', -1),
            created_by=callback.from_user.id
        )

        await callback.message.edit_text(
            f"🎩 Lucien:\n\n"
            f"✅ Producto creado exitosamente!\n\n"
            f"📦 {product.name}\n"
            f"💰 {product.price} besitos\n\n"
            f"El producto ya esta disponible en la tienda.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_store")]
            ])
        )
        logger.info(f"Producto creado: {product.name} por admin {callback.from_user.id}")

    except Exception as e:
        logger.error(f"Error creando producto: {e}")
        await callback.message.edit_text(
            "Error al crear el producto.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_store")]
            ])
        )

    await state.clear()
    await callback.answer()


# ==================== LISTAR PRODUCTOS ====================

@router.callback_query(F.data == "list_products", lambda cb: is_admin(cb.from_user.id))
async def list_products(callback: CallbackQuery):
    """Lista todos los productos"""
    store_service = StoreService()
    products = store_service.get_all_products(active_only=False)

    if not products:
        await callback.message.edit_text(
            "No hay productos registrados.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_store")]
            ])
        )
        await callback.answer()
        return

    text = "🎩 Lucien:\n\nProductos registrados:\n\n"
    buttons = []

    for product in products:
        status = "✅" if product.is_active else "❌"

        # Stock indicator
        if product.stock == -1:
            stock_emoji = "♾️"
            stock_text = "∞"
        elif product.stock == 0:
            stock_emoji = "🚨"
            stock_text = "AGOTADO"
        elif product.is_low_stock:
            stock_emoji = "⚠️"
            stock_text = f"{product.stock}"
        else:
            stock_emoji = "📦"
            stock_text = str(product.stock)

        text += f"{status} {product.name}\n"
        text += f"   {stock_emoji} Stock: {stock_text} | 💰 {product.price} besitos\n\n"

        buttons.append([InlineKeyboardButton(
            text=f"{status} {product.name[:30]}",
            callback_data=f"product_admin_detail_{product.id}"
        )])

    buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="admin_store")])

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()


@router.callback_query(F.data.startswith("product_admin_detail_"), lambda cb: is_admin(cb.from_user.id))
async def product_admin_detail(callback: CallbackQuery):
    """Muestra detalles de un producto"""
    try:
        product_id = int(callback.data.replace("product_admin_detail_", ""))
    except ValueError:
        await callback.answer("ID invalido", show_alert=True)
        return

    store_service = StoreService()
    product = store_service.get_product(product_id)

    if not product:
        await callback.answer("Producto no encontrado", show_alert=True)
        return

    status = "✅ Activo" if product.is_active else "❌ Inactivo"
    stock_text = "Ilimitado" if product.stock == -1 else str(product.stock)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"{'Desactivar' if product.is_active else 'Activar'}",
            callback_data=f"toggle_product_{product_id}"
        )],
        [InlineKeyboardButton(
            text="📝 Reabastecer",
            callback_data=f"restock_product_{product_id}"
        )],
        [InlineKeyboardButton(
            text="⚙️ Configurar alerta",
            callback_data=f"config_stock_alert_{product_id}"
        )],
        [InlineKeyboardButton(
            text="🗑️ Eliminar",
            callback_data=f"delete_product_{product_id}"
        )],
        [InlineKeyboardButton(text="🔙 Volver", callback_data="list_products")]
    ])

    await callback.message.edit_text(
        f"🎩 Lucien:\n\n"
        f"📦 {product.name}\n\n"
        f"📝 {product.description or 'Sin descripcion'}\n\n"
        f"💰 Precio: {product.price} besitos\n"
        f"📊 Stock: {stock_text}\n"
        f"Estado: {status}\n\n"
        f"Que deseas hacer?",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith("config_stock_alert_"), lambda cb: is_admin(cb.from_user.id))
async def config_stock_alert(callback: CallbackQuery, state: FSMContext):
    """Configura umbral de alerta de stock"""
    try:
        product_id = int(callback.data.replace("config_stock_alert_", ""))
    except ValueError:
        await callback.answer("ID invalido", show_alert=True)
        return

    store_service = StoreService()
    product = store_service.get_product(product_id)

    if not product:
        await callback.answer("Producto no encontrado", show_alert=True)
        return

    await state.update_data(product_id=product_id, product_name=product.name)

    await callback.message.edit_text(
        f"🎩 <b>Lucien:</b>\n\n"
        f"<i>Configurar alerta de stock...</i>\n\n"
        f"📦 <b>{product.name}</b>\n"
        f"📊 Umbral actual: {product.low_stock_threshold}\n\n"
        f"Indica el nuevo umbral de alerta (ej: 5):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancelar", callback_data=f"product_admin_detail_{product_id}")]
        ])
    )
    await state.set_state(ProductRestockStates.waiting_threshold)
    await callback.answer()


@router.message(ProductRestockStates.waiting_threshold, F.text.regexp(r"^\d+$"))
async def process_stock_threshold(message: Message, state: FSMContext):
    """Procesa umbral de alerta de stock"""

    try:
        threshold = int(message.text.strip())
        if threshold < 0:
            await message.answer("El umbral debe ser 0 o mayor.")
            return
    except ValueError:
        await message.answer("Indica un numero valido.")
        return

    data = await state.get_data()
    product_id = data.get('product_id')

    store_service = StoreService()
    success = store_service.update_low_stock_threshold(product_id, threshold)

    if success:
        await message.answer(
            f"🎩 <b>Lucien:</b>\n\n"
            f"✅ Umbral de alerta actualizado a {threshold}.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Volver", callback_data=f"product_admin_detail_{product_id}")]
            ])
        )
    else:
        await message.answer(
            "Error al actualizar el umbral.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_store")]
            ])
        )

    await state.clear()


@router.callback_query(F.data.startswith("toggle_product_"), lambda cb: is_admin(cb.from_user.id))
async def toggle_product(callback: CallbackQuery):
    """Activa/desactiva un producto"""
    try:
        product_id = int(callback.data.replace("toggle_product_", ""))
    except ValueError:
        await callback.answer("ID invalido", show_alert=True)
        return

    store_service = StoreService()
    product = store_service.get_product(product_id)

    if not product:
        await callback.answer("Producto no encontrado", show_alert=True)
        return

    store_service.update_product(product_id, is_active=not product.is_active)

    status = "activado" if not product.is_active else "desactivado"
    await callback.answer(f"Producto {status}")
    await product_admin_detail(callback)


@router.callback_query(F.data.startswith("delete_product_"), lambda cb: is_admin(cb.from_user.id))
async def delete_product_confirm(callback: CallbackQuery):
    """Confirma eliminacion de producto"""
    try:
        product_id = int(callback.data.replace("delete_product_", ""))
    except ValueError:
        await callback.answer("ID invalido", show_alert=True)
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Si, eliminar", callback_data=f"confirm_delete_product_{product_id}")],
        [InlineKeyboardButton(text="❌ Cancelar", callback_data=f"product_admin_detail_{product_id}")]
    ])

    await callback.message.edit_text(
        "🎩 Lucien:\n\n"
        "Estas seguro de eliminar este producto?\n\n"
        "Esta accion no se puede deshacer.",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_product_"), lambda cb: is_admin(cb.from_user.id))
async def confirm_delete_product(callback: CallbackQuery):
    """Elimina el producto"""
    try:
        product_id = int(callback.data.replace("confirm_delete_product_", ""))
    except ValueError:
        await callback.answer("ID invalido", show_alert=True)
        return

    store_service = StoreService()
    success = store_service.delete_product(product_id)

    if success:
        await callback.message.edit_text(
            "🎩 Lucien:\n\n"
            "✅ Producto eliminado correctamente.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_store")]
            ])
        )
    else:
        await callback.message.edit_text(
            "Error al eliminar el producto.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_store")]
            ])
        )
    await callback.answer()


# ==================== ESTADISTICAS ====================

@router.callback_query(F.data == "store_stats", lambda cb: is_admin(cb.from_user.id))
async def store_stats(callback: CallbackQuery):
    """Muestra estadisticas de la tienda"""
    store_service = StoreService()
    stats = store_service.get_store_stats()

    await callback.message.edit_text(
        f"🎩 Lucien:\n\n"
        f"📊 Estadisticas de la Tienda:\n\n"
        f"📦 Productos:\n"
        f"   • Activos: {stats['available_products']}\n"
        f"   • Total: {stats['total_products']}\n\n"
        f"🛒 Ordenes:\n"
        f"   • Completadas: {stats['completed_orders']}\n"
        f"   • Total: {stats['total_orders']}\n\n"
        f"💰 Besitos gastados: {stats['total_besitos_spent']}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_store")]
        ])
    )
    await callback.answer()
