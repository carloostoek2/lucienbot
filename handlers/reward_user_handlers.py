"""
Handlers de Recompensas para Usuarios - Lucien Bot

Muestra recompensas disponibles y sus misiones asociadas.
"""

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from keyboards.callback_data import MissionDetailCallback, RewardUserDetailCallback
from keyboards.inline_keyboards import back_keyboard
from services.mission_service import MissionService
from services.reward_service import RewardService

logger = logging.getLogger(__name__)
router = Router()

_EMPTY_REWARDS_TEXT = """🎩 Lucien:

No hay recompensas disponibles en este momento...

Vuelve mas tarde para nuevas oportunidades."""


def _build_rewards_list_text(total: int) -> str:
    return f"""🎩 Lucien:

🎁 Recompensas Disponibles: {total}

Elige una recompensa para ver como obtenerla...

"""


def _build_reward_detail_text(
    reward_emoji: str,
    reward_name: str,
    reward_desc: str | None,
    reward_gives: str,
    mission_name: str,
    mission_desc: str | None,
    status_text: str,
) -> str:
    return f"""🎩 Lucien:

{reward_emoji} {reward_name}

📝 Descripcion:
{reward_desc or "Sin descripcion"}

🎁 Que otorga:
{reward_gives}

🎯 Mision asociada:
{mission_name}
{mission_desc or ""}
{status_text}

<i>Completa la mision para recibir esta recompensa.</i>"""


def _build_progress_bar(current: int, target: int) -> tuple[str, int]:
    percentage = min(100, int((current / target) * 100))
    filled = int(percentage / 10)
    bar = "█" * filled + "░" * (10 - filled)
    return bar, percentage


@router.callback_query(F.data == "rewards_list")
async def show_available_rewards(callback: CallbackQuery):
    """Muestra las recompensas disponibles con sus misiones asociadas"""
    # Idempotency / dedup now handled globally by IdempotencyMiddleware (gsd-mw-hardening phase 5 cleanup)
    user_id = callback.from_user.id
    mission_service = MissionService()
    reward_service = RewardService()

    try:
        rewards_data = mission_service.get_available_rewards_for_user(user_id)

        if not rewards_data:
            await callback.message.edit_text(
                _EMPTY_REWARDS_TEXT, reply_markup=back_keyboard("back_to_main")
            )
            _safe_answer(callback, user_id)
            return

        text = _build_rewards_list_text(len(rewards_data))
        buttons = _build_rewards_buttons(rewards_data)
        buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="back_to_main")])

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await callback.message.edit_text(text, reply_markup=keyboard)
        _safe_answer(callback, user_id)

    finally:
        mission_service.close()
        reward_service.close()


@router.callback_query(RewardUserDetailCallback.filter())
async def reward_detail(callback: CallbackQuery, callback_data: RewardUserDetailCallback):
    """Muestra detalles de una recompensa y su mision asociada"""
    # Idempotency / dedup now handled globally by IdempotencyMiddleware (gsd-mw-hardening phase 5 cleanup)
    mission_id = callback_data.mission_id
    user_id = callback.from_user.id
    mission_service = MissionService()
    reward_service = RewardService()

    try:
        mission = mission_service.get_mission(mission_id)
        if not mission or not mission.reward_id:
            _safe_answer_alert(callback, mission_id, user_id, "Recompensa no encontrada")
            return

        reward = reward_service.get_reward(mission.reward_id)
        if not reward:
            _safe_answer_alert(callback, mission_id, user_id, "Recompensa no encontrada")
            return

        progress = mission_service.get_or_create_progress(user_id, mission_id)
        bar, percentage = _build_progress_bar(progress.current_value, mission.target_value)
        reward_emoji, reward_gives = reward_service.get_reward_emoji(reward)

        status_text = (
            "\n✅ ¡Mision completada! La recompensa ha sido entregada."
            if progress.is_completed
            else f"\n📊 Progreso: {bar} {percentage}%\n   {progress.current_value} / {mission.target_value}"
        )

        text = _build_reward_detail_text(
            reward_emoji,
            reward.name,
            reward.description,
            reward_gives,
            mission.name,
            mission.description,
            status_text,
        )

        buttons = [
            [
                InlineKeyboardButton(
                    text="🎯 Ver mision",
                    callback_data=MissionDetailCallback(mission_id=mission.id).pack(),
                )
            ],
            [InlineKeyboardButton(text="🔙 Volver a recompensas", callback_data="rewards_list")],
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback.message.edit_text(text, reply_markup=keyboard)
        _safe_answer(callback, user_id, mission_id)

    finally:
        mission_service.close()
        reward_service.close()


def _build_rewards_buttons(rewards_data: list) -> list:
    buttons = []
    for item in rewards_data:
        mission = item["mission"]
        reward = item["reward"]
        reward_emoji, _ = RewardService().get_reward_emoji(reward)
        status_emoji = "🔒" if item["progress"] and item["progress"].is_completed else "✨"
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{status_emoji} {reward_emoji} {reward.name[:30]}",
                    callback_data=RewardUserDetailCallback(mission_id=mission.id).pack(),
                )
            ]
        )
    return buttons


def _safe_answer(callback: CallbackQuery, user_id: int, mission_id: int = None):
    try:
        callback.answer()
    except Exception as e:
        loc = f"reward_detail_{mission_id}" if mission_id else "rewards_list"
        logger.warning(f"callback.answer() silenciosa en {loc} para user {user_id}: {e}")


def _safe_answer_alert(callback: CallbackQuery, mission_id: int, user_id: int, text: str):
    try:
        callback.answer(text, show_alert=True)
    except Exception as e:
        logger.warning(
            f"callback.answer() falló en reward_detail {mission_id} para user {user_id}: {e}"
        )
