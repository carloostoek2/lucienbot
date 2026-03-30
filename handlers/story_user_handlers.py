"""
Handlers de Narrativa para Usuarios - Lucien Bot

Experiencia de historia interactiva, cuestionario de arquetipos y progreso.
Con la voz caracteristica de Lucien.
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from services.story_service import StoryService
from services.vip_service import VIPService
from models.models import NodeType, ArchetypeType
import json
import logging

logger = logging.getLogger(__name__)
router = Router()


# Estados para FSM
class ArchetypeQuizStates(StatesGroup):
    answering = State()


# ==================== MENU PRINCIPAL ====================

@router.callback_query(F.data == "narrative")
async def narrative_menu(callback: CallbackQuery):
    """Menu principal de narrativa - Voz de Lucien"""
    story_service = StoryService()
    user_id = callback.from_user.id

    has_started = story_service.has_started_story(user_id)
    user_archetype = story_service.get_user_archetype(user_id)

    buttons = []

    if not has_started:
        buttons.append([InlineKeyboardButton(
            text="🎭 Comenzar la historia",
            callback_data="start_story"
        )])
    else:
        buttons.append([InlineKeyboardButton(
            text="📖 Continuar la historia",
            callback_data="continue_story"
        )])

    if user_archetype:
        buttons.append([InlineKeyboardButton(
            text="🎭 Mi arquetipo",
            callback_data="view_my_archetype"
        )])
    else:
        buttons.append([InlineKeyboardButton(
            text="🎭 Descubrir mi arquetipo",
            callback_data="discover_archetype"
        )])

    buttons.append([InlineKeyboardButton(
        text="🏆 Mis logros",
        callback_data="my_story_achievements"
    )])
    buttons.append([InlineKeyboardButton(
        text="🔙 Volver",
        callback_data="back_to_main"
    )])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    if not has_started:
        text = ("🎩 <b>Lucien:</b>\n\n"
                "<i>Ah... los Fragmentos de la Historia.</i>\n\n"
                "Diana ha tejido una narrativa que se adapta a quien la experimenta. "
                "Cada decision que tome, cada camino que elija... "
                "todo revelara facetas de su propia naturaleza.\n\n"
                "<i>Al final del viaje, descubrira que arquetipo lo define...</i>\n\n"
                "🌸 <b>Los Fragmentos le esperan.</b>")
    else:
        progress = story_service.get_user_progress(user_id)
        chapter = progress.current_chapter if progress else 1
        archetype_text = f"\n🎭 Su arquetipo: <b>{user_archetype.value.title()}</b>" if user_archetype else ""

        text = (f"🎩 <b>Lucien:</b>\n\n"
                f"<i>Bienvenido de vuelta a los Fragmentos...</i>\n\n"
                f"Esta en el <b>Capitulo {chapter}</b> de la historia de Diana.{archetype_text}\n\n"
                f"<i>La narrativa continua, y usted con ella...</i>")

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await callback.answer()


# ==================== INICIAR HISTORIA ====================

@router.callback_query(F.data == "start_story")
async def start_story(callback: CallbackQuery):
    """Inicia la historia para el usuario - Voz de Lucien"""
    story_service = StoryService()
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

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎭 Descubrir mi arquetipo", callback_data="discover_archetype")],
            [InlineKeyboardButton(text="🔙 Volver", callback_data="narrative")]
        ])

        text = ("🎩 <b>Lucien:</b>\n\n"
                "<i>Los Fragmentos aun estan siendo tejidos por Diana...</i>\n\n"
                "Mientras tanto, puede descubrir su arquetipo para cuando la historia este lista.")

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        await callback.answer()
        return

    # Crear progreso con nodo inicial
    story_service.create_user_progress(user_id, starting_node.id)

    # Mostrar nodo inicial
    await show_node(callback, starting_node.id)


@router.callback_query(F.data == "continue_story")
async def continue_story(callback: CallbackQuery):
    """Continua la historia del usuario - Voz de Lucien"""
    story_service = StoryService()
    user_id = callback.from_user.id

    progress = story_service.get_user_progress(user_id)

    if not progress or not progress.current_node_id:
        # Si no hay nodo actual, ir al inicio
        await start_story(callback)
        return

    await show_node(callback, progress.current_node_id)


async def show_node(callback: CallbackQuery, node_id: int):
    """Muestra un nodo de historia al usuario - Voz de Lucien"""
    story_service = StoryService()
    vip_service = VIPService()
    user_id = callback.from_user.id

    node = story_service.get_node(node_id)
    if not node:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Volver", callback_data="narrative")]
        ])
        text = ("🎩 <b>Lucien:</b>\n\n"
                "<i>Ese fragmento parece haberse desvanecido...</i>")
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        await callback.answer()
        return

    # Verificar acceso
    is_vip = vip_service.is_user_vip(user_id)
    can_access, reason = story_service.can_access_node(user_id, node_id, is_vip)

    if not can_access:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Volver", callback_data="narrative")]
        ])
        text = f"🎩 <b>Lucien:</b>\n\n<i>{reason}</i>"
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        await callback.answer()
        return

    # Construir el mensaje
    chapter_text = f"📖 <b>Capitulo {node.chapter}</b>\n\n" if node.chapter else ""

    text = f"🎩 <b>Lucien:</b>\n\n"
    text += chapter_text
    text += f"✨ <b>{node.title}</b>\n\n"
    text += f"{node.content}\n\n"

    # Si tiene costo, mostrarlo
    if node.cost_besitos > 0:
        text += f"<i>Acceder a este fragmento cuesta {node.cost_besitos} besitos...</i>\n\n"

    # Obtener opciones
    choices = story_service.get_node_choices(node_id)

    buttons = []

    if node.node_type == NodeType.ENDING:
        text += "<i>~ Fin del camino ~</i>\n\n"
        buttons.append([InlineKeyboardButton(
            text="🎭 Ver mi arquetipo",
            callback_data="view_my_archetype"
        )])
    elif choices:
        for choice in choices:
            btn_text = choice.text
            if choice.additional_cost > 0:
                btn_text += f" ({choice.additional_cost} 💋)"
            buttons.append([InlineKeyboardButton(
                text=btn_text,
                callback_data=f"story_choice_{choice.id}"
            )])
    else:
        # Nodo narrativo sin opciones - boton para continuar
        next_nodes = story_service.get_nodes_by_chapter(node.chapter)
        current_idx = next((i for i, n in enumerate(next_nodes) if n.id == node_id), -1)

        if current_idx >= 0 and current_idx + 1 < len(next_nodes):
            next_node = next_nodes[current_idx + 1]
            buttons.append([InlineKeyboardButton(
                text="Continuar...",
                callback_data=f"story_node_{next_node.id}"
            )])

    buttons.append([InlineKeyboardButton(text="🔙 Menu de Fragmentos", callback_data="narrative")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await callback.answer()


@router.callback_query(F.data.startswith("story_node_"))
async def go_to_node(callback: CallbackQuery):
    """Navega a un nodo especifico"""
    try:
        node_id = int(callback.data.replace("story_node_", ""))
    except ValueError:
        await callback.answer("Fragmento no valido", show_alert=True)
        return

    await show_node(callback, node_id)


@router.callback_query(F.data.startswith("story_choice_"))
async def make_choice(callback: CallbackQuery):
    """Procesa la eleccion del usuario"""
    try:
        choice_id = int(callback.data.replace("story_choice_", ""))
    except ValueError:
        await callback.answer("Opcion no valida", show_alert=True)
        return

    story_service = StoryService()
    vip_service = VIPService()
    user_id = callback.from_user.id

    choice = story_service.get_choice(choice_id)
    if not choice:
        await callback.answer("Esa opcion ya no esta disponible", show_alert=True)
        return

    is_vip = vip_service.is_user_vip(user_id)

    # Avanzar al siguiente nodo
    if choice.next_node_id:
        success, message, progress = story_service.advance_to_node(
            user_id=user_id,
            node_id=choice.next_node_id,
            choice_id=choice_id,
            is_vip=is_vip
        )

        if not success:
            await callback.answer(message, show_alert=True)
            return

        await show_node(callback, choice.next_node_id)
    else:
        # Fin de la historia
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎭 Ver mi arquetipo", callback_data="view_my_archetype")],
            [InlineKeyboardButton(text="🔙 Volver", callback_data="narrative")]
        ])

        text = ("🎩 <b>Lucien:</b>\n\n"
                "<i>Ha llegado al final de este camino...</i>\n\n"
                "Pero la historia de Diana tiene muchos senderos. "
                "Descubra su arquetipo para desbloquear nuevos fragmentos.")

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        await callback.answer()


# ==================== CUESTIONARIO DE ARQUETIPO ====================

@router.callback_query(F.data == "discover_archetype")
async def start_archetype_quiz(callback: CallbackQuery, state: FSMContext):
    """Inicia el cuestionario de arquetipo - Voz de Lucien"""
    story_service = StoryService()

    questions = story_service.get_archetype_quiz_questions()

    await state.update_data(
        quiz_answers=[],
        current_question=0
    )

    await show_quiz_question(callback, state)


async def show_quiz_question(callback: CallbackQuery, state: FSMContext):
    """Muestra una pregunta del cuestionario - Voz de Lucien"""
    story_service = StoryService()
    data = await state.get_data()

    questions = story_service.get_archetype_quiz_questions()
    current = data.get('current_question', 0)

    if current >= len(questions):
        # Calcular arquetipo
        await calculate_and_show_archetype(callback, state)
        return

    question = questions[current]

    text = (f"🎩 <b>Lucien:</b>\n\n"
            f"<i>Permitame conocerle mejor...</i>\n\n"
            f"<b>Pregunta {current + 1} de {len(questions)}</b>\n\n"
            f"{question['question']}")

    buttons = []
    for i, option in enumerate(question['options']):
        buttons.append([InlineKeyboardButton(
            text=option['text'],
            callback_data=f"quiz_answer_{i}"
        )])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await callback.answer()


@router.callback_query(F.data.startswith("quiz_answer_"))
async def process_quiz_answer(callback: CallbackQuery, state: FSMContext):
    """Procesa la respuesta del cuestionario"""
    try:
        answer_idx = int(callback.data.replace("quiz_answer_", ""))
    except ValueError:
        await callback.answer("Respuesta no valida", show_alert=True)
        return

    data = await state.get_data()
    answers = data.get('quiz_answers', [])
    current = data.get('current_question', 0)

    answers.append(answer_idx)
    await state.update_data(
        quiz_answers=answers,
        current_question=current + 1
    )

    await show_quiz_question(callback, state)


async def calculate_and_show_archetype(callback: CallbackQuery, state: FSMContext):
    """Calcula y muestra el arquetipo del usuario - Voz de Lucien"""
    story_service = StoryService()
    user_id = callback.from_user.id

    data = await state.get_data()
    answers = data.get('quiz_answers', [])

    # Calcular arquetipo
    archetype_type = story_service.calculate_archetype_from_quiz(answers)

    # Asignar al usuario
    if story_service.has_started_story(user_id):
        story_service.assign_archetype_to_user(user_id, archetype_type)
    else:
        # Crear progreso con el arquetipo
        progress = story_service.create_user_progress(user_id)
        story_service.assign_archetype_to_user(user_id, archetype_type)

    # Obtener descripcion del arquetipo
    archetype_desc = story_service.get_archetype_description(archetype_type)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 Continuar la historia", callback_data="continue_story")],
        [InlineKeyboardButton(text="🔙 Menu de Fragmentos", callback_data="narrative")]
    ])

    text = (f"🎩 <b>Lucien:</b>\n\n"
            f"<i>Interesante... las respuestas revelan su naturaleza.</i>\n\n"
            f"🎭 <b>Su arquetipo es: {archetype_type.value.title()}</b>\n\n"
            f"{archetype_desc}\n\n"
            f"<i>Esto determinara que fragmentos de la historia de Diana "
            f"estaran disponibles para usted...</i>")

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.clear()
    await callback.answer()


# ==================== VER ARQUETIPO ====================

@router.callback_query(F.data == "view_my_archetype")
async def view_my_archetype(callback: CallbackQuery):
    """Muestra el arquetipo del usuario - Voz de Lucien"""
    story_service = StoryService()
    user_id = callback.from_user.id

    archetype_type = story_service.get_user_archetype(user_id)

    if not archetype_type:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎭 Descubrir mi arquetipo", callback_data="discover_archetype")],
            [InlineKeyboardButton(text="🔙 Volver", callback_data="narrative")]
        ])

        text = ("🎩 <b>Lucien:</b>\n\n"
                "<i>Aun no ha despertado su arquetipo...</i>\n\n"
                "Responda algunas preguntas y descubra que facetas de su "
                "personalidad resuenan con la historia de Diana.")

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        await callback.answer()
        return

    # Obtener descripcion
    archetype_desc = story_service.get_archetype_description(archetype_type)

    # Obtener progreso
    progress = story_service.get_user_progress(user_id)
    visited_count = len(json.loads(progress.visited_nodes)) if progress else 0

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 Continuar la historia", callback_data="continue_story")],
        [InlineKeyboardButton(text="🎭 Recalcular arquetipo", callback_data="discover_archetype")],
        [InlineKeyboardButton(text="🔙 Volver", callback_data="narrative")]
    ])

    text = (f"🎩 <b>Lucien:</b>\n\n"
            f"🎭 <b>Su arquetipo: {archetype_type.value.title()}</b>\n\n"
            f"{archetype_desc}\n\n"
            f"📊 <b>Progreso:</b>\n"
            f"   Fragmentos descubiertos: {visited_count}\n\n"
            f"<i>Su arquetipo determina que caminos de la historia estan "
            f"abiertos para usted. Pero recuerde... siempre puede evolucionar.</i>")

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await callback.answer()


# ==================== LOGROS ====================

@router.callback_query(F.data == "my_story_achievements")
async def my_story_achievements(callback: CallbackQuery):
    """Muestra los logros del usuario - Voz de Lucien"""
    story_service = StoryService()
    user_id = callback.from_user.id

    achievements = story_service.get_user_achievements(user_id)

    if not achievements:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📖 Explorar Fragmentos", callback_data="continue_story")],
            [InlineKeyboardButton(text="🔙 Volver", callback_data="narrative")]
        ])

        text = ("🎩 <b>Lucien:</b>\n\n"
                "<i>Aun no ha desbloqueado ningun reconocimiento...</i>\n\n"
                "Avance en la historia de Diana y descubra los secretos "
                "que le otorgaran estos honores.")

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        await callback.answer()
        return

    text = "🎩 <b>Lucien:</b>\n\n"
    text += "<i>Sus reconocimientos en los Fragmentos:</i>\n\n"

    for ua in achievements:
        achievement = ua.achievement
        text += f"🏆 <b>{achievement.name}</b>\n"
        text += f"   <i>{achievement.description}</i>\n"
        text += f"   Desbloqueado: {ua.unlocked_at.strftime('%d/%m/%Y')}\n\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 Continuar explorando", callback_data="continue_story")],
        [InlineKeyboardButton(text="🔙 Volver", callback_data="narrative")]
    ])

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await callback.answer()
