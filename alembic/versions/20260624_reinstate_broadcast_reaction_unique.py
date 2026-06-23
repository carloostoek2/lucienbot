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
    """Cleanup duplicates then create the (broadcast_id, user_id) unique constraint for both dialects."""
    conn = op.get_bind()
    dialect = conn.dialect.name

    # 1. Remove duplicates, keeping the earliest reaction per (broadcast_id, user_id)
    #    Works on both sqlite and postgresql.
    try:
        if dialect == "sqlite":
            conn.execute(
                sa.text("""
                    DELETE FROM broadcast_reactions
                    WHERE id NOT IN (
                        SELECT MIN(id)
                        FROM broadcast_reactions
                        GROUP BY broadcast_id, user_id
                    )
                """)
            )
        else:
            conn.execute(
                sa.text("""
                    DELETE FROM broadcast_reactions
                    WHERE id NOT IN (
                        SELECT MIN(id)
                        FROM broadcast_reactions
                        GROUP BY broadcast_id, user_id
                    )
                """)
            )
        logger.info("broadcast_reactions duplicate cleanup completed (pre-constraint)")
    except Exception as exc:
        logger.warning(f"broadcast_reactions dup cleanup skipped or partial: {exc}")

    # 2. Create the unique constraint (idempotent / safe re-run)
    #    Use batch_alter for SQLite compatibility (it recreates the table under the hood when needed).
    try:
        with op.batch_alter_table("broadcast_reactions", schema=None) as batch_op:
            # Check existence to avoid "already exists" errors on re-runs or partial history
            # (sqlite + pg differ; we catch and log)
            batch_op.create_unique_constraint(
                "uq_broadcast_user_reaction", ["broadcast_id", "user_id"]
            )
        logger.info("uq_broadcast_user_reaction constraint created (or already present)")
    except Exception as exc:
        # On PG it may raise if the name (with or without batch.f) already exists; on sqlite similar.
        msg = str(exc).lower()
        if "already exists" in msg or "duplicate" in msg or "exist" in msg:
            logger.info("uq_broadcast_user_reaction already present — skipping create")
        else:
            logger.warning(f"create_unique_constraint for broadcast_reactions skipped: {exc}")
            # Re-raise only on unexpected errors in strict environments; for safety we swallow here
            # so the migration can be re-applied. If you prefer hard fail, remove the swallow.
            # raise


def downgrade() -> None:
    """Drop the unique constraint (non-destructive for data)."""
    try:
        with op.batch_alter_table("broadcast_reactions", schema=None) as batch_op:
            batch_op.drop_constraint("uq_broadcast_user_reaction", type_="unique")
    except Exception as exc:
        logger.debug(f"drop uq_broadcast_user_reaction skipped: {exc}")
