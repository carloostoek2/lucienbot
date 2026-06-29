"""
FulfillmentService - post-commit orchestration for store catalog.

Fulfillment must NEVER run inside StoreService.complete_order atomic transaction.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from config.settings import bot_config
from models.database import SessionLocal
from models.models import (
    DeliveryMode,
    FulfillmentKind,
    FulfillmentStatus,
    Order,
    OrderFulfillment,
    OrderItem,
    OrderStatus,
    PrivilegeType,
    StorePrivilege,
    StoreProduct,
    StoreWaitlistEntry,
    WaitlistStatus,
)
from keyboards.inline_keyboards import vip_access_keyboard
from services.package_service import PackageService
from services.story_service import StoryService
from services.vip_service import VIPService
from utils.lucien_voice import LucienVoice

logger = logging.getLogger(__name__)

_MX_TZ = ZoneInfo("America/Mexico_City")
_INPUT_KINDS = {FulfillmentKind.USER_INPUT_THEN_MANUAL}
_AUTO_DISPATCH_KINDS = {
    FulfillmentKind.PACKAGE,
    FulfillmentKind.VIP_GRANT,
    FulfillmentKind.STORY_UNLOCK,
    FulfillmentKind.PRIVILEGE_EARLY_ACCESS,
    FulfillmentKind.PRIVILEGE_DISCOUNT,
    FulfillmentKind.WAITLIST_ENTRY,
}
_MANUAL_QUEUE_KINDS = {
    FulfillmentKind.PACKAGE_DEFERRED,
    FulfillmentKind.CHANNEL_HONOR,
    FulfillmentKind.SCHEDULED_CHAT,
    FulfillmentKind.USER_INPUT_THEN_MANUAL,
}
_CAP_COUNT_STATUSES = {
    FulfillmentStatus.PENDING_INPUT,
    FulfillmentStatus.PENDING_FULFILLMENT,
    FulfillmentStatus.AUTO_IN_PROGRESS,
    FulfillmentStatus.FULFILLED,
}
_MAX_PACKAGE_RETRIES = 3
_RETRY_COOLDOWN_SEC = 60


def _parse_json(text: str | None) -> dict:
    if not text:
        return {}
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return {}


def _dump_json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False)


def _initial_status_for_product(product: StoreProduct) -> FulfillmentStatus:
    if product.fulfillment_kind in _INPUT_KINDS:
        return FulfillmentStatus.PENDING_INPUT
    if product.fulfillment_kind in _AUTO_DISPATCH_KINDS:
        return FulfillmentStatus.AUTO_IN_PROGRESS
    if product.delivery_mode == DeliveryMode.MANUAL:
        return FulfillmentStatus.PENDING_FULFILLMENT
    return FulfillmentStatus.AUTO_IN_PROGRESS


def _normalize_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _mx_month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
    start = datetime(year, month, 1, tzinfo=_MX_TZ)
    if month == 12:
        end = datetime(year + 1, 1, 1, tzinfo=_MX_TZ)
    else:
        end = datetime(year, month + 1, 1, tzinfo=_MX_TZ)
    return start.astimezone(UTC), end.astimezone(UTC)


def _resolve_input_prompt_key(cfg: dict) -> str:
    return cfg.get("prompt_key") or cfg.get("input_type", "question")


def _sanitize_auto_result_for_user(auto: dict) -> dict:
    return {
        k: v
        for k, v in auto.items()
        if k not in ("token_code", "token_url", "errors", "admin_notes")
    }


def _resolve_status_display(status: FulfillmentStatus, kind: FulfillmentKind) -> str:
    mapping = {
        FulfillmentStatus.PENDING_INPUT: LucienVoice.backpack_fulfillment_status_pending_input,
        FulfillmentStatus.PENDING_FULFILLMENT: LucienVoice.backpack_fulfillment_status_pending_diana,
        FulfillmentStatus.AUTO_IN_PROGRESS: LucienVoice.backpack_fulfillment_status_processing,
        FulfillmentStatus.FULFILLED: LucienVoice.backpack_fulfillment_status_fulfilled,
        FulfillmentStatus.FAILED: LucienVoice.backpack_fulfillment_status_failed,
    }
    fn = mapping.get(status, LucienVoice.backpack_fulfillment_status_processing)
    return fn()


def _resolve_actions_available(
    status: FulfillmentStatus, kind: FulfillmentKind, auto_result: dict
) -> list[str]:
    actions: list[str] = []
    if (
        kind == FulfillmentKind.USER_INPUT_THEN_MANUAL
        and status == FulfillmentStatus.PENDING_INPUT
    ):
        actions.append("submit_input")
    if kind == FulfillmentKind.PACKAGE and status == FulfillmentStatus.FAILED:
        actions.append("retry_delivery")
    if kind == FulfillmentKind.VIP_GRANT and auto_result.get("vip_activated"):
        actions.append("resend_vip_invite")
    if kind == FulfillmentKind.STORY_UNLOCK and status == FulfillmentStatus.FULFILLED:
        actions.append("read_chapter")
    if kind == FulfillmentKind.WAITLIST_ENTRY and status == FulfillmentStatus.FULFILLED:
        if auto_result.get("position") is not None:
            actions.append("view_waitlist")
    return actions


class FulfillmentService:
    """Servicio de cumplimiento post-compra (dominio Store)."""

    def __init__(self, db: Session | None = None):
        self.db = db
        self._owns_session = db is None

    def _get_db(self) -> Session:
        if self.db is None:
            self.db = SessionLocal()
        return self.db

    def close(self):
        if self._owns_session and self.db:
            self.db.close()
            self.db = None

    def _get_product(self, product_id: int) -> StoreProduct | None:
        return self._get_db().query(StoreProduct).filter(StoreProduct.id == product_id).first()

    def _get_fulfillment_row(self, fulfillment_id: int) -> OrderFulfillment | None:
        return (
            self._get_db().query(OrderFulfillment).filter(OrderFulfillment.id == fulfillment_id).first()
        )

    def create_fulfillments_for_order(self, order_id: int) -> list[OrderFulfillment]:
        db = self._get_db()
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return []
        created: list[OrderFulfillment] = []
        for item in order.items:
            existing = (
                db.query(OrderFulfillment)
                .filter(OrderFulfillment.order_item_id == item.id)
                .first()
            )
            if existing:
                created.append(existing)
                continue
            product = self._get_product(item.product_id)
            if not product:
                continue
            row = OrderFulfillment(
                order_item_id=item.id,
                user_id=order.user_id,
                product_id=product.id,
                fulfillment_kind=product.fulfillment_kind,
                status=_initial_status_for_product(product),
            )
            db.add(row)
            created.append(row)
        db.commit()
        for row in created:
            db.refresh(row)
        logger.info(
            f"fulfillment_service | create_fulfillments_for_order | user_id={order.user_id} | "
            f"order_id={order_id} | result=ok count={len(created)}"
        )
        return created

    async def process_order_fulfillments(
        self, bot, order_id: int, *, skip_notifications: bool = False
    ) -> None:
        db = self._get_db()
        rows = (
            db.query(OrderFulfillment)
            .join(OrderItem, OrderFulfillment.order_item_id == OrderItem.id)
            .filter(OrderItem.order_id == order_id)
            .all()
        )
        incomplete_dispatch = {
            FulfillmentStatus.AUTO_IN_PROGRESS,
            FulfillmentStatus.FAILED,
        }
        for row in rows:
            try:
                if row.status == FulfillmentStatus.PENDING_INPUT:
                    if not skip_notifications:
                        await self._notify_user_pending_input(bot, row)
                        await self._notify_admin_manual_order(bot, row)
                elif row.status == FulfillmentStatus.PENDING_FULFILLMENT:
                    if not skip_notifications:
                        await self._notify_admin_manual_order(bot, row)
                elif row.status in incomplete_dispatch:
                    await self.dispatch_fulfillment(bot, row.id)
            except Exception as exc:
                logger.error(
                    f"fulfillment_service | process_order_fulfillments | "
                    f"fulfillment_id={row.id} | error={exc}"
                )

    async def dispatch_fulfillment(self, bot, fulfillment_id: int) -> tuple[bool, str]:
        row = self._get_fulfillment_row(fulfillment_id)
        if not row:
            return False, LucienVoice.store_order_not_found()
        if row.status == FulfillmentStatus.FULFILLED:
            return True, LucienVoice.backpack_fulfillment_status_fulfilled()
        product = self._get_product(row.product_id)
        if not product:
            return False, LucienVoice.store_product_not_found()
        row.last_attempt_at = datetime.now(UTC)
        handlers = {
            FulfillmentKind.PACKAGE: self._dispatch_package,
            FulfillmentKind.VIP_GRANT: self._dispatch_vip_grant,
            FulfillmentKind.STORY_UNLOCK: self._dispatch_story_unlock,
            FulfillmentKind.PRIVILEGE_EARLY_ACCESS: self._dispatch_privilege_early_access,
            FulfillmentKind.PRIVILEGE_DISCOUNT: self._dispatch_privilege_discount,
            FulfillmentKind.WAITLIST_ENTRY: self._dispatch_waitlist_entry,
        }
        if (
            product.fulfillment_kind in _MANUAL_QUEUE_KINDS
            and product.fulfillment_kind not in _AUTO_DISPATCH_KINDS
            and row.status != FulfillmentStatus.FAILED
        ):
            return True, LucienVoice.fulfillment_manual_queued(product.name)
        handler = handlers.get(product.fulfillment_kind)
        if not handler:
            return False, LucienVoice.store_product_unavailable()
        ok, msg = await handler(bot, row, product)
        logger.info(
            f"fulfillment_service | dispatch_fulfillment | user_id={row.user_id} | "
            f"fulfillment_id={fulfillment_id} | result={ok}"
        )
        return ok, msg

    async def _dispatch_package(self, bot, row: OrderFulfillment, product: StoreProduct) -> tuple[bool, str]:
        if not product.package_id:
            row.status = FulfillmentStatus.FAILED
            self._get_db().commit()
            return False, LucienVoice.package_not_found()
        pkg_svc = PackageService(self._get_db())
        qty = row.order_item.quantity if row.order_item else 1
        errors: list[str] = []
        for _ in range(qty):
            try:
                ok, msg = await pkg_svc.deliver_package_to_user(
                    bot=bot,
                    user_id=row.user_id,
                    package_id=product.package_id,
                    delivery_source="fulfillment_auto",
                )
                if not ok:
                    errors.append(msg)
            except Exception as exc:
                errors.append(str(exc))
        if errors:
            row.status = FulfillmentStatus.FAILED
            row.auto_result = _dump_json({"errors": errors})
            row.retry_count += 1
            self._get_db().commit()
            return False, LucienVoice.fulfillment_package_failed_retry_mochila()
        row.status = FulfillmentStatus.FULFILLED
        row.auto_result = _dump_json({"package_id": product.package_id, "delivered": True})
        self._get_db().commit()
        return True, LucienVoice.fulfillment_package_delivered(product.name)

    async def _send_vip_access_dm(self, bot, user_id: int, msg: str) -> bool:
        try:
            await bot.send_message(
                chat_id=user_id,
                text=msg,
                reply_markup=vip_access_keyboard(),
                parse_mode="HTML",
            )
            return True
        except Exception as exc:
            logger.error(
                f"fulfillment_service | _send_vip_access_dm | user_id={user_id} | error={exc}"
            )
            return False

    def _partial_vip_metadata(
        self, vip_svc: VIPService, product: StoreProduct, subscription
    ) -> dict:
        tariff = vip_svc.get_tariff(product.tariff_id) if product.tariff_id else None
        return {
            "vip_activated": True,
            "subscription_id": subscription.id if subscription else None,
            "invite_link": None,
            "tariff_name": tariff.name if tariff else "",
            "token_id": subscription.token_id if subscription else None,
        }

    async def _finalize_vip_resend(
        self, bot, row: OrderFulfillment, vip_svc: VIPService, auto: dict
    ) -> tuple[bool, str]:
        ok, msg, invite = await vip_svc.resend_vip_invite_for_user(bot, row.user_id)
        if not ok:
            return False, msg
        if not await self._send_vip_access_dm(bot, row.user_id, msg):
            return False, LucienVoice.fulfillment_vip_delivery_failed()
        auto["invite_link"] = invite
        row.status = FulfillmentStatus.FULFILLED
        row.auto_result = _dump_json(auto)
        self._get_db().commit()
        return True, msg

    async def _commit_vip_grant_after_send(
        self, bot, row: OrderFulfillment, msg: str, metadata: dict
    ) -> tuple[bool, str]:
        if not await self._send_vip_access_dm(bot, row.user_id, msg):
            row.status = FulfillmentStatus.AUTO_IN_PROGRESS
            row.auto_result = _dump_json(metadata)
            self._get_db().commit()
            return False, LucienVoice.fulfillment_vip_delivery_failed()
        row.status = FulfillmentStatus.FULFILLED
        row.auto_result = _dump_json(metadata)
        self._get_db().commit()
        return True, msg

    async def _dispatch_vip_grant(self, bot, row: OrderFulfillment, product: StoreProduct) -> tuple[bool, str]:
        auto = _parse_json(row.auto_result)
        vip_svc = VIPService(self._get_db())
        if auto.get("vip_activated"):
            return await self._finalize_vip_resend(bot, row, vip_svc, auto)
        if not product.tariff_id:
            row.status = FulfillmentStatus.FAILED
            self._get_db().commit()
            return False, LucienVoice.reward_vip_not_configured()
        ok, msg, metadata = await vip_svc.grant_vip_from_tariff(
            bot, row.user_id, product.tariff_id
        )
        if not ok:
            if metadata.get("vip_activated"):
                row.status = FulfillmentStatus.AUTO_IN_PROGRESS
                row.auto_result = _dump_json(metadata)
                self._get_db().commit()
                return False, msg
            row.status = FulfillmentStatus.FAILED
            row.auto_result = _dump_json({"errors": [msg]})
            self._get_db().commit()
            return False, msg
        if not metadata.get("invite_link"):
            row.status = FulfillmentStatus.AUTO_IN_PROGRESS
            row.auto_result = _dump_json(metadata)
            self._get_db().commit()
            return False, LucienVoice.reward_vip_invite_failed()
        return await self._commit_vip_grant_after_send(bot, row, msg, metadata)

    async def _dispatch_story_unlock(
        self, bot, row: OrderFulfillment, product: StoreProduct
    ) -> tuple[bool, str]:
        if not product.story_node_id:
            row.status = FulfillmentStatus.FAILED
            self._get_db().commit()
            return False, LucienVoice.story_fragment_unavailable()
        story_svc = StoryService(self._get_db())
        node = story_svc.get_node(product.story_node_id)
        ok, msg = story_svc.grant_node_access(
            row.user_id, product.story_node_id, reference_fulfillment_id=row.id
        )
        if not ok:
            row.status = FulfillmentStatus.FAILED
            self._get_db().commit()
            return False, msg or LucienVoice.story_fragment_unavailable()
        row.status = FulfillmentStatus.FULFILLED
        row.auto_result = _dump_json({"node_id": product.story_node_id})
        self._get_db().commit()
        title = node.title if node else product.name
        return True, LucienVoice.fulfillment_story_unlocked(title)

    async def _dispatch_privilege_early_access(
        self, bot, row: OrderFulfillment, product: StoreProduct
    ) -> tuple[bool, str]:
        return self._create_privileges_for_row(row, product, include_combo_discount=True)

    async def _dispatch_privilege_discount(
        self, bot, row: OrderFulfillment, product: StoreProduct
    ) -> tuple[bool, str]:
        return self._create_privileges_for_row(row, product, include_combo_discount=False)

    def _privilege_exists(
        self, db: Session, fulfillment_id: int, privilege_type: PrivilegeType
    ) -> bool:
        return (
            db.query(StorePrivilege)
            .filter(
                StorePrivilege.order_fulfillment_id == fulfillment_id,
                StorePrivilege.privilege_type == privilege_type,
            )
            .first()
            is not None
        )

    def _add_early_access_privilege(
        self, db: Session, row: OrderFulfillment, product: StoreProduct, cfg: dict, now: datetime
    ) -> bool:
        if self._privilege_exists(db, row.id, PrivilegeType.EARLY_ACCESS):
            return False
        hours = cfg.get("early_access_hours", 24)
        db.add(
            StorePrivilege(
                user_id=row.user_id,
                product_id=product.id,
                order_fulfillment_id=row.id,
                privilege_type=PrivilegeType.EARLY_ACCESS,
                config=_dump_json({"hours": hours, "drop_reference": cfg.get("drop_reference")}),
                expires_at=now + timedelta(hours=hours),
            )
        )
        return True

    def _add_discount_privilege(
        self, db: Session, row: OrderFulfillment, product: StoreProduct, cfg: dict, now: datetime
    ) -> bool:
        if self._privilege_exists(db, row.id, PrivilegeType.DISCOUNT):
            return False
        pct = cfg.get("discount_pct") or cfg.get("companion_discount_pct")
        if not pct:
            return False
        ttl_days = cfg.get("ttl_days", 30)
        db.add(
            StorePrivilege(
                user_id=row.user_id,
                product_id=product.id,
                order_fulfillment_id=row.id,
                privilege_type=PrivilegeType.DISCOUNT,
                config=_dump_json({"discount_pct": pct}),
                expires_at=now + timedelta(days=ttl_days),
            )
        )
        return True

    def _create_privileges_for_row(
        self, row: OrderFulfillment, product: StoreProduct, *, include_combo_discount: bool
    ) -> tuple[bool, str]:
        db = self._get_db()
        if row.status == FulfillmentStatus.FULFILLED:
            return True, LucienVoice.fulfillment_early_access_granted(
                _parse_json(product.fulfillment_config).get("early_access_hours", 24)
            )
        cfg = _parse_json(product.fulfillment_config)
        now = datetime.now(UTC)
        created_any = False
        hours = cfg.get("early_access_hours", 24)
        if product.fulfillment_kind == FulfillmentKind.PRIVILEGE_EARLY_ACCESS or include_combo_discount:
            created_any |= self._add_early_access_privilege(db, row, product, cfg, now)
        pct = cfg.get("discount_pct") or cfg.get("companion_discount_pct")
        if product.fulfillment_kind == FulfillmentKind.PRIVILEGE_DISCOUNT or (
            include_combo_discount and pct
        ):
            created_any |= self._add_discount_privilege(db, row, product, cfg, now)
        if not created_any and row.status != FulfillmentStatus.FULFILLED:
            row.status = FulfillmentStatus.FAILED
            db.commit()
            return False, LucienVoice.store_product_unavailable()
        row.status = FulfillmentStatus.FULFILLED
        row.auto_result = _dump_json({"privileges_created": True})
        db.commit()
        if product.fulfillment_kind == FulfillmentKind.PRIVILEGE_DISCOUNT:
            return True, LucienVoice.fulfillment_discount_granted(
                pct, (now + timedelta(days=cfg.get("ttl_days", 30))).strftime("%d/%m/%Y")
            )
        return True, LucienVoice.fulfillment_early_access_granted(hours)

    async def _dispatch_waitlist_entry(
        self, bot, row: OrderFulfillment, product: StoreProduct
    ) -> tuple[bool, str]:
        db = self._get_db()
        if row.waitlist_entry:
            return True, LucienVoice.fulfillment_waitlist_joined(row.waitlist_entry.position)
        db.query(StoreWaitlistEntry).filter(
            StoreWaitlistEntry.product_id == product.id
        ).with_for_update().all()
        max_pos = (
            db.query(func.max(StoreWaitlistEntry.position))
            .filter(StoreWaitlistEntry.product_id == product.id)
            .scalar()
        ) or 0
        entry = StoreWaitlistEntry(
            user_id=row.user_id,
            product_id=product.id,
            order_fulfillment_id=row.id,
            position=max_pos + 1,
            status=WaitlistStatus.ACTIVE,
        )
        db.add(entry)
        row.status = FulfillmentStatus.FULFILLED
        row.auto_result = _dump_json({"position": max_pos + 1})
        db.commit()
        return True, LucienVoice.fulfillment_waitlist_joined(max_pos + 1)

    def get_fulfillment_by_id(self, fulfillment_id: int) -> OrderFulfillment | None:
        return self._get_fulfillment_row(fulfillment_id)

    def get_fulfillment_for_order_item(self, order_item_id: int) -> OrderFulfillment | None:
        return (
            self._get_db()
            .query(OrderFulfillment)
            .filter(OrderFulfillment.order_item_id == order_item_id)
            .first()
        )

    def get_user_fulfillments(self, user_id: int, limit: int = 50) -> list[OrderFulfillment]:
        return (
            self._get_db()
            .query(OrderFulfillment)
            .filter(OrderFulfillment.user_id == user_id)
            .order_by(desc(OrderFulfillment.created_at))
            .limit(limit)
            .all()
        )

    def get_user_input_prompt_message(self, user_id: int, fulfillment_id: int) -> tuple[bool, str]:
        row = self._get_fulfillment_row(fulfillment_id)
        if not row or row.user_id != user_id:
            return False, LucienVoice.store_order_not_found()
        if row.status != FulfillmentStatus.PENDING_INPUT:
            return False, LucienVoice.fulfillment_input_already_submitted()
        product = self._get_product(row.product_id)
        cfg = _parse_json(product.fulfillment_config if product else None)
        prompt = LucienVoice.fulfillment_input_prompt_for_key(_resolve_input_prompt_key(cfg))
        return True, LucienVoice.fulfillment_awaiting_input(prompt)

    async def submit_user_input(
        self, bot, fulfillment_id: int, user_id: int, text: str
    ) -> tuple[bool, str]:
        row = self._get_fulfillment_row(fulfillment_id)
        if not row or row.user_id != user_id:
            return False, LucienVoice.store_order_not_found()
        if row.status != FulfillmentStatus.PENDING_INPUT:
            return False, LucienVoice.fulfillment_input_already_submitted()
        product = self._get_product(row.product_id)
        cfg = _parse_json(product.fulfillment_config if product else None)
        min_len = cfg.get("min_length", 3)
        max_len = cfg.get("max_length", 500)
        cleaned = (text or "").strip()
        if len(cleaned) < min_len or len(cleaned) > max_len:
            return False, LucienVoice.fulfillment_input_invalid_length(min_len, max_len)
        row.user_input = cleaned
        row.status = FulfillmentStatus.PENDING_FULFILLMENT
        self._get_db().commit()
        await self._notify_admin_manual_order(bot, row)
        logger.info(
            f"fulfillment_service | submit_user_input | user_id={user_id} | "
            f"fulfillment_id={fulfillment_id} | result=ok"
        )
        return True, LucienVoice.fulfillment_input_received_queued()

    async def admin_mark_fulfilled(
        self,
        bot,
        fulfillment_id: int,
        admin_id: int,
        notes: str,
        *,
        package_id: int | None = None,
    ) -> tuple[bool, str]:
        row = self._get_fulfillment_row(fulfillment_id)
        if not row:
            return False, LucienVoice.store_order_not_found()
        if not (notes or "").strip():
            return False, LucienVoice.fulfillment_admin_notes_required()
        allowed = {FulfillmentStatus.PENDING_FULFILLMENT, FulfillmentStatus.FAILED}
        if row.status == FulfillmentStatus.PENDING_INPUT and not row.user_input:
            return False, LucienVoice.fulfillment_admin_input_required()
        if row.status not in allowed and row.status != FulfillmentStatus.PENDING_INPUT:
            return False, LucienVoice.fulfillment_admin_invalid_status()
        row.admin_notes = notes.strip()
        row.fulfilled_by = admin_id
        row.fulfilled_at = datetime.now(UTC)
        row.status = FulfillmentStatus.FULFILLED
        self._get_db().commit()
        if package_id:
            await self.admin_deliver_package_from_queue(bot, fulfillment_id, package_id, admin_id)
        logger.info(
            f"fulfillment_service | admin_mark_fulfilled | user_id={row.user_id} | "
            f"fulfillment_id={fulfillment_id} | result=ok"
        )
        return True, LucienVoice.backpack_fulfillment_fulfilled(row.product.name if row.product else "")

    async def admin_deliver_package_from_queue(
        self, bot, fulfillment_id: int, package_id: int, admin_id: int
    ) -> tuple[bool, str]:
        row = self._get_fulfillment_row(fulfillment_id)
        if not row:
            return False, LucienVoice.store_order_not_found()
        if row.fulfillment_kind not in (
            FulfillmentKind.PACKAGE,
            FulfillmentKind.PACKAGE_DEFERRED,
        ):
            return False, LucienVoice.fulfillment_admin_deliver_invalid_kind()
        product = self._get_product(row.product_id)
        if product and product.package_id and package_id != product.package_id:
            return False, LucienVoice.fulfillment_admin_package_mismatch()
        auto = _parse_json(row.auto_result)
        if row.status == FulfillmentStatus.FULFILLED and auto.get("package_id"):
            return True, LucienVoice.backpack_fulfillment_status_fulfilled()
        allowed = {FulfillmentStatus.PENDING_FULFILLMENT, FulfillmentStatus.FAILED}
        if row.status not in allowed:
            return False, LucienVoice.fulfillment_admin_invalid_status()
        pkg_svc = PackageService(self._get_db())
        ok, msg = await pkg_svc.deliver_package_to_user(
            bot=bot,
            user_id=row.user_id,
            package_id=package_id,
            delivery_source="fulfillment_admin",
        )
        if ok:
            row.status = FulfillmentStatus.FULFILLED
            row.fulfilled_by = admin_id
            row.fulfilled_at = datetime.now(UTC)
            row.auto_result = _dump_json({"package_id": package_id, "admin_deliver": True})
            self._get_db().commit()
        return ok, msg

    def get_pending_queue(
        self, *, status: FulfillmentStatus | None = None, limit: int = 50
    ) -> list[OrderFulfillment]:
        q = self._get_db().query(OrderFulfillment)
        if status:
            q = q.filter(OrderFulfillment.status == status)
        else:
            q = q.filter(
                OrderFulfillment.status.in_(
                    [
                        FulfillmentStatus.PENDING_INPUT,
                        FulfillmentStatus.PENDING_FULFILLMENT,
                        FulfillmentStatus.FAILED,
                    ]
                )
            )
        return q.order_by(desc(OrderFulfillment.created_at)).limit(limit).all()

    def count_monthly_sales(self, product_id: int, year: int, month: int) -> int:
        db = self._get_db()
        start_utc, end_utc = _mx_month_bounds(year, month)
        rows = (
            db.query(OrderFulfillment)
            .filter(
                OrderFulfillment.product_id == product_id,
                OrderFulfillment.status.in_(list(_CAP_COUNT_STATUSES)),
            )
            .all()
        )
        count = 0
        for row in rows:
            created = _normalize_utc(row.created_at)
            if created and start_utc <= created < end_utc:
                count += 1
        return count

    def count_monthly_completed_order_items(
        self, product_id: int, *, db: Session | None = None
    ) -> int:
        """Count sold units on COMPLETED orders in current MX month (atomic cap reserve)."""
        session = db or self._get_db()
        now = datetime.now(_MX_TZ)
        start_utc, end_utc = _mx_month_bounds(now.year, now.month)
        items = (
            session.query(OrderItem)
            .join(Order, OrderItem.order_id == Order.id)
            .filter(
                OrderItem.product_id == product_id,
                Order.status == OrderStatus.COMPLETED,
                Order.completed_at.isnot(None),
                Order.completed_at >= start_utc,
                Order.completed_at < end_utc,
            )
            .all()
        )
        return sum(item.quantity for item in items)

    def is_monthly_cap_available(self, product_id: int) -> bool:
        product = self._get_product(product_id)
        if not product or not product.monthly_stock_cap:
            return True
        count = self.count_monthly_completed_order_items(product_id)
        return count < product.monthly_stock_cap

    def get_active_discount_pct(self, user_id: int) -> int:
        now = datetime.now(UTC)
        row = (
            self._get_db()
            .query(StorePrivilege)
            .filter(
                StorePrivilege.user_id == user_id,
                StorePrivilege.privilege_type == PrivilegeType.DISCOUNT,
                StorePrivilege.consumed_at.is_(None),
                (StorePrivilege.expires_at.is_(None)) | (StorePrivilege.expires_at > now),
            )
            .order_by(desc(StorePrivilege.created_at))
            .first()
        )
        if not row:
            return 0
        return _parse_json(row.config).get("discount_pct", 0)

    def consume_active_discount(self, user_id: int, *, db: Session | None = None) -> bool:
        """Consume active discount with FOR UPDATE inside atomic transaction."""
        session = db or self._get_db()
        now = datetime.now(UTC)
        row = (
            session.query(StorePrivilege)
            .filter(
                StorePrivilege.user_id == user_id,
                StorePrivilege.privilege_type == PrivilegeType.DISCOUNT,
                StorePrivilege.consumed_at.is_(None),
                (StorePrivilege.expires_at.is_(None)) | (StorePrivilege.expires_at > now),
            )
            .order_by(desc(StorePrivilege.created_at))
            .with_for_update()
            .first()
        )
        if row:
            row.consumed_at = now
            if db is None:
                session.commit()
            return True
        return False

    def build_purchase_enrichment(self, order_item_id: int) -> dict:
        row = self.get_fulfillment_for_order_item(order_item_id)
        if not row:
            return {}
        raw_auto = _parse_json(row.auto_result)
        auto = _sanitize_auto_result_for_user(raw_auto)
        package_id = row.product.package_id if row.product else None
        if not package_id:
            package_id = raw_auto.get("package_id")
        return {
            "fulfillment_id": row.id,
            "fulfillment_status": row.status.value,
            "fulfillment_kind": row.fulfillment_kind.value,
            "status_display": _resolve_status_display(row.status, row.fulfillment_kind),
            "actions_available": _resolve_actions_available(
                row.status, row.fulfillment_kind, raw_auto
            ),
            "auto_result": auto,
            "package_id": package_id,
        }

    async def resend_vip_invite_for_fulfillment(
        self, bot, user_id: int, fulfillment_id: int
    ) -> tuple[bool, str]:
        row = self._get_fulfillment_row(fulfillment_id)
        if not row or row.user_id != user_id:
            return False, LucienVoice.store_order_not_found()
        if row.fulfillment_kind != FulfillmentKind.VIP_GRANT:
            return False, LucienVoice.store_product_unavailable()
        auto = _parse_json(row.auto_result)
        if not auto.get("vip_activated"):
            return False, LucienVoice.reward_vip_not_configured()
        vip_svc = VIPService(self._get_db())
        ok, msg, invite_link = await vip_svc.resend_vip_invite_for_user(bot, user_id)
        if not ok:
            return False, msg
        auto["invite_link"] = invite_link
        row.status = FulfillmentStatus.FULFILLED
        row.auto_result = _dump_json(auto)
        self._get_db().commit()
        return True, msg

    async def retry_fulfillment_delivery(self, bot, user_id: int, fulfillment_id: int) -> tuple[bool, str]:
        row = self._get_fulfillment_row(fulfillment_id)
        if not row or row.user_id != user_id:
            return False, LucienVoice.store_order_not_found()
        if row.fulfillment_kind != FulfillmentKind.PACKAGE:
            return False, LucienVoice.store_product_unavailable()
        if row.status != FulfillmentStatus.FAILED:
            return False, LucienVoice.fulfillment_retry_not_allowed()
        if row.retry_count >= _MAX_PACKAGE_RETRIES:
            return False, LucienVoice.fulfillment_retry_limit_reached()
        now = datetime.now(UTC)
        if row.last_attempt_at:
            last = _normalize_utc(row.last_attempt_at)
            if last and (now - last).total_seconds() < _RETRY_COOLDOWN_SEC:
                return False, LucienVoice.fulfillment_retry_cooldown()
        row.status = FulfillmentStatus.AUTO_IN_PROGRESS
        self._get_db().commit()
        ok, msg = await self.dispatch_fulfillment(bot, fulfillment_id)
        return ok, msg

    async def notify_early_access_holders(self, drop_id: str) -> None:
        logger.info(
            f"fulfillment_service | notify_early_access_holders | drop_id={drop_id} | "
            f"result=stub_deferred_v1_1"
        )

    async def _notify_user_pending_input(self, bot, row: OrderFulfillment) -> None:
        product = self._get_product(row.product_id)
        cfg = _parse_json(product.fulfillment_config if product else None)
        prompt = LucienVoice.fulfillment_input_prompt_for_key(_resolve_input_prompt_key(cfg))
        try:
            await bot.send_message(
                chat_id=row.user_id,
                text=LucienVoice.fulfillment_awaiting_input(prompt),
                parse_mode="HTML",
            )
        except Exception as exc:
            logger.error(
                f"fulfillment_service | notify_user_pending_input | user_id={row.user_id} | "
                f"error={exc}"
            )

    async def _notify_admin_manual_order(self, bot, row: OrderFulfillment) -> None:
        if not bot_config.ADMIN_IDS:
            return
        product = self._get_product(row.product_id)
        order_id = row.order_item.order_id if row.order_item else 0
        text = LucienVoice.fulfillment_admin_new_manual_order(
            product.name if product else "?",
            order_id,
            row.user_id,
            row.fulfillment_kind.value,
            row.status.value,
            row.user_input,
        )
        for admin_id in bot_config.ADMIN_IDS:
            try:
                await bot.send_message(chat_id=admin_id, text=text, parse_mode="HTML")
            except Exception as exc:
                logger.error(
                    f"fulfillment_service | notify_admin_manual_order | admin_id={admin_id} | "
                    f"error={exc}"
                )


async def reset_monthly_store_caps_job() -> None:
    """Job scheduler: habilita nuevas compras mensuales (no borra historial)."""
    now = datetime.now(_MX_TZ)
    logger.info(
        f"scheduler | monthly_store_cap_reset | month={now.year}-{now.month:02d} | result=ok"
    )