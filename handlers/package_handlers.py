"""
Handlers de Paquetes - Lucien Bot

Wizard de creación y gestión de paquetes de contenido.
"""

import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from keyboards.callback_data import (
    ConfirmDeleteFileCallback,
    ContinueDeleteFilesCallback,
    DeleteFilePkgCallback,
    DeletePackageCallback,
    DeletePackageFilesCallback,
    ExecuteDeleteFileCallback,
    FinishDeleteFilesCallback,
    PackageDetailCallback,
    PackageListCallback,
    SendPackageSelectCallback,
    TogglePackageCallback,
    UpdatePackageSelectCallback,
    ViewPackageFilesCallback,
)
from keyboards.inline_keyboards import back_keyboard, cancel_keyboard
from services import get_service
from services.package_service import PackageService
from utils.admin import is_admin
from utils.lucien_voice import LucienVoice

logger = logging.getLogger(__name__)
router = Router()


# Estados para FSM del Wizard de Paquetes
class PackageWizardStates(StatesGroup):
    waiting_name = State()
    waiting_description = State()
    waiting_files = State()
    waiting_store_stock = State()
    waiting_reward_stock = State()
    confirming = State()


# Estados para enviar paquete a usuario
class SendPackageStates(StatesGroup):
    selecting_package = State()
    waiting_user_id = State()
    confirming = State()


# Estados para actualizar paquete (agregar archivos)
class UpdatePackageStates(StatesGroup):
    selecting_package = State()
    waiting_files = State()
    confirming = State()


# Estados para eliminar archivos de paquete
class DeleteFileStates(StatesGroup):
    selecting_package = State()
    deleting_files = State()


# ==================== MENÚ DE PAQUETES ====================


@router.callback_query(F.data == "manage_packages", lambda cb: is_admin(cb.from_user.id))
async def manage_packages_menu(callback: CallbackQuery):
    """Menú principal de gestión de paquetes"""
    with get_service(PackageService) as package_service:
        packages = package_service.get_all_packages(active_only=False)

        active_count = sum(1 for p in packages if p.is_active)
        inactive_count = len(packages) - active_count

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="➕ Crear nuevo paquete", callback_data="create_package"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📝 Actualizar paquete (agregar archivos)",
                        callback_data="update_package_add_files",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🗑️ Eliminar archivos de paquete", callback_data="pkgfiles_delete_menu"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📤 Enviar paquete a usuario", callback_data="send_package_to_user"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📋 Ver paquetes activos",
                        callback_data=PackageListCallback(list_type="active").pack(),
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📋 Ver todos los paquetes",
                        callback_data=PackageListCallback(list_type="all").pack(),
                    )
                ],
                [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_gamification")],
            ]
        )

        await callback.message.edit_text(
            f"""🎩 <b>Lucien:</b>

        <i>Los tesoros que Diana ha seleccionado...</i>

        📦 <b>Gestión de Paquetes</b>

        📊 <b>Estadísticas:</b>
           • Activos: {active_count}
           • Inactivos: {inactive_count}
           • Total: {len(packages)}

        <i>Los paquetes pueden entregarse como recompensas o venderse en la tienda.</i>""",
            reply_markup=keyboard,
            parse_mode="HTML",
        )
        await callback.answer()

    # ==================== LISTAR PAQUETES ====================


@router.callback_query(PackageListCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def list_packages(callback: CallbackQuery, callback_data: PackageListCallback):
    """Lista los paquetes"""
    list_type = callback_data.list_type
    active_only = list_type == "active"

    with get_service(PackageService) as package_service:
        packages = package_service.get_all_packages(active_only=active_only)

        if not packages:
            await callback.message.edit_text(
                """🎩 <b>Lucien:</b>

        <i>No hay paquetes registrados en los archivos...</i>

        👉 <i>Cree un paquete primero usando "Crear nuevo paquete".</i>""",
                reply_markup=back_keyboard("manage_packages"),
                parse_mode="HTML",
            )
            await callback.answer()
            return

        text = f"""🎩 <b>Lucien:</b>

        <i>Los tesoros del reino...</i>

        📦 <b>Paquetes {"activos" if active_only else "registrados"}:</b>

        """

        buttons = []
        for pkg in packages:
            status = "✅" if pkg.is_active else "❌"
            store_info = (
                "N/D"
                if pkg.store_stock == -2
                else ("∞" if pkg.store_stock == -1 else str(pkg.store_stock))
            )
            reward_info = (
                "N/D"
                if pkg.reward_stock == -2
                else ("∞" if pkg.reward_stock == -1 else str(pkg.reward_stock))
            )

            text += f"{status} <b>{pkg.name}</b>\n"
            text += f"   📁 {pkg.file_count} archivos | 🛒 {store_info} | 🎁 {reward_info}\n\n"

            buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"{status} {pkg.name[:30]}",
                        callback_data=PackageDetailCallback(package_id=pkg.id).pack(),
                    )
                ]
            )

        buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="manage_packages")])

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()


@router.callback_query(PackageDetailCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def package_detail(callback: CallbackQuery, callback_data: PackageDetailCallback):
    """Muestra detalles de un paquete"""
    package_id = callback_data.package_id

    with get_service(PackageService) as package_service:
        package = package_service.get_package(package_id)

        if not package:
            await callback.answer("Paquete no encontrado", show_alert=True)
            return

        files = package_service.get_package_files(package_id)

        store_text = (
            "No disponible"
            if package.store_stock == -2
            else ("Ilimitado" if package.store_stock == -1 else str(package.store_stock))
        )
        reward_text = (
            "No disponible"
            if package.reward_stock == -2
            else ("Ilimitado" if package.reward_stock == -1 else str(package.reward_stock))
        )
        status = "✅ Activo" if package.is_active else "❌ Inactivo"

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="👁️ Ver archivos",
                        callback_data=ViewPackageFilesCallback(package_id=package_id).pack(),
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🗑️ Eliminar archivos",
                        callback_data=DeletePackageFilesCallback(package_id=package_id).pack(),
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=f"{'Desactivar' if package.is_active else 'Activar'}",
                        callback_data=TogglePackageCallback(package_id=package_id).pack(),
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🗑️ Eliminar paquete",
                        callback_data=DeletePackageCallback(
                            package_id=package_id, confirmed=False
                        ).pack(),
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔙 Volver", callback_data=PackageListCallback(list_type="all").pack()
                    )
                ],
            ]
        )

        await callback.message.edit_text(
            f"""🎩 <b>Lucien:</b>

        <i>Detalles del tesoro seleccionado...</i>

        📦 <b>{package.name}</b>

        📝 <b>Descripción:</b>
        <i>{package.description or "Sin descripción"}</i>

        📊 <b>Información:</b>
           • Estado: {status}
           • Archivos: {len(files)}
           • Stock tienda: {store_text}
           • Stock recompensas: {reward_text}

        <i>¿Qué desea hacer con este paquete?</i>""",
            reply_markup=keyboard,
            parse_mode="HTML",
        )
        await callback.answer()


@router.callback_query(TogglePackageCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def toggle_package(callback: CallbackQuery, callback_data: TogglePackageCallback):
    """Activa/desactiva un paquete"""
    package_id = callback_data.package_id

    with get_service(PackageService) as package_service:
        package = package_service.get_package(package_id)

        if not package:
            await callback.answer("Paquete no encontrado", show_alert=True)
            return

        package_service.update_package(package_id, is_active=not package.is_active)

        status = "activado" if not package.is_active else "desactivado"
        await callback.answer(f"Paquete {status}")
        await package_detail(callback, PackageDetailCallback(package_id=package_id))


@router.callback_query(DeletePackageCallback.filter(not F.confirmed))
async def delete_package_confirm(callback: CallbackQuery, callback_data: DeletePackageCallback):
    """Confirma eliminación de paquete"""
    if not is_admin(callback.from_user.id):
        await callback.answer("No autorizado", show_alert=True)
        return
    package_id = callback_data.package_id

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Sí, eliminar",
                    callback_data=DeletePackageCallback(
                        package_id=package_id, confirmed=True
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Cancelar",
                    callback_data=PackageDetailCallback(package_id=package_id).pack(),
                )
            ],
        ]
    )

    await callback.message.edit_text(
        """🎩 <b>Lucien:</b>

<i>¿Está seguro de que desea eliminar este paquete?</i>

⚠️ <b>Esta acción no se puede deshacer.</b>

Los archivos asociados también serán eliminados.""",
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(DeletePackageCallback.filter(F.confirmed))
async def confirm_delete_package(callback: CallbackQuery, callback_data: DeletePackageCallback):
    """Elimina el paquete"""
    if not is_admin(callback.from_user.id):
        await callback.answer("No autorizado", show_alert=True)
        return
    package_id = callback_data.package_id

    with get_service(PackageService) as package_service:
        success = package_service.delete_package(package_id)

        if success:
            await callback.message.edit_text(
                """🎩 <b>Lucien:</b>

        <i>El paquete ha sido removido de los archivos de Diana...</i>

        ✅ <b>Paquete eliminado correctamente.</b>""",
                reply_markup=back_keyboard("manage_packages"),
                parse_mode="HTML",
            )
        else:
            await callback.message.edit_text(
                LucienVoice.error_message("la eliminación del paquete"),
                reply_markup=back_keyboard("manage_packages"),
                parse_mode="HTML",
            )
        await callback.answer()

        # ==================== WIZARD DE CREACIÓN DE PAQUETE ====================


@router.callback_query(F.data == "create_package", lambda cb: is_admin(cb.from_user.id))
async def create_package_start(callback: CallbackQuery, state: FSMContext):
    """Inicia el wizard de creación de paquete"""
    await callback.message.edit_text(
        """🎩 <b>Lucien:</b>

<i>Vamos a crear un nuevo tesoro para el reino...</i>

📋 <b>Paso 1 de 6:</b> Nombre del paquete

Indique un nombre descriptivo para el paquete:
Ejemplo: <code>Fotos exclusivas de marzo</code>""",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(PackageWizardStates.waiting_name)
    await callback.answer()


@router.message(PackageWizardStates.waiting_name)
async def process_package_name(message: Message, state: FSMContext):
    """Procesa el nombre del paquete"""
    name = message.text.strip()

    if len(name) < 3:
        await message.answer(
            "🎩 <b>Lucien:</b>\n\n<i>El nombre debe tener al menos 3 caracteres...</i>",
            reply_markup=cancel_keyboard(),
            parse_mode="HTML",
        )
        return

    await state.update_data(name=name)

    await message.answer(
        """🎩 <b>Lucien:</b>

<i>Excelente nombre. Ahora la descripción...</i>

📋 <b>Paso 2 de 6:</b> Descripción del paquete

Escriba una descripción corta (opcional):
Ejemplo: <code>Una colección especial de fotos</code>

O envíe /skip para omitir.""",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(PackageWizardStates.waiting_description)


@router.message(PackageWizardStates.waiting_description)
async def process_package_description(message: Message, state: FSMContext):
    """Procesa la descripción del paquete"""
    description = None if message.text == "/skip" else message.text.strip()

    await state.update_data(description=description)

    await message.answer(
        """🎩 <b>Lucien:</b>

<i>Ahora los archivos del tesoro...</i>

📋 <b>Paso 3 de 6:</b> Cargar archivos

Envíe las fotos, videos o archivos que desea incluir en el paquete.

Puede enviar varios archivos uno por uno.

Cuando termine, envíe /done""",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML",
    )

    # Inicializar lista de archivos
    await state.update_data(files=[])
    await state.set_state(PackageWizardStates.waiting_files)


@router.message(PackageWizardStates.waiting_files)
async def process_package_files(message: Message, state: FSMContext):
    """Procesa los archivos del paquete"""
    if message.text == "/done":
        # Verificar que hay archivos
        data = await state.get_data()
        files = data.get("files", [])

        if not files:
            await message.answer(
                "🎩 <b>Lucien:</b>\n\n"
                "<i>Debe agregar al menos un archivo al paquete...</i>\n\n"
                "Envíe los archivos o /cancel para cancelar.",
                reply_markup=cancel_keyboard(),
                parse_mode="HTML",
            )
            return

        # Continuar al siguiente paso
        await ask_store_stock(message, state)
        return

    # Procesar archivo
    file_id = None
    file_type = None
    file_name = None
    file_size = None

    if message.photo:
        file_id = message.photo[-1].file_id
        file_type = "photo"
        file_size = message.photo[-1].file_size
    elif message.video:
        file_id = message.video.file_id
        file_type = "video"
        file_name = message.video.file_name
        file_size = message.video.file_size
    elif message.document:
        file_id = message.document.file_id
        file_type = "document"
        file_name = message.document.file_name
        file_size = message.document.file_size
    elif message.animation:
        file_id = message.animation.file_id
        file_type = "animation"
        file_name = message.animation.file_name
        file_size = message.animation.file_size
    else:
        await message.answer(
            "🎩 <b>Lucien:</b>\n\n"
            "<i>No reconocí el tipo de archivo.\n"
            "Por favor envíe fotos, videos, documentos o GIFs...</i>",
            reply_markup=cancel_keyboard(),
            parse_mode="HTML",
        )
        return

    # Agregar a la lista
    data = await state.get_data()
    files = data.get("files", [])
    files.append(
        {"file_id": file_id, "file_type": file_type, "file_name": file_name, "file_size": file_size}
    )
    await state.update_data(files=files)

    await message.answer(
        f"""🎩 <b>Lucien:</b>

✅ <b>Archivo agregado:</b> {file_type}

📊 <b>Total de archivos:</b> {len(files)}

<i>Envíe más archivos o /done para continuar.</i>""",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML",
    )


async def ask_store_stock(message: Message, state: FSMContext):
    """Pregunta por el stock de tienda"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="♾️ Ilimitado", callback_data="store_stock_unlimited")],
            [InlineKeyboardButton(text="📦 Limitado", callback_data="store_stock_limited")],
            [InlineKeyboardButton(text="🚫 No disponible", callback_data="store_stock_none")],
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="cancel")],
        ]
    )

    await message.answer(
        """🎩 <b>Lucien:</b>

<i>Configuremos la disponibilidad en la tienda...</i>

📋 <b>Paso 4 de 6:</b> Stock en tienda

¿El paquete estará disponible en la tienda?""",
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    await state.set_state(PackageWizardStates.waiting_store_stock)


@router.callback_query(PackageWizardStates.waiting_store_stock, F.data == "store_stock_unlimited")
async def store_stock_unlimited(callback: CallbackQuery, state: FSMContext):
    """Stock ilimitado en tienda"""
    await state.update_data(store_stock=-1)
    await ask_reward_stock(callback, state)
    await callback.answer()


@router.callback_query(PackageWizardStates.waiting_store_stock, F.data == "store_stock_none")
async def store_stock_none(callback: CallbackQuery, state: FSMContext):
    """No disponible en tienda"""
    await state.update_data(store_stock=-2)
    await ask_reward_stock(callback, state)
    await callback.answer()


@router.callback_query(PackageWizardStates.waiting_store_stock, F.data == "store_stock_limited")
async def store_stock_limited(callback: CallbackQuery, state: FSMContext):
    """Pide cantidad de stock limitado para tienda"""
    await callback.message.edit_text(
        """🎩 <b>Lucien:</b>

<i>Indique la cantidad de unidades disponibles para venta...</i>

📋 Stock en tienda:

Ejemplo: <code>10</code> para 10 unidades""",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(PackageWizardStates.waiting_store_stock)
async def process_store_stock(message: Message, state: FSMContext):
    """Procesa el stock de tienda"""
    try:
        stock = int(message.text.strip())
        if stock < 0:
            raise ValueError("Stock no puede ser negativo")
    except ValueError:
        await message.answer(
            "🎩 <b>Lucien:</b>\n\n<i>Por favor, indique un número válido (0 o mayor)...</i>",
            reply_markup=cancel_keyboard(),
            parse_mode="HTML",
        )
        return

    await state.update_data(store_stock=stock)
    await ask_reward_stock(message, state)


async def ask_reward_stock(target, state: FSMContext):
    """Pregunta por el stock de recompensas"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="♾️ Ilimitado", callback_data="reward_stock_unlimited")],
            [InlineKeyboardButton(text="📦 Limitado", callback_data="reward_stock_limited")],
            [InlineKeyboardButton(text="🚫 No disponible", callback_data="reward_stock_none")],
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="cancel")],
        ]
    )

    text = """🎩 <b>Lucien:</b>

<i>Configuremos la disponibilidad para recompensas...</i>

📋 <b>Paso 5 de 6:</b> Stock en recompensas

¿El paquete estará disponible para entrega como recompensa?"""

    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await target.answer(text, reply_markup=keyboard, parse_mode="HTML")

    await state.set_state(PackageWizardStates.waiting_reward_stock)


@router.callback_query(PackageWizardStates.waiting_reward_stock, F.data == "reward_stock_unlimited")
async def reward_stock_unlimited(callback: CallbackQuery, state: FSMContext):
    """Stock ilimitado en recompensas"""
    await state.update_data(reward_stock=-1)
    await show_package_preview(callback, state)
    await callback.answer()


@router.callback_query(PackageWizardStates.waiting_reward_stock, F.data == "reward_stock_none")
async def reward_stock_none(callback: CallbackQuery, state: FSMContext):
    """No disponible en recompensas"""
    await state.update_data(reward_stock=-2)
    await show_package_preview(callback, state)
    await callback.answer()


@router.callback_query(PackageWizardStates.waiting_reward_stock, F.data == "reward_stock_limited")
async def reward_stock_limited(callback: CallbackQuery, state: FSMContext):
    """Pide cantidad de stock limitado para recompensas"""
    await callback.message.edit_text(
        """🎩 <b>Lucien:</b>

<i>Indique la cantidad de unidades disponibles para recompensas...</i>

📋 Stock en recompensas:

Ejemplo: <code>50</code> para 50 unidades""",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(PackageWizardStates.waiting_reward_stock)
async def process_reward_stock(message: Message, state: FSMContext):
    """Procesa el stock de recompensas"""
    try:
        stock = int(message.text.strip())
        if stock < 0:
            raise ValueError("Stock no puede ser negativo")
    except ValueError:
        await message.answer(
            "🎩 <b>Lucien:</b>\n\n<i>Por favor, indique un número válido (0 o mayor)...</i>",
            reply_markup=cancel_keyboard(),
            parse_mode="HTML",
        )
        return

    await state.update_data(reward_stock=stock)
    await show_package_preview(message, state)


async def show_package_preview(target, state: FSMContext):
    """Muestra preview del paquete antes de crear"""
    data = await state.get_data()

    name = data.get("name", "")
    description = data.get("description", "Sin descripción")
    files = data.get("files", [])
    store_stock = data.get("store_stock", -1)
    reward_stock = data.get("reward_stock", -1)

    store_text = (
        "No disponible"
        if store_stock == -2
        else ("Ilimitado" if store_stock == -1 else str(store_stock))
    )
    reward_text = (
        "No disponible"
        if reward_stock == -2
        else ("Ilimitado" if reward_stock == -1 else str(reward_stock))
    )

    text = f"""🎩 <b>Lucien:</b>

<i>Permíteme mostrarle el resumen del tesoro...</i>

📦 <b>Resumen del Paquete:</b>

📛 <b>Nombre:</b> {name}
📝 <b>Descripción:</b> {description}
📁 <b>Archivos:</b> {len(files)}
🛒 <b>Stock tienda:</b> {store_text}
🎁 <b>Stock recompensas:</b> {reward_text}

<i>¿Desea crear este paquete?</i>"""

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Crear paquete", callback_data="confirm_create_package")],
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="manage_packages")],
        ]
    )

    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await target.answer(text, reply_markup=keyboard, parse_mode="HTML")

    await state.set_state(PackageWizardStates.confirming)


@router.callback_query(PackageWizardStates.confirming, F.data == "confirm_create_package")
async def confirm_create_package(callback: CallbackQuery, state: FSMContext):
    """Crea el paquete con todos los datos"""
    data = await state.get_data()

    with get_service(PackageService) as package_service:
        try:
            # Crear el paquete
            package = package_service.create_package(
                name=data["name"],
                description=data.get("description"),
                store_stock=data.get("store_stock", -1),
                reward_stock=data.get("reward_stock", -1),
                created_by=callback.from_user.id,
            )

            # Agregar archivos
            files = data.get("files", [])
            for i, file_data in enumerate(files):
                package_service.add_file_to_package(
                    package_id=package.id,
                    file_id=file_data["file_id"],
                    file_type=file_data["file_type"],
                    file_name=file_data.get("file_name"),
                    file_size=file_data.get("file_size"),
                    order_index=i,
                )

            await callback.message.edit_text(
                f"""🎩 <b>Lucien:</b>

        <i>El tesoro ha sido registrado en los archivos de Diana...</i>

        ✅ <b>Paquete creado exitosamente!</b>

        📦 <b>{package.name}</b>
        📁 {len(files)} archivo(s)

        <i>El paquete está listo para usarse en recompensas o tienda.</i>""",
                reply_markup=back_keyboard("manage_packages"),
                parse_mode="HTML",
            )

            logger.info(
                f"Paquete creado: {package.name} (ID: {package.id}) por admin {callback.from_user.id}"
            )

        except Exception as e:
            logger.error(f"Error creando paquete: {e}")
            await callback.message.edit_text(
                LucienVoice.error_message("la creación del paquete"),
                reply_markup=back_keyboard("manage_packages"),
                parse_mode="HTML",
            )

        await state.clear()
        await callback.answer()

    # ==================== ENVIAR PAQUETE A USUARIO (PRUEBA) ====================


@router.callback_query(F.data == "send_package_to_user", lambda cb: is_admin(cb.from_user.id))
async def send_package_to_user_start(callback: CallbackQuery, state: FSMContext):
    """Inicia envio de paquete a usuario"""
    with get_service(PackageService) as package_service:
        packages = package_service.get_all_packages(active_only=True)

        if not packages:
            await callback.message.edit_text(
                """🎩 Lucien:

        No hay paquetes disponibles.

        Crea un paquete primero.""",
                reply_markup=back_keyboard("manage_packages"),
            )
            await callback.answer()
            return

        buttons = []
        for pkg in packages:
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"{pkg.name} ({pkg.file_count} archivos)",
                        callback_data=SendPackageSelectCallback(package_id=pkg.id).pack(),
                    )
                ]
            )

        buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="manage_packages")])

        await callback.message.edit_text(
            """🎩 Lucien:

        Enviar paquete a usuario...

        Selecciona el paquete:""",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        )
        await state.set_state(SendPackageStates.selecting_package)
        await callback.answer()


@router.callback_query(SendPackageStates.selecting_package, SendPackageSelectCallback.filter())
async def select_package_to_send(
    callback: CallbackQuery, state: FSMContext, callback_data: SendPackageSelectCallback
):
    """Selecciona paquete y pide ID de usuario"""
    package_id = callback_data.package_id

    with get_service(PackageService) as package_service:
        package = package_service.get_package(package_id)

        if not package:
            await callback.answer("Paquete no encontrado", show_alert=True)
            return

        await state.update_data(package_id=package_id, package_name=package.name)

    await callback.message.edit_text(
        f"""🎩 Lucien:

        Paquete seleccionado: {package.name}

        Indica el ID del usuario destino:

        Ejemplo: 123456789

        (Obtén el ID desde @userinfobot)""",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Volver", callback_data="manage_packages")]
            ]
        ),
    )

    await state.set_state(SendPackageStates.waiting_user_id)
    await callback.answer()


@router.message(SendPackageStates.waiting_user_id)
async def process_user_id_for_package(message: Message, state: FSMContext, bot: Bot):
    """Procesa ID de usuario y envia paquete"""
    try:
        user_id = int(message.text.strip())
    except ValueError:
        await message.answer("Por favor indica un ID de usuario valido (numeros solo).")
        return

    data = await state.get_data()
    package_id = data.get("package_id")
    package_name = data.get("package_name")

    with get_service(PackageService) as package_service:
        # Enviar paquete
        await message.answer(f"Enviando paquete '{package_name}' al usuario {user_id}...")

        success, result_msg = await package_service.deliver_package_to_user(
            bot=bot, user_id=user_id, package_id=package_id
        )

        if success:
            await message.answer(
                f"✅ Paquete enviado exitosamente!\n\n{result_msg}",
                reply_markup=back_keyboard("manage_packages"),
            )
        else:
            await message.answer(
                f"❌ Error al enviar: {result_msg}", reply_markup=back_keyboard("manage_packages")
            )

        await state.clear()

    # ==================== VER ARCHIVOS DE PAQUETE (CON PREVIEW) ====================


@router.callback_query(ViewPackageFilesCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def view_package_files(
    callback: CallbackQuery, bot: Bot, callback_data: ViewPackageFilesCallback
):
    """Muestra los archivos de un paquete con preview"""
    package_id = callback_data.package_id

    with get_service(PackageService) as package_service:
        package = package_service.get_package(package_id)
        files = package_service.get_package_files(package_id)

        if not files:
            await callback.answer("El paquete no tiene archivos", show_alert=True)
            return

        # Enviar mensaje de introduccion
        await callback.message.edit_text(
            f"""🎩 Lucien:

        Mostrando archivos del paquete '{package.name}'...

        Total: {len(files)} archivo(s)

        Enviando previews...""",
            reply_markup=back_keyboard(PackageDetailCallback(package_id=package_id).pack()),
        )
        await callback.answer()

        # Enviar cada archivo como preview
        for i, file_entry in enumerate(files[:10], 1):  # Max 10 previews
            try:
                caption = (
                    f"{i}/{min(len(files), 10)}: {file_entry.file_name or file_entry.file_type}"
                )

                if file_entry.file_type == "photo":
                    await bot.send_photo(
                        chat_id=callback.from_user.id, photo=file_entry.file_id, caption=caption
                    )
                elif file_entry.file_type == "video":
                    await bot.send_video(
                        chat_id=callback.from_user.id, video=file_entry.file_id, caption=caption
                    )
                elif file_entry.file_type == "animation":
                    await bot.send_animation(
                        chat_id=callback.from_user.id, animation=file_entry.file_id, caption=caption
                    )
                else:  # document y otros
                    await bot.send_document(
                        chat_id=callback.from_user.id, document=file_entry.file_id, caption=caption
                    )
            except Exception as e:
                logger.error(f"Error enviando preview de archivo {file_entry.id}: {e}")
                await bot.send_message(
                    chat_id=callback.from_user.id, text=f"❌ Error al mostrar archivo {i}"
                )

    # ==================== ACTUALIZAR PAQUETE (AGREGAR ARCHIVOS) ====================


@router.callback_query(F.data == "update_package_add_files", lambda cb: is_admin(cb.from_user.id))
async def update_package_start(callback: CallbackQuery, state: FSMContext):
    """Inicia el proceso de actualizar un paquete agregando archivos"""
    with get_service(PackageService) as package_service:
        packages = package_service.get_all_packages(active_only=True)

        if not packages:
            await callback.message.edit_text(
                """🎩 <b>Lucien:</b>

        <i>No hay paquetes disponibles para actualizar...</i>

        👉 <i>Cree un paquete primero usando "Crear nuevo paquete".</i>""",
                reply_markup=back_keyboard("manage_packages"),
                parse_mode="HTML",
            )
            await callback.answer()
            return

        buttons = []
        for pkg in packages:
            status = "✅" if pkg.is_active else "❌"
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"{status} {pkg.name[:35]} ({pkg.file_count} archivos)",
                        callback_data=UpdatePackageSelectCallback(package_id=pkg.id).pack(),
                    )
                ]
            )

        buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="manage_packages")])

        await callback.message.edit_text(
            """🎩 <b>Lucien:</b>

        <i>Seleccione el tesoro al que desea agregar más archivos...</i>

        📦 <b>Paquetes disponibles:</b>

        <i>Haga clic en un paquete para agregar archivos.</i>""",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
            parse_mode="HTML",
        )
        await state.set_state(UpdatePackageStates.selecting_package)
        await callback.answer()


@router.callback_query(UpdatePackageStates.selecting_package, UpdatePackageSelectCallback.filter())
async def select_package_to_update(
    callback: CallbackQuery, state: FSMContext, callback_data: UpdatePackageSelectCallback
):
    """Selecciona el paquete a actualizar y pide archivos"""
    package_id = callback_data.package_id

    with get_service(PackageService) as package_service:
        package = package_service.get_package(package_id)

        if not package:
            await callback.answer("Paquete no encontrado", show_alert=True)
            return

        # Guardar datos en el estado
        await state.update_data(
            package_id=package_id,
            package_name=package.name,
            current_file_count=len(package_service.get_package_files(package_id)),
            new_files=[],
        )

        await callback.message.edit_text(
            f"""🎩 <b>Lucien:</b>

        <i>Paquete seleccionado: <b>{package.name}</b></i>

        📊 <b>Archivos actuales:</b> {len(package_service.get_package_files(package_id))}

        📋 <b>Paso 1:</b> Envíe los nuevos archivos

        Envíe las fotos, videos o archivos que desea <b>agregar</b> al paquete.

        Puede enviar varios archivos uno por uno.

        Cuando termine, envíe <code>/done</code>""",
            reply_markup=cancel_keyboard(),
            parse_mode="HTML",
        )
        await state.set_state(UpdatePackageStates.waiting_files)
        await callback.answer()


@router.message(UpdatePackageStates.waiting_files)
async def process_update_files(message: Message, state: FSMContext):
    """Procesa los archivos nuevos para agregar al paquete"""
    if message.text == "/done":
        # Verificar que hay archivos nuevos
        data = await state.get_data()
        new_files = data.get("new_files", [])

        if not new_files:
            await message.answer(
                """🎩 <b>Lucien:</b>

<i>No ha agregado ningún archivo nuevo...</i>

Envíe archivos o /cancel para cancelar.""",
                reply_markup=cancel_keyboard(),
                parse_mode="HTML",
            )
            return

        # Mostrar confirmación
        await show_update_confirmation(message, state)
        return

    # Procesar archivo
    file_id = None
    file_type = None
    file_name = None
    file_size = None

    if message.photo:
        file_id = message.photo[-1].file_id
        file_type = "photo"
        file_size = message.photo[-1].file_size
    elif message.video:
        file_id = message.video.file_id
        file_type = "video"
        file_name = message.video.file_name
        file_size = message.video.file_size
    elif message.document:
        file_id = message.document.file_id
        file_type = "document"
        file_name = message.document.file_name
        file_size = message.document.file_size
    elif message.animation:
        file_id = message.animation.file_id
        file_type = "animation"
        file_name = message.animation.file_name
        file_size = message.animation.file_size
    else:
        await message.answer(
            """🎩 <b>Lucien:</b>

<i>No reconocí el tipo de archivo.
Por favor envíe fotos, videos, documentos o GIFs...</i>""",
            reply_markup=cancel_keyboard(),
            parse_mode="HTML",
        )
        return

    # Agregar a la lista de nuevos archivos
    data = await state.get_data()
    new_files = data.get("new_files", [])
    new_files.append(
        {"file_id": file_id, "file_type": file_type, "file_name": file_name, "file_size": file_size}
    )
    await state.update_data(new_files=new_files)

    await message.answer(
        f"""🎩 <b>Lucien:</b>

✅ <b>Archivo agregado:</b> {file_type}

📊 <b>Nuevos archivos:</b> {len(new_files)}

<i>Envíe más archivos o /done para finalizar.</i>""",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML",
    )


async def show_update_confirmation(message: Message, state: FSMContext):
    """Muestra confirmación antes de actualizar el paquete"""
    data = await state.get_data()

    package_name = data.get("package_name", "")
    current_count = data.get("current_file_count", 0)
    new_files = data.get("new_files", [])
    total_files = current_count + len(new_files)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Confirmar y agregar archivos", callback_data="confirm_update_package"
                )
            ],
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="manage_packages")],
        ]
    )

    await message.answer(
        f"""🎩 <b>Lucien:</b>

<i>Permítame mostrarle el resumen de la actualización...</i>

📦 <b>Paquete:</b> {package_name}

📊 <b>Cambios:</b>
   • Archivos actuales: {current_count}
   • Archivos nuevos: {len(new_files)}
   • <b>Total después de actualizar:</b> {total_files}

<i>¿Desea confirmar la actualización?</i>""",
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    await state.set_state(UpdatePackageStates.confirming)


@router.callback_query(UpdatePackageStates.confirming, F.data == "confirm_update_package")
async def confirm_update_package(callback: CallbackQuery, state: FSMContext):
    """Confirma la actualización y agrega los archivos al paquete"""
    data = await state.get_data()

    package_id = data.get("package_id")
    package_name = data.get("package_name")
    new_files = data.get("new_files", [])

    with get_service(PackageService) as package_service:
        try:
            # Obtener el último índice de orden actual
            existing_files = package_service.get_package_files(package_id)
            last_index = len(existing_files)

            # Agregar cada archivo nuevo
            for i, file_data in enumerate(new_files):
                package_service.add_file_to_package(
                    package_id=package_id,
                    file_id=file_data["file_id"],
                    file_type=file_data["file_type"],
                    file_name=file_data.get("file_name"),
                    file_size=file_data.get("file_size"),
                    order_index=last_index + i,
                )

            total_files = len(existing_files) + len(new_files)

            await callback.message.edit_text(
                f"""🎩 <b>Lucien:</b>

        <i>El tesoro ha sido actualizado en los archivos de Diana...</i>

        ✅ <b>Paquete actualizado exitosamente!</b>

        📦 <b>{package_name}</b>
           • Archivos agregados: {len(new_files)}
           • <b>Total de archivos:</b> {total_files}

        <i>Los nuevos archivos están disponibles inmediatamente.</i>""",
                reply_markup=back_keyboard("manage_packages"),
                parse_mode="HTML",
            )

            logger.info(
                f"Paquete actualizado: {package_name} (ID: {package_id}) - "
                f"{len(new_files)} archivos agregados por admin {callback.from_user.id}"
            )

        except Exception as e:
            logger.error(f"Error actualizando paquete: {e}")
            await callback.message.edit_text(
                LucienVoice.error_message("la actualización del paquete"),
                reply_markup=back_keyboard("manage_packages"),
                parse_mode="HTML",
            )

        await state.clear()
        await callback.answer()

    # ==================== ELIMINAR ARCHIVOS DE PAQUETE ====================


@router.callback_query(F.data == "pkgfiles_delete_menu", lambda cb: is_admin(cb.from_user.id))
async def pkgfiles_delete_menu(callback: CallbackQuery, state: FSMContext):
    """Inicia el flujo de eliminar archivos desde el menú principal"""
    with get_service(PackageService) as package_service:
        packages = package_service.get_all_packages(active_only=True)

        if not packages:
            await callback.message.edit_text(
                """🎩 <b>Lucien:</b>

        <i>No hay paquetes disponibles...</i>

        👉 <i>Cree un paquete primero.</i>""",
                reply_markup=back_keyboard("manage_packages"),
                parse_mode="HTML",
            )
            await callback.answer()
            return

        buttons = []
        for pkg in packages:
            file_count = len(package_service.get_package_files(pkg.id))
            if file_count > 0:  # Solo mostrar paquetes con archivos
                buttons.append(
                    [
                        InlineKeyboardButton(
                            text=f"{pkg.name[:30]} ({file_count} archivos)",
                            callback_data=DeleteFilePkgCallback(package_id=pkg.id).pack(),
                        )
                    ]
                )

        if not buttons:
            await callback.message.edit_text(
                """🎩 <b>Lucien:</b>

        <i>No hay paquetes con archivos para eliminar...</i>

        👉 <i>Agregue archivos a un paquete primero.</i>""",
                reply_markup=back_keyboard("manage_packages"),
                parse_mode="HTML",
            )
            await callback.answer()
            return

        buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="manage_packages")])

        await callback.message.edit_text(
            """🎩 <b>Lucien:</b>

        <i>Seleccione el paquete del cual desea eliminar archivos...</i>

        🗑️ <b>Eliminar archivos:</b>

        <i>Solo se muestran paquetes que contienen archivos.</i>""",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
            parse_mode="HTML",
        )
        await state.set_state(DeleteFileStates.selecting_package)
        await callback.answer()


@router.callback_query(DeletePackageFilesCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def delete_package_files_start(
    callback: CallbackQuery, state: FSMContext, callback_data: DeletePackageFilesCallback
):
    """Inicia el flujo de eliminar archivos desde el detalle del paquete"""
    package_id = callback_data.package_id

    with get_service(PackageService) as package_service:
        package = package_service.get_package(package_id)
        files = package_service.get_package_files(package_id)

        if not package:
            await callback.answer("Paquete no encontrado", show_alert=True)
            return

        if not files:
            await callback.message.edit_text(
                """🎩 <b>Lucien:</b>

        <i>Este paquete no tiene archivos...</i>

        👉 <i>No hay nada que eliminar.</i>""",
                reply_markup=back_keyboard(PackageDetailCallback(package_id=package_id).pack()),
                parse_mode="HTML",
            )
            await callback.answer()
            return

        await state.update_data(package_id=package_id, package_name=package.name)
        await callback.message.edit_text(
            f"""🎩 <b>Lucien:</b>

        <i>Preparando vista de archivos para eliminar...</i>

        📦 <b>{package.name}</b>
        📁 {len(files)} archivo(s)

        <i>Enviando archivos con opción de eliminar...</i>""",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="❌ Cancelar", callback_data=f"package_detail_{package_id}"
                        )
                    ]
                ]
            ),
            parse_mode="HTML",
        )
        await callback.answer()
        await show_files_for_deletion(callback, state, bot=callback.bot)


@router.callback_query(DeleteFileStates.selecting_package, DeleteFilePkgCallback.filter())
async def select_package_for_delete_files(
    callback: CallbackQuery, state: FSMContext, callback_data: DeleteFilePkgCallback
):
    """Selecciona el paquete para eliminar archivos"""
    package_id = callback_data.package_id

    with get_service(PackageService) as package_service:
        package = package_service.get_package(package_id)
        files = package_service.get_package_files(package_id)

        if not package:
            await callback.answer("Paquete no encontrado", show_alert=True)
            return

        if not files:
            await callback.message.edit_text(
                """🎩 <b>Lucien:</b>

        <i>Este paquete no tiene archivos...</i>

        👉 <i>No hay nada que eliminar.</i>""",
                reply_markup=back_keyboard("pkgfiles_delete_menu"),
                parse_mode="HTML",
            )
            await callback.answer()
            return

        await state.update_data(package_id=package_id, package_name=package.name)
        await callback.message.edit_text(
            f"""🎩 <b>Lucien:</b>

        <i>Preparando vista de archivos para eliminar...</i>

        📦 <b>{package.name}</b>
        📁 {len(files)} archivo(s)

        <i>Enviando archivos con opción de eliminar...</i>""",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="❌ Cancelar", callback_data="pkgfiles_delete_menu")]
                ]
            ),
            parse_mode="HTML",
        )
        await callback.answer()
        await show_files_for_deletion(callback, state, bot=callback.bot)


async def show_files_for_deletion(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Muestra cada archivo con botón para eliminar"""
    data = await state.get_data()
    package_id = data.get("package_id")
    package_name = data.get("package_name")

    with get_service(PackageService) as package_service:
        files = package_service.get_package_files(package_id)

        if not files:
            await callback.message.edit_text(
                """🎩 <b>Lucien:</b>

        <i>El paquete ya no tiene archivos...</i>

        ✅ <b>Todos los archivos han sido eliminados.</b>""",
                reply_markup=back_keyboard(PackageDetailCallback(package_id=package_id).pack()),
                parse_mode="HTML",
            )
            await state.clear()
            return

        await state.set_state(DeleteFileStates.deleting_files)

        # Enviar mensaje con instrucciones
        await bot.send_message(
            chat_id=callback.from_user.id,
            text=f"""🎩 <b>Lucien:</b>

        <i>Archivos del paquete: <b>{package_name}</b></i>

        🗑️ <b>Haga clic en "Eliminar" para remover un archivo.</b>

        <i>Los archivos se muestran uno por uno con su preview.</i>""",
            parse_mode="HTML",
        )

        # Enviar cada archivo con botón de eliminar
        for i, file_entry in enumerate(files, 1):
            try:
                keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="🗑️ Eliminar este archivo",
                                callback_data=ConfirmDeleteFileCallback(
                                    file_id=file_entry.id
                                ).pack(),
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text="✅ Terminar",
                                callback_data=FinishDeleteFilesCallback(
                                    package_id=package_id
                                ).pack(),
                            )
                        ],
                    ]
                )

                caption = f"📁 {i}/{len(files)} | ID: {file_entry.id} | {file_entry.file_type}"

                if file_entry.file_type == "photo":
                    await bot.send_photo(
                        chat_id=callback.from_user.id,
                        photo=file_entry.file_id,
                        caption=caption,
                        reply_markup=keyboard,
                    )
                elif file_entry.file_type == "video":
                    await bot.send_video(
                        chat_id=callback.from_user.id,
                        video=file_entry.file_id,
                        caption=caption,
                        reply_markup=keyboard,
                    )
                elif file_entry.file_type == "animation":
                    await bot.send_animation(
                        chat_id=callback.from_user.id,
                        animation=file_entry.file_id,
                        caption=caption,
                        reply_markup=keyboard,
                    )
                else:  # document y otros
                    await bot.send_document(
                        chat_id=callback.from_user.id,
                        document=file_entry.file_id,
                        caption=caption,
                        reply_markup=keyboard,
                    )
            except Exception as e:
                logger.error(f"Error enviando archivo {file_entry.id}: {e}")
                await bot.send_message(
                    chat_id=callback.from_user.id,
                    text=f"❌ Error al mostrar archivo {i} (ID: {file_entry.id})",
                )


@router.callback_query(DeleteFileStates.deleting_files, ConfirmDeleteFileCallback.filter())
async def confirm_delete_file(
    callback: CallbackQuery, state: FSMContext, callback_data: ConfirmDeleteFileCallback
):
    """Muestra confirmación antes de eliminar el archivo"""
    file_id = callback_data.file_id

    data = await state.get_data()
    package_id = data.get("package_id")

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Sí, eliminar",
                    callback_data=ExecuteDeleteFileCallback(file_id=file_id).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Cancelar",
                    callback_data=ContinueDeleteFilesCallback(package_id=package_id).pack(),
                )
            ],
        ]
    )

    await callback.message.edit_caption(
        caption=f"{callback.message.caption}\n\n⚠️ <b>¿Eliminar este archivo?</b>",
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(DeleteFileStates.deleting_files, ExecuteDeleteFileCallback.filter())
async def execute_delete_file(
    callback: CallbackQuery, state: FSMContext, callback_data: ExecuteDeleteFileCallback
):
    """Ejecuta la eliminación del archivo"""
    file_id = callback_data.file_id

    data = await state.get_data()
    package_id = data.get("package_id")
    data.get("package_name")

    with get_service(PackageService) as package_service:
        try:
            success = package_service.remove_file_from_package(file_id)

            if success:
                await callback.message.edit_caption(
                    caption="✅ <b>Archivo eliminado correctamente.</b>",
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[
                            [
                                InlineKeyboardButton(
                                    text="🗑️ Eliminar más archivos",
                                    callback_data=ContinueDeleteFilesCallback(
                                        package_id=package_id
                                    ).pack(),
                                )
                            ],
                            [
                                InlineKeyboardButton(
                                    text="✅ Terminar",
                                    callback_data=FinishDeleteFilesCallback(
                                        package_id=package_id
                                    ).pack(),
                                )
                            ],
                        ]
                    ),
                    parse_mode="HTML",
                )
                logger.info(
                    f"Archivo {file_id} eliminado del paquete {package_id} por admin {callback.from_user.id}"
                )
            else:
                await callback.answer("No se pudo eliminar el archivo", show_alert=True)

        except Exception as e:
            logger.error(f"Error eliminando archivo {file_id}: {e}")
            await callback.answer("Error al eliminar el archivo", show_alert=True)


@router.callback_query(ContinueDeleteFilesCallback.filter())
async def continue_delete_files(
    callback: CallbackQuery, state: FSMContext, callback_data: ContinueDeleteFilesCallback
):
    """Continúa mostrando archivos para eliminar"""

    await callback.message.delete()
    await show_files_for_deletion(callback, state, bot=callback.bot)


@router.callback_query(FinishDeleteFilesCallback.filter())
async def finish_delete_files(
    callback: CallbackQuery, state: FSMContext, callback_data: FinishDeleteFilesCallback
):
    """Termina el flujo de eliminación de archivos"""
    package_id = callback_data.package_id

    await state.clear()

    await callback.message.edit_caption(
        caption="✅ <b>Operación finalizada.</b>",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📦 Ver paquete",
                        callback_data=PackageDetailCallback(package_id=package_id).pack(),
                    )
                ],
                [InlineKeyboardButton(text="🔙 Menú de paquetes", callback_data="manage_packages")],
            ]
        ),
        parse_mode="HTML",
    )
    await callback.answer()
