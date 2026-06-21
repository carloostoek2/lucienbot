"""Normalize fulfillment enum values to StrEnum .value (lowercase).

Revision ID: 20260622_fix_fulfillment_enums
Revises: 20260621_fulfillment_mig3
Create Date: 2026-06-22
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260622_fix_fulfillment_enums"
down_revision: Union[str, None] = "20260621_fulfillment_mig3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_DELIVERY_MAP = {
    "AUTO": "auto",
    "MANUAL": "manual",
}

_KIND_MAP = {
    "PACKAGE": "package",
    "PACKAGE_DEFERRED": "package_deferred",
    "USER_INPUT_THEN_MANUAL": "user_input_manual",
    "PRIVILEGE_EARLY_ACCESS": "early_access",
    "PRIVILEGE_DISCOUNT": "discount",
    "STORY_UNLOCK": "story_unlock",
    "VIP_GRANT": "vip_grant",
    "WAITLIST_ENTRY": "waitlist",
    "CHANNEL_HONOR": "channel_honor",
    "SCHEDULED_CHAT": "scheduled_chat",
}

_STATUS_MAP = {
    "PENDING_INPUT": "pending_input",
    "PENDING_FULFILLMENT": "pending",
    "AUTO_IN_PROGRESS": "auto_running",
    "FULFILLED": "fulfilled",
    "FAILED": "failed",
    "CANCELLED": "cancelled",
}


def _normalize_column(table: str, column: str, mapping: dict[str, str]) -> None:
    for old, new in mapping.items():
        op.execute(
            f"UPDATE {table} SET {column} = '{new}' WHERE {column}::text = '{old}'"
        )


def upgrade() -> None:
    _normalize_column("store_products", "delivery_mode", _DELIVERY_MAP)
    _normalize_column("store_products", "fulfillment_kind", _KIND_MAP)
    _normalize_column("order_fulfillments", "fulfillment_kind", _KIND_MAP)
    _normalize_column("order_fulfillments", "status", _STATUS_MAP)


def downgrade() -> None:
    reverse_delivery = {v: k for k, v in _DELIVERY_MAP.items()}
    reverse_kind = {v: k for k, v in _KIND_MAP.items()}
    reverse_status = {v: k for k, v in _STATUS_MAP.items()}
    _normalize_column("store_products", "delivery_mode", reverse_delivery)
    _normalize_column("store_products", "fulfillment_kind", reverse_kind)
    _normalize_column("order_fulfillments", "fulfillment_kind", reverse_kind)
    _normalize_column("order_fulfillments", "status", reverse_status)