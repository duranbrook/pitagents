"""add_report_columns

Revision ID: 0008
Revises: 0007
Create Date: 2026-04-26 00:00:00.000000

Adds vehicle_id, title, status, estimate (JSON), and vehicle (JSON snapshot) to reports.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {c["name"] for c in inspector.get_columns("reports")}

    if "vehicle_id" not in columns:
        op.add_column("reports", sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), nullable=True))
        op.create_foreign_key(
            "fk_reports_vehicle_id",
            "reports", "vehicles",
            ["vehicle_id"], ["id"],
            ondelete="SET NULL",
        )
        op.create_index("ix_reports_vehicle_id", "reports", ["vehicle_id"])

    if "title" not in columns:
        op.add_column("reports", sa.Column("title", sa.String(255), nullable=True))

    if "status" not in columns:
        op.add_column(
            "reports",
            sa.Column("status", sa.String(10), nullable=False, server_default="draft"),
        )

    if "estimate" not in columns:
        op.add_column("reports", sa.Column("estimate", sa.JSON(), nullable=True))

    if "vehicle" not in columns:
        op.add_column("reports", sa.Column("vehicle", sa.JSON(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {c["name"] for c in inspector.get_columns("reports")}

    if "vehicle" in columns:
        op.drop_column("reports", "vehicle")
    if "estimate" in columns:
        op.drop_column("reports", "estimate")
    if "status" in columns:
        op.drop_column("reports", "status")
    if "title" in columns:
        op.drop_column("reports", "title")
    if "vehicle_id" in columns:
        op.drop_index("ix_reports_vehicle_id", table_name="reports")
        op.drop_constraint("fk_reports_vehicle_id", "reports", type_="foreignkey")
        op.drop_column("reports", "vehicle_id")
