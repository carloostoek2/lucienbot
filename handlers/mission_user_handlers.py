"""
Handlers de Misiones para Usuarios - Lucien Bot

Muestra misiones activas y progreso del usuario.
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from services.mission_service import MissionService
from services.reward_service import RewardService
from keyboards.inline_keyboards import back_keyboard
import logging

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "my_missions")
async def show_my_missions(callback: CallbackQuery):
    """Muestra las misiones activas del usuario"""
    user_id = callback.from_user.id
    
    mission_service = MissionService()
    active_missions = mission_service.get_user_active_missions(user_id)
    
    if not active_missions:
        await callback.message.edit_text(
            """🎩 Lucien:

No hay desafios disponibles en este momento...

Vuelve mas tarde para nuevas misiones.""",
            reply_markup=back_keyboard("back_to_main")
        )
        await callback.answer()
        return
    
    text = """🎩 Lucien:

Tus desafios actuales...

🎯 Misiones Activas:

"""
    
    buttons = []
    
    for item in active_missions:
        mission = item['mission']
        progress = item['progress']
        percentage = item['percentage']
        
        # Barra de progreso
        filled = int(percentage / 10)
        bar = "█" * filled + "░" * (10 - filled)
        
        status = "✅ Completada" if progress.is_completed else f"{bar} {percentage}%"
        
        text += f"📋 {mission.name}\n"
        text += f"   {mission.description or 'Sin descripcion'}\n"
        text += f"   Progreso: {progress.current_value}/{mission.target_value} {status}\n\n"
        
        if not progress.is_completed:
            buttons.append([InlineKeyboardButton(
                text=f"Ver: {mission.name[:25]}",
                callback_data=f"mission_detail_{mission.id}"
            )])
    
    buttons.append([InlineKeyboardButton(
        text="🔙 Volver",
        callback_data="back_to_main"
    )])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("mission_detail_"))
async def mission_detail(callback: CallbackQuery):
    """Muestra detalles de una mision"""
    mission_id = int(callback.data.replace("mission_detail_", ""))
    user_id = callback.from_user.id
    
    mission_service = MissionService()
    mission = mission_service.get_mission(mission_id)
    
    if not mission:
        await callback.answer("Mision no encontrada", show_alert=True)
        return
    
    progress = mission_service.get_or_create_progress(user_id, mission_id)
    percentage = min(100, int((progress.current_value / mission.target_value) * 100))
    
    # Barra de progreso
    filled = int(percentage / 10)
    bar = "█" * filled + "░" * (10 - filled)
    
    # Info de recompensa
    reward_text = "Sin recompensa"
    if mission.reward:
        if mission.reward.reward_type.value == "besitos":
            reward_text = f"{mission.reward.besito_amount} besitos"
        elif mission.reward.reward_type.value == "package":
            reward_text = f"Paquete: {mission.reward.name}"
        elif mission.reward.reward_type.value == "vip_access":
            reward_text = f"Acceso VIP: {mission.reward.name}"
    
    text = f"""🎩 Lucien:

📋 {mission.name}

📝 Descripcion:
{mission.description or 'Sin descripcion'}

📊 Progreso:
{bar} {percentage}%
{progress.current_value} / {mission.target_value}

🎁 Recompensa:
{reward_text}

<i>Completa esta mision para recibir tu recompensa.</i>"""
    
    await callback.message.edit_text(
        text,
        reply_markup=back_keyboard("my_missions")
    )
    await callback.answer()


@router.callback_query(F.data == "claim_mission_reward")
async def claim_mission_reward(callback: CallbackQuery):
    """Reclama recompensa de mision completada"""
    await callback.answer("Funcion en desarrollo", show_alert=True)
