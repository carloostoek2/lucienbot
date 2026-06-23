"""Add broadcast_buttons catalog table + extra_button_id nullable FK to broadcast_messages.

Revision ID: 20260623_add_broadcast_buttons
Revises: 20260622_fix_fulfillment_enums
Create Date: 2026-06-23

ITEM 1 (broadcast-link-buttons-item1): foundation catalog only.
- New table broadcast_buttons (id, label, url, description, is_active, created_at)
- Add nullable extra_button_id FK to broadcast_messages (no relationship in model for ITEM 1)
- URL validation is LOOSE (business requirement "enlace de Telegram", not hard enforcement in ITEM 1)
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260623_add_broadcast_buttons"
down_revision: str | None = "20260622_fix_fulfillment_enums"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create broadcast_buttons table and add nullable FK column to broadcast_messages."""
    # Create the catalog table for reusable link buttons (pattern mirrors reaction_emojis)
    op.create_table(
        "broadcast_buttons",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("broadcast_buttons", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_broadcast_buttons_id"), ["id"], unique=False)

    # Add nullable FK column (existing rows unaffected; ITEM 2 will populate)
    op.add_column(
        "broadcast_messages",
        sa.Column("extra_button_id", sa.Integer(), nullable=True),
    )

    # Create FK via batch_alter for SQLite compatibility (recreates table under the hood)
    with op.batch_alter_table("broadcast_messages", schema=None) as batch_op:
        batch_op.create_foreign_key(
            "fk_broadcast_messages_extra_button",
            "broadcast_buttons",
            ["extra_button_id"],
            ["id"],
        )


def downgrade() -> None:
    """Reverse: drop FK, drop column, drop table."""
    # Drop FK first (inside batch for SQLite)
    with op.batch_alter_table("broadcast_messages", schema=None) as batch_op:
        batch_op.drop_constraint("fk_broadcast_messages_extra_button", type_="foreignkey")

    # Drop the column
    op.drop_column("broadcast_messages", "extra_button_id")

    # Drop the catalog table (explicit index drop to match baseline precedent e.g. reaction_emojis)
    with op.batch_alter_table("broadcast_buttons", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_broadcast_buttons_id"))
    op.drop_table("broadcast_buttons")
