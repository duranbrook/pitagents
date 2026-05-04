"""add composite index on chat_messages(user_id, agent_id, created_at)

Revision ID: 0027
Revises: 0026
Create Date: 2026-05-03
"""
from alembic import op

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Composite index covers the paginated history query:
    #   WHERE user_id = ? AND agent_id = ? ORDER BY created_at DESC LIMIT n
    # The (user_id, agent_id, created_at DESC) ordering lets Postgres satisfy
    # both the filter and the sort from the index alone.
    op.create_index(
        "ix_chat_messages_user_agent_created",
        "chat_messages",
        ["user_id", "agent_id", "created_at"],
    )
    # The old single-column index is now a redundant prefix of the composite.
    op.drop_index("ix_chat_messages_user_id", table_name="chat_messages")


def downgrade() -> None:
    op.create_index("ix_chat_messages_user_id", "chat_messages", ["user_id"])
    op.drop_index("ix_chat_messages_user_agent_created", table_name="chat_messages")
