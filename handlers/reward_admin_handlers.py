"""
Handlers de Recompensas para Admin - Lucien Bot

Wizard de creacion de recompensas con cascada a paquetes.
"""
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config.settings import bot_config
from services.reward_service import RewardService
from services.package_service import PackageService
from services.vip_service import VIPService
from models.models import RewardType
import logging

logger = logging.getLogger(__name__)
router = Router()


# Estados para FSM de Recompensas
class RewardWizardStates(StatesGroup):
    waiting_name = State()
    waiting_description = State()
    selecting_type = State()
    # Besitos
    waiting_besito_amount = State()
    # Paquete
    selecting_package = State()
    create_package_requested = State()
    # VIP
    selecting_tariff = State()
    confirming = State()


# Estados para FSM de creacion de paquete desde recompensa
class PackageFromRewardStates(StatesGroup):
    waiting_name = State()
    waiting_description = State()
    waiting_files = State()
    waiting_store_stock = State()
    waiting_reward_stock = State()
    confirming = State()


def is_admin(user_id: int) -> bool:
    return user_id in bot_config.ADMIN_IDS


# ==================== WIZARD CREAR RECOMPENSA ====================

@router.callback_query(F.data == "create_reward", lambda cb: is_admin(cb.from_user.id))
async def create_reward_start(callback: CallbackQuery, state: FSMContext):
    """Inicia wizard de recompensa"""
    await callback.message.edit_text(
        """🎩 Lucien:

Vamos a crear una nueva recompensa...

Paso 1 de 5: Nombre

Indica un nombre descriptivo:
Ejemplo: 50 Besitos de regalo""",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_missions")]
        ])
    )
    await state.set_state(RewardWizardStates.waiting_name)
    await callback.answer()


@router.message(RewardWizardStates.waiting_name)
async def process_reward_name(message: Message, state: FSMContext):
    """Procesa nombre de recompensa"""
    name = message.text.strip()
    if len(name) < 3:
        await message.answer("El nombre debe tener al menos 3 caracteres.")
        return
    
    await state.update_data(name=name)
    await message.answer(
        """🎩 Lucien:

Paso 2 de 5: Descripcion

Escribe una descripcion (opcional):
Ejemplo: Recibe 50 besitos al completar la mision

O envia /skip para omitir.""",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_missions")]
        ])
    )
    await state.set_state(RewardWizardStates.waiting_description)


@router.message(RewardWizardStates.waiting_description)
async def process_reward_description(message: Message, state: FSMContext):
    """Procesa descripcion de recompensa"""
    description = None if message.text == "/skip" else message.text.strip()
    await state.update_data(description=description)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💋 Besitos", callback_data="reward_type_besitos")],
        [InlineKeyboardButton(text="📦 Paquete de fotos", callback_data="reward_type_package")],
        [InlineKeyboardButton(text="👑 Acceso VIP", callback_data="reward_type_vip")],
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_missions")]
    ])
    
    await message.answer(
        """🎩 Lucien:

Paso 3 de 5: Tipo de recompensa

Selecciona el tipo:""",
        reply_markup=keyboard
    )
    await state.set_state(RewardWizardStates.selecting_type)


@router.callback_query(RewardWizardStates.selecting_type, F.data.startswith("reward_type_"))
async def select_reward_type(callback: CallbackQuery, state: FSMContext):
    """Selecciona tipo de recompensa"""
    type_map = {
        "reward_type_besitos": RewardType.BESITOS,
        "reward_type_package": RewardType.PACKAGE,
        "reward_type_vip": RewardType.VIP_ACCESS
    }
    
    reward_type = type_map.get(callback.data)
    if not reward_type:
        await callback.answer("Tipo invalido", show_alert=True)
        return
    
    await state.update_data(reward_type=reward_type)
    
    if reward_type == RewardType.BESITOS:
        await callback.message.edit_text(
            """🎩 Lucien:

Paso 4 de 5: Cantidad de besitos

Indica cuantos besitos otorga:
Ejemplo: 50""",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_missions")]
            ])
        )
        await state.set_state(RewardWizardStates.waiting_besito_amount)
    
    elif reward_type == RewardType.PACKAGE:
        await show_package_selection(callback, state)
    
    elif reward_type == RewardType.VIP_ACCESS:
        await show_tariff_selection(callback, state)
    
    await callback.answer()


@router.message(RewardWizardStates.waiting_besito_amount)
async def process_besito_amount(message: Message, state: FSMContext):
    """Procesa cantidad de besitos"""
    try:
        amount = int(message.text.strip())
        if amount < 1:
            raise ValueError("Debe ser mayor a 0")
    except ValueError:
        await message.answer("Por favor indica un numero valido mayor a 0.")
        return
    
    await state.update_data(besito_amount=amount)
    await show_reward_confirmation(message, state)


async def show_package_selection(callback: CallbackQuery, state: FSMContext):
    """Muestra seleccion de paquetes"""
    package_service = PackageService()
    packages = package_service.get_available_packages_for_rewards()
    
    buttons = []
    
    if packages:
        for pkg in packages:
            stock_text = "∞" if pkg.reward_stock == -1 else str(pkg.reward_stock)
            buttons.append([InlineKeyboardButton(
                text=f"{pkg.name} ({pkg.file_count} archivos, stock: {stock_text})",
                callback_data=f"select_pkg_{pkg.id}"
            )])
    
    buttons.append([InlineKeyboardButton(
        text="➕ Crear nuevo paquete",
        callback_data="create_package_for_reward"
    )])
    buttons.append([InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_missions")])
    
    text = """🎩 Lucien:

Paso 4 de 5: Seleccionar paquete

Elige un paquete existente o crea uno nuevo:"""
    
    if not packages:
        text = """🎩 Lucien:

Paso 4 de 5: Seleccionar paquete

No hay paquetes disponibles para recompensas.

Debes crear uno nuevo:"""
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await state.set_state(RewardWizardStates.selecting_package)


@router.callback_query(RewardWizardStates.selecting_package, F.data.startswith("select_pkg_"))
async def select_package_for_reward(callback: CallbackQuery, state: FSMContext):
    """Selecciona paquete para recompensa"""
    try:
        package_id = int(callback.data.replace("select_pkg_", ""))
    except ValueError:
        await callback.answer("ID invalido", show_alert=True)
        return
    
    await state.update_data(package_id=package_id)
    await show_reward_confirmation(callback, state)
    await callback.answer()


@router.callback_query(RewardWizardStates.selecting_package, F.data == "create_package_for_reward")
async def create_package_for_reward(callback: CallbackQuery, state: FSMContext):
    """Inicia creacion de paquete desde recompensa"""
    await callback.message.edit_text(
        """🎩 Lucien:

Creando paquete para la recompensa...

Paso 1 de 5: Nombre del paquete

Indica un nombre descriptivo:
Ejemplo: Fotos exclusivas de marzo""",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_missions")]
        ])
    )
    await state.set_state(PackageFromRewardStates.waiting_name)
    await callback.answer()


# ==================== WIZARD PAQUETE DESDE RECOMPENSA ====================

@router.message(PackageFromRewardStates.waiting_name)
async def process_pkg_name_from_reward(message: Message, state: FSMContext):
    """Procesa nombre de paquete desde recompensa"""
    name = message.text.strip()
    if len(name) < 3:
        await message.answer("El nombre debe tener al menos 3 caracteres.")
        return
    
    await state.update_data(pkg_name=name)
    await message.answer(
        """🎩 Lucien:

Paso 2 de 5: Descripcion del paquete

Escribe una descripcion (opcional):
Ejemplo: Una coleccion especial de fotos

O envia /skip para omitir.""",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_missions")]
        ])
    )
    await state.set_state(PackageFromRewardStates.waiting_description)


@router.message(PackageFromRewardStates.waiting_description)
async def process_pkg_desc_from_reward(message: Message, state: FSMContext):
    """Procesa descripcion de paquete desde recompensa"""
    description = None if message.text == "/skip" else message.text.strip()
    await state.update_data(pkg_description=description)
    
    await message.answer(
        """🎩 Lucien:

Paso 3 de 5: Cargar archivos

Envia las fotos, videos o archivos.
Puedes enviar varios archivos uno por uno.

Cuando termines, envia /done""",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_missions")]
        ])
    )
    await state.update_data(pkg_files=[])
    await state.set_state(PackageFromRewardStates.waiting_files)


@router.message(PackageFromRewardStates.waiting_files)
async def process_pkg_files_from_reward(message: Message, state: FSMContext):
    """Procesa archivos del paquete desde recompensa"""
    if message.text == "/done":
        data = await state.get_data()
        files = data.get('pkg_files', [])
        
        if not files:
            await message.answer("Debes agregar al menos un archivo.")
            return
        
        await ask_pkg_stocks_from_reward(message, state)
        return
    
    # Procesar archivo
    file_id = None
    file_type = None
    file_name = None
    
    if message.photo:
        file_id = message.photo[-1].file_id
        file_type = "photo"
    elif message.video:
        file_id = message.video.file_id
        file_type = "video"
    elif message.document:
        file_id = message.document.file_id
        file_type = "document"
        file_name = message.document.file_name
    elif message.animation:
        file_id = message.animation.file_id
        file_type = "animation"
    else:
        await message.answer("Envia una foto, video, documento o GIF.")
        return
    
    data = await state.get_data()
    files = data.get('pkg_files', [])
    files.append({
        'file_id': file_id,
        'file_type': file_type,
        'file_name': file_name
    })
    await state.update_data(pkg_files=files)
    
    await message.answer(f"Archivo agregado. Total: {len(files)}. Envia mas o /done")


async def ask_pkg_stocks_from_reward(message: Message, state: FSMContext):
    """Pregunta stocks del paquete desde recompensa"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="♾️ Ilimitado", callback_data="pkg_reward_stock_unlimited")],
        [InlineKeyboardButton(text="📦 Limitado", callback_data="pkg_reward_stock_limited")],
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_missions")]
    ])
    
    await message.answer(
        """🎩 Lucien:

Paso 4 de 5: Stock para recompensas

El stock de tienda se configurara como No disponible.

Stock para recompensas:""",
        reply_markup=keyboard
    )
    await state.set_state(PackageFromRewardStates.waiting_reward_stock)


@router.callback_query(PackageFromRewardStates.waiting_reward_stock, F.data == "pkg_reward_stock_unlimited")
async def pkg_reward_stock_unlimited(callback: CallbackQuery, state: FSMContext):
    """Stock ilimitado para recompensas"""
    await state.update_data(pkg_reward_stock=-1)
    await show_pkg_confirmation_from_reward(callback, state)
    await callback.answer()


@router.callback_query(PackageFromRewardStates.waiting_reward_stock, F.data == "pkg_reward_stock_limited")
async def pkg_reward_stock_limited(callback: CallbackQuery, state: FSMContext):
    """Pide cantidad limitada para recompensas"""
    await callback.message.edit_text(
        """🎩 Lucien:

Indica la cantidad de unidades:
Ejemplo: 50""",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_missions")]
        ])
    )
    await callback.answer()


@router.message(PackageFromRewardStates.waiting_reward_stock)
async def process_pkg_reward_stock(message: Message, state: FSMContext):
    """Procesa stock de recompensas del paquete"""
    try:
        stock = int(message.text.strip())
        if stock < 0:
            raise ValueError("Debe ser 0 o mayor")
    except ValueError:
        await message.answer("Indica un numero valido (0 o mayor).")
        return
    
    await state.update_data(pkg_reward_stock=stock)
    await show_pkg_confirmation_from_reward(message, state)


async def show_pkg_confirmation_from_reward(target, state: FSMContext):
    """Muestra confirmacion del paquete desde recompensa"""
    data = await state.get_data()
    
    name = data.get('pkg_name', '')
    description = data.get('pkg_description', 'Sin descripcion')
    files = data.get('pkg_files', [])
    reward_stock = data.get('pkg_reward_stock', -1)
    
    stock_text = "Ilimitado" if reward_stock == -1 else str(reward_stock)
    
    text = f"""🎩 Lucien:

Resumen del paquete:

📦 {name}
📝 {description}
📁 {len(files)} archivos
🎁 Stock recompensas: {stock_text}
🛒 Stock tienda: No disponible

Crear este paquete?"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Crear paquete", callback_data="confirm_create_pkg_from_reward")],
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_missions")]
    ])
    
    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=keyboard)
    else:
        await target.answer(text, reply_markup=keyboard)
    
    await state.set_state(PackageFromRewardStates.confirming)


@router.callback_query(PackageFromRewardStates.confirming, F.data == "confirm_create_pkg_from_reward")
async def confirm_create_pkg_from_reward(callback: CallbackQuery, state: FSMContext):
    """Crea el paquete y retorna a la recompensa"""
    data = await state.get_data()
    package_service = PackageService()
    
    try:
        # Crear paquete
        package = package_service.create_package(
            name=data.get('pkg_name'),
            description=data.get('pkg_description'),
            store_stock=-2,  # No disponible en tienda
            reward_stock=data.get('pkg_reward_stock', -1),
            created_by=callback.from_user.id
        )
        
        # Agregar archivos
        files = data.get('pkg_files', [])
        for i, file_data in enumerate(files):
            package_service.add_file_to_package(
                package_id=package.id,
                file_id=file_data['file_id'],
                file_type=file_data['file_type'],
                file_name=file_data.get('file_name'),
                order_index=i
            )
        
        # Guardar package_id para la recompensa
        await state.update_data(package_id=package.id)
        
        await callback.message.edit_text(
            f"""🎩 Lucien:

Paquete creado exitosamente!

📦 {package.name}
📁 {len(files)} archivos

Continuando con la recompensa..."""
        )
        
        # Continuar con confirmacion de recompensa
        await show_reward_confirmation(callback, state)
        logger.info(f"Paquete creado desde recompensa: {package.name}")
        
    except Exception as e:
        logger.error(f"Error creando paquete: {e}")
        await callback.message.edit_text(
            "Error al crear el paquete.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_missions")]
            ])
        )
        await state.clear()
    
    await callback.answer()


# ==================== SELECCION TARIFA VIP ====================

async def show_tariff_selection(callback: CallbackQuery, state: FSMContext):
    """Muestra seleccion de tarifas VIP"""
    vip_service = VIPService()
    tariffs = vip_service.get_all_tariffs(active_only=True)
    
    if not tariffs:
        await callback.message.edit_text(
            """🎩 Lucien:

No hay tarifas VIP configuradas.

Crea una tarifa primero desde el panel VIP.""",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_missions")]
            ])
        )
        await state.clear()
        return
    
    buttons = []
    for tariff in tariffs:
        buttons.append([InlineKeyboardButton(
            text=f"{tariff.name} ({tariff.duration_days} dias)",
            callback_data=f"select_tariff_{tariff.id}"
        )])
    
    buttons.append([InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_missions")])
    
    await callback.message.edit_text(
        """🎩 Lucien:

Paso 4 de 5: Seleccionar tarifa VIP

Elige la tarifa para el acceso VIP:""",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await state.set_state(RewardWizardStates.selecting_tariff)


@router.callback_query(RewardWizardStates.selecting_tariff, F.data.startswith("select_tariff_"))
async def select_tariff_for_reward(callback: CallbackQuery, state: FSMContext):
    """Selecciona tarifa para recompensa VIP"""
    try:
        tariff_id = int(callback.data.replace("select_tariff_", ""))
    except ValueError:
        await callback.answer("ID invalido", show_alert=True)
        return
    
    await state.update_data(tariff_id=tariff_id)
    await show_reward_confirmation(callback, state)
    await callback.answer()


# ==================== CONFIRMACION RECOMPENSA ====================

async def show_reward_confirmation(target, state: FSMContext):
    """Muestra confirmacion de recompensa"""
    data = await state.get_data()
    
    name = data.get('name', '')
    description = data.get('description', 'Sin descripcion')
    reward_type = data.get('reward_type')
    
    type_text = ""
    if reward_type == RewardType.BESITOS:
        type_text = f"{data.get('besito_amount', 0)} besitos"
    elif reward_type == RewardType.PACKAGE:
        package_id = data.get('package_id')
        if package_id:
            package_service = PackageService()
            pkg = package_service.get_package(package_id)
            type_text = f"Paquete: {pkg.name if pkg else 'Desconocido'}"
    elif reward_type == RewardType.VIP_ACCESS:
        tariff_id = data.get('tariff_id')
        if tariff_id:
            vip_service = VIPService()
            tariff = vip_service.get_tariff(tariff_id)
            type_text = f"VIP: {tariff.name if tariff else 'Desconocido'}"
    
    text = f"""🎩 Lucien:

Resumen de la recompensa:

🎁 {name}
📝 {description}
📋 Tipo: {reward_type.value}
💎 Contenido: {type_text}

Crear esta recompensa?"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Crear", callback_data="confirm_create_reward")],
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_missions")]
    ])
    
    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=keyboard)
    else:
        await target.answer(text, reply_markup=keyboard)
    
    await state.set_state(RewardWizardStates.confirming)


@router.callback_query(RewardWizardStates.confirming, F.data == "confirm_create_reward")
async def confirm_create_reward(callback: CallbackQuery, state: FSMContext):
    """Crea la recompensa"""
    data = await state.get_data()
    reward_service = RewardService()
    
    try:
        reward_type = data.get('reward_type')
        
        if reward_type == RewardType.BESITOS:
            reward = reward_service.create_reward_besitos(
                name=data.get('name'),
                description=data.get('description'),
                besito_amount=data.get('besito_amount'),
                created_by=callback.from_user.id
            )
        
        elif reward_type == RewardType.PACKAGE:
            reward = reward_service.create_reward_package(
                name=data.get('name'),
                description=data.get('description'),
                package_id=data.get('package_id'),
                created_by=callback.from_user.id
            )
        
        elif reward_type == RewardType.VIP_ACCESS:
            reward = reward_service.create_reward_vip(
                name=data.get('name'),
                description=data.get('description'),
                tariff_id=data.get('tariff_id'),
                created_by=callback.from_user.id
            )
        
        await callback.message.edit_text(
            f"""🎩 Lucien:

Recompensa creada exitosamente!

🎁 {reward.name}
📋 Tipo: {reward.reward_type.value}

La recompensa esta lista para usarse en misiones.""",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_missions")]
            ])
        )
        logger.info(f"Recompensa creada: {reward.name} por admin {callback.from_user.id}")
        
    except Exception as e:
        logger.error(f"Error creando recompensa: {e}")
        await callback.message.edit_text(
            "Error al crear la recompensa.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_missions")]
            ])
        )
    
    await state.clear()
    await callback.answer()


# ==================== LISTAR RECOMPENSAS ====================

@router.callback_query(F.data == "list_rewards", lambda cb: is_admin(cb.from_user.id))
async def list_rewards(callback: CallbackQuery):
    """Lista todas las recompensas"""
    reward_service = RewardService()
    rewards = reward_service.get_all_rewards(active_only=False)
    
    if not rewards:
        await callback.message.edit_text(
            "No hay recompensas registradas.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_missions")]
            ])
        )
        await callback.answer()
        return
    
    text = "🎩 Lucien:\n\nRecompensas registradas:\n\n"
    buttons = []
    
    for reward in rewards:
        status = "✅" if reward.is_active else "❌"
        text += f"{status} {reward.name} ({reward.reward_type.value})\n"
        buttons.append([InlineKeyboardButton(
            text=f"{status} {reward.name[:30]}",
            callback_data=f"reward_admin_detail_{reward.id}"
        )])
    
    buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="admin_missions")])
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()
