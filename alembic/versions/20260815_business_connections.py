"""Create business_connections table (Fase 6 link)."""
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision: str = "20260815_business_connections"
down_revision: str | Sequence[str] | None = "20260629_user_chat_id"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    op.create_table(
        "business_connections",
        sa.Column("business_connection_id", sa.Text(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("user_chat_id", sa.BigInteger(), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

def downgrade() -> None:
    op.drop_table("business_connections")
