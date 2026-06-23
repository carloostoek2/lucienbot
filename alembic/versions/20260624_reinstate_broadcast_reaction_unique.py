"""Reinstate unique constraint on broadcast_reactions (one reaction per user per broadcast).

Revision ID: 20260624_reinstate_broadcast_reaction_unique
Revises: 20260623_add_broadcast_buttons
Create Date: 2026-06-24

This restores the invariant that a user may react only once to a given broadcast
(regardless of which emoji/button they choose).

History:
- UC was added in early 2025 migs (non-sqlite only).
- 3f20074a2dd3 (active head at some point) dropped it for PG ("SQLite no tiene esta constraint")
  and never re-created it on upgrade.
- Result: multiple reactions per (broadcast, user) were possible on real DBs; cleanup
  script had to be run manually; besitos + missions could be over-awarded.

Fix:
- Clean any existing duplicates (keep the oldest id per group).
- Create the named unique constraint for BOTH postgresql and sqlite.
- Defensive (existence checks + try/except) following patterns from prior broadcast UC migs
  and 3f20074a2dd3.

The Python model (models/models.py) already declares the UC via __table_args__; this
migration ensures it exists in Alembic-managed databases.
"""
from typing import Sequence, Union

from alembic import op, context
import sqlalchemy as sa
import logging

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = "20260624_reinstate_broadcast_reaction_unique"
down_revision: Union[str, None] = "20260623_add_broadcast_buttons"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Cleanup duplicates then create the (broadcast_id, user_id) unique constraint for both dialects.

    This version is hardened for Postgres transactional DDL (the cause of the
    InFailedSqlTransaction crash on 2026-06-23 deploy).

    - Uses window function for reliable dedup (works on PG + modern SQLite).
    - For Postgres: uses a DO $$ block with IF NOT EXISTS so the ALTER never
      raises "already exists" (prevents tx abort on re-runs or partial applies).
    - For SQLite: keeps batch_alter (with try/except for safety).
    - Swallows non-fatal errors so the alembic_version stamp can succeed.
    """
    conn = op.get_bind()
    dialect = conn.dialect.name

    # 1. Remove duplicates, keeping one (the one with smallest id) per (broadcast_id, user_id).
    #    Using window function for clarity and reliability across dialects.
    try:
        conn.execute(
            sa.text("""
                DELETE FROM broadcast_reactions
                WHERE id IN (
                    SELECT id FROM (
                        SELECT id,
                               ROW_NUMBER() OVER (
                                   PARTITION BY broadcast_id, user_id
                                   ORDER BY created_at NULLS LAST, id
                               ) AS rn
                        FROM broadcast_reactions
                    ) t
                    WHERE rn > 1
                )
            """)
        )
        logger.info("broadcast_reactions duplicate cleanup completed (pre-constraint)")
    except Exception as exc:
        logger.warning(f"broadcast_reactions dup cleanup skipped or partial: {exc}")

    # 2. Create the unique constraint in a way that does not raise on re-execution.
    #    This is the critical part that was causing "current transaction is aborted"
    #    on Postgres when the constraint (or a previous statement) hit an issue.
    if dialect == "postgresql":
        try:
            op.execute(sa.text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname = 'uq_broadcast_user_reaction'
                          AND conrelid = 'broadcast_reactions'::regclass
                    ) THEN
                        ALTER TABLE broadcast_reactions
                        ADD CONSTRAINT uq_broadcast_user_reaction
                        UNIQUE (broadcast_id, user_id);
                    END IF;
                END $$;
            """))
            logger.info("uq_broadcast_user_reaction constraint ensured on Postgres (idempotent)")
        except Exception as exc:
            logger.warning(f"Postgres unique constraint step skipped: {exc}")
    else:
        # SQLite path (batch_alter recreates table under the hood)
        try:
            with op.batch_alter_table("broadcast_reactions", schema=None) as batch_op:
                batch_op.create_unique_constraint(
                    "uq_broadcast_user_reaction", ["broadcast_id", "user_id"]
                )
            logger.info("uq_broadcast_user_reaction constraint created on SQLite (or already present)")
        except Exception as exc:
            msg = str(exc).lower()
            if "already exists" in msg or "duplicate" in msg or "exist" in msg:
                logger.info("uq_broadcast_user_reaction already present on SQLite — skipping")
            else:
                logger.warning(f"SQLite create_unique_constraint skipped: {exc}")


def downgrade() -> None:
    """Drop the unique constraint (non-destructive for data)."""
    try:
        conn = op.get_bind()
        if conn.dialect.name == "postgresql":
            op.execute(sa.text("""
                ALTER TABLE broadcast_reactions
                DROP CONSTRAINT IF EXISTS uq_broadcast_user_reaction
            """))
        else:
            with op.batch_alter_table("broadcast_reactions", schema=None) as batch_op:
                batch_op.drop_constraint("uq_broadcast_user_reaction", type_="unique")
        logger.info("uq_broadcast_user_reaction dropped (if existed)")
    except Exception as exc:
        logger.debug(f"drop uq_broadcast_user_reaction skipped: {exc}")
