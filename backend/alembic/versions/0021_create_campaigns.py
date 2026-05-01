"""create_campaigns

Revision ID: 0021
Revises: 0020
Create Date: 2026-05-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0021'
down_revision = '0020'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'campaigns',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('shop_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='draft'),
        sa.Column('message_body', sa.String(), nullable=False),
        sa.Column('channel', sa.String(), nullable=False, server_default='sms'),
        sa.Column('audience_segment', sa.JSON(), nullable=False),
        sa.Column('send_at', sa.DateTime(), nullable=True),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('stats', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_campaigns_shop_id', 'campaigns', ['shop_id'])


def downgrade():
    op.drop_index('ix_campaigns_shop_id', table_name='campaigns')
    op.drop_table('campaigns')
