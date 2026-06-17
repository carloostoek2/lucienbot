"""
Handlers de Misiones para Usuarios - Lucien Bot

Muestra misiones activas y progreso del usuario.
"""

import html
import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from keyboards.callback_data import MissionDetailCallback
from keyboards.inline_keyboards import back_keyboard
from services import get_service
from services.mission_service import MissionService
from utils.admin import is_admin
from utils.lucien_voice import LucienVoice

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "my_missions", lambda cb: not is_admin(cb.from_user.id))
async def show_my_missions(callback: CallbackQuery):
    """Muestra las misiones activas del usuario"""
    user_id = callback.from_user.id

    with get_service(MissionService) as mission_service:
        active_missions = await mission_service.get_user_active_missions(
            user_id, bot=callback.bot
        )

        if not active_missions:
            await callback.message.edit_text(
                """🎩 Lucien:

        No hay desafios disponibles en este momento...

        Vuelve mas tarde para nuevas misiones.""",
                reply_markup=back_keyboard("back_to_main"),
            )
            await callback.answer()
            return

        text = """🎩 Lucien:

        Tus desafios actuales...

        🎯 Misiones Activas:

        """

        buttons = []

        for item in active_missions:
            mission = item["mission"]
            progress = item["progress"]
            percentage = item["percentage"]

            # Barra de progreso
            filled = int(percentage / 10)
            bar = "█" * filled + "░" * (10 - filled)

            status = "✅ Completada" if progress.is_completed else f"{bar} {percentage}%"

            text += f"📋 {html.escape(mission.name)}\n"
            text += f"   {html.escape(mission.description or 'Sin descripcion')}\n"
            text += f"   Progreso: {progress.current_value}/{mission.target_value} {status}\n\n"

            if not progress.is_completed:
                buttons.append(
                    [
                        InlineKeyboardButton(
                            text=f"Ver: {html.escape(mission.name[:25])}",
                            callback_data=MissionDetailCallback(mission_id=mission.id).pack(),
                        )
                    ]
                )

        buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="back_to_main")])

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()


@router.callback_query(MissionDetailCallback.filter(), lambda cb: not is_admin(cb.from_user.id))
async def mission_detail(callback: CallbackQuery, callback_data: MissionDetailCallback):
    """Muestra detalles de una mision"""
    mission_id = callback_data.mission_id
    user_id = callback.from_user.id

    with get_service(MissionService) as mission_service:
        mission = mission_service.get_mission(mission_id)

        if not mission:
            await callback.answer("Mision no encontrada", show_alert=True)
            return

        progress = mission_service.get_or_create_progress(user_id, mission_id)
        await mission_service.deliver_pending_rewards_for_mission(
            user_id, mission_id, bot=callback.bot
        )
        percentage = min(100, int((progress.current_value / mission.target_value) * 100))

        # Barra de progreso
        filled = int(percentage / 10)
        bar = "█" * filled + "░" * (10 - filled)

        safe_name = html.escape(mission.name)
        safe_desc = html.escape(mission.description or "Sin descripcion")
        reward_text = "Sin recompensa"
        if mission.reward:
            if mission.reward.reward_type.value == "besitos":
                reward_text = f"{mission.reward.besito_amount} besitos"
            elif mission.reward.reward_type.value == "package":
                reward_text = f"Paquete: {html.escape(mission.reward.name)}"
            elif mission.reward.reward_type.value == "vip_access":
                reward_text = f"Acceso VIP: {html.escape(mission.reward.name)}"

        text = f"""🎩 Lucien:

        📋 {safe_name}

        📝 Descripcion:
        {safe_desc}

        📊 Progreso:
        {bar} {percentage}%
        {progress.current_value} / {mission.target_value}

        🎁 Recompensa:
        {reward_text}

        <i>Completa esta mision para recibir tu recompensa.</i>"""

        await callback.message.edit_text(text, reply_markup=back_keyboard("my_missions"))
        await callback.answer()


@router.callback_query(F.data == "claim_mission_reward", lambda cb: not is_admin(cb.from_user.id))
async def claim_mission_reward(callback: CallbackQuery):
    """Catch-up de recompensas de misiones pendientes (red de seguridad)."""
    user_id = callback.from_user.id
    with get_service(MissionService) as mission_service:
        delivered = await mission_service.deliver_pending_rewards(
            user_id, bot=callback.bot
        )
    if delivered:
        await callback.answer(
            LucienVoice.mission_reward_claim_success_alert("sus misiones"),
            show_alert=True,
        )
    else:
        await callback.answer(
            LucienVoice.mission_reward_claim_pending_alert(), show_alert=True
        )
