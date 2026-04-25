"""Add customers and vehicles tables

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-25
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if "customers" not in existing_tables:
        op.create_table(
            "customers",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "shop_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("shops.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("email", sa.String(255), nullable=True),
            sa.Column("phone", sa.String(50), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )
        op.create_index("ix_customers_shop_id", "customers", ["shop_id"])

    if "vehicles" not in existing_tables:
        op.create_table(
            "vehicles",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "customer_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("customers.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("year", sa.SmallInteger(), nullable=False),
            sa.Column("make", sa.String(100), nullable=False),
            sa.Column("model", sa.String(100), nullable=False),
            sa.Column("trim", sa.String(100), nullable=True),
            sa.Column("vin", sa.String(17), nullable=True, unique=True),
            sa.Column("color", sa.String(50), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )
        op.create_index("ix_vehicles_customer_id", "vehicles", ["customer_id"])


def downgrade() -> None:
    op.drop_index("ix_vehicles_customer_id", table_name="vehicles")
    op.drop_table("vehicles")
    op.drop_index("ix_customers_shop_id", table_name="customers")
    op.drop_table("customers")
