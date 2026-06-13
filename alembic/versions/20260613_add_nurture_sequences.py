"""Add nurture sequences, steps and user progress tables (Nurture/User Content Lifecycle)

Revision ID: 20260613_add_nurture_sequences
Revises: 20260528_add_is_gift_to_tokens
Create Date: 2026-06-13

Implements admin-configurable timed content delivery sequences (primarily post-VIP)
with audience granularity (free/vip/all), step delay_hours + package or fallback,
persistent per-user progress, exact reuse of Package delivery and DateTrigger scheduler.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260613_add_nurture_sequences"
down_revision: str | None = "20260528_add_is_gift_to_tokens"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create nurture_sequences, nurture_steps, user_nurture_progress tables + constraints."""
    op.create_table(
        "nurture_sequences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "audience", sa.Enum("free", "vip", "all", name="nurtureaudience"), nullable=False
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_nurture_sequences_name"),
    )
    with op.batch_alter_table("nurture_sequences", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_nurture_sequences_id"), ["id"], unique=False)
        batch_op.create_index(
            batch_op.f("ix_nurture_sequences_audience"), ["audience"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_nurture_sequences_is_active"), ["is_active"], unique=False
        )

    op.create_table(
        "nurture_steps",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sequence_id", sa.Integer(), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("delay_hours", sa.Integer(), nullable=False),
        sa.Column("package_id", sa.Integer(), nullable=True),
        sa.Column("fallback_text", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(
            ["sequence_id"],
            ["nurture_sequences.id"],
        ),
        sa.ForeignKeyConstraint(
            ["package_id"],
            ["packages.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sequence_id", "step_order", name="uq_sequence_step_order"),
    )
    with op.batch_alter_table("nurture_steps", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_nurture_steps_id"), ["id"], unique=False)
        batch_op.create_index(
            batch_op.f("ix_nurture_steps_sequence_id"), ["sequence_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_nurture_steps_package_id"), ["package_id"], unique=False
        )

    op.create_table(
        "user_nurture_progress",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("sequence_id", sa.Integer(), nullable=False),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True
        ),
        sa.Column(
            "last_step_order_delivered", sa.Integer(), nullable=True, server_default=sa.text("0")
        ),
        sa.Column(
            "status", sa.String(length=20), nullable=True, server_default=sa.text("'active'")
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["sequence_id"],
            ["nurture_sequences.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_telegram_id", "sequence_id", name="uq_user_sequence"),
    )
    with op.batch_alter_table("user_nurture_progress", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_user_nurture_progress_id"), ["id"], unique=False)
        batch_op.create_index(
            batch_op.f("ix_user_nurture_progress_user_telegram_id"),
            ["user_telegram_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_user_nurture_progress_sequence_id"), ["sequence_id"], unique=False
        )


def downgrade() -> None:
    """Drop nurture tables in reverse order (respect FKs)."""
    with op.batch_alter_table("user_nurture_progress", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_user_nurture_progress_sequence_id"))
        batch_op.drop_index(batch_op.f("ix_user_nurture_progress_user_telegram_id"))
        batch_op.drop_index(batch_op.f("ix_user_nurture_progress_id"))
    op.drop_table("user_nurture_progress")

    with op.batch_alter_table("nurture_steps", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_nurture_steps_package_id"))
        batch_op.drop_index(batch_op.f("ix_nurture_steps_sequence_id"))
        batch_op.drop_index(batch_op.f("ix_nurture_steps_id"))
    op.drop_table("nurture_steps")

    with op.batch_alter_table("nurture_sequences", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_nurture_sequences_is_active"))
        batch_op.drop_index(batch_op.f("ix_nurture_sequences_audience"))
        batch_op.drop_index(batch_op.f("ix_nurture_sequences_id"))
    op.drop_table("nurture_sequences")

    # Drop the enum type (PostgreSQL); SQLite ignores.
    op.execute("DROP TYPE IF EXISTS nurtureaudience")
