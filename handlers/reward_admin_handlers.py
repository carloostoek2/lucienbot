"""
Handlers de Recompensas para Admin - Lucien Bot

Wizard de creacion de recompensas con cascada a paquetes.
"""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from keyboards.callback_data import (
    RewardAdminDetailCallback,
    RewardDeleteCallback,
    RewardSelectPkgCallback,
    RewardToggleCallback,
    RewardTypeCallback,
    SelectTariffCallback,
)
from models.models import RewardType
from services import get_service
from services.reward_service import RewardService
from utils.admin import is_admin

logger = logging.getLogger(__name__)
router = Router()


# Estados para FSM de Recompensas
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


# Estados para FSM de creacion de paquete desde recompensa
class PackageFromRewardStates(StatesGroup):
    waiting_name = State()
    waiting_description = State()
    waiting_files = State()
    waiting_store_stock = State()
    waiting_reward_stock = State()
    confirming = State()


# ==================== PURE HELPERS (extracted for <=50 LOC + exactly 1 service) ====================
# Función pura (sin estado ni side-effects). Soporte para UI de admin rewards (wizard/list/detail).
# 1:1 de lógica previamente inline (item34, arch-enforcer). Precedent item7/8/9.


def build_package_selection_text_and_buttons(packages: list) -> tuple[str, list[list]]:
    """Función pura (sin estado ni side-effects). Soporte para UI de admin rewards (wizard package select).
    1:1 de lógica previamente inline (item34, arch-enforcer). Precedent item7/8/9.
    """
    buttons = []
    if packages:
        for pkg in packages:
            stock_text = "∞" if pkg.reward_stock == -1 else str(pkg.reward_stock)
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"{pkg.name} ({pkg.file_count} archivos, stock: {stock_text})",
                        callback_data=RewardSelectPkgCallback(pkg_id=pkg.id).pack(),
                    )
                ]
            )
    buttons.append(
        [
            InlineKeyboardButton(
                text="➕ Crear nuevo paquete", callback_data="create_package_for_reward"
            )
        ]
    )
    buttons.append([InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_missions")])
    text = """🎩 Lucien:

Paso 4 de 5: Seleccionar paquete

Elige un paquete existente o crea uno nuevo:"""
    if not packages:
        text = """🎩 Lucien:

Paso 4 de 5: Seleccionar paquete

No hay paquetes disponibles para recompensas.

Debes crear uno nuevo:"""
    return text, buttons


def build_tariff_selection_buttons(tariffs: list) -> list[list]:
    """Función pura (sin estado ni side-effects). Soporte para UI de admin rewards (tariff select).
    1:1 de lógica previamente inline (item34, arch-enforcer). Precedent item7/8/9.
    """
    buttons = []
    for tariff in tariffs:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{tariff.name} ({tariff.duration_days} dias)",
                    callback_data=SelectTariffCallback(tariff_id=tariff.id).pack(),
                )
            ]
        )
    buttons.append([InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_missions")])
    return buttons


def build_pkg_confirmation_text_and_keyboard(data: dict) -> tuple[str, InlineKeyboardMarkup]:
    """Función pura (sin estado ni side-effects). Soporte para UI de admin rewards (pkg confirm from reward).
    1:1 de lógica previamente inline (item34, arch-enforcer). Precedent item7/8/9.
    """
    name = data.get("pkg_name", "")
    description = data.get("pkg_description", "Sin descripcion")
    files = data.get("pkg_files", [])
    reward_stock = data.get("pkg_reward_stock", -1)
    stock_text = "Ilimitado" if reward_stock == -1 else str(reward_stock)
    text = f"""🎩 Lucien:

Resumen del paquete:

📦 {name}
📝 {description}
📁 {len(files)} archivos
🎁 Stock recompensas: {stock_text}
🛒 Stock tienda: No disponible

Crear este paquete?"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Crear paquete", callback_data="confirm_create_pkg_from_reward"
                )
            ],
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_missions")],
        ]
    )
    return text, keyboard


def compute_reward_type_text(reward_type, besito_amount=None, pkg=None, tariff=None) -> str:
    """Función pura (sin estado ni side-effects). Soporte para UI de admin rewards (confirm type text).
    1:1 de lógica previamente inline (item34, arch-enforcer). Precedent item7/8/9.
    """
    if reward_type == RewardType.BESITOS:
        return f"{besito_amount or 0} besitos"
    if reward_type == RewardType.PACKAGE:
        if pkg:
            return f"Paquete: {pkg.name}"
        return "Paquete: Desconocido"
    if reward_type == RewardType.VIP_ACCESS:
        if tariff:
            return f"VIP: {tariff.name}"
        return "VIP: Desconocido"
    return ""


def build_reward_confirm_text_and_keyboard(
    data: dict, pkg=None, tariff=None
) -> tuple[str, InlineKeyboardMarkup]:
    """Función pura (sin estado ni side-effects). Soporte para UI de admin rewards (reward confirm).
    1:1 de lógica previamente inline (item34, arch-enforcer). Precedent item7/8/9.
    """
    name = data.get("name", "")
    description = data.get("description") or "Sin descripcion"
    reward_type = data.get("reward_type")
    type_text = compute_reward_type_text(
        reward_type,
        besito_amount=data.get("besito_amount"),
        pkg=pkg,
        tariff=tariff,
    )
    text = f"""🎩 Lucien:

Resumen de la recompensa:

🎁 {name}
📝 {description}
📋 Tipo: {reward_type.value if reward_type else ""}
💎 Contenido: {type_text}

Crear esta recompensa?"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Crear", callback_data="confirm_create_reward")],
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_missions")],
        ]
    )
    return text, keyboard


def build_reward_list_entry_and_button(reward) -> tuple[str, list[InlineKeyboardButton]]:
    """Función pura (sin estado ni side-effects). Soporte para UI de admin rewards (list entry).
    1:1 de lógica previamente inline (item34, arch-enforcer). Precedent item7/8/9.
    """
    status = "✅" if reward.is_active else "❌"
    entry_text = f"{status} {reward.name[:30]}"
    button = InlineKeyboardButton(
        text=entry_text,
        callback_data=RewardAdminDetailCallback(reward_id=reward.id).pack(),
    )
    return entry_text, [button]


def build_reward_detail_text_and_keyboard(reward) -> tuple[str, InlineKeyboardMarkup]:
    """Función pura (sin estado ni side-effects). Soporte para UI de admin rewards (detail).
    1:1 de lógica previamente inline (item34, arch-enforcer). Precedent item7/8/9.
    """
    status = "✅ Activo" if reward.is_active else "❌ Inactivo"
    content_text = ""
    if reward.reward_type.value == "besitos":
        content_text = f"{reward.besito_amount} besitos"
    elif reward.reward_type.value == "package" and reward.package:
        content_text = f"Paquete: {reward.package.name}"
    elif reward.reward_type.value == "vip_access" and reward.tariff:
        content_text = f"VIP: {reward.tariff.name}"
    text = f"""🎩 Lucien:

🎁 {reward.name}

📝 {reward.description or "Sin descripcion"}

📋 Informacion:
   • Tipo: {reward.reward_type.value}
   • Contenido: {content_text}
   • Estado: {status}

Que deseas hacer?"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{'Desactivar' if reward.is_active else 'Activar'}",
                    callback_data=RewardToggleCallback(reward_id=reward.id).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑️ Eliminar",
                    callback_data=RewardDeleteCallback(reward_id=reward.id).pack(),
                )
            ],
            [InlineKeyboardButton(text="🔙 Volver", callback_data="list_rewards")],
        ]
    )
    return text, keyboard


def build_reward_delete_confirm_keyboard(reward_id: int) -> InlineKeyboardMarkup:
    """Función pura (sin estado ni side-effects). Soporte para UI de admin rewards (delete confirm).
    1:1 de lógica previamente inline (item34, arch-enforcer). Precedent item7/8/9.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Si, eliminar",
                    callback_data=RewardDeleteCallback(reward_id=reward_id, confirmed=True).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Cancelar",
                    callback_data=RewardAdminDetailCallback(reward_id=reward_id).pack(),
                )
            ],
        ]
    )


def build_reward_created_text(reward) -> str:
    """Función pura (sin estado ni side-effects). Soporte para UI de admin rewards (create success).
    1:1 de lógica previamente inline (item34, arch-enforcer). Precedent item7/8/9.
    """
    return f"""🎩 Lucien:

Recompensa creada exitosamente!

🎁 {reward.name}
📋 Tipo: {reward.reward_type.value}

La recompensa esta lista para usarse en misiones."""


def build_reward_error_text(action: str = "crear la recompensa") -> str:
    """Función pura (sin estado ni side-effects). Soporte para UI de admin rewards (error).
    1:1 de lógica previamente inline (item34, arch-enforcer). Precedent item7/8/9.
    """
    return f"Error al {action}."


def build_back_only_keyboard() -> InlineKeyboardMarkup:
    """Función pura (sin estado ni side-effects). Soporte para UI de admin rewards (back only kb).
    1:1 de lógica previamente inline (item34, arch-enforcer). Precedent item7/8/9.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 Volver", callback_data="admin_missions")]]
    )


# ==================== WIZARD CREAR RECOMPENSA ====================


@router.callback_query(F.data == "create_reward", lambda cb: is_admin(cb.from_user.id))
async def create_reward_start(callback: CallbackQuery, state: FSMContext):
    """Inicia wizard de recompensa"""
    await callback.message.edit_text(
        """🎩 Lucien:

Vamos a crear una nueva recompensa...

Paso 1 de 5: Nombre

Indica un nombre descriptivo:
Ejemplo: 50 Besitos de regalo""",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_missions")]
            ]
        ),
    )
    await state.set_state(RewardWizardStates.waiting_name)
    await callback.answer()


@router.message(RewardWizardStates.waiting_name)
async def process_reward_name(message: Message, state: FSMContext):
    """Procesa nombre de recompensa"""
    name = message.text.strip()
    if len(name) < 3:
        await message.answer("El nombre debe tener al menos 3 caracteres.")
        return

    await state.update_data(name=name)
    await message.answer(
        """🎩 Lucien:

Paso 2 de 5: Descripcion

Escribe una descripcion (opcional):
Ejemplo: Recibe 50 besitos al completar la mision

O envia /skip para omitir.""",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_missions")]
            ]
        ),
    )
    await state.set_state(RewardWizardStates.waiting_description)


@router.message(RewardWizardStates.waiting_description)
async def process_reward_description(message: Message, state: FSMContext):
    """Procesa descripcion de recompensa"""
    description = None if message.text == "/skip" else message.text.strip()
    await state.update_data(description=description)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💋 Besitos",
                    callback_data=RewardTypeCallback(reward_type="besitos").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="📦 Paquete de fotos",
                    callback_data=RewardTypeCallback(reward_type="package").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="👑 Acceso VIP",
                    callback_data=RewardTypeCallback(reward_type="vip_access").pack(),
                )
            ],
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_missions")],
        ]
    )

    await message.answer(
        """🎩 Lucien:

Paso 3 de 5: Tipo de recompensa

Selecciona el tipo:""",
        reply_markup=keyboard,
    )
    await state.set_state(RewardWizardStates.selecting_type)


@router.callback_query(RewardWizardStates.selecting_type, RewardTypeCallback.filter())
async def select_reward_type(
    callback: CallbackQuery, state: FSMContext, callback_data: RewardTypeCallback
):
    """Selecciona tipo de recompensa"""
    # Validar que el tipo sea válido
    valid_types = {"besitos", "package", "vip_access"}
    if callback_data.reward_type not in valid_types:
        await callback.answer("Tipo inválido", show_alert=True)
        return

    reward_type = RewardType(callback_data.reward_type)

    await state.update_data(reward_type=reward_type)

    if reward_type == RewardType.BESITOS:
        await callback.message.edit_text(
            """🎩 Lucien:

Paso 4 de 5: Cantidad de besitos

Indica cuantos besitos otorga:
Ejemplo: 50""",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_missions")]
                ]
            ),
        )
        await state.set_state(RewardWizardStates.waiting_besito_amount)

    elif reward_type == RewardType.PACKAGE:
        await show_package_selection(callback, state)

    elif reward_type == RewardType.VIP_ACCESS:
        await show_tariff_selection(callback, state)

    await callback.answer()


@router.message(RewardWizardStates.waiting_besito_amount)
async def process_besito_amount(message: Message, state: FSMContext):
    """Procesa cantidad de besitos"""
    try:
        amount = int(message.text.strip())
        if amount < 1:
            raise ValueError("Debe ser mayor a 0")
    except ValueError:
        await message.answer("Por favor indica un numero valido mayor a 0.")
        return

    await state.update_data(besito_amount=amount)
    await show_reward_confirmation(message, state)


async def show_package_selection(callback: CallbackQuery, state: FSMContext):
    """Muestra seleccion de paquetes"""
    with get_service(RewardService) as reward_service:
        packages = reward_service.get_available_packages_for_rewards()

    text, button_rows = build_package_selection_text_and_buttons(packages)
    await callback.message.edit_text(
        text, reply_markup=InlineKeyboardMarkup(inline_keyboard=button_rows)
    )
    await state.set_state(RewardWizardStates.selecting_package)


@router.callback_query(RewardWizardStates.selecting_package, RewardSelectPkgCallback.filter())
async def select_package_for_reward(
    callback: CallbackQuery, state: FSMContext, callback_data: RewardSelectPkgCallback
):
    """Selecciona paquete para recompensa"""
    package_id = callback_data.pkg_id

    await state.update_data(package_id=package_id)
    await show_reward_confirmation(callback, state)
    await callback.answer()


@router.callback_query(
    RewardWizardStates.selecting_package,
    F.data == "create_package_for_reward",
    lambda cb: is_admin(cb.from_user.id),
)
async def create_package_for_reward(callback: CallbackQuery, state: FSMContext):
    """Inicia creacion de paquete desde recompensa"""
    await callback.message.edit_text(
        """🎩 Lucien:

Creando paquete para la recompensa...

Paso 1 de 5: Nombre del paquete

Indica un nombre descriptivo:
Ejemplo: Fotos exclusivas de marzo""",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_missions")]
            ]
        ),
    )
    await state.set_state(PackageFromRewardStates.waiting_name)
    await callback.answer()


# ==================== WIZARD PAQUETE DESDE RECOMPENSA ====================


@router.message(PackageFromRewardStates.waiting_name)
async def process_pkg_name_from_reward(message: Message, state: FSMContext):
    """Procesa nombre de paquete desde recompensa"""
    name = message.text.strip()
    if len(name) < 3:
        await message.answer("El nombre debe tener al menos 3 caracteres.")
        return

    await state.update_data(pkg_name=name)
    await message.answer(
        """🎩 Lucien:

Paso 2 de 5: Descripcion del paquete

Escribe una descripcion (opcional):
Ejemplo: Una coleccion especial de fotos

O envia /skip para omitir.""",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_missions")]
            ]
        ),
    )
    await state.set_state(PackageFromRewardStates.waiting_description)


@router.message(PackageFromRewardStates.waiting_description)
async def process_pkg_desc_from_reward(message: Message, state: FSMContext):
    """Procesa descripcion de paquete desde recompensa"""
    description = None if message.text == "/skip" else message.text.strip()
    await state.update_data(pkg_description=description)

    await message.answer(
        """🎩 Lucien:

Paso 3 de 5: Cargar archivos

Envia las fotos, videos o archivos.
Puedes enviar varios archivos uno por uno.

Cuando termines, envia /done""",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_missions")]
            ]
        ),
    )
    await state.update_data(pkg_files=[])
    await state.set_state(PackageFromRewardStates.waiting_files)


@router.message(PackageFromRewardStates.waiting_files)
async def process_pkg_files_from_reward(message: Message, state: FSMContext):
    """Procesa archivos del paquete desde recompensa"""
    if message.text == "/done":
        data = await state.get_data()
        files = data.get("pkg_files", [])

        if not files:
            await message.answer("Debes agregar al menos un archivo.")
            return

        await ask_pkg_stocks_from_reward(message, state)
        return

    # Procesar archivo
    file_id = None
    file_type = None
    file_name = None

    if message.photo:
        file_id = message.photo[-1].file_id
        file_type = "photo"
    elif message.video:
        file_id = message.video.file_id
        file_type = "video"
    elif message.document:
        file_id = message.document.file_id
        file_type = "document"
        file_name = message.document.file_name
    elif message.animation:
        file_id = message.animation.file_id
        file_type = "animation"
    else:
        await message.answer("Envia una foto, video, documento o GIF.")
        return

    data = await state.get_data()
    files = data.get("pkg_files", [])
    files.append({"file_id": file_id, "file_type": file_type, "file_name": file_name})
    await state.update_data(pkg_files=files)

    await message.answer(f"Archivo agregado. Total: {len(files)}. Envia mas o /done")


async def ask_pkg_stocks_from_reward(message: Message, state: FSMContext):
    """Pregunta stocks del paquete desde recompensa"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="♾️ Ilimitado", callback_data="pkg_reward_stock_unlimited")],
            [InlineKeyboardButton(text="📦 Limitado", callback_data="pkg_reward_stock_limited")],
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_missions")],
        ]
    )

    await message.answer(
        """🎩 Lucien:

Paso 4 de 5: Stock para recompensas

El stock de tienda se configurara como No disponible.

Stock para recompensas:""",
        reply_markup=keyboard,
    )
    await state.set_state(PackageFromRewardStates.waiting_reward_stock)


@router.callback_query(
    PackageFromRewardStates.waiting_reward_stock, F.data == "pkg_reward_stock_unlimited"
)
async def pkg_reward_stock_unlimited(callback: CallbackQuery, state: FSMContext):
    """Stock ilimitado para recompensas"""
    await state.update_data(pkg_reward_stock=-1)
    await show_pkg_confirmation_from_reward(callback, state)
    await callback.answer()


@router.callback_query(
    PackageFromRewardStates.waiting_reward_stock, F.data == "pkg_reward_stock_limited"
)
async def pkg_reward_stock_limited(callback: CallbackQuery, state: FSMContext):
    """Pide cantidad limitada para recompensas"""
    await callback.message.edit_text(
        """🎩 Lucien:

Indica la cantidad de unidades:
Ejemplo: 50""",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_missions")]
            ]
        ),
    )
    await callback.answer()


@router.message(PackageFromRewardStates.waiting_reward_stock)
async def process_pkg_reward_stock(message: Message, state: FSMContext):
    """Procesa stock de recompensas del paquete"""
    try:
        stock = int(message.text.strip())
        if stock < 0:
            raise ValueError("Debe ser 0 o mayor")
    except ValueError:
        await message.answer("Indica un numero valido (0 o mayor).")
        return

    await state.update_data(pkg_reward_stock=stock)
    await show_pkg_confirmation_from_reward(message, state)


async def show_pkg_confirmation_from_reward(target, state: FSMContext):
    """Muestra confirmacion del paquete desde recompensa"""
    data = await state.get_data()

    name = data.get("pkg_name", "")
    description = data.get("pkg_description", "Sin descripcion")
    files = data.get("pkg_files", [])
    reward_stock = data.get("pkg_reward_stock", -1)

    stock_text = "Ilimitado" if reward_stock == -1 else str(reward_stock)

    text = f"""🎩 Lucien:

Resumen del paquete:

📦 {name}
📝 {description}
📁 {len(files)} archivos
🎁 Stock recompensas: {stock_text}
🛒 Stock tienda: No disponible

Crear este paquete?"""

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Crear paquete", callback_data="confirm_create_pkg_from_reward"
                )
            ],
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_missions")],
        ]
    )

    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=keyboard)
    else:
        await target.answer(text, reply_markup=keyboard)

    await state.set_state(PackageFromRewardStates.confirming)


@router.callback_query(
    PackageFromRewardStates.confirming, F.data == "confirm_create_pkg_from_reward"
)
async def confirm_create_pkg_from_reward(callback: CallbackQuery, state: FSMContext):
    """Crea el paquete y retorna a la recompensa"""
    data = await state.get_data()

    try:
        files = data.get("pkg_files", [])
        with get_service(RewardService) as reward_service:
            package = reward_service.create_package_for_reward_wizard(
                name=data.get("pkg_name"),
                description=data.get("pkg_description"),
                store_stock=-2,
                reward_stock=data.get("pkg_reward_stock", -1),
                files=files,
                created_by=callback.from_user.id,
            )
        # Guardar package_id para la recompensa
        await state.update_data(package_id=package.id)

        await callback.message.edit_text(
            f"""🎩 Lucien:

Paquete creado exitosamente!

📦 {package.name}
📁 {len(files)} archivos

Continuando con la recompensa..."""
        )

        # Continuar con confirmacion de recompensa
        await show_reward_confirmation(callback, state)
        logger.info(f"Paquete creado desde recompensa: {package.name}")

    except Exception as e:
        logger.error(f"Error creando paquete: {e}")
        await callback.message.edit_text(
            "Error al crear el paquete.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_missions")]
                ]
            ),
        )
        await state.clear()

    await callback.answer()


# ==================== SELECCION TARIFA VIP ====================


async def show_tariff_selection(callback: CallbackQuery, state: FSMContext):
    """Muestra seleccion de tarifas VIP"""
    with get_service(RewardService) as reward_service:
        tariffs = reward_service.get_all_tariffs(active_only=True)

    if not tariffs:
        await callback.message.edit_text(
            """🎩 Lucien:

No hay tarifas VIP configuradas.

Crea una tarifa primero desde el panel VIP.""",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_missions")]
                ]
            ),
        )
        await state.clear()
        return

    buttons = build_tariff_selection_buttons(tariffs)
    await callback.message.edit_text(
        """🎩 Lucien:

Paso 4 de 5: Seleccionar tarifa VIP

Elige la tarifa para el acceso VIP:""",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await state.set_state(RewardWizardStates.selecting_tariff)


@router.callback_query(RewardWizardStates.selecting_tariff, SelectTariffCallback.filter())
async def select_tariff_for_reward(
    callback: CallbackQuery, state: FSMContext, callback_data: SelectTariffCallback
):
    """Selecciona tarifa para recompensa VIP"""
    tariff_id = callback_data.tariff_id
    logger.info(
        f"{__name__} | select_tariff_for_reward | user_id={callback.from_user.id} | tariff_id={tariff_id}"
    )

    await state.update_data(tariff_id=tariff_id)
    await show_reward_confirmation(callback, state)
    await callback.answer()


# ==================== CONFIRMACION RECOMPENSA ====================


async def show_reward_confirmation(target, state: FSMContext):
    """Muestra confirmacion de recompensa"""
    data = await state.get_data()

    reward_type = data.get("reward_type")

    pkg = None
    tariff = None
    with get_service(RewardService) as reward_service:
        if reward_type == RewardType.PACKAGE:
            package_id = data.get("package_id")
            if package_id:
                pkg = reward_service.get_package(package_id)
        elif reward_type == RewardType.VIP_ACCESS:
            tariff_id = data.get("tariff_id")
            if tariff_id:
                tariff = reward_service.get_tariff(tariff_id)

    text, keyboard = build_reward_confirm_text_and_keyboard(data, pkg=pkg, tariff=tariff)

    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=keyboard)
    else:
        await target.answer(text, reply_markup=keyboard)

    await state.set_state(RewardWizardStates.confirming)


@router.callback_query(RewardWizardStates.confirming, F.data == "confirm_create_reward")
async def confirm_create_reward(callback: CallbackQuery, state: FSMContext):
    """Crea la recompensa"""
    data = await state.get_data()
    with get_service(RewardService) as reward_service:
        try:
            reward_type = data.get("reward_type")

            if reward_type == RewardType.BESITOS:
                reward = reward_service.create_reward_besitos(
                    name=data.get("name"),
                    description=data.get("description"),
                    besito_amount=data.get("besito_amount"),
                    created_by=callback.from_user.id,
                )

            elif reward_type == RewardType.PACKAGE:
                reward = reward_service.create_reward_package(
                    name=data.get("name"),
                    description=data.get("description"),
                    package_id=data.get("package_id"),
                    created_by=callback.from_user.id,
                )

            elif reward_type == RewardType.VIP_ACCESS:
                reward = reward_service.create_reward_vip(
                    name=data.get("name"),
                    description=data.get("description"),
                    tariff_id=data.get("tariff_id"),
                    created_by=callback.from_user.id,
                )

            await callback.message.edit_text(
                build_reward_created_text(reward),
                reply_markup=build_back_only_keyboard(),
            )
            logger.info(f"reward_admin_handlers | confirm_create_reward | user_id={callback.from_user.id} | reward_id={reward.id} | result=success")
        except Exception as e:
            logger.error(f"Error creando recompensa: {e}")
            await callback.message.edit_text(
                build_reward_error_text("crear la recompensa"),
                reply_markup=build_back_only_keyboard(),
            )

        await state.clear()
        await callback.answer()

    # ==================== LISTAR RECOMPENSAS ====================


@router.callback_query(F.data == "list_rewards", lambda cb: is_admin(cb.from_user.id))
async def list_rewards(callback: CallbackQuery):
    """Lista todas las recompensas"""
    with get_service(RewardService) as reward_service:
        rewards = reward_service.get_all_rewards(active_only=False)

        if not rewards:
            await callback.message.edit_text(
                "No hay recompensas registradas.",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_missions")]
                    ]
                ),
            )
            await callback.answer()
            return

        text = "🎩 Lucien:\n\nRecompensas registradas:\n\n"
        buttons = []

        for reward in rewards:
            entry_text, button_row = build_reward_list_entry_and_button(reward)
            text += entry_text + "\n"
            buttons.append(button_row)

        buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="admin_missions")])

        await callback.message.edit_text(
            text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
        await callback.answer()

    # ==================== VER DETALLE DE RECOMPENSA ====================


@router.callback_query(RewardAdminDetailCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def reward_admin_detail(callback: CallbackQuery, callback_data: RewardAdminDetailCallback):
    """Muestra detalles de una recompensa"""
    reward_id = callback_data.reward_id

    with get_service(RewardService) as reward_service:
        reward = reward_service.get_reward(reward_id)

        if not reward:
            await callback.answer("Recompensa no encontrada", show_alert=True)
            return

        text, keyboard = build_reward_detail_text_and_keyboard(reward)
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()


@router.callback_query(RewardToggleCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def toggle_reward(callback: CallbackQuery, callback_data: RewardToggleCallback):
    """Activa/desactiva una recompensa"""
    reward_id = callback_data.reward_id

    with get_service(RewardService) as reward_service:
        reward = reward_service.get_reward(reward_id)

        if not reward:
            await callback.answer("Recompensa no encontrada", show_alert=True)
            return

        reward_service.update_reward(reward_id, is_active=not reward.is_active)

        status = "activada" if not reward.is_active else "desactivada"
        await callback.answer(f"Recompensa {status}")

        # Show updated detail
        new_reward = reward_service.get_reward(reward_id)
        if new_reward:
            await reward_admin_detail(callback, RewardAdminDetailCallback(reward_id=reward_id))
        await callback.answer()


@router.callback_query(RewardDeleteCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def delete_reward_confirm(callback: CallbackQuery, callback_data: RewardDeleteCallback):
    """Confirma o ejecuta eliminacion de recompensa"""
    reward_id = callback_data.reward_id

    with get_service(RewardService) as reward_service:
        if callback_data.confirmed:
            # Execute deletion
            success = reward_service.delete_reward(reward_id)

            if success:
                await callback.message.edit_text(
                    "🎩 Lucien:\n\n✅ Recompensa eliminada correctamente.",
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[
                            [InlineKeyboardButton(text="🔙 Volver", callback_data="list_rewards")]
                        ]
                    ),
                )
            else:
                await callback.message.edit_text(
                    "Error al eliminar la recompensa.",
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[
                            [InlineKeyboardButton(text="🔙 Volver", callback_data="list_rewards")]
                        ]
                    ),
                )
            await callback.answer()
            return

    # Show confirmation keyboard
    keyboard = build_reward_delete_confirm_keyboard(reward_id)
    await callback.message.edit_text(
        "🎩 Lucien:\n\n"
        "Estas seguro de eliminar esta recompensa?\n\n"
        "Esta accion no se puede deshacer.",
        reply_markup=keyboard,
    )
    await callback.answer()
