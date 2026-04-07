"""
Handlers de Recompensas para Usuarios - Lucien Bot

Muestra recompensas disponibles y sus misiones asociadas.
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from services.mission_service import MissionService
from services.reward_service import RewardService
from keyboards.inline_keyboards import back_keyboard
import logging

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "rewards_list")
async def show_available_rewards(callback: CallbackQuery):
    """Muestra las recompensas disponibles con sus misiones asociadas"""
    user_id = callback.from_user.id

    mission_service = MissionService()
    reward_service = RewardService()

    try:
        # Obtener misiones disponibles que tengan recompensa
        available_missions = mission_service.get_available_missions()
        rewards_with_missions = []

        for mission in available_missions:
            if mission.reward_id:
                progress = mission_service.get_user_progress(user_id, mission.id)
                # Solo mostrar si no está completada o si es recurrente
                if not progress or not progress.is_completed or mission.frequency.value == "recurring":
                    reward = reward_service.get_reward(mission.reward_id)
                    if reward and reward.is_active:
                        rewards_with_missions.append({
                            'mission': mission,
                            'reward': reward,
                            'progress': progress
                        })

        if not rewards_with_missions:
            await callback.message.edit_text(
                """🎩 Lucien:

No hay recompensas disponibles en este momento...

Vuelve mas tarde para nuevas oportunidades.""",
                reply_markup=back_keyboard("back_to_main")
            )
            try:
                await callback.answer()
            except Exception:
                pass
            return

        total_rewards = len(rewards_with_missions)

        text = f"""🎩 Lucien:

🎁 Recompensas Disponibles: {total_rewards}

Elige una recompensa para ver como obtenerla...

"""

        buttons = []

        for item in rewards_with_missions:
            mission = item['mission']
            reward = item['reward']

            # Determinar emoji según tipo de recompensa
            reward_emoji = "🎁"
            if reward.reward_type.value == "besitos":
                reward_emoji = "💋"
            elif reward.reward_type.value == "package":
                reward_emoji = "📦"
            elif reward.reward_type.value == "vip_access":
                reward_emoji = "👑"

            status_emoji = "🔒" if item['progress'] and item['progress'].is_completed else "✨"

            buttons.append([InlineKeyboardButton(
                text=f"{status_emoji} {reward_emoji} {reward.name[:30]}",
                callback_data=f"reward_detail_{mission.id}"
            )])

        buttons.append([InlineKeyboardButton(
            text="🔙 Volver",
            callback_data="back_to_main"
        )])

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback.message.edit_text(text, reply_markup=keyboard)
        try:
            await callback.answer()
        except Exception:
            pass

    finally:
        mission_service.close()
        reward_service.close()


@router.callback_query(F.data.startswith("reward_detail_"))
async def reward_detail(callback: CallbackQuery):
    """Muestra detalles de una recompensa y su mision asociada"""
    mission_id = int(callback.data.replace("reward_detail_", ""))
    user_id = callback.from_user.id

    mission_service = MissionService()
    reward_service = RewardService()

    try:
        mission = mission_service.get_mission(mission_id)

        if not mission or not mission.reward_id:
            try:
                await callback.answer("Recompensa no encontrada", show_alert=True)
            except Exception:
                pass
            return

        reward = reward_service.get_reward(mission.reward_id)
        if not reward:
            try:
                await callback.answer("Recompensa no encontrada", show_alert=True)
            except Exception:
                pass
            return

        progress = mission_service.get_or_create_progress(user_id, mission_id)
        percentage = min(100, int((progress.current_value / mission.target_value) * 100))

        # Determinar que otorga la recompensa
        reward_gives = ""
        reward_emoji = "🎁"
        if reward.reward_type.value == "besitos":
            reward_gives = f"{reward.besito_amount} besitos"
            reward_emoji = "💋"
        elif reward.reward_type.value == "package":
            reward_gives = f"Paquete exclusivo: {reward.name}"
            reward_emoji = "📦"
        elif reward.reward_type.value == "vip_access":
            reward_gives = f"Acceso VIP: {reward.name}"
            reward_emoji = "👑"

        # Barra de progreso
        filled = int(percentage / 10)
        bar = "█" * filled + "░" * (10 - filled)

        status_text = ""
        if progress.is_completed:
            status_text = "\n✅ ¡Mision completada! La recompensa ha sido entregada."
        else:
            status_text = f"\n📊 Progreso: {bar} {percentage}%\n   {progress.current_value} / {mission.target_value}"

        text = f"""🎩 Lucien:

{reward_emoji} {reward.name}

📝 Descripcion:
{reward.description or 'Sin descripcion'}

🎁 Que otorga:
{reward_gives}

🎯 Mision asociada:
{mission.name}
{mission.description or ''}
{status_text}

<i>Completa la mision para recibir esta recompensa.</i>"""

        # Botones: Ir a la mision, Volver a recompensas
        buttons = [
            [InlineKeyboardButton(
                text="🎯 Ver mision",
                callback_data=f"mission_detail_{mission.id}"
            )],
            [InlineKeyboardButton(
                text="🔙 Volver a recompensas",
                callback_data="rewards_list"
            )]
        ]

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback.message.edit_text(text, reply_markup=keyboard)
        try:
            await callback.answer()
        except Exception:
            pass

    finally:
        mission_service.close()
        reward_service.close()
