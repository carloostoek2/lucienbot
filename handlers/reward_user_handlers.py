"""
Handlers de Recompensas para Usuarios - Lucien Bot

Muestra recompensas disponibles y sus misiones asociadas.
"""

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from keyboards.callback_data import MissionDetailCallback, RewardUserDetailCallback
from keyboards.inline_keyboards import back_keyboard
from services import get_service
from services.mission_service import MissionService
from services.reward_service import get_reward_emoji

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


def compute_reward_status_text(progress, mission) -> str:
    """Construye el texto de status (completada o barra de progreso) para el detalle de recompensa. Función pura."""
    if progress.is_completed:
        return "\n✅ ¡Mision completada! La recompensa ha sido entregada."
    bar, percentage = _build_progress_bar(progress.current_value, mission.target_value)
    return (
        f"\n📊 Progreso: {bar} {percentage}%\n   {progress.current_value} / {mission.target_value}"
    )


def build_reward_detail_keyboard(mission_id: int) -> InlineKeyboardMarkup:
    """Construye el teclado inline para el detalle de recompensa (ver mision + volver)."""
    buttons = [
        [
            InlineKeyboardButton(
                text="🎯 Ver mision",
                callback_data=MissionDetailCallback(mission_id=mission_id).pack(),
            )
        ],
        [InlineKeyboardButton(text="🔙 Volver a recompensas", callback_data="rewards_list")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(F.data == "rewards_list")
async def show_available_rewards(callback: CallbackQuery):
    """Muestra las recompensas disponibles con sus misiones asociadas"""
    # Idempotency / dedup now handled globally by IdempotencyMiddleware (gsd-mw-hardening phase 5 cleanup)
    user_id = callback.from_user.id

    with get_service(MissionService) as mission_service:
        rewards_data = mission_service.get_available_rewards_for_user(user_id)
        logger.info(
            f"reward_user_handlers | show_available_rewards | user_id={user_id} | count={len(rewards_data)}"
        )

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


@router.callback_query(RewardUserDetailCallback.filter())
async def reward_detail(callback: CallbackQuery, callback_data: RewardUserDetailCallback):
    """Muestra detalles de una recompensa y su mision asociada"""
    # Idempotency / dedup now handled globally by IdempotencyMiddleware (gsd-mw-hardening phase 5 cleanup)
    mission_id = callback_data.mission_id
    user_id = callback.from_user.id

    with get_service(MissionService) as mission_service:
        mission = mission_service.get_mission(mission_id)
        if not mission or not mission.reward:
            _safe_answer_alert(callback, mission_id, user_id, "Recompensa no encontrada")
            return

        progress = mission_service.get_or_create_progress(user_id, mission_id)
        reward_emoji, reward_gives = get_reward_emoji(mission.reward)

        status_text = compute_reward_status_text(progress, mission)

        text = _build_reward_detail_text(
            reward_emoji,
            mission.reward.name,
            mission.reward.description,
            reward_gives,
            mission.name,
            mission.description,
            status_text,
        )

        keyboard = build_reward_detail_keyboard(mission.id)

        await callback.message.edit_text(text, reply_markup=keyboard)
        _safe_answer(callback, user_id, mission_id)

        logger.info(
            f"reward_user_handlers | reward_detail | user_id={user_id} | mission_id={mission_id} | completed={progress.is_completed}"
        )


def _build_rewards_buttons(rewards_data: list) -> list:
    buttons = []
    for item in rewards_data:
        mission = item["mission"]
        reward = item["reward"]
        reward_emoji, _ = get_reward_emoji(reward)
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
