"""
Handlers de Narrativa para Usuarios - Lucien Bot

Experiencia de historia interactiva, cuestionario de arquetipos y progreso.
Con la voz caracteristica de Lucien.
"""

import html
import logging

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from keyboards.callback_data import (
    ContinueStoryCallback,
    QuizAnswerCallback,
    StoryChoiceCallback,
)
from models.models import NodeType
from services import get_service
from services.story_service import StoryService
from utils.admin import is_admin

logger = logging.getLogger(__name__)
router = Router()


# Estados para FSM
class ArchetypeQuizStates(StatesGroup):
    answering = State()


async def _clear_quiz_state(state: FSMContext) -> None:
    """Limpia FSM del cuestionario al abandonar o completar."""
    await state.clear()


# ==================== MENU PRINCIPAL ====================


@router.callback_query(F.data == "narrative", lambda cb: not is_admin(cb.from_user.id))
async def narrative_menu(callback: CallbackQuery, state: FSMContext):
    """Menu principal de narrativa - Voz de Lucien"""
    await _clear_quiz_state(state)
    with get_service(StoryService) as story_service:
        user_id = callback.from_user.id

        has_started = story_service.has_started_story(user_id)
        user_archetype = story_service.get_user_archetype(user_id)

        buttons = []

        if not has_started:
            buttons.append(
                [InlineKeyboardButton(text="🎭 Comenzar la historia", callback_data="start_story")]
            )
        else:
            buttons.append(
                [
                    InlineKeyboardButton(
                        text="📖 Continuar la historia", callback_data="continue_story"
                    )
                ]
            )

        if user_archetype:
            buttons.append(
                [InlineKeyboardButton(text="🎭 Mi arquetipo", callback_data="view_my_archetype")]
            )
        else:
            buttons.append(
                [
                    InlineKeyboardButton(
                        text="🎭 Descubrir mi arquetipo", callback_data="discover_archetype"
                    )
                ]
            )

        buttons.append(
            [InlineKeyboardButton(text="🏆 Mis logros", callback_data="my_story_achievements")]
        )
        buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="back_to_main")])

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        if not has_started:
            text = (
                "🎩 <b>Lucien:</b>\n\n"
                "<i>Ah... los Fragmentos de la Historia.</i>\n\n"
                "Diana ha tejido una narrativa que se adapta a quien la experimenta. "
                "Cada decision que tome, cada camino que elija... "
                "todo revelara facetas de su propia naturaleza.\n\n"
                "<i>Al final del viaje, descubrira que arquetipo lo define...</i>\n\n"
                "🌸 <b>Los Fragmentos le esperan.</b>"
            )
        else:
            progress = story_service.get_user_progress(user_id)
            chapter = progress.current_chapter if progress else 1
            archetype_text = (
                f"\n🎭 Su arquetipo: <b>{html.escape(user_archetype.value.title())}</b>"
                if user_archetype
                else ""
            )

            text = (
                f"🎩 <b>Lucien:</b>\n\n"
                f"<i>Bienvenido de vuelta a los Fragmentos...</i>\n\n"
                f"Esta en el <b>Capitulo {chapter}</b> de la historia de Diana.{archetype_text}\n\n"
                f"<i>La narrativa continua, y usted con ella...</i>"
            )

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        await callback.answer()
        logger.info(
            f"story_user_handlers | narrative_menu | user_id={user_id} | result=ok"
        )


# ==================== INICIAR HISTORIA ====================


def _build_node_denial_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 Volver", callback_data="narrative")]]
    )


def _build_story_node_text(node, story_service: StoryService) -> str:
    chapter_text = f"📖 <b>Capitulo {node.chapter}</b>\n\n" if node.chapter else ""
    text = "🎩 <b>Lucien:</b>\n\n"
    text += chapter_text
    text += f"✨ <b>{html.escape(node.title)}</b>\n\n"
    text += f"{node.content}\n\n"
    if node.cost_besitos > 0:
        text += f"<i>Acceder a este fragmento cuesta {node.cost_besitos} besitos...</i>\n\n"
    return text


def _build_story_node_keyboard(
    node, choices, story_service: StoryService
) -> InlineKeyboardMarkup:
    buttons = []
    if node.node_type == NodeType.ENDING:
        buttons.append(
            [InlineKeyboardButton(text="🎭 Ver mi arquetipo", callback_data="view_my_archetype")]
        )
    elif node.node_type == NodeType.QUIZ:
        buttons.append(
            [InlineKeyboardButton(text="🎭 Iniciar cuestionario", callback_data="discover_archetype")]
        )
    elif choices:
        for choice in choices:
            btn_text = choice.text
            if choice.additional_cost > 0:
                btn_text += f" ({choice.additional_cost} 💋)"
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=btn_text,
                        callback_data=StoryChoiceCallback(choice_id=choice.id).pack(),
                    )
                ]
            )
    else:
        next_node_id = story_service.resolve_next_narrative_node(node.id)
        if next_node_id:
            buttons.append(
                [
                    InlineKeyboardButton(
                        text="Continuar...",
                        callback_data=ContinueStoryCallback(node_id=next_node_id).pack(),
                    )
                ]
            )
    buttons.append([InlineKeyboardButton(text="🔙 Menu de Fragmentos", callback_data="narrative")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(F.data == "start_story", lambda cb: not is_admin(cb.from_user.id))
async def start_story(callback: CallbackQuery):
    """Inicia la historia para el usuario - Voz de Lucien"""
    with get_service(StoryService) as story_service:
        user_id = callback.from_user.id

        # Verificar si ya tiene progreso
        if story_service.has_started_story(user_id):
            await continue_story(callback)
            return

        # Obtener nodo inicial
        starting_node = story_service.get_starting_node()

        if not starting_node:
            # Crear progreso sin nodo inicial
            story_service.create_user_progress(user_id)

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🎭 Descubrir mi arquetipo", callback_data="discover_archetype"
                        )
                    ],
                    [InlineKeyboardButton(text="🔙 Volver", callback_data="narrative")],
                ]
            )

            text = (
                "🎩 <b>Lucien:</b>\n\n"
                "<i>Los Fragmentos aun estan siendo tejidos por Diana...</i>\n\n"
                "Mientras tanto, puede descubrir su arquetipo para cuando la historia este lista."
            )

            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
            await callback.answer()
            return

        success, message, _ = story_service.advance_to_node(user_id, starting_node.id)
        if not success:
            await callback.answer(message, show_alert=True)
            logger.info(
                f"story_user_handlers | start_story | user_id={user_id} | result=denied"
            )
            return

        logger.info(f"story_user_handlers | start_story | user_id={user_id} | result=ok")
        await show_node(callback, starting_node.id, story_service)


@router.callback_query(F.data == "continue_story", lambda cb: not is_admin(cb.from_user.id))
async def continue_story(callback: CallbackQuery, state: FSMContext):
    """Continua la historia del usuario - Voz de Lucien"""
    await _clear_quiz_state(state)
    with get_service(StoryService) as story_service:
        user_id = callback.from_user.id

        progress = story_service.get_user_progress(user_id)

        if not progress or not progress.current_node_id:
            # Si no hay nodo actual, ir al inicio
            await start_story(callback)
            return

        logger.info(
            f"story_user_handlers | continue_story | user_id={user_id} | "
            f"node_id={progress.current_node_id} | result=ok"
        )
        await show_node(callback, progress.current_node_id, story_service)


async def show_node(callback: CallbackQuery, node_id: int, story_service: StoryService):
    """Muestra un nodo de historia al usuario - Voz de Lucien."""
    await _render_node(callback, node_id, story_service)


async def _render_node(callback: CallbackQuery, node_id: int, story_service: StoryService):
    user_id = callback.from_user.id
    node = story_service.get_node(node_id)
    if not node:
        text = "🎩 <b>Lucien:</b>\n\n<i>Ese fragmento parece haberse desvanecido...</i>"
        await callback.message.edit_text(
            text, reply_markup=_build_node_denial_keyboard(), parse_mode=ParseMode.HTML
        )
        await callback.answer()
        return

    can_access, reason = story_service.can_access_node(user_id, node_id)
    if not can_access:
        safe_reason = html.escape(reason) if reason else ""
        text = f"🎩 <b>Lucien:</b>\n\n<i>{safe_reason}</i>"
        await callback.message.edit_text(
            text, reply_markup=_build_node_denial_keyboard(), parse_mode=ParseMode.HTML
        )
        await callback.answer()
        return

    text = _build_story_node_text(node, story_service)
    if node.node_type == NodeType.ENDING:
        text += "<i>~ Fin del camino ~</i>\n\n"

    choices = story_service.get_node_choices(node_id)
    keyboard = _build_story_node_keyboard(node, choices, story_service)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await callback.answer()
    logger.info(
        f"story_user_handlers | show_node | user_id={user_id} | "
        f"node_id={node_id} | result=ok"
    )


@router.callback_query(ContinueStoryCallback.filter(), lambda cb: not is_admin(cb.from_user.id))
async def go_to_node(callback: CallbackQuery, callback_data: ContinueStoryCallback):
    """Navega al siguiente fragmento lineal via advance_to_node."""
    user_id = callback.from_user.id
    node_id = callback_data.node_id

    with get_service(StoryService) as story_service:
        valid, reason = story_service.validate_continue_transition(user_id, node_id)
        if not valid:
            await callback.answer(reason, show_alert=True)
            logger.info(
                f"story_user_handlers | go_to_node | user_id={user_id} | result=invalid_transition"
            )
            return

        success, message, _ = story_service.advance_to_node(user_id, node_id)
        if not success:
            await callback.answer(message, show_alert=True)
            logger.info(f"story_user_handlers | go_to_node | user_id={user_id} | result=denied")
            return

        logger.info(f"story_user_handlers | go_to_node | user_id={user_id} | node_id={node_id} | result=ok")
        await show_node(callback, node_id, story_service)


@router.callback_query(StoryChoiceCallback.filter(), lambda cb: not is_admin(cb.from_user.id))
async def make_choice(callback: CallbackQuery, callback_data: StoryChoiceCallback):
    """Procesa la eleccion del usuario"""
    choice_id = callback_data.choice_id

    with get_service(StoryService) as story_service:
        user_id = callback.from_user.id

        choice = story_service.get_choice(choice_id)
        if not choice:
            await callback.answer("Esa opcion ya no esta disponible", show_alert=True)
            return

        target_node_id = choice.next_node_id if choice.next_node_id else choice.node_id
        success, message, _ = story_service.advance_to_node(
            user_id=user_id,
            node_id=target_node_id,
            choice_id=choice_id,
        )

        if not success:
            await callback.answer(message, show_alert=True)
            logger.info(
                f"story_user_handlers | make_choice | user_id={user_id} | "
                f"choice_id={choice_id} | result=denied"
            )
            return

        logger.info(
            f"story_user_handlers | make_choice | user_id={user_id} | "
            f"choice_id={choice_id} | result=ok"
        )

        if choice.next_node_id:
            await show_node(callback, choice.next_node_id, story_service)
        else:
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🎭 Ver mi arquetipo", callback_data="view_my_archetype"
                        )
                    ],
                    [InlineKeyboardButton(text="🔙 Volver", callback_data="narrative")],
                ]
            )
            text = (
                "🎩 <b>Lucien:</b>\n\n"
                "<i>Ha llegado al final de este camino...</i>\n\n"
                "Pero la historia de Diana tiene muchos senderos. "
                "Descubra su arquetipo para desbloquear nuevos fragmentos."
            )
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
            await callback.answer()


# ==================== CUESTIONARIO DE ARQUETIPO ====================


@router.callback_query(F.data == "discover_archetype", lambda cb: not is_admin(cb.from_user.id))
async def start_archetype_quiz(callback: CallbackQuery, state: FSMContext):
    """Inicia el cuestionario de arquetipo - Voz de Lucien"""
    with get_service(StoryService) as story_service:
        user_id = callback.from_user.id
        if story_service.get_user_archetype(user_id):
            await callback.answer(
                "Su arquetipo ya esta asignado y no puede recalcularse.",
                show_alert=True,
            )
            return

        story_service.get_archetype_quiz_questions()

        await state.update_data(quiz_answers=[], current_question=0)
        await state.set_state(ArchetypeQuizStates.answering)

        logger.info(
            f"story_user_handlers | start_archetype_quiz | user_id={user_id} | result=ok"
        )
        await show_quiz_question(callback, state, story_service)


async def show_quiz_question(
    callback: CallbackQuery, state: FSMContext, story_service: StoryService
):
    """Muestra una pregunta del cuestionario - Voz de Lucien."""
    data = await state.get_data()

    questions = story_service.get_archetype_quiz_questions()
    current = data.get("current_question", 0)

    if current >= len(questions):
        await calculate_and_show_archetype(callback, state, story_service)
        return

    question = questions[current]

    text = (
        f"🎩 <b>Lucien:</b>\n\n"
        f"<i>Permitame conocerle mejor...</i>\n\n"
        f"<b>Pregunta {current + 1} de {len(questions)}</b>\n\n"
        f"{question['question']}"
    )

    buttons = []
    for i, option in enumerate(question["options"]):
        buttons.append(
            [
                InlineKeyboardButton(
                    text=option["text"], callback_data=QuizAnswerCallback(answer_idx=i).pack()
                )
            ]
        )

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await callback.answer()


@router.callback_query(
    ArchetypeQuizStates.answering,
    QuizAnswerCallback.filter(),
    lambda cb: not is_admin(cb.from_user.id),
)
async def process_quiz_answer(
    callback: CallbackQuery, state: FSMContext, callback_data: QuizAnswerCallback
):
    """Procesa la respuesta del cuestionario"""
    answer_idx = callback_data.answer_idx
    user_id = callback.from_user.id

    with get_service(StoryService) as story_service:
        data = await state.get_data()
        current = data.get("current_question", 0)
        questions = story_service.get_archetype_quiz_questions()

        if current >= len(questions):
            await callback.answer("El cuestionario ya finalizo", show_alert=True)
            return

        question = questions[current]
        if answer_idx < 0 or answer_idx >= len(question["options"]):
            await callback.answer("Opcion no valida", show_alert=True)
            return

        answers = data.get("quiz_answers", [])
        answers.append(answer_idx)
        await state.update_data(quiz_answers=answers, current_question=current + 1)

        logger.info(
            f"story_user_handlers | process_quiz_answer | user_id={user_id} | "
            f"question={current} | result=ok"
        )
        await show_quiz_question(callback, state, story_service)


async def calculate_and_show_archetype(
    callback: CallbackQuery, state: FSMContext, story_service: StoryService
):
    """Calcula y muestra el arquetipo del usuario - Voz de Lucien."""
    user_id = callback.from_user.id

    data = await state.get_data()
    answers = data.get("quiz_answers", [])

    archetype_type = story_service.calculate_archetype_from_quiz(answers)

    if story_service.has_started_story(user_id):
        progress = story_service.get_user_progress(user_id)
    else:
        progress = story_service.create_user_progress(user_id)

    story_service.apply_quiz_scores_to_progress(progress, answers)
    story_service.assign_archetype_to_user(user_id, archetype_type)

    archetype_desc = story_service.get_archetype_description(archetype_type)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📖 Continuar la historia", callback_data="continue_story"
                )
            ],
            [InlineKeyboardButton(text="🔙 Menu de Fragmentos", callback_data="narrative")],
        ]
    )

    text = (
        f"🎩 <b>Lucien:</b>\n\n"
        f"<i>Interesante... las respuestas revelan su naturaleza.</i>\n\n"
        f"🎭 <b>Su arquetipo es: {html.escape(archetype_type.value.title())}</b>\n\n"
        f"{html.escape(archetype_desc)}\n\n"
        f"<i>Esto determinara que fragmentos de la historia de Diana "
        f"estaran disponibles para usted...</i>"
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await _clear_quiz_state(state)
    await callback.answer()
    logger.info(
        f"story_user_handlers | calculate_archetype | user_id={user_id} | "
        f"archetype={archetype_type.value} | result=ok"
    )


# ==================== VER ARQUETIPO ====================


@router.callback_query(F.data == "view_my_archetype", lambda cb: not is_admin(cb.from_user.id))
async def view_my_archetype(callback: CallbackQuery):
    """Muestra el arquetipo del usuario - Voz de Lucien"""
    with get_service(StoryService) as story_service:
        user_id = callback.from_user.id

        archetype_type = story_service.get_user_archetype(user_id)

        if not archetype_type:
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🎭 Descubrir mi arquetipo", callback_data="discover_archetype"
                        )
                    ],
                    [InlineKeyboardButton(text="🔙 Volver", callback_data="narrative")],
                ]
            )

            text = (
                "🎩 <b>Lucien:</b>\n\n"
                "<i>Aun no ha despertado su arquetipo...</i>\n\n"
                "Responda algunas preguntas y descubra que facetas de su "
                "personalidad resuenan con la historia de Diana."
            )

            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
            await callback.answer()
            return

        # Obtener descripcion
        archetype_desc = story_service.get_archetype_description(archetype_type)

        visited_count = story_service.get_visited_node_count(user_id)

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📖 Continuar la historia", callback_data="continue_story"
                    )
                ],
                [InlineKeyboardButton(text="🔙 Volver", callback_data="narrative")],
            ]
        )

        text = (
            f"🎩 <b>Lucien:</b>\n\n"
            f"🎭 <b>Su arquetipo: {html.escape(archetype_type.value.title())}</b>\n\n"
            f"{html.escape(archetype_desc)}\n\n"
            f"📊 <b>Progreso:</b>\n"
            f"   Fragmentos descubiertos: {visited_count}\n\n"
            f"<i>Su arquetipo determina que caminos de la historia estan "
            f"abiertos para usted. Pero recuerde... siempre puede evolucionar.</i>"
        )

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        await callback.answer()
        logger.info(
            f"story_user_handlers | view_my_archetype | user_id={user_id} | result=ok"
        )


# ==================== LOGROS ====================


@router.callback_query(F.data == "my_story_achievements", lambda cb: not is_admin(cb.from_user.id))
async def my_story_achievements(callback: CallbackQuery):
    """Muestra los logros del usuario - Voz de Lucien"""
    with get_service(StoryService) as story_service:
        user_id = callback.from_user.id

        achievements = story_service.get_user_achievements(user_id)

        if not achievements:
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="📖 Explorar Fragmentos", callback_data="continue_story"
                        )
                    ],
                    [InlineKeyboardButton(text="🔙 Volver", callback_data="narrative")],
                ]
            )

            text = (
                "🎩 <b>Lucien:</b>\n\n"
                "<i>Aun no ha desbloqueado ningun reconocimiento...</i>\n\n"
                "Avance en la historia de Diana y descubra los secretos "
                "que le otorgaran estos honores."
            )

            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
            await callback.answer()
            logger.info(
                f"story_user_handlers | my_story_achievements | user_id={user_id} | "
                f"count=0 | result=ok"
            )
            return

        text = "🎩 <b>Lucien:</b>\n\n"
        text += "<i>Sus reconocimientos en los Fragmentos:</i>\n\n"

        for ua in achievements:
            achievement = ua.achievement
            text += f"🏆 <b>{html.escape(achievement.name)}</b>\n"
            text += f"   <i>{html.escape(achievement.description)}</i>\n"
            text += f"   Desbloqueado: {ua.unlocked_at.strftime('%d/%m/%Y')}\n\n"

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📖 Continuar explorando", callback_data="continue_story"
                    )
                ],
                [InlineKeyboardButton(text="🔙 Volver", callback_data="narrative")],
            ]
        )

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        await callback.answer()
        logger.info(
            f"story_user_handlers | my_story_achievements | user_id={user_id} | "
            f"count={len(achievements)} | result=ok"
        )
