"""add_persona_name_to_shop_agents

Revision ID: 0023
Revises: 0022
Create Date: 2026-05-02
"""
from alembic import op
import sqlalchemy as sa

revision = '0023'
down_revision = '0022'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('shop_agents', sa.Column('persona_name', sa.String(), nullable=True))


def downgrade():
    op.drop_column('shop_agents', 'persona_name')
