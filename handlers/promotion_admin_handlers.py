"""
Handlers de Promociones para Administradores - Lucien Bot

Gestion de promociones comerciales, intereses de usuarios y bloqueos.
Con la voz caracteristica de Lucien.
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
from config.settings import bot_config
from services import get_service
from services.promotion_service import PromotionService
from services import get_service
from services.package_service import PackageService
from services.question_set_service import QuestionSetService
from models.models import PromotionStatus, InterestStatus
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = Router()


# Estados para FSM
class PromotionWizardStates(StatesGroup):
    waiting_name = State()
    waiting_description = State()
    selecting_source = State()  # Nuevo: elegir entre paquete o manual
    selecting_package = State()
    waiting_manual_files = State()  # Nuevo: ingresar número manual
    waiting_price = State()
    waiting_dates = State()
    waiting_question_set = State()  # Opcional: asociar QuestionSet
    confirming = State()


class BlockUserStates(StatesGroup):
    waiting_reason = State()
    confirming = State()


def is_admin(user_id: int) -> bool:
    return user_id in bot_config.ADMIN_IDS


# ==================== MENU PRINCIPAL ====================

@router.callback_query(F.data == "admin_promotions", lambda cb: is_admin(cb.from_user.id))
async def admin_promotions_menu(callback: CallbackQuery):
    """Menu de administracion de promociones - Voz de Lucien"""
    with get_service(PromotionService) as promotion_service:
            stats = promotion_service.get_promotion_stats()

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Forjar nueva experiencia", callback_data="create_promotion")],
                [InlineKeyboardButton(text="📋 Ver el Gabinete", callback_data="list_promotions")],
                [InlineKeyboardButton(text="🔔 Expresiones pendientes", callback_data="promo_pending_interests")],
                [InlineKeyboardButton(text="🚫 Visitantes restringidos", callback_data="promo_blocked_users")],
                [InlineKeyboardButton(text="📊 Observar el pulso", callback_data="promo_stats")],
                [InlineKeyboardButton(text="🔙 Volver al sanctum", callback_data="admin_gamification")]
            ])

            text = ("🎩 <b>Lucien:</b>\n\n"
                    "<i>Ah... el Gabinete de Oportunidades Comerciales.</i>\n\n"
                    "Aqui es donde Diana selecciona las experiencias que se ofrecen "
                    "a quienes desean... invertir en momentos exclusivos.\n\n"
                    f"📊 <b>El estado del Gabinete:</b>\n"
                    f"   • Experiencias activas: {stats['active_promotions']}\n"
                    f"   • Total de experiencias: {stats['total_promotions']}\n"
                    f"   • Expresiones pendientes: {stats['pending_interests']}\n"
                    f"   • Expresiones atendidas: {stats['attended_interests']}\n"
                    f"   • Visitantes restringidos: {stats['blocked_users']}\n\n"
                    "<i>Que aspecto del Gabinete requiere su atencion?</i>")

            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
            await callback.answer()


        # ==================== WIZARD CREAR PROMOCION ====================

@router.callback_query(F.data == "create_promotion", lambda cb: is_admin(cb.from_user.id))
async def create_promotion_start(callback: CallbackQuery, state: FSMContext):
    """Inicia wizard de creacion de promocion - Voz de Lucien"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_promotions")]
    ])

    text = ("🎩 <b>Lucien:</b>\n\n"
            "<i>Vamos a forjar una nueva experiencia para el Gabinete...</i>\n\n"
            "<b>Paso 1 de 5:</b> El nombre de la experiencia\n\n"
            "Indique un nombre que capture la esencia de lo que Diana ofrece:\n"
            "<i>Ejemplo: Coleccion Primavera - Momentos Intimos</i>")

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(PromotionWizardStates.waiting_name)
    await callback.answer()


@router.message(PromotionWizardStates.waiting_name)
async def process_promotion_name(message: Message, state: FSMContext):
    """Procesa nombre de la promocion - Voz de Lucien"""
    name = message.text.strip()
    if len(name) < 3:
        await message.answer("El nombre debe tener al menos 3 caracteres.")
        return

    await state.update_data(name=name)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_promotions")]
    ])

    text = ("🎩 <b>Lucien:</b>\n\n"
            "<b>Paso 2 de 5:</b> La descripcion\n\n"
            "Describa lo que esta experiencia ofrece (opcional):\n"
            "<i>Ejemplo: Una seleccion curada de momentos capturados...</i>\n\n"
            "Envie /skip para omitir.")

    await message.answer(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(PromotionWizardStates.waiting_description)


@router.message(PromotionWizardStates.waiting_description)
async def process_promotion_description(message: Message, state: FSMContext):
    """Procesa descripcion de la promocion - Voz de Lucien"""
    description = None if message.text == "/skip" else message.text.strip()
    await state.update_data(description=description)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Seleccionar coleccion existente", callback_data="promo_select_package")],
        [InlineKeyboardButton(text="📝 Definir archivos manualmente", callback_data="promo_manual_files")],
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_promotions")]
    ])

    text = ("🎩 <b>Lucien:</b>\n\n"
            "<b>Paso 3 de 5:</b> Definir el contenido\n\n"
            "Diana puede vincular esta experiencia a una coleccion existente, "
            "o simplemente indicar cuantos archivos entregara de forma independiente...")

    await message.answer(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(PromotionWizardStates.selecting_source)


@router.callback_query(PromotionWizardStates.selecting_source, F.data == "promo_select_package")
async def select_package_source(callback: CallbackQuery, state: FSMContext):
    """Muestra lista de paquetes para seleccionar - Voz de Lucien"""
    package_service = PackageService()
    packages = package_service.get_all_packages()

    if not packages:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 Definir archivos manualmente", callback_data="promo_manual_files")],
            [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_promotions")]
        ])
        text = ("🎩 <b>Lucien:</b>\n\n"
                "<i>No hay colecciones disponibles...</i>\n\n"
                "Puede definir los archivos manualmente o crear una coleccion primero.")
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        return

    buttons = []
    for pkg in packages:
        if pkg.is_active:
            file_count = len(pkg.files) if pkg.files else 0
            buttons.append([InlineKeyboardButton(
                text=f"{pkg.name} ({file_count} archivos)",
                callback_data=f"select_pkg_promo_{pkg.id}"
            )])

    buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="admin_promotions")])

    text = ("🎩 <b>Lucien:</b>\n\n"
            "<b>Paso 3 de 5:</b> Seleccionar la coleccion\n\n"
            "Elija que coleccion formara parte de esta experiencia:")

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode=ParseMode.HTML)
    await state.set_state(PromotionWizardStates.selecting_package)
    await callback.answer()


@router.callback_query(PromotionWizardStates.selecting_source, F.data == "promo_manual_files")
async def select_manual_files(callback: CallbackQuery, state: FSMContext):
    """Inicia entrada manual de archivos - Voz de Lucien"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_promotions")]
    ])

    text = ("🎩 <b>Lucien:</b>\n\n"
            "<b>Paso 3 de 5:</b> Definir archivos manualmente\n\n"
            "Indique cuantos archivos contendra esta experiencia:\n"
            "<i>Ejemplo: 15</i>")

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(PromotionWizardStates.waiting_manual_files)
    await callback.answer()


@router.message(PromotionWizardStates.waiting_manual_files)
async def process_manual_files(message: Message, state: FSMContext):
    """Procesa numero manual de archivos - Voz de Lucien"""
    try:
        file_count = int(message.text.strip())
        if file_count < 0:
            raise ValueError("Debe ser 0 o mayor")
    except ValueError:
        await message.answer("Por favor indique un numero valido (0 o mayor).")
        return

    await state.update_data(manual_file_count=file_count, package_id=None)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_promotions")]
    ])

    text = ("🎩 <b>Lucien:</b>\n\n"
            "<b>Paso 4 de 5:</b> La inversion\n\n"
            "Indique el precio en pesos mexicanos (sin decimales):\n"
            "<i>Ejemplo: 299 (para $299.00 MXN)</i>")

    await message.answer(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(PromotionWizardStates.waiting_price)


@router.callback_query(PromotionWizardStates.selecting_package, F.data.startswith("select_pkg_promo_"))
async def select_package_for_promotion(callback: CallbackQuery, state: FSMContext):
    """Selecciona paquete para la promocion - Voz de Lucien"""
    try:
        package_id = int(callback.data.replace("select_pkg_promo_", ""))
    except ValueError:
        await callback.answer("ID invalido", show_alert=True)
        return

    await state.update_data(package_id=package_id, manual_file_count=None)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_promotions")]
    ])

    text = ("🎩 <b>Lucien:</b>\n\n"
            "<b>Paso 4 de 5:</b> La inversion\n\n"
            "Indique el precio en pesos mexicanos (sin decimales):\n"
            "<i>Ejemplo: 299 (para $299.00 MXN)</i>")

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(PromotionWizardStates.waiting_price)
    await callback.answer()


@router.message(PromotionWizardStates.waiting_price)
async def process_promotion_price(message: Message, state: FSMContext):
    """Procesa precio de la promocion - Voz de Lucien"""
    try:
        price = int(message.text.strip())
        if price < 1:
            raise ValueError("Debe ser mayor a 0")
    except ValueError:
        await message.answer("Por favor indique un numero valido mayor a 0.")
        return

    # Convertir a centavos para almacenamiento
    price_cents = price * 100
    await state.update_data(price_mxn=price_cents)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Sin fechas", callback_data="promo_no_dates")],
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_promotions")]
    ])

    text = ("🎩 <b>Lucien:</b>\n\n"
            "<b>Paso 5 de 5:</b> Periodo de disponibilidad (opcional)\n\n"
            "Puede configurar fechas de inicio y fin, o dejarlo sin fechas "
            "para que este disponible inmediatamente y sin expiracion.\n\n"
            "Para configurar fechas, envie:\n"
            "<code>INICIO: YYYY-MM-DD</code>\n"
            "<code>FIN: YYYY-MM-DD</code>\n\n"
            "<i>Ejemplo:</i>\n"
            "<code>INICIO: 2026-04-01</code>\n"
            "<code>FIN: 2026-04-30</code>")

    await message.answer(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(PromotionWizardStates.waiting_dates)


@router.callback_query(PromotionWizardStates.waiting_dates, F.data == "promo_no_dates")
async def promotion_no_dates(callback: CallbackQuery, state: FSMContext):
    """Sin fechas de vigencia - Voz de Lucien"""
    await state.update_data(start_date=None, end_date=None)
    await show_question_set_selection(callback, state)
    await callback.answer()


@router.message(PromotionWizardStates.waiting_dates)
async def process_promotion_dates(message: Message, state: FSMContext):
    """Procesa fechas de vigencia - Voz de Lucien"""
    text = message.text.strip()
    start_date = None
    end_date = None

    try:
        lines = text.split('\n')
        for line in lines:
            if line.startswith('INICIO:'):
                date_str = line.replace('INICIO:', '').strip()
                start_date = datetime.strptime(date_str, '%Y-%m-%d')
            elif line.startswith('FIN:'):
                date_str = line.replace('FIN:', '').strip()
                end_date = datetime.strptime(date_str, '%Y-%m-%d')

        await state.update_data(start_date=start_date, end_date=end_date)
        await show_question_set_selection(message, state)
    except ValueError:
        await message.answer(
            "Formato incorrecto. Use:\n\n"
            "<code>INICIO: YYYY-MM-DD</code>\n"
            "<code>FIN: YYYY-MM-DD</code>",
            parse_mode=ParseMode.HTML
        )


async def show_question_set_selection(target, state: FSMContext):
    """Muestra seleccion de QuestionSet (opcional) - Voz de Lucien"""
    with get_service(QuestionSetService) as question_set_service:
        sets = question_set_service.get_all_sets()

    buttons = []
    for qs in sets:
        status = "✅" if qs.is_active else "❌"
        buttons.append([InlineKeyboardButton(
            text=f"{status} {qs.name}",
            callback_data=f"select_qs_promo_{qs.id}"
        )])

    buttons.append([InlineKeyboardButton(
        text="No asociar",
        callback_data="skip_qs_promo"
    )])
    buttons.append([InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_promotions")])

    text = ("🎩 <b>Lucien:</b>\n\n"
            "<b>Paso opcional:</b> Asociar un set de preguntas\n\n"
            "Si lo desea, puede vincular una trivia temática a esta experiencia. "
            "Los visitantes que adquieran la experiencia podrán participar en la trivia.\n\n"
            "<i>Seleccione un set o elija 'No asociar' para omitir:</i>")

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    else:
        await target.answer(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)

    await state.set_state(PromotionWizardStates.waiting_question_set)


@router.callback_query(PromotionWizardStates.waiting_question_set, F.data == "skip_qs_promo")
async def skip_question_set(callback: CallbackQuery, state: FSMContext):
    """Omite la asociacion de QuestionSet - Voz de Lucien"""
    await state.update_data(question_set_id=None)
    await show_promotion_confirmation(callback, state)
    await callback.answer()


@router.callback_query(PromotionWizardStates.waiting_question_set, F.data.startswith("select_qs_promo_"))
async def select_question_set(callback: CallbackQuery, state: FSMContext):
    """Selecciona QuestionSet para la promocion - Voz de Lucien"""
    try:
        qs_id = int(callback.data.replace("select_qs_promo_", ""))
    except ValueError:
        await callback.answer("ID invalido", show_alert=True)
        return

    await state.update_data(question_set_id=qs_id)
    await show_promotion_confirmation(callback, state)
    await callback.answer()


async def show_promotion_confirmation(target, state: FSMContext):
    """Muestra confirmacion de la promocion - Voz de Lucien"""
    data = await state.get_data()

    name = data.get('name', '')
    description = data.get('description', 'Sin descripcion')
    price_mxn = data.get('price_mxn', 0)
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    manual_file_count = data.get('manual_file_count')
    package_id = data.get('package_id')
    question_set_id = data.get('question_set_id')

    price_display = f"${price_mxn // 100:,}.00 MXN"

    # Determinar el numero de archivos para mostrar
    if manual_file_count is not None:
        file_text = f"📁 <b>Archivos:</b> {manual_file_count} (definido manualmente)\n"
    elif package_id:
        file_text = "📁 <b>Contenido:</b> De coleccion existente\n"
    else:
        file_text = "📁 <b>Archivos:</b> No especificado\n"

    dates_text = "Sin fechas (disponible inmediatamente, sin expiracion)"
    if start_date:
        dates_text = f"Inicio: {start_date.strftime('%Y-%m-%d')}\n"
        if end_date:
            dates_text += f"Fin: {end_date.strftime('%Y-%m-%d')}"

    text = (f"🎩 <b>Lucien:</b>\n\n"
            f"<i>Permitame confirmar los detalles de esta experiencia...</i>\n\n"
            f"✨ <b>{name}</b>\n"
            f"📝 {description}\n"
            f"💰 <b>Inversion:</b> {price_display}\n"
            f"{file_text}"
            f"📅 <b>Disponibilidad:</b> {dates_text}\n\n"
            f"<i>Desea forjar esta experiencia?</i>")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Forjar experiencia", callback_data="confirm_create_promotion")],
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_promotions")]
    ])

    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    else:
        await target.answer(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)

    await state.set_state(PromotionWizardStates.confirming)


@router.callback_query(PromotionWizardStates.confirming, F.data == "confirm_create_promotion")
async def confirm_create_promotion(callback: CallbackQuery, state: FSMContext):
    """Crea la promocion - Voz de Lucien"""
    data = await state.get_data()
    with get_service(PromotionService) as promotion_service:

            try:
                promotion = promotion_service.create_promotion(
                    name=data.get('name'),
                    description=data.get('description'),
                    package_id=data.get('package_id'),
                    manual_file_count=data.get('manual_file_count'),
                    price_mxn=data.get('price_mxn'),
                    created_by=callback.from_user.id,
                    start_date=data.get('start_date'),
                    end_date=data.get('end_date'),
                    question_set_id=data.get('question_set_id')
                )

                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Volver al Gabinete", callback_data="admin_promotions")]
                ])

                text = (f"🎩 <b>Lucien:</b>\n\n"
                        f"<i>Excelente. La experiencia ha sido forjada...</i>\n\n"
                        f"✨ <b>{promotion.name}</b>\n"
                        f"💰 {promotion.price_display}\n\n"
                        f"<i>Ya esta disponible en el Gabinete para quienes deseen... explorarla.</i>")

                await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
                logger.info(f"Experiencia creada: {promotion.name} por custodio {callback.from_user.id}")

            except Exception as e:
                logger.error(f"Error forjando experiencia: {e}")
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_promotions")]
                ])
                text = ("🎩 <b>Lucien:</b>\n\n"
                        "<i>Hmm... algo inesperado ha ocurrido.</i>\n\n"
                        "Permitame consultar con Diana sobre este inconveniente.")
                await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)

            await state.clear()
            await callback.answer()


        # ==================== LISTAR PROMOCIONES ====================

@router.callback_query(F.data == "list_promotions", lambda cb: is_admin(cb.from_user.id))
async def list_promotions(callback: CallbackQuery):
    """Lista todas las promociones - Voz de Lucien"""
    with get_service(PromotionService) as promotion_service:
            promotions = promotion_service.get_all_promotions()

            if not promotions:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_promotions")]
                ])
                text = ("🎩 <b>Lucien:</b>\n\n"
                        "<i>El Gabinete esta vacio...</i>\n\n"
                        "Aun no se han forjado experiencias.")
                await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
                await callback.answer()
                return

            text = "🎩 <b>Lucien:</b>\n\n"
            text += "<i>Las experiencias en el Gabinete:</i>\n\n"
            buttons = []

            for promo in promotions:
                status = "✅" if promo.is_active else "❌"
                text += f"{status} <b>{promo.name}</b>\n"
                text += f"   💰 {promo.price_display}\n\n"

                buttons.append([InlineKeyboardButton(
                    text=f"{status} {promo.name[:30]}",
                    callback_data=f"promo_admin_detail_{promo.id}"
                )])

            buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="admin_promotions")])

            await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode=ParseMode.HTML)
            await callback.answer()


@router.callback_query(F.data.startswith("promo_admin_detail_"), lambda cb: is_admin(cb.from_user.id))
async def promotion_admin_detail(callback: CallbackQuery):
    """Muestra detalles de una promocion - Voz de Lucien"""
    try:
        promo_id = int(callback.data.replace("promo_admin_detail_", ""))
    except ValueError:
        await callback.answer("ID invalido", show_alert=True)
        return

    with get_service(PromotionService) as promotion_service:
            promo = promotion_service.get_promotion(promo_id)

            if not promo:
                await callback.answer("Experiencia no encontrada", show_alert=True)
                return

            status = "✅ Activa" if promo.is_active else "❌ Inactiva"
            available = "🟢 Disponible" if promo.is_available else "🔴 No disponible"

            # Contar intereses
            total_interests = len(promo.interests) if promo.interests else 0
            pending_interests = len([i for i in promo.interests if i.status == InterestStatus.PENDING]) if promo.interests else 0

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=f"{'Desactivar' if promo.is_active else 'Activar'}",
                    callback_data=f"toggle_promo_{promo_id}"
                )],
                [InlineKeyboardButton(
                    text="📊 Ver expresiones de interes",
                    callback_data=f"promo_interests_{promo_id}"
                )],
                [InlineKeyboardButton(
                    text="🗑️ Eliminar",
                    callback_data=f"delete_promo_{promo_id}"
                )],
                [InlineKeyboardButton(text="🔙 Volver", callback_data="list_promotions")]
            ])

            text = (f"🎩 <b>Lucien:</b>\n\n"
                    f"✨ <b>{promo.name}</b>\n\n"
                    f"📝 {promo.description or 'Sin descripcion'}\n\n"
                    f"💰 <b>Inversion:</b> {promo.price_display}\n"
                    f"Estado: {status}\n"
                    f"Disponibilidad: {available}\n"
                    f"📦 Archivos: {promo.file_count}\n\n"
                    f"📊 <b>Expresiones de interes:</b>\n"
                    f"   • Total: {total_interests}\n"
                    f"   • Pendientes: {pending_interests}\n\n"
                    "<i>Que desea hacer con esta experiencia?</i>")

            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
            await callback.answer()


@router.callback_query(F.data.startswith("toggle_promo_"), lambda cb: is_admin(cb.from_user.id))
async def toggle_promotion(callback: CallbackQuery):
    """Activa/desactiva una promocion - Voz de Lucien"""
    try:
        promo_id = int(callback.data.replace("toggle_promo_", ""))
    except ValueError:
        await callback.answer("ID invalido", show_alert=True)
        return

    with get_service(PromotionService) as promotion_service:
            promo = promotion_service.get_promotion(promo_id)

            if not promo:
                await callback.answer("Experiencia no encontrada", show_alert=True)
                return

            promotion_service.update_promotion(promo_id, is_active=not promo.is_active)

            status = "activada" if not promo.is_active else "desactivada"
            await callback.answer(f"Experiencia {status}")
            await promotion_admin_detail(callback)


@router.callback_query(F.data.startswith("delete_promo_"), lambda cb: is_admin(cb.from_user.id))
async def delete_promotion_confirm(callback: CallbackQuery):
    """Confirma eliminacion de promocion - Voz de Lucien"""
    try:
        promo_id = int(callback.data.replace("delete_promo_", ""))
    except ValueError:
        await callback.answer("ID invalido", show_alert=True)
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Si, eliminar", callback_data=f"confirm_delete_promo_{promo_id}")],
        [InlineKeyboardButton(text="❌ Cancelar", callback_data=f"promo_admin_detail_{promo_id}")]
    ])

    text = ("🎩 <b>Lucien:</b>\n\n"
            "<i>Esta seguro de eliminar esta experiencia?</i>\n\n"
            "Esta accion no se puede deshacer. "
            "Las expresiones de interes asociadas tambien se perderan...")

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_promo_"), lambda cb: is_admin(cb.from_user.id))
async def confirm_delete_promotion(callback: CallbackQuery):
    """Elimina la promocion - Voz de Lucien"""
    try:
        promo_id = int(callback.data.replace("confirm_delete_promo_", ""))
    except ValueError:
        await callback.answer("ID invalido", show_alert=True)
        return

    with get_service(PromotionService) as promotion_service:
            success = promotion_service.delete_promotion(promo_id)

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Volver al Gabinete", callback_data="admin_promotions")]
            ])

            if success:
                text = ("🎩 <b>Lucien:</b>\n\n"
                        "<i>La experiencia ha sido eliminada del Gabinete.</i>")
            else:
                text = ("🎩 <b>Lucien:</b>\n\n"
                        "<i>Hmm... no se pudo eliminar la experiencia.</i>")

            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
            await callback.answer()


        # ==================== INTERESES ====================

@router.callback_query(F.data == "promo_pending_interests", lambda cb: is_admin(cb.from_user.id))
async def show_pending_interests(callback: CallbackQuery):
    """Muestra intereses pendientes de todas las promociones - Voz de Lucien"""
    with get_service(PromotionService) as promotion_service:
            pending = promotion_service.get_pending_interests()

            if not pending:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_promotions")]
                ])
                text = ("🎩 <b>Lucien:</b>\n\n"
                        "<i>No hay expresiones de interes pendientes...</i>\n\n"
                        "El Gabinete espera nuevas curiosidades.")
                await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
                await callback.answer()
                return

            text = f"🎩 <b>Lucien:</b>\n\n"
            text += f"🔔 <b>Expresiones pendientes: {len(pending)}</b>\n\n"

            buttons = []
            for interest in pending[:20]:  # Limitar a 20 para no sobrecargar
                promo_name = interest.promotion.name if interest.promotion else "Desconocida"
                user_display = interest.username or interest.first_name or f"Visitante {interest.user_id}"
                text += f"• {user_display} - {promo_name[:20]}\n"

                buttons.append([InlineKeyboardButton(
                    text=f"{user_display[:20]} - {promo_name[:15]}",
                    callback_data=f"interest_detail_{interest.id}"
                )])

            buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="admin_promotions")])

            await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode=ParseMode.HTML)
            await callback.answer()


@router.callback_query(F.data.startswith("promo_interests_"), lambda cb: is_admin(cb.from_user.id))
async def show_promotion_interests(callback: CallbackQuery):
    """Muestra intereses de una promocion especifica - Voz de Lucien"""
    try:
        promo_id = int(callback.data.replace("promo_interests_", ""))
    except ValueError:
        await callback.answer("ID invalido", show_alert=True)
        return

    with get_service(PromotionService) as promotion_service:
            promo = promotion_service.get_promotion(promo_id)

            if not promo:
                await callback.answer("Experiencia no encontrada", show_alert=True)
                return

            pending = [i for i in promo.interests if i.status == InterestStatus.PENDING] if promo.interests else []

            if not pending:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Volver", callback_data=f"promo_admin_detail_{promo_id}")]
                ])
                text = (f"🎩 <b>Lucien:</b>\n\n"
                        f"<i>No hay expresiones pendientes para '{promo.name}'...</i>")
                await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
                await callback.answer()
                return

            text = f"🎩 <b>Lucien:</b>\n\n"
            text += f"✨ <b>{promo.name}</b>\n"
            text += f"🔔 <b>Expresiones pendientes: {len(pending)}</b>\n\n"

            buttons = []
            for interest in pending[:15]:
                user_display = interest.username or interest.first_name or f"Visitante {interest.user_id}"
                text += f"• {user_display}\n"

                buttons.append([InlineKeyboardButton(
                    text=f"{user_display[:25]}",
                    callback_data=f"interest_detail_{interest.id}"
                )])

            buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data=f"promo_admin_detail_{promo_id}")])

            await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode=ParseMode.HTML)
            await callback.answer()


@router.callback_query(F.data.startswith("interest_detail_"), lambda cb: is_admin(cb.from_user.id))
async def show_interest_detail(callback: CallbackQuery):
    """Muestra detalle de un interes con botones de accion - Voz de Lucien"""
    try:
        interest_id = int(callback.data.replace("interest_detail_", ""))
    except ValueError:
        await callback.answer("ID invalido", show_alert=True)
        return

    with get_service(PromotionService) as promotion_service:
            interest = promotion_service.get_interest(interest_id)

            if not interest:
                await callback.answer("Expresion no encontrada", show_alert=True)
                return

            promo = interest.promotion
            promo_name = promo.name if promo else "Desconocida"

            # Construir nombre de usuario
            user_display = interest.username or interest.first_name or "Visitante"
            if interest.first_name and interest.last_name:
                user_display = f"{interest.first_name} {interest.last_name}"
            elif interest.first_name:
                user_display = interest.first_name

            user_link = f"tg://user?id={interest.user_id}"

            status_emoji = {
                InterestStatus.PENDING: "⏳",
                InterestStatus.ATTENDED: "✅",
                InterestStatus.BLOCKED: "🚫"
            }.get(interest.status, "❓")

            keyboard = InlineKeyboardMarkup(inline_keyboard=[])

            # Solo mostrar acciones si esta pendiente
            if interest.status == InterestStatus.PENDING:
                keyboard.inline_keyboard.extend([
                    [InlineKeyboardButton(
                        text="💬 Contactar al visitante",
                        url=user_link
                    )],
                    [InlineKeyboardButton(
                        text="✅ Marcar como atendido",
                        callback_data=f"mark_attended_{interest_id}"
                    )],
                    [InlineKeyboardButton(
                        text="🚫 Restringir visitante",
                        callback_data=f"block_interest_user_{interest_id}"
                    )]
                ])

            keyboard.inline_keyboard.append([InlineKeyboardButton(
                text="🔙 Volver",
                callback_data="promo_pending_interests"
            )])

            text = (f"🎩 <b>Lucien:</b>\n\n"
                    f"📋 <b>Detalle de la expresion:</b>\n\n"
                    f"👤 <b>Visitante:</b> {user_display}\n"
                    f"   ID: <code>{interest.user_id}</code>\n"
                    f"   Username: @{interest.username or 'N/A'}\n\n"
                    f"✨ <b>Experiencia:</b> {promo_name}\n"
                    f"💰 <b>Inversion:</b> {promo.price_display if promo else 'N/A'}\n\n"
                    f"{status_emoji} <b>Estado:</b> {interest.status.value.title()}\n"
                    f"📅 <b>Fecha:</b> {interest.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
                    "<i>Acciones disponibles:</i>")

            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
            await callback.answer()


@router.callback_query(F.data.startswith("mark_attended_"), lambda cb: is_admin(cb.from_user.id))
async def mark_interest_attended(callback: CallbackQuery):
    """Marca un interes como atendido - Voz de Lucien"""
    try:
        interest_id = int(callback.data.replace("mark_attended_", ""))
    except ValueError:
        await callback.answer("ID invalido", show_alert=True)
        return

    with get_service(PromotionService) as promotion_service:
            success = promotion_service.mark_interest_attended(interest_id, callback.from_user.id)

            if success:
                await callback.answer("✅ Marcado como atendido")
                await show_pending_interests(callback)
            else:
                await callback.answer("Error al marcar como atendido", show_alert=True)


@router.callback_query(F.data.startswith("block_interest_user_"), lambda cb: is_admin(cb.from_user.id))
async def block_interest_user(callback: CallbackQuery, state: FSMContext):
    """Inicia proceso de bloqueo de usuario - Voz de Lucien"""
    try:
        interest_id = int(callback.data.replace("block_interest_user_", ""))
    except ValueError:
        await callback.answer("ID invalido", show_alert=True)
        return

    with get_service(PromotionService) as promotion_service:
            interest = promotion_service.get_interest(interest_id)

            if not interest:
                await callback.answer("Expresion no encontrada", show_alert=True)
                return

            # Guardar datos para el bloqueo
            await state.update_data(
                block_user_id=interest.user_id,
                block_username=interest.username,
                block_first_name=interest.first_name,
                block_last_name=interest.last_name,
                interest_id=interest_id
            )

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Cancelar", callback_data=f"interest_detail_{interest_id}")]
            ])

            user_display = interest.username or interest.first_name or str(interest.user_id)

            text = (f"🎩 <b>Lucien:</b>\n\n"
                    f"<i>Va a restringir al visitante {user_display}...</i>\n\n"
                    f"Indique la razon de esta restriccion (opcional):\n"
                    f"<i>Ejemplo: Comportamiento inapropiado, spam, etc.</i>\n\n"
                    f"Envie /skip para omitir la razon.")

            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
            await state.set_state(BlockUserStates.waiting_reason)
            await callback.answer()


@router.message(BlockUserStates.waiting_reason)
async def process_block_reason(message: Message, state: FSMContext):
    """Procesa la razon del bloqueo - Voz de Lucien"""
    reason = None if message.text == "/skip" else message.text.strip()
    await state.update_data(block_reason=reason)

    data = await state.get_data()
    user_display = data.get('block_username') or data.get('block_first_name') or str(data.get('block_user_id'))

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Si, restringir", callback_data="confirm_block_user")],
        [InlineKeyboardButton(text="❌ Cancelar", callback_data=f"interest_detail_{data.get('interest_id')}")]
    ])

    text = (f"🎩 <b>Lucien:</b>\n\n"
            f"<i>Confirma restringir a {user_display}?</i>\n\n"
            f"Razon: {reason or 'No especificada'}\n\n"
            f"El visitante no podra expresar interes en ninguna experiencia del Gabinete.")

    await message.answer(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(BlockUserStates.confirming)


@router.callback_query(BlockUserStates.confirming, F.data == "confirm_block_user")
async def confirm_block_user(callback: CallbackQuery, state: FSMContext):
    """Confirma el bloqueo del usuario - Voz de Lucien"""
    data = await state.get_data()
    with get_service(PromotionService) as promotion_service:

            try:
                blocked = promotion_service.block_user(
                    user_id=data.get('block_user_id'),
                    blocked_by=callback.from_user.id,
                    reason=data.get('block_reason'),
                    is_permanent=True,
                    username=data.get('block_username'),
                    first_name=data.get('block_first_name'),
                    last_name=data.get('block_last_name')
                )

                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Volver", callback_data="promo_pending_interests")]
                ])

                text = ("🎩 <b>Lucien:</b>\n\n"
                        "<i>El visitante ha sido restringido del Gabinete.</i>\n\n"
                        "Ya no podra expresar interes en las experiencias.")

                await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
                logger.info(f"Visitante {data.get('block_user_id')} restringido por custodio {callback.from_user.id}")

            except Exception as e:
                logger.error(f"Error restringiendo visitante: {e}")
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Volver", callback_data="promo_pending_interests")]
                ])
                text = ("🎩 <b>Lucien:</b>\n\n"
                        "<i>Hmm... no se pudo restringir al visitante.</i>")
                await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)

            await state.clear()
            await callback.answer()


        # ==================== USUARIOS BLOQUEADOS ====================

@router.callback_query(F.data == "promo_blocked_users", lambda cb: is_admin(cb.from_user.id))
async def show_blocked_users(callback: CallbackQuery):
    """Muestra usuarios bloqueados - Voz de Lucien"""
    with get_service(PromotionService) as promotion_service:
            blocked = promotion_service.get_blocked_users()

            if not blocked:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_promotions")]
                ])
                text = ("🎩 <b>Lucien:</b>\n\n"
                        "<i>No hay visitantes restringidos...</i>\n\n"
                        "El Gabinete esta abierto para todos.")
                await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
                await callback.answer()
                return

            text = f"🎩 <b>Lucien:</b>\n\n"
            text += f"🚫 <b>Visitantes restringidos: {len(blocked)}</b>\n\n"

            buttons = []
            for user in blocked:
                user_display = user.username or user.first_name or f"Visitante {user.user_id}"
                text += f"• {user_display}\n"

                buttons.append([InlineKeyboardButton(
                    text=f"{user_display[:25]}",
                    callback_data=f"blocked_user_detail_{user.user_id}"
                )])

            buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="admin_promotions")])

            await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode=ParseMode.HTML)
            await callback.answer()


@router.callback_query(F.data.startswith("blocked_user_detail_"), lambda cb: is_admin(cb.from_user.id))
async def show_blocked_user_detail(callback: CallbackQuery):
    """Muestra detalle de un usuario bloqueado - Voz de Lucien"""
    try:
        user_id = int(callback.data.replace("blocked_user_detail_", ""))
    except ValueError:
        await callback.answer("ID invalido", show_alert=True)
        return

    with get_service(PromotionService) as promotion_service:
            blocked = promotion_service.get_blocked_user_info(user_id)

            if not blocked:
                await callback.answer("Visitante no encontrado", show_alert=True)
                return

            user_display = blocked.username or blocked.first_name or f"Visitante {blocked.user_id}"

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="✅ Levantar restriccion",
                    callback_data=f"unblock_user_{user_id}"
                )],
                [InlineKeyboardButton(text="🔙 Volver", callback_data="promo_blocked_users")]
            ])

            text = (f"🎩 <b>Lucien:</b>\n\n"
                    f"🚫 <b>Visitante restringido:</b>\n\n"
                    f"👤 {user_display}\n"
                    f"   ID: <code>{blocked.user_id}</code>\n"
                    f"   Username: @{blocked.username or 'N/A'}\n\n"
                    f"📅 <b>Restringido:</b> {blocked.blocked_at.strftime('%Y-%m-%d %H:%M')}\n"
                    f"📝 <b>Razon:</b> {blocked.reason or 'No especificada'}\n"
                    f"⏱️ <b>Permanente:</b> {'Si' if blocked.is_permanent else 'No'}\n\n"
                    "<i>Que desea hacer?</i>")

            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
            await callback.answer()


@router.callback_query(F.data.startswith("unblock_user_"), lambda cb: is_admin(cb.from_user.id))
async def unblock_user(callback: CallbackQuery):
    """Desbloquea un usuario - Voz de Lucien"""
    try:
        user_id = int(callback.data.replace("unblock_user_", ""))
    except ValueError:
        await callback.answer("ID invalido", show_alert=True)
        return

    with get_service(PromotionService) as promotion_service:
            success = promotion_service.unblock_user(user_id)

            if success:
                await callback.answer("✅ Restriccion levantada")
                await show_blocked_users(callback)
            else:
                await callback.answer("Error al levantar restriccion", show_alert=True)


        # ==================== ESTADISTICAS ====================

@router.callback_query(F.data == "promo_stats", lambda cb: is_admin(cb.from_user.id))
async def promotion_stats(callback: CallbackQuery):
    """Muestra estadisticas de promociones - Voz de Lucien"""
    with get_service(PromotionService) as promotion_service:
            stats = promotion_service.get_promotion_stats()

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_promotions")]
            ])

            text = (f"🎩 <b>Lucien:</b>\n\n"
                    f"📊 <b>El pulso del Gabinete:</b>\n\n"
                    f"✨ <b>Experiencias:</b>\n"
                    f"   • Activas: {stats['active_promotions']}\n"
                    f"   • Total: {stats['total_promotions']}\n\n"
                    f"🔔 <b>Expresiones de interes:</b>\n"
                    f"   • Pendientes: {stats['pending_interests']}\n"
                    f"   • Atendidas: {stats['attended_interests']}\n"
                    f"   • Total: {stats['total_interests']}\n\n"
                    f"🚫 <b>Visitantes restringidos:</b> {stats['blocked_users']}")

            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
            await callback.answer()
