"""add shop_settings table

Revision ID: 0010
Revises: 0009
Create Date: 2026-05-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "shop_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nav_pins", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("stripe_publishable_key", sa.String(length=200), nullable=True),
        sa.Column("stripe_secret_key_encrypted", sa.Text(), nullable=True),
        sa.Column("mitchell1_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("mitchell1_api_key_encrypted", sa.Text(), nullable=True),
        sa.Column("synchrony_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("synchrony_dealer_id", sa.String(length=100), nullable=True),
        sa.Column("wisetack_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("wisetack_merchant_id", sa.String(length=100), nullable=True),
        sa.Column("quickbooks_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("quickbooks_refresh_token_encrypted", sa.Text(), nullable=True),
        sa.Column("financing_threshold", sa.String(length=10), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["shop_id"],
            ["shops.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shop_id"),
    )
    op.create_index(
        op.f("ix_shop_settings_shop_id"),
        "shop_settings",
        ["shop_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_shop_settings_shop_id"), table_name="shop_settings")
    op.drop_table("shop_settings")
