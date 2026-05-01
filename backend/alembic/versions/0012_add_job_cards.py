"""add job_cards table

Revision ID: 0012
Revises: 0011
Create Date: 2026-05-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "job_cards",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("number", sa.String(length=20), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("column_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("technician_ids", sa.JSON(), nullable=True),
        sa.Column("services", sa.JSON(), nullable=True),
        sa.Column("parts", sa.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["column_id"], ["job_card_columns.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shop_id", "number", name="uq_job_cards_shop_number"),
    )
    op.create_index(op.f("ix_job_cards_shop_id"), "job_cards", ["shop_id"], unique=False)
    op.create_index(op.f("ix_job_cards_customer_id"), "job_cards", ["customer_id"], unique=False)
    op.create_index(op.f("ix_job_cards_vehicle_id"), "job_cards", ["vehicle_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_job_cards_vehicle_id"), table_name="job_cards")
    op.drop_index(op.f("ix_job_cards_customer_id"), table_name="job_cards")
    op.drop_index(op.f("ix_job_cards_shop_id"), table_name="job_cards")
    op.drop_table("job_cards")
