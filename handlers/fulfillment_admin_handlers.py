"""Admin handlers — cola de fulfillment del catálogo Kinky."""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from keyboards.callback_data import (
    FulfillmentAdminDeliverCallback,
    FulfillmentAdminItemCallback,
    FulfillmentAdminMarkCallback,
    FulfillmentAdminQueueCallback,
)
from models.models import FulfillmentKind, FulfillmentStatus
from services import get_service
from services.fulfillment_service import FulfillmentService
from services.store_service import StoreService
from utils.admin import is_admin
from utils.lucien_voice import LucienVoice

logger = logging.getLogger(__name__)
router = Router()


class FulfillmentAdminNotesStates(StatesGroup):
    awaiting_notes = State()


class FulfillmentAdminDeliverStates(StatesGroup):
    selecting_package = State()


def build_fulfillment_queue_menu_keyboard() -> InlineKeyboardMarkup:
    """Teclado filtros cola admin."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=LucienVoice.fulfillment_admin_filter_pending_input(),
                    callback_data=FulfillmentAdminQueueCallback(status="pending_input").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=LucienVoice.fulfillment_admin_filter_pending_diana(),
                    callback_data=FulfillmentAdminQueueCallback(status="pending").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=LucienVoice.fulfillment_admin_filter_failed(),
                    callback_data=FulfillmentAdminQueueCallback(status="failed").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=LucienVoice.fulfillment_admin_filter_fulfilled(),
                    callback_data=FulfillmentAdminQueueCallback(status="fulfilled").pack(),
                )
            ],
            [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_store")],
        ]
    )


def build_fulfillment_item_keyboard(
    fulfillment_id: int,
    user_id: int,
    *,
    filter_status: str = "pending",
    show_deliver: bool = False,
) -> InlineKeyboardMarkup:
    """Teclado acciones sobre item de cola."""
    rows = [
        [
            InlineKeyboardButton(
                text=LucienVoice.fulfillment_admin_mark_fulfilled_button(),
                callback_data=FulfillmentAdminMarkCallback(fulfillment_id=fulfillment_id).pack(),
            )
        ],
    ]
    if show_deliver:
        rows.append(
            [
                InlineKeyboardButton(
                    text=LucienVoice.fulfillment_admin_deliver_package_button(),
                    callback_data=f"fulfill_deliver_start:{fulfillment_id}:{filter_status}",
                )
            ]
        )
    rows.extend(
        [
            [
                InlineKeyboardButton(
                    text=LucienVoice.fulfillment_admin_contact_visitor_button(),
                    url=f"tg://user?id={user_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Volver",
                    callback_data=FulfillmentAdminQueueCallback(status=filter_status).pack(),
                )
            ],
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data == "fulfill_admin_menu", lambda cb: is_admin(cb.from_user.id))
async def fulfillment_admin_menu(callback: CallbackQuery):
    """Menú cola de entregas."""
    await callback.message.edit_text(
        LucienVoice.fulfillment_admin_queue_menu(),
        reply_markup=build_fulfillment_queue_menu_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(
    FulfillmentAdminQueueCallback.filter(), lambda cb: is_admin(cb.from_user.id)
)
async def fulfillment_admin_queue_list(
    callback: CallbackQuery, callback_data: FulfillmentAdminQueueCallback
):
    """Lista items de cola según filtro."""
    status_map = {
        "pending_input": FulfillmentStatus.PENDING_INPUT,
        "pending": FulfillmentStatus.PENDING_FULFILLMENT,
        "failed": FulfillmentStatus.FAILED,
        "fulfilled": FulfillmentStatus.FULFILLED,
    }
    status = status_map.get(callback_data.status)
    with get_service(FulfillmentService) as svc:
        items = svc.get_pending_queue(status=status, limit=20)
    if not items:
        await callback.answer(LucienVoice.fulfillment_admin_queue_empty(), show_alert=True)
        return
    buttons = []
    for row in items[:10]:
        label = f"#{row.id} · {row.product.name if row.product else '?'}"
        buttons.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=FulfillmentAdminItemCallback(
                        fulfillment_id=row.id,
                        filter_status=callback_data.status,
                    ).pack(),
                )
            ]
        )
    buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="fulfill_admin_menu")])
    await callback.message.edit_text(
        LucienVoice.fulfillment_admin_queue_menu(),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(
    FulfillmentAdminItemCallback.filter(), lambda cb: is_admin(cb.from_user.id)
)
async def fulfillment_admin_item_detail(
    callback: CallbackQuery, callback_data: FulfillmentAdminItemCallback
):
    """Detalle de item en cola."""
    with get_service(FulfillmentService) as svc:
        row = svc.get_fulfillment_by_id(callback_data.fulfillment_id)
    if not row:
        await callback.answer(LucienVoice.fulfillment_admin_item_not_found(), show_alert=True)
        return
    order_id = row.order_item.order_id if row.order_item else 0
    show_deliver = row.fulfillment_kind in (
        FulfillmentKind.PACKAGE_DEFERRED,
        FulfillmentKind.PACKAGE,
    ) and row.status in (
        FulfillmentStatus.PENDING_FULFILLMENT,
        FulfillmentStatus.FAILED,
    )
    text = LucienVoice.fulfillment_admin_queue_item(
        row.product.name if row.product else "?",
        order_id,
        row.user_id,
        row.status.value,
        row.user_input,
    )
    await callback.message.edit_text(
        text,
        reply_markup=build_fulfillment_item_keyboard(
            row.id,
            row.user_id,
            filter_status=callback_data.filter_status,
            show_deliver=show_deliver,
        ),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(
    FulfillmentAdminMarkCallback.filter(), lambda cb: is_admin(cb.from_user.id)
)
async def fulfillment_admin_mark_start(
    callback: CallbackQuery, callback_data: FulfillmentAdminMarkCallback, state: FSMContext
):
    """Inicia FSM notas obligatorias."""
    await state.update_data(fulfillment_id=callback_data.fulfillment_id)
    await state.set_state(FulfillmentAdminNotesStates.awaiting_notes)
    await callback.message.edit_text(
        LucienVoice.fulfillment_admin_notes_required(), parse_mode="HTML"
    )
    await callback.answer()


@router.message(FulfillmentAdminNotesStates.awaiting_notes, lambda m: is_admin(m.from_user.id))
async def fulfillment_admin_mark_submit(message: Message, state: FSMContext):
    """Marca cumplido con notas."""
    data = await state.get_data()
    fulfillment_id = data.get("fulfillment_id")
    await state.clear()
    with get_service(FulfillmentService) as svc:
        ok, msg = await svc.admin_mark_fulfilled(
            message.bot, fulfillment_id, message.from_user.id, message.text or ""
        )
    await message.answer(msg, parse_mode="HTML")
    logger.info(
        f"fulfillment_admin_handlers | mark_fulfilled | admin_id={message.from_user.id} | "
        f"fulfillment_id={fulfillment_id} | result={ok}"
    )


@router.callback_query(F.data.startswith("fulfill_deliver_start:"), lambda cb: is_admin(cb.from_user.id))
async def fulfillment_admin_deliver_start(
    callback: CallbackQuery, state: FSMContext
):
    """Lista paquetes para entrega manual desde cola."""
    parts = callback.data.split(":")
    fulfillment_id = int(parts[1])
    filter_status = parts[2] if len(parts) > 2 else "pending"
    await state.update_data(fulfillment_id=fulfillment_id, filter_status=filter_status)
    with get_service(StoreService) as store_service:
        packages = store_service.get_available_packages_for_store()
    if not packages:
        await callback.answer(LucienVoice.package_not_found(), show_alert=True)
        return
    buttons = [
        [
            InlineKeyboardButton(
                text=pkg.name,
                callback_data=FulfillmentAdminDeliverCallback(
                    fulfillment_id=fulfillment_id, package_id=pkg.id
                ).pack(),
            )
        ]
        for pkg in packages[:15]
    ]
    buttons.append(
        [
            InlineKeyboardButton(
                text="🔙 Volver",
                callback_data=FulfillmentAdminItemCallback(
                    fulfillment_id=fulfillment_id,
                    filter_status=filter_status,
                ).pack(),
            )
        ]
    )
    await callback.message.edit_text(
        LucienVoice.fulfillment_admin_deliver_select_package(),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(
    FulfillmentAdminDeliverCallback.filter(), lambda cb: is_admin(cb.from_user.id)
)
async def fulfillment_admin_deliver_package(
    callback: CallbackQuery, callback_data: FulfillmentAdminDeliverCallback
):
    """Entrega paquete seleccionado desde cola admin."""
    with get_service(FulfillmentService) as svc:
        ok, msg = await svc.admin_deliver_package_from_queue(
            callback.bot,
            callback_data.fulfillment_id,
            callback_data.package_id,
            callback.from_user.id,
        )
    await callback.answer(msg[:200], show_alert=not ok)
    if ok:
        await callback.message.edit_text(msg, parse_mode="HTML")