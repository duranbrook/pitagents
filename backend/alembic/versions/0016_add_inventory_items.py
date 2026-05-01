"""add inventory items

Revision ID: 0016
Revises: 0015
Create Date: 2026-05-01
"""
from typing import Union
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0016"
down_revision: Union[str, None] = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inventory_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("sku", sa.String(100), nullable=True),
        sa.Column("category", sa.String(50), nullable=False, server_default="Misc"),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("reorder_at", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("cost_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("sell_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("vendor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_inventory_items_shop_id", "inventory_items", ["shop_id"])


def downgrade() -> None:
    op.drop_index("ix_inventory_items_shop_id", table_name="inventory_items")
    op.drop_table("inventory_items")
