"""add appointments and booking_configs tables

Revision ID: 0014
Revises: 0013
Create Date: 2026-05-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "appointments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("service_requested", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=20), nullable=False, server_default="manual"),
        sa.Column("booking_token", sa.String(length=100), nullable=True),
        sa.Column("job_card_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("customer_name", sa.String(length=255), nullable=True),
        sa.Column("customer_phone", sa.String(length=50), nullable=True),
        sa.Column("customer_email", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["job_card_id"], ["job_cards.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("booking_token", name="uq_appointments_booking_token"),
    )
    op.create_index(op.f("ix_appointments_shop_id"), "appointments", ["shop_id"], unique=False)
    op.create_index(op.f("ix_appointments_customer_id"), "appointments", ["customer_id"], unique=False)
    op.create_index(op.f("ix_appointments_starts_at"), "appointments", ["starts_at"], unique=False)

    op.create_table(
        "booking_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("available_services", sa.String(), nullable=True, server_default="[]"),
        sa.Column("working_hours_start", sa.String(length=5), nullable=True, server_default="08:00"),
        sa.Column("working_hours_end", sa.String(length=5), nullable=True, server_default="17:00"),
        sa.Column("slot_duration_minutes", sa.String(length=5), nullable=True, server_default="60"),
        sa.Column("working_days", sa.String(), nullable=True, server_default="[1,2,3,4,5]"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shop_id", name="uq_booking_configs_shop_id"),
        sa.UniqueConstraint("slug", name="uq_booking_configs_slug"),
    )
    op.create_index(op.f("ix_booking_configs_shop_id"), "booking_configs", ["shop_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_booking_configs_shop_id"), table_name="booking_configs")
    op.drop_table("booking_configs")
    op.drop_index(op.f("ix_appointments_starts_at"), table_name="appointments")
    op.drop_index(op.f("ix_appointments_customer_id"), table_name="appointments")
    op.drop_index(op.f("ix_appointments_shop_id"), table_name="appointments")
    op.drop_table("appointments")
