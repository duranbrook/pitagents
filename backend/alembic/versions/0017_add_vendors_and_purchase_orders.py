"""add vendors and purchase orders

Revision ID: 0017
Revises: 0016
Create Date: 2026-05-01
"""
from typing import Union
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0017"
down_revision: Union[str, None] = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vendors",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(50), nullable=False, server_default="Parts"),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("website", sa.String(500), nullable=True),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("rep_name", sa.String(255), nullable=True),
        sa.Column("rep_phone", sa.String(50), nullable=True),
        sa.Column("account_number", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("source", sa.String(20), nullable=False, server_default="manual"),
        sa.Column("ytd_spend", sa.Numeric(10, 2), nullable=True),
        sa.Column("order_count", sa.Integer(), nullable=True),
        sa.Column("last_order_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vendors_shop_id", "vendors", ["shop_id"])

    op.create_table(
        "purchase_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vendor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("po_number", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("items", sa.Text(), nullable=True),
        sa.Column("total", sa.Numeric(10, 2), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("ordered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shop_id", "po_number", name="uq_purchase_orders_shop_po_number"),
    )
    op.create_index("ix_purchase_orders_shop_id", "purchase_orders", ["shop_id"])
    op.create_index("ix_purchase_orders_vendor_id", "purchase_orders", ["vendor_id"])

    # Add FK on inventory_items.vendor_id now that vendors table exists
    op.create_foreign_key(
        "fk_inventory_items_vendor_id",
        "inventory_items", "vendors",
        ["vendor_id"], ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_inventory_items_vendor_id", "inventory_items", type_="foreignkey")
    op.drop_index("ix_purchase_orders_vendor_id", table_name="purchase_orders")
    op.drop_index("ix_purchase_orders_shop_id", table_name="purchase_orders")
    op.drop_table("purchase_orders")
    op.drop_index("ix_vendors_shop_id", table_name="vendors")
    op.drop_table("vendors")
