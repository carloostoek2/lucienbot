"""
Handlers de Admin - Trivia Discount System

Handlers para la gestión del sistema de promociones por racha de trivia.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from services.trivia_discount_service import TriviaDiscountService
from services.promotion_service import PromotionService
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
    waiting_max_codes = State()
    waiting_start_date = State()
    waiting_end_date = State()
    waiting_confirmation = State()


# ==================== MENÚ PRINCIPAL ====================

@router.callback_query(F.data == "admin_trivia_discount", lambda cb: is_admin(cb.from_user.id))
async def admin_trivia_discount_menu(callback: CallbackQuery):
    """Menú principal de gestión de promociones por racha"""
    service = TriviaDiscountService()
    try:
        configs = service.get_active_trivia_promotion_configs()

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="➕ Crear promoción de trivia",
                callback_data="create_trivia_discount"
            )]
        ])

        if configs:
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(
                    text="📋 Ver promociones activas",
                    callback_data="view_trivia_discounts"
                )
            ])

        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text="🔙 Volver",
                callback_data="admin_gamification"
            )
        ])

        await callback.message.edit_text(
            "🎩 <b>Lucien:</b>\n\n"
            "<i>Las recompensas que el conocimiento merece...</i>\n\n"
            f"Promociones activas: {len(configs)}\n\n"
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
    """Procesar racha requerida"""
    try:
        streak = int(message.text.strip())
        if streak < 3:
            await message.answer("La racha debe ser al menos 3. Intente de nuevo:")
            return
        await state.update_data(required_streak=streak)

        await message.answer(
            "🎩 <b>Lucien:</b>\n\n"
            "<i>Paso 4 de 6:</i> Ingrese el límite de códigos\n\n"
            "Número máximo de códigos que se pueden reclamar (mínimo 1)",
            parse_mode="HTML"
        )
        await state.set_state(TriviaDiscountStates.waiting_max_codes)
    except ValueError:
        await message.answer("Por favor ingrese un número válido:")


@router.message(TriviaDiscountStates.waiting_max_codes, lambda msg: is_admin(msg.from_user.id))
async def create_trivia_discount_max_codes(message: Message, state: FSMContext):
    """Procesar límite de códigos"""
    try:
        max_codes = int(message.text.strip())
        if max_codes < 1:
            await message.answer("El límite debe ser al menos 1. Intente de nuevo:")
            return
        await state.update_data(max_codes=max_codes)

        await message.answer(
            "🎩 <b>Lucien:</b>\n\n"
            "<i>Paso 5 de 6:</i> Fechas de vigencia (opcional)\n\n"
            "Envíe las fechas en formato:\n"
            "<code>YYYY-MM-DD YYYY-MM-DD</code>\n\n"
            "O envíe <b>skip</b> para sin límite de tiempo",
            parse_mode="HTML"
        )
        await state.set_state(TriviaDiscountStates.waiting_start_date)
    except ValueError:
        await message.answer("Por favor ingrese un número válido:")


@router.message(TriviaDiscountStates.waiting_start_date, lambda msg: is_admin(msg.from_user.id))
async def create_trivia_discount_dates(message: Message, state: FSMContext):
    """Procesar fechas"""
    text = message.text.strip().lower()

    if text == "skip":
        await state.update_data(start_date=None, end_date=None)
    else:
        try:
            parts = text.split()
            if len(parts) != 2:
                raise ValueError("Formato inválido")

            from datetime import datetime
            start = datetime.strptime(parts[0], "%Y-%m-%d")
            end = datetime.strptime(parts[1], "%Y-%m-%d")

            await state.update_data(start_date=start, end_date=end)
        except Exception:
            await message.answer(
                "Formato inválido. Envíe:\n"
                "<code>YYYY-MM-DD YYYY-MM-DD</code>\n"
                "o <b>skip</b> para omitir",
                parse_mode="HTML"
            )
            return

    # Mostrar confirmación
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

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✓ Confirmar", callback_data="confirm_trivia_discount")],
        [InlineKeyboardButton(text="✗ Cancelar", callback_data="admin_trivia_discount")]
    ])

    await message.answer(
        f"🎩 <b>Lucien:</b>\n\n"
        "<i>Paso 6 de 6:</i> Confirmar configuración\n\n"
        f"📋 <b>Promoción:</b> {promo_info}\n"
        f"💰 <b>Descuento:</b> {data['discount_percentage']}%\n"
        f"🔥 <b>Racha requerida:</b> {data['required_streak']} respuestas correctas\n"
        f"🎫 <b>Códigos máximo:</b> {data['max_codes']}\n"
        f"📅 <b>Vigencia:</b> {data.get('start_date', 'Sin inicio')} - {data.get('end_date', 'Sin fin')}",
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
        custom_description=data.get('custom_description')
    )

    if config:
        await callback.message.edit_text(
            "🎩 <b>Lucien:</b>\n\n"
            f"<i>Configuración creada con éxito.</i>\n\n"
            f"ID: {config.id}\n"
            f"Descuento: {config.discount_percentage}%\n"
            f"Racha: {config.required_streak}\n"
            f"Códigos: {config.max_codes}",
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
    """Ver configuraciones activas"""
    service = TriviaDiscountService()
    try:
        configs = service.get_active_trivia_promotion_configs()

        if not configs:
            await callback.message.edit_text(
                "🎩 <b>Lucien:</b>\n\n"
                "<i>No hay configuraciones activas.</i>",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_trivia_discount")]
                ]),
                parse_mode="HTML"
            )
            await callback.answer()
            return

        for config in configs:
            stats = service.get_discount_stats(config.id)

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="📊 Ver códigos",
                    callback_data=f"view_codes_{config.id}"
                )],
                [InlineKeyboardButton(
                    text="⏸️ Pausar",
                    callback_data=f"pause_trivia_{config.id}"
                )],
                [InlineKeyboardButton(
                    text="🗑️ Eliminar",
                    callback_data=f"delete_trivia_{config.id}"
                )],
                [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_trivia_discount")]
            ])

            promo = config.promotion
            promo_info = f"🏪 {promo.name}" if promo else f"✨ {config.custom_description or 'N/A'}"
            await callback.message.edit_text(
                f"🎫 <b>{config.name}</b>\n\n"
                f"📋 {promo_info}\n"
                f"💰 Descuento: {config.discount_percentage}%\n"
                f"🔥 Racha: {config.required_streak}\n"
                f"🎫 Códigos: {stats['available']} disponibles / {config.max_codes} total\n"
                f"📊 Usados: {stats['used']} ({stats['used_percentage']}%)",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            break
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
