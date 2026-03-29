"""
Handlers de Paquetes - Lucien Bot

Wizard de creación y gestión de paquetes de contenido.
"""
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config.settings import bot_config
from services.package_service import PackageService
from keyboards.inline_keyboards import back_keyboard, confirmation_keyboard, cancel_keyboard
from utils.lucien_voice import LucienVoice
import logging

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


# Función helper para verificar admin
def is_admin(user_id: int) -> bool:
    return user_id in bot_config.ADMIN_IDS


# ==================== MENÚ DE PAQUETES ====================

@router.callback_query(F.data == "manage_packages", lambda cb: is_admin(cb.from_user.id))
async def manage_packages_menu(callback: CallbackQuery):
    """Menú principal de gestión de paquetes"""
    package_service = PackageService()
    packages = package_service.get_all_packages(active_only=False)
    
    active_count = sum(1 for p in packages if p.is_active)
    inactive_count = len(packages) - active_count
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="➕ Crear nuevo paquete",
            callback_data="create_package"
        )],
        [InlineKeyboardButton(
            text="📋 Ver paquetes activos",
            callback_data="list_packages_active"
        )],
        [InlineKeyboardButton(
            text="📋 Ver todos los paquetes",
            callback_data="list_packages_all"
        )],
        [InlineKeyboardButton(
            text="🔙 Volver",
            callback_data="admin_gamification"
        )]
    ])
    
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
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== LISTAR PAQUETES ====================

@router.callback_query(F.data.startswith("list_packages_"), lambda cb: is_admin(cb.from_user.id))
async def list_packages(callback: CallbackQuery):
    """Lista los paquetes"""
    list_type = callback.data.replace("list_packages_", "")
    active_only = list_type == "active"
    
    package_service = PackageService()
    packages = package_service.get_all_packages(active_only=active_only)
    
    if not packages:
        await callback.message.edit_text(
            f"""🎩 <b>Lucien:</b>

<i>No hay paquetes registrados en los archivos...</i>

👉 <i>Cree un paquete primero usando "Crear nuevo paquete".</i>""",
            reply_markup=back_keyboard("manage_packages"),
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    text = f"""🎩 <b>Lucien:</b>

<i>Los tesoros del reino...</i>

📦 <b>Paquetes {'activos' if active_only else 'registrados'}:</b>

"""
    
    buttons = []
    for pkg in packages:
        status = "✅" if pkg.is_active else "❌"
        store_info = "N/D" if pkg.store_stock == -2 else ("∞" if pkg.store_stock == -1 else str(pkg.store_stock))
        reward_info = "N/D" if pkg.reward_stock == -2 else ("∞" if pkg.reward_stock == -1 else str(pkg.reward_stock))
        
        text += f"{status} <b>{pkg.name}</b>\n"
        text += f"   📁 {pkg.file_count} archivos | 🛒 {store_info} | 🎁 {reward_info}\n\n"
        
        buttons.append([InlineKeyboardButton(
            text=f"{status} {pkg.name[:30]}",
            callback_data=f"package_detail_{pkg.id}"
        )])
    
    buttons.append([InlineKeyboardButton(
        text="🔙 Volver",
        callback_data="manage_packages"
    )])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("package_detail_"), lambda cb: is_admin(cb.from_user.id))
async def package_detail(callback: CallbackQuery):
    """Muestra detalles de un paquete"""
    package_id = int(callback.data.replace("package_detail_", ""))
    
    package_service = PackageService()
    package = package_service.get_package(package_id)
    
    if not package:
        await callback.answer("Paquete no encontrado", show_alert=True)
        return
    
    files = package_service.get_package_files(package_id)
    
    store_text = "No disponible" if package.store_stock == -2 else ("Ilimitado" if package.store_stock == -1 else str(package.store_stock))
    reward_text = "No disponible" if package.reward_stock == -2 else ("Ilimitado" if package.reward_stock == -1 else str(package.reward_stock))
    status = "✅ Activo" if package.is_active else "❌ Inactivo"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="👁️ Ver archivos",
            callback_data=f"view_package_files_{package_id}"
        )],
        [InlineKeyboardButton(
            text=f"{'Desactivar' if package.is_active else 'Activar'}",
            callback_data=f"toggle_package_{package_id}"
        )],
        [InlineKeyboardButton(
            text="🗑️ Eliminar",
            callback_data=f"delete_package_{package_id}"
        )],
        [InlineKeyboardButton(
            text="🔙 Volver",
            callback_data="list_packages_all"
        )]
    ])
    
    await callback.message.edit_text(
        f"""🎩 <b>Lucien:</b>

<i>Detalles del tesoro seleccionado...</i>

📦 <b>{package.name}</b>

📝 <b>Descripción:</b>
<i>{package.description or 'Sin descripción'}</i>

📊 <b>Información:</b>
   • Estado: {status}
   • Archivos: {len(files)}
   • Stock tienda: {store_text}
   • Stock recompensas: {reward_text}

<i>¿Qué desea hacer con este paquete?</i>""",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("view_package_files_"), lambda cb: is_admin(cb.from_user.id))
async def view_package_files(callback: CallbackQuery):
    """Muestra los archivos de un paquete"""
    package_id = int(callback.data.replace("view_package_files_", ""))
    
    package_service = PackageService()
    package = package_service.get_package(package_id)
    files = package_service.get_package_files(package_id)
    
    if not files:
        await callback.answer("El paquete no tiene archivos", show_alert=True)
        return
    
    text = f"""🎩 <b>Lucien:</b>

<i>Contenido del paquete <b>{package.name}</b>...</i>

📁 <b>Archivos ({len(files)}):</b>

"""
    
    for i, file in enumerate(files, 1):
        file_type_emoji = {
            "photo": "🖼️",
            "video": "🎬",
            "animation": "🎞️",
            "document": "📄"
        }.get(file.file_type, "📎")
        
        text += f"{i}. {file_type_emoji} {file.file_name or file.file_type}\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=back_keyboard(f"package_detail_{package_id}"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("toggle_package_"), lambda cb: is_admin(cb.from_user.id))
async def toggle_package(callback: CallbackQuery):
    """Activa/desactiva un paquete"""
    package_id = int(callback.data.replace("toggle_package_", ""))
    
    package_service = PackageService()
    package = package_service.get_package(package_id)
    
    if not package:
        await callback.answer("Paquete no encontrado", show_alert=True)
        return
    
    package_service.update_package(package_id, is_active=not package.is_active)
    
    status = "activado" if not package.is_active else "desactivado"
    await callback.answer(f"Paquete {status}")
    await package_detail(callback)


@router.callback_query(F.data.startswith("delete_package_"), lambda cb: is_admin(cb.from_user.id))
async def delete_package_confirm(callback: CallbackQuery):
    """Confirma eliminación de paquete"""
    package_id = int(callback.data.replace("delete_package_", ""))
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="✅ Sí, eliminar",
            callback_data=f"confirm_delete_package_{package_id}"
        )],
        [InlineKeyboardButton(
            text="❌ Cancelar",
            callback_data=f"package_detail_{package_id}"
        )]
    ])
    
    await callback.message.edit_text(
        f"""🎩 <b>Lucien:</b>

<i>¿Está seguro de que desea eliminar este paquete?</i>

⚠️ <b>Esta acción no se puede deshacer.</b>

Los archivos asociados también serán eliminados.""",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_package_"), lambda cb: is_admin(cb.from_user.id))
async def confirm_delete_package(callback: CallbackQuery):
    """Elimina el paquete"""
    package_id = int(callback.data.replace("confirm_delete_package_", ""))
    
    package_service = PackageService()
    success = package_service.delete_package(package_id)
    
    if success:
        await callback.message.edit_text(
            f"""🎩 <b>Lucien:</b>

<i>El paquete ha sido removido de los archivos de Diana...</i>

✅ <b>Paquete eliminado correctamente.</b>""",
            reply_markup=back_keyboard("manage_packages"),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            LucienVoice.error_message("la eliminación del paquete"),
            reply_markup=back_keyboard("manage_packages"),
            parse_mode="HTML"
        )
    await callback.answer()


# ==================== WIZARD DE CREACIÓN DE PAQUETE ====================

@router.callback_query(F.data == "create_package", lambda cb: is_admin(cb.from_user.id))
async def create_package_start(callback: CallbackQuery, state: FSMContext):
    """Inicia el wizard de creación de paquete"""
    await callback.message.edit_text(
        f"""🎩 <b>Lucien:</b>

<i>Vamos a crear un nuevo tesoro para el reino...</i>

📋 <b>Paso 1 de 6:</b> Nombre del paquete

Indique un nombre descriptivo para el paquete:
Ejemplo: <code>Fotos exclusivas de marzo</code>""",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(PackageWizardStates.waiting_name)
    await callback.answer()


@router.message(PackageWizardStates.waiting_name)
async def process_package_name(message: Message, state: FSMContext):
    """Procesa el nombre del paquete"""
    name = message.text.strip()
    
    if len(name) < 3:
        await message.answer(
            f"🎩 <b>Lucien:</b>\n\n"
            f"<i>El nombre debe tener al menos 3 caracteres...</i>",
            reply_markup=cancel_keyboard(),
            parse_mode="HTML"
        )
        return
    
    await state.update_data(name=name)
    
    await message.answer(
        f"""🎩 <b>Lucien:</b>

<i>Excelente nombre. Ahora la descripción...</i>

📋 <b>Paso 2 de 6:</b> Descripción del paquete

Escriba una descripción corta (opcional):
Ejemplo: <code>Una colección especial de fotos</code>

O envíe /skip para omitir.""",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(PackageWizardStates.waiting_description)


@router.message(PackageWizardStates.waiting_description)
async def process_package_description(message: Message, state: FSMContext):
    """Procesa la descripción del paquete"""
    if message.text == "/skip":
        description = None
    else:
        description = message.text.strip()
    
    await state.update_data(description=description)
    
    await message.answer(
        f"""🎩 <b>Lucien:</b>

<i>Ahora los archivos del tesoro...</i>

📋 <b>Paso 3 de 6:</b> Cargar archivos

Envíe las fotos, videos o archivos que desea incluir en el paquete.

Puede enviar varios archivos uno por uno.

Cuando termine, envíe /done""",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
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
        files = data.get('files', [])
        
        if not files:
            await message.answer(
                f"🎩 <b>Lucien:</b>\n\n"
                f"<i>Debe agregar al menos un archivo al paquete...</i>\n\n"
                f"Envíe los archivos o /cancel para cancelar.",
                reply_markup=cancel_keyboard(),
                parse_mode="HTML"
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
            f"🎩 <b>Lucien:</b>\n\n"
            f"<i>No reconocí el tipo de archivo.\n"
            f"Por favor envíe fotos, videos, documentos o GIFs...</i>",
            reply_markup=cancel_keyboard(),
            parse_mode="HTML"
        )
        return
    
    # Agregar a la lista
    data = await state.get_data()
    files = data.get('files', [])
    files.append({
        'file_id': file_id,
        'file_type': file_type,
        'file_name': file_name,
        'file_size': file_size
    })
    await state.update_data(files=files)
    
    await message.answer(
        f"""🎩 <b>Lucien:</b>

✅ <b>Archivo agregado:</b> {file_type}

📊 <b>Total de archivos:</b> {len(files)}

<i>Envíe más archivos o /done para continuar.</i>""",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
    )


async def ask_store_stock(message: Message, state: FSMContext):
    """Pregunta por el stock de tienda"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="♾️ Ilimitado", callback_data="store_stock_unlimited")],
        [InlineKeyboardButton(text="📦 Limitado", callback_data="store_stock_limited")],
        [InlineKeyboardButton(text="🚫 No disponible", callback_data="store_stock_none")],
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="cancel")]
    ])
    
    await message.answer(
        f"""🎩 <b>Lucien:</b>

<i>Configuremos la disponibilidad en la tienda...</i>

📋 <b>Paso 4 de 6:</b> Stock en tienda

¿El paquete estará disponible en la tienda?""",
        reply_markup=keyboard,
        parse_mode="HTML"
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
        f"""🎩 <b>Lucien:</b>

<i>Indique la cantidad de unidades disponibles para venta...</i>

📋 Stock en tienda:

Ejemplo: <code>10</code> para 10 unidades""",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
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
            f"🎩 <b>Lucien:</b>\n\n"
            f"<i>Por favor, indique un número válido (0 o mayor)...</i>",
            reply_markup=cancel_keyboard(),
            parse_mode="HTML"
        )
        return
    
    await state.update_data(store_stock=stock)
    await ask_reward_stock(message, state)


async def ask_reward_stock(target, state: FSMContext):
    """Pregunta por el stock de recompensas"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="♾️ Ilimitado", callback_data="reward_stock_unlimited")],
        [InlineKeyboardButton(text="📦 Limitado", callback_data="reward_stock_limited")],
        [InlineKeyboardButton(text="🚫 No disponible", callback_data="reward_stock_none")],
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="cancel")]
    ])
    
    text = f"""🎩 <b>Lucien:</b>

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
        f"""🎩 <b>Lucien:</b>

<i>Indique la cantidad de unidades disponibles para recompensas...</i>

📋 Stock en recompensas:

Ejemplo: <code>50</code> para 50 unidades""",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
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
            f"🎩 <b>Lucien:</b>\n\n"
            f"<i>Por favor, indique un número válido (0 o mayor)...</i>",
            reply_markup=cancel_keyboard(),
            parse_mode="HTML"
        )
        return
    
    await state.update_data(reward_stock=stock)
    await show_package_preview(message, state)


async def show_package_preview(target, state: FSMContext):
    """Muestra preview del paquete antes de crear"""
    data = await state.get_data()
    
    name = data.get('name', '')
    description = data.get('description', 'Sin descripción')
    files = data.get('files', [])
    store_stock = data.get('store_stock', -1)
    reward_stock = data.get('reward_stock', -1)
    
    store_text = "No disponible" if store_stock == -2 else ("Ilimitado" if store_stock == -1 else str(store_stock))
    reward_text = "No disponible" if reward_stock == -2 else ("Ilimitado" if reward_stock == -1 else str(reward_stock))
    
    text = f"""🎩 <b>Lucien:</b>

<i>Permíteme mostrarle el resumen del tesoro...</i>

📦 <b>Resumen del Paquete:</b>

📛 <b>Nombre:</b> {name}
📝 <b>Descripción:</b> {description}
📁 <b>Archivos:</b> {len(files)}
🛒 <b>Stock tienda:</b> {store_text}
🎁 <b>Stock recompensas:</b> {reward_text}

<i>¿Desea crear este paquete?</i>"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Crear paquete", callback_data="confirm_create_package")],
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="manage_packages")]
    ])
    
    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await target.answer(text, reply_markup=keyboard, parse_mode="HTML")
    
    await state.set_state(PackageWizardStates.confirming)


@router.callback_query(PackageWizardStates.confirming, F.data == "confirm_create_package")
async def confirm_create_package(callback: CallbackQuery, state: FSMContext):
    """Crea el paquete con todos los datos"""
    data = await state.get_data()
    
    package_service = PackageService()
    
    try:
        # Crear el paquete
        package = package_service.create_package(
            name=data['name'],
            description=data.get('description'),
            store_stock=data.get('store_stock', -1),
            reward_stock=data.get('reward_stock', -1),
            created_by=callback.from_user.id
        )
        
        # Agregar archivos
        files = data.get('files', [])
        for i, file_data in enumerate(files):
            package_service.add_file_to_package(
                package_id=package.id,
                file_id=file_data['file_id'],
                file_type=file_data['file_type'],
                file_name=file_data.get('file_name'),
                file_size=file_data.get('file_size'),
                order_index=i
            )
        
        await callback.message.edit_text(
            f"""🎩 <b>Lucien:</b>

<i>El tesoro ha sido registrado en los archivos de Diana...</i>

✅ <b>Paquete creado exitosamente!</b>

📦 <b>{package.name}</b>
📁 {len(files)} archivo(s)

<i>El paquete está listo para usarse en recompensas o tienda.</i>""",
            reply_markup=back_keyboard("manage_packages"),
            parse_mode="HTML"
        )
        
        logger.info(f"Paquete creado: {package.name} (ID: {package.id}) por admin {callback.from_user.id}")
        
    except Exception as e:
        logger.error(f"Error creando paquete: {e}")
        await callback.message.edit_text(
            LucienVoice.error_message("la creación del paquete"),
            reply_markup=back_keyboard("manage_packages"),
            parse_mode="HTML"
        )
    
    await state.clear()
    await callback.answer()
