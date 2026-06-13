"""
Handlers Admin de Nurture / User Content Lifecycle - Lucien Bot

Admin-only FSM wizard para CRUD de NurtureSequence + NurtureStep.
Sigue patrón EXACTO de package_handlers.py (StatesGroup, waiting_*,
callbacks con data, get_service, is_admin guard, Lucien voice, inline lists + select, test send).

- Secuencias: nombre, desc, audience (VIP/FREE/ALL), active.
- Steps: orden, delay_hours, seleccionar Package real (via NurtureService
  delegates internally to Package for real pkg content) o fallback text.
- "Enviar test delivery": reutiliza NurtureService.deliver_test_package
  (delegates to Package.deliver) a tg del admin actual.
- Sin comandos user-facing. Todo background/silencioso via scheduler + event.

Handlers llaman EXACTAMENTE 1 service (via with get_service).
"""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from keyboards.callback_data import (
    NurtureSequenceDetailCallback,
    NurtureSequenceListCallback,
    NurtureStepDetailCallback,
    NurtureStepSelectPackageCallback,
    NurtureTestSendCallback,
    NurtureToggleSequenceCallback,
    NurtureToggleStepCallback,
)
from keyboards.inline_keyboards import back_keyboard, cancel_keyboard
from models.models import NurtureAudience
from services import get_service
from services.nurture_service import NurtureService
from utils.admin import is_admin
from utils.lucien_voice import LucienVoice

logger = logging.getLogger(__name__)
router = Router()


# Estados FSM para wizard de secuencias nurture (siguiendo PackageWizardStates)
class NurtureSequenceWizardStates(StatesGroup):
    waiting_name = State()
    waiting_description = State()
    waiting_audience = State()
    confirming = State()


class NurtureStepWizardStates(StatesGroup):
    selecting_sequence = State()
    waiting_step_order = State()
    waiting_delay = State()
    selecting_package = State()
    waiting_fallback = State()
    confirming = State()


# ==================== MENÚ NURTURE (entry desde gamification admin) ====================


@router.callback_query(F.data == "manage_nurture", lambda cb: is_admin(cb.from_user.id))
async def manage_nurture_menu(callback: CallbackQuery):
    """Menú principal de gestión de nurture sequences (post-VIP lifecycle)."""
    with get_service(NurtureService) as nurture_service:
        sequences = nurture_service.get_all_sequences(active_only=False)
        active = sum(1 for s in sequences if s.is_active)
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="➕ Crear nueva secuencia", callback_data="create_nurture_sequence"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📋 Ver secuencias activas",
                        callback_data=NurtureSequenceListCallback(list_type="active").pack(),
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📋 Ver todas las secuencias",
                        callback_data=NurtureSequenceListCallback(list_type="all").pack(),
                    )
                ],
                [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_gamification")],
            ]
        )
        await callback.message.edit_text(
            f"""🎩 <b>Lucien:</b>

<i>El embudo de contenido que cultiva devoción más allá de la conversión...</i>

🌱 <b>Nurture / User Content Lifecycle</b>

📊 <b>Secuencias:</b> {len(sequences)} total | {active} activas

<i>Cada secuencia entrega paquetes (o texto) en delays relativos. Audience: VIP (default), free o all. Event-driven desde activación VIP. Real delivery vía PackageService + Scheduler.</i>""",
            reply_markup=keyboard,
            parse_mode="HTML",
        )
        await callback.answer()


# ==================== LISTAR SECUENCIAS ====================


@router.callback_query(NurtureSequenceListCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def list_nurture_sequences(
    callback: CallbackQuery, callback_data: NurtureSequenceListCallback
):
    """Lista secuencias nurture."""
    list_type = callback_data.list_type
    active_only = list_type == "active"

    with get_service(NurtureService) as nurture_service:
        seqs = nurture_service.get_all_sequences(active_only=active_only)

        if not seqs:
            await callback.message.edit_text(
                """🎩 <b>Lucien:</b>

<i>No hay secuencias nurture configuradas...</i>

👉 <i>Cree una usando "Crear nueva secuencia".</i>""",
                reply_markup=back_keyboard("manage_nurture"),
                parse_mode="HTML",
            )
            await callback.answer()
            return

        text = f"""🎩 <b>Lucien:</b>

<i>Las secuencias de cuidado que siguen al círculo VIP...</i>

🌱 <b>Secuencias {"activas" if active_only else "registradas"}:</b>

"""
        buttons = []
        for seq in seqs:
            status = "✅" if seq.is_active else "❌"
            aud = seq.audience.value if hasattr(seq.audience, "value") else str(seq.audience)
            text += f"{status} <b>{seq.name}</b> (aud: {aud})\n   {seq.description or 'Sin descripción'}\n\n"
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"{status} {seq.name[:35]}",
                        callback_data=NurtureSequenceDetailCallback(sequence_id=seq.id).pack(),
                    )
                ]
            )

        buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="manage_nurture")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()


# ==================== PURE HELPERS (for <=50 LOC + 1svc handlers per hardener) ====================


def build_nurture_seq_detail_text_and_keyboard(
    seq, enriched_steps: list[dict], seq_id: int
) -> tuple[str, InlineKeyboardMarkup]:
    """Función pura (sin estado ni side-effects). UI builder extracted from detail handler.
    1:1 port of inline logic; keeps nurture_sequence_detail thin + exactly 1 NurtureService call.
    """
    aud = seq.audience.value if hasattr(seq.audience, "value") else str(seq.audience)
    status = "✅ Activa" if seq.is_active else "❌ Inactiva"
    step_lines = ""
    buttons = []
    for info in enriched_steps:
        st = info["step"]
        pkg_name = (
            f" 📦 {info['pkg_name']}"
            if info.get("pkg_name")
            else (" 📝 fallback" if info.get("has_fallback") else "")
        )
        st_status = "✅" if st.is_active else "❌"
        step_lines += f"  {st_status} Paso {st.step_order}: +{st.delay_hours}h{pkg_name}\n"
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{st_status} Paso {st.step_order} (+{st.delay_hours}h)",
                    callback_data=NurtureStepDetailCallback(step_id=st.id).pack(),
                )
            ]
        )
    buttons.append(
        [InlineKeyboardButton(text="➕ Agregar paso", callback_data=f"add_nurture_step_{seq_id}")]
    )
    buttons.append(
        [
            InlineKeyboardButton(
                text=f"{'Desactivar' if seq.is_active else 'Activar'} secuencia",
                callback_data=NurtureToggleSequenceCallback(sequence_id=seq_id).pack(),
            )
        ]
    )
    buttons.append(
        [
            InlineKeyboardButton(
                text="🔙 Volver", callback_data=NurtureSequenceListCallback(list_type="all").pack()
            )
        ]
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    text = f"""🎩 <b>Lucien:</b>

<i>Secuencia de nurture seleccionada...</i>

🌱 <b>{seq.name}</b>

📝 <i>{seq.description or "Sin descripción"}</i>

🎯 <b>Audience:</b> {aud}
📊 <b>Estado:</b> {status}
📋 <b>Pasos ({len(enriched_steps)}):</b>
{step_lines or "  (sin pasos aún)"}

<i>Usa "Enviar test" en un paso para probar delivery real al admin actual.</i>"""
    return text, keyboard


# ==================== DETALLE SECUENCIA + STEPS + TEST ====================


@router.callback_query(NurtureSequenceDetailCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def nurture_sequence_detail(
    callback: CallbackQuery, callback_data: NurtureSequenceDetailCallback
):
    """Muestra detalle + steps. Thin: exactly 1 NurtureService call + pure UI helper (M2/M3)."""
    seq_id = callback_data.sequence_id

    with get_service(NurtureService) as nurture_service:
        seq = nurture_service.get_sequence(seq_id)
        if not seq:
            await callback.answer("Secuencia no encontrada", show_alert=True)
            return
        enriched = nurture_service.get_steps_with_package_info(seq_id, active_only=False)
        text, keyboard = build_nurture_seq_detail_text_and_keyboard(seq, enriched, seq_id)
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()


@router.callback_query(NurtureToggleSequenceCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def toggle_nurture_sequence(
    callback: CallbackQuery, callback_data: NurtureToggleSequenceCallback
):
    """Toggle active de secuencia."""
    if not is_admin(callback.from_user.id):
        await callback.answer("No autorizado", show_alert=True)
        return
    seq_id = callback_data.sequence_id
    with get_service(NurtureService) as svc:
        seq = svc.get_sequence(seq_id)
        if seq:
            svc.update_sequence(seq_id, is_active=not seq.is_active)
    await callback.answer("Secuencia actualizada")
    await nurture_sequence_detail(callback, NurtureSequenceDetailCallback(sequence_id=seq_id))


# ==================== CREAR SECUENCIA WIZARD ====================


@router.callback_query(F.data == "create_nurture_sequence", lambda cb: is_admin(cb.from_user.id))
async def create_nurture_sequence_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        """🎩 <b>Lucien:</b>

<i>Vamos a definir una nueva secuencia de contenido timed...</i>

📋 <b>Paso 1 de 4:</b> Nombre de la secuencia
Ej: <code>Post-VIP Bienvenida 7 dias</code>""",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(NurtureSequenceWizardStates.waiting_name)
    await callback.answer()


@router.message(NurtureSequenceWizardStates.waiting_name)
async def process_nurture_seq_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 3:
        await message.answer(
            "El nombre debe tener al menos 3 caracteres.",
            reply_markup=cancel_keyboard(),
            parse_mode="HTML",
        )
        return
    await state.update_data(name=name)
    await message.answer(
        """🎩 <b>Lucien:</b>

<i>Ahora una descripción (opcional, /skip para omitir).</i>

📋 <b>Paso 2 de 4:</b> Descripción""",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(NurtureSequenceWizardStates.waiting_description)


@router.message(NurtureSequenceWizardStates.waiting_description)
async def process_nurture_seq_desc(message: Message, state: FSMContext):
    desc = None if message.text == "/skip" else message.text.strip()
    await state.update_data(description=desc)
    # Audience choice via buttons (no text)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👑 VIP (recomendado post-conversión)", callback_data="nurture_aud_vip"
                )
            ],
            [InlineKeyboardButton(text="🆓 FREE", callback_data="nurture_aud_free")],
            [InlineKeyboardButton(text="🌍 ALL (free + vip)", callback_data="nurture_aud_all")],
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="cancel")],
        ]
    )
    await message.answer(
        """🎩 <b>Lucien:</b>

<i>Seleccione la audiencia objetivo de la secuencia.</i>

📋 <b>Paso 3 de 4:</b> Audience""",
        reply_markup=kb,
        parse_mode="HTML",
    )
    await state.set_state(NurtureSequenceWizardStates.waiting_audience)


@router.callback_query(
    NurtureSequenceWizardStates.waiting_audience, F.data.startswith("nurture_aud_")
)
async def process_nurture_seq_audience(callback: CallbackQuery, state: FSMContext):
    data = callback.data
    aud = NurtureAudience.VIP
    if "free" in data:
        aud = NurtureAudience.FREE
    elif "all" in data:
        aud = NurtureAudience.ALL
    await state.update_data(audience=aud.value)
    await callback.message.edit_text(
        f"""🎩 <b>Lucien:</b>

<i>Audience: {aud.value}. Confirme para crear.</i>

📋 <b>Paso 4 de 4:</b> Confirmar creación de secuencia.""",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Crear secuencia", callback_data="confirm_create_nurture_seq"
                    )
                ],
                [InlineKeyboardButton(text="❌ Cancelar", callback_data="cancel")],
            ]
        ),
        parse_mode="HTML",
    )
    await state.set_state(NurtureSequenceWizardStates.confirming)
    await callback.answer()


@router.callback_query(F.data == "confirm_create_nurture_seq", lambda cb: is_admin(cb.from_user.id))
async def confirm_create_nurture_sequence(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    with get_service(NurtureService) as svc:
        svc.create_sequence(
            name=data["name"],
            description=data.get("description"),
            audience=NurtureAudience(data.get("audience", "vip")),
            created_by=callback.from_user.id,
        )
    await state.clear()
    await callback.message.edit_text(
        f"""🎩 <b>Lucien:</b>

✅ <b>Secuencia creada:</b> {data["name"]}

Ahora agregue pasos (delay + package o texto) desde el detalle.""",
        reply_markup=back_keyboard("manage_nurture"),
        parse_mode="HTML",
    )
    await callback.answer()


# ==================== AGREGAR STEP (simple flow desde detail) ====================


@router.callback_query(F.data.startswith("add_nurture_step_"), lambda cb: is_admin(cb.from_user.id))
async def add_nurture_step_start(callback: CallbackQuery, state: FSMContext):
    seq_id = int(callback.data.split("_")[-1])
    await state.update_data(sequence_id=seq_id)
    await callback.message.edit_text(
        """🎩 <b>Lucien:</b>

<i>Defina el orden del paso (entero, ej 1,2,3... único por secuencia).</i>

Envíe número de orden del paso:""",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(NurtureStepWizardStates.waiting_step_order)
    await callback.answer()


@router.message(NurtureStepWizardStates.waiting_step_order)
async def process_nurture_step_order(message: Message, state: FSMContext):
    try:
        order = int(message.text.strip())
        if order < 1:
            raise ValueError
    except Exception:
        await message.answer(
            "Orden debe ser entero >=1", reply_markup=cancel_keyboard(), parse_mode="HTML"
        )
        return
    await state.update_data(step_order=order)
    await message.answer(
        """🎩 <b>Lucien:</b>

<i>Delay en horas desde el trigger (activación VIP o start). Ej: 24, 72, 168.</i>

Envíe delay_hours:""",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(NurtureStepWizardStates.waiting_delay)


@router.message(NurtureStepWizardStates.waiting_delay)
async def process_nurture_step_delay(message: Message, state: FSMContext):
    try:
        delay = int(message.text.strip())
        if delay < 0:
            raise ValueError
    except Exception:
        await message.answer(
            "delay_hours debe ser entero >=0", reply_markup=cancel_keyboard(), parse_mode="HTML"
        )
        return
    await state.update_data(delay_hours=delay)

    # List via Nurture delegate only (1 service per handler)
    with get_service(NurtureService) as nurture_service:
        pkgs = nurture_service.get_available_packages_for_steps()
    if not pkgs:
        # Allow fallback only path
        await message.answer(
            "No hay paquetes activos. Envíe texto fallback (o /skip para ninguno):",
            reply_markup=cancel_keyboard(),
            parse_mode="HTML",
        )
        await state.set_state(NurtureStepWizardStates.waiting_fallback)
        return

    buttons = []
    data = await state.get_data()
    seq_id = data["sequence_id"]
    s_order = data.get("step_order", 1)
    for p in pkgs[:12]:
        cb = NurtureStepSelectPackageCallback(
            sequence_id=seq_id, temp_step_order=s_order, package_id=p.id
        ).pack()
        buttons.append([InlineKeyboardButton(text=f"📦 {p.name[:28]}", callback_data=cb)])
    buttons.append(
        [
            InlineKeyboardButton(
                text="📝 Usar solo fallback text",
                callback_data=NurtureStepSelectPackageCallback(
                    sequence_id=seq_id, temp_step_order=s_order, package_id=0
                ).pack(),
            )
        ]
    )
    buttons.append([InlineKeyboardButton(text="❌ Cancelar", callback_data="cancel")])

    await message.answer(
        """🎩 <b>Lucien:</b>

<i>Seleccione el Package real a entregar en este paso (o fallback).</i>

📦 Paquetes disponibles:""",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML",
    )
    await state.set_state(NurtureStepWizardStates.selecting_package)


@router.callback_query(
    NurtureStepSelectPackageCallback.filter(), lambda cb: is_admin(cb.from_user.id)
)
async def nurture_pick_package_for_step(
    callback: CallbackQuery, state: FSMContext, callback_data: NurtureStepSelectPackageCallback
):
    """Wired to NurtureStepSelectPackageCallback (no ad-hoc string parse)."""
    seq_id = callback_data.sequence_id
    step_order = callback_data.temp_step_order
    pkg_id = callback_data.package_id if callback_data.package_id > 0 else None

    await state.update_data(sequence_id=seq_id, step_order=step_order, package_id=pkg_id)

    if pkg_id:
        await callback.message.edit_text(
            f"Paquete seleccionado ID {pkg_id}. Envíe /skip o texto fallback opcional, o /done para crear sin fallback.",
            reply_markup=cancel_keyboard(),
            parse_mode="HTML",
        )
        await state.set_state(NurtureStepWizardStates.waiting_fallback)
    else:
        await callback.message.edit_text(
            "Sin paquete. Envíe el fallback_text para el paso (texto plano/HTML simple):",
            reply_markup=cancel_keyboard(),
            parse_mode="HTML",
        )
        await state.set_state(NurtureStepWizardStates.waiting_fallback)
    await callback.answer()


@router.message(NurtureStepWizardStates.waiting_fallback)
async def process_nurture_step_fallback(message: Message, state: FSMContext):
    fb = None if message.text in ("/skip", "/done") else message.text.strip()
    data = await state.get_data()
    seq_id = data["sequence_id"]
    order = data["step_order"]
    delay = data.get("delay_hours", 24)
    pkg_id = data.get("package_id")

    with get_service(NurtureService) as svc:
        step = svc.create_step(
            sequence_id=seq_id,
            step_order=order,
            delay_hours=delay,
            package_id=pkg_id,
            fallback_text=fb,
        )
    await state.clear()
    if step:
        await message.answer(
            f"""🎩 <b>Lucien:</b>

✅ Paso {order} creado (+{delay}h) para secuencia {seq_id}.

Vuelva al detalle para ver lista de pasos y testear.""",
            reply_markup=back_keyboard("manage_nurture"),
            parse_mode="HTML",
        )
    else:
        await message.answer(
            LucienVoice.error_message("crear el paso nurture"),
            reply_markup=back_keyboard("manage_nurture"),
            parse_mode="HTML",
        )


# ==================== PURE HELPERS (step detail for 1svc + LOC) ====================


def build_nurture_step_detail_text_and_keyboard(
    info: dict, seq, step_id: int
) -> tuple[str, InlineKeyboardMarkup]:
    """Función pura (sin estado ni side-effects). UI builder for step_detail (like build_nurture_seq...).
    Keeps handler body thin + exactly 1 NurtureService.
    """
    step = info["step"]
    pkg_info = (
        f"📦 Paquete: {info.get('pkg_name') or step.package_id} (ID {step.package_id})"
        if step.package_id
        else f"📝 Fallback: {step.fallback_text[:60] if step.fallback_text else 'ninguno'}..."
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🧪 Enviar test delivery (a ti)",
                    callback_data=NurtureTestSendCallback(package_id=step.package_id or 0).pack(),
                )
            ]
            if step.package_id
            else [],
            [
                InlineKeyboardButton(
                    text=f"{'Desactivar' if step.is_active else 'Activar'} paso",
                    callback_data=NurtureToggleStepCallback(step_id=step_id).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Volver a secuencia",
                    callback_data=NurtureSequenceDetailCallback(
                        sequence_id=step.sequence_id
                    ).pack(),
                )
            ],
        ]
    )
    text = f"""🎩 <b>Lucien:</b>

<i>Paso de nurture...</i>

Secuencia: {seq.name if seq else step.sequence_id}
Paso #{step.step_order} | Delay: +{step.delay_hours}h
{pkg_info}
Estado: {"✅ activo" if step.is_active else "❌ inactivo"}

<i>El test usa NurtureService (delegates internally to Package for real pkg content) deliver real (Lucien intro + media groups) al admin actual.</i>"""
    return text, kb


# ==================== STEP DETAIL + TEST SEND (reusa deliver) ====================


@router.callback_query(NurtureStepDetailCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def nurture_step_detail(callback: CallbackQuery, callback_data: NurtureStepDetailCallback):
    """Step detail: exactly 1 NurtureService (via get_step + get_step_with_package_info delegate + pure build)."""
    step_id = callback_data.step_id
    with get_service(NurtureService) as svc:
        step = svc.get_step(step_id)
        if not step:
            await callback.answer("Step no encontrado", show_alert=True)
            return
        seq = svc.get_sequence(step.sequence_id)
        info = svc.get_step_with_package_info(step_id) or {
            "step": step,
            "pkg_name": None,
            "has_fallback": bool(step.fallback_text),
        }
        text, kb = build_nurture_step_detail_text_and_keyboard(info, seq, step_id)
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(NurtureToggleStepCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def toggle_nurture_step(callback: CallbackQuery, callback_data: NurtureToggleStepCallback):
    step_id = callback_data.step_id
    with get_service(NurtureService) as svc:
        step = svc.get_step(step_id)
        if step:
            svc.update_step(step_id, is_active=not step.is_active)
    await callback.answer("Paso actualizado")
    await nurture_step_detail(callback, NurtureStepDetailCallback(step_id=step_id))


@router.callback_query(NurtureTestSendCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def nurture_test_send(callback: CallbackQuery, callback_data: NurtureTestSendCallback):
    """Reusa deliver_package_to_user contra el propio admin (from_user.id) para prueba inmediata."""
    pkg_id = callback_data.package_id
    admin_id = callback.from_user.id
    if not pkg_id or pkg_id == 0:
        await callback.answer("Este paso usa fallback (sin pkg para test)", show_alert=True)
        return
    with get_service(NurtureService) as nurture_service:
        success, msg = await nurture_service.deliver_test_package(callback.bot, admin_id, pkg_id)
    await callback.answer(f"Test: {'OK' if success else 'FAIL'} - {msg[:60]}", show_alert=True)
    logger.info(
        f"nurture_admin | test_send | admin_id={admin_id} | pkg={pkg_id} | result={success}"
    )


# Cancel genérico (reutilizado de patrones)
@router.callback_query(F.data == "cancel")
async def cancel_nurture_wizard(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "🎩 <b>Lucien:</b>\n\n<i>Operación cancelada.</i>",
        reply_markup=back_keyboard("manage_nurture"),
        parse_mode="HTML",
    )
    await callback.answer()
