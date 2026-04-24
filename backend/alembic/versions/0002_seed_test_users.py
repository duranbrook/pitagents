"""seed_test_users

Revision ID: 0002_seed_test_users
Revises: 9c5e490936db
Create Date: 2026-04-24 00:00:00.000000

Seeds the default shop and two test users so that the hardcoded JWT
credentials (owner@shop.com / tech@shop.com) have matching DB rows
and chat_messages FK constraints are satisfied.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0002_seed_test_users"
down_revision: Union[str, None] = "9c5e490936db"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SHOP_ID    = "00000000-0000-0000-0000-000000000099"
OWNER_ID   = "00000000-0000-0000-0000-000000000001"
TECH_ID    = "00000000-0000-0000-0000-000000000002"
# bcrypt hash of "testpass"
HASHED_PW  = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"


def upgrade() -> None:
    conn = op.get_bind()

    conn.execute(sa.text("""
        INSERT INTO shops (id, name, labor_rate, pricing_flag)
        VALUES (:id, 'Demo Shop', 120, 'shop')
        ON CONFLICT (id) DO NOTHING
    """), {"id": SHOP_ID})

    conn.execute(sa.text("""
        INSERT INTO users (id, shop_id, email, hashed_password, role)
        VALUES (:id, :shop_id, :email, :pw, 'owner')
        ON CONFLICT (id) DO NOTHING
    """), {"id": OWNER_ID, "shop_id": SHOP_ID, "email": "owner@shop.com", "pw": HASHED_PW})

    conn.execute(sa.text("""
        INSERT INTO users (id, shop_id, email, hashed_password, role)
        VALUES (:id, :shop_id, :email, :pw, 'technician')
        ON CONFLICT (id) DO NOTHING
    """), {"id": TECH_ID, "shop_id": SHOP_ID, "email": "tech@shop.com", "pw": HASHED_PW})


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM users WHERE id IN (:o, :t)"), {"o": OWNER_ID, "t": TECH_ID})
    conn.execute(sa.text("DELETE FROM shops WHERE id = :s"), {"s": SHOP_ID})
