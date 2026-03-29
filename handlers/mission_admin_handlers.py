"""
Handlers de Misiones y Recompensas para Admin - Lucien Bot

Wizard de creacion de misiones y recompensas con cascada a paquetes.
"""
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config.settings import bot_config
from services.mission_service import MissionService
from services.reward_service import RewardService
from services.package_service import PackageService
from models.models import MissionType, MissionFrequency, RewardType
import logging

logger = logging.getLogger(__name__)
router = Router()


# Estados para FSM
class MissionWizardStates(StatesGroup):
    waiting_name = State()
    waiting_description = State()
    selecting_type = State()
    waiting_target = State()
    selecting_frequency = State()
    selecting_reward = State()
    confirming = State()


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


def is_admin(user_id: int) -> bool:
    return user_id in bot_config.ADMIN_IDS


# ==================== MENU PRINCIPAL ====================

@router.callback_query(F.data == "admin_missions", lambda cb: is_admin(cb.from_user.id))
async def admin_missions_menu(callback: CallbackQuery):
    """Menu de gestion de misiones y recompensas"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Crear mision", callback_data="create_mission")],
        [InlineKeyboardButton(text="📋 Ver misiones", callback_data="list_missions")],
        [InlineKeyboardButton(text="🎁 Crear recompensa", callback_data="create_reward")],
        [InlineKeyboardButton(text="📋 Ver recompensas", callback_data="list_rewards")],
        [InlineKeyboardButton(text="📊 Estadisticas", callback_data="missions_stats")],
        [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_gamification")]
    ])
    
    await callback.message.edit_text(
        """🎩 Lucien:

Los desafios que cultivan devocion...

Que deseas gestionar?""",
        reply_markup=keyboard
    )
    await callback.answer()


# ==================== WIZARD CREAR MISION ====================

@router.callback_query(F.data == "create_mission", lambda cb: is_admin(cb.from_user.id))
async def create_mission_start(callback: CallbackQuery, state: FSMContext):
    """Inicia wizard de mision"""
    await callback.message.edit_text(
        """🎩 Lucien:

Vamos a crear un nuevo desafio...

Paso 1 de 6: Nombre de la mision

Indica un nombre descriptivo:
Ejemplo: Reacciona 10 veces""",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_missions")]
        ])
    )
    await state.set_state(MissionWizardStates.waiting_name)
    await callback.answer()


@router.message(MissionWizardStates.waiting_name)
async def process_mission_name(message: Message, state: FSMContext):
    """Procesa nombre de mision"""
    name = message.text.strip()
    if len(name) < 3:
        await message.answer("El nombre debe tener al menos 3 caracteres.")
        return
    
    await state.update_data(name=name)
    await message.answer(
        """🎩 Lucien:

Paso 2 de 6: Descripcion

Escribe una descripcion (opcional):
Ejemplo: Reacciona a 10 mensajes de Diana

O envia /skip para omitir.""",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_missions")]
        ])
    )
    await state.set_state(MissionWizardStates.waiting_description)


@router.message(MissionWizardStates.waiting_description)
async def process_mission_description(message: Message, state: FSMContext):
    """Procesa descripcion de mision"""
    description = None if message.text == "/skip" else message.text.strip()
    await state.update_data(description=description)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💋 Reaccionar N veces", callback_data="type_reaction_count")],
        [InlineKeyboardButton(text="🎁 Reclamar regalo N dias (consecutivos)", callback_data="type_daily_streak")],
        [InlineKeyboardButton(text="🎁 Reclamar regalo N dias (total)", callback_data="type_daily_total")],
        [InlineKeyboardButton(text="🛒 Comprar en tienda", callback_data="type_store_purchase")],
        [InlineKeyboardButton(text="👑 Tener VIP activo", callback_data="type_vip_active")],
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_missions")]
    ])
    
    await message.answer(
        """🎩 Lucien:

Paso 3 de 6: Tipo de mision

Selecciona el tipo de desafio:""",
        reply_markup=keyboard
    )
    await state.set_state(MissionWizardStates.selecting_type)


@router.callback_query(MissionWizardStates.selecting_type, F.data.startswith("type_"))
async def select_mission_type(callback: CallbackQuery, state: FSMContext):
    """Selecciona tipo de mision"""
    type_map = {
        "type_reaction_count": MissionType.REACTION_COUNT,
        "type_daily_streak": MissionType.DAILY_GIFT_STREAK,
        "type_daily_total": MissionType.DAILY_GIFT_TOTAL,
        "type_store_purchase": MissionType.STORE_PURCHASE,
        "type_vip_active": MissionType.VIP_ACTIVE
    }
    
    mission_type = type_map.get(callback.data)
    if not mission_type:
        await callback.answer("Tipo invalido", show_alert=True)
        return
    
    await state.update_data(mission_type=mission_type)
    
    examples = {
        MissionType.REACTION_COUNT: "10 (para 10 reacciones)",
        MissionType.DAILY_GIFT_STREAK: "7 (para 7 dias consecutivos)",
        MissionType.DAILY_GIFT_TOTAL: "5 (para 5 dias en total)",
        MissionType.STORE_PURCHASE: "1 (para 1 compra)",
        MissionType.VIP_ACTIVE: "1 (siempre 1 para VIP)"
    }
    
    await callback.message.edit_text(
        f"""🎩 Lucien:

Paso 4 de 6: Valor objetivo

Indica la meta numerica:
Ejemplo: {examples.get(mission_type, "10")}""",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_missions")]
        ])
    )
    await state.set_state(MissionWizardStates.waiting_target)
    await callback.answer()


@router.message(MissionWizardStates.waiting_target)
async def process_mission_target(message: Message, state: FSMContext):
    """Procesa valor objetivo"""
    try:
        target = int(message.text.strip())
        if target < 1:
            raise ValueError("Debe ser mayor a 0")
    except ValueError:
        await message.answer("Por favor indica un numero valido mayor a 0.")
        return
    
    await state.update_data(target_value=target)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Una vez", callback_data="freq_one_time")],
        [InlineKeyboardButton(text="Recurrente", callback_data="freq_recurring")],
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_missions")]
    ])
    
    await message.answer(
        """🎩 Lucien:

Paso 5 de 6: Frecuencia

Selecciona la frecuencia:

Una vez: El usuario la completa una sola vez
Recurrente: Se reinicia al completarse""",
        reply_markup=keyboard
    )
    await state.set_state(MissionWizardStates.selecting_frequency)


@router.callback_query(MissionWizardStates.selecting_frequency, F.data.startswith("freq_"))
async def select_frequency(callback: CallbackQuery, state: FSMContext):
    """Selecciona frecuencia"""
    freq_map = {
        "freq_one_time": MissionFrequency.ONE_TIME,
        "freq_recurring": MissionFrequency.RECURRING
    }
    
    frequency = freq_map.get(callback.data)
    if not frequency:
        await callback.answer("Frecuencia invalida", show_alert=True)
        return
    
    await state.update_data(frequency=frequency)
    
    # Mostrar recompensas disponibles
    reward_service = RewardService()
    rewards = reward_service.get_all_rewards(active_only=True)
    
    if not rewards:
        await callback.message.edit_text(
            """🎩 Lucien:

No hay recompensas configuradas...

Crea una recompensa primero.""",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Crear recompensa", callback_data="create_reward")],
                [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_missions")]
            ])
        )
        await state.clear()
        await callback.answer()
        return
    
    buttons = []
    for reward in rewards:
        buttons.append([InlineKeyboardButton(
            text=f"{reward.name} ({reward.reward_type.value})",
            callback_data=f"select_reward_{reward.id}"
        )])
    
    buttons.append([InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_missions")])
    
    await callback.message.edit_text(
        """🎩 Lucien:

Paso 6 de 6: Recompensa

Selecciona la recompensa para esta mision:""",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await state.set_state(MissionWizardStates.selecting_reward)
    await callback.answer()


@router.callback_query(MissionWizardStates.selecting_reward, F.data.startswith("select_reward_"))
async def select_reward_for_mission(callback: CallbackQuery, state: FSMContext):
    """Selecciona recompensa y muestra confirmacion"""
    try:
        reward_id = int(callback.data.replace("select_reward_", ""))
    except ValueError:
        await callback.answer("ID invalido", show_alert=True)
        return
    
    await state.update_data(reward_id=reward_id)
    data = await state.get_data()
    
    reward_service = RewardService()
    reward = reward_service.get_reward(reward_id)
    
    freq_text = "Una vez" if data.get('frequency') == MissionFrequency.ONE_TIME else "Recurrente"
    
    text = f"""🎩 Lucien:

Resumen de la mision:

📋 Nombre: {data.get('name')}
📝 Descripcion: {data.get('description') or 'Sin descripcion'}
🎯 Tipo: {data.get('mission_type').value}
📊 Meta: {data.get('target_value')}
🔄 Frecuencia: {freq_text}
🎁 Recompensa: {reward.name if reward else 'Ninguna'}

Deseas crear esta mision?"""
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Crear", callback_data="confirm_create_mission")],
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_missions")]
        ])
    )
    await state.set_state(MissionWizardStates.confirming)
    await callback.answer()


@router.callback_query(MissionWizardStates.confirming, F.data == "confirm_create_mission")
async def confirm_create_mission(callback: CallbackQuery, state: FSMContext):
    """Crea la mision"""
    data = await state.get_data()
    mission_service = MissionService()
    
    try:
        mission = mission_service.create_mission(
            name=data.get('name'),
            description=data.get('description'),
            mission_type=data.get('mission_type'),
            target_value=data.get('target_value'),
            reward_id=data.get('reward_id'),
            frequency=data.get('frequency'),
            created_by=callback.from_user.id
        )
        
        await callback.message.edit_text(
            f"""🎩 Lucien:

Mision creada exitosamente!

📋 {mission.name}
🎯 Tipo: {mission.mission_type.value}
📊 Meta: {mission.target_value}

La mision esta activa y disponible para los usuarios.""",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_missions")]
            ])
        )
        logger.info(f"Mision creada: {mission.name} por admin {callback.from_user.id}")
        
    except Exception as e:
        logger.error(f"Error creando mision: {e}")
        await callback.message.edit_text(
            "Error al crear la mision. Intenta de nuevo.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_missions")]
            ])
        )
    
    await state.clear()
    await callback.answer()


# ==================== LISTAR MISIONES ====================

@router.callback_query(F.data == "list_missions", lambda cb: is_admin(cb.from_user.id))
async def list_missions(callback: CallbackQuery):
    """Lista todas las misiones"""
    mission_service = MissionService()
    missions = mission_service.get_all_missions(active_only=False)
    
    if not missions:
        await callback.message.edit_text(
            "No hay misiones registradas.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_missions")]
            ])
        )
        await callback.answer()
        return
    
    text = "🎩 Lucien:\n\nMisiones registradas:\n\n"
    buttons = []
    
    for mission in missions:
        status = "✅" if mission.is_active else "❌"
        text += f"{status} {mission.name} ({mission.mission_type.value})\n"
        buttons.append([InlineKeyboardButton(
            text=f"{status} {mission.name[:30]}",
            callback_data=f"mission_admin_detail_{mission.id}"
        )])
    
    buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="admin_missions")])
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()
