"""
Handlers de Admin - QuestionSet Management

Handlers para la gestión de sets de preguntas de trivia.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from services.question_set_service import QuestionSetService
from handlers.admin_handlers import is_admin
import logging

logger = logging.getLogger(__name__)
router = Router()


# Estados para FSM
class QuestionSetStates(StatesGroup):
    waiting_name = State()
    waiting_description = State()
    waiting_file_path = State()
    waiting_question_set_confirm = State()  # Para confirmacion en flujo de creacion
    waiting_set_to_activate = State()      # Para seleccion en flujo de activacion


# ==================== MENÚ PRINCIPAL ====================

@router.callback_query(F.data == "admin_question_sets", lambda cb: is_admin(cb.from_user.id))
async def admin_question_sets_menu(callback: CallbackQuery):
    """Menú principal de gestión de QuestionSets"""
    service = QuestionSetService()
    try:
        sets = service.get_all_sets()
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="📋 Ver sets",
                callback_data="view_question_sets"
            )],
            [InlineKeyboardButton(
                text="➕ Crear set",
                callback_data="create_question_set"
            )],
            [InlineKeyboardButton(
                text="✅ Activar set manualmente",
                callback_data="activate_question_set"
            )],
            [InlineKeyboardButton(
                text="❌ Desactivar override",
                callback_data="deactivate_override"
            )],
            [InlineKeyboardButton(
                text="🔙 Volver",
                callback_data="admin_trivia_management"
            )]
        ])

        await callback.message.edit_text(
            "🎩 <b>Lucien:</b>\n\n"
            "<i>Los conjuntos de preguntas bajo nuestra tutela...</i>\n\n"
            f"Gestione los sets temáticos de preguntas de trivia.\n\n"
            f"Sets registrados: {len(sets)}",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    finally:
        service.close()
    await callback.answer()


# ==================== VER SETS ====================

@router.callback_query(F.data == "view_question_sets", lambda cb: is_admin(cb.from_user.id))
async def view_question_sets(callback: CallbackQuery):
    """Ver todos los QuestionSets"""
    service = QuestionSetService()
    try:
        sets = service.get_all_sets()

        if not sets:
            await callback.message.edit_text(
                "🎩 <b>Lucien:</b>\n\n"
                "<i>No hay sets de preguntas registrados.</i>\n\n"
                "Cree uno primero.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_question_sets")]
                ]),
                parse_mode="HTML"
            )
            await callback.answer()
            return

        lines = ["📋 <b>Sets de preguntas registrados:</b>\n"]

        keyboard_buttons = []
        for s in sets:
            status_parts = []
            if s.is_active:
                status_parts.append("✅ Activo")
            if s.is_override:
                status_parts.append("⚡ Override")
            status = " | ".join(status_parts) if status_parts else "❌ Inactivo"

            desc = s.description[:50] + "..." if s.description and len(s.description) > 50 else (s.description or "Sin descripción")
            lines.append(
                f"\n<b>{s.name}</b>\n"
                f"   📝 {desc}\n"
                f"   📁 {s.file_path}\n"
                f"   Estado: {status}\n"
            )
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"📖 {s.name}",
                    callback_data=f"view_qs_{s.id}"
                )
            ])

        text = "".join(lines)
        keyboard_buttons.append([
            InlineKeyboardButton(text="🔙 Volver", callback_data="admin_question_sets")
        ])

        await callback.message.edit_text(
            f"🎩 <b>Lucien:</b>\n\n{text}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons),
            parse_mode="HTML"
        )
    finally:
        service.close()
    await callback.answer()


# ==================== VER DETALLES SET ====================

@router.callback_query(F.data.startswith("view_qs_"), lambda cb: is_admin(cb.from_user.id))
async def view_question_set_details(callback: CallbackQuery, state: FSMContext):
    """Ver detalles de un QuestionSet específico"""
    set_id = int(callback.data.replace("view_qs_", ""))
    user_id = callback.from_user.id

    service = QuestionSetService()
    try:
        question_set = service.get_set_by_id(set_id)

        if not question_set:
            logger.warning(
                f"question_set_admin - view details failed: set not found: "
                f"user_id={user_id}, set_id={set_id}"
            )
            await callback.message.edit_text(
                "🎩 <b>Lucien:</b>\n\n"
                "<i>No se encontró el set de preguntas.</i>",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Volver", callback_data="view_question_sets")]
                ]),
                parse_mode="HTML"
            )
            await callback.answer()
            return

        status_parts = []
        if question_set.is_active:
            status_parts.append("✅ Activo")
        if question_set.is_override:
            status_parts.append("⚡ Override")
        status = " | ".join(status_parts) if status_parts else "❌ Inactivo"

        desc = question_set.description or "Sin descripción"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="⚡ Activar override",
                callback_data=f"activate_set_{question_set.id}"
            )],
            [InlineKeyboardButton(text="🔙 Volver", callback_data="view_question_sets")]
        ])

        await callback.message.edit_text(
            f"🎩 <b>Lucien:</b>\n\n"
            f"<b>{question_set.name}</b>\n\n"
            f"📝 <b>Descripción:</b> {desc}\n"
            f"📁 <b>Archivo:</b> <code>{question_set.file_path}</code>\n"
            f"📊 <b>Estado:</b> {status}\n"
            f"🆔 <b>ID:</b> {question_set.id}",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    finally:
        service.close()
    await callback.answer()


# ==================== CREAR SET ====================

@router.callback_query(F.data == "create_question_set", lambda cb: is_admin(cb.from_user.id))
async def create_question_set_start(callback: CallbackQuery, state: FSMContext):
    """Iniciar wizard de creación de QuestionSet"""
    await callback.message.edit_text(
        "🎩 <b>Lucien:</b>\n\n"
        "<i>Paso 1 de 3:</i> Ingrese el nombre del set\n\n"
        "Este nombre debe ser único. Ejemplo: <code>Primero de Mayo</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Cancelar", callback_data="admin_question_sets")]
        ]),
        parse_mode="HTML"
    )
    await state.set_state(QuestionSetStates.waiting_name)
    await callback.answer()


@router.message(QuestionSetStates.waiting_name, lambda msg: is_admin(msg.from_user.id))
async def create_question_set_name(message: Message, state: FSMContext):
    """Procesar nombre del set"""
    name = message.text.strip()

    if len(name) < 2:
        await message.answer(
            "🎩 <b>Lucien:</b>\n\n"
            "El nombre debe tener al menos 2 caracteres. Intente de nuevo:",
            parse_mode="HTML"
        )
        return

    if len(name) > 200:
        await message.answer(
            "🎩 <b>Lucien:</b>\n\n"
            "El nombre no puede exceder 200 caracteres. Intente de nuevo:",
            parse_mode="HTML"
        )
        return

    await state.update_data(name=name)

    await message.answer(
        "🎩 <b>Lucien:</b>\n\n"
        "<i>Paso 2 de 3:</i> Ingrese la descripción (opcional)\n\n"
        "Envíe <b>skip</b> para omitir o escriba una descripción.",
        parse_mode="HTML"
    )
    await state.set_state(QuestionSetStates.waiting_description)


@router.message(QuestionSetStates.waiting_description, lambda msg: is_admin(msg.from_user.id))
async def create_question_set_description(message: Message, state: FSMContext):
    """Procesar descripción del set"""
    text = message.text.strip()

    if text.lower() == "skip":
        await state.update_data(description=None)
    else:
        if len(text) > 1000:
            await message.answer(
                "🎩 <b>Lucien:</b>\n\n"
                "La descripción no puede exceder 1000 caracteres. Intente de nuevo:",
                parse_mode="HTML"
            )
            return
        await state.update_data(description=text)

    await message.answer(
        "🎩 <b>Lucien:</b>\n\n"
        "<i>Paso 3 de 3:</i> Ingrese la ruta del archivo JSON\n\n"
        "Ejemplo: <code>docs/question_sets/primero_de_mayo.json</code>",
        parse_mode="HTML"
    )
    await state.set_state(QuestionSetStates.waiting_file_path)


@router.message(QuestionSetStates.waiting_file_path, lambda msg: is_admin(msg.from_user.id))
async def create_question_set_file_path(message: Message, state: FSMContext):
    """Procesar ruta del archivo y confirmar"""
    file_path = message.text.strip()

    if not file_path:
        await message.answer(
            "🎩 <b>Lucien:</b>\n\n"
            "La ruta del archivo no puede estar vacía. Intente de nuevo:",
            parse_mode="HTML"
        )
        return

    if len(file_path) > 500:
        await message.answer(
            "🎩 <b>Lucien:</b>\n\n"
            "La ruta no puede exceder 500 caracteres. Intente de nuevo:",
            parse_mode="HTML"
        )
        return

    from pathlib import Path
    if not Path(file_path).exists():
        await message.answer(
            "🎩 <b>Lucien:</b>\n\n"
            "<i>El archivo no parece existir en la ruta indicada.</i>\n\n"
            "Por favor, verifique que el archivo JSON esté en el servidor e intente de nuevo:",
            parse_mode="HTML"
        )
        return

    data = await state.get_data()

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✓ Confirmar", callback_data="confirm_question_set")],
        [InlineKeyboardButton(text="✗ Cancelar", callback_data="admin_question_sets")]
    ])

    await message.answer(
        f"🎩 <b>Lucien:</b>\n\n"
        "<i>Confirmar creación del set:</i>\n\n"
        f"📋 <b>Nombre:</b> {data['name']}\n"
        f"📝 <b>Descripción:</b> {data.get('description') or 'Sin descripción'}\n"
        f"📁 <b>Archivo:</b> {file_path}",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

    await state.update_data(file_path=file_path)
    await state.set_state(QuestionSetStates.waiting_question_set_confirm)


@router.callback_query(F.data == "confirm_question_set", lambda cb: is_admin(cb.from_user.id))
async def confirm_question_set(callback: CallbackQuery, state: FSMContext):
    """Confirmar y guardar QuestionSet"""
    data = await state.get_data()
    user_id = callback.from_user.id

    service = QuestionSetService()
    try:
        # Verificar si ya existe un set con el mismo nombre
        if service.exists_by_name(data['name']):
            logger.warning(
                f"question_set_admin - create failed: duplicate name: "
                f"user_id={user_id}, name={data['name']}"
            )
            await callback.message.edit_text(
                "🎩 <b>Lucien:</b>\n\n"
                "<i>Ya existe un set con ese nombre.</i>\n\n"
                "Use un nombre diferente.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_question_sets")]
                ]),
                parse_mode="HTML"
            )
            await state.clear()
            await callback.answer()
            return

        # Crear el nuevo set
        new_set = service.create_set(
            name=data['name'],
            file_path=data['file_path'],
            description=data.get('description')
        )

        if new_set:
            logger.info(
                f"question_set_admin - created: "
                f"user_id={user_id}, set_id={new_set.id}, name={data['name']}"
            )

            await callback.message.edit_text(
                "🎩 <b>Lucien:</b>\n\n"
                f"<i>Set de preguntas creado con éxito.</i>\n\n"
                f"ID: {new_set.id}\n"
                f"Nombre: {new_set.name}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_question_sets")]
                ]),
                parse_mode="HTML"
            )
        else:
            await callback.message.edit_text(
                "🎩 <b>Lucien:</b>\n\n"
                "<i>Error al crear el set.</i>\n\n"
                "Intente de nuevo.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_question_sets")]
                ]),
                parse_mode="HTML"
            )
    finally:
        service.close()

    await state.clear()
    await callback.answer()


# ==================== ACTIVAR SET ====================

@router.callback_query(F.data == "activate_question_set", lambda cb: is_admin(cb.from_user.id))
async def activate_question_set_start(callback: CallbackQuery, state: FSMContext):
    """Mostrar lista de sets para activar"""
    service = QuestionSetService()
    try:
        sets = service.get_all_sets()

        if not sets:
            await callback.message.edit_text(
                "🎩 <b>Lucien:</b>\n\n"
                "<i>No hay sets de preguntas registrados.</i>\n\n"
                "Cree uno primero.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_question_sets")]
                ]),
                parse_mode="HTML"
            )
            await callback.answer()
            return

        keyboard_buttons = [
            [InlineKeyboardButton(
                text=f"{s.name} {'✅' if s.is_active and s.is_override else ''}",
                callback_data=f"activate_set_{s.id}"
            )]
            for s in sets
        ]
        keyboard_buttons.append([
            InlineKeyboardButton(text="🔙 Cancelar", callback_data="admin_question_sets")
        ])

        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        await callback.message.edit_text(
            "🎩 <b>Lucien:</b>\n\n"
            "<i>Seleccione el set a activar:</i>\n\n"
            "Solo un set puede tener override activo a la vez.",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    finally:
        service.close()

    await state.set_state(QuestionSetStates.waiting_set_to_activate)
    await callback.answer()


@router.callback_query(F.data.startswith("activate_set_"), lambda cb: is_admin(cb.from_user.id))
async def activate_question_set_confirm(callback: CallbackQuery, state: FSMContext):
    """Activar el set seleccionado"""
    set_id = int(callback.data.replace("activate_set_", ""))
    user_id = callback.from_user.id

    service = QuestionSetService()
    try:
        activated = service.activate_set(set_id)

        if activated:
            logger.info(
                f"question_set_admin - activated: "
                f"user_id={user_id}, set_id={set_id}, name={activated.name}"
            )

            await callback.message.edit_text(
                "🎩 <b>Lucien:</b>\n\n"
                f"<i>Set activado con éxito.</i>\n\n"
                f"ID: {activated.id}\n"
                f"Nombre: {activated.name}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_question_sets")]
                ]),
                parse_mode="HTML"
            )
        else:
            logger.warning(
                f"question_set_admin - activate failed: set not found: "
                f"user_id={user_id}, set_id={set_id}"
            )
            await callback.message.edit_text(
                "🎩 <b>Lucien:</b>\n\n"
                "<i>No se encontró el set.</i>",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_question_sets")]
                ]),
                parse_mode="HTML"
            )
    finally:
        service.close()

    await state.clear()
    await callback.answer()


# ==================== DESACTIVAR OVERRIDE ====================

@router.callback_query(F.data == "deactivate_override", lambda cb: is_admin(cb.from_user.id))
async def deactivate_override(callback: CallbackQuery):
    """Desactivar override en todos los sets"""
    user_id = callback.from_user.id

    service = QuestionSetService()
    try:
        updated = service.deactivate_all_overrides()

        logger.info(
            f"question_set_admin - deactivate_override: "
            f"user_id={user_id}, sets_updated={updated}"
        )

        await callback.message.edit_text(
            "🎩 <b>Lucien:</b>\n\n"
            f"<i>Override desactivado en {updated} set(s).</i>\n\n"
            "El sistema volverá al comportamiento automático.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_question_sets")]
            ]),
            parse_mode="HTML"
        )
    finally:
        service.close()
    await callback.answer()