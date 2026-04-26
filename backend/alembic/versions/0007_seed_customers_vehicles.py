"""seed_customers_vehicles

Revision ID: 0007
Revises: 0006
Create Date: 2026-04-26 00:00:00.000000

Seeds realistic test customers and vehicles for the Demo Shop.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SHOP_ID = "00000000-0000-0000-0000-000000000099"

CUSTOMERS = [
    ("c1000000-0000-0000-0000-000000000001", "James Carter",    "james.carter@email.com",  "(555) 234-5678"),
    ("c1000000-0000-0000-0000-000000000002", "Maria Gonzalez",  "maria.g@gmail.com",       "(555) 876-5432"),
    ("c1000000-0000-0000-0000-000000000003", "David Chen",      "d.chen@work.com",         "(555) 444-1234"),
    ("c1000000-0000-0000-0000-000000000004", "Sarah Johnson",   "sarah.j@email.com",       "(555) 999-8888"),
]

VEHICLES = [
    # customer_id                              year  make       model        trim              vin                   color
    ("c1000000-0000-0000-0000-000000000001", 2019, "Toyota",  "Camry",     "SE",             "4T1B11HK1KU123456",  "Silver"),
    ("c1000000-0000-0000-0000-000000000001", 2021, "Honda",   "CR-V",      "EX",             "2HKRW2H54MH123456",  "Blue"),
    ("c1000000-0000-0000-0000-000000000002", 2017, "Ford",    "F-150",     "XLT",            "1FTEW1EP1HKE12345",  "Black"),
    ("c1000000-0000-0000-0000-000000000003", 2022, "Tesla",   "Model 3",   "Long Range",     "5YJ3E1EA2NF123456",  "White"),
    ("c1000000-0000-0000-0000-000000000003", 2018, "BMW",     "3 Series",  "330i",           "WBA8B9G56JNU12345",  "Gray"),
    ("c1000000-0000-0000-0000-000000000004", 2020, "Chevrolet","Equinox",  "LT",             "2GNAXKEV9L6123456",  "Red"),
]


def upgrade() -> None:
    conn = op.get_bind()

    for cid, name, email, phone in CUSTOMERS:
        conn.execute(sa.text("""
            INSERT INTO customers (id, shop_id, name, email, phone)
            VALUES (:id, :shop_id, :name, :email, :phone)
            ON CONFLICT (id) DO NOTHING
        """), {"id": cid, "shop_id": SHOP_ID, "name": name, "email": email, "phone": phone})

    for cid, year, make, model, trim, vin, color in VEHICLES:
        conn.execute(sa.text("""
            INSERT INTO vehicles (customer_id, year, make, model, trim, vin, color)
            VALUES (:cid, :year, :make, :model, :trim, :vin, :color)
            ON CONFLICT (vin) DO NOTHING
        """), {"cid": cid, "year": year, "make": make, "model": model,
               "trim": trim, "vin": vin, "color": color})


def downgrade() -> None:
    conn = op.get_bind()
    ids = [c[0] for c in CUSTOMERS]
    for cid in ids:
        conn.execute(sa.text("DELETE FROM customers WHERE id = :id"), {"id": cid})
