"""add invoices and invoice_payment_events tables

Revision ID: 0013
Revises: 0012
Create Date: 2026-05-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_card_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("number", sa.String(length=20), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("line_items", postgresql.JSON(), nullable=True),
        sa.Column("subtotal", sa.Numeric(10, 2), nullable=True, server_default="0"),
        sa.Column("tax_rate", sa.Numeric(5, 4), nullable=True, server_default="0"),
        sa.Column("total", sa.Numeric(10, 2), nullable=True, server_default="0"),
        sa.Column("amount_paid", sa.Numeric(10, 2), nullable=True, server_default="0"),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("stripe_payment_link", sa.String(length=500), nullable=True),
        sa.Column("stripe_payment_intent_id", sa.String(length=200), nullable=True),
        sa.Column("pdf_url", sa.String(length=500), nullable=True),
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
        sa.ForeignKeyConstraint(["job_card_id"], ["job_cards.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shop_id", "number", name="uq_invoices_shop_number"),
    )
    op.create_index(op.f("ix_invoices_shop_id"), "invoices", ["shop_id"], unique=False)
    op.create_index(op.f("ix_invoices_job_card_id"), "invoices", ["job_card_id"], unique=False)

    op.create_table(
        "invoice_payment_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("method", sa.String(length=50), nullable=False),
        sa.Column("recorded_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_invoice_payment_events_invoice_id"),
        "invoice_payment_events",
        ["invoice_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_invoice_payment_events_invoice_id"), table_name="invoice_payment_events")
    op.drop_table("invoice_payment_events")
    op.drop_index(op.f("ix_invoices_job_card_id"), table_name="invoices")
    op.drop_index(op.f("ix_invoices_shop_id"), table_name="invoices")
    op.drop_table("invoices")
