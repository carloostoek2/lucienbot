"""
Handlers de Narrativa para Administradores - Lucien Bot

Gestion de nodos de historia, arquetipos, logros y estadisticas.
Con la voz caracteristica de Lucien.
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode

from config.settings import bot_config
from services.story_service import StoryService
from models.models import NodeType, ArchetypeType
from utils.helpers import is_admin
import logging

logger = logging.getLogger(__name__)
router = Router()


# Estados para FSM
class NodeWizardStates(StatesGroup):
    waiting_title = State()
    waiting_content = State()
    selecting_type = State()
    waiting_chapter = State()
    waiting_requirements = State()
    waiting_cost = State()
    confirming = State()


class ChoiceWizardStates(StatesGroup):
    selecting_node = State()
    waiting_text = State()
    selecting_next_node = State()
    waiting_archetype_points = State()
    confirming = State()


class ArchetypeWizardStates(StatesGroup):
    selecting_type = State()
    waiting_name = State()
    waiting_description = State()
    waiting_welcome = State()
    confirming = State()


class AchievementWizardStates(StatesGroup):
    waiting_name = State()
    waiting_description = State()
    waiting_icon = State()
    confirming = State()


# ==================== MENU PRINCIPAL ====================

@router.callback_query(F.data == "admin_narrative", lambda cb: is_admin(cb.from_user.id))
async def admin_narrative_menu(callback: CallbackQuery):
    """Menu de administracion de narrativa - Voz de Lucien"""
    story_service = StoryService()
    stats = story_service.get_story_stats()

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Forjar fragmento", callback_data="create_node")],
        [InlineKeyboardButton(text="📋 Ver fragmentos", callback_data="list_nodes")],
        [InlineKeyboardButton(text="🔗 Gestionar opciones", callback_data="manage_choices")],
        [InlineKeyboardButton(text="🎭 Gestionar arquetipos", callback_data="manage_archetypes")],
        [InlineKeyboardButton(text="🏆 Gestionar logros", callback_data="manage_achievements")],
        [InlineKeyboardButton(text="📊 Observar el pulso", callback_data="story_stats")],
        [InlineKeyboardButton(text="🔙 Volver al sanctum", callback_data="admin_gamification")]
    ])

    text = (f"🎩 <b>Lucien:</b>\n\n"
            f"<i>Ah... los Hilos de la Historia de Diana.</i>\n\n"
            f"Aqui es donde se teje la narrativa que los visitantes experimentaran. "
            f"Cada fragmento, cada decision, cada arquetipo... todo se orquesta desde aqui.\n\n"
            f"📊 <b>El estado de los Fragmentos:</b>\n"
            f"   • Fragmentos activos: {stats['total_nodes']}\n"
            f"   • Capitulos: {stats['total_chapters']}\n"
            f"   • Visitantes en la historia: {stats['total_users']}\n"
            f"   • Han completado: {stats['completed_users']}\n"
            f"   • Logros disponibles: {stats['total_achievements']}\n\n"
            f"<i>Que aspecto de la narrativa requiere su atencion?</i>")

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await callback.answer()


# ==================== CREAR NODO ====================

@router.callback_query(F.data == "create_node", lambda cb: is_admin(cb.from_user.id))
async def create_node_start(callback: CallbackQuery, state: FSMContext):
    """Inicia wizard de creacion de nodo - Voz de Lucien"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_narrative")]
    ])

    text = ("🎩 <b>Lucien:</b>\n\n"
            "<i>Vamos a forjar un nuevo fragmento de la historia...</i>\n\n"
            "<b>Paso 1:</b> El titulo del fragmento\n\n"
            "Indique un titulo evocador:\n"
            "<i>Ejemplo: El Primer Encuentro</i>")

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(NodeWizardStates.waiting_title)
    await callback.answer()


@router.message(NodeWizardStates.waiting_title)
async def process_node_title(message: Message, state: FSMContext):
    """Procesa titulo del nodo - Voz de Lucien"""
    title = message.text.strip()
    if len(title) < 3:
        await message.answer("El titulo debe tener al menos 3 caracteres.")
        return

    await state.update_data(title=title)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_narrative")]
    ])

    text = ("🎩 <b>Lucien:</b>\n\n"
            "<b>Paso 2:</b> El contenido del fragmento\n\n"
            "Escriba el texto que Diana compartira en este momento:\n\n"
            "<i>Puede usar HTML para formato: &lt;b&gt;negrita&lt;/b&gt;, &lt;i&gt;cursiva&lt;/i&gt;, etc.</i>")

    await message.answer(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(NodeWizardStates.waiting_content)


@router.message(NodeWizardStates.waiting_content)
async def process_node_content(message: Message, state: FSMContext):
    """Procesa contenido del nodo - Voz de Lucien"""
    content = message.text.strip()
    if len(content) < 10:
        await message.answer("El contenido debe tener al menos 10 caracteres.")
        return

    await state.update_data(content=content)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 Narrativo", callback_data="node_type_narrative")],
        [InlineKeyboardButton(text="🎭 Decision", callback_data="node_type_decision")],
        [InlineKeyboardButton(text="🏁 Final", callback_data="node_type_ending")],
        [InlineKeyboardButton(text="❓ Cuestionario", callback_data="node_type_quiz")],
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_narrative")]
    ])

    text = ("🎩 <b>Lucien:</b>\n\n"
            "<b>Paso 3:</b> Tipo de fragmento\n\n"
            "Seleccione que tipo de momento es este:")

    await message.answer(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(NodeWizardStates.selecting_type)


@router.callback_query(NodeWizardStates.selecting_type, F.data.startswith("node_type_"))
async def select_node_type(callback: CallbackQuery, state: FSMContext):
    """Selecciona tipo de nodo - Voz de Lucien"""
    type_map = {
        "node_type_narrative": NodeType.NARRATIVE,
        "node_type_decision": NodeType.DECISION,
        "node_type_ending": NodeType.ENDING,
        "node_type_quiz": NodeType.QUIZ
    }

    node_type = type_map.get(callback.data)
    if not node_type:
        await callback.answer("Tipo no valido", show_alert=True)
        return

    await state.update_data(node_type=node_type)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_narrative")]
    ])

    text = ("🎩 <b>Lucien:</b>\n\n"
            "<b>Paso 4:</b> Capitulo\n\n"
            "Indique a que capitulo pertenece este fragmento (numero):\n"
            "<i>Ejemplo: 1</i>")

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(NodeWizardStates.waiting_chapter)
    await callback.answer()


@router.message(NodeWizardStates.waiting_chapter)
async def process_node_chapter(message: Message, state: FSMContext):
    """Procesa capitulo del nodo - Voz de Lucien"""
    try:
        chapter = int(message.text.strip())
        if chapter < 1:
            raise ValueError("Debe ser mayor a 0")
    except ValueError:
        await message.answer("Por favor indique un numero valido mayor a 0.")
        return

    await state.update_data(chapter=chapter)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌸 Cualquiera", callback_data="req_archetype_none")],
        [InlineKeyboardButton(text="🎭 El Seductor", callback_data="req_archetype_seductor")],
        [InlineKeyboardButton(text="👁️ El Observador", callback_data="req_archetype_observer")],
        [InlineKeyboardButton(text="💎 El Devoto", callback_data="req_archetype_devoto")],
        [InlineKeyboardButton(text="🗺️ El Explorador", callback_data="req_archetype_explorador")],
        [InlineKeyboardButton(text="🌑 El Misterioso", callback_data="req_archetype_misterioso")],
        [InlineKeyboardButton(text="🔥 El Intrepido", callback_data="req_archetype_intrepido")],
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_narrative")]
    ])

    text = ("🎩 <b>Lucien:</b>\n\n"
            "<b>Paso 5:</b> Requisitos de arquetipo\n\n"
            "Este fragmento esta disponible para todos, "
            "o solo para quienes han despertado un arquetipo especifico?")

    await message.answer(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(NodeWizardStates.waiting_requirements)


@router.callback_query(NodeWizardStates.waiting_requirements, F.data.startswith("req_archetype_"))
async def select_archetype_requirement(callback: CallbackQuery, state: FSMContext):
    """Selecciona requisito de arquetipo - Voz de Lucien"""
    archetype_map = {
        "req_archetype_none": None,
        "req_archetype_seductor": ArchetypeType.SEDUCTOR,
        "req_archetype_observer": ArchetypeType.OBSERVER,
        "req_archetype_devoto": ArchetypeType.DEVOTO,
        "req_archetype_explorador": ArchetypeType.EXPLORADOR,
        "req_archetype_misterioso": ArchetypeType.MISTERIOSO,
        "req_archetype_intrepido": ArchetypeType.INTREPIDO
    }

    required_archetype = archetype_map.get(callback.data)
    await state.update_data(required_archetype=required_archetype)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💋 Sin costo", callback_data="node_cost_0")],
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_narrative")]
    ])

    text = ("🎩 <b>Lucien:</b>\n\n"
            "<b>Paso 6:</b> Costo en besitos\n\n"
            "Indique cuantos besitos cuesta acceder a este fragmento:\n"
            "<i>Ejemplo: 50 (o 0 para gratuito)</i>")

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(NodeWizardStates.waiting_cost)
    await callback.answer()


@router.callback_query(NodeWizardStates.waiting_cost, F.data == "node_cost_0")
async def node_cost_zero(callback: CallbackQuery, state: FSMContext):
    """Costo cero - Voz de Lucien"""
    await state.update_data(cost_besitos=0)
    await show_node_confirmation(callback, state)


@router.message(NodeWizardStates.waiting_cost)
async def process_node_cost(message: Message, state: FSMContext):
    """Procesa costo del nodo - Voz de Lucien"""
    try:
        cost = int(message.text.strip())
        if cost < 0:
            raise ValueError("Debe ser 0 o mayor")
    except ValueError:
        await message.answer("Por favor indique un numero valido (0 o mayor).")
        return

    await state.update_data(cost_besitos=cost)
    await show_node_confirmation(message, state)


async def show_node_confirmation(target, state: FSMContext):
    """Muestra confirmacion del nodo - Voz de Lucien"""
    data = await state.get_data()

    title = data.get('title', '')
    content = data.get('content', '')[:100] + '...' if len(data.get('content', '')) > 100 else data.get('content', '')
    node_type = data.get('node_type', NodeType.NARRATIVE)
    chapter = data.get('chapter', 1)
    required_archetype = data.get('required_archetype')
    cost_besitos = data.get('cost_besitos', 0)

    archetype_text = "Cualquiera" if not required_archetype else required_archetype.value.title()

    text = (f"🎩 <b>Lucien:</b>\n\n"
            f"<i>Permitame confirmar el fragmento...</i>\n\n"
            f"📖 <b>{title}</b>\n"
            f"Tipo: {node_type.value.title()}\n"
            f"Capitulo: {chapter}\n"
            f"Arquetipo requerido: {archetype_text}\n"
            f"Costo: {cost_besitos} besitos\n\n"
            f"Contenido:\n<i>{content}</i>\n\n"
            f"<i>Desea forjar este fragmento?</i>")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Forjar fragmento", callback_data="confirm_create_node")],
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_narrative")]
    ])

    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    else:
        await target.answer(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)

    await state.set_state(NodeWizardStates.confirming)


@router.callback_query(NodeWizardStates.confirming, F.data == "confirm_create_node")
async def confirm_create_node(callback: CallbackQuery, state: FSMContext):
    """Crea el nodo - Voz de Lucien"""
    data = await state.get_data()
    story_service = StoryService()

    try:
        node = story_service.create_node(
            title=data.get('title'),
            content=data.get('content'),
            node_type=data.get('node_type'),
            chapter=data.get('chapter', 1),
            required_archetype=data.get('required_archetype'),
            cost_besitos=data.get('cost_besitos', 0),
            created_by=callback.from_user.id
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Agregar opciones", callback_data=f"add_choices_{node.id}")],
            [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_narrative")]
        ])

        text = (f"🎩 <b>Lucien:</b>\n\n"
                f"<i>Excelente. El fragmento ha sido forjado...</i>\n\n"
                f"📖 <b>{node.title}</b>\n\n"
                f"<i>Ahora puede agregar opciones de decision si es necesario.</i>")

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        logger.info(f"Fragmento creado: {node.title} por custodio {callback.from_user.id}")

    except Exception as e:
        logger.error(f"Error forjando fragmento: {e}")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_narrative")]
        ])
        text = ("🎩 <b>Lucien:</b>\n\n"
                "<i>Hmm... algo inesperado ha ocurrido.</i>\n\n"
                "Permitame consultar con Diana sobre este inconveniente.")
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)

    await state.clear()
    await callback.answer()


# ==================== LISTAR NODOS ====================

@router.callback_query(F.data == "list_nodes", lambda cb: is_admin(cb.from_user.id))
async def list_nodes(callback: CallbackQuery):
    """Lista todos los nodos - Voz de Lucien"""
    story_service = StoryService()
    nodes = story_service.get_all_nodes()

    if not nodes:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Forjar fragmento", callback_data="create_node")],
            [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_narrative")]
        ])
        text = ("🎩 <b>Lucien:</b>\n\n"
                "<i>Los Fragmentos aun estan vacios...</i>\n\n"
                "Comience forjando el primer fragmento de la historia.")
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        await callback.answer()
        return

    text = "🎩 <b>Lucien:</b>\n\n"
    text += "<i>Los fragmentos de la historia:</i>\n\n"

    buttons = []
    current_chapter = 0

    for node in nodes:
        if node.chapter != current_chapter:
            current_chapter = node.chapter
            text += f"\n📚 <b>Capitulo {current_chapter}</b>\n"

        status = "✅" if node.is_active else "❌"
        node_type_emoji = {
            NodeType.NARRATIVE: "📖",
            NodeType.DECISION: "🎭",
            NodeType.ENDING: "🏁",
            NodeType.QUIZ: "❓"
        }.get(node.node_type, "📄")

        text += f"{status} {node_type_emoji} {node.title[:30]}\n"

        buttons.append([InlineKeyboardButton(
            text=f"{status} {node.title[:35]}",
            callback_data=f"node_detail_{node.id}"
        )])

    buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="admin_narrative")])

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode=ParseMode.HTML)
    await callback.answer()


# ==================== ESTADISTICAS ====================

@router.callback_query(F.data == "story_stats", lambda cb: is_admin(cb.from_user.id))
async def story_stats(callback: CallbackQuery):
    """Muestra estadisticas de la narrativa - Voz de Lucien"""
    story_service = StoryService()
    stats = story_service.get_story_stats()

    # Distribucion de arquetipos
    archetype_text = ""
    for archetype, count in stats['archetype_distribution'].items():
        if count > 0:
            archetype_text += f"   • {archetype.title()}: {count}\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_narrative")]
    ])

    text = (f"🎩 <b>Lucien:</b>\n\n"
            f"📊 <b>El pulso de los Fragmentos:</b>\n\n"
            f"📖 <b>Fragmentos:</b>\n"
            f"   • Activos: {stats['total_nodes']}\n"
            f"   • Capitulos: {stats['total_chapters']}\n\n"
            f"👥 <b>Visitantes:</b>\n"
            f"   • En la historia: {stats['total_users']}\n"
            f"   • Han completado: {stats['completed_users']}\n\n"
            f"🎭 <b>Distribucion de arquetipos:</b>\n"
            f"{archetype_text}\n"
            f"🏆 <b>Logros disponibles:</b> {stats['total_achievements']}")

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await callback.answer()


# ==================== GESTIONAR ARQUETIPOS ====================

@router.callback_query(F.data == "manage_archetypes", lambda cb: is_admin(cb.from_user.id))
async def manage_archetypes(callback: CallbackQuery):
    """Menu de gestion de arquetipos - Voz de Lucien"""
    story_service = StoryService()
    archetypes = story_service.get_all_archetypes()

    buttons = []

    # Mostrar arquetipos existentes
    for archetype in archetypes:
        buttons.append([InlineKeyboardButton(
            text=f"🎭 {archetype.name}",
            callback_data=f"archetype_detail_{archetype.archetype_type.value}"
        )])

    # Opcion para crear nuevo
    buttons.append([InlineKeyboardButton(
        text="➕ Definir nuevo arquetipo",
        callback_data="create_archetype"
    )])
    buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="admin_narrative")])

    text = ("🎩 <b>Lucien:</b>\n\n"
            "<i>Los arquetipos que Diana ha definido...</i>\n\n"
            "Cada uno representa una faceta de quienes experimentan los Fragmentos.")

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode=ParseMode.HTML)
    await callback.answer()


# ==================== GESTIONAR LOGROS ====================

@router.callback_query(F.data == "manage_achievements", lambda cb: is_admin(cb.from_user.id))
async def manage_achievements(callback: CallbackQuery):
    """Menu de gestion de logros - Voz de Lucien"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Crear reconocimiento", callback_data="create_achievement")],
        [InlineKeyboardButton(text="📋 Ver reconocimientos", callback_data="list_achievements")],
        [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_narrative")]
    ])

    text = ("🎩 <b>Lucien:</b>\n\n"
            "<i>Los reconocimientos que los visitantes pueden obtener...</i>\n\n"
            "Cada logro es un hito en su viaje por los Fragmentos de Diana.")

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await callback.answer()


# ==================== GESTIONAR OPCIONES ====================

@router.callback_query(F.data == "manage_choices", lambda cb: is_admin(cb.from_user.id))
async def manage_choices(callback: CallbackQuery):
    """Menu de gestion de opciones - Voz de Lucien"""
    story_service = StoryService()
    nodes = story_service.get_all_nodes()

    # Solo nodos de decision
    decision_nodes = [n for n in nodes if n.node_type == NodeType.DECISION]

    if not decision_nodes:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Forjar fragmento de decision", callback_data="create_node")],
            [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_narrative")]
        ])
        text = ("🎩 <b>Lucien:</b>\n\n"
                "<i>No hay fragmentos de decision...</i>\n\n"
                "Cree un fragmento de tipo 'Decision' primero.")
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        await callback.answer()
        return

    buttons = []
    for node in decision_nodes:
        buttons.append([InlineKeyboardButton(
            text=f"🎭 {node.title[:35]}",
            callback_data=f"add_choices_{node.id}"
        )])

    buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="admin_narrative")])

    text = ("🎩 <b>Lucien:</b>\n\n"
            "<i>Seleccione el fragmento al que desea agregar opciones:</i>")

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode=ParseMode.HTML)
    await callback.answer()


# ==================== VER DETALLE DE NODO ====================

@router.callback_query(F.data.startswith("node_detail_"), lambda cb: is_admin(cb.from_user.id))
async def node_detail(callback: CallbackQuery):
    """Muestra detalle de un nodo - Voz de Lucien"""
    try:
        node_id = int(callback.data.replace("node_detail_", ""))
    except ValueError:
        await callback.answer("ID invalido", show_alert=True)
        return

    story_service = StoryService()
    node = story_service.get_node(node_id)

    if not node:
        await callback.answer("Fragmento no encontrado", show_alert=True)
        return

    # Obtener opciones del nodo
    choices = story_service.get_node_choices(node_id)

    status = "✅ Activo" if node.is_active else "❌ Inactivo"
    node_type_emoji = {
        NodeType.NARRATIVE: "📖",
        NodeType.DECISION: "🎭",
        NodeType.ENDING: "🏁",
        NodeType.QUIZ: "❓"
    }.get(node.node_type, "📄")

    archetype_text = "Cualquiera" if not node.required_archetype else node.required_archetype.value.title()

    text = (f"🎩 <b>Lucien:</b>\n\n"
            f"{node_type_emoji} <b>{node.title}</b>\n\n"
            f"📖 <b>Contenido:</b>\n<i>{node.content[:200]}{'...' if len(node.content) > 200 else ''}</i>\n\n"
            f"📊 <b>Detalles:</b>\n"
            f"   Tipo: {node.node_type.value.title()}\n"
            f"   Capitulo: {node.chapter}\n"
            f"   Estado: {status}\n"
            f"   Arquetipo requerido: {archetype_text}\n"
            f"   Costo: {node.cost_besitos} besitos\n"
            f"   Opciones: {len(choices)}\n\n"
            f"<i>Que desea hacer con este fragmento?</i>")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    # Boton para agregar opciones si es de decision
    if node.node_type == NodeType.DECISION:
        keyboard.inline_keyboard.append([InlineKeyboardButton(
            text="➕ Agregar opcion",
            callback_data=f"add_choices_{node.id}"
        )])

    keyboard.inline_keyboard.extend([
        [InlineKeyboardButton(
            text=f"{'Desactivar' if node.is_active else 'Activar'}",
            callback_data=f"toggle_node_{node.id}"
        )],
        [InlineKeyboardButton(
            text="🗑️ Eliminar",
            callback_data=f"delete_node_{node.id}"
        )],
        [InlineKeyboardButton(text="🔙 Volver", callback_data="list_nodes")]
    ])

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await callback.answer()


@router.callback_query(F.data.startswith("toggle_node_"), lambda cb: is_admin(cb.from_user.id))
async def toggle_node(callback: CallbackQuery):
    """Activa/desactiva un nodo - Voz de Lucien"""
    try:
        node_id = int(callback.data.replace("toggle_node_", ""))
    except ValueError:
        await callback.answer("ID invalido", show_alert=True)
        return

    story_service = StoryService()
    node = story_service.get_node(node_id)

    if not node:
        await callback.answer("Fragmento no encontrado", show_alert=True)
        return

    story_service.update_node(node_id, is_active=not node.is_active)

    status = "activado" if not node.is_active else "desactivado"
    await callback.answer(f"Fragmento {status}")
    await node_detail(callback)


@router.callback_query(F.data.startswith("delete_node_"), lambda cb: is_admin(cb.from_user.id))
async def delete_node_confirm(callback: CallbackQuery):
    """Confirma eliminacion de nodo - Voz de Lucien"""
    try:
        node_id = int(callback.data.replace("delete_node_", ""))
    except ValueError:
        await callback.answer("ID invalido", show_alert=True)
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Si, eliminar", callback_data=f"confirm_delete_node_{node_id}")],
        [InlineKeyboardButton(text="❌ Cancelar", callback_data=f"node_detail_{node_id}")]
    ])

    text = ("🎩 <b>Lucien:</b>\n\n"
            "<i>Esta seguro de eliminar este fragmento?</i>\n\n"
            "Esta accion no se puede deshacer. "
            "Las opciones y progresos asociados tambien se perderan...")

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_node_"), lambda cb: is_admin(cb.from_user.id))
async def confirm_delete_node(callback: CallbackQuery):
    """Elimina el nodo - Voz de Lucien"""
    try:
        node_id = int(callback.data.replace("confirm_delete_node_", ""))
    except ValueError:
        await callback.answer("ID invalido", show_alert=True)
        return

    story_service = StoryService()
    success = story_service.delete_node(node_id)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Volver", callback_data="list_nodes")]
    ])

    if success:
        text = ("🎩 <b>Lucien:</b>\n\n"
                "<i>El fragmento ha sido eliminado.</i>")
    else:
        text = ("🎩 <b>Lucien:</b>\n\n"
                "<i>No se pudo eliminar el fragmento.</i>")

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await callback.answer()


# ==================== AGREGAR OPCIONES A NODO ====================

@router.callback_query(F.data.startswith("add_choices_"), lambda cb: is_admin(cb.from_user.id))
async def add_choices_start(callback: CallbackQuery, state: FSMContext):
    """Inicia wizard para agregar opcion a nodo - Voz de Lucien"""
    try:
        node_id = int(callback.data.replace("add_choices_", ""))
    except ValueError:
        await callback.answer("ID invalido", show_alert=True)
        return

    story_service = StoryService()
    node = story_service.get_node(node_id)

    if not node:
        await callback.answer("Fragmento no encontrado", show_alert=True)
        return

    await state.update_data(choice_node_id=node_id)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancelar", callback_data=f"node_detail_{node_id}")]
    ])

    text = (f"🎩 <b>Lucien:</b>\n\n"
            f"<i>Agregando opcion a: {node.title}</i>\n\n"
            f"<b>Paso 1:</b> Texto de la opcion\n\n"
            f"Escriba el texto que el visitante vera:\n"
            f"<i>Ejemplo: Aceptar la invitacion</i>")

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(ChoiceWizardStates.waiting_text)
    await callback.answer()


@router.message(ChoiceWizardStates.waiting_text)
async def process_choice_text(message: Message, state: FSMContext):
    """Procesa texto de la opcion - Voz de Lucien"""
    text = message.text.strip()
    if len(text) < 3:
        await message.answer("El texto debe tener al menos 3 caracteres.")
        return

    await state.update_data(choice_text=text)

    story_service = StoryService()
    nodes = story_service.get_all_nodes()

    buttons = []
    for node in nodes:
        buttons.append([InlineKeyboardButton(
            text=f"📖 {node.title[:35]}",
            callback_data=f"choice_next_{node.id}"
        )])

    buttons.append([InlineKeyboardButton(text="🏁 Fin de historia", callback_data="choice_next_none")])
    buttons.append([InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_narrative")])

    text_msg = ("🎩 <b>Lucien:</b>\n\n"
                "<b>Paso 2:</b> Seleccionar siguiente fragmento\n\n"
                "A que fragmento lleva esta opcion?")

    await message.answer(text_msg, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode=ParseMode.HTML)
    await state.set_state(ChoiceWizardStates.selecting_next_node)


@router.callback_query(ChoiceWizardStates.selecting_next_node, F.data.startswith("choice_next_"))
async def select_choice_next_node(callback: CallbackQuery, state: FSMContext):
    """Selecciona el siguiente nodo - Voz de Lucien"""
    next_node_id = None
    if callback.data != "choice_next_none":
        try:
            next_node_id = int(callback.data.replace("choice_next_", ""))
        except ValueError:
            await callback.answer("ID invalido", show_alert=True)
            return

    await state.update_data(choice_next_node_id=next_node_id)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌸 Ninguno", callback_data="choice_points_none")],
        [InlineKeyboardButton(text="🎭 Seductor", callback_data="choice_points_seductor")],
        [InlineKeyboardButton(text="👁️ Observador", callback_data="choice_points_observer")],
        [InlineKeyboardButton(text="💎 Devoto", callback_data="choice_points_devoto")],
        [InlineKeyboardButton(text="🗺️ Explorador", callback_data="choice_points_explorador")],
        [InlineKeyboardButton(text="🌑 Misterioso", callback_data="choice_points_misterioso")],
        [InlineKeyboardButton(text="🔥 Intrepido", callback_data="choice_points_intrepido")],
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_narrative")]
    ])

    text = ("🎩 <b>Lucien:</b>\n\n"
            "<b>Paso 3:</b> Puntos de arquetipo\n\n"
            "Esta opcion suma puntos a algun arquetipo?")

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(ChoiceWizardStates.waiting_archetype_points)
    await callback.answer()


@router.callback_query(ChoiceWizardStates.waiting_archetype_points, F.data.startswith("choice_points_"))
async def select_choice_archetype_points(callback: CallbackQuery, state: FSMContext):
    """Selecciona puntos de arquetipo - Voz de Lucien"""
    archetype_map = {
        "choice_points_none": None,
        "choice_points_seductor": ArchetypeType.SEDUCTOR,
        "choice_points_observer": ArchetypeType.OBSERVER,
        "choice_points_devoto": ArchetypeType.DEVOTO,
        "choice_points_explorador": ArchetypeType.EXPLORADOR,
        "choice_points_misterioso": ArchetypeType.MISTERIOSO,
        "choice_points_intrepido": ArchetypeType.INTREPIDO
    }

    selected_archetype = archetype_map.get(callback.data)
    await state.update_data(choice_archetype=selected_archetype)

    data = await state.get_data()
    choice_text = data.get('choice_text', '')
    next_node_id = data.get('choice_next_node_id')

    next_node_text = "Fin de historia" if not next_node_id else f"Fragmento {next_node_id}"
    archetype_text = "Ninguno" if not selected_archetype else selected_archetype.value.title()

    text = (f"🎩 <b>Lucien:</b>\n\n"
            f"<i>Confirme la opcion...</i>\n\n"
            f"🎭 <b>Texto:</b> {choice_text}\n"
            f"📖 <b>Lleva a:</b> {next_node_text}\n"
            f"🌸 <b>Arquetipo:</b> {archetype_text}\n\n"
            f"<i>Desea agregar esta opcion?</i>")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Agregar opcion", callback_data="confirm_create_choice")],
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_narrative")]
    ])

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(ChoiceWizardStates.confirming)
    await callback.answer()


@router.callback_query(ChoiceWizardStates.confirming, F.data == "confirm_create_choice")
async def confirm_create_choice(callback: CallbackQuery, state: FSMContext):
    """Crea la opcion - Voz de Lucien"""
    data = await state.get_data()
    story_service = StoryService()

    try:
        choice = story_service.create_choice(
            node_id=data.get('choice_node_id'),
            text=data.get('choice_text'),
            next_node_id=data.get('choice_next_node_id'),
            choice_archetype=data.get('choice_archetype'),
            archetype_points=data.get('choice_archetype') and 3 or 0
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Agregar otra opcion", callback_data=f"add_choices_{data.get('choice_node_id')}")],
            [InlineKeyboardButton(text="🔙 Volver", callback_data=f"node_detail_{data.get('choice_node_id')}")]
        ])

        text = ("🎩 <b>Lucien:</b>\n\n"
                "<i>La opcion ha sido agregada...</i>")

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        logger.info(f"Opcion agregada al nodo {data.get('choice_node_id')} por custodio {callback.from_user.id}")

    except Exception as e:
        logger.error(f"Error agregando opcion: {e}")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_narrative")]
        ])
        text = ("🎩 <b>Lucien:</b>\n\n"
                "<i>Hmm... algo inesperado ha ocurrido.</i>")
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)

    await state.clear()
    await callback.answer()


# ==================== CREAR ARQUETIPO ====================

@router.callback_query(F.data == "create_archetype", lambda cb: is_admin(cb.from_user.id))
async def create_archetype_start(callback: CallbackQuery, state: FSMContext):
    """Inicia wizard para crear arquetipo - Voz de Lucien"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎭 El Seductor", callback_data="new_archetype_seductor")],
        [InlineKeyboardButton(text="👁️ El Observador", callback_data="new_archetype_observer")],
        [InlineKeyboardButton(text="💎 El Devoto", callback_data="new_archetype_devoto")],
        [InlineKeyboardButton(text="🗺️ El Explorador", callback_data="new_archetype_explorador")],
        [InlineKeyboardButton(text="🌑 El Misterioso", callback_data="new_archetype_misterioso")],
        [InlineKeyboardButton(text="🔥 El Intrepido", callback_data="new_archetype_intrepido")],
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="manage_archetypes")]
    ])

    text = ("🎩 <b>Lucien:</b>\n\n"
            "<i>Que arquetipo desea definir?</i>\n\n"
            "Seleccione el tipo de arquetipo:")

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(ArchetypeWizardStates.selecting_type)
    await callback.answer()


@router.callback_query(ArchetypeWizardStates.selecting_type, F.data.startswith("new_archetype_"))
async def select_new_archetype_type(callback: CallbackQuery, state: FSMContext):
    """Selecciona tipo de arquetipo - Voz de Lucien"""
    archetype_map = {
        "new_archetype_seductor": ArchetypeType.SEDUCTOR,
        "new_archetype_observer": ArchetypeType.OBSERVER,
        "new_archetype_devoto": ArchetypeType.DEVOTO,
        "new_archetype_explorador": ArchetypeType.EXPLORADOR,
        "new_archetype_misterioso": ArchetypeType.MISTERIOSO,
        "new_archetype_intrepido": ArchetypeType.INTREPIDO
    }

    archetype_type = archetype_map.get(callback.data)
    if not archetype_type:
        await callback.answer("Tipo no valido", show_alert=True)
        return

    # Verificar si ya existe
    story_service = StoryService()
    existing = story_service.get_archetype(archetype_type)
    if existing:
        await callback.answer("Este arquetipo ya esta definido", show_alert=True)
        return

    await state.update_data(archetype_type=archetype_type)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="manage_archetypes")]
    ])

    text = (f"🎩 <b>Lucien:</b>\n\n"
            f"<b>Definiendo:</b> {archetype_type.value.title()}\n\n"
            f"<b>Paso 1:</b> Nombre del arquetipo\n\n"
            f"Indique como se llamara este arquetipo:\n"
            f"<i>Ejemplo: El Seductor</i>")

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(ArchetypeWizardStates.waiting_name)
    await callback.answer()


@router.message(ArchetypeWizardStates.waiting_name)
async def process_archetype_name(message: Message, state: FSMContext):
    """Procesa nombre del arquetipo - Voz de Lucien"""
    name = message.text.strip()
    if len(name) < 3:
        await message.answer("El nombre debe tener al menos 3 caracteres.")
        return

    await state.update_data(archetype_name=name)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="manage_archetypes")]
    ])

    text = ("🎩 <b>Lucien:</b>\n\n"
            "<b>Paso 2:</b> Descripcion\n\n"
            "Describa este arquetipo:\n"
            "<i>Ejemplo: Quien busca el placer y la conquista...</i>")

    await message.answer(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(ArchetypeWizardStates.waiting_description)


@router.message(ArchetypeWizardStates.waiting_description)
async def process_archetype_description(message: Message, state: FSMContext):
    """Procesa descripcion del arquetipo - Voz de Lucien"""
    description = message.text.strip()
    if len(description) < 10:
        await message.answer("La descripcion debe tener al menos 10 caracteres.")
        return

    await state.update_data(archetype_description=description)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 Omitir", callback_data="archetype_welcome_skip")],
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="manage_archetypes")]
    ])

    text = ("🎩 <b>Lucien:</b>\n\n"
            "<b>Paso 3:</b> Mensaje de bienvenida (opcional)\n\n"
            "Escriba el mensaje que recibira quien despierte este arquetipo:\n"
            "<i>Ejemplo: Has despertado al Seductor...</i>")

    await message.answer(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(ArchetypeWizardStates.waiting_welcome)


@router.callback_query(ArchetypeWizardStates.waiting_welcome, F.data == "archetype_welcome_skip")
async def skip_archetype_welcome(callback: CallbackQuery, state: FSMContext):
    """Omite mensaje de bienvenida - Voz de Lucien"""
    await state.update_data(archetype_welcome=None)
    await show_archetype_confirmation(callback, state)


@router.message(ArchetypeWizardStates.waiting_welcome)
async def process_archetype_welcome(message: Message, state: FSMContext):
    """Procesa mensaje de bienvenida - Voz de Lucien"""
    welcome = message.text.strip()
    await state.update_data(archetype_welcome=welcome)
    await show_archetype_confirmation(message, state)


async def show_archetype_confirmation(target, state: FSMContext):
    """Muestra confirmacion del arquetipo - Voz de Lucien"""
    data = await state.get_data()

    archetype_type = data.get('archetype_type')
    name = data.get('archetype_name')
    description = data.get('archetype_description')
    welcome = data.get('archetype_welcome', 'No especificado')

    text = (f"🎩 <b>Lucien:</b>\n\n"
            f"<i>Confirme el arquetipo...</i>\n\n"
            f"🎭 <b>{name}</b> ({archetype_type.value.title()})\n\n"
            f"📖 <b>Descripcion:</b>\n<i>{description[:100]}{'...' if len(description) > 100 else ''}</i>\n\n"
            f"💬 <b>Bienvenida:</b>\n<i>{welcome[:100] if welcome else 'No especificado'}{'...' if welcome and len(welcome) > 100 else ''}</i>\n\n"
            f"<i>Desea definir este arquetipo?</i>")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Definir arquetipo", callback_data="confirm_create_archetype")],
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="manage_archetypes")]
    ])

    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    else:
        await target.answer(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)

    await state.set_state(ArchetypeWizardStates.confirming)


@router.callback_query(ArchetypeWizardStates.confirming, F.data == "confirm_create_archetype")
async def confirm_create_archetype(callback: CallbackQuery, state: FSMContext):
    """Crea el arquetipo - Voz de Lucien"""
    data = await state.get_data()
    story_service = StoryService()

    try:
        archetype = story_service.create_archetype(
            archetype_type=data.get('archetype_type'),
            name=data.get('archetype_name'),
            description=data.get('archetype_description'),
            welcome_message=data.get('archetype_welcome'),
            created_by=callback.from_user.id
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Volver", callback_data="manage_archetypes")]
        ])

        text = (f"🎩 <b>Lucien:</b>\n\n"
                f"<i>El arquetipo ha sido definido...</i>\n\n"
                f"🎭 <b>{archetype.name}</b>")

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        logger.info(f"Arquetipo creado: {archetype.name} por custodio {callback.from_user.id}")

    except Exception as e:
        logger.error(f"Error definiendo arquetipo: {e}")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Volver", callback_data="manage_archetypes")]
        ])
        text = ("🎩 <b>Lucien:</b>\n\n"
                "<i>Hmm... algo inesperado ha ocurrido.</i>")
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)

    await state.clear()
    await callback.answer()


# ==================== VER DETALLE DE ARQUETIPO ====================

@router.callback_query(F.data.startswith("archetype_detail_"), lambda cb: is_admin(cb.from_user.id))
async def archetype_detail(callback: CallbackQuery):
    """Muestra detalle de un arquetipo - Voz de Lucien"""
    try:
        archetype_value = callback.data.replace("archetype_detail_", "")
        archetype_type = ArchetypeType(archetype_value)
    except (ValueError, KeyError):
        await callback.answer("Arquetipo no valido", show_alert=True)
        return

    story_service = StoryService()
    archetype = story_service.get_archetype(archetype_type)

    if not archetype:
        await callback.answer("Arquetipo no encontrado", show_alert=True)
        return

    text = (f"🎩 <b>Lucien:</b>\n\n"
            f"🎭 <b>{archetype.name}</b>\n"
            f"Tipo: {archetype.archetype_type.value.title()}\n\n"
            f"📖 <b>Descripcion:</b>\n<i>{archetype.description}</i>\n\n")

    if archetype.welcome_message:
        text += f"💬 <b>Mensaje de bienvenida:</b>\n<i>{archetype.welcome_message}</i>\n\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Volver", callback_data="manage_archetypes")]
    ])

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await callback.answer()


# ==================== CREAR LOGRO ====================

@router.callback_query(F.data == "create_achievement", lambda cb: is_admin(cb.from_user.id))
async def create_achievement_start(callback: CallbackQuery, state: FSMContext):
    """Inicia wizard para crear logro - Voz de Lucien"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="manage_achievements")]
    ])

    text = ("🎩 <b>Lucien:</b>\n\n"
            "<i>Vamos a crear un nuevo reconocimiento...</i>\n\n"
            "<b>Paso 1:</b> Nombre del logro\n\n"
            "Indique un nombre evocador:\n"
            "<i>Ejemplo: El Primer Paso</i>")

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(AchievementWizardStates.waiting_name)
    await callback.answer()


@router.message(AchievementWizardStates.waiting_name)
async def achievement_name_input(message: Message, state: FSMContext):
    """Recibe nombre del logro"""
    await state.update_data(achievement_name=message.text.strip())

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="manage_achievements")]
    ])

    text = ("🎩 <b>Lucien:</b>\n\n"
            "<b>Paso 2:</b> Descripcion\n\n"
            "Describa este reconocimiento:\n"
            "<i>Ejemplo: Completa tu primer fragmento de historia</i>")

    await message.answer(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(AchievementWizardStates.waiting_description)


@router.message(AchievementWizardStates.waiting_description)
async def achievement_description_input(message: Message, state: FSMContext):
    """Recibe descripcion del logro"""
    await state.update_data(achievement_description=message.text.strip())

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="manage_achievements")]
    ])

    text = ("🎩 <b>Lucien:</b>\n\n"
            "<b>Paso 3:</b> Icono\n\n"
            "Envie un emoji para este reconocimiento:\n"
            "<i>Ejemplo: 🌹</i>")

    await message.answer(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(AchievementWizardStates.waiting_icon)


@router.message(AchievementWizardStates.waiting_icon)
async def achievement_icon_input(message: Message, state: FSMContext):
    """Recibe icono y pide confirmacion"""
    icon = message.text.strip()[:10]
    await state.update_data(achievement_icon=icon)

    data = await state.get_data()
    name = data.get('achievement_name', '')
    desc = data.get('achievement_description', '')

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Crear reconocimiento", callback_data="confirm_create_achievement")],
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="manage_achievements")]
    ])

    text = (f"🎩 <b>Lucien:</b>\n\n"
            f"<i>Confirme el reconocimiento...</i>\n\n"
            f"{icon} <b>{name}</b>\n"
            f"_{desc}_")

    await message.answer(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(AchievementWizardStates.confirming)


@router.callback_query(AchievementWizardStates.confirming, F.data == "confirm_create_achievement")
async def confirm_create_achievement(callback: CallbackQuery, state: FSMContext):
    """Crea el logro"""
    data = await state.get_data()
    story_service = StoryService()

    try:
        achievement = story_service.create_achievement(
            name=data.get('achievement_name'),
            description=data.get('achievement_description'),
            icon=data.get('achievement_icon', '🏆'),
            created_by=callback.from_user.id
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Volver", callback_data="manage_achievements")]
        ])

        text = (f"🎩 <b>Lucien:</b>\n\n"
                f"<i>El reconocimiento ha sido creado...</i>\n\n"
                f"{achievement.icon} <b>{achievement.name}</b>")

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        logger.info(f"Logro creado: {achievement.name} por custodio {callback.from_user.id}")

    except Exception as e:
        logger.error(f"Error creando logro: {e}")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Volver", callback_data="manage_achievements")]
        ])
        text = ("🎩 <b>Lucien:</b>\n\n"
                "<i>Hmm... algo inesperado ha ocurrido.</i>")
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)

    await state.clear()
    await callback.answer()


# ==================== LISTAR LOGROS ====================

@router.callback_query(F.data == "list_achievements", lambda cb: is_admin(cb.from_user.id))
async def list_achievements(callback: CallbackQuery):
    """Lista todos los logros - Voz de Lucien"""
    story_service = StoryService()
    achievements = story_service.get_all_achievements()

    if achievements:
        lines = []
        for ach in achievements:
            status = "✅" if ach.is_active else "❌"
            lines.append(f"{status} {ach.icon} <b>{ach.name}</b>\n   _{ach.description[:60]}_")
        achievements_text = "\n\n".join(lines)
    else:
        achievements_text = "<i>Aun no hay reconocimientos definidos...</i>"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Crear reconocimiento", callback_data="create_achievement")],
        [InlineKeyboardButton(text="🔙 Volver", callback_data="manage_achievements")]
    ])

    text = (f"🎩 <b>Lucien:</b>\n\n"
            f"<i>Los reconocimientos disponibles...</i>\n\n"
            f"{achievements_text}")

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await callback.answer()
