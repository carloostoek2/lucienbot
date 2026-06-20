"""
Handlers de Narrativa para Administradores - Lucien Bot

Gestion de nodos de historia, arquetipos, logros y estadisticas.
Con la voz caracteristica de Lucien.
"""

import html
import logging
import math

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from keyboards.callback_data import (
    ArchetypeDetailCallback,
    StoryAchievementNodeCallback,
    StoryAddChoicesCallback,
    StoryArchetypeEditCallback,
    StoryArchetypeReqCallback,
    StoryChoiceNextCallback,
    StoryChoicePointsCallback,
    StoryNewArchetypeCallback,
    StoryNodeDeleteCallback,
    StoryNodeDetailCallback,
    StoryNodeListPageCallback,
    StoryNodeToggleCallback,
    StoryNodeTypeCallback,
)
from models.models import ArchetypeType, NodeType
from services import get_service
from services.story_service import StoryService
from utils.admin import is_admin

logger = logging.getLogger(__name__)
router = Router()

NODES_LIST_PAGE_SIZE = 12


def _deny_non_admin_message(message: Message) -> bool:
    """Retorna True si el usuario no es admin (handler debe abortar)."""
    return not is_admin(message.from_user.id)


async def _deny_non_admin_callback(callback: CallbackQuery) -> bool:
    """Retorna True si el usuario no es admin."""
    if not is_admin(callback.from_user.id):
        await callback.answer("Acceso denegado", show_alert=True)
        return True
    return False


# Estados para FSM
class NodeWizardStates(StatesGroup):
    waiting_title = State()
    waiting_content = State()
    selecting_type = State()
    waiting_chapter = State()
    waiting_order = State()
    selecting_starting = State()
    waiting_requirements = State()
    waiting_vip = State()
    waiting_cost = State()
    confirming = State()


class ChoiceWizardStates(StatesGroup):
    selecting_node = State()
    waiting_text = State()
    selecting_next_node = State()
    waiting_archetype_points = State()
    waiting_points_amount = State()
    waiting_additional_cost = State()
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
    waiting_reward = State()
    waiting_requirement_chapter = State()
    selecting_requirement_node = State()
    selecting_requirement_archetype = State()
    confirming = State()


# ==================== MENU PRINCIPAL ====================


@router.callback_query(F.data == "admin_narrative", lambda cb: is_admin(cb.from_user.id))
async def admin_narrative_menu(callback: CallbackQuery):
    """Menu de administracion de narrativa - Voz de Lucien"""
    with get_service(StoryService) as story_service:
        stats = story_service.get_story_stats()

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="➕ Forjar fragmento", callback_data="create_node")],
                [InlineKeyboardButton(text="📋 Ver fragmentos", callback_data="list_nodes")],
                [
                    InlineKeyboardButton(
                        text="🔗 Gestionar opciones", callback_data="manage_choices"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🎭 Gestionar arquetipos", callback_data="manage_archetypes"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🏆 Gestionar logros", callback_data="manage_achievements"
                    )
                ],
                [InlineKeyboardButton(text="📊 Observar el pulso", callback_data="story_stats")],
                [
                    InlineKeyboardButton(
                        text="🔙 Volver al sanctum", callback_data="admin_gamification"
                    )
                ],
            ]
        )

        text = (
            f"🎩 <b>Lucien:</b>\n\n"
            f"<i>Ah... los Hilos de la Historia de Diana.</i>\n\n"
            f"Aqui es donde se teje la narrativa que los visitantes experimentaran. "
            f"Cada fragmento, cada decision, cada arquetipo... todo se orquesta desde aqui.\n\n"
            f"📊 <b>El estado de los Fragmentos:</b>\n"
            f"   • Fragmentos activos: {stats['total_nodes']}\n"
            f"   • Capitulos: {stats['total_chapters']}\n"
            f"   • Visitantes en la historia: {stats['total_users']}\n"
            f"   • Han completado: {stats['completed_users']}\n"
            f"   • Logros disponibles: {stats['total_achievements']}\n\n"
            f"<i>Que aspecto de la narrativa requiere su atencion?</i>"
        )

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        await callback.answer()


# ==================== CREAR NODO ====================


@router.callback_query(F.data == "create_node", lambda cb: is_admin(cb.from_user.id))
async def create_node_start(callback: CallbackQuery, state: FSMContext):
    """Inicia wizard de creacion de nodo - Voz de Lucien"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_narrative")]
        ]
    )

    text = (
        "🎩 <b>Lucien:</b>\n\n"
        "<i>Vamos a forjar un nuevo fragmento de la historia...</i>\n\n"
        "<b>Paso 1:</b> El titulo del fragmento\n\n"
        "Indique un titulo evocador:\n"
        "<i>Ejemplo: El Primer Encuentro</i>"
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(NodeWizardStates.waiting_title)
    await callback.answer()


@router.message(NodeWizardStates.waiting_title)
async def process_node_title(message: Message, state: FSMContext):
    """Procesa titulo del nodo - Voz de Lucien"""
    if _deny_non_admin_message(message):
        return

    title = message.text.strip()
    if len(title) < 3:
        await message.answer("El titulo debe tener al menos 3 caracteres.")
        return

    await state.update_data(title=title)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_narrative")]
        ]
    )

    text = (
        "🎩 <b>Lucien:</b>\n\n"
        "<b>Paso 2:</b> El contenido del fragmento\n\n"
        "Escriba el texto que Diana compartira en este momento:\n\n"
        "<i>Puede usar HTML para formato: &lt;b&gt;negrita&lt;/b&gt;, &lt;i&gt;cursiva&lt;/i&gt;, etc.</i>"
    )

    await message.answer(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(NodeWizardStates.waiting_content)


@router.message(NodeWizardStates.waiting_content)
async def process_node_content(message: Message, state: FSMContext):
    """Procesa contenido del nodo - Voz de Lucien"""
    if _deny_non_admin_message(message):
        return

    content = message.text.strip()
    if len(content) < 10:
        await message.answer("El contenido debe tener al menos 10 caracteres.")
        return

    await state.update_data(content=content)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📖 Narrativo",
                    callback_data=StoryNodeTypeCallback(node_type=NodeType.NARRATIVE.value).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎭 Decision",
                    callback_data=StoryNodeTypeCallback(node_type=NodeType.DECISION.value).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏁 Final",
                    callback_data=StoryNodeTypeCallback(node_type=NodeType.ENDING.value).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="❓ Cuestionario",
                    callback_data=StoryNodeTypeCallback(node_type=NodeType.QUIZ.value).pack(),
                )
            ],
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_narrative")],
        ]
    )

    text = (
        "🎩 <b>Lucien:</b>\n\n"
        "<b>Paso 3:</b> Tipo de fragmento\n\n"
        "Seleccione que tipo de momento es este:"
    )

    await message.answer(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(NodeWizardStates.selecting_type)


@router.callback_query(NodeWizardStates.selecting_type, StoryNodeTypeCallback.filter())
async def select_node_type(
    callback: CallbackQuery, state: FSMContext, callback_data: StoryNodeTypeCallback
):
    """Selecciona tipo de nodo - Voz de Lucien"""
    if await _deny_non_admin_callback(callback):
        return

    try:
        node_type = NodeType(callback_data.node_type)
    except ValueError:
        await callback.answer("Tipo no valido", show_alert=True)
        return

    await state.update_data(node_type=node_type)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_narrative")]
        ]
    )

    text = (
        "🎩 <b>Lucien:</b>\n\n"
        "<b>Paso 4:</b> Capitulo\n\n"
        "Indique a que capitulo pertenece este fragmento (numero):\n"
        "<i>Ejemplo: 1</i>"
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(NodeWizardStates.waiting_chapter)
    await callback.answer()


@router.message(NodeWizardStates.waiting_chapter)
async def process_node_chapter(message: Message, state: FSMContext):
    """Procesa capitulo del nodo - Voz de Lucien"""
    if _deny_non_admin_message(message):
        return

    try:
        chapter = int(message.text.strip())
        if chapter < 1:
            raise ValueError("Debe ser mayor a 0")
    except ValueError:
        await message.answer("Por favor indique un numero valido mayor a 0.")
        return

    await state.update_data(chapter=chapter)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_narrative")]
        ]
    )

    text = (
        "🎩 <b>Lucien:</b>\n\n"
        "<b>Paso 5:</b> Orden en el capitulo\n\n"
        "Indique la posicion lineal de este fragmento (0 = primero):\n"
        "<i>Ejemplo: 0</i>"
    )

    await message.answer(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(NodeWizardStates.waiting_order)


@router.message(NodeWizardStates.waiting_order)
async def process_node_order(message: Message, state: FSMContext):
    """Procesa orden en capitulo del nodo."""
    if _deny_non_admin_message(message):
        return

    try:
        order_in_chapter = int(message.text.strip())
        if order_in_chapter < 0:
            raise ValueError
    except ValueError:
        await message.answer("Por favor indique un numero valido (0 o mayor).")
        return

    await state.update_data(order_in_chapter=order_in_chapter)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Si, nodo inicial", callback_data="node_starting_yes")],
            [InlineKeyboardButton(text="No", callback_data="node_starting_no")],
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_narrative")],
        ]
    )

    text = (
        "🎩 <b>Lucien:</b>\n\n"
        "<b>Paso 6:</b> Nodo inicial\n\n"
        "Este fragmento es el punto de entrada de la historia?"
    )

    await message.answer(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(NodeWizardStates.selecting_starting)


@router.callback_query(
    NodeWizardStates.selecting_starting, F.data.in_({"node_starting_yes", "node_starting_no"})
)
async def select_node_starting(callback: CallbackQuery, state: FSMContext):
    """Selecciona si el nodo es starting node."""
    if await _deny_non_admin_callback(callback):
        return

    await state.update_data(is_starting_node=callback.data == "node_starting_yes")

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🌸 Cualquiera",
                    callback_data=StoryArchetypeReqCallback(archetype="none").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎭 El Seductor",
                    callback_data=StoryArchetypeReqCallback(
                        archetype=ArchetypeType.SEDUCTOR.value
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="👁️ El Observador",
                    callback_data=StoryArchetypeReqCallback(
                        archetype=ArchetypeType.OBSERVER.value
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="💎 El Devoto",
                    callback_data=StoryArchetypeReqCallback(
                        archetype=ArchetypeType.DEVOTO.value
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗺️ El Explorador",
                    callback_data=StoryArchetypeReqCallback(
                        archetype=ArchetypeType.EXPLORADOR.value
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🌑 El Misterioso",
                    callback_data=StoryArchetypeReqCallback(
                        archetype=ArchetypeType.MISTERIOSO.value
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔥 El Intrepido",
                    callback_data=StoryArchetypeReqCallback(
                        archetype=ArchetypeType.INTREPIDO.value
                    ).pack(),
                )
            ],
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_narrative")],
        ]
    )

    text = (
        "🎩 <b>Lucien:</b>\n\n"
        "<b>Paso 7:</b> Requisitos de arquetipo\n\n"
        "Este fragmento esta disponible para todos, "
        "o solo para quienes han despertado un arquetipo especifico?"
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(NodeWizardStates.waiting_requirements)
    await callback.answer()


@router.callback_query(NodeWizardStates.waiting_requirements, StoryArchetypeReqCallback.filter())
async def select_archetype_requirement(
    callback: CallbackQuery, state: FSMContext, callback_data: StoryArchetypeReqCallback
):
    """Selecciona requisito de arquetipo - Voz de Lucien"""
    if await _deny_non_admin_callback(callback):
        return

    if callback_data.archetype == "none":
        required_archetype = None
    else:
        try:
            required_archetype = ArchetypeType(callback_data.archetype)
        except ValueError:
            await callback.answer("Arquetipo no valido", show_alert=True)
            return

    await state.update_data(required_archetype=required_archetype)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🌸 Sin requisito VIP", callback_data="node_vip_no")],
            [InlineKeyboardButton(text="💎 Requiere El Divan (VIP)", callback_data="node_vip_yes")],
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_narrative")],
        ]
    )

    text = (
        "🎩 <b>Lucien:</b>\n\n"
        "<b>Paso 8:</b> Requisito VIP\n\n"
        "Este fragmento requiere acceso a El Divan?"
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(NodeWizardStates.waiting_vip)
    await callback.answer()


@router.callback_query(NodeWizardStates.waiting_vip, F.data.in_({"node_vip_yes", "node_vip_no"}))
async def select_node_vip(callback: CallbackQuery, state: FSMContext):
    """Selecciona requisito VIP del nodo."""
    if await _deny_non_admin_callback(callback):
        return

    await state.update_data(required_vip=callback.data == "node_vip_yes")

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💋 Sin costo", callback_data="node_cost_0")],
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_narrative")],
        ]
    )

    text = (
        "🎩 <b>Lucien:</b>\n\n"
        "<b>Paso 9:</b> Costo en besitos\n\n"
        "Indique cuantos besitos cuesta acceder a este fragmento:\n"
        "<i>Ejemplo: 50 (o 0 para gratuito)</i>"
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(NodeWizardStates.waiting_cost)
    await callback.answer()


@router.callback_query(NodeWizardStates.waiting_cost, F.data == "node_cost_0")
async def node_cost_zero(callback: CallbackQuery, state: FSMContext):
    """Costo cero - Voz de Lucien"""
    if await _deny_non_admin_callback(callback):
        return

    await state.update_data(cost_besitos=0)
    await show_node_confirmation(callback, state)


@router.message(NodeWizardStates.waiting_cost)
async def process_node_cost(message: Message, state: FSMContext):
    """Procesa costo del nodo - Voz de Lucien"""
    if _deny_non_admin_message(message):
        return

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

    title = data.get("title", "")
    content = (
        data.get("content", "")[:100] + "..."
        if len(data.get("content", "")) > 100
        else data.get("content", "")
    )
    node_type = data.get("node_type", NodeType.NARRATIVE)
    chapter = data.get("chapter", 1)
    order_in_chapter = data.get("order_in_chapter", 0)
    is_starting_node = data.get("is_starting_node", False)
    required_archetype = data.get("required_archetype")
    required_vip = data.get("required_vip", False)
    cost_besitos = data.get("cost_besitos", 0)

    archetype_text = "Cualquiera" if not required_archetype else required_archetype.value.title()
    vip_text = "Si" if required_vip else "No"
    starting_text = "Si" if is_starting_node else "No"

    text = (
        f"🎩 <b>Lucien:</b>\n\n"
        f"<i>Permitame confirmar el fragmento...</i>\n\n"
        f"📖 <b>{html.escape(title)}</b>\n"
        f"Tipo: {node_type.value.title()}\n"
        f"Capitulo: {chapter}\n"
        f"Orden: {order_in_chapter}\n"
        f"Nodo inicial: {starting_text}\n"
        f"Arquetipo requerido: {html.escape(archetype_text)}\n"
        f"VIP requerido: {vip_text}\n"
        f"Costo: {cost_besitos} besitos\n\n"
        f"Contenido:\n<i>{html.escape(content)}</i>\n\n"
        f"<i>Desea forjar este fragmento?</i>"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Forjar fragmento", callback_data="confirm_create_node")],
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_narrative")],
        ]
    )

    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    else:
        await target.answer(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)

    await state.set_state(NodeWizardStates.confirming)


@router.callback_query(NodeWizardStates.confirming, F.data == "confirm_create_node")
async def confirm_create_node(callback: CallbackQuery, state: FSMContext):
    """Crea el nodo - Voz de Lucien"""
    if await _deny_non_admin_callback(callback):
        return

    data = await state.get_data()
    with get_service(StoryService) as story_service:
        try:
            if data.get("is_starting_node"):
                for existing in story_service.get_all_nodes(active_only=False):
                    if existing.is_starting_node:
                        story_service.update_node(existing.id, is_starting_node=False)

            node = story_service.create_node(
                title=data.get("title"),
                content=data.get("content"),
                node_type=data.get("node_type"),
                chapter=data.get("chapter", 1),
                order_in_chapter=data.get("order_in_chapter", 0),
                is_starting_node=data.get("is_starting_node", False),
                required_archetype=data.get("required_archetype"),
                required_vip=data.get("required_vip", False),
                cost_besitos=data.get("cost_besitos", 0),
                created_by=callback.from_user.id,
            )

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="➕ Agregar opciones",
                            callback_data=StoryAddChoicesCallback(node_id=node.id).pack(),
                        )
                    ],
                    [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_narrative")],
                ]
            )

            text = (
                f"🎩 <b>Lucien:</b>\n\n"
                f"<i>Excelente. El fragmento ha sido forjado...</i>\n\n"
                f"📖 <b>{html.escape(node.title)}</b>\n\n"
                f"<i>Ahora puede agregar opciones de decision si es necesario.</i>"
            )

            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
            logger.info(f"Fragmento creado: {node.title} por custodio {callback.from_user.id}")

        except Exception as e:
            logger.exception(f"Error forjando fragmento: {e}")
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_narrative")]
                ]
            )
            text = (
                "🎩 <b>Lucien:</b>\n\n"
                "<i>Hmm... algo inesperado ha ocurrido.</i>\n\n"
                "Permitame consultar con Diana sobre este inconveniente."
            )
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)

        await state.clear()
        await callback.answer()


# ==================== LISTAR NODOS ====================


def _build_nodes_list_view(nodes: list, page: int) -> tuple[str, InlineKeyboardMarkup]:
    """Construye texto y teclado paginado para list_nodes."""
    total_pages = max(1, math.ceil(len(nodes) / NODES_LIST_PAGE_SIZE))
    page = max(0, min(page, total_pages - 1))
    start = page * NODES_LIST_PAGE_SIZE
    page_nodes = nodes[start : start + NODES_LIST_PAGE_SIZE]

    text = "🎩 <b>Lucien:</b>\n\n"
    text += "<i>Los fragmentos de la historia:</i>\n\n"
    if total_pages > 1:
        text += f"<i>Pagina {page + 1} de {total_pages}</i>\n\n"

    buttons = []
    current_chapter = None
    for node in page_nodes:
        if node.chapter != current_chapter:
            current_chapter = node.chapter
            text += f"\n📚 <b>Capitulo {current_chapter}</b>\n"

        status = "✅" if node.is_active else "❌"
        node_type_emoji = {
            NodeType.NARRATIVE: "📖",
            NodeType.DECISION: "🎭",
            NodeType.ENDING: "🏁",
            NodeType.QUIZ: "❓",
        }.get(node.node_type, "📄")

        safe_title = html.escape(node.title[:30])
        text += f"{status} {node_type_emoji} {safe_title}\n"
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{status} {node.title[:35]}",
                    callback_data=StoryNodeDetailCallback(node_id=node.id).pack(),
                )
            ]
        )

    nav_row = []
    if page > 0:
        nav_row.append(
            InlineKeyboardButton(
                text="◀️",
                callback_data=StoryNodeListPageCallback(page=page - 1).pack(),
            )
        )
    if page < total_pages - 1:
        nav_row.append(
            InlineKeyboardButton(
                text="▶️",
                callback_data=StoryNodeListPageCallback(page=page + 1).pack(),
            )
        )
    if nav_row:
        buttons.append(nav_row)

    buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="admin_narrative")])
    return text, InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(F.data == "list_nodes", lambda cb: is_admin(cb.from_user.id))
async def list_nodes(callback: CallbackQuery):
    """Lista todos los nodos - Voz de Lucien"""
    await _render_nodes_list(callback, page=0)


@router.callback_query(StoryNodeListPageCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def list_nodes_page(callback: CallbackQuery, callback_data: StoryNodeListPageCallback):
    """Paginacion del listado de nodos."""
    await _render_nodes_list(callback, page=callback_data.page)


async def _render_nodes_list(callback: CallbackQuery, page: int) -> None:
    with get_service(StoryService) as story_service:
        nodes = story_service.get_all_nodes()

        if not nodes:
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="➕ Forjar fragmento", callback_data="create_node")],
                    [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_narrative")],
                ]
            )
            text = (
                "🎩 <b>Lucien:</b>\n\n"
                "<i>Los Fragmentos aun estan vacios...</i>\n\n"
                "Comience forjando el primer fragmento de la historia."
            )
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
            await callback.answer()
            return

        text, keyboard = _build_nodes_list_view(nodes, page)
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        await callback.answer()


# ==================== ESTADISTICAS ====================


@router.callback_query(F.data == "story_stats", lambda cb: is_admin(cb.from_user.id))
async def story_stats(callback: CallbackQuery):
    """Muestra estadisticas de la narrativa - Voz de Lucien"""
    with get_service(StoryService) as story_service:
        stats = story_service.get_story_stats()

        # Distribucion de arquetipos
        archetype_text = ""
        for archetype, count in stats["archetype_distribution"].items():
            if count > 0:
                archetype_text += f"   • {archetype.title()}: {count}\n"

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_narrative")]
            ]
        )

        text = (
            f"🎩 <b>Lucien:</b>\n\n"
            f"📊 <b>El pulso de los Fragmentos:</b>\n\n"
            f"📖 <b>Fragmentos:</b>\n"
            f"   • Activos: {stats['total_nodes']}\n"
            f"   • Capitulos: {stats['total_chapters']}\n\n"
            f"👥 <b>Visitantes:</b>\n"
            f"   • En la historia: {stats['total_users']}\n"
            f"   • Han completado: {stats['completed_users']}\n\n"
            f"🎭 <b>Distribucion de arquetipos:</b>\n"
            f"{archetype_text}\n"
            f"🏆 <b>Logros disponibles:</b> {stats['total_achievements']}"
        )

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        await callback.answer()


# ==================== GESTIONAR ARQUETIPOS ====================


@router.callback_query(F.data == "manage_archetypes", lambda cb: is_admin(cb.from_user.id))
async def manage_archetypes(callback: CallbackQuery):
    """Menu de gestion de arquetipos - Voz de Lucien"""
    with get_service(StoryService) as story_service:
        archetypes = story_service.get_all_archetypes()

        buttons = []

        # Mostrar arquetipos existentes
        for archetype in archetypes:
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"🎭 {archetype.name}",
                        callback_data=ArchetypeDetailCallback(
                            archetype=archetype.archetype_type.value
                        ).pack(),
                    )
                ]
            )

        # Opcion para crear nuevo
        buttons.append(
            [
                InlineKeyboardButton(
                    text="➕ Definir nuevo arquetipo", callback_data="create_archetype"
                )
            ]
        )
        buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="admin_narrative")])

        text = (
            "🎩 <b>Lucien:</b>\n\n"
            "<i>Los arquetipos que Diana ha definido...</i>\n\n"
            "Cada uno representa una faceta de quienes experimentan los Fragmentos."
        )

        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
            parse_mode=ParseMode.HTML,
        )
        await callback.answer()


# ==================== GESTIONAR LOGROS ====================


@router.callback_query(F.data == "manage_achievements", lambda cb: is_admin(cb.from_user.id))
async def manage_achievements(callback: CallbackQuery):
    """Menu de gestion de logros - Voz de Lucien"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Crear reconocimiento", callback_data="create_achievement"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 Ver reconocimientos", callback_data="list_achievements"
                )
            ],
            [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_narrative")],
        ]
    )

    text = (
        "🎩 <b>Lucien:</b>\n\n"
        "<i>Los reconocimientos que los visitantes pueden obtener...</i>\n\n"
        "Cada logro es un hito en su viaje por los Fragmentos de Diana."
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await callback.answer()


# ==================== GESTIONAR OPCIONES ====================


@router.callback_query(F.data == "manage_choices", lambda cb: is_admin(cb.from_user.id))
async def manage_choices(callback: CallbackQuery):
    """Menu de gestion de opciones - Voz de Lucien"""
    with get_service(StoryService) as story_service:
        nodes = story_service.get_all_nodes()

        # Solo nodos de decision
        decision_nodes = [n for n in nodes if n.node_type == NodeType.DECISION]

        if not decision_nodes:
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="➕ Forjar fragmento de decision", callback_data="create_node"
                        )
                    ],
                    [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_narrative")],
                ]
            )
            text = (
                "🎩 <b>Lucien:</b>\n\n"
                "<i>No hay fragmentos de decision...</i>\n\n"
                "Cree un fragmento de tipo 'Decision' primero."
            )
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
            await callback.answer()
            return

        buttons = []
        for node in decision_nodes:
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"🎭 {node.title[:35]}",
                        callback_data=StoryAddChoicesCallback(node_id=node.id).pack(),
                    )
                ]
            )

        buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="admin_narrative")])

        text = "🎩 <b>Lucien:</b>\n\n<i>Seleccione el fragmento al que desea agregar opciones:</i>"

        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
            parse_mode=ParseMode.HTML,
        )
        await callback.answer()

    # ==================== VER DETALLE DE NODO ====================


@router.callback_query(StoryNodeDetailCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def node_detail(callback: CallbackQuery, callback_data: StoryNodeDetailCallback):
    """Muestra detalle de un nodo - Voz de Lucien"""
    node_id = callback_data.node_id

    with get_service(StoryService) as story_service:
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
            NodeType.QUIZ: "❓",
        }.get(node.node_type, "📄")

        archetype_text = (
            "Cualquiera" if not node.required_archetype else node.required_archetype.value.title()
        )

        content_preview = node.content[:200] + ("..." if len(node.content) > 200 else "")
        text = (
            f"🎩 <b>Lucien:</b>\n\n"
            f"{node_type_emoji} <b>{html.escape(node.title)}</b>\n\n"
            f"📖 <b>Contenido:</b>\n<i>{html.escape(content_preview)}</i>\n\n"
            f"📊 <b>Detalles:</b>\n"
            f"   Tipo: {node.node_type.value.title()}\n"
            f"   Capitulo: {node.chapter}\n"
            f"   Estado: {status}\n"
            f"   Arquetipo requerido: {archetype_text}\n"
            f"   Costo: {node.cost_besitos} besitos\n"
            f"   Opciones: {len(choices)}\n\n"
            f"<i>Que desea hacer con este fragmento?</i>"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[])

        # Boton para agregar opciones si es de decision
        if node.node_type == NodeType.DECISION:
            keyboard.inline_keyboard.append(
                [
                    InlineKeyboardButton(
                        text="➕ Agregar opcion",
                        callback_data=StoryAddChoicesCallback(node_id=node.id).pack(),
                    )
                ]
            )

        keyboard.inline_keyboard.extend(
            [
                [
                    InlineKeyboardButton(
                        text=f"{'Desactivar' if node.is_active else 'Activar'}",
                        callback_data=StoryNodeToggleCallback(node_id=node.id).pack(),
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🗑️ Eliminar",
                        callback_data=StoryNodeDeleteCallback(node_id=node.id).pack(),
                    )
                ],
                [InlineKeyboardButton(text="🔙 Volver", callback_data="list_nodes")],
            ]
        )

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        await callback.answer()


@router.callback_query(StoryNodeToggleCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def toggle_node(callback: CallbackQuery, callback_data: StoryNodeToggleCallback):
    """Activa/desactiva un nodo - Voz de Lucien"""
    node_id = callback_data.node_id

    with get_service(StoryService) as story_service:
        node = story_service.get_node(node_id)

        if not node:
            await callback.answer("Fragmento no encontrado", show_alert=True)
            return

        story_service.update_node(node_id, is_active=not node.is_active)

        status = "activado" if not node.is_active else "desactivado"
        logger.info(
            f"story_admin_handlers | toggle_node | node_id={node_id} | "
            f"admin_id={callback.from_user.id} | result={status}"
        )
        await callback.answer(f"Fragmento {status}")
        detail_cb = StoryNodeDetailCallback(node_id=node_id)
        await node_detail(callback, detail_cb)


@router.callback_query(StoryNodeDeleteCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def delete_node_confirm(callback: CallbackQuery, callback_data: StoryNodeDeleteCallback):
    """Confirma eliminacion de nodo - Voz de Lucien"""
    node_id = callback_data.node_id

    # If already confirmed, execute delete
    if callback_data.confirmed:
        with get_service(StoryService) as story_service:
            success = story_service.delete_node(node_id)
            logger.info(
                f"story_admin_handlers | delete_node | node_id={node_id} | "
                f"admin_id={callback.from_user.id} | result={'ok' if success else 'failed'}"
            )

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Volver", callback_data="list_nodes")]
                ]
            )

            if success:
                text = "🎩 <b>Lucien:</b>\n\n<i>El fragmento ha sido eliminado.</i>"
            else:
                text = "🎩 <b>Lucien:</b>\n\n<i>No se pudo eliminar el fragmento.</i>"

            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
            await callback.answer()
        return

    # Show confirmation
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Si, eliminar",
                    callback_data=StoryNodeDeleteCallback(node_id=node_id, confirmed=True).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Cancelar",
                    callback_data=StoryNodeDetailCallback(node_id=node_id).pack(),
                )
            ],
        ]
    )

    text = (
        "🎩 <b>Lucien:</b>\n\n"
        "<i>Esta seguro de eliminar este fragmento?</i>\n\n"
        "Esta accion no se puede deshacer. "
        "Las opciones y progresos asociados tambien se perderan..."
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await callback.answer()


# ==================== AGREGAR OPCIONES A NODO ====================


@router.callback_query(StoryAddChoicesCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def add_choices_start(
    callback: CallbackQuery, state: FSMContext, callback_data: StoryAddChoicesCallback
):
    """Inicia wizard para agregar opcion a nodo - Voz de Lucien"""
    node_id = callback_data.node_id

    with get_service(StoryService) as story_service:
        node = story_service.get_node(node_id)

        if not node:
            await callback.answer("Fragmento no encontrado", show_alert=True)
            return

        await state.update_data(choice_node_id=node_id)

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="❌ Cancelar",
                        callback_data=StoryNodeDetailCallback(node_id=node_id).pack(),
                    )
                ]
            ]
        )

        text = (
            f"🎩 <b>Lucien:</b>\n\n"
            f"<i>Agregando opcion a: {html.escape(node.title)}</i>\n\n"
            f"<b>Paso 1:</b> Texto de la opcion\n\n"
            f"Escriba el texto que el visitante vera:\n"
            f"<i>Ejemplo: Aceptar la invitacion</i>"
        )

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        await state.set_state(ChoiceWizardStates.waiting_text)
        await callback.answer()


@router.message(ChoiceWizardStates.waiting_text)
async def process_choice_text(message: Message, state: FSMContext):
    """Procesa texto de la opcion - Voz de Lucien"""
    if _deny_non_admin_message(message):
        return

    text = message.text.strip()
    if len(text) < 3:
        await message.answer("El texto debe tener al menos 3 caracteres.")
        return

    await state.update_data(choice_text=text)

    with get_service(StoryService) as story_service:
        nodes = story_service.get_all_nodes()

        buttons = []
        for node in nodes:
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"📖 {node.title[:35]}",
                        callback_data=StoryChoiceNextCallback(node_id=node.id).pack(),
                    )
                ]
            )

        buttons.append(
            [
                InlineKeyboardButton(
                    text="🏁 Fin de historia",
                    callback_data=StoryChoiceNextCallback(node_id=0).pack(),
                )
            ]
        )
        buttons.append([InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_narrative")])

        text_msg = (
            "🎩 <b>Lucien:</b>\n\n"
            "<b>Paso 2:</b> Seleccionar siguiente fragmento\n\n"
            "A que fragmento lleva esta opcion?"
        )

        await message.answer(
            text_msg,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
            parse_mode=ParseMode.HTML,
        )
        await state.set_state(ChoiceWizardStates.selecting_next_node)


@router.callback_query(ChoiceWizardStates.selecting_next_node, StoryChoiceNextCallback.filter())
async def select_choice_next_node(
    callback: CallbackQuery, state: FSMContext, callback_data: StoryChoiceNextCallback
):
    """Selecciona el siguiente nodo - Voz de Lucien"""
    if await _deny_non_admin_callback(callback):
        return

    next_node_id = callback_data.node_id if callback_data.node_id else None

    await state.update_data(choice_next_node_id=next_node_id)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🌸 Ninguno",
                    callback_data=StoryChoicePointsCallback(archetype="none").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎭 Seductor",
                    callback_data=StoryChoicePointsCallback(
                        archetype=ArchetypeType.SEDUCTOR.value
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="👁️ Observador",
                    callback_data=StoryChoicePointsCallback(
                        archetype=ArchetypeType.OBSERVER.value
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="💎 Devoto",
                    callback_data=StoryChoicePointsCallback(
                        archetype=ArchetypeType.DEVOTO.value
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗺️ Explorador",
                    callback_data=StoryChoicePointsCallback(
                        archetype=ArchetypeType.EXPLORADOR.value
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🌑 Misterioso",
                    callback_data=StoryChoicePointsCallback(
                        archetype=ArchetypeType.MISTERIOSO.value
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔥 Intrepido",
                    callback_data=StoryChoicePointsCallback(
                        archetype=ArchetypeType.INTREPIDO.value
                    ).pack(),
                )
            ],
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_narrative")],
        ]
    )

    text = (
        "🎩 <b>Lucien:</b>\n\n"
        "<b>Paso 3:</b> Puntos de arquetipo\n\n"
        "Esta opcion suma puntos a algun arquetipo?"
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(ChoiceWizardStates.waiting_archetype_points)
    await callback.answer()


@router.callback_query(
    ChoiceWizardStates.waiting_archetype_points, StoryChoicePointsCallback.filter()
)
async def select_choice_archetype_points(
    callback: CallbackQuery, state: FSMContext, callback_data: StoryChoicePointsCallback
):
    """Selecciona puntos de arquetipo - Voz de Lucien"""
    if await _deny_non_admin_callback(callback):
        return

    if callback_data.archetype == "none":
        selected_archetype = None
    else:
        try:
            selected_archetype = ArchetypeType(callback_data.archetype)
        except ValueError:
            await callback.answer("Arquetipo no valido", show_alert=True)
            return

    await state.update_data(choice_archetype=selected_archetype)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="0 puntos", callback_data="choice_points_0")],
            [InlineKeyboardButton(text="1 punto", callback_data="choice_points_1")],
            [InlineKeyboardButton(text="3 puntos", callback_data="choice_points_3")],
            [InlineKeyboardButton(text="5 puntos", callback_data="choice_points_5")],
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_narrative")],
        ]
    )

    text = (
        "🎩 <b>Lucien:</b>\n\n"
        "<b>Paso 4:</b> Cantidad de puntos de arquetipo\n\n"
        "Cuantos puntos suma esta opcion?"
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(ChoiceWizardStates.waiting_points_amount)
    await callback.answer()


@router.callback_query(
    ChoiceWizardStates.waiting_points_amount, F.data.startswith("choice_points_")
)
async def select_choice_points_amount(callback: CallbackQuery, state: FSMContext):
    """Selecciona cantidad de puntos de arquetipo."""
    if await _deny_non_admin_callback(callback):
        return

    points = int(callback.data.rsplit("_", 1)[-1])
    await state.update_data(choice_archetype_points=points)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Sin costo extra", callback_data="choice_extra_cost_0")],
            [InlineKeyboardButton(text="10 besitos extra", callback_data="choice_extra_cost_10")],
            [InlineKeyboardButton(text="50 besitos extra", callback_data="choice_extra_cost_50")],
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_narrative")],
        ]
    )

    text = (
        "🎩 <b>Lucien:</b>\n\n"
        "<b>Paso 5:</b> Costo adicional en besitos\n\n"
        "Esta opcion tiene un recargo extra?"
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(ChoiceWizardStates.waiting_additional_cost)
    await callback.answer()


@router.callback_query(
    ChoiceWizardStates.waiting_additional_cost, F.data.startswith("choice_extra_cost_")
)
async def select_choice_additional_cost(callback: CallbackQuery, state: FSMContext):
    """Selecciona costo adicional de la opcion."""
    if await _deny_non_admin_callback(callback):
        return

    additional_cost = int(callback.data.rsplit("_", 1)[-1])
    await state.update_data(choice_additional_cost=additional_cost)

    data = await state.get_data()
    choice_text = data.get("choice_text", "")
    next_node_id = data.get("choice_next_node_id")
    selected_archetype = data.get("choice_archetype")
    points = data.get("choice_archetype_points", 0)

    next_node_text = "Fin de historia" if not next_node_id else f"Fragmento {next_node_id}"
    archetype_text = "Ninguno" if not selected_archetype else selected_archetype.value.title()

    text = (
        f"🎩 <b>Lucien:</b>\n\n"
        f"<i>Confirme la opcion...</i>\n\n"
        f"🎭 <b>Texto:</b> {html.escape(choice_text)}\n"
        f"📖 <b>Lleva a:</b> {html.escape(next_node_text)}\n"
        f"🌸 <b>Arquetipo:</b> {html.escape(archetype_text)}\n"
        f"⭐ <b>Puntos:</b> {points}\n"
        f"💋 <b>Costo extra:</b> {additional_cost} besitos\n\n"
        f"<i>Desea agregar esta opcion?</i>"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Agregar opcion", callback_data="confirm_create_choice")],
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_narrative")],
        ]
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(ChoiceWizardStates.confirming)
    await callback.answer()


@router.callback_query(ChoiceWizardStates.confirming, F.data == "confirm_create_choice")
async def confirm_create_choice(callback: CallbackQuery, state: FSMContext):
    """Crea la opcion - Voz de Lucien"""
    if await _deny_non_admin_callback(callback):
        return

    data = await state.get_data()
    with get_service(StoryService) as story_service:
        try:
            next_node_id = data.get("choice_next_node_id") or None
            archetype = data.get("choice_archetype")
            points = data.get("choice_archetype_points", 0) if archetype else 0
            story_service.create_choice(
                node_id=data.get("choice_node_id"),
                text=data.get("choice_text"),
                next_node_id=next_node_id,
                choice_archetype=archetype,
                archetype_points=points,
                additional_cost=data.get("choice_additional_cost", 0),
            )

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="➕ Agregar otra opcion",
                            callback_data=StoryAddChoicesCallback(
                                node_id=data.get("choice_node_id")
                            ).pack(),
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="🔙 Volver",
                            callback_data=StoryNodeDetailCallback(
                                node_id=data.get("choice_node_id")
                            ).pack(),
                        )
                    ],
                ]
            )

            text = "🎩 <b>Lucien:</b>\n\n<i>La opcion ha sido agregada...</i>"

            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
            logger.info(
                f"Opcion agregada al nodo {data.get('choice_node_id')} por custodio {callback.from_user.id}"
            )

        except Exception as e:
            logger.exception(f"Error agregando opcion: {e}")
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_narrative")]
                ]
            )
            text = "🎩 <b>Lucien:</b>\n\n<i>Hmm... algo inesperado ha ocurrido.</i>"
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)

        await state.clear()
        await callback.answer()


# ==================== CREAR ARQUETIPO ====================


@router.callback_query(F.data == "create_archetype", lambda cb: is_admin(cb.from_user.id))
async def create_archetype_start(callback: CallbackQuery, state: FSMContext):
    """Inicia wizard para crear arquetipo - Voz de Lucien"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎭 El Seductor",
                    callback_data=StoryNewArchetypeCallback(
                        archetype=ArchetypeType.SEDUCTOR.value
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="👁️ El Observador",
                    callback_data=StoryNewArchetypeCallback(
                        archetype=ArchetypeType.OBSERVER.value
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="💎 El Devoto",
                    callback_data=StoryNewArchetypeCallback(
                        archetype=ArchetypeType.DEVOTO.value
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗺️ El Explorador",
                    callback_data=StoryNewArchetypeCallback(
                        archetype=ArchetypeType.EXPLORADOR.value
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🌑 El Misterioso",
                    callback_data=StoryNewArchetypeCallback(
                        archetype=ArchetypeType.MISTERIOSO.value
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔥 El Intrepido",
                    callback_data=StoryNewArchetypeCallback(
                        archetype=ArchetypeType.INTREPIDO.value
                    ).pack(),
                )
            ],
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="manage_archetypes")],
        ]
    )

    text = (
        "🎩 <b>Lucien:</b>\n\n"
        "<i>Que arquetipo desea definir?</i>\n\n"
        "Seleccione el tipo de arquetipo:"
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(ArchetypeWizardStates.selecting_type)
    await callback.answer()


@router.callback_query(ArchetypeWizardStates.selecting_type, StoryNewArchetypeCallback.filter())
async def select_new_archetype_type(
    callback: CallbackQuery, state: FSMContext, callback_data: StoryNewArchetypeCallback
):
    """Selecciona tipo de arquetipo - Voz de Lucien"""
    if await _deny_non_admin_callback(callback):
        return

    try:
        archetype_type = ArchetypeType(callback_data.archetype)
    except ValueError:
        await callback.answer("Tipo no valido", show_alert=True)
        return

    # Verificar si ya existe
    with get_service(StoryService) as story_service:
        existing = story_service.get_archetype(archetype_type)
        if existing:
            await callback.answer("Este arquetipo ya esta definido", show_alert=True)
            return

        await state.update_data(archetype_type=archetype_type)

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="❌ Cancelar", callback_data="manage_archetypes")]
            ]
        )

        text = (
            f"🎩 <b>Lucien:</b>\n\n"
            f"<b>Definiendo:</b> {archetype_type.value.title()}\n\n"
            f"<b>Paso 1:</b> Nombre del arquetipo\n\n"
            f"Indique como se llamara este arquetipo:\n"
            f"<i>Ejemplo: El Seductor</i>"
        )

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        await state.set_state(ArchetypeWizardStates.waiting_name)
        await callback.answer()


@router.message(ArchetypeWizardStates.waiting_name)
async def process_archetype_name(message: Message, state: FSMContext):
    """Procesa nombre del arquetipo - Voz de Lucien"""
    if _deny_non_admin_message(message):
        return

    name = message.text.strip()
    if len(name) < 3:
        await message.answer("El nombre debe tener al menos 3 caracteres.")
        return

    await state.update_data(archetype_name=name)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="manage_archetypes")]
        ]
    )

    text = (
        "🎩 <b>Lucien:</b>\n\n"
        "<b>Paso 2:</b> Descripcion\n\n"
        "Describa este arquetipo:\n"
        "<i>Ejemplo: Quien busca el placer y la conquista...</i>"
    )

    await message.answer(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(ArchetypeWizardStates.waiting_description)


@router.message(ArchetypeWizardStates.waiting_description)
async def process_archetype_description(message: Message, state: FSMContext):
    """Procesa descripcion del arquetipo - Voz de Lucien"""
    if _deny_non_admin_message(message):
        return

    description = message.text.strip()
    if len(description) < 10:
        await message.answer("La descripcion debe tener al menos 10 caracteres.")
        return

    await state.update_data(archetype_description=description)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📖 Omitir", callback_data="archetype_welcome_skip")],
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="manage_archetypes")],
        ]
    )

    text = (
        "🎩 <b>Lucien:</b>\n\n"
        "<b>Paso 3:</b> Mensaje de bienvenida (opcional)\n\n"
        "Escriba el mensaje que recibira quien despierte este arquetipo:\n"
        "<i>Ejemplo: Has despertado al Seductor...</i>"
    )

    await message.answer(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(ArchetypeWizardStates.waiting_welcome)


@router.callback_query(ArchetypeWizardStates.waiting_welcome, F.data == "archetype_welcome_skip")
async def skip_archetype_welcome(callback: CallbackQuery, state: FSMContext):
    """Omite mensaje de bienvenida - Voz de Lucien"""
    if await _deny_non_admin_callback(callback):
        return

    await state.update_data(archetype_welcome=None)
    await show_archetype_confirmation(callback, state)


@router.message(ArchetypeWizardStates.waiting_welcome)
async def process_archetype_welcome(message: Message, state: FSMContext):
    """Procesa mensaje de bienvenida - Voz de Lucien"""
    if _deny_non_admin_message(message):
        return

    welcome = message.text.strip()
    await state.update_data(archetype_welcome=welcome)
    await show_archetype_confirmation(message, state)


async def show_archetype_confirmation(target, state: FSMContext):
    """Muestra confirmacion del arquetipo - Voz de Lucien"""
    data = await state.get_data()

    archetype_type = data.get("archetype_type")
    name = data.get("archetype_name")
    description = data.get("archetype_description")
    welcome = data.get("archetype_welcome", "No especificado")

    is_edit = data.get("is_edit", False)
    desc_preview = description[:100] + ("..." if len(description) > 100 else "")
    welcome_preview = (
        (welcome[:100] + ("..." if len(welcome) > 100 else ""))
        if welcome and welcome != "No especificado"
        else "No especificado"
    )

    text = (
        f"🎩 <b>Lucien:</b>\n\n"
        f"<i>Confirme el arquetipo...</i>\n\n"
        f"🎭 <b>{html.escape(name)}</b> ({html.escape(archetype_type.value.title())})\n\n"
        f"📖 <b>Descripcion:</b>\n<i>{html.escape(desc_preview)}</i>\n\n"
        f"💬 <b>Bienvenida:</b>\n<i>{html.escape(welcome_preview)}</i>\n\n"
        f"<i>Desea {'actualizar' if is_edit else 'definir'} este arquetipo?</i>"
    )

    confirm_cb = "confirm_edit_archetype" if is_edit else "confirm_create_archetype"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Actualizar arquetipo" if is_edit else "✅ Definir arquetipo",
                    callback_data=confirm_cb,
                )
            ],
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="manage_archetypes")],
        ]
    )

    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    else:
        await target.answer(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)

    await state.set_state(ArchetypeWizardStates.confirming)


@router.callback_query(ArchetypeWizardStates.confirming, F.data == "confirm_create_archetype")
async def confirm_create_archetype(callback: CallbackQuery, state: FSMContext):
    """Crea el arquetipo - Voz de Lucien"""
    if await _deny_non_admin_callback(callback):
        return

    data = await state.get_data()
    with get_service(StoryService) as story_service:
        try:
            archetype = story_service.create_archetype(
                archetype_type=data.get("archetype_type"),
                name=data.get("archetype_name"),
                description=data.get("archetype_description"),
                welcome_message=data.get("archetype_welcome"),
                created_by=callback.from_user.id,
            )

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Volver", callback_data="manage_archetypes")]
                ]
            )

            text = (
                f"🎩 <b>Lucien:</b>\n\n"
                f"<i>El arquetipo ha sido definido...</i>\n\n"
                f"🎭 <b>{html.escape(archetype.name)}</b>"
            )

            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
            logger.info(f"Arquetipo creado: {archetype.name} por custodio {callback.from_user.id}")

        except Exception as e:
            logger.exception(f"Error definiendo arquetipo: {e}")
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Volver", callback_data="manage_archetypes")]
                ]
            )
            text = "🎩 <b>Lucien:</b>\n\n<i>Hmm... algo inesperado ha ocurrido.</i>"
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)

        await state.clear()
        await callback.answer()


@router.callback_query(ArchetypeWizardStates.confirming, F.data == "confirm_edit_archetype")
async def confirm_edit_archetype(callback: CallbackQuery, state: FSMContext):
    """Actualiza metadatos del arquetipo."""
    if await _deny_non_admin_callback(callback):
        return

    data = await state.get_data()
    with get_service(StoryService) as story_service:
        try:
            archetype_type = data.get("archetype_type")
            success = story_service.update_archetype(
                archetype_type,
                name=data.get("archetype_name"),
                description=data.get("archetype_description"),
                welcome_message=data.get("archetype_welcome"),
            )
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Volver", callback_data="manage_archetypes")]
                ]
            )
            if success:
                text = (
                    "🎩 <b>Lucien:</b>\n\n"
                    f"<i>El arquetipo ha sido actualizado...</i>\n\n"
                    f"🎭 <b>{html.escape(data.get('archetype_name', ''))}</b>"
                )
            else:
                text = "🎩 <b>Lucien:</b>\n\n<i>No se pudo actualizar el arquetipo.</i>"

            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.exception(f"Error actualizando arquetipo: {e}")
            await callback.answer("Error al actualizar", show_alert=True)

        await state.clear()
        await callback.answer()


# ==================== VER DETALLE DE ARQUETIPO ====================


@router.callback_query(ArchetypeDetailCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def archetype_detail(callback: CallbackQuery, callback_data: ArchetypeDetailCallback):
    """Muestra detalle de un arquetipo - Voz de Lucien"""
    try:
        archetype_type = ArchetypeType(callback_data.archetype)
    except (ValueError, KeyError):
        await callback.answer("Arquetipo no valido", show_alert=True)
        return

    with get_service(StoryService) as story_service:
        archetype = story_service.get_archetype(archetype_type)

        if not archetype:
            await callback.answer("Arquetipo no encontrado", show_alert=True)
            return

        text = (
            f"🎩 <b>Lucien:</b>\n\n"
            f"🎭 <b>{html.escape(archetype.name)}</b>\n"
            f"Tipo: {html.escape(archetype.archetype_type.value.title())}\n\n"
            f"📖 <b>Descripcion:</b>\n<i>{html.escape(archetype.description)}</i>\n\n"
        )

        if archetype.welcome_message:
            text += (
                f"💬 <b>Mensaje de bienvenida:</b>\n"
                f"<i>{html.escape(archetype.welcome_message)}</i>\n\n"
            )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✏️ Editar",
                        callback_data=StoryArchetypeEditCallback(
                            archetype=archetype.archetype_type.value
                        ).pack(),
                    )
                ],
                [InlineKeyboardButton(text="🔙 Volver", callback_data="manage_archetypes")],
            ]
        )

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        await callback.answer()


@router.callback_query(StoryArchetypeEditCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def edit_archetype_start(
    callback: CallbackQuery, state: FSMContext, callback_data: StoryArchetypeEditCallback
):
    """Inicia wizard de edicion de arquetipo (tipo fijo)."""
    if await _deny_non_admin_callback(callback):
        return

    try:
        archetype_type = ArchetypeType(callback_data.archetype)
    except ValueError:
        await callback.answer("Tipo no valido", show_alert=True)
        return

    with get_service(StoryService) as story_service:
        archetype = story_service.get_archetype(archetype_type)
        if not archetype:
            await callback.answer("Arquetipo no encontrado", show_alert=True)
            return

        await state.update_data(
            is_edit=True,
            archetype_type=archetype_type,
            archetype_name=archetype.name,
            archetype_description=archetype.description,
            archetype_welcome=archetype.welcome_message,
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="❌ Cancelar", callback_data="manage_archetypes")]
            ]
        )

        text = (
            f"🎩 <b>Lucien:</b>\n\n"
            f"<b>Editando:</b> {html.escape(archetype_type.value.title())}\n\n"
            f"<b>Paso 1:</b> Nombre del arquetipo\n\n"
            f"Nombre actual: <b>{html.escape(archetype.name)}</b>\n"
            f"Envie el nuevo nombre o reenvie el actual:"
        )

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        await state.set_state(ArchetypeWizardStates.waiting_name)
        await callback.answer()


# ==================== CREAR LOGRO ====================


@router.callback_query(F.data == "create_achievement", lambda cb: is_admin(cb.from_user.id))
async def create_achievement_start(callback: CallbackQuery, state: FSMContext):
    """Inicia wizard para crear logro - Voz de Lucien"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="manage_achievements")]
        ]
    )

    text = (
        "🎩 <b>Lucien:</b>\n\n"
        "<i>Vamos a crear un nuevo reconocimiento...</i>\n\n"
        "<b>Paso 1:</b> Nombre del logro\n\n"
        "Indique un nombre evocador:\n"
        "<i>Ejemplo: El Primer Paso</i>"
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(AchievementWizardStates.waiting_name)
    await callback.answer()


@router.message(AchievementWizardStates.waiting_name)
async def achievement_name_input(message: Message, state: FSMContext):
    """Recibe nombre del logro"""
    if _deny_non_admin_message(message):
        return

    name = message.text.strip()
    if len(name) < 3:
        await message.answer("El nombre debe tener al menos 3 caracteres.")
        return

    await state.update_data(achievement_name=name)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="manage_achievements")]
        ]
    )

    text = (
        "🎩 <b>Lucien:</b>\n\n"
        "<b>Paso 2:</b> Descripcion\n\n"
        "Describa este reconocimiento:\n"
        "<i>Ejemplo: Completa tu primer fragmento de historia</i>"
    )

    await message.answer(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(AchievementWizardStates.waiting_description)


@router.message(AchievementWizardStates.waiting_description)
async def achievement_description_input(message: Message, state: FSMContext):
    """Recibe descripcion del logro"""
    if _deny_non_admin_message(message):
        return

    description = message.text.strip()
    if len(description) < 5:
        await message.answer("La descripcion debe tener al menos 5 caracteres.")
        return

    await state.update_data(achievement_description=description)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="manage_achievements")]
        ]
    )

    text = (
        "🎩 <b>Lucien:</b>\n\n"
        "<b>Paso 3:</b> Icono\n\n"
        "Envie un emoji para este reconocimiento:\n"
        "<i>Ejemplo: 🌹</i>"
    )

    await message.answer(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(AchievementWizardStates.waiting_icon)


@router.message(AchievementWizardStates.waiting_icon)
async def achievement_icon_input(message: Message, state: FSMContext):
    """Recibe icono y pide recompensa en besitos."""
    if _deny_non_admin_message(message):
        return

    icon = message.text.strip()[:10]
    if not icon:
        await message.answer("Indique un emoji valido.")
        return

    await state.update_data(achievement_icon=icon)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="manage_achievements")]
        ]
    )

    text = (
        "🎩 <b>Lucien:</b>\n\n"
        "<b>Paso 4:</b> Recompensa en besitos\n\n"
        "Cuantos besitos otorga este reconocimiento?\n"
        "<i>Ejemplo: 0 o 25</i>"
    )

    await message.answer(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(AchievementWizardStates.waiting_reward)


@router.message(AchievementWizardStates.waiting_reward)
async def achievement_reward_input(message: Message, state: FSMContext):
    """Recibe recompensa en besitos."""
    if _deny_non_admin_message(message):
        return

    try:
        reward = int(message.text.strip())
        if reward < 0:
            raise ValueError
    except ValueError:
        await message.answer("Indique un numero valido (0 o mayor).")
        return

    await state.update_data(reward_besitos=reward)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="manage_achievements")]
        ]
    )

    text = (
        "🎩 <b>Lucien:</b>\n\n"
        "<b>Paso 5:</b> Capitulo requerido\n\n"
        "Indique el capitulo minimo requerido (0 = ninguno):\n"
        "<i>Ejemplo: 2</i>"
    )

    await message.answer(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(AchievementWizardStates.waiting_requirement_chapter)


@router.message(AchievementWizardStates.waiting_requirement_chapter)
async def achievement_chapter_requirement_input(message: Message, state: FSMContext):
    """Recibe capitulo requerido y pide arquetipo opcional."""
    if _deny_non_admin_message(message):
        return

    try:
        chapter = int(message.text.strip())
        if chapter < 0:
            raise ValueError
    except ValueError:
        await message.answer("Indique un numero valido (0 o mayor).")
        return

    await state.update_data(
        required_chapter=chapter if chapter > 0 else None,
    )

    with get_service(StoryService) as story_service:
        nodes = story_service.get_all_nodes()
        buttons = [
            [
                InlineKeyboardButton(
                    text="🌸 Sin nodo requerido",
                    callback_data=StoryAchievementNodeCallback(node_id=0).pack(),
                )
            ]
        ]
        for node in nodes[:20]:
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"📖 {node.title[:35]}",
                        callback_data=StoryAchievementNodeCallback(node_id=node.id).pack(),
                    )
                ]
            )
        buttons.append(
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="manage_achievements")]
        )

        text = (
            "🎩 <b>Lucien:</b>\n\n"
            "<b>Paso 6:</b> Nodo requerido (opcional)\n\n"
            "Seleccione el fragmento que debe visitarse para desbloquear:"
        )

        await message.answer(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
            parse_mode=ParseMode.HTML,
        )
    await state.set_state(AchievementWizardStates.selecting_requirement_node)


@router.callback_query(
    AchievementWizardStates.selecting_requirement_node,
    StoryAchievementNodeCallback.filter(),
)
async def achievement_node_requirement_select(
    callback: CallbackQuery, state: FSMContext, callback_data: StoryAchievementNodeCallback
):
    """Selecciona nodo requerido y pide arquetipo opcional."""
    if await _deny_non_admin_callback(callback):
        return

    required_node_id = callback_data.node_id if callback_data.node_id else None
    await state.update_data(required_node_id=required_node_id)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🌸 Sin arquetipo",
                    callback_data=StoryArchetypeReqCallback(archetype="none").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎭 Seductor",
                    callback_data=StoryArchetypeReqCallback(
                        archetype=ArchetypeType.SEDUCTOR.value
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="👁️ Observador",
                    callback_data=StoryArchetypeReqCallback(
                        archetype=ArchetypeType.OBSERVER.value
                    ).pack(),
                )
            ],
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="manage_achievements")],
        ]
    )

    text = (
        "🎩 <b>Lucien:</b>\n\n"
        "<b>Paso 7:</b> Arquetipo requerido (opcional)\n\n"
        "Seleccione un arquetipo requerido, si aplica:"
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(AchievementWizardStates.selecting_requirement_archetype)
    await callback.answer()


@router.callback_query(
    AchievementWizardStates.selecting_requirement_archetype,
    StoryArchetypeReqCallback.filter(),
)
async def achievement_archetype_requirement_select(
    callback: CallbackQuery, state: FSMContext, callback_data: StoryArchetypeReqCallback
):
    """Selecciona arquetipo requerido y muestra confirmacion."""
    if await _deny_non_admin_callback(callback):
        return

    if callback_data.archetype == "none":
        required_archetype = None
    else:
        try:
            required_archetype = ArchetypeType(callback_data.archetype)
        except ValueError:
            await callback.answer("Arquetipo no valido", show_alert=True)
            return

    await state.update_data(required_archetype=required_archetype)

    data = await state.get_data()
    name = data.get("achievement_name", "")
    desc = data.get("achievement_description", "")
    icon = data.get("achievement_icon", "🏆")
    reward = data.get("reward_besitos", 0)
    chapter = data.get("required_chapter")
    required_node_id = data.get("required_node_id")
    archetype_text = (
        "Ninguno" if not required_archetype else required_archetype.value.title()
    )
    node_text = "Ninguno" if not required_node_id else f"Fragmento {required_node_id}"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Crear reconocimiento", callback_data="confirm_create_achievement"
                )
            ],
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="manage_achievements")],
        ]
    )

    text = (
        f"🎩 <b>Lucien:</b>\n\n"
        f"<i>Confirme el reconocimiento...</i>\n\n"
        f"{icon} <b>{html.escape(name)}</b>\n"
        f"<i>{html.escape(desc)}</i>\n\n"
        f"Recompensa: {reward} besitos\n"
        f"Nodo req.: {html.escape(node_text)}\n"
        f"Capitulo req.: {chapter or 'Ninguno'}\n"
        f"Arquetipo req.: {html.escape(archetype_text)}"
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(AchievementWizardStates.confirming)
    await callback.answer()


@router.callback_query(AchievementWizardStates.confirming, F.data == "confirm_create_achievement")
async def confirm_create_achievement(callback: CallbackQuery, state: FSMContext):
    """Crea el logro"""
    if await _deny_non_admin_callback(callback):
        return

    data = await state.get_data()
    with get_service(StoryService) as story_service:
        try:
            achievement = story_service.create_achievement(
                name=data.get("achievement_name"),
                description=data.get("achievement_description"),
                icon=data.get("achievement_icon", "🏆"),
                required_node_id=data.get("required_node_id"),
                required_chapter=data.get("required_chapter"),
                required_archetype=data.get("required_archetype"),
                reward_besitos=data.get("reward_besitos", 0),
                created_by=callback.from_user.id,
            )

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Volver", callback_data="manage_achievements")]
                ]
            )

            text = (
                f"🎩 <b>Lucien:</b>\n\n"
                f"<i>El reconocimiento ha sido creado...</i>\n\n"
                f"{achievement.icon} <b>{html.escape(achievement.name)}</b>"
            )

            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
            logger.info(f"Logro creado: {achievement.name} por custodio {callback.from_user.id}")

        except Exception as e:
            logger.exception(f"Error creando logro: {e}")
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Volver", callback_data="manage_achievements")]
                ]
            )
            text = "🎩 <b>Lucien:</b>\n\n<i>Hmm... algo inesperado ha ocurrido.</i>"
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)

        await state.clear()
        await callback.answer()


# ==================== LISTAR LOGROS ====================


@router.callback_query(F.data == "list_achievements", lambda cb: is_admin(cb.from_user.id))
async def list_achievements(callback: CallbackQuery):
    """Lista todos los logros - Voz de Lucien"""
    with get_service(StoryService) as story_service:
        achievements = story_service.get_all_achievements()

        if achievements:
            lines = []
            for ach in achievements:
                status = "✅" if ach.is_active else "❌"
                lines.append(
                    f"{status} {ach.icon} <b>{html.escape(ach.name)}</b>\n"
                    f"   <i>{html.escape(ach.description[:60])}</i>"
                )
            achievements_text = "\n\n".join(lines)
        else:
            achievements_text = "<i>Aun no hay reconocimientos definidos...</i>"

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="➕ Crear reconocimiento", callback_data="create_achievement"
                    )
                ],
                [InlineKeyboardButton(text="🔙 Volver", callback_data="manage_achievements")],
            ]
        )

        text = (
            f"🎩 <b>Lucien:</b>\n\n<i>Los reconocimientos disponibles...</i>\n\n{achievements_text}"
        )

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        await callback.answer()
