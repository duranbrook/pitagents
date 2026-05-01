"""create_shop_agents

Revision ID: 0022
Revises: 0021
Create Date: 2026-05-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0022'
down_revision = '0021'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'shop_agents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('shop_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('role_tagline', sa.String(), nullable=False),
        sa.Column('accent_color', sa.String(20), nullable=False, server_default='#d97706'),
        sa.Column('initials', sa.String(3), nullable=False),
        sa.Column('system_prompt', sa.String(), nullable=False),
        sa.Column('tools', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index('ix_shop_agents_shop_id', 'shop_agents', ['shop_id'])


def downgrade():
    op.drop_index('ix_shop_agents_shop_id', table_name='shop_agents')
    op.drop_table('shop_agents')
