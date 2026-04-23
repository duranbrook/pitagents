"""initial_schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-04-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    postgresql.ENUM("alldata", "shop", name="pricing_source_enum").create(bind, checkfirst=True)
    postgresql.ENUM("owner", "technician", name="user_role_enum").create(bind, checkfirst=True)
    postgresql.ENUM(
        "recording", "processing", "complete", "failed", name="session_status_enum"
    ).create(bind, checkfirst=True)
    postgresql.ENUM("photo", "video", "audio", name="media_type_enum").create(bind, checkfirst=True)
    postgresql.ENUM(
        "vin", "odometer", "tire", "damage", "general", name="media_tag_enum"
    ).create(bind, checkfirst=True)

    op.create_table(
        "shops",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("address", sa.String(length=500), nullable=True),
        sa.Column(
            "labor_rate",
            sa.Numeric(precision=8, scale=2),
            server_default="120.00",
            nullable=False,
        ),
        sa.Column(
            "pricing_flag",
            postgresql.ENUM("alldata", "shop", name="pricing_source_enum", create_type=False),
            nullable=False,
        ),
        sa.Column("alldata_api_key", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM("owner", "technician", name="user_role_enum", create_type=False),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_table(
        "inspection_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("technician_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "recording", "processing", "complete", "failed",
                name="session_status_enum", create_type=False
            ),
            nullable=False,
        ),
        sa.Column("vehicle", sa.JSON(), nullable=True),
        sa.Column("transcript", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"]),
        sa.ForeignKeyConstraint(["technician_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_inspection_sessions_shop_id"), "inspection_sessions", ["shop_id"], unique=False
    )
    op.create_index(
        op.f("ix_inspection_sessions_technician_id"),
        "inspection_sessions",
        ["technician_id"],
        unique=False,
    )
    op.create_table(
        "media_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "type",
            postgresql.ENUM("photo", "video", "audio", name="media_type_enum", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "tag",
            postgresql.ENUM(
                "vin", "odometer", "tire", "damage", "general",
                name="media_tag_enum", create_type=False
            ),
            nullable=False,
        ),
        sa.Column("s3_url", sa.String(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["inspection_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_media_files_session_id"), "media_files", ["session_id"], unique=False
    )
    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("summary", sa.String(), nullable=True),
        sa.Column("findings", sa.JSON(), nullable=True),
        sa.Column("estimate_total", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("share_token", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("share_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_to", sa.JSON(), nullable=True),
        sa.Column("pdf_url", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["session_id"], ["inspection_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_reports_share_token"), "reports", ["share_token"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_reports_share_token"), table_name="reports")
    op.drop_table("reports")
    op.drop_index(op.f("ix_media_files_session_id"), table_name="media_files")
    op.drop_table("media_files")
    op.drop_index(
        op.f("ix_inspection_sessions_technician_id"), table_name="inspection_sessions"
    )
    op.drop_index(op.f("ix_inspection_sessions_shop_id"), table_name="inspection_sessions")
    op.drop_table("inspection_sessions")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
    op.drop_table("shops")
    bind = op.get_bind()
    postgresql.ENUM(name="pricing_source_enum").drop(bind, checkfirst=True)
    postgresql.ENUM(name="user_role_enum").drop(bind, checkfirst=True)
    postgresql.ENUM(name="session_status_enum").drop(bind, checkfirst=True)
    postgresql.ENUM(name="media_type_enum").drop(bind, checkfirst=True)
    postgresql.ENUM(name="media_tag_enum").drop(bind, checkfirst=True)
