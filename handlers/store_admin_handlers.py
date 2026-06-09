"""
Handlers de Tienda para Administradores - Lucien Bot

Gestion de productos y estadisticas de la tienda.
"""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from keyboards.callback_data import (
    ConfigStockAlertCallback,
    DeleteProductCallback,
    ProductAdminDetailCallback,
    RestockProductCallback,
    SelectPkgProductCallback,
    ToggleProductCallback,
)
from services import get_service
from services.store_service import StoreService, compute_stock_emoji_and_text
from utils.admin import is_admin

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


# ==================== PURE HELPERS (extracted for <=50 LOC rule - Item 8 / arch-enforcer) ====================


def compute_restock_new_stock(current_stock: int, amount: int) -> int:
    """Calcula el nuevo stock tras reabastecimiento (maneja ilimitado como base 0). Función pura."""
    base = 0 if current_stock == -1 else current_stock
    return base + amount


def build_product_detail_keyboard(product_id: int, is_active: bool) -> InlineKeyboardMarkup:
    """Construye el teclado para detalle de producto admin (toggle/restock/config/delete/back). Función pura."""
    buttons = [
        [
            InlineKeyboardButton(
                text=f"{'Desactivar' if is_active else 'Activar'}",
                callback_data=ToggleProductCallback(product_id=product_id).pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="📝 Reabastecer",
                callback_data=RestockProductCallback(product_id=product_id).pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="⚙️ Configurar alerta",
                callback_data=ConfigStockAlertCallback(product_id=product_id).pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="🗑️ Eliminar",
                callback_data=DeleteProductCallback(product_id=product_id).pack(),
            )
        ],
        [InlineKeyboardButton(text="🔙 Volver", callback_data="list_products")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_stock_alerts_text_and_buttons(
    low_stock: list, out_of_stock: list
) -> tuple[str, list[list[InlineKeyboardButton]]]:
    """Construye texto y botones para alertas de stock (out/low + Reabastecer cbs + back). Función pura."""
    text = "🎩 <b>Lucien:</b>\n\n<i>Alertas de inventario...</i>\n\n"
    buttons: list[list[InlineKeyboardButton]] = []

    if out_of_stock:
        text += "🚨 <b>Productos agotados:</b>\n"
        for product in out_of_stock:
            text += f"   ❌ {product.name}\n"
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"📝 Reabastecer: {product.name[:25]}",
                        callback_data=RestockProductCallback(product_id=product.id).pack(),
                    )
                ]
            )
        text += "\n"

    if low_stock:
        text += "⚠️ <b>Stock bajo:</b>\n"
        for product in low_stock:
            stock_status = f"{product.stock}/{product.low_stock_threshold}"
            text += f"   ⚠️ {product.name} ({stock_status})\n"
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"📝 Reabastecer: {product.name[:25]}",
                        callback_data=RestockProductCallback(product_id=product.id).pack(),
                    )
                ]
            )

    buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="admin_store")])
    return text, buttons


def build_product_list_entry_and_button(product) -> tuple[str, list[InlineKeyboardButton]]:
    """Construye entrada de texto y botón para un producto en lista admin (status + stock emoji via pure + price + detail cb + trunc). Función pura."""
    status = "✅" if product.is_active else "❌"
    emoji, stock_text = compute_stock_emoji_and_text(product.stock, product.is_low_stock)
    entry = (
        f"{status} {product.name}\n   {emoji} Stock: {stock_text} | 💰 {product.price} besitos\n\n"
    )
    button = [
        InlineKeyboardButton(
            text=f"{status} {product.name[:30]}",
            callback_data=ProductAdminDetailCallback(product_id=product.id).pack(),
        )
    ]
    return entry, button


def build_product_confirmation_text_and_keyboard(data: dict) -> tuple[str, InlineKeyboardMarkup]:
    """Construye texto de resumen y teclado de confirm/cancel para wizard crear producto (desc None->'Sin descripcion'). Función pura."""
    name = data.get("name", "")
    description = data.get("description") or "Sin descripcion"
    price = data.get("price", 0)
    stock = data.get("stock", -1)
    stock_text = "Ilimitado" if stock == -1 else str(stock)

    text = (
        f"🎩 Lucien:\n\n"
        f"Resumen del producto:\n\n"
        f"📦 {name}\n"
        f"📝 {description}\n"
        f"💰 Precio: {price} besitos\n"
        f"📊 Stock: {stock_text}\n\n"
        f"Crear este producto?"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Crear", callback_data="confirm_create_product")],
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_store")],
        ]
    )
    return text, keyboard


def build_delete_confirm_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """Construye el teclado de confirmación para eliminar producto (si con confirmed + cancel a detail). Función pura."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Si, eliminar",
                    callback_data=DeleteProductCallback(
                        product_id=product_id, confirmed=True
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Cancelar",
                    callback_data=ProductAdminDetailCallback(product_id=product_id).pack(),
                )
            ],
        ]
    )


# ==================== MENU PRINCIPAL ====================


@router.callback_query(F.data == "admin_store", lambda cb: is_admin(cb.from_user.id))
async def admin_store_menu(callback: CallbackQuery):
    """Menu de administracion de tienda"""
    with get_service(StoreService) as store_service:
        stats = store_service.get_store_stats()
        low_stock = store_service.get_low_stock_products()
        out_of_stock = store_service.get_out_of_stock_products()

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="➕ Crear producto", callback_data="create_product")],
                [InlineKeyboardButton(text="📋 Ver productos", callback_data="list_products")],
                [InlineKeyboardButton(text="⚠️ Alertas de stock", callback_data="stock_alerts")],
                [InlineKeyboardButton(text="📊 Estadisticas", callback_data="store_stats")],
                [
                    InlineKeyboardButton(
                        text="📁 Gestionar categorías", callback_data="manage_categories"
                    )
                ],
                [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_gamification")],
            ]
        )

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

        text += "\nQue deseas hacer?"

        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()

    # ==================== ALERTAS DE STOCK ====================


@router.callback_query(F.data == "stock_alerts", lambda cb: is_admin(cb.from_user.id))
async def stock_alerts(callback: CallbackQuery):
    """Muestra alertas de stock"""
    with get_service(StoreService) as store_service:
        low_stock = store_service.get_low_stock_products()
        out_of_stock = store_service.get_out_of_stock_products()

        if not low_stock and not out_of_stock:
            await callback.message.edit_text(
                "🎩 <b>Lucien:</b>\n\n"
                "<i>Todos los tesoros están bien abastecidos...</i>\n\n"
                "No hay alertas de stock.",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_store")]
                    ]
                ),
            )
            await callback.answer()
            return

        text, buttons = build_stock_alerts_text_and_buttons(low_stock, out_of_stock)

        await callback.message.edit_text(
            text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
        await callback.answer()


@router.callback_query(RestockProductCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def restock_product(
    callback: CallbackQuery, state: FSMContext, callback_data: RestockProductCallback
):
    """Inicia reabastecimiento de producto"""
    product_id = callback_data.product_id

    with get_service(StoreService) as store_service:
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
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="♾️ Ilimitado", callback_data="restock_unlimited")],
                    [InlineKeyboardButton(text="❌ Cancelar", callback_data="stock_alerts")],
                ]
            ),
        )
        await state.set_state(ProductRestockStates.waiting_amount)
        await callback.answer()


@router.callback_query(ProductRestockStates.waiting_amount, F.data == "restock_unlimited")
async def restock_unlimited(callback: CallbackQuery, state: FSMContext):
    """Establece stock ilimitado"""
    data = await state.get_data()
    product_id = data.get("product_id")

    with get_service(StoreService) as store_service:
        store_service.update_product(product_id, stock=-1)

        await callback.message.edit_text(
            "🎩 <b>Lucien:</b>\n\n✅ Stock actualizado a ilimitado.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Volver a alertas", callback_data="stock_alerts")]
                ]
            ),
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
    product_id = data.get("product_id")
    product_name = data.get("product_name")

    with get_service(StoreService) as store_service:
        product = store_service.get_product(product_id)

        if not product:
            await message.answer("Producto no encontrado.")
            await state.clear()
            return

        # Calcular nuevo stock (via pure helper extracted for <=50 LOC)
        current_stock = 0 if product.stock == -1 else product.stock
        new_stock = compute_restock_new_stock(product.stock, amount)

        store_service.update_product(product_id, stock=new_stock)

        await message.answer(
            f"🎩 <b>Lucien:</b>\n\n"
            f"✅ <b>{product_name}</b> reabastecido.\n\n"
            f"📊 Stock anterior: {current_stock}\n"
            f"📦 Cantidad agregada: {amount}\n"
            f"📊 Nuevo stock: {new_stock}",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Volver a alertas", callback_data="stock_alerts")]
                ]
            ),
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
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_store")]
            ]
        ),
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
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_store")]
            ]
        ),
    )
    await state.set_state(ProductWizardStates.waiting_description)


@router.message(ProductWizardStates.waiting_description)
async def process_product_description(message: Message, state: FSMContext):
    """Procesa descripcion del producto"""
    description = None if message.text == "/skip" else message.text.strip()
    await state.update_data(description=description)

    # Mostrar paquetes disponibles (via StoreService delegate for exactly 1 service per entrypoint)
    with get_service(StoreService) as store_service:
        packages = store_service.get_available_packages_for_store()

    if not packages:
        await message.answer(
            "🎩 Lucien:\n\n"
            "No hay paquetes disponibles para la tienda.\n\n"
            "Crea un paquete primero desde 'Gestionar paquetes'.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_store")]
                ]
            ),
        )
        await state.clear()
        return

    buttons = []
    for pkg in packages:
        stock_text = "∞" if pkg.store_stock == -1 else str(pkg.store_stock)
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{pkg.name} ({pkg.file_count} archivos, stock: {stock_text})",
                    callback_data=SelectPkgProductCallback(product_id=pkg.id).pack(),
                )
            ]
        )

    buttons.append([InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_store")])

    await message.answer(
        "🎩 Lucien:\n\nPaso 3 de 5: Seleccionar paquete\n\nElige el paquete que se vendera:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await state.set_state(ProductWizardStates.selecting_package)


@router.callback_query(ProductWizardStates.selecting_package, SelectPkgProductCallback.filter())
async def select_package_for_product(
    callback: CallbackQuery, state: FSMContext, callback_data: SelectPkgProductCallback
):
    """Selecciona paquete para el producto"""
    package_id = callback_data.product_id

    await state.update_data(package_id=package_id)

    await callback.message.edit_text(
        "🎩 Lucien:\n\nPaso 4 de 5: Precio\n\nIndica el precio en besitos:\nEjemplo: 100",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_store")]
            ]
        ),
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

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="♾️ Ilimitado", callback_data="product_stock_unlimited")],
            [InlineKeyboardButton(text="📦 Limitado", callback_data="product_stock_limited")],
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_store")],
        ]
    )

    await message.answer(
        "🎩 Lucien:\n\nPaso 5 de 5: Stock\n\nConfigura el stock disponible:",
        reply_markup=keyboard,
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
        "🎩 Lucien:\n\nIndica la cantidad de unidades disponibles:\nEjemplo: 50",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_store")]
            ]
        ),
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

    text, keyboard = build_product_confirmation_text_and_keyboard(data)

    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=keyboard)
    else:
        await target.answer(text, reply_markup=keyboard)

    await state.set_state(ProductWizardStates.confirming)


@router.callback_query(ProductWizardStates.confirming, F.data == "confirm_create_product")
async def confirm_create_product(callback: CallbackQuery, state: FSMContext):
    """Crea el producto"""
    data = await state.get_data()
    with get_service(StoreService) as store_service:
        try:
            product = store_service.create_product(
                name=data.get("name"),
                description=data.get("description"),
                package_id=data.get("package_id"),
                price=data.get("price"),
                stock=data.get("stock", -1),
                created_by=callback.from_user.id,
            )
            logger.info(
                f"store_admin_handlers | confirm_create_product | user_id={callback.from_user.id} | product_id={product.id} | name={product.name}"
            )

            await callback.message.edit_text(
                f"🎩 Lucien:\n\n"
                f"✅ Producto creado exitosamente!\n\n"
                f"📦 {product.name}\n"
                f"💰 {product.price} besitos\n\n"
                f"El producto ya esta disponible en la tienda.",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_store")]
                    ]
                ),
            )

        except Exception as e:
            logger.error(f"Error creando producto: {e}")
            await callback.message.edit_text(
                "Error al crear el producto.",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_store")]
                    ]
                ),
            )

        await state.clear()
        await callback.answer()

    # ==================== LISTAR PRODUCTOS ====================


@router.callback_query(F.data == "list_products", lambda cb: is_admin(cb.from_user.id))
async def list_products(callback: CallbackQuery):
    """Lista todos los productos"""
    with get_service(StoreService) as store_service:
        products = store_service.get_all_products(active_only=False)
        logger.info(
            f"store_admin_handlers | list_products | user_id={callback.from_user.id} | count={len(products)}"
        )

        if not products:
            await callback.message.edit_text(
                "No hay productos registrados.",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_store")]
                    ]
                ),
            )
            await callback.answer()
            return

        text = "🎩 Lucien:\n\nProductos registrados:\n\n"
        buttons = []

        for product in products:
            entry, button = build_product_list_entry_and_button(product)
            text += entry
            buttons.append(button)

        buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="admin_store")])

        await callback.message.edit_text(
            text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
        await callback.answer()


@router.callback_query(ProductAdminDetailCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def product_admin_detail(callback: CallbackQuery, callback_data: ProductAdminDetailCallback):
    """Muestra detalles de un producto"""
    product_id = callback_data.product_id

    with get_service(StoreService) as store_service:
        product = store_service.get_product(product_id)

        if not product:
            await callback.answer("Producto no encontrado", show_alert=True)
            return

        status = "✅ Activo" if product.is_active else "❌ Inactivo"
        stock_text = "Ilimitado" if product.stock == -1 else str(product.stock)

        keyboard = build_product_detail_keyboard(product_id, product.is_active)

        await callback.message.edit_text(
            f"🎩 Lucien:\n\n"
            f"📦 {product.name}\n\n"
            f"📝 {product.description or 'Sin descripcion'}\n\n"
            f"💰 Precio: {product.price} besitos\n"
            f"📊 Stock: {stock_text}\n"
            f"Estado: {status}\n\n"
            f"Que deseas hacer?",
            reply_markup=keyboard,
        )
        await callback.answer()


@router.callback_query(ConfigStockAlertCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def config_stock_alert(
    callback: CallbackQuery, state: FSMContext, callback_data: ConfigStockAlertCallback
):
    """Configura umbral de alerta de stock"""
    product_id = callback_data.product_id

    with get_service(StoreService) as store_service:
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
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="❌ Cancelar", callback_data=f"product_admin_detail_{product_id}"
                        )
                    ]
                ]
            ),
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
    product_id = data.get("product_id")

    with get_service(StoreService) as store_service:
        success = store_service.update_low_stock_threshold(product_id, threshold)

        if success:
            await message.answer(
                f"🎩 <b>Lucien:</b>\n\n✅ Umbral de alerta actualizado a {threshold}.",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="🔙 Volver", callback_data=f"product_admin_detail_{product_id}"
                            )
                        ]
                    ]
                ),
            )
        else:
            await message.answer(
                "Error al actualizar el umbral.",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_store")]
                    ]
                ),
            )

        await state.clear()


@router.callback_query(ToggleProductCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def toggle_product(callback: CallbackQuery, callback_data: ToggleProductCallback):
    """Activa/desactiva un producto"""
    product_id = callback_data.product_id

    with get_service(StoreService) as store_service:
        product = store_service.get_product(product_id)

        if not product:
            await callback.answer("Producto no encontrado", show_alert=True)
            return

        store_service.update_product(product_id, is_active=not product.is_active)

        status = "activado" if not product.is_active else "desactivado"
        await callback.answer(f"Producto {status}")
        await product_admin_detail(callback, ProductAdminDetailCallback(product_id=product_id))


@router.callback_query(DeleteProductCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def handle_delete_product(callback: CallbackQuery, callback_data: DeleteProductCallback):
    """Maneja eliminacion de producto (confirm/execute)"""
    product_id = callback_data.product_id

    if not callback_data.confirmed:
        # Show confirmation (via pure helper extracted for <=50 LOC)
        keyboard = build_delete_confirm_keyboard(product_id)

        await callback.message.edit_text(
            "🎩 Lucien:\n\n"
            "Estas seguro de eliminar este producto?\n\n"
            "Esta accion no se puede deshacer.",
            reply_markup=keyboard,
        )
        await callback.answer()
        return

    with get_service(StoreService) as store_service:
        success = store_service.delete_product(product_id)

        if success:
            await callback.message.edit_text(
                "🎩 Lucien:\n\n✅ Producto eliminado correctamente.",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_store")]
                    ]
                ),
            )
        else:
            await callback.message.edit_text(
                "Error al eliminar el producto.",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_store")]
                    ]
                ),
            )
        await callback.answer()

    # ==================== ESTADISTICAS ====================


@router.callback_query(F.data == "store_stats", lambda cb: is_admin(cb.from_user.id))
async def store_stats(callback: CallbackQuery):
    """Muestra estadisticas de la tienda"""
    with get_service(StoreService) as store_service:
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
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_store")]
                ]
            ),
        )
        await callback.answer()
