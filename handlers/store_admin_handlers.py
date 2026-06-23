"""
Handlers de Tienda para Administradores - Lucien Bot

Gestion de productos y estadisticas de la tienda.
"""

import json
import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from handlers.states.package_states import PackageWizardStates
from keyboards.callback_data import (
    CancelPackageWizardCallback,
    ConfigStockAlertCallback,
    CreatePkgForProductCallback,
    DeleteProductCallback,
    EditProductCallback,
    EditProductFieldCallback,
    ProductAdminDetailCallback,
    RestockProductCallback,
    SelectPkgEditProductCallback,
    SelectPkgProductCallback,
    SelectStoryNodeEditProductCallback,
    SelectStoryNodeStoreWizardCallback,
    SelectTariffEditProductCallback,
    SelectTariffStoreWizardCallback,
    SelectTierEditProductCallback,
    ToggleProductCallback,
)
from keyboards.inline_keyboards import cancel_keyboard
from models.models import DeliveryMode, FulfillmentKind
from services import get_service
from services.store_service import StoreService, compute_stock_emoji_and_text
from utils.admin import is_admin
from utils.lucien_voice import LucienVoice

logger = logging.getLogger(__name__)
router = Router()


# Estados para FSM
class ProductWizardStates(StatesGroup):
    waiting_name = State()
    waiting_description = State()
    selecting_tier = State()
    selecting_delivery_mode = State()
    selecting_fulfillment_kind = State()
    selecting_package = State()
    selecting_tariff = State()
    selecting_story_node = State()
    waiting_fulfillment_config = State()
    waiting_price = State()
    waiting_stock = State()
    waiting_monthly_cap = State()
    confirming = State()


_WIZARD_PACKAGE_KINDS = {
    FulfillmentKind.PACKAGE.value,
    FulfillmentKind.PACKAGE_DEFERRED.value,
}
_WIZARD_CONFIG_KINDS = {
    FulfillmentKind.PRIVILEGE_EARLY_ACCESS.value,
    FulfillmentKind.PRIVILEGE_DISCOUNT.value,
    FulfillmentKind.USER_INPUT_THEN_MANUAL.value,
    FulfillmentKind.CHANNEL_HONOR.value,
    FulfillmentKind.SCHEDULED_CHAT.value,
}


class ProductRestockStates(StatesGroup):
    waiting_amount = State()
    waiting_threshold = State()


class ProductEditStates(StatesGroup):
    waiting_name = State()
    waiting_description = State()
    selecting_package = State()
    selecting_tier = State()
    selecting_tariff = State()
    selecting_story_node = State()
    waiting_price = State()
    waiting_stock = State()


# ==================== PURE HELPERS (extracted for <=50 LOC rule - Item 8 / arch-enforcer) ====================


def compute_restock_new_stock(current_stock: int, amount: int) -> int:
    """Calcula el nuevo stock tras reabastecimiento (maneja ilimitado como base 0). Función pura."""
    base = 0 if current_stock == -1 else current_stock
    return base + amount


def build_product_detail_keyboard(product_id: int, is_active: bool) -> InlineKeyboardMarkup:
    """Construye el teclado para detalle de producto admin (edit/toggle/restock/config/delete/back). Función pura."""
    buttons = [
        [
            InlineKeyboardButton(
                text="✏️ Editar",
                callback_data=EditProductCallback(product_id=product_id).pack(),
            )
        ],
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


def _product_tier_label(product) -> str:
    """Etiqueta de tier para vistas admin. Función pura."""
    tier = getattr(product, "tier", None)
    return tier.name if tier else "Sin nivel"


def build_product_list_entry_and_button(product) -> tuple[str, list[InlineKeyboardButton]]:
    """Construye entrada de texto y botón para un producto en lista admin (status + stock emoji via pure + price + detail cb + trunc). Función pura."""
    status = "✅" if product.is_active else "❌"
    emoji, stock_text = compute_stock_emoji_and_text(product.stock, product.is_low_stock)
    tier_label = _product_tier_label(product)
    entry = (
        f"{status} {product.name}\n"
        f"   ✨ {tier_label} | {emoji} Stock: {stock_text} | 💰 {product.price} besitos\n\n"
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

    tier = data.get("tier_name", "—")
    delivery = data.get("delivery_mode", "auto")
    kind = data.get("fulfillment_kind", "package")
    cap = data.get("monthly_stock_cap")
    cap_text = (
        LucienVoice.fulfillment_admin_wizard_cap_unlimited_label()
        if not cap or cap < 0
        else str(cap)
    )
    text = LucienVoice.fulfillment_admin_wizard_confirmation_summary(
        name,
        description,
        tier,
        delivery,
        kind,
        price,
        stock_text,
        cap_text,
        tariff_name=data.get("tariff_name"),
        story_node_title=data.get("story_node_title"),
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Crear", callback_data="confirm_create_product")],
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_store")],
        ]
    )
    return text, keyboard


def build_product_edit_menu_text(product) -> str:
    """Construye el texto del menú de edición con valores actuales. Función pura."""
    stock_text = "Ilimitado" if product.stock == -1 else str(product.stock)
    package_name = product.package.name if getattr(product, "package", None) else "Sin paquete"
    description = product.description or "Sin descripcion"
    lines = [
        "🎩 Lucien:\n",
        "Editar producto:\n",
        f"📦 {product.name}",
        f"📝 {description}",
        f"✨ Nivel: {_product_tier_label(product)}",
        f"📁 Paquete: {package_name}",
    ]
    if product.fulfillment_kind == FulfillmentKind.VIP_GRANT:
        tariff_name = product.tariff.name if getattr(product, "tariff", None) else "Sin tarifa"
        lines.append(f"👑 Tarifa: {tariff_name}")
    elif product.fulfillment_kind == FulfillmentKind.STORY_UNLOCK:
        node_title = product.story_node.title if getattr(product, "story_node", None) else "Sin nodo"
        lines.append(f"📖 Nodo: {node_title}")
    lines.extend(
        [
            f"💰 Precio: {product.price} besitos",
            f"📊 Stock: {stock_text}",
            "",
            "Que campo deseas modificar?",
        ]
    )
    return "\n".join(lines)


def build_product_edit_menu_keyboard(product) -> InlineKeyboardMarkup:
    """Construye el teclado del menú de edición por campo. Función pura."""
    product_id = product.id
    fields = [
        ("📦 Nombre", "name"),
        ("📝 Descripcion", "description"),
        ("✨ Nivel", "tier"),
        ("📁 Paquete", "package"),
        ("💰 Precio", "price"),
        ("📊 Stock", "stock"),
    ]
    if product.fulfillment_kind == FulfillmentKind.VIP_GRANT:
        fields.append(("👑 Tarifa VIP", "tariff"))
    elif product.fulfillment_kind == FulfillmentKind.STORY_UNLOCK:
        fields.append(("📖 Nodo narrativo", "story_node"))
    buttons = [
        [
            InlineKeyboardButton(
                text=label,
                callback_data=EditProductFieldCallback(product_id=product_id, field=field).pack(),
            )
        ]
        for label, field in fields
    ]
    buttons.append(
        [
            InlineKeyboardButton(
                text="🔙 Volver",
                callback_data=ProductAdminDetailCallback(product_id=product_id).pack(),
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_edit_cancel_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """Construye teclado de cancelar para flujos de edición. Función pura."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Cancelar",
                    callback_data=EditProductCallback(product_id=product_id).pack(),
                )
            ]
        ]
    )


def build_edit_name_prompt_and_keyboard(product_id: int, name: str) -> tuple[str, InlineKeyboardMarkup]:
    """Construye prompt y teclado para editar nombre. Función pura."""
    text = f"🎩 Lucien:\n\nNombre actual: {name}\n\nIndica el nuevo nombre:"
    return text, build_edit_cancel_keyboard(product_id)


def build_edit_description_prompt_and_keyboard(
    product_id: int, description: str | None
) -> tuple[str, InlineKeyboardMarkup]:
    """Construye prompt y teclado para editar descripción. Función pura."""
    current = description or "Sin descripcion"
    text = (
        f"🎩 Lucien:\n\nDescripcion actual: {current}\n\n"
        f"Escribe la nueva descripcion o envia /skip para quitarla:"
    )
    return text, build_edit_cancel_keyboard(product_id)


def build_edit_price_prompt_and_keyboard(
    product_id: int, price: int
) -> tuple[str, InlineKeyboardMarkup]:
    """Construye prompt y teclado para editar precio. Función pura."""
    text = f"🎩 Lucien:\n\nPrecio actual: {price} besitos\n\nIndica el nuevo precio:"
    return text, build_edit_cancel_keyboard(product_id)


def build_edit_stock_prompt_and_keyboard(
    product_id: int, stock: int
) -> tuple[str, InlineKeyboardMarkup]:
    """Construye prompt y teclado para editar stock. Función pura."""
    stock_text = "Ilimitado" if stock == -1 else str(stock)
    text = f"🎩 Lucien:\n\nStock actual: {stock_text}\n\nConfigura el nuevo stock:"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="♾️ Ilimitado", callback_data="edit_product_stock_unlimited")],
            [InlineKeyboardButton(text="📦 Limitado", callback_data="edit_product_stock_limited")],
            [
                InlineKeyboardButton(
                    text="❌ Cancelar",
                    callback_data=EditProductCallback(product_id=product_id).pack(),
                )
            ],
        ]
    )
    return text, keyboard


def build_edit_package_buttons(
    product_id: int, packages: list
) -> list[list[InlineKeyboardButton]]:
    """Construye botones de selección de paquete para edición. Función pura."""
    buttons = []
    for pkg in packages:
        stock_text = "∞" if pkg.store_stock == -1 else str(pkg.store_stock)
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{pkg.name} ({pkg.file_count} archivos, stock: {stock_text})",
                    callback_data=SelectPkgEditProductCallback(
                        product_id=product_id, package_id=pkg.id
                    ).pack(),
                )
            ]
        )
    buttons.append(
        [
            InlineKeyboardButton(
                text="➕ Crear nuevo paquete",
                callback_data=CreatePkgForProductCallback(
                    source="edit", product_id=product_id
                ).pack(),
            )
        ]
    )
    buttons.append(
        [
            InlineKeyboardButton(
                text="❌ Cancelar",
                callback_data=EditProductCallback(product_id=product_id).pack(),
            )
        ]
    )
    return buttons


def build_wizard_tariff_keyboard(tariffs: list) -> InlineKeyboardMarkup:
    """Construye teclado inline de tarifas VIP para wizard crear producto. Función pura."""
    buttons = [
        [
            InlineKeyboardButton(
                text=f"{tariff.name} ({tariff.duration_days} dias)",
                callback_data=SelectTariffStoreWizardCallback(tariff_id=tariff.id).pack(),
            )
        ]
        for tariff in tariffs[:20]
    ]
    buttons.append([InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_store")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_wizard_story_node_keyboard(nodes: list) -> InlineKeyboardMarkup:
    """Construye teclado inline de nodos narrativos para wizard crear producto. Función pura."""
    buttons = [
        [
            InlineKeyboardButton(
                text=node.title,
                callback_data=SelectStoryNodeStoreWizardCallback(story_node_id=node.id).pack(),
            )
        ]
        for node in nodes[:20]
    ]
    buttons.append([InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_store")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_edit_tier_buttons(product_id: int, tiers: list) -> list[list[InlineKeyboardButton]]:
    """Construye botones de selección de tier para edición. Función pura."""
    buttons = [
        [
            InlineKeyboardButton(
                text=f"{tier.name} ({tier.price_min}-{tier.price_max} 💋)",
                callback_data=SelectTierEditProductCallback(
                    product_id=product_id, tier_id=tier.id
                ).pack(),
            )
        ]
        for tier in tiers
    ]
    buttons.append(
        [InlineKeyboardButton(text="❌ Cancelar", callback_data=f"edit_product:{product_id}")]
    )
    return buttons


def build_edit_tariff_buttons(
    product_id: int, tariffs: list
) -> list[list[InlineKeyboardButton]]:
    """Construye botones de selección de tarifa para edición. Función pura."""
    buttons = [
        [
            InlineKeyboardButton(
                text=f"{tariff.name} ({tariff.duration_days} dias)",
                callback_data=SelectTariffEditProductCallback(
                    product_id=product_id, tariff_id=tariff.id
                ).pack(),
            )
        ]
        for tariff in tariffs
    ]
    buttons.append(
        [
            InlineKeyboardButton(
                text="❌ Cancelar",
                callback_data=EditProductCallback(product_id=product_id).pack(),
            )
        ]
    )
    return buttons


def build_edit_story_node_buttons(
    product_id: int, nodes: list
) -> list[list[InlineKeyboardButton]]:
    """Construye botones de selección de nodo narrativo para edición. Función pura."""
    buttons = [
        [
            InlineKeyboardButton(
                text=node.title,
                callback_data=SelectStoryNodeEditProductCallback(
                    product_id=product_id, story_node_id=node.id
                ).pack(),
            )
        ]
        for node in nodes
    ]
    buttons.append(
        [
            InlineKeyboardButton(
                text="❌ Cancelar",
                callback_data=EditProductCallback(product_id=product_id).pack(),
            )
        ]
    )
    return buttons


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
                        text=LucienVoice.fulfillment_admin_queue_button(),
                        callback_data="fulfill_admin_menu",
                    )
                ],
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
                LucienVoice.store_admin_stock_alerts_empty(),
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
        LucienVoice.fulfillment_admin_wizard_start(),
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
        await message.answer(LucienVoice.fulfillment_admin_wizard_name_too_short())
        return

    await state.update_data(name=name)
    await message.answer(
        LucienVoice.fulfillment_admin_wizard_step_description(),
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

    with get_service(StoreService) as store_service:
        tiers = store_service.get_all_tiers()
    if not tiers:
        await message.answer(
            LucienVoice.fulfillment_admin_wizard_select_tier(),
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_store")]
                ]
            ),
        )
        await state.clear()
        return

    buttons = [
        [InlineKeyboardButton(text=t.name, callback_data=f"wiz_tier:{t.id}")]
        for t in tiers
    ]
    buttons.append([InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_store")])
    await message.answer(
        LucienVoice.fulfillment_admin_wizard_select_tier(),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await state.set_state(ProductWizardStates.selecting_tier)


@router.callback_query(ProductWizardStates.selecting_tier, F.data.startswith("wiz_tier:"))
async def wizard_select_tier(callback: CallbackQuery, state: FSMContext):
    """Selecciona tier del catálogo."""
    tier_id = int(callback.data.split(":")[1])
    with get_service(StoreService) as store_service:
        tiers = {t.id: t.name for t in store_service.get_all_tiers()}
    await state.update_data(tier_id=tier_id, tier_name=tiers.get(tier_id, "?"))
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="AUTO", callback_data="wiz_dm:auto")],
            [InlineKeyboardButton(text="MANUAL", callback_data="wiz_dm:manual")],
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_store")],
        ]
    )
    await callback.message.edit_text(
        LucienVoice.fulfillment_admin_wizard_delivery_mode(),
        reply_markup=keyboard,
    )
    await state.set_state(ProductWizardStates.selecting_delivery_mode)
    await callback.answer()


@router.callback_query(ProductWizardStates.selecting_delivery_mode, F.data.startswith("wiz_dm:"))
async def wizard_select_delivery_mode(callback: CallbackQuery, state: FSMContext):
    """Selecciona modo de entrega."""
    mode = callback.data.split(":")[1]
    await state.update_data(delivery_mode=mode)
    kinds = [
        ("PACKAGE", FulfillmentKind.PACKAGE.value),
        ("PKG_DEFERRED", FulfillmentKind.PACKAGE_DEFERRED.value),
        ("VIP_GRANT", FulfillmentKind.VIP_GRANT.value),
        ("STORY_UNLOCK", FulfillmentKind.STORY_UNLOCK.value),
        ("EARLY_ACCESS", FulfillmentKind.PRIVILEGE_EARLY_ACCESS.value),
        ("DISCOUNT", FulfillmentKind.PRIVILEGE_DISCOUNT.value),
        ("USER_INPUT", FulfillmentKind.USER_INPUT_THEN_MANUAL.value),
        ("WAITLIST", FulfillmentKind.WAITLIST_ENTRY.value),
        ("CHANNEL_HONOR", FulfillmentKind.CHANNEL_HONOR.value),
        ("SCHEDULED_CHAT", FulfillmentKind.SCHEDULED_CHAT.value),
    ]
    buttons = [
        [InlineKeyboardButton(text=label, callback_data=f"wiz_kind:{value}")]
        for label, value in kinds
    ]
    buttons.append([InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_store")])
    await callback.message.edit_text(
        LucienVoice.fulfillment_admin_wizard_fulfillment_kind(),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await state.set_state(ProductWizardStates.selecting_fulfillment_kind)
    await callback.answer()


async def _wizard_prompt_price_step(target, state: FSMContext) -> None:
    """Pide precio en besitos."""
    text = LucienVoice.fulfillment_admin_wizard_step_price()
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_store")]
        ]
    )
    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=keyboard)
    else:
        await target.answer(text, reply_markup=keyboard)
    await state.set_state(ProductWizardStates.waiting_price)


async def _wizard_route_after_kind(target, state: FSMContext, kind: str) -> None:
    """Enruta al paso de payload según fulfillment_kind."""
    if kind in _WIZARD_PACKAGE_KINDS:
        await _wizard_prompt_package_selection(target, state)
    elif kind == FulfillmentKind.VIP_GRANT.value:
        await _wizard_prompt_tariff_selection(target, state)
    elif kind == FulfillmentKind.STORY_UNLOCK.value:
        await _wizard_prompt_story_node_selection(target, state)
    elif kind in _WIZARD_CONFIG_KINDS:
        text = LucienVoice.fulfillment_admin_wizard_step_fulfillment_config()
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⏭️ Omitir", callback_data="wiz_cfg_skip")],
                [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_store")],
            ]
        )
        if isinstance(target, CallbackQuery):
            await target.message.edit_text(text, reply_markup=keyboard)
        else:
            await target.answer(text, reply_markup=keyboard)
        await state.set_state(ProductWizardStates.waiting_fulfillment_config)
    else:
        await state.update_data(package_id=None, fulfillment_config=None)
        await _wizard_prompt_price_step(target, state)


async def _wizard_prompt_monthly_cap(target, state: FSMContext) -> None:
    """Pide cupo mensual opcional."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"♾️ {LucienVoice.fulfillment_admin_wizard_cap_unlimited_label()}",
                    callback_data="wiz_cap_none",
                )
            ],
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_store")],
        ]
    )
    text = LucienVoice.fulfillment_admin_wizard_step_monthly_cap()
    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=keyboard)
    else:
        await target.answer(text, reply_markup=keyboard)
    await state.set_state(ProductWizardStates.waiting_monthly_cap)


async def _wizard_prompt_package_selection(target, state: FSMContext) -> None:
    """Muestra paquetes si el kind lo requiere; si no, salta a precio."""
    with get_service(StoreService) as store_service:
        packages = store_service.get_available_packages_for_store()

    create_btn = InlineKeyboardButton(
        text="➕ Crear nuevo paquete",
        callback_data=CreatePkgForProductCallback(source="wizard").pack(),
    )

    if not packages:
        text = LucienVoice.fulfillment_admin_wizard_no_packages()
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [create_btn],
                [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_store")],
            ]
        )
        if isinstance(target, CallbackQuery):
            await target.message.edit_text(text, reply_markup=keyboard)
        else:
            await target.answer(text, reply_markup=keyboard)
        await state.set_state(ProductWizardStates.selecting_package)
        return
    buttons = [
        [
            InlineKeyboardButton(
                text=pkg.name,
                callback_data=SelectPkgProductCallback(product_id=pkg.id).pack(),
            )
        ]
        for pkg in packages[:20]
    ]
    buttons.append([create_btn])
    buttons.append([InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_store")])
    text = LucienVoice.fulfillment_admin_wizard_step_select_package()
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=keyboard)
    else:
        await target.answer(text, reply_markup=keyboard)
    await state.set_state(ProductWizardStates.selecting_package)


async def _wizard_prompt_tariff_selection(target, state: FSMContext) -> None:
    """Muestra tarifas VIP para VIP_GRANT; si vacío, vuelve a admin tienda."""
    with get_service(StoreService) as store_service:
        tariffs = store_service.get_tariffs_for_product_wizard()

    if not tariffs:
        text = LucienVoice.fulfillment_admin_wizard_no_tariffs()
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_store")]
            ]
        )
        if isinstance(target, CallbackQuery):
            await target.message.edit_text(text, reply_markup=keyboard)
        else:
            await target.answer(text, reply_markup=keyboard)
        await state.clear()
        return

    keyboard = build_wizard_tariff_keyboard(tariffs)
    text = LucienVoice.fulfillment_admin_wizard_select_tariff()
    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=keyboard)
    else:
        await target.answer(text, reply_markup=keyboard)
    await state.set_state(ProductWizardStates.selecting_tariff)


async def _wizard_prompt_story_node_selection(target, state: FSMContext) -> None:
    """Muestra nodos narrativos para STORY_UNLOCK; si vacío, vuelve a admin tienda."""
    with get_service(StoreService) as store_service:
        nodes = store_service.get_story_nodes_for_product_wizard()

    if not nodes:
        text = LucienVoice.fulfillment_admin_wizard_no_story_nodes()
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_store")]
            ]
        )
        if isinstance(target, CallbackQuery):
            await target.message.edit_text(text, reply_markup=keyboard)
        else:
            await target.answer(text, reply_markup=keyboard)
        await state.clear()
        return

    keyboard = build_wizard_story_node_keyboard(nodes)
    text = LucienVoice.fulfillment_admin_wizard_select_story_node()
    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=keyboard)
    else:
        await target.answer(text, reply_markup=keyboard)
    await state.set_state(ProductWizardStates.selecting_story_node)


@router.callback_query(
    ProductWizardStates.selecting_fulfillment_kind, F.data.startswith("wiz_kind:")
)
async def wizard_select_fulfillment_kind(callback: CallbackQuery, state: FSMContext):
    """Selecciona tipo de fulfillment."""
    kind = callback.data.split(":")[1]
    await state.update_data(fulfillment_kind=kind)
    await _wizard_route_after_kind(callback, state, kind)
    await callback.answer()


@router.callback_query(
    ProductWizardStates.selecting_tariff, SelectTariffStoreWizardCallback.filter()
)
async def wizard_select_tariff(
    callback: CallbackQuery, state: FSMContext, callback_data: SelectTariffStoreWizardCallback
):
    """Selecciona tarifa VIP en wizard crear producto."""
    with get_service(StoreService) as store_service:
        tariffs = store_service.get_tariffs_for_product_wizard()
    tariff_name = next(
        (t.name for t in tariffs if t.id == callback_data.tariff_id),
        str(callback_data.tariff_id),
    )
    await state.update_data(tariff_id=callback_data.tariff_id, tariff_name=tariff_name)
    await _wizard_prompt_price_step(callback, state)
    await callback.answer()


@router.callback_query(
    ProductWizardStates.selecting_story_node, SelectStoryNodeStoreWizardCallback.filter()
)
async def wizard_select_story_node(
    callback: CallbackQuery,
    state: FSMContext,
    callback_data: SelectStoryNodeStoreWizardCallback,
):
    """Selecciona nodo narrativo en wizard crear producto."""
    with get_service(StoreService) as store_service:
        nodes = store_service.get_story_nodes_for_product_wizard()
    story_node_title = next(
        (n.title for n in nodes if n.id == callback_data.story_node_id),
        str(callback_data.story_node_id),
    )
    await state.update_data(
        story_node_id=callback_data.story_node_id, story_node_title=story_node_title
    )
    await _wizard_prompt_price_step(callback, state)
    await callback.answer()


@router.callback_query(
    ProductWizardStates.waiting_fulfillment_config, F.data == "wiz_cfg_skip"
)
async def wizard_skip_fulfillment_config(callback: CallbackQuery, state: FSMContext):
    """Usa fulfillment_config vacío."""
    await state.update_data(fulfillment_config="{}")
    await _wizard_prompt_price_step(callback, state)
    await callback.answer()


@router.message(ProductWizardStates.waiting_fulfillment_config)
async def wizard_process_fulfillment_config(message: Message, state: FSMContext):
    """Captura fulfillment_config JSON."""
    import json

    raw = (message.text or "").strip()
    try:
        json.loads(raw)
    except json.JSONDecodeError:
        await message.answer(LucienVoice.fulfillment_admin_wizard_invalid_json())
        return
    await state.update_data(fulfillment_config=raw)
    await _wizard_prompt_price_step(message, state)


@router.callback_query(ProductWizardStates.selecting_package, SelectPkgProductCallback.filter())
async def select_package_for_product(
    callback: CallbackQuery, state: FSMContext, callback_data: SelectPkgProductCallback
):
    """Selecciona paquete para el producto"""
    package_id = callback_data.product_id

    await state.update_data(package_id=package_id)

    await callback.message.edit_text(
        LucienVoice.fulfillment_admin_wizard_step_price_with_example(),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_store")]
            ]
        ),
    )
    await state.set_state(ProductWizardStates.waiting_price)
    await callback.answer()


@router.callback_query(
    ProductWizardStates.selecting_package,
    CreatePkgForProductCallback.filter(F.source == "wizard"),
)
async def create_package_for_product_wizard(
    callback: CallbackQuery, state: FSMContext, callback_data: CreatePkgForProductCallback
):
    """Inicia wizard de creación de paquete desde el wizard de producto."""
    wizard_data = await state.get_data()
    return_context = {"source": "product_wizard", "data": wizard_data}
    await state.clear()
    await state.update_data(__return_context=json.dumps(return_context))
    await state.set_state(PackageWizardStates.waiting_name)

    await callback.message.edit_text(
        """🎩 <b>Lucien:</b>

<i>Vamos a crear un nuevo tesoro para el reino...</i>

📋 <b>Paso 1 de 6:</b> Nombre del paquete

Indique un nombre descriptivo para el paquete:
Ejemplo: <code>Fotos exclusivas de marzo</code>""",
        reply_markup=cancel_keyboard(CancelPackageWizardCallback().pack()),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(
    ProductEditStates.selecting_package,
    CreatePkgForProductCallback.filter(F.source == "edit"),
)
async def create_package_for_product_edit(
    callback: CallbackQuery, state: FSMContext, callback_data: CreatePkgForProductCallback
):
    """Inicia wizard de creación de paquete desde la edición de producto."""
    product_id = callback_data.product_id
    return_context = {"source": "product_edit", "data": {"edit_product_id": product_id}}
    await state.clear()
    await state.update_data(__return_context=json.dumps(return_context))
    await state.set_state(PackageWizardStates.waiting_name)

    await callback.message.edit_text(
        """🎩 <b>Lucien:</b>

<i>Vamos a crear un nuevo tesoro para el reino...</i>

📋 <b>Paso 1 de 6:</b> Nombre del paquete

Indique un nombre descriptivo para el paquete:
Ejemplo: <code>Fotos exclusivas de marzo</code>""",
        reply_markup=cancel_keyboard(CancelPackageWizardCallback().pack()),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(ProductWizardStates.waiting_price)
async def process_product_price(message: Message, state: FSMContext):
    """Procesa precio del producto"""
    try:
        price = int(message.text.strip())
        if price < 1:
            raise ValueError("Debe ser mayor a 0")
    except ValueError:
        await message.answer(LucienVoice.fulfillment_admin_wizard_invalid_price())
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
        LucienVoice.fulfillment_admin_wizard_step_stock(),
        reply_markup=keyboard,
    )
    await state.set_state(ProductWizardStates.waiting_stock)


@router.callback_query(ProductWizardStates.waiting_stock, F.data == "product_stock_unlimited")
async def product_stock_unlimited(callback: CallbackQuery, state: FSMContext):
    """Stock ilimitado"""
    await state.update_data(stock=-1)
    await _wizard_prompt_monthly_cap(callback, state)
    await callback.answer()


@router.callback_query(ProductWizardStates.waiting_stock, F.data == "product_stock_limited")
async def product_stock_limited(callback: CallbackQuery, state: FSMContext):
    """Pide cantidad limitada"""
    await callback.message.edit_text(
        LucienVoice.fulfillment_admin_wizard_step_limited_stock(),
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
        await message.answer(LucienVoice.fulfillment_admin_wizard_invalid_stock())
        return

    await state.update_data(stock=stock)
    await _wizard_prompt_monthly_cap(message, state)


@router.callback_query(ProductWizardStates.waiting_monthly_cap, F.data == "wiz_cap_none")
async def wizard_monthly_cap_none(callback: CallbackQuery, state: FSMContext):
    """Sin cupo mensual."""
    await state.update_data(monthly_stock_cap=None)
    await show_product_confirmation(callback, state)
    await callback.answer()


@router.message(ProductWizardStates.waiting_monthly_cap)
async def wizard_process_monthly_cap(message: Message, state: FSMContext):
    """Captura cupo mensual numérico."""
    try:
        cap = int(message.text.strip())
        if cap < 1:
            raise ValueError
    except ValueError:
        await message.answer(LucienVoice.fulfillment_admin_wizard_invalid_monthly_cap())
        return
    await state.update_data(monthly_stock_cap=cap)
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
            dm_raw = (data.get("delivery_mode") or "auto").lower()
            fk_raw = (data.get("fulfillment_kind") or "package").lower()
            product = store_service.create_product(
                name=data.get("name"),
                description=data.get("description"),
                package_id=data.get("package_id"),
                price=data.get("price"),
                stock=data.get("stock", -1),
                created_by=callback.from_user.id,
                tier_id=data.get("tier_id"),
                delivery_mode=DeliveryMode(dm_raw),
                fulfillment_kind=FulfillmentKind(fk_raw),
                fulfillment_config=data.get("fulfillment_config"),
                monthly_stock_cap=data.get("monthly_stock_cap"),
                story_node_id=data.get("story_node_id"),
                tariff_id=data.get("tariff_id"),
            )
            logger.info(
                f"store_admin_handlers | confirm_create_product | user_id={callback.from_user.id} | product_id={product.id} | name={product.name}"
            )

            await callback.message.edit_text(
                LucienVoice.fulfillment_admin_wizard_product_created(
                    product.name, product.price
                ),
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_store")]
                    ]
                ),
            )

        except Exception as e:
            logger.error(f"Error creando producto: {e}")
            await callback.message.edit_text(
                LucienVoice.fulfillment_admin_wizard_product_create_error(),
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
        package_name = product.package.name if product.package else "Sin paquete"
        tier_label = _product_tier_label(product)

        keyboard = build_product_detail_keyboard(product_id, product.is_active)

        await callback.message.edit_text(
            f"🎩 Lucien:\n\n"
            f"📦 {product.name}\n\n"
            f"📝 {product.description or 'Sin descripcion'}\n\n"
            f"✨ Nivel: {tier_label}\n"
            f"📁 Paquete: {package_name}\n"
            f"💰 Precio: {product.price} besitos\n"
            f"📊 Stock: {stock_text}\n"
            f"Estado: {status}\n\n"
            f"Que deseas hacer?",
            reply_markup=keyboard,
        )
        await callback.answer()


# ==================== EDITAR PRODUCTO ====================


@router.callback_query(EditProductCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def edit_product_menu(callback: CallbackQuery, callback_data: EditProductCallback):
    """Muestra menú de edición de producto"""
    product_id = callback_data.product_id

    with get_service(StoreService) as store_service:
        product = store_service.get_product(product_id)
        if not product:
            await callback.answer("Producto no encontrado", show_alert=True)
            return

        await callback.message.edit_text(
            build_product_edit_menu_text(product),
            reply_markup=build_product_edit_menu_keyboard(product),
        )
        await callback.answer()


@router.callback_query(EditProductFieldCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def edit_product_field_start(
    callback: CallbackQuery, state: FSMContext, callback_data: EditProductFieldCallback
):
    """Inicia edición de un campo específico del producto"""
    product_id = callback_data.product_id
    field = callback_data.field

    with get_service(StoreService) as store_service:
        product = store_service.get_product(product_id)
        if not product:
            await callback.answer("Producto no encontrado", show_alert=True)
            return

        await state.update_data(edit_product_id=product_id, edit_field=field)

        if field == "name":
            text, keyboard = build_edit_name_prompt_and_keyboard(product_id, product.name)
            next_state = ProductEditStates.waiting_name
        elif field == "description":
            text, keyboard = build_edit_description_prompt_and_keyboard(
                product_id, product.description
            )
            next_state = ProductEditStates.waiting_description
        elif field == "package":
            packages = store_service.get_packages_for_product_edit(product_id)
            if not packages:
                await callback.answer("No hay paquetes disponibles", show_alert=True)
                return
            text = "🎩 Lucien:\n\nSelecciona el nuevo paquete:"
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=build_edit_package_buttons(product_id, packages)
            )
            next_state = ProductEditStates.selecting_package
        elif field == "tier":
            tiers = store_service.get_all_tiers()
            if not tiers:
                await callback.answer(
                    LucienVoice.fulfillment_admin_wizard_select_tier(), show_alert=True
                )
                return
            text = LucienVoice.fulfillment_admin_wizard_select_tier()
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=build_edit_tier_buttons(product_id, tiers)
            )
            next_state = ProductEditStates.selecting_tier
        elif field == "price":
            text, keyboard = build_edit_price_prompt_and_keyboard(product_id, product.price)
            next_state = ProductEditStates.waiting_price
        elif field == "stock":
            text, keyboard = build_edit_stock_prompt_and_keyboard(product_id, product.stock)
            next_state = ProductEditStates.waiting_stock
        elif field == "tariff":
            tariffs = store_service.get_tariffs_for_product_edit(product_id)
            if not tariffs:
                await callback.answer(
                    LucienVoice.fulfillment_admin_wizard_no_tariffs(), show_alert=True
                )
                return
            text = LucienVoice.fulfillment_admin_wizard_select_tariff()
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=build_edit_tariff_buttons(product_id, tariffs)
            )
            next_state = ProductEditStates.selecting_tariff
        elif field == "story_node":
            nodes = store_service.get_story_nodes_for_product_edit(product_id)
            if not nodes:
                await callback.answer(
                    LucienVoice.fulfillment_admin_wizard_no_story_nodes(), show_alert=True
                )
                return
            text = LucienVoice.fulfillment_admin_wizard_select_story_node()
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=build_edit_story_node_buttons(product_id, nodes)
            )
            next_state = ProductEditStates.selecting_story_node
        else:
            await callback.answer("Campo no valido", show_alert=True)
            return

        await callback.message.edit_text(text, reply_markup=keyboard)
        await state.set_state(next_state)
        await callback.answer()


@router.message(ProductEditStates.waiting_name)
async def process_edit_product_name(message: Message, state: FSMContext):
    """Procesa nuevo nombre del producto"""
    name = message.text.strip()
    if len(name) < 3:
        await message.answer("El nombre debe tener al menos 3 caracteres.")
        return

    data = await state.get_data()
    product_id = data.get("edit_product_id")

    with get_service(StoreService) as store_service:
        success = store_service.update_product(product_id, name=name)
        await _finish_product_edit(message, state, product_id, success, "nombre")


@router.message(ProductEditStates.waiting_description)
async def process_edit_product_description(message: Message, state: FSMContext):
    """Procesa nueva descripcion del producto"""
    description = None if message.text == "/skip" else message.text.strip()
    data = await state.get_data()
    product_id = data.get("edit_product_id")

    with get_service(StoreService) as store_service:
        success = store_service.update_product(product_id, description=description)
        await _finish_product_edit(message, state, product_id, success, "descripcion")


@router.callback_query(
    ProductEditStates.selecting_package, SelectPkgEditProductCallback.filter()
)
async def process_edit_product_package(
    callback: CallbackQuery, state: FSMContext, callback_data: SelectPkgEditProductCallback
):
    """Procesa nuevo paquete del producto"""
    product_id = callback_data.product_id
    package_id = callback_data.package_id

    with get_service(StoreService) as store_service:
        success = store_service.update_product(product_id, package_id=package_id)
        await _finish_product_edit(callback, state, product_id, success, "paquete")


@router.callback_query(
    ProductEditStates.selecting_tier, SelectTierEditProductCallback.filter()
)
async def process_edit_product_tier(
    callback: CallbackQuery, state: FSMContext, callback_data: SelectTierEditProductCallback
):
    """Procesa nuevo tier del producto."""
    product_id = callback_data.product_id
    tier_id = callback_data.tier_id

    with get_service(StoreService) as store_service:
        success = store_service.update_product(product_id, tier_id=tier_id)
        await _finish_product_edit(callback, state, product_id, success, "nivel")


@router.callback_query(
    ProductEditStates.selecting_tariff, SelectTariffEditProductCallback.filter()
)
async def process_edit_product_tariff(
    callback: CallbackQuery, state: FSMContext, callback_data: SelectTariffEditProductCallback
):
    """Procesa nueva tarifa VIP del producto."""
    product_id = callback_data.product_id

    with get_service(StoreService) as store_service:
        success = store_service.update_product(product_id, tariff_id=callback_data.tariff_id)
        await _finish_product_edit(callback, state, product_id, success, "tarifa")


@router.callback_query(
    ProductEditStates.selecting_story_node, SelectStoryNodeEditProductCallback.filter()
)
async def process_edit_product_story_node(
    callback: CallbackQuery,
    state: FSMContext,
    callback_data: SelectStoryNodeEditProductCallback,
):
    """Procesa nuevo nodo narrativo del producto."""
    product_id = callback_data.product_id

    with get_service(StoreService) as store_service:
        success = store_service.update_product(
            product_id, story_node_id=callback_data.story_node_id
        )
        await _finish_product_edit(callback, state, product_id, success, "nodo narrativo")


@router.message(ProductEditStates.waiting_price)
async def process_edit_product_price(message: Message, state: FSMContext):
    """Procesa nuevo precio del producto"""
    try:
        price = int(message.text.strip())
        if price < 1:
            raise ValueError("Debe ser mayor a 0")
    except ValueError:
        await message.answer("Por favor indica un numero valido mayor a 0.")
        return

    data = await state.get_data()
    product_id = data.get("edit_product_id")

    with get_service(StoreService) as store_service:
        success = store_service.update_product(product_id, price=price)
        await _finish_product_edit(message, state, product_id, success, "precio")


@router.callback_query(ProductEditStates.waiting_stock, F.data == "edit_product_stock_unlimited")
async def edit_product_stock_unlimited(callback: CallbackQuery, state: FSMContext):
    """Establece stock ilimitado al editar"""
    data = await state.get_data()
    product_id = data.get("edit_product_id")

    with get_service(StoreService) as store_service:
        success = store_service.update_product(product_id, stock=-1)
        await _finish_product_edit(callback, state, product_id, success, "stock")


@router.callback_query(ProductEditStates.waiting_stock, F.data == "edit_product_stock_limited")
async def edit_product_stock_limited(callback: CallbackQuery, state: FSMContext):
    """Pide cantidad limitada al editar stock"""
    data = await state.get_data()
    product_id = data.get("edit_product_id")

    await callback.message.edit_text(
        "🎩 Lucien:\n\nIndica la nueva cantidad de unidades disponibles:\nEjemplo: 50",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="❌ Cancelar",
                        callback_data=EditProductCallback(product_id=product_id).pack(),
                    )
                ]
            ]
        ),
    )
    await callback.answer()


@router.message(ProductEditStates.waiting_stock)
async def process_edit_product_stock(message: Message, state: FSMContext):
    """Procesa nuevo stock del producto"""
    try:
        stock = int(message.text.strip())
        if stock < 0:
            raise ValueError("Debe ser 0 o mayor")
    except ValueError:
        await message.answer("Indica un numero valido (0 o mayor).")
        return

    data = await state.get_data()
    product_id = data.get("edit_product_id")

    with get_service(StoreService) as store_service:
        success = store_service.update_product(product_id, stock=stock)
        await _finish_product_edit(message, state, product_id, success, "stock")


async def _finish_product_edit(target, state: FSMContext, product_id: int, success: bool, field: str):
    """Muestra resultado de edición y limpia estado FSM."""
    if success:
        text = f"🎩 Lucien:\n\n✅ {field.capitalize()} actualizado correctamente."
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📦 Ver producto",
                        callback_data=ProductAdminDetailCallback(product_id=product_id).pack(),
                    )
                ],
                [InlineKeyboardButton(text="🔙 Tienda", callback_data="admin_store")],
            ]
        )
    else:
        text = f"🎩 Lucien:\n\nError al actualizar el {field}."
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔙 Volver",
                        callback_data=EditProductCallback(product_id=product_id).pack(),
                    )
                ]
            ]
        )

    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=keyboard)
        await target.answer()
    else:
        await target.answer(text, reply_markup=keyboard)

    await state.clear()


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

        success = store_service.update_product(product_id, is_active=not product.is_active)
        if not success:
            await callback.answer("No se pudo actualizar el producto", show_alert=True)
            return

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
