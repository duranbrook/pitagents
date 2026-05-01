"""add job_card_columns table

Revision ID: 0011
Revises: 0010
Create Date: 2026-05-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "job_card_columns",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["shop_id"],
            ["shops.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint('shop_id', 'position', name='uq_job_card_columns_shop_position'),
    )
    op.create_index(
        op.f("ix_job_card_columns_shop_id"),
        "job_card_columns",
        ["shop_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_job_card_columns_shop_id"), table_name="job_card_columns")
    op.drop_table("job_card_columns")
