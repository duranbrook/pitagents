"""add_quotes

Revision ID: 0003_add_quotes
Revises: 0002_seed_test_users
Create Date: 2026-04-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0003_add_quotes"
down_revision: Union[str, None] = "0002_seed_test_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    # Create the quote_status enum type
    quote_status_enum = postgresql.ENUM("draft", "final", "sent", name="quote_status", create_type=False)
    quote_status_enum.create(bind, checkfirst=True)

    # Create the quotes table
    op.create_table(
        "quotes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM("draft", "final", "sent", name="quote_status", create_type=False),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("line_items", sa.JSON(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column(
            "total",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["inspection_sessions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_quotes_session_id"), "quotes", ["session_id"], unique=False)

    # Add quote_id column to reports table
    op.add_column(
        "reports",
        sa.Column("quote_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_reports_quote_id",
        "reports",
        "quotes",
        ["quote_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    # Remove the foreign key and quote_id column from reports
    op.drop_constraint("fk_reports_quote_id", "reports", type_="foreignkey")
    op.drop_column("reports", "quote_id")

    # Drop the quotes table
    op.drop_index(op.f("ix_quotes_session_id"), table_name="quotes")
    op.drop_table("quotes")

    # Drop the quote_status enum type
    bind = op.get_bind()
    postgresql.ENUM(name="quote_status").drop(bind, checkfirst=True)
