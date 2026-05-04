"""make report session_id nullable

Revision ID: 0028
Revises: 0027
Create Date: 2026-05-03
"""
from alembic import op

revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("reports", "session_id", nullable=True)


def downgrade() -> None:
    op.alter_column("reports", "session_id", nullable=False)
