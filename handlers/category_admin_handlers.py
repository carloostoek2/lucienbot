"""
Handlers de Administración de Categorías - Lucien Bot

Gestión de categorías para organizar paquetes en la tienda.
"""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from keyboards.callback_data import (
    CategoryAdminConfirmDeleteCallback,
    CategoryAdminDeleteCallback,
    CategoryAdminDetailCallback,
    CategoryAdminToggleCallback,
    CategoryAssignCallback,
    PackageAssignCallback,
)
from services import get_service
from services.package_service import PackageService
from utils.admin import is_admin

logger = logging.getLogger(__name__)
router = Router()


# Estados para FSM del Wizard de Categorías
class CategoryWizardStates(StatesGroup):
    waiting_name = State()
    waiting_description = State()
    waiting_order = State()
    confirming = State()


class AssignCategoryStates(StatesGroup):
    selecting_category = State()
    selecting_package = State()
    confirming = State()


# ==================== MENÚ PRINCIPAL ====================


@router.callback_query(F.data == "manage_categories", lambda cb: is_admin(cb.from_user.id))
async def manage_categories_menu(callback: CallbackQuery):
    """Menú principal de gestión de categorías"""
    with get_service(PackageService) as package_service:
        categories = package_service.get_all_categories(active_only=False)

        active_count = sum(1 for c in categories if c.is_active)

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="➕ Crear categoría", callback_data="create_category")],
                [InlineKeyboardButton(text="📋 Ver categorías", callback_data="list_categories")],
                [
                    InlineKeyboardButton(
                        text="📦 Asignar paquete a categoría",
                        callback_data="assign_package_category",
                    )
                ],
                [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_store")],
            ]
        )

        await callback.message.edit_text(
            f"""🎩 <b>Lucien:</b>

        <i>Las estanterías donde reposan los tesoros...</i>

        📊 Resumen:
           • Categorías activas: {active_count}
           • Total categorías: {len(categories)}

        ¿Qué deseas hacer?""",
            reply_markup=keyboard,
        )
        await callback.answer()

    # ==================== WIZARD CREAR CATEGORÍA ====================


@router.callback_query(F.data == "create_category", lambda cb: is_admin(cb.from_user.id))
async def create_category_start(callback: CallbackQuery, state: FSMContext):
    """Inicia wizard de creación de categoría"""
    await callback.message.edit_text(
        "🎩 <b>Lucien:</b>\n\n"
        "<i>Vamos a crear una nueva estantería...</i>\n\n"
        "Paso 1 de 3: Nombre de la categoría\n\n"
        "Indica un nombre descriptivo:\n"
        "Ejemplo: Fotos Exclusivas",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="❌ Cancelar", callback_data="manage_categories")]
            ]
        ),
    )
    await state.set_state(CategoryWizardStates.waiting_name)
    await callback.answer()


@router.message(CategoryWizardStates.waiting_name)
async def process_category_name(message: Message, state: FSMContext):
    """Procesa nombre de la categoría"""
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("El nombre debe tener al menos 2 caracteres.")
        return

    await state.update_data(name=name)
    await message.answer(
        "🎩 <b>Lucien:</b>\n\n"
        "<i>Paso 2 de 3...</i>\n\n"
        "Descripción de la categoría (opcional):\n"
        "Ejemplo: Colección de fotos exclusivas de Diana\n\n"
        "O envía /skip para omitir.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="❌ Cancelar", callback_data="manage_categories")]
            ]
        ),
    )
    await state.set_state(CategoryWizardStates.waiting_description)


@router.message(CategoryWizardStates.waiting_description)
async def process_category_description(message: Message, state: FSMContext):
    """Procesa descripción de la categoría"""
    description = None if message.text == "/skip" else message.text.strip()
    await state.update_data(description=description)

    await message.answer(
        "🎩 <b>Lucien:</b>\n\n"
        "<i>Paso 3 de 3...</i>\n\n"
        "Orden de visualización (número):\n"
        "Las categorías se ordenan de menor a mayor.\n"
        "Ejemplo: 1 (primera), 2 (segunda)...",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="❌ Cancelar", callback_data="manage_categories")]
            ]
        ),
    )
    await state.set_state(CategoryWizardStates.waiting_order)


@router.message(CategoryWizardStates.waiting_order)
async def process_category_order(message: Message, state: FSMContext):
    """Procesa orden de la categoría"""
    try:
        order = int(message.text.strip())
        if order < 0:
            raise ValueError("Debe ser positivo")
    except ValueError:
        await message.answer("Por favor indica un número válido mayor o igual a 0.")
        return

    await state.update_data(order_index=order)

    # Mostrar confirmación
    data = await state.get_data()
    name = data.get("name", "")
    description = data.get("description", "Sin descripción")
    order_index = data.get("order_index", 0)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Crear", callback_data="confirm_create_category")],
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="manage_categories")],
        ]
    )

    await message.answer(
        f"""🎩 <b>Lucien:</b>

<i>Resumen de la categoría:</i>

📁 <b>{name}</b>
📝 {description}
🔢 Orden: {order_index}

¿Crear esta categoría?""",
        reply_markup=keyboard,
    )
    await state.set_state(CategoryWizardStates.confirming)


@router.callback_query(CategoryWizardStates.confirming, F.data == "confirm_create_category")
async def confirm_create_category(callback: CallbackQuery, state: FSMContext):
    """Crea la categoría"""
    data = await state.get_data()
    with get_service(PackageService) as package_service:
        try:
            category = package_service.create_category(
                name=data.get("name"),
                description=data.get("description"),
                order_index=data.get("order_index", 0),
            )

            await callback.message.edit_text(
                f"""🎩 <b>Lucien:</b>

        <i>✅ Nueva estantería creada...</i>

        📁 <b>{category.name}</b>
        🔢 Orden: {category.order_index}

        La categoría está lista para recibir tesoros.""",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="📦 Asignar paquete", callback_data="assign_package_category"
                            )
                        ],
                        [InlineKeyboardButton(text="🔙 Volver", callback_data="manage_categories")],
                    ]
                ),
            )
            logger.info(f"Categoría creada: {category.name} por admin {callback.from_user.id}")

        except Exception as e:
            logger.error(f"Error creando categoría: {e}")
            await callback.message.edit_text(
                "Error al crear la categoría.",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Volver", callback_data="manage_categories")]
                    ]
                ),
            )

        await state.clear()
        await callback.answer()

    # ==================== LISTAR CATEGORÍAS ====================


@router.callback_query(F.data == "list_categories", lambda cb: is_admin(cb.from_user.id))
async def list_categories(callback: CallbackQuery):
    """Lista todas las categorías"""
    with get_service(PackageService) as package_service:
        categories = package_service.get_all_categories(active_only=False)

        if not categories:
            await callback.message.edit_text(
                "🎩 <b>Lucien:</b>\n\n"
                "<i>No hay estanterías creadas...</i>\n\n"
                "Crea una categoría para organizar los tesoros.",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="➕ Crear categoría", callback_data="create_category"
                            )
                        ],
                        [InlineKeyboardButton(text="🔙 Volver", callback_data="manage_categories")],
                    ]
                ),
            )
            await callback.answer()
            return

        text = "🎩 <b>Lucien:</b>\n\n<i>Las estanterías del reino:</i>\n\n"
        buttons = []

        for category in categories:
            status = "✅" if category.is_active else "❌"
            package_count = len(category.packages) if category.packages else 0
            text += f"{status} <b>{category.name}</b>\n"
            text += f"   📦 {package_count} paquetes | 🔢 {category.order_index}\n\n"

            buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"{status} {category.name[:30]}",
                        callback_data=CategoryAdminDetailCallback(category_id=category.id).pack(),
                    )
                ]
            )

        buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="manage_categories")])

        await callback.message.edit_text(
            text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
        await callback.answer()


@router.callback_query(CategoryAdminDetailCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def category_admin_detail(
    callback: CallbackQuery, callback_data: CategoryAdminDetailCallback
):
    """Muestra detalles de una categoría"""
    category_id = callback_data.category_id

    with get_service(PackageService) as package_service:
        category = package_service.get_category(category_id)

        if not category:
            await callback.answer("Categoría no encontrada", show_alert=True)
            return

        status = "✅ Activa" if category.is_active else "❌ Inactiva"
        package_count = len(category.packages) if category.packages else 0

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=f"{'Desactivar' if category.is_active else 'Activar'}",
                        callback_data=CategoryAdminToggleCallback(category_id=category_id).pack(),
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🗑️ Eliminar",
                        callback_data=CategoryAdminDeleteCallback(category_id=category_id).pack(),
                    )
                ],
                [InlineKeyboardButton(text="🔙 Volver", callback_data="list_categories")],
            ]
        )

        await callback.message.edit_text(
            f"""🎩 <b>Lucien:</b>

        <i>Detalles de la estantería:</i>

        📁 <b>{category.name}</b>
        📝 {category.description or "Sin descripción"}
        🔢 Orden: {category.order_index}
        📦 Paquetes: {package_count}
        Estado: {status}

        ¿Qué deseas hacer?""",
            reply_markup=keyboard,
        )
        await callback.answer()
        logger.info(
            f"category_admin_detail | view | user_id={callback.from_user.id} | category_id={category_id}"
        )


@router.callback_query(CategoryAdminToggleCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def toggle_category(callback: CallbackQuery, callback_data: CategoryAdminToggleCallback):
    """Activa/desactiva una categoría"""
    category_id = callback_data.category_id

    with get_service(PackageService) as package_service:
        category = package_service.get_category(category_id)

        if not category:
            await callback.answer("Categoría no encontrada", show_alert=True)
            return

        package_service.update_category(category_id, is_active=not category.is_active)

        status = "activada" if not category.is_active else "desactivada"
        await callback.answer(f"Categoría {status}")
        await category_admin_detail(callback, CategoryAdminDetailCallback(category_id=category_id))
        logger.info(
            f"toggle_category | toggle | user_id={callback.from_user.id} | category_id={category_id}"
        )


@router.callback_query(CategoryAdminDeleteCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def delete_category_confirm(
    callback: CallbackQuery, callback_data: CategoryAdminDeleteCallback
):
    """Confirma eliminación de categoría"""
    category_id = callback_data.category_id

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Sí, eliminar",
                    callback_data=CategoryAdminConfirmDeleteCallback(
                        category_id=category_id
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Cancelar",
                    callback_data=CategoryAdminDetailCallback(category_id=category_id).pack(),
                )
            ],
        ]
    )

    await callback.message.edit_text(
        "🎩 <b>Lucien:</b>\n\n"
        "<i>¿Estás seguro de eliminar esta estantería?</i>\n\n"
        "Los paquetes asignados quedarán sin categoría.\n"
        "Esta acción no se puede deshacer.",
        reply_markup=keyboard,
    )
    await callback.answer()
    logger.info(
        f"delete_category_confirm | confirm | user_id={callback.from_user.id} | category_id={category_id}"
    )


@router.callback_query(
    CategoryAdminConfirmDeleteCallback.filter(), lambda cb: is_admin(cb.from_user.id)
)
async def confirm_delete_category(
    callback: CallbackQuery, callback_data: CategoryAdminConfirmDeleteCallback
):
    """Elimina la categoría"""
    category_id = callback_data.category_id

    with get_service(PackageService) as package_service:
        success = package_service.delete_category(category_id)

        if success:
            await callback.message.edit_text(
                "🎩 <b>Lucien:</b>\n\n<i>✅ Estantería eliminada...</i>",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Volver", callback_data="list_categories")]
                    ]
                ),
            )
            logger.info(
                f"confirm_delete_category | delete | user_id={callback.from_user.id} | category_id={category_id}"
            )
        else:
            await callback.message.edit_text(
                "Error al eliminar la categoría.",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Volver", callback_data="list_categories")]
                    ]
                ),
            )
        await callback.answer()

    # ==================== ASIGNAR PAQUETE A CATEGORÍA ====================


@router.callback_query(F.data == "assign_package_category", lambda cb: is_admin(cb.from_user.id))
async def assign_package_category_start(callback: CallbackQuery, state: FSMContext):
    """Inicia asignación de paquete a categoría"""
    with get_service(PackageService) as package_service:
        categories = package_service.get_all_categories(active_only=True)

        if not categories:
            await callback.message.edit_text(
                "🎩 <b>Lucien:</b>\n\n"
                "<i>No hay estanterías disponibles...</i>\n\n"
                "Crea una categoría primero.",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="➕ Crear categoría", callback_data="create_category"
                            )
                        ],
                        [InlineKeyboardButton(text="🔙 Volver", callback_data="manage_categories")],
                    ]
                ),
            )
            await callback.answer()
            return

        buttons = []
        for category in categories:
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"📁 {category.name}",
                        callback_data=CategoryAssignCallback(category_id=category.id).pack(),
                    )
                ]
            )

        buttons.append(
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="manage_categories")]
        )

        await callback.message.edit_text(
            "🎩 <b>Lucien:</b>\n\n<i>Selecciona una estantería...</i>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        )
        await state.set_state(AssignCategoryStates.selecting_category)
        await callback.answer()


@router.callback_query(AssignCategoryStates.selecting_category, CategoryAssignCallback.filter())
async def select_category_for_assign(
    callback: CallbackQuery, callback_data: CategoryAssignCallback, state: FSMContext
):
    """Selecciona categoría y muestra paquetes"""
    category_id = callback_data.category_id

    with get_service(PackageService) as package_service:
        category = package_service.get_category(category_id)

        if not category:
            await callback.answer("Categoría no encontrada", show_alert=True)
            return

        await state.update_data(category_id=category_id, category_name=category.name)

        # Mostrar paquetes sin categoría
        packages = package_service.get_all_packages(active_only=True)
        uncategorized = [p for p in packages if p.category_id is None]

        if not uncategorized:
            await callback.message.edit_text(
                "🎩 <b>Lucien:</b>\n\n"
                "<i>No hay tesoros sin estantería...</i>\n\n"
                "Todos los paquetes ya están categorizados.",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Volver", callback_data="manage_categories")]
                    ]
                ),
            )
            await state.clear()
            await callback.answer()
            return

        buttons = []
        for package in uncategorized:
            file_count = len(package.files) if package.files else 0
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"📦 {package.name} ({file_count} archivos)",
                        callback_data=PackageAssignCallback(package_id=package.id).pack(),
                    )
                ]
            )

        buttons.append(
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="manage_categories")]
        )

        await callback.message.edit_text(
            f"🎩 <b>Lucien:</b>\n\n<i>Selecciona un tesoro para '{category.name}'...</i>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        )
        await state.set_state(AssignCategoryStates.selecting_package)
        await callback.answer()


@router.callback_query(AssignCategoryStates.selecting_package, PackageAssignCallback.filter())
async def select_package_for_assign(
    callback: CallbackQuery, callback_data: PackageAssignCallback, state: FSMContext
):
    """Confirma asignación de paquete a categoría"""
    package_id = callback_data.package_id

    data = await state.get_data()
    data.get("category_id")
    category_name = data.get("category_name")

    with get_service(PackageService) as package_service:
        package = package_service.get_package(package_id)

        if not package:
            await callback.answer("Paquete no encontrado", show_alert=True)
            return

        await state.update_data(package_id=package_id, package_name=package.name)

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✅ Confirmar", callback_data="confirm_assign_package")],
                [InlineKeyboardButton(text="❌ Cancelar", callback_data="manage_categories")],
            ]
        )

        await callback.message.edit_text(
            f"""🎩 <b>Lucien:</b>

        <i>Confirmar asignación:</i>

        📦 <b>{package.name}</b>
        ➡️
        📁 <b>{category_name}</b>

        ¿Confirmar?""",
            reply_markup=keyboard,
        )
        await state.set_state(AssignCategoryStates.confirming)
        await callback.answer()


@router.callback_query(AssignCategoryStates.confirming, F.data == "confirm_assign_package")
async def confirm_assign_package(callback: CallbackQuery, state: FSMContext):
    """Ejecuta asignación de paquete a categoría"""
    data = await state.get_data()
    category_id = data.get("category_id")
    package_id = data.get("package_id")
    package_name = data.get("package_name")
    category_name = data.get("category_name")

    with get_service(PackageService) as package_service:
        success = package_service.assign_package_to_category(package_id, category_id)

        if success:
            await callback.message.edit_text(
                f"""🎩 <b>Lucien:</b>

        <i>✅ Tesoro asignado...</i>

        📦 <b>{package_name}</b>
        📁 <b>{category_name}</b>

        El paquete ahora reposa en su estantería.""",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="📦 Asignar otro", callback_data="assign_package_category"
                            )
                        ],
                        [InlineKeyboardButton(text="🔙 Volver", callback_data="manage_categories")],
                    ]
                ),
            )
            logger.info(
                f"Paquete {package_id} asignado a categoría {category_id} por admin {callback.from_user.id}"
            )
        else:
            await callback.message.edit_text(
                "Error al asignar el paquete.",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Volver", callback_data="manage_categories")]
                    ]
                ),
            )

        await state.clear()
        await callback.answer()
