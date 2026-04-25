"""Add customer_messages table; add vehicle_id/title/status to reports; add vehicle_id to chat_messages

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-25
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    # Enums — use DO blocks to create idempotently (asyncpg doesn't support
    # "CREATE TYPE IF NOT EXISTS" and checkfirst has asyncpg issues)
    op.execute(sa.text("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'customer_message_direction') THEN
                CREATE TYPE customer_message_direction AS ENUM ('out', 'in');
            END IF;
        END $$;
    """))
    op.execute(sa.text("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'customer_message_channel') THEN
                CREATE TYPE customer_message_channel AS ENUM ('wa', 'email');
            END IF;
        END $$;
    """))

    if "customer_messages" not in existing_tables:
        op.create_table(
            "customer_messages",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "vehicle_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("vehicles.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "report_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("reports.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "direction",
                postgresql.ENUM("out", "in", name="customer_message_direction", create_type=False),
                nullable=False,
            ),
            sa.Column(
                "channel",
                postgresql.ENUM("wa", "email", name="customer_message_channel", create_type=False),
                nullable=False,
            ),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("external_id", sa.String(255), nullable=True),
            sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )
        op.create_index(op.f("ix_customer_messages_vehicle_id"), "customer_messages", ["vehicle_id"])

    # Add columns to reports
    reports_cols = {c["name"] for c in inspector.get_columns("reports")}
    if "vehicle_id" not in reports_cols:
        op.add_column(
            "reports",
            sa.Column(
                "vehicle_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("vehicles.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
        op.create_index(op.f("ix_reports_vehicle_id"), "reports", ["vehicle_id"])
    if "title" not in reports_cols:
        op.add_column("reports", sa.Column("title", sa.String(255), nullable=True))
    if "status" not in reports_cols:
        op.add_column(
            "reports",
            sa.Column("status", sa.String(10), nullable=False, server_default="draft"),
        )

    # Add vehicle_id to chat_messages
    chat_cols = {c["name"] for c in inspector.get_columns("chat_messages")}
    if "vehicle_id" not in chat_cols:
        op.add_column(
            "chat_messages",
            sa.Column(
                "vehicle_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("vehicles.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    # Remove vehicle_id from chat_messages if present
    chat_cols = {c["name"] for c in inspector.get_columns("chat_messages")}
    if "vehicle_id" in chat_cols:
        op.drop_column("chat_messages", "vehicle_id")

    # Remove added columns from reports
    reports_cols = {c["name"] for c in inspector.get_columns("reports")}
    if "vehicle_id" in reports_cols:
        op.drop_index(op.f("ix_reports_vehicle_id"), table_name="reports")
        op.drop_column("reports", "vehicle_id")
    if "status" in reports_cols:
        op.drop_column("reports", "status")
    if "title" in reports_cols:
        op.drop_column("reports", "title")

    # Drop customer_messages table
    if "customer_messages" in existing_tables:
        op.drop_index(op.f("ix_customer_messages_vehicle_id"), table_name="customer_messages")
        op.drop_table("customer_messages")

    # Drop enums
    postgresql.ENUM(name="customer_message_channel").drop(bind, checkfirst=True)
    postgresql.ENUM(name="customer_message_direction").drop(bind, checkfirst=True)
