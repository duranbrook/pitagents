"""add vehicle_id to quotes

Revision ID: 0024
Revises: 9c5e490936db
Create Date: 2026-05-02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "quotes",
        sa.Column(
            "vehicle_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("vehicles.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_quotes_vehicle_id", "quotes", ["vehicle_id"])


def downgrade() -> None:
    op.drop_index("ix_quotes_vehicle_id", table_name="quotes")
    op.drop_column("quotes", "vehicle_id")
