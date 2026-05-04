"""
Handlers de Admin - Trivia Discount System

Handlers para la gestión del sistema de promociones por racha de trivia.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from typing import Optional
from services.trivia_discount_service import TriviaDiscountService
from services.promotion_service import PromotionService
from services.question_set_service import QuestionSetService
from services.user_service import UserService
from models.models import DiscountCodeStatus
from handlers.admin_handlers import is_admin
import logging

logger = logging.getLogger(__name__)
router = Router()


# Estados para FSM
class TriviaDiscountStates(StatesGroup):
    waiting_promotion_type = State()
    waiting_promotion = State()
    waiting_custom_description = State()
    waiting_discount_percentage = State()
    waiting_required_streak = State()
    waiting_tier_mode = State()          # Nuevo: single o multi tier
    waiting_discount_tiers = State()     # Nuevo: JSON de tiers
    waiting_max_codes = State()
    waiting_start_date = State()
    waiting_end_date = State()
    waiting_duration = State()
    waiting_auto_reset = State()
    waiting_reset_cycles = State()
    waiting_question_set = State()
    waiting_confirmation = State()
    waiting_extend_duration = State()


# ==================== MENÚ PRINCIPAL ====================

@router.callback_query(F.data == "admin_trivia_discount", lambda cb: is_admin(cb.from_user.id))
async def admin_trivia_discount_menu(callback: CallbackQuery):
    """Menú principal de gestión de promociones por racha"""
    service = TriviaDiscountService()
    try:
        all_configs = service.get_all_trivia_promotion_configs()
        active = [c for c in all_configs if c.status == 'active']
        paused = [c for c in all_configs if c.status == 'paused']
        expired = [c for c in all_configs if c.status == 'expired']
        completed = [c for c in all_configs if c.status == 'completed']

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="➕ Crear promoción de trivia",
                callback_data="create_trivia_discount"
            )]
        ])

        # Mostrar todas las categorías con conteos
        if all_configs:
            status_lines = []
            if active:
                status_lines.append(f"✅ Activas: {len(active)}")
            if paused:
                status_lines.append(f"⏸️ Pausadas: {len(paused)}")
            if expired:
                status_lines.append(f"🔚 Terminadas: {len(expired)}")
            if completed:
                status_lines.append(f"📭 Completadas: {len(completed)}")

            status_text = "\n".join(status_lines)
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(
                    text="📋 Ver todas las promociones",
                    callback_data="view_trivia_discounts"
                )
            ])
        else:
            status_text = "\n<i>No hay configuraciones creadas.</i>"

        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text="🔙 Volver",
                callback_data="admin_trivia_management"
            )
        ])

        await callback.message.edit_text(
            "🎩 <b>Lucien:</b>\n\n"
            "<i>Las recompensas que el conocimiento merece...</i>\n\n"
            f"{status_text}\n\n"
            "Configure promociones que se desbloquean al alcanzar rachas en trivia.",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    finally:
        pass
    await callback.answer()


# ==================== CREAR CONFIGURACIÓN (WIZARD) ====================

@router.callback_query(F.data == "create_trivia_discount", lambda cb: is_admin(cb.from_user.id))
async def create_trivia_discount_start(callback: CallbackQuery, state: FSMContext):
    """Paso 1: Seleccionar tipo de promoción"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🏪 Usar promoción existente",
            callback_data="select_promo_type_existing"
        )],
        [InlineKeyboardButton(
            text="✨ Crear promoción independiente",
            callback_data="select_promo_type_independent"
        )],
        [InlineKeyboardButton(text="🔙 Cancelar", callback_data="admin_trivia_discount")]
    ])

    await callback.message.edit_text(
        "🎩 <b>Lucien:</b>\n\n"
        "<i>Paso 1 de 6:</i> Seleccione el tipo de promoción\n\n"
        "🏪 <b>Promoción existente:</b> Vincular a una promoción comercial del catálogo\n"
        "✨ <b>Promoción independiente:</b> Crear una trivia sin promoción comercial (ej: descuentos eventales)",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(TriviaDiscountStates.waiting_promotion_type)
    await callback.answer()


@router.callback_query(F.data.regex(r"^select_promo_\d+$"), lambda cb: is_admin(cb.from_user.id))
async def create_trivia_discount_promo(callback: CallbackQuery, state: FSMContext):
    """Paso 2: Porcentaje de descuento"""
    promotion_id = int(callback.data.replace("select_promo_", ""))

    # Guardar promoción seleccionada
    await state.update_data(promotion_id=promotion_id)

    await callback.message.edit_text(
        "🎩 <b>Lucien:</b>\n\n"
        "<i>Paso 2 de 6:</i> Ingrese el porcentaje de descuento (0-100)\n\n"
        "Ejemplo: 20 para 20% de descuento",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Cancelar", callback_data="admin_trivia_discount")]
        ]),
        parse_mode="HTML"
    )
    await state.set_state(TriviaDiscountStates.waiting_discount_percentage)
    await callback.answer()


@router.message(TriviaDiscountStates.waiting_discount_percentage, lambda msg: is_admin(msg.from_user.id))
async def create_trivia_discount_percentage(message: Message, state: FSMContext):
    """Procesar porcentaje"""
    try:
        percentage = int(message.text.strip())
        if not 0 <= percentage <= 100:
            await message.answer("El porcentaje debe ser entre 0 y 100. Intente de nuevo:")
            return
        await state.update_data(discount_percentage=percentage)

        await message.answer(
            "🎩 <b>Lucien:</b>\n\n"
            "<i>Paso 3 de 6:</i> Ingrese la racha requerida\n\n"
            "Número mínimo de respuestas correctas consecutivas (mínimo 3)",
            parse_mode="HTML"
        )
        await state.set_state(TriviaDiscountStates.waiting_required_streak)
    except ValueError:
        await message.answer("Por favor ingrese un número válido:")


@router.message(TriviaDiscountStates.waiting_required_streak, lambda msg: is_admin(msg.from_user.id))
async def create_trivia_discount_streak(message: Message, state: FSMContext):
    """Procesar racha requerida y preguntar por modo de tiers"""
    try:
        streak = int(message.text.strip())
        if streak < 3:
            await message.answer("La racha debe ser al menos 3. Intente de nuevo:")
            return
        await state.update_data(required_streak=streak)

        # Preguntar si quiere un solo tier o múltiples
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="1️⃣ Un solo nivel",
                callback_data="tier_mode_single"
            )],
            [InlineKeyboardButton(
                text="2️⃣ Múltiples niveles",
                callback_data="tier_mode_multi"
            )],
            [InlineKeyboardButton(text="🔙 Cancelar", callback_data="admin_trivia_discount")]
        ])

        await message.answer(
            "🎩 <b>Lucien:</b>\n\n"
            "<i>Paso 3b:</i> Configuración de niveles de descuento\n\n"
            "1️⃣ <b>Un solo nivel:</b> Un único descuento al alcanzar la racha\n"
            "2️⃣ <b>Múltiples niveles:</b> Varios descuentos progresivos (ej: 5=50%, 10=75%, 15=100%)",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await state.set_state(TriviaDiscountStates.waiting_tier_mode)
    except ValueError:
        await message.answer("Por favor ingrese un número válido:")


@router.callback_query(F.data == "tier_mode_single", lambda cb: is_admin(cb.from_user.id))
async def tier_mode_single(callback: CallbackQuery, state: FSMContext):
    """Usuario eligió un solo tier - usar valores por defecto"""
    data = await state.get_data()

    # Crear tier único con los valores por defecto
    discount_tiers = [{
        'streak': data.get('required_streak', 5),
        'discount': data.get('discount_percentage', 50)
    }]
    await state.update_data(discount_tiers=discount_tiers)

    # Continuar al paso de max_codes
    await callback.message.edit_text(
        "🎩 <b>Lucien:</b>\n\n"
        "<i>Paso 4 de 6:</i> Ingrese el límite de códigos\n\n"
        "Número máximo de códigos que se pueden reclamar (mínimo 1)",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Cancelar", callback_data="admin_trivia_discount")]
        ]),
        parse_mode="HTML"
    )
    await state.set_state(TriviaDiscountStates.waiting_max_codes)
    await callback.answer()


@router.callback_query(F.data == "tier_mode_multi", lambda cb: is_admin(cb.from_user.id))
async def tier_mode_multi(callback: CallbackQuery, state: FSMContext):
    """Usuario eligió múltiples tiers - solicitar JSON"""
    await callback.message.edit_text(
        "🎩 <b>Lucien:</b>\n\n"
        "<i>Paso 3c:</i> Ingrese los niveles de descuento en formato JSON\n\n"
        "Ejemplo:\n"
        "<code>[{\"streak\": 5, \"discount\": 50}, {\"streak\": 10, \"discount\": 75}, {\"streak\": 15, \"discount\": 100}]</code>\n\n"
        "• streak: respuestas correctas para desbloquear\n"
        "• discount: porcentaje de descuento (0-100)\n"
        "• Ordene por streak ascendente\n"
        "• El último tier DEBE ser 100%",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Cancelar", callback_data="admin_trivia_discount")]
        ]),
        parse_mode="HTML"
    )
    await state.set_state(TriviaDiscountStates.waiting_discount_tiers)
    await callback.answer()


@router.message(TriviaDiscountStates.waiting_discount_tiers, lambda msg: is_admin(msg.from_user.id))
async def process_discount_tiers(message: Message, state: FSMContext):
    """Procesar y validar tiers JSON"""
    import json as json_lib

    text = message.text.strip()
    try:
        tiers = json_lib.loads(text)
    except json_lib.JSONDecodeError:
        await message.answer(
            "Formato JSON inválido. Intente de nuevo:\n"
            "Ejemplo: <code>[{\"streak\": 5, \"discount\": 50}, {\"streak\": 10, \"discount\": 100}]</code>",
            parse_mode="HTML"
        )
        return

    # Validar usando el servicio
    service = TriviaDiscountService()
    is_valid, error_msg = service.validate_discount_tiers(tiers)
    service.close()

    if not is_valid:
        await message.answer(
            f"Error en los tiers: {error_msg}\n\n"
            "Intente de nuevo:",
            parse_mode="HTML"
        )
        return

    await state.update_data(discount_tiers=tiers)

    # Continuar al paso de max_codes
    await message.answer(
        "🎩 <b>Lucien:</b>\n\n"
        "<i>Paso 4 de 6:</i> Ingrese el límite de códigos\n\n"
        "Número máximo de códigos que se pueden reclamar (mínimo 1)",
        parse_mode="HTML"
    )
    await state.set_state(TriviaDiscountStates.waiting_max_codes)


@router.message(TriviaDiscountStates.waiting_max_codes, lambda msg: is_admin(msg.from_user.id))
async def create_trivia_discount_max_codes(message: Message, state: FSMContext):
    """Procesar límite de códigos"""
    try:
        max_codes = int(message.text.strip())
        if max_codes < 1:
            await message.answer("El límite debe ser al menos 1. Intente de nuevo:")
            return
        await state.update_data(max_codes=max_codes)

        # Nuevo paso: Elegir tipo de vigencia
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="📅 Fechas fijas",
                callback_data="duration_type_fixed"
            )],
            [InlineKeyboardButton(
                text="⏰ Duración relativa (min/h/d)",
                callback_data="duration_type_relative"
            )],
            [InlineKeyboardButton(text="🔙 Cancelar", callback_data="admin_trivia_discount")]
        ])

        await message.answer(
            "🎩 <b>Lucien:</b>\n\n"
            "<i>Paso 5 de 6:</i> Seleccione el tipo de vigencia\n\n"
            "📅 <b>Fechas fijas:</b> Fecha de inicio y fin específica\n"
            "⏰ <b>Duración relativa:</b> Ej: 30min, 2h, 1d (contador regresivo)",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await state.set_state(TriviaDiscountStates.waiting_duration)
    except ValueError:
        await message.answer("Por favor ingrese un número válido:")


def _parse_duration(text: str) -> Optional[int]:
    """Parsea texto de duración a minutos. Formatos: 30m, 30min, 2h, 2hr, 1d, 1day"""
    text = text.strip().lower()
    try:
        if text.endswith('min') or text.endswith('m'):
            return int(text.replace('min', '').replace('m', '').strip())
        elif text.endswith('hr') or text.endswith('h'):
            return int(text.replace('hr', '').replace('h', '').strip()) * 60
        elif text.endswith('d') or text.endswith('day'):
            return int(text.replace('day', '').replace('d', '').strip()) * 1440
        else:
            # Asumir minutos
            return int(text)
    except (ValueError, TypeError):
        return None


@router.callback_query(F.data == "duration_type_fixed", lambda cb: is_admin(cb.from_user.id))
async def duration_type_fixed(callback: CallbackQuery, state: FSMContext):
    """Usuario eligió fechas fijas"""
    await state.update_data(duration_type='fixed', duration_minutes=None)

    await callback.message.edit_text(
        "🎩 <b>Lucien:</b>\n\n"
        "<i>Paso 5b:</i> Fechas de vigencia (opcional)\n\n"
        "Envíe las fechas en formato:\n"
        "<code>YYYY-MM-DD YYYY-MM-DD</code>\n\n"
        "O envíe <b>skip</b> para sin límite de tiempo",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Cancelar", callback_data="admin_trivia_discount")]
        ]),
        parse_mode="HTML"
    )
    await state.set_state(TriviaDiscountStates.waiting_start_date)
    await callback.answer()


@router.callback_query(F.data == "duration_type_relative", lambda cb: is_admin(cb.from_user.id))
async def duration_type_relative(callback: CallbackQuery, state: FSMContext):
    """Usuario eligió duración relativa"""
    await state.update_data(duration_type='relative')

    await callback.message.edit_text(
        "🎩 <b>Lucien:</b>\n\n"
        "<i>Paso 5b:</i> Ingrese la duración\n\n"
        "Formatos aceptados:\n"
        "• <code>30</code> → 30 minutos\n"
        "• <code>30m</code> o <code>30min</code> → 30 minutos\n"
        "• <code>2h</code> o <code>2hr</code> → 2 horas\n"
        "• <code>1d</code> o <code>1day</code> → 1 día\n\n"
        "La promoción começará a contar cuando se active.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Cancelar", callback_data="admin_trivia_discount")]
        ]),
        parse_mode="HTML"
    )
    await state.set_state(TriviaDiscountStates.waiting_start_date)
    await callback.answer()


@router.message(TriviaDiscountStates.waiting_start_date, lambda msg: is_admin(msg.from_user.id))
async def create_trivia_discount_dates(message: Message, state: FSMContext):
    """Procesar fechas o duración relativa"""
    data = await state.get_data()
    duration_type = data.get('duration_type')

    # Debug: registrar el tipo de duración
    logger.info(f"create_trivia_discount_dates - duration_type: {duration_type}, message: {message.text}")

    # Si duration_type es 'relative' o no está definido Y el mensaje parece ser duración
    if duration_type == 'relative':
        # Procesar duración relativa
        duration = _parse_duration(message.text.strip())
        if not duration or duration < 1:
            await message.answer(
                "Duración inválida. Use formatos como: 30m, 2h, 1d\n"
                "Intente de nuevo:",
                parse_mode="HTML"
            )
            return
        await state.update_data(start_date=None, end_date=None, duration_minutes=duration)
    elif duration_type == 'fixed':
        # Procesar fechas fijas
        text = message.text.strip().lower()
        if text == "skip":
            await state.update_data(start_date=None, end_date=None, duration_minutes=None)
        else:
            try:
                parts = text.split()
                if len(parts) != 2:
                    raise ValueError("Formato inválido")

                from datetime import datetime
                start = datetime.strptime(parts[0], "%Y-%m-%d")
                end = datetime.strptime(parts[1], "%Y-%m-%d")

                await state.update_data(start_date=start, end_date=end, duration_minutes=None)
            except Exception:
                await message.answer(
                    "Formato inválido. Envíe:\n"
                    "<code>YYYY-MM-DD YYYY-MM-DD</code>\n"
                    "o <b>skip</b> para omitir",
                    parse_mode="HTML"
                )
                return
    else:
        #duration_type no está definido - tratar como duración relativa por defecto
        duration = _parse_duration(message.text.strip())
        if duration and duration > 0:
            await state.update_data(duration_type='relative', start_date=None, end_date=None, duration_minutes=duration)
        else:
            await message.answer(
                "Formato inválido. Seleccione:\n"
                "• Duración: 30m, 2h, 1d\n"
                "• O fechas: YYYY-MM-DD YYYY-MM-DD\n"
                "• O skip para omitir",
                parse_mode="HTML"
            )
            return

    # Verificar si es duración relativa para preguntar por reinicio automático
    data = await state.get_data()
    if data.get('duration_type') == 'relative' and data.get('duration_minutes'):
        # Preguntar por reinicio automático
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Sí", callback_data="auto_reset_yes")],
            [InlineKeyboardButton(text="❌ No", callback_data="auto_reset_no")],
            [InlineKeyboardButton(text="🔙 Cancelar", callback_data="admin_trivia_discount")]
        ])

        await message.answer(
            "🎩 <b>Lucien:</b>\n\n"
            "<i>Pregunta adicional:</i> ¿Desea habilitar el <b>reinicio automático</b>?\n\n"
            "Cuando el tiempo expire, el contador se reiniciará al <b>25%</b> del tiempo original.\n"
            "Por ejemplo: 1 hora → 15 minutos.\n\n"
            "Esto permite múltiples ciclos de juego.",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await state.set_state(TriviaDiscountStates.waiting_auto_reset)
        return

    # Si no es duración relativa, ir directo a selección de question set
    await state.update_data(auto_reset_enabled=False, max_reset_cycles=None)
    await show_question_set_selection(message, state)


# ==================== REINICIO AUTOMÁTICO ====================

@router.callback_query(F.data == "auto_reset_yes", lambda cb: is_admin(cb.from_user.id))
async def auto_reset_yes(callback: CallbackQuery, state: FSMContext):
    """Usuario eligió habilitar reinicio automático"""
    await state.update_data(auto_reset_enabled=True)

    await callback.message.edit_text(
        "🎩 <b>Lucien:</b>\n\n"
        "Ingrese el <b>número máximo de ciclos de reinicio</b> permitidos.\n\n"
        "Cada vez que el tiempo expire, se reiniciará al 25% del tiempo original.\n"
        "Cuando se completen todos los ciclos, la promoción finalizará.\n\n"
        "Ejemplo: <code>3</code> ciclos",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Cancelar", callback_data="admin_trivia_discount")]
        ]),
        parse_mode="HTML"
    )
    await state.set_state(TriviaDiscountStates.waiting_reset_cycles)
    await callback.answer()


@router.callback_query(F.data == "auto_reset_no", lambda cb: is_admin(cb.from_user.id))
async def auto_reset_no(callback: CallbackQuery, state: FSMContext):
    """Usuario eligió NO habilitar reinicio automático"""
    await state.update_data(auto_reset_enabled=False, max_reset_cycles=None)
    await show_question_set_selection(callback.message, state)
    await callback.answer()


@router.message(TriviaDiscountStates.waiting_reset_cycles, lambda msg: is_admin(msg.from_user.id))
async def process_reset_cycles(message: Message, state: FSMContext):
    """Procesar número de ciclos de reinicio"""
    try:
        cycles = int(message.text.strip())
        if cycles < 1:
            await message.answer("El número de ciclos debe ser al menos 1. Intente de nuevo:")
            return
        await state.update_data(max_reset_cycles=cycles)
        await show_question_set_selection(message, state)
    except ValueError:
        await message.answer("Por favor ingrese un número válido:")


async def show_question_set_selection(message: Message, state: FSMContext):
    """Muestra la pantalla de selección de QuestionSet"""
    qs_service = QuestionSetService()
    sets = qs_service.get_all_sets()
    qs_service.close()

    keyboard_buttons = []
    if sets:
        for s in sets:
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"📚 {s.name}",
                    callback_data=f"select_qs_{s.id}"
                )
            ])
    keyboard_buttons.append([
        InlineKeyboardButton(
            text="🔄 Ninguno (usar default)",
            callback_data="select_qs_none"
    )])
    keyboard_buttons.append([
        InlineKeyboardButton(text="🔙 Cancelar", callback_data="admin_trivia_discount")
    ])

    await message.answer(
        "🎩 <b>Lucien:</b>\n\n"
        "<i>Pregunta adicional:</i> Seleccione el set de preguntas de trivia\n\n"
        "📚 <b>Set temático:</b> Las preguntas de trivia serán de este tema durante la promoción\n"
        "🔄 <b>Ninguno:</b> Usará las preguntas por defecto",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons),
        parse_mode="HTML"
    )
    await state.set_state(TriviaDiscountStates.waiting_question_set)


@router.callback_query(F.data.startswith("select_qs_"), lambda cb: is_admin(cb.from_user.id))
async def select_question_set(callback: CallbackQuery, state: FSMContext):
    """Procesar selección de QuestionSet"""
    data = callback.data.replace("select_qs_", "")
    if data == "none":
        await state.update_data(question_set_id=None)
    else:
        qs_id = int(data)
        await state.update_data(question_set_id=qs_id)
    await show_confirmation(callback.message, state)
    await callback.answer()


async def show_confirmation(message: Message, state: FSMContext):
    """Muestra la pantalla de confirmación"""
    data = await state.get_data()

    # Determinar tipo de promoción
    if data.get('promotion_id'):
        promo_service = PromotionService()
        try:
            promo = promo_service.get_promotion(data['promotion_id'])
            promo_name = promo.name if promo else "Desconocida"
        finally:
            promo_service.close()
        promo_info = f"🏪 {promo_name}"
    else:
        promo_info = f"✨ {data.get('custom_description', 'N/A')}"

    # Construir info de vigencia
    duration_type = data.get('duration_type')
    if duration_type == 'relative':
        duration_val = data.get('duration_minutes', 0)
        if duration_val >= 1440:
            days = duration_val // 1440
            vigencia = f"⏰ {days} día(s)"
        elif duration_val >= 60:
            hours = duration_val // 60
            mins = duration_val % 60
            vigencia = f"⏰ {hours}h {mins}min" if mins > 0 else f"⏰ {hours} horas"
        else:
            vigencia = f"⏰ {duration_val} minutos"
    else:
        start = data.get('start_date')
        end = data.get('end_date')
        if start and end:
            vigencia = f"📅 {start.strftime('%Y-%m-%d')} - {end.strftime('%Y-%m-%d')}"
        elif start:
            vigencia = f"📅 Desde {start.strftime('%Y-%m-%d')}"
        else:
            vigencia = "📅 Sin límite"

    # Info de reinicio automático
    if data.get('auto_reset_enabled') and data.get('max_reset_cycles'):
        reset_info = f"🔄 Activado ({data['max_reset_cycles']} ciclos máx.)"
    elif data.get('auto_reset_enabled'):
        reset_info = "🔄 Activado (ilimitado)"
    else:
        reset_info = "❌ Desactivado"

    # Info de question set
    qs_id = data.get('question_set_id')
    if qs_id:
        qs_service = QuestionSetService()
        qs = qs_service.get_set_by_id(qs_id)
        qs_service.close()
        qs_info = f"📚 {qs.name}" if qs else f"📚 ID:{qs_id}"
    else:
        qs_info = "🔄 Default"

    # Info de tiers
    tiers = data.get('discount_tiers')
    if tiers and len(tiers) > 0:
        if len(tiers) == 1:
            tiers_info = f"🔥 <b>Nivel único:</b> {tiers[0]['streak']} respuestas = {tiers[0]['discount']}%\n"
        else:
            tiers_info = "🔥 <b>Niveles de descuento:</b>\n"
            for i, tier in enumerate(tiers, 1):
                is_last = (i == len(tiers))
                bonus = " (GRATIS)" if is_last and tier['discount'] == 100 else ""
                tiers_info += f"   {i}. {tier['streak']} respuestas → {tier['discount']}%{bonus}\n"
    else:
        tiers_info = f"🔥 <b>Racha requerida:</b> {data['required_streak']} respuestas\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✓ Confirmar", callback_data="confirm_trivia_discount")],
        [InlineKeyboardButton(text="✗ Cancelar", callback_data="admin_trivia_discount")]
    ])

    await message.answer(
        f"🎩 <b>Lucien:</b>\n\n"
        "<i>Paso 7 de 7:</i> Confirmar configuración\n\n"
        f"📋 <b>Promoción:</b> {promo_info}\n"
        f"🎫 <b>Códigos máximo:</b> {data['max_codes']}\n"
        f"{tiers_info}"
        f"⏱️ <b>Vigencia:</b> {vigencia}\n"
        f"🔁 <b>Reinicio auto:</b> {reset_info}\n"
        f"📚 <b>Set de trivia:</b> {qs_info}",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(TriviaDiscountStates.waiting_confirmation)


@router.callback_query(F.data == "select_promo_type_existing", lambda cb: is_admin(cb.from_user.id))
async def create_trivia_discount_existing_promo(callback: CallbackQuery, state: FSMContext):
    """Mostrar lista de promociones existentes"""
    promo_service = PromotionService()
    try:
        promotions = promo_service.get_active_promotions()
    finally:
        promo_service.close()

    if not promotions:
        await callback.message.edit_text(
            "🎩 <b>Lucien:</b>\n\n"
            "<i>No hay promociones comerciales activas.</i>\n\n"
            "Cree una promoción primero en el panel de promociones.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_trivia_discount")]
            ]),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"{p.name} ({p.price_display})",
            callback_data=f"select_promo_{p.id}"
        )]
        for p in promotions
    ])
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="🔙 Cancelar", callback_data="admin_trivia_discount")
    ])

    await callback.message.edit_text(
        "🎩 <b>Lucien:</b>\n\n"
        "<i>Paso 1a:</i> Seleccione la promoción comercial\n"
        "que se aplicará al código de descuento.",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(TriviaDiscountStates.waiting_promotion)
    await callback.answer()


@router.callback_query(F.data == "select_promo_type_independent", lambda cb: is_admin(cb.from_user.id))
async def create_trivia_discount_independent_promo(callback: CallbackQuery, state: FSMContext):
    """Solicitar descripción para promoción independiente"""
    await callback.message.edit_text(
        "🎩 <b>Lucien:</b>\n\n"
        "<i>Paso 1b:</i> Ingrese la descripción de la promoción\n\n"
        "Esta descripción se mostrará al usuario cuando desbloquee el código.\n"
        "Ejemplo: <code>2x1 en fotos de Srta. Kinky</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Cancelar", callback_data="admin_trivia_discount")]
        ]),
        parse_mode="HTML"
    )
    await state.set_state(TriviaDiscountStates.waiting_custom_description)
    await callback.answer()


@router.message(TriviaDiscountStates.waiting_custom_description, lambda msg: is_admin(msg.from_user.id))
async def create_trivia_discount_custom_description(message: Message, state: FSMContext):
    """Procesar descripción personalizada"""
    description = message.text.strip()
    if len(description) < 3:
        await message.answer("La descripción debe tener al menos 3 caracteres:")
        return
    if len(description) > 500:
        await message.answer("La descripción no puede exceder 500 caracteres:")
        return

    await state.update_data(custom_description=description)

    await message.answer(
        "🎩 <b>Lucien:</b>\n\n"
        "<i>Paso 2 de 6:</i> Ingrese el porcentaje de descuento (0-100)\n\n"
        "Ejemplo: 20 para 20% de descuento",
        parse_mode="HTML"
    )
    await state.set_state(TriviaDiscountStates.waiting_discount_percentage)


@router.callback_query(F.data == "confirm_trivia_discount", lambda cb: is_admin(cb.from_user.id))
async def create_trivia_discount_confirm(callback: CallbackQuery, state: FSMContext):
    """Confirmar y crear configuración"""
    data = await state.get_data()
    user_id = callback.from_user.id

    service = TriviaDiscountService()
    config = service.create_trivia_promotion_config(
        name=f"Trivia {data.get('promotion_id', data.get('custom_description', 'Ind'))[:30]}",
        promotion_id=data.get('promotion_id'),
        discount_percentage=data['discount_percentage'],
        required_streak=data['required_streak'],
        max_codes=data['max_codes'],
        start_date=data.get('start_date'),
        end_date=data.get('end_date'),
        created_by=user_id,
        custom_description=data.get('custom_description'),
        duration_minutes=data.get('duration_minutes'),
        auto_reset_enabled=data.get('auto_reset_enabled', False),
        max_reset_cycles=data.get('max_reset_cycles'),
        question_set_id=data.get('question_set_id'),
        discount_tiers=data.get('discount_tiers')
    )

    if config:
        # Si es duración relativa, iniciar automáticamente
        started = False
        if data.get('duration_minutes'):
            started = service.start_trivia_promotion(config.id)

        duration_info = ""
        if data.get('duration_minutes'):
            duration_val = data['duration_minutes']
            if duration_val >= 60:
                duration_info = f"\n⏱️ Duración: {duration_val // 60}h (iniciada)" if started else f"\n⏱️ Duración: {duration_val // 60}h"
            else:
                duration_info = f"\n⏱️ Duración: {duration_val} min (iniciada)" if started else f"\n⏱️ Duración: {duration_val} min"

        await callback.message.edit_text(
            "🎩 <b>Lucien:</b>\n\n"
            f"<i>Configuración creada con éxito.</i>\n\n"
            f"ID: {config.id}\n"
            f"Descuento: {config.discount_percentage}%\n"
            f"Racha: {config.required_streak}\n"
            f"Códigos: {config.max_codes}{duration_info}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_trivia_discount")]
            ]),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            "🎩 <b>Lucien:</b>\n\n"
            "<i>Error al crear la configuración.</i>\n\n"
            "Intente de nuevo.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_trivia_discount")]
            ]),
            parse_mode="HTML"
        )

    await state.clear()
    await callback.answer()


# ==================== VER CONFIGURACIONES ====================

@router.callback_query(F.data == "view_trivia_discounts", lambda cb: is_admin(cb.from_user.id))
async def view_trivia_discounts(callback: CallbackQuery):
    """Ver configuraciones (todas, activas e inactivas)"""
    service = TriviaDiscountService()
    try:
        # Obtener TODAS las configs (no solo activas)
        all_configs = service.get_all_trivia_promotion_configs()
        active_configs = [c for c in all_configs if c.is_active]

        if not all_configs:
            await callback.message.edit_text(
                "🎩 <b>Lucien:</b>\n\n"
                "<i>No hay configuraciones creadas.</i>",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_trivia_discount")]
                ]),
                parse_mode="HTML"
            )
            await callback.answer()
            return

        # Mostrar siempre la primera (índice 0 del message group)
        config = all_configs[0]
        stats = service.get_discount_stats(config.id)

        # Determinar estado basado en status
        status_labels = {
            'active': '✅ Activa',
            'paused': '⏸️ Pausada',
            'expired': '🔚 Terminada',
            'completed': '📭 Completada'
        }
        status_text = status_labels.get(config.status, '❓ Desconocido')

        # Construir botones según el tipo de vigencia
        keyboard_buttons = [
            [InlineKeyboardButton(
                text="📊 Ver códigos",
                callback_data=f"view_codes_{config.id}"
            )]
        ]

        # Si es duración relativa, mostrar tiempo restante y botón de extender
        if service.is_duration_based(config):
            remaining = service.get_time_remaining_formatted(config.id)
            # Info de ciclos de reinicio automático
            if config.auto_reset_enabled and config.max_reset_cycles:
                cycles_info = f" | 🔄 Ciclo {config.reset_count}/{config.max_reset_cycles}"
            elif config.auto_reset_enabled:
                cycles_info = f" | 🔄 Ciclo {config.reset_count}/∞"
            else:
                cycles_info = ""
            time_info = f"\n⏱️ Tiempo: {remaining}{cycles_info}"
            if config.status == 'active':
                keyboard_buttons.append([
                    InlineKeyboardButton(
                        text="⏰ Extender",
                        callback_data=f"extend_duration_{config.id}"
                    )
                ])
        else:
            # Mostrar fechas de vigencia
            if config.start_date and config.end_date:
                time_info = f"\n📅 {config.start_date.strftime('%Y-%m-%d')} - {config.end_date.strftime('%Y-%m-%d')}"
            elif config.start_date:
                time_info = f"\n📅 Desde {config.start_date.strftime('%Y-%m-%d')}"
            elif config.end_date:
                time_info = f"\n📅 Hasta {config.end_date.strftime('%Y-%m-%d')}"
            else:
                time_info = ""

        # Botones según estado
        if config.status == 'active':
            keyboard_buttons.extend([
                [InlineKeyboardButton(
                    text="⏸️ Pausar",
                    callback_data=f"pause_trivia_{config.id}"
                )],
                [InlineKeyboardButton(
                    text="🗑️ Eliminar",
                    callback_data=f"delete_trivia_{config.id}"
                )]
            ])
        elif config.status in ('paused', 'expired'):
            keyboard_buttons.extend([
                [InlineKeyboardButton(
                    text="▶️ Reanudar",
                    callback_data=f"resume_trivia_{config.id}"
                )],
                [InlineKeyboardButton(
                    text="🗑️ Eliminar",
                    callback_data=f"delete_trivia_{config.id}"
                )]
            ])
        else:
            # completed u otro estado - solo eliminar
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text="🗑️ Eliminar",
                    callback_data=f"delete_trivia_{config.id}"
                )]
            )

        keyboard_buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="admin_trivia_discount")])

        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        promo = config.promotion
        promo_info = f"🏪 {promo.name}" if promo else f"✨ {config.custom_description or 'N/A'}"
        status_line = f"\n📌 Estado: {status_text}" if status_text else ""

        await callback.message.edit_text(
            f"🎫 <b>{config.name}</b>{status_line}\n\n"
            f"📋 {promo_info}\n"
            f"💰 Descuento: {config.discount_percentage}%\n"
            f"🔥 Racha: {config.required_streak}\n"
            f"🎫 Códigos: {stats['available']} disponibles / {config.max_codes} total\n"
            f"📊 Usados: {stats['used']} ({stats['used_percentage']}%){time_info}",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    finally:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("view_codes_"), lambda cb: is_admin(cb.from_user.id))
async def view_discount_codes(callback: CallbackQuery):
    """Ver códigos de una configuración"""
    config_id = int(callback.data.replace("view_codes_", ""))
    service = TriviaDiscountService()

    try:
        codes = service.get_codes_by_config(config_id)
        config = service.get_trivia_promotion_config(config_id)

        if not codes:
            await callback.message.edit_text(
                "🎩 <b>Lucien:</b>\n\n"
                "<i>No hay códigos generados aún.</i>",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Volver", callback_data="view_trivia_discounts")]
                ]),
                parse_mode="HTML"
            )
            await callback.answer()
            return

        # Agrupar códigos por estado
        active_codes = [c for c in codes if c.status == DiscountCodeStatus.ACTIVE]
        used_codes = [c for c in codes if c.status == DiscountCodeStatus.USED]
        other_codes = [c for c in codes if c.status not in [DiscountCodeStatus.ACTIVE, DiscountCodeStatus.USED]]

        # Construir mensaje con cada código y sus acciones
        text_parts = ["🎫 <b>Códigos de descuento</b>\n"]

        if active_codes:
            text_parts.append("\n🟢 <b>Activos:</b>")
            for i, code in enumerate(active_codes, 1):
                user_info = code.username or code.first_name or f"ID:{code.user_id}"
                text_parts.append(f"\n{i}. <code>{code.code}</code> - {user_info}")
                text_parts.append(f"   [ACTIVO]")

        if used_codes:
            text_parts.append("\n✅ <b>Usados:</b>")
            for i, code in enumerate(used_codes, 1):
                user_info = code.username or code.first_name or f"ID:{code.user_id}"
                text_parts.append(f"\n{i}. <code>{code.code}</code> - {user_info}")
                text_parts.append(f"   [USADO]")

        if other_codes:
            text_parts.append("\n⚪ <b>Otros:</b>")
            for i, code in enumerate(other_codes, 1):
                user_info = code.username or code.first_name or f"ID:{code.user_id}"
                text_parts.append(f"\n{i}. <code>{code.code}</code> - {user_info}")
                text_parts.append(f"   [{code.status.value}]")

        text = "".join(text_parts)

        keyboard_buttons = []

        # Agregar botones de acción para códigos activos
        for code in active_codes[:5]:
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"✓ Usar {code.code}",
                    callback_data=f"use_code_{code.id}"
                ),
                InlineKeyboardButton(
                    text=f"✗ Cancelar {code.code}",
                    callback_data=f"cancel_code_{code.id}"
                )
            ])

        keyboard_buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="view_trivia_discounts")])

        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    finally:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("pause_trivia_"), lambda cb: is_admin(cb.from_user.id))
async def pause_trivia_discount(callback: CallbackQuery):
    """Pausar configuración"""
    config_id = int(callback.data.replace("pause_trivia_", ""))
    service = TriviaDiscountService()
    result = service.pause_trivia_promotion_config(config_id)

    await callback.message.edit_text(
        "🎩 <b>Lucien:</b>\n\n"
        f"<i>Configuración {'pausada' if result else 'error al pausar'}.</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_trivia_discount")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("resume_trivia_"), lambda cb: is_admin(cb.from_user.id))
async def resume_trivia_discount(callback: CallbackQuery):
    """Reanudar configuración pausada o terminada"""
    config_id = int(callback.data.replace("resume_trivia_", ""))
    service = TriviaDiscountService()
    result = service.resume_trivia_promotion_config(config_id)

    await callback.message.edit_text(
        "🎩 <b>Lucien:</b>\n\n"
        f"<i>Configuración {'reanudada' if result else 'error al reanudar'}.</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_trivia_discount")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("delete_trivia_"), lambda cb: is_admin(cb.from_user.id))
async def delete_trivia_discount(callback: CallbackQuery):
    """Eliminar configuración"""
    config_id = int(callback.data.replace("delete_trivia_", ""))
    service = TriviaDiscountService()
    result = service.delete_trivia_promotion_config(config_id)

    await callback.message.edit_text(
        "🎩 <b>Lucien:</b>\n\n"
        f"<i>Configuración {'eliminada' if result else 'error al eliminar'}.</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_trivia_discount")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("use_code_"), lambda cb: is_admin(cb.from_user.id))
async def mark_code_as_used(callback: CallbackQuery):
    """Marcar código como usado"""
    code_id = int(callback.data.replace("use_code_", ""))
    service = TriviaDiscountService()
    result = service.use_discount_code(code_id)

    await callback.answer("Código marcado como usado" if result else "Error")
    await callback.message.delete()

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Volver a códigos", callback_data="view_trivia_discounts")]
    ])

    await callback.message.answer(
        "🎩 <b>Lucien:</b>\n\n"
        f"<i>Código {'marcado como usado' if result else 'error al marcar'}.</i>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("cancel_code_"), lambda cb: is_admin(cb.from_user.id))
async def cancel_discount_code(callback: CallbackQuery):
    """Cancelar código"""
    code_id = int(callback.data.replace("cancel_code_", ""))
    service = TriviaDiscountService()
    result = service.cancel_discount_code(code_id)

    await callback.answer("Código cancelado" if result else "Error")
    await callback.message.delete()

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Volver a códigos", callback_data="view_trivia_discounts")]
    ])

    await callback.message.answer(
        "🎩 <b>Lucien:</b>\n\n"
        f"<i>Código {'cancelado' if result else 'error al cancelar'}.</i>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


# ==================== EXTENDER DURACIÓN ====================

@router.callback_query(F.data.regex(r"^extend_duration_\d+$"), lambda cb: is_admin(cb.from_user.id))
async def extend_duration_start(callback: CallbackQuery, state: FSMContext):
    """Iniciar extensión de duración"""
    config_id = int(callback.data.replace("extend_duration_", ""))
    await state.update_data(extend_config_id=config_id)

    await callback.message.edit_text(
        "🎩 <b>Lucien:</b>\n\n"
        "Ingrese la duración a agregar:\n\n"
        "Formatos aceptados:\n"
        "• <code>30</code> → 30 minutos\n"
        "• <code>30m</code> o <code>30min</code> → 30 minutos\n"
        "• <code>2h</code> o <code>2hr</code> → 2 horas\n"
        "• <code>1d</code> o <code>1day</code> → 1 día",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Cancelar", callback_data="view_trivia_discounts")]
        ]),
        parse_mode="HTML"
    )
    await state.set_state(TriviaDiscountStates.waiting_extend_duration)
    await callback.answer()


@router.message(TriviaDiscountStates.waiting_extend_duration, lambda msg: is_admin(msg.from_user.id))
async def extend_duration_process(message: Message, state: FSMContext):
    """Procesar extensión de duración"""
    data = await state.get_data()
    config_id = data.get('extend_config_id')

    additional = _parse_duration(message.text.strip())
    if not additional or additional < 1:
        await message.answer(
            "Duración inválida. Use formatos como: 30m, 2h, 1d\n"
            "Intente de nuevo:",
            parse_mode="HTML"
        )
        return

    service = TriviaDiscountService()
    result = service.extend_duration(config_id, additional)

    if result:
        remaining = service.get_time_remaining_formatted(config_id)
        await message.answer(
            "🎩 <b>Lucien:</b>\n\n"
            f"<i>Duración extendida con éxito.</i>\n\n"
            f"Nuevo tiempo restante: {remaining}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Volver", callback_data="view_trivia_discounts")]
            ]),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "🎩 <b>Lucien:</b>\n\n"
            "<i>Error al extender la duración.</i>\n\n"
            "Intente de nuevo.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Volver", callback_data="view_trivia_discounts")]
            ]),
            parse_mode="HTML"
        )

    await state.clear()
