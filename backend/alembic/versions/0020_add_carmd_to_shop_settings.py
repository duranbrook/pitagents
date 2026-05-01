"""add_carmd_to_shop_settings

Revision ID: 0020
Revises: 0019
Create Date: 2026-05-01
"""
from alembic import op
import sqlalchemy as sa

revision = '0020'
down_revision = '0019'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('shop_settings', sa.Column('carmd_api_key', sa.String(), nullable=True))
    op.add_column('shop_settings', sa.Column('carmd_partner_token', sa.String(), nullable=True))


def downgrade():
    op.drop_column('shop_settings', 'carmd_partner_token')
    op.drop_column('shop_settings', 'carmd_api_key')
