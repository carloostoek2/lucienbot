"""
Handlers de Administracion de Promociones por Racha - Lucien Bot

Handlers FSM para gestion de promociones por racha de trivia.
Phase 17 - Promos de Trivias.
"""

import logging
from datetime import UTC, datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from keyboards.callback_data import (
    TriviaStreakCategoryCallback,
    TriviaStreakConfirmDeleteCallback,
    TriviaStreakDeleteCallback,
    TriviaStreakDetailCallback,
    TriviaStreakGoalTypeCallback,
    TriviaStreakRedemptionsCallback,
    TriviaStreakToggleCallback,
)
from services import StreakPromotionService, get_service
from services.scheduler_service import get_scheduler
from services.trivia_service import TriviaCategoryService
from utils.admin import is_admin

logger = logging.getLogger(__name__)
router = Router()


class StreakPromotionStates(StatesGroup):
    """Estados FSM para el wizard de creacion de promocion por racha."""

    waiting_name = State()
    waiting_description = State()
    waiting_level = State()
    waiting_more_levels = State()
    waiting_duration_mode = State()
    waiting_start_date = State()
    waiting_end_date = State()
    waiting_duration_hours = State()
    waiting_category = State()
    waiting_game_types = State()
    waiting_confirmation = State()


def streak_promotion_action_keyboard(promo_id: int) -> InlineKeyboardMarkup:
    """Teclado de acciones para una promocion especifica."""
    buttons = [
        [
            InlineKeyboardButton(
                text="\U0001f4cb Ver canjes",
                callback_data=TriviaStreakRedemptionsCallback(promo_id=promo_id).pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="\U000023f8️ Pausar / ▶️ Activar",
                callback_data=TriviaStreakToggleCallback(promo_id=promo_id).pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="\U0001f5d1️ Eliminar",
                callback_data=TriviaStreakDeleteCallback(promo_id=promo_id).pack(),
            )
        ],
        [InlineKeyboardButton(text="\U0001f519 Volver", callback_data="admin_streak_promotions")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ==================== MAIN MENU ====================


def _build_promotions_list(promotions) -> tuple:
    """Construye el texto y botones para la lista de promociones."""
    text = (
        "\U0001f3c6 <b>Promociones por Racha</b>\n\n"
        "<i>Lucien gestiona las promociones que recompensan a los "
        "visitantes mas dedicados en las trivias de Diana.</i>\n\n"
    )
    buttons = []
    for promo in promotions:
        if promo.is_active and promo.status.value == "active":
            icon = "\U0001f7e2"
        elif promo.status.value == "paused":
            icon = "\U0001f534"
        elif promo.status.value == "pending":
            icon = "\U000023f3"
        else:
            icon = "⚪"
        level_desc = ", ".join(
            f"{level.consecutive_required}r/{level.discount_pct}%({level.codes_available}cod)"
            for level in promo.levels
        )
        desc_short = (promo.description or "")[:50]
        if promo.description and len(promo.description) > 50:
            desc_short += "..."
        text += f"{icon} <b>{promo.name}</b>\n   <i>{desc_short}</i>\n   Niveles: {level_desc}\n\n"
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{icon} {promo.name}",
                    callback_data=TriviaStreakDetailCallback(promo_id=promo.id).pack(),
                )
            ]
        )
    return text, buttons


@router.callback_query(F.data == "admin_streak_promotions", lambda cb: is_admin(cb.from_user.id))
async def admin_streak_promotions_menu(callback: CallbackQuery):
    """Menu principal de gestion de promociones por racha."""
    with get_service(StreakPromotionService) as service:
        promotions = service.get_all_promotions()

    text, buttons = _build_promotions_list(promotions)
    buttons.extend(
        [
            [
                InlineKeyboardButton(
                    text="➕ Forjar nueva promocion", callback_data="streak_promo_create"
                )
            ],
            [
                InlineKeyboardButton(
                    text="\U0001f519 Volver a Trivias", callback_data="admin_trivia"
                )
            ],
        ]
    )

    await callback.message.edit_text(
        text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML"
    )
    await callback.answer()
    logger.info(
        f"trivia_streak_admin_handlers - admin_streak_promotions_menu - "
        f"{callback.from_user.id} - shown"
    )


# ==================== CREATE WIZARD ====================


@router.callback_query(F.data == "streak_promo_create", lambda cb: is_admin(cb.from_user.id))
async def streak_promo_create_start(callback: CallbackQuery, state: FSMContext):
    """Inicia el wizard de creacion de promocion: pide el nombre."""
    await state.set_state(StreakPromotionStates.waiting_name)
    await callback.message.edit_text(
        "\U0001f3c6 <b>Forjar nueva promocion por racha</b>\n\n"
        "<i>Lucien le guiara en la creacion de una nueva promocion.</i>\n\n"
        "\U0001f539 <b>Paso 1/6:</b> Ingrese el <b>nombre</b> de la promocion:\n\n"
        '<i>Ejemplo: "Semana de la Devocion"</i>',
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_streak_promotions")]
            ]
        ),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(StreakPromotionStates.waiting_name, lambda msg: is_admin(msg.from_user.id))
async def streak_promo_get_name(message, state: FSMContext):
    """Guarda el nombre y pide la descripcion."""
    name = message.text.strip()
    if not name or len(name) > 100:
        await message.answer("⚠️ El nombre debe tener entre 1 y 100 caracteres. Intente de nuevo:")
        return
    await state.update_data(name=name)
    await state.set_state(StreakPromotionStates.waiting_description)
    await message.answer(
        "\U0001f539 <b>Paso 2/6:</b> Ingrese una <b>descripcion</b> para la promocion:\n\n"
        "<i>Explique que deben hacer los visitantes para ganar los codigos.</i>",
        parse_mode="HTML",
    )


@router.message(StreakPromotionStates.waiting_description, lambda msg: is_admin(msg.from_user.id))
async def streak_promo_get_description(message, state: FSMContext):
    """Guarda la descripcion y pide el primer nivel."""
    description = message.text.strip()
    if not description:
        await message.answer("⚠️ La descripcion no puede estar vacia. Intente de nuevo:")
        return
    await state.update_data(description=description, levels=[])
    await state.set_state(StreakPromotionStates.waiting_level)
    await message.answer(
        "\U0001f539 <b>Paso 3/6 - Nivel 1:</b>\n\n"
        "Ingrese los datos del nivel en este formato:\n"
        "<code>preguntas_consecutivas, %_descuento, codigos_disponibles</code>\n\n"
        "<i>Ejemplo: <code>5, 30, 20</code> = 5 aciertos seguidos, 30% descuento, 20 codigos</i>",
        parse_mode="HTML",
    )


@router.message(StreakPromotionStates.waiting_level, lambda msg: is_admin(msg.from_user.id))
async def streak_promo_get_level(message, state: FSMContext):
    """Procesa un nivel y pregunta si desea agregar mas."""
    try:
        parts = message.text.strip().split(",")
        if len(parts) != 3:
            raise ValueError("Formato invalido")
        consecutive = int(parts[0].strip())
        discount = int(parts[1].strip())
        codes = int(parts[2].strip())
        if consecutive <= 0 or discount <= 0 or codes <= 0:
            raise ValueError("Valores deben ser positivos")
    except (ValueError, IndexError):
        await message.answer(
            "⚠️ Formato invalido. Use: <code>preguntas, descuento, codigos</code>\n"
            "<i>Ejemplo: <code>5, 30, 20</code></i>",
            parse_mode="HTML",
        )
        return

    data = await state.get_data()
    levels = data.get("levels", [])
    level_num = len(levels) + 1
    levels.append(
        {
            "consecutive_required": consecutive,
            "discount_pct": discount,
            "codes_available": codes,
        }
    )
    await state.update_data(levels=levels)
    await state.set_state(StreakPromotionStates.waiting_more_levels)

    buttons = [
        [
            InlineKeyboardButton(
                text="✅ Si, agregar otro nivel", callback_data="streak_promo_add_level"
            )
        ],
        [
            InlineKeyboardButton(
                text="\U0001f6ab No, continuar", callback_data="streak_promo_no_more_levels"
            )
        ],
    ]
    await message.answer(
        f"\U00002705 Nivel {level_num} guardado: {consecutive} preguntas, "
        f"{discount}% desc., {codes} codigos.\n\n"
        "\U0001f539 <b>Agregar otro nivel?</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "streak_promo_add_level", lambda cb: is_admin(cb.from_user.id))
async def streak_promo_add_another_level(callback: CallbackQuery, state: FSMContext):
    """Vuelve al estado waiting_level para agregar otro nivel."""
    data = await state.get_data()
    level_num = len(data.get("levels", [])) + 1
    await state.set_state(StreakPromotionStates.waiting_level)
    await callback.message.edit_text(
        f"\U0001f539 <b>Paso 3/6 - Nivel {level_num}:</b>\n\n"
        "Ingrese los datos del nivel:\n"
        "<code>preguntas_consecutivas, %_descuento, codigos_disponibles</code>\n\n"
        f"<i>Niveles actuales: {len(data.get('levels', []))} configurados</i>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(
    F.data == "streak_promo_no_more_levels", lambda cb: is_admin(cb.from_user.id)
)
async def streak_promo_choose_duration_mode(callback: CallbackQuery, state: FSMContext):
    """Pregunta el modo de duracion de la promocion."""
    await state.set_state(StreakPromotionStates.waiting_duration_mode)
    buttons = [
        [
            InlineKeyboardButton(
                text="\U0001f4c5 Fechas concretas", callback_data="streak_promo_dur_dates"
            )
        ],
        [
            InlineKeyboardButton(
                text="\U000023f1️ Duracion relativa (horas)",
                callback_data="streak_promo_dur_relative",
            )
        ],
    ]
    await callback.message.edit_text(
        "\U0001f539 <b>Paso 4/6:</b> Seleccione el modo de duracion:\n\n"
        "<i>Las promociones pueden tener fechas concretas de inicio y fin, "
        "o una duracion relativa desde su activacion.</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "streak_promo_dur_dates", lambda cb: is_admin(cb.from_user.id))
async def streak_promo_get_start_date(callback: CallbackQuery, state: FSMContext):
    """Pide la fecha de inicio de la promocion."""
    await state.update_data(duration_mode="dates")
    await state.set_state(StreakPromotionStates.waiting_start_date)
    await callback.message.edit_text(
        "\U0001f539 <b>Fecha de inicio:</b>\n\n"
        "Ingrese la fecha de inicio en formato:\n"
        "<code>DD/MM/AAAA HH:MM</code>\n\n"
        "<i>Ejemplo: <code>15/05/2026 10:00</code></i>\n\n"
        "O escriba <code>ahora</code> para iniciar inmediatamente.",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(StreakPromotionStates.waiting_start_date, lambda msg: is_admin(msg.from_user.id))
async def streak_promo_get_end_date(message, state: FSMContext):
    """Guarda la fecha de inicio y pide la fecha de fin."""
    text = message.text.strip()
    if text.lower() == "ahora":
        start_date = datetime.now(UTC)
    else:
        try:
            start_date = datetime.strptime(text, "%d/%m/%Y %H:%M")
        except ValueError:
            await message.answer(
                "⚠️ Formato invalido. Use <code>DD/MM/AAAA HH:MM</code> o <code>ahora</code>.",
                parse_mode="HTML",
            )
            return

    await state.update_data(start_date=start_date)
    await state.set_state(StreakPromotionStates.waiting_end_date)
    await message.answer(
        "\U0001f539 <b>Fecha de fin:</b>\n\n"
        "Ingrese la fecha de finalizacion en formato:\n"
        "<code>DD/MM/AAAA HH:MM</code>\n\n"
        "<i>Ejemplo: <code>15/06/2026 23:59</code></i>",
        parse_mode="HTML",
    )


@router.message(StreakPromotionStates.waiting_end_date, lambda msg: is_admin(msg.from_user.id))
async def streak_promo_get_category(message, state: FSMContext):
    """Guarda la fecha de fin y pregunta por la categoria."""
    try:
        end_date = datetime.strptime(message.text.strip(), "%d/%m/%Y %H:%M")
    except ValueError:
        await message.answer(
            "⚠️ Formato invalido. Use <code>DD/MM/AAAA HH:MM</code>.", parse_mode="HTML"
        )
        return

    await state.update_data(end_date=end_date)
    await state.set_state(StreakPromotionStates.waiting_category)

    with get_service(TriviaCategoryService) as tcs:
        categories = tcs.discover_categories()

    buttons = [
        [
            InlineKeyboardButton(
                text="\U0001f3b0 Mazo general",
                callback_data=TriviaStreakCategoryCallback(category="none").pack(),
            )
        ]
    ]
    for cat in categories:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{cat['display_name']} ({cat['question_count']} preguntas)",
                    callback_data=TriviaStreakCategoryCallback(
                        category=str(cat["category_id"])
                    ).pack(),
                )
            ]
        )

    await message.answer(
        "\U0001f539 <b>Paso 5/6:</b> Seleccione la categoria asociada:\n\n"
        "<i>Si selecciona un mazo especifico, la promocion solo "
        "aplicara cuando se juegue esa categoria.</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "streak_promo_dur_relative", lambda cb: is_admin(cb.from_user.id))
async def streak_promo_duration_relative_wait(callback: CallbackQuery, state: FSMContext):
    """Pide las horas de duracion relativa."""
    await state.update_data(duration_mode="relative")
    await state.set_state(StreakPromotionStates.waiting_duration_hours)
    await callback.message.edit_text(
        "\U0001f539 <b>Duracion en horas:</b>\n\n"
        "Ingrese la cantidad de horas que durara la promocion:\n\n"
        "<i>Ejemplo: <code>72</code> para 3 dias</i>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(
    StreakPromotionStates.waiting_duration_hours, lambda msg: is_admin(msg.from_user.id)
)
async def streak_promo_duration_hours_got(message, state: FSMContext):
    """Guarda las horas de duracion y pasa a seleccion de categoria."""
    try:
        hours = int(message.text.strip())
        if hours <= 0:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ Ingrese un numero valido de horas positivo.", parse_mode="HTML")
        return

    await state.update_data(duration_hours=hours, start_date=None, end_date=None)
    await state.set_state(StreakPromotionStates.waiting_category)

    with get_service(TriviaCategoryService) as tcs:
        categories = tcs.discover_categories()

    buttons = [
        [
            InlineKeyboardButton(
                text="\U0001f3b0 Mazo general",
                callback_data=TriviaStreakCategoryCallback(category="none").pack(),
            )
        ]
    ]
    for cat in categories:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{cat['display_name']} ({cat['question_count']} preguntas)",
                    callback_data=TriviaStreakCategoryCallback(
                        category=str(cat["category_id"])
                    ).pack(),
                )
            ]
        )

    await message.answer(
        "\U0001f539 <b>Paso 5/6:</b> Seleccione la categoria asociada:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML",
    )


@router.callback_query(TriviaStreakCategoryCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def streak_promo_choose_game_types(
    callback: CallbackQuery, callback_data: TriviaStreakCategoryCallback, state: FSMContext
):
    """Guarda la categoria y pregunta por tipos de juego."""
    category_id = None if callback_data.category == "none" else callback_data.category

    await state.update_data(category_id=category_id)
    await state.set_state(StreakPromotionStates.waiting_game_types)

    buttons = [
        [
            InlineKeyboardButton(
                text="✅ General (trivia clasica)",
                callback_data=TriviaStreakGoalTypeCallback(goal_type="general").pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="✅ Simple (trivia especial)",
                callback_data=TriviaStreakGoalTypeCallback(goal_type="simple").pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ VIP (trivia exclusiva)",
                callback_data=TriviaStreakGoalTypeCallback(goal_type="vip").pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="\U0001f6d1 Continuar",
                callback_data=TriviaStreakGoalTypeCallback(goal_type="done").pack(),
            )
        ],
    ]
    await callback.message.edit_text(
        "\U0001f539 <b>Paso 6/6:</b> Seleccione los tipos de juego:\n\n"
        "<i>Los tipos seleccionados activaran la promocion. "
        "Toque cada uno para alternar. Presione Continuar al finalizar.</i>\n\n"
        "Seleccion actual: General + Simple",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML",
    )
    await callback.answer()


def _build_game_type_selection_keyboard(gt_flag: dict) -> InlineKeyboardMarkup:
    """Construye el teclado de seleccion de tipos de juego."""
    labels = []
    if gt_flag.get("general"):
        labels.append("General")
    if gt_flag.get("simple"):
        labels.append("Simple")
    if gt_flag.get("vip"):
        labels.append("VIP")
    " + ".join(labels) if labels else "Ninguno"
    buttons = [
        [
            InlineKeyboardButton(
                text=f"{'✅' if gt_flag['general'] else '❌'} General (trivia clasica)",
                callback_data=TriviaStreakGoalTypeCallback(goal_type="general").pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text=f"{'✅' if gt_flag['simple'] else '❌'} Simple (trivia especial)",
                callback_data=TriviaStreakGoalTypeCallback(goal_type="simple").pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text=f"{'✅' if gt_flag['vip'] else '❌'} VIP (trivia exclusiva)",
                callback_data=TriviaStreakGoalTypeCallback(goal_type="vip").pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="\U0001f6d1 Continuar",
                callback_data=TriviaStreakGoalTypeCallback(goal_type="done").pack(),
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(TriviaStreakGoalTypeCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def streak_promo_toggle_game_type(
    callback: CallbackQuery, callback_data: TriviaStreakGoalTypeCallback, state: FSMContext
):
    """Alterna la seleccion de tipos de juego."""
    data = await state.get_data()
    gt_flag = data.get("game_types", {"general": True, "vip": False, "simple": True})
    flag = callback_data.goal_type

    if flag == "done":
        if not any(gt_flag.values()):
            await callback.answer("Seleccione al menos un tipo de juego.", show_alert=True)
            return
        await state.update_data(game_types=gt_flag)
        await state.set_state(StreakPromotionStates.waiting_confirmation)
        summary_text = streak_promo_build_summary(data, gt_flag)
        confirm_buttons = [
            [
                InlineKeyboardButton(
                    text="✅ Confirmar y crear", callback_data="streak_promo_confirm"
                )
            ],
            [
                InlineKeyboardButton(
                    text="\U0001f504 Reiniciar", callback_data="streak_promo_create"
                )
            ],
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_streak_promotions")],
        ]
        await callback.message.edit_text(
            summary_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=confirm_buttons),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    toggles = {"general": "general", "vip": "vip", "simple": "simple"}
    if flag in toggles:
        gt_flag[toggles[flag]] = not gt_flag[toggles[flag]]
        await state.update_data(game_types=gt_flag)

    labels = [k.capitalize() for k in ["general", "simple", "vip"] if gt_flag.get(k)]
    selection = " + ".join(labels) if labels else "Ninguno"
    await callback.message.edit_text(
        f"\U0001f539 <b>Paso 6/6:</b> Seleccione los tipos de juego:\n\n"
        f"Seleccion actual: <b>{selection}</b>",
        reply_markup=_build_game_type_selection_keyboard(gt_flag),
        parse_mode="HTML",
    )
    await callback.answer()


def _build_success_message(name: str, level_count: int) -> str:
    """Construye el mensaje de exito tras crear una promocion."""
    return (
        f"✅ <b>Promocion creada exitosamente!</b>\n\n"
        f"<b>{name}</b> con {level_count} nivel(es) "
        f"ha sido forjada.\n\n"
        f"<i>Lucien ha registrado esta promocion en su archivo personal. "
        f"Los visitantes mas devotos comenzaran a recibir codigos "
        f"cuando alcancen las rachas establecidas.</i>"
    )


def streak_promo_build_summary(data: dict, game_types: dict) -> str:
    """Construye el resumen de la promocion para confirmacion."""
    lines = ["\U0001f3c6 <b>Resumen de la promocion</b>\n"]
    lines.append(f"<b>Nombre:</b> {data.get('name', '?')}")
    lines.append(f"<b>Descripcion:</b> {data.get('description', '?')}")
    lines.append("")
    levels = data.get("levels", [])
    lines.append(f"<b>Niveles ({len(levels)}):</b>")
    for i, lv in enumerate(levels, 1):
        lines.append(
            f"  {i}. {lv['consecutive_required']} aciertos seguidos "
            f"-> {lv['discount_pct']}% desc. ({lv['codes_available']} codigos)"
        )
    lines.append("")
    mode = data.get("duration_mode", "?")
    if mode == "dates":
        start = data.get("start_date")
        end = data.get("end_date")
        lines.append("<b>Duracion:</b> Fechas concretas")
        if start:
            lines.append(f"  Inicio: {start.strftime('%d/%m/%Y %H:%M')}")
        if end:
            lines.append(f"  Fin: {end.strftime('%d/%m/%Y %H:%M')}")
    else:
        hours = data.get("duration_hours", "?")
        lines.append(f"<b>Duracion:</b> {hours} horas")

    cat = data.get("category_id")
    lines.append(f"<b>Categoria:</b> {cat if cat else 'Mazo general'}")
    labels = []
    if game_types.get("general"):
        labels.append("General")
    if game_types.get("simple"):
        labels.append("Simple")
    if game_types.get("vip"):
        labels.append("VIP")
    lines.append(f"<b>Tipos de juego:</b> {' + '.join(labels)}")
    lines.append("")
    lines.append("<i>Lucien forjara esta promocion si confirma.</i>")
    return "\n".join(lines)


@router.callback_query(F.data == "streak_promo_confirm", lambda cb: is_admin(cb.from_user.id))
async def streak_promo_confirm_create(callback: CallbackQuery, state: FSMContext):
    """Confirma y crea la promocion mediante StreakPromotionService."""
    data = await state.get_data()
    levels = data.get("levels", [])
    gt = data.get("game_types", {"general": True, "vip": False, "simple": True})

    with get_service(StreakPromotionService) as service:
        promotion = service.create_promotion(
            name=data["name"],
            description=data["description"],
            levels=levels,
            duration_mode=data.get("duration_mode", "dates"),
            start_date=data.get("start_date"),
            end_date=data.get("end_date"),
            duration_hours=data.get("duration_hours"),
            category_id=data.get("category_id"),
            include_general=gt.get("general", True),
            include_vip=gt.get("vip", False),
            include_simple=gt.get("simple", True),
            created_by=callback.from_user.id,
        )
        scheduler = get_scheduler()
        if scheduler:
            scheduler.schedule_streak_promotion(
                promo_id=promotion.id,
                start_date=data.get("start_date"),
                end_date=data.get("end_date"),
            )

    await state.clear()
    await callback.message.edit_text(
        _build_success_message(promotion.name, len(levels)),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="\U0001f3c6 Ver promociones", callback_data="admin_streak_promotions"
                    )
                ],
            ]
        ),
        parse_mode="HTML",
    )
    await callback.answer()
    logger.info(
        f"trivia_streak_admin_handlers - streak_promo_confirm_create - "
        f"{callback.from_user.id} - promo_id:{promotion.id} - name:{promotion.name}"
    )


# ==================== VIEW PROMOTION ====================


@router.callback_query(TriviaStreakDetailCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def streak_promo_view(callback: CallbackQuery, callback_data: TriviaStreakDetailCallback):
    """Muestra los detalles de una promocion."""
    promo_id = callback_data.promo_id
    with get_service(StreakPromotionService) as service:
        promo = service.get_promotion(promo_id)
        if not promo:
            await callback.answer("Promocion no encontrada.", show_alert=True)
            return

    await callback.message.edit_text(
        _build_promotion_detail_text(promo),
        reply_markup=streak_promotion_action_keyboard(promo_id),
        parse_mode="HTML",
    )
    await callback.answer()


def _build_promotion_detail_text(promo) -> str:
    """Construye el texto de detalle de una promocion."""
    status_icons = {
        "active": "\U0001f7e2",
        "paused": "\U0001f534",
        "pending": "\U000023f3",
        "expired": "⚪",
    }
    status_text = promo.status.value if hasattr(promo.status, "value") else str(promo.status)
    icon = status_icons.get(status_text, "⚪")

    lines = [
        f"<b>{promo.name}</b>\n",
        f"{icon} <b>Estado:</b> {status_text.capitalize()}\n",
        f"<i>{promo.description}</i>\n",
    ]
    lines.append(f"\n<b>Duracion:</b> {promo.duration_mode}")
    if promo.start_date:
        lines.append(f"  Inicio: {promo.start_date.strftime('%d/%m/%Y %H:%M')}")
    if promo.end_date:
        lines.append(f"  Fin: {promo.end_date.strftime('%d/%m/%Y %H:%M')}")
    if promo.duration_hours:
        lines.append(f"  Horas: {promo.duration_hours}")

    lines.append(
        f"\n<b>Categoria:</b> {promo.category_id if promo.category_id else 'Mazo general'}"
    )
    game_types = [
        t
        for t, attr in [
            ("General", promo.include_general),
            ("Simple", promo.include_simple),
            ("VIP", promo.include_vip),
        ]
        if attr
    ]
    lines.append(f"<b>Tipos:</b> {' + '.join(game_types)}")
    lines.append("\n<b>Niveles:</b>")
    for level in promo.levels:
        delivered = sum(
            1 for c in level.codes if getattr(c.status, "value", str(c.status)) == "delivered"
        )
        lines.append(
            f"  • {level.consecutive_required} aciertos -> {level.discount_pct}% desc. "
            f"({delivered}/{level.codes_available} codigos)"
        )
    return "\n".join(lines)


# ==================== PAUSE / ACTIVATE ====================


@router.callback_query(TriviaStreakToggleCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def streak_promo_toggle(callback: CallbackQuery, callback_data: TriviaStreakToggleCallback):
    """Alterna entre pausar y activar una promocion."""
    promo_id = callback_data.promo_id
    with get_service(StreakPromotionService) as service:
        promo = service.get_promotion(promo_id)
        if not promo:
            await callback.answer("Promocion no encontrada.", show_alert=True)
            return

        if promo.is_active:
            service.pause_promotion(promo_id)
            await callback.answer("\U000023f8️ Promocion pausada.", show_alert=True)
        else:
            service.activate(promo_id)
            await callback.answer("✅ Promocion activada.", show_alert=True)

    await streak_promo_view(callback, TriviaStreakDetailCallback(promo_id=promo_id))
    logger.info(
        f"trivia_streak_admin_handlers - streak_promo_toggle - "
        f"{callback.from_user.id} - promo_id:{promo_id}"
    )


# ==================== DELETE ====================


@router.callback_query(TriviaStreakDeleteCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def streak_promo_delete_confirm(
    callback: CallbackQuery, callback_data: TriviaStreakDeleteCallback
):
    """Pide confirmacion antes de eliminar una promocion."""
    promo_id = callback_data.promo_id
    buttons = [
        [
            InlineKeyboardButton(
                text="✅ Si, eliminar permanentemente",
                callback_data=TriviaStreakConfirmDeleteCallback(promo_id=promo_id).pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ No, conservar",
                callback_data=TriviaStreakDetailCallback(promo_id=promo_id).pack(),
            )
        ],
    ]
    await callback.message.edit_text(
        "⚠️ <b>Eliminar promocion?</b>\n\n"
        "<i>Esta accion es irreversible. Todos los niveles, codigos "
        "y canjes asociados seran eliminados permanentemente.</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(
    TriviaStreakConfirmDeleteCallback.filter(), lambda cb: is_admin(cb.from_user.id)
)
async def streak_promo_delete_execute(
    callback: CallbackQuery, callback_data: TriviaStreakConfirmDeleteCallback
):
    """Ejecuta la eliminacion de la promocion."""
    promo_id = callback_data.promo_id
    with get_service(StreakPromotionService) as service:
        success = service.delete_promotion(promo_id)

    if success:
        await callback.message.edit_text(
            "✅ <b>Promocion eliminada.</b>\n\n"
            "<i>Lucien ha eliminado la promocion de su archivo personal.</i>",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="\U0001f3c6 Ver promociones",
                            callback_data="admin_streak_promotions",
                        )
                    ],
                ]
            ),
            parse_mode="HTML",
        )
        await callback.answer("Promocion eliminada.", show_alert=True)
        logger.info(
            f"trivia_streak_admin_handlers - streak_promo_delete_execute - "
            f"{callback.from_user.id} - promo_id:{promo_id} - deleted"
        )
    else:
        await callback.answer("Error al eliminar la promocion.", show_alert=True)


# ==================== VIEW REDEMPTIONS ====================


@router.callback_query(
    TriviaStreakRedemptionsCallback.filter(), lambda cb: is_admin(cb.from_user.id)
)
async def streak_promo_redemptions(
    callback: CallbackQuery, callback_data: TriviaStreakRedemptionsCallback
):
    """Muestra los canjes realizados para una promocion."""
    promo_id = callback_data.promo_id
    with get_service(StreakPromotionService) as service:
        stats = service.get_redemption_stats(promo_id)

    if not stats or not stats.get("levels"):
        await callback.answer("No hay datos de canjes.", show_alert=True)
        return

    lines = ["\U0001f4cb <b>Canjes de la promocion</b>\n"]
    for level in stats["levels"]:
        lines.append(
            f"\n<b>{level['consecutive_required']} aciertos - {level['discount_pct']}% desc.</b>\n"
            f"  Codigos: {level['delivered_count']}/{level['total_codes']} entregados "
            f"({level['remaining']} restantes)"
        )
        for redemption in level["redemptions"]:
            uid = redemption["user_id"]
            date_str = redemption["redeemed_at"][:10] if redemption.get("redeemed_at") else "?"
            lines.append(f"  • Usuario {uid} - {date_str}")

    await callback.message.edit_text(
        "\n".join(lines) if len(lines) > 1 else "Sin canjes registrados.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="\U0001f519 Volver",
                        callback_data=TriviaStreakDetailCallback(promo_id=promo_id).pack(),
                    )
                ],
            ]
        ),
        parse_mode="HTML",
    )
    await callback.answer()
