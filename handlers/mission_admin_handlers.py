"""
Handlers de Misiones y Recompensas para Admin - Lucien Bot

Wizard de creacion de misiones y recompensas con cascada a paquetes.
"""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from keyboards.callback_data import (
    MissionDeleteCallback,
    MissionDetailCallback,
    MissionFreqSelectCallback,
    MissionStatsCallback,
    MissionToggleCallback,
    MissionTypeSelectCallback,
    SelectRewardMissionCallback,
)
from models.models import MissionFrequency, MissionType
from services import get_service
from services.mission_service import MissionService
from services.reward_service import RewardService
from utils.admin import is_admin

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


# ==================== MENU PRINCIPAL ====================


@router.callback_query(F.data == "admin_missions", lambda cb: is_admin(cb.from_user.id))
async def admin_missions_menu(callback: CallbackQuery):
    """Menu de gestion de misiones y recompensas"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Crear mision", callback_data="create_mission")],
            [InlineKeyboardButton(text="📋 Ver misiones", callback_data="list_missions")],
            [InlineKeyboardButton(text="🎁 Crear recompensa", callback_data="create_reward")],
            [InlineKeyboardButton(text="📋 Ver recompensas", callback_data="list_rewards")],
            [InlineKeyboardButton(text="📊 Estadisticas", callback_data="missions_stats")],
            [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_gamification")],
        ]
    )

    await callback.message.edit_text(
        """🎩 Lucien:

Los desafios que cultivan devocion...

Que deseas gestionar?""",
        reply_markup=keyboard,
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
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_missions")]
            ]
        ),
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
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_missions")]
            ]
        ),
    )
    await state.set_state(MissionWizardStates.waiting_description)


@router.message(MissionWizardStates.waiting_description)
async def process_mission_description(message: Message, state: FSMContext):
    """Procesa descripcion de mision"""
    description = None if message.text == "/skip" else message.text.strip()
    await state.update_data(description=description)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💋 Reaccionar N veces",
                    callback_data=MissionTypeSelectCallback(
                        mission_type=MissionType.REACTION_COUNT.value
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎁 Reclamar regalo N dias (consecutivos)",
                    callback_data=MissionTypeSelectCallback(
                        mission_type=MissionType.DAILY_GIFT_STREAK.value
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎁 Reclamar regalo N dias (total)",
                    callback_data=MissionTypeSelectCallback(
                        mission_type=MissionType.DAILY_GIFT_TOTAL.value
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🛒 Comprar en tienda",
                    callback_data=MissionTypeSelectCallback(
                        mission_type=MissionType.STORE_PURCHASE.value
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="👑 Tener VIP activo",
                    callback_data=MissionTypeSelectCallback(
                        mission_type=MissionType.VIP_ACTIVE.value
                    ).pack(),
                )
            ],
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_missions")],
        ]
    )

    await message.answer(
        """🎩 Lucien:

Paso 3 de 6: Tipo de mision

Selecciona el tipo de desafio:""",
        reply_markup=keyboard,
    )
    await state.set_state(MissionWizardStates.selecting_type)


@router.callback_query(MissionWizardStates.selecting_type, MissionTypeSelectCallback.filter())
async def select_mission_type(
    callback: CallbackQuery, state: FSMContext, callback_data: MissionTypeSelectCallback
):
    """Selecciona tipo de mision"""
    try:
        mission_type = MissionType(callback_data.mission_type)
    except ValueError:
        await callback.answer("Tipo invalido", show_alert=True)
        return

    await state.update_data(mission_type=mission_type)

    examples = {
        MissionType.REACTION_COUNT: "10 (para 10 reacciones)",
        MissionType.DAILY_GIFT_STREAK: "7 (para 7 dias consecutivos)",
        MissionType.DAILY_GIFT_TOTAL: "5 (para 5 dias en total)",
        MissionType.STORE_PURCHASE: "1 (para 1 compra)",
        MissionType.VIP_ACTIVE: "1 (siempre 1 para VIP)",
    }

    await callback.message.edit_text(
        f"""🎩 Lucien:

Paso 4 de 6: Valor objetivo

Indica la meta numerica:
Ejemplo: {examples.get(mission_type, "10")}""",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_missions")]
            ]
        ),
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

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Una vez",
                    callback_data=MissionFreqSelectCallback(
                        frequency=MissionFrequency.ONE_TIME.value
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="Recurrente",
                    callback_data=MissionFreqSelectCallback(
                        frequency=MissionFrequency.RECURRING.value
                    ).pack(),
                )
            ],
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_missions")],
        ]
    )

    await message.answer(
        """🎩 Lucien:

Paso 5 de 6: Frecuencia

Selecciona la frecuencia:

Una vez: El usuario la completa una sola vez
Recurrente: Se reinicia al completarse""",
        reply_markup=keyboard,
    )
    await state.set_state(MissionWizardStates.selecting_frequency)


@router.callback_query(MissionWizardStates.selecting_frequency, MissionFreqSelectCallback.filter())
async def select_frequency(
    callback: CallbackQuery, state: FSMContext, callback_data: MissionFreqSelectCallback
):
    """Selecciona frecuencia"""
    try:
        frequency = MissionFrequency(callback_data.frequency)
    except ValueError:
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
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="➕ Crear recompensa", callback_data="create_reward"
                        )
                    ],
                    [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_missions")],
                ]
            ),
        )
        await state.clear()
        await callback.answer()
        return

    buttons = []
    for reward in rewards:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{reward.name} ({reward.reward_type.value})",
                    callback_data=SelectRewardMissionCallback(reward_id=reward.id).pack(),
                )
            ]
        )

    buttons.append([InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_missions")])

    await callback.message.edit_text(
        """🎩 Lucien:

Paso 6 de 6: Recompensa

Selecciona la recompensa para esta mision:""",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await state.set_state(MissionWizardStates.selecting_reward)
    await callback.answer()


@router.callback_query(MissionWizardStates.selecting_reward, SelectRewardMissionCallback.filter())
async def select_reward_for_mission(
    callback: CallbackQuery, state: FSMContext, callback_data: SelectRewardMissionCallback
):
    """Selecciona recompensa y muestra confirmacion"""
    reward_id = callback_data.reward_id

    await state.update_data(reward_id=reward_id)
    data = await state.get_data()

    reward_service = RewardService()
    reward = reward_service.get_reward(reward_id)

    freq_text = "Una vez" if data.get("frequency") == MissionFrequency.ONE_TIME else "Recurrente"

    text = f"""🎩 Lucien:

Resumen de la mision:

📋 Nombre: {data.get("name")}
📝 Descripcion: {data.get("description") or "Sin descripcion"}
🎯 Tipo: {data.get("mission_type").value}
📊 Meta: {data.get("target_value")}
🔄 Frecuencia: {freq_text}
🎁 Recompensa: {reward.name if reward else "Ninguna"}

Deseas crear esta mision?"""

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✅ Crear", callback_data="confirm_create_mission")],
                [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_missions")],
            ]
        ),
    )
    await state.set_state(MissionWizardStates.confirming)
    await callback.answer()


@router.callback_query(MissionWizardStates.confirming, F.data == "confirm_create_mission")
async def confirm_create_mission(callback: CallbackQuery, state: FSMContext):
    """Crea la mision"""
    data = await state.get_data()
    with get_service(MissionService) as mission_service:
        try:
            mission = mission_service.create_mission(
                name=data.get("name"),
                description=data.get("description"),
                mission_type=data.get("mission_type"),
                target_value=data.get("target_value"),
                reward_id=data.get("reward_id"),
                frequency=data.get("frequency"),
                created_by=callback.from_user.id,
            )

            await callback.message.edit_text(
                f"""🎩 Lucien:

        Mision creada exitosamente!

        📋 {mission.name}
        🎯 Tipo: {mission.mission_type.value}
        📊 Meta: {mission.target_value}

        La mision esta activa y disponible para los usuarios.""",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_missions")]
                    ]
                ),
            )
            logger.info(f"Mision creada: {mission.name} por admin {callback.from_user.id}")

        except Exception as e:
            logger.error(f"Error creando mision: {e}")
            await callback.message.edit_text(
                "Error al crear la mision. Intenta de nuevo.",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_missions")]
                    ]
                ),
            )

        await state.clear()
        await callback.answer()

    # ==================== LISTAR MISIONES ====================


@router.callback_query(F.data == "list_missions", lambda cb: is_admin(cb.from_user.id))
async def list_missions(callback: CallbackQuery):
    """Lista todas las misiones"""
    with get_service(MissionService) as mission_service:
        missions = mission_service.get_all_missions(active_only=False)

        if not missions:
            await callback.message.edit_text(
                "No hay misiones registradas.",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_missions")]
                    ]
                ),
            )
            await callback.answer()
            return

        text = "🎩 Lucien:\n\nMisiones registradas:\n\n"
        buttons = []

        for mission in missions:
            status = "✅" if mission.is_active else "❌"
            text += f"{status} {mission.name} ({mission.mission_type.value})\n"
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"{status} {mission.name[:30]}",
                        callback_data=MissionDetailCallback(mission_id=mission.id).pack(),
                    )
                ]
            )

        buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="admin_missions")])

        await callback.message.edit_text(
            text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
        await callback.answer()

    # ==================== VER DETALLE DE MISION ====================


@router.callback_query(MissionDetailCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def mission_admin_detail(callback: CallbackQuery, callback_data: MissionDetailCallback):
    """Muestra detalles de una mision"""
    mission_id = callback_data.mission_id

    with get_service(MissionService) as mission_service:
        mission = mission_service.get_mission(mission_id)

        if not mission:
            await callback.answer("Mision no encontrada", show_alert=True)
            return

        status = "✅ Activo" if mission.is_active else "❌ Inactivo"
        freq_text = "Una vez" if mission.frequency.value == "one_time" else "Recurrente"

        reward_text = "Sin recompensa"
        if mission.reward:
            reward_text = f"{mission.reward.name} ({mission.reward.reward_type.value})"

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=f"{'Desactivar' if mission.is_active else 'Activar'}",
                        callback_data=MissionToggleCallback(mission_id=mission.id).pack(),
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🗑️ Eliminar",
                        callback_data=MissionDeleteCallback(mission_id=mission.id).pack(),
                    )
                ],
                [InlineKeyboardButton(text="🔙 Volver", callback_data="list_missions")],
            ]
        )

        await callback.message.edit_text(
            f"""🎩 Lucien:

        📋 {mission.name}

        📝 {mission.description or "Sin descripcion"}

        📊 Informacion:
           • Tipo: {mission.mission_type.value}
           • Meta: {mission.target_value}
           • Frecuencia: {freq_text}
           • Estado: {status}

        🎁 Recompensa: {reward_text}

        Que deseas hacer?""",
            reply_markup=keyboard,
        )
        await callback.answer()


@router.callback_query(MissionToggleCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def toggle_mission(callback: CallbackQuery, callback_data: MissionToggleCallback):
    """Activa/desactiva una mision"""
    mission_id = callback_data.mission_id

    with get_service(MissionService) as mission_service:
        mission = mission_service.get_mission(mission_id)

        if not mission:
            await callback.answer("Mision no encontrada", show_alert=True)
            return

        mission_service.update_mission(mission_id, is_active=not mission.is_active)

        status = "activada" if not mission.is_active else "desactivada"
        await callback.answer(f"Mision {status}")

        # Reload mission and show updated detail
        new_mission = mission_service.get_mission(mission_id)
        if new_mission:
            await show_mission_detail(callback, new_mission)
        await callback.answer()


async def show_mission_detail(callback: CallbackQuery, mission):
    """Muestra detalles de una mision (helper)"""
    status = "✅ Activo" if mission.is_active else "❌ Inactivo"
    freq_text = "Una vez" if mission.frequency.value == "one_time" else "Recurrente"

    reward_text = "Sin recompensa"
    if mission.reward:
        reward_text = f"{mission.reward.name} ({mission.reward.reward_type.value})"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{'Desactivar' if mission.is_active else 'Activar'}",
                    callback_data=MissionToggleCallback(mission_id=mission.id).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑️ Eliminar",
                    callback_data=MissionDeleteCallback(mission_id=mission.id).pack(),
                )
            ],
            [InlineKeyboardButton(text="🔙 Volver", callback_data="list_missions")],
        ]
    )

    await callback.message.edit_text(
        f"""🎩 Lucien:

        📋 {mission.name}

        📝 {mission.description or "Sin descripcion"}

        📊 Informacion:
           • Tipo: {mission.mission_type.value}
           • Meta: {mission.target_value}
           • Frecuencia: {freq_text}
           • Estado: {status}

        🎁 Recompensa: {reward_text}

        Que deseas hacer?""",
        reply_markup=keyboard,
    )


@router.callback_query(MissionDeleteCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def delete_mission_confirm(callback: CallbackQuery, callback_data: MissionDeleteCallback):
    """Confirma o ejecuta eliminacion de mision"""
    mission_id = callback_data.mission_id

    with get_service(MissionService) as mission_service:
        if callback_data.confirmed:
            # Execute deletion
            success = mission_service.delete_mission(mission_id)

            if success:
                await callback.message.edit_text(
                    "🎩 Lucien:\n\n✅ Mision eliminada correctamente.",
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[
                            [InlineKeyboardButton(text="🔙 Volver", callback_data="list_missions")]
                        ]
                    ),
                )
            else:
                await callback.message.edit_text(
                    "Error al eliminar la mision.",
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[
                            [InlineKeyboardButton(text="🔙 Volver", callback_data="list_missions")]
                        ]
                    ),
                )
            await callback.answer()
            return

    # Show confirmation keyboard
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Si, eliminar",
                    callback_data=MissionDeleteCallback(
                        mission_id=mission_id, confirmed=True
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Cancelar",
                    callback_data=MissionDetailCallback(mission_id=mission_id).pack(),
                )
            ],
        ]
    )

    await callback.message.edit_text(
        "🎩 Lucien:\n\nEstas seguro de eliminar esta mision?\n\nEsta accion no se puede deshacer.",
        reply_markup=keyboard,
    )
    await callback.answer()

    # ==================== ESTADISTICAS ====================


@router.callback_query(F.data == "missions_stats", lambda cb: is_admin(cb.from_user.id))
async def missions_stats(callback: CallbackQuery):
    """Muestra estadisticas de misiones"""
    with get_service(MissionService) as mission_service:
        missions = mission_service.get_all_missions(active_only=False)

        total_missions = len(missions)
        active_missions = sum(1 for m in missions if m.is_active)

        text = f"""🎩 Lucien:

        📊 Estadisticas de Misiones:

        📋 Misiones:
           • Activas: {active_missions}
           • Total: {total_missions}

        Selecciona una mision para ver estadisticas detalladas:"""

        buttons = []
        for mission in missions:
            if mission.is_active:
                buttons.append(
                    [
                        InlineKeyboardButton(
                            text=f"📊 {mission.name[:30]}",
                            callback_data=MissionStatsCallback(mission_id=mission.id).pack(),
                        )
                    ]
                )

        buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="admin_missions")])

        await callback.message.edit_text(
            text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
        await callback.answer()


@router.callback_query(MissionStatsCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def mission_detail_stats(callback: CallbackQuery, callback_data: MissionStatsCallback):
    """Muestra estadisticas detalladas de una mision"""
    mission_id = callback_data.mission_id

    with get_service(MissionService) as mission_service:
        stats = mission_service.get_mission_stats(mission_id)

        if not stats:
            await callback.answer("Mision no encontrada", show_alert=True)
            return

        await callback.message.edit_text(
            f"""🎩 Lucien:

        📊 Estadisticas: {stats["mission_name"]}

        📈 Progreso:
           • Usuarios participando: {stats["total_users"]}
           • Completadas: {stats["completed"]}
           • En progreso: {stats["in_progress"]}
           • Tasa de completion: {stats["completion_rate"]}%
        """,
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Volver", callback_data="missions_stats")]
                ]
            ),
        )
        await callback.answer()
