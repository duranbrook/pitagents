"""add google_id to users and create demo_requests table

Revision ID: 0026
Revises: 0025
Create Date: 2026-05-02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Make hashed_password nullable (Google OAuth users have no password)
    op.alter_column("users", "hashed_password", nullable=True)

    # Add google_id for Google OAuth identity linking
    op.add_column("users", sa.Column("google_id", sa.String(255), nullable=True))
    op.create_index("ix_users_google_id", "users", ["google_id"], unique=True)

    # Demo requests table
    op.create_table(
        "demo_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("first_name", sa.String(255), nullable=False),
        sa.Column("last_name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("shop_name", sa.String(255), nullable=False),
        sa.Column("locations", sa.String(50), nullable=False),
        sa.Column("message", sa.String(2000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_demo_requests_email", "demo_requests", ["email"])


def downgrade() -> None:
    op.drop_index("ix_demo_requests_email", table_name="demo_requests")
    op.drop_table("demo_requests")
    op.drop_index("ix_users_google_id", table_name="users")
    op.drop_column("users", "google_id")
    op.alter_column("users", "hashed_password", nullable=False)
