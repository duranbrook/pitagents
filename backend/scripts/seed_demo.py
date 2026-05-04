"""
Demo seed script — City Auto Care shop.

Usage:
    DATABASE_URL=postgresql://user:pass@host/db .venv/bin/python scripts/seed_demo.py

Nukes ALL existing data and reseeds deterministic demo data. Safe to run
multiple times. Produces the same data every run.

Demo narrative:
  Shop:    City Auto Care
  Owner:   Joe Hernandez  (owner@shop.com / testpass)
  Tech:    Dan Rivera     (tech@shop.com / testpass)
  7 customers in various lifecycle stages.
"""

import asyncio
import json
import os
import re
import sys
import uuid
from datetime import date, datetime, timedelta, timezone

import asyncpg


# ---------------------------------------------------------------------------
# Fixed IDs — never change these (FK constraints + in-memory auth)
# ---------------------------------------------------------------------------

SHOP_ID     = "00000000-0000-0000-0000-000000000099"
OWNER_ID    = "00000000-0000-0000-0000-000000000001"
TECH_ID     = "00000000-0000-0000-0000-000000000002"

# Customers
C1 = "cccccccc-0000-0000-0000-000000000001"  # James Parker
C2 = "cccccccc-0000-0000-0000-000000000002"  # Sarah Chen
C3 = "cccccccc-0000-0000-0000-000000000003"  # Marcus Johnson
C4 = "cccccccc-0000-0000-0000-000000000004"  # Emily Rodriguez
C5 = "cccccccc-0000-0000-0000-000000000005"  # David Kim
C6 = "cccccccc-0000-0000-0000-000000000006"  # Linda Thompson
C7 = "cccccccc-0000-0000-0000-000000000007"  # Robert Martinez

# Vehicles
V1 = "b7b7b7b7-0000-0000-0000-000000000001"  # 2019 Toyota Camry      (James)
V2 = "b7b7b7b7-0000-0000-0000-000000000002"  # 2021 BMW 330i          (Sarah)
V3 = "b7b7b7b7-0000-0000-0000-000000000003"  # 2020 Ford F-150        (Marcus)
V4 = "b7b7b7b7-0000-0000-0000-000000000004"  # 2018 Honda Civic       (Emily)
V5 = "b7b7b7b7-0000-0000-0000-000000000005"  # 2022 Audi A4           (David)
V6 = "b7b7b7b7-0000-0000-0000-000000000006"  # 2019 Subaru Outback    (Linda)
V7 = "b7b7b7b7-0000-0000-0000-000000000007"  # 2017 Chevrolet Silverado (Robert)

# Job card columns
JCC1 = "b8b8b8b8-0000-0000-0000-000000000001"  # Scheduled
JCC2 = "b8b8b8b8-0000-0000-0000-000000000002"  # In Progress
JCC3 = "b8b8b8b8-0000-0000-0000-000000000003"  # Awaiting Parts
JCC4 = "b8b8b8b8-0000-0000-0000-000000000004"  # Done

# Job cards
JC1 = "b9b9b9b9-1111-0000-0000-000000000001"  # James  — brake service (Done)
JC2 = "b9b9b9b9-1111-0000-0000-000000000002"  # Sarah  — transmission flush (In Progress)
JC3 = "b9b9b9b9-1111-0000-0000-000000000003"  # Marcus — TPS replacement (Awaiting Parts)
JC4 = "b9b9b9b9-1111-0000-0000-000000000004"  # Emily  — oil change + tire rotation (Done)
JC5 = "b9b9b9b9-1111-0000-0000-000000000005"  # David  — A/C service (Scheduled)

# Invoices
INV1 = "c4c4c4c4-0000-0000-0000-000000000001"  # James  — paid $487.50
INV2 = "c4c4c4c4-0000-0000-0000-000000000002"  # Sarah  — pending $1,240.00
INV3 = "c4c4c4c4-0000-0000-0000-000000000003"  # Emily  — paid $198.50

# Payment events
PE1 = "c6c6c6c6-0000-0000-0000-000000000001"  # INV1 cash $487.50
PE2 = "c6c6c6c6-0000-0000-0000-000000000002"  # INV3 card $198.50

# Inspection sessions
IS1 = "c7c7c7c7-0000-0000-0000-000000000001"  # James (complete)
IS2 = "c7c7c7c7-0000-0000-0000-000000000002"  # Emily (complete)
IS3 = "c7c7c7c7-0000-0000-0000-000000000003"  # Sarah (processing)

# Reports
R1 = "c8c8c8c8-0000-0000-0000-000000000001"  # James report (final)
R2 = "c8c8c8c8-0000-0000-0000-000000000002"  # Emily report (final)

# Report share tokens
RS1 = "aa000001-0000-0000-0000-000000000001"
RS2 = "aa000002-0000-0000-0000-000000000002"

# Quotes
Q1 = "c9c9c9c9-0000-0000-0000-000000000001"  # linked to IS1 (final)
Q2 = "c9c9c9c9-0000-0000-0000-000000000002"  # linked to IS3 (draft)

# Vendors
VEN1 = "eeeeeeee-0000-0000-0000-000000000001"  # NAPA Auto Parts
VEN2 = "eeeeeeee-0000-0000-0000-000000000002"  # AutoZone
VEN3 = "eeeeeeee-0000-0000-0000-000000000003"  # Advance Auto Parts

# Inventory items
II1 = "c5c5c5c5-1111-0000-0000-000000000001"  # 5W-30 Synthetic Oil
II2 = "c5c5c5c5-1111-0000-0000-000000000002"  # Oil Filter
II3 = "c5c5c5c5-1111-0000-0000-000000000003"  # Brake Pads (Front, Premium)
II4 = "c5c5c5c5-1111-0000-0000-000000000004"  # Brake Rotors (Front pair)
II5 = "c5c5c5c5-1111-0000-0000-000000000005"  # Throttle Position Sensor — F-150
II6 = "c5c5c5c5-1111-0000-0000-000000000006"  # Air Filter
II7 = "c5c5c5c5-1111-0000-0000-000000000007"  # Cabin Air Filter
II8 = "c5c5c5c5-1111-0000-0000-000000000008"  # ATF Transmission Fluid (gallon)

# Purchase orders
PO1 = "d4d4d4d4-0000-0000-0000-000000000001"  # TPS ordered from NAPA (pending)
PO2 = "d4d4d4d4-0000-0000-0000-000000000002"  # Brake parts received from AutoZone

# Appointments
A1 = "aaaaaaaa-0000-0000-0000-000000000001"  # David Kim  May 5 (confirmed)
A2 = "aaaaaaaa-0000-0000-0000-000000000002"  # Linda Thompson May 7 (booking link)
A3 = "aaaaaaaa-0000-0000-0000-000000000003"  # Robert Martinez May 12 (follow-up)

# Booking config
BC1 = "bbbbbbbb-0000-0000-0000-000000000001"

# Service reminder configs
SRC1 = "dddddddd-0000-0000-0000-000000000001"  # Oil Change
SRC2 = "dddddddd-0000-0000-0000-000000000002"  # Tire Rotation
SRC3 = "dddddddd-0000-0000-0000-000000000003"  # Full Service
SRC4 = "dddddddd-0000-0000-0000-000000000004"  # AC Check

# Service reminders
SR1 = "ffffffff-0000-0000-0000-000000000001"  # Robert — Oil Change (overdue, sent)
SR2 = "ffffffff-0000-0000-0000-000000000002"  # James  — Tire Rotation (upcoming)
SR3 = "ffffffff-0000-0000-0000-000000000003"  # Emily  — Oil Change (booked)
SR4 = "ffffffff-0000-0000-0000-000000000004"  # Sarah  — Full Service (active)

# Time entries
TE1 = "d5d5d5d5-0000-0000-0000-000000000001"  # Tech on JC1 — 2.5 hrs brake service
TE2 = "d5d5d5d5-0000-0000-0000-000000000002"  # Tech on JC4 — 1.0 hr oil/rotation
TE3 = "d5d5d5d5-0000-0000-0000-000000000003"  # Tech on JC2 — in progress (no end_at)
TE4 = "d5d5d5d5-0000-0000-0000-000000000004"  # Tech on JC3 — 0.5 hr diagnostics

# Expenses
EX1 = "d6d6d6d6-0000-0000-0000-000000000001"  # Shop supplies
EX2 = "d6d6d6d6-0000-0000-0000-000000000002"  # Brake parts purchase
EX3 = "d6d6d6d6-0000-0000-0000-000000000003"  # Utility bill
EX4 = "d6d6d6d6-0000-0000-0000-000000000004"  # Equipment service

# Campaigns (shop_id is stored as String, not UUID FK)
CAM1 = "cccccccc-1111-0000-0000-000000000001"  # Spring A/C Check (sent)
CAM2 = "cccccccc-1111-0000-0000-000000000002"  # Mother's Day Oil Change (draft)

# Shop agents
SA1 = "aaaaaaaa-aaaa-0000-0000-000000000001"  # Service Advisor
SA2 = "aaaaaaaa-aaaa-0000-0000-000000000002"  # Technician
SA3 = "aaaaaaaa-aaaa-0000-0000-000000000003"  # Parts Manager
SA4 = "aaaaaaaa-aaaa-0000-0000-000000000004"  # Bookkeeper
SA5 = "aaaaaaaa-aaaa-0000-0000-000000000005"  # Manager

# Chat messages
CM1 = "cccccccc-2222-0000-0000-000000000001"  # Owner → Service Advisor
CM2 = "cccccccc-2222-0000-0000-000000000002"  # Service Advisor → Owner (reply)
CM3 = "cccccccc-2222-0000-0000-000000000003"  # Owner → Technician
CM4 = "cccccccc-2222-0000-0000-000000000004"  # Technician → Owner (reply)

# Customer messages (report sends)
CMSG1 = "cccccccc-3333-0000-0000-000000000001"  # Outbound report to James
CMSG2 = "cccccccc-3333-0000-0000-000000000002"  # Outbound report to Emily
CMSG3 = "cccccccc-3333-0000-0000-000000000003"  # Inbound reply from Emily

# Media files
MF1 = "d7d7d7d7-0000-0000-0000-000000000001"  # VIN photo IS1
MF2 = "d7d7d7d7-0000-0000-0000-000000000002"  # Odometer photo IS1
MF3 = "d7d7d7d7-0000-0000-0000-000000000003"  # Damage photo IS1 (worn brake pads)
MF4 = "d7d7d7d7-0000-0000-0000-000000000004"  # VIN photo IS2

# Shop settings
SS1 = "d8d8d8d8-0000-0000-0000-000000000001"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def ts(days_ago: int = 0, hour: int = 9, minute: int = 0) -> datetime:
    """Return a UTC datetime relative to 2026-05-01."""
    base = datetime(2026, 5, 1, hour, minute, 0, tzinfo=timezone.utc)
    return base - timedelta(days=days_ago)


def dt(days_offset: int = 0, hour: int = 9, minute: int = 0) -> datetime:
    base = datetime(2026, 5, 1, hour, minute, 0, tzinfo=timezone.utc)
    return base + timedelta(days=days_offset)


def j(obj) -> str:
    return json.dumps(obj)


# ---------------------------------------------------------------------------
# Nuke order — safe deletion sequence respecting FK constraints
# ---------------------------------------------------------------------------

NUKE_ORDER = [
    "invoice_payment_events",
    "time_entries",
    "service_reminders",
    "service_reminder_configs",
    "purchase_orders",
    "inventory_items",
    "expenses",
    "campaigns",          # shop_id is String — no FK, must delete explicitly
    "shop_agents",        # shop_id is UUID but no FK declared
    "chat_messages",
    "customer_messages",
    "appointments",
    "booking_configs",
    "quotes",             # no shop_id — delete all (single-shop demo)
    "media_files",
    "reports",
    "inspection_sessions",
    "invoices",
    "job_cards",
    "job_card_columns",
    "vendors",
    "vehicles",
    "customers",
    "shop_settings",
    # shops and users: keep rows (auth is in-memory but FK constraints need them)
]


async def nuke(conn: asyncpg.Connection) -> None:
    print("Nuking existing data...")
    for table in NUKE_ORDER:
        await conn.execute(f'DELETE FROM "{table}"')
        print(f"  cleared {table}")


# ---------------------------------------------------------------------------
# Seed functions
# ---------------------------------------------------------------------------

async def seed_shop_and_users(conn: asyncpg.Connection) -> None:
    print("Seeding shop + users...")
    await conn.execute("""
        INSERT INTO shops (id, name, address, labor_rate, pricing_flag)
        VALUES ($1, 'City Auto Care', '1420 W. Maple Ave, Austin, TX 78701', 95.00, 'shop')
        ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, address = EXCLUDED.address
    """, SHOP_ID)

    # Bcrypt hash of "testpass"
    hashed = "$2b$12$wqw07EbXIM9iKhSh/vZm4Os2eyFeY.hY7cFMAQcBmMhAvhc/nRQqi"

    await conn.execute("""
        INSERT INTO users (id, shop_id, email, hashed_password, role, name, preferences)
        VALUES
          ($1, $2, 'owner@shop.com', $3, 'owner', 'Joe Hernandez', '{}'),
          ($4, $2, 'tech@shop.com',  $3, 'technician', 'Dan Rivera', '{}')
        ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name
    """, OWNER_ID, SHOP_ID, hashed, TECH_ID)


async def seed_shop_settings(conn: asyncpg.Connection) -> None:
    print("Seeding shop settings...")
    await conn.execute("""
        INSERT INTO shop_settings (id, shop_id, nav_pins, financing_threshold)
        VALUES ($1, $2, $3, '500')
    """, SS1, SHOP_ID, j(["customers", "reports", "job_cards"]))


async def seed_booking_config(conn: asyncpg.Connection) -> None:
    print("Seeding booking config...")
    await conn.execute("""
        INSERT INTO booking_configs
          (id, shop_id, slug, available_services, working_hours_start,
           working_hours_end, slot_duration_minutes, working_days)
        VALUES ($1, $2, 'city-auto-care',
          $3, '08:00', '17:00', '60', '[1,2,3,4,5]')
    """, BC1, SHOP_ID, j([
        "Oil Change", "Tire Rotation", "Brake Service",
        "A/C Service", "Full Inspection", "Transmission Service",
    ]))


async def seed_customers(conn: asyncpg.Connection) -> None:
    print("Seeding customers...")
    customers = [
        (C1, "James Parker",    "james.parker@gmail.com",     "(512) 555-0101"),
        (C2, "Sarah Chen",      "sarah.chen@outlook.com",     "(512) 555-0102"),
        (C3, "Marcus Johnson",  "marcusj@icloud.com",         "(512) 555-0103"),
        (C4, "Emily Rodriguez", "emily.r@gmail.com",          "(512) 555-0104"),
        (C5, "David Kim",       "david.kim@gmail.com",        "(512) 555-0105"),
        (C6, "Linda Thompson",  "lthompson@yahoo.com",        "(512) 555-0106"),
        (C7, "Robert Martinez", "rmartinez@hotmail.com",      "(512) 555-0107"),
    ]
    await conn.executemany("""
        INSERT INTO customers (id, shop_id, name, email, phone)
        VALUES ($1, $2, $3, $4, $5)
    """, [(c[0], SHOP_ID, c[1], c[2], c[3]) for c in customers])


async def seed_vehicles(conn: asyncpg.Connection) -> None:
    print("Seeding vehicles...")
    vehicles = [
        (V1, C1, 2019, "Toyota",    "Camry",   "SE",      "2T1BURHE0KC185042", "White"),
        (V2, C2, 2021, "BMW",       "330i",    "xDrive",  "3MW5R7J03M8C11234", "Mineral Gray"),
        (V3, C3, 2020, "Ford",      "F-150",   "XLT",     "1FTEW1EP5LFB34567", "Oxford White"),
        (V4, C4, 2018, "Honda",     "Civic",   "LX",      "19XFC2F59JE201348", "Rallye Red"),
        (V5, C5, 2022, "Audi",      "A4",      "Premium", "WAUAAAFY1N2012345", "Glacier White"),
        (V6, C6, 2019, "Subaru",    "Outback", "Premium", "4S4BSANC2K3219876", "Crimson Red"),
        (V7, C7, 2017, "Chevrolet", "Silverado","LT",     "3GCUKREC5HG123456", "Summit White"),
    ]
    await conn.executemany("""
        INSERT INTO vehicles (id, customer_id, year, make, model, trim, vin, color)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
    """, vehicles)


async def seed_vendors(conn: asyncpg.Connection) -> None:
    print("Seeding vendors...")
    await conn.executemany("""
        INSERT INTO vendors
          (id, shop_id, name, category, phone, email, rep_name,
           account_number, ytd_spend, order_count, last_order_at, source)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
    """, [
        (VEN1, SHOP_ID, "NAPA Auto Parts", "Parts", "(512) 555-6001",
         "orders@napa.com", "Kevin Walsh", "NAP-0044821",
         1247.80, 18, ts(3, 14, 30), "manual"),
        (VEN2, SHOP_ID, "AutoZone", "Parts", "(512) 555-6002",
         "commercial@autozone.com", "Maria Flores", "AZC-992341",
         893.40, 12, ts(6, 10, 0), "manual"),
        (VEN3, SHOP_ID, "Advance Auto Parts", "Parts", "(512) 555-6003",
         "commercial@advance.com", "Tom Bradley", "ADV-551002",
         420.00, 6, ts(14, 9, 0), "manual"),
    ])


async def seed_inventory(conn: asyncpg.Connection) -> None:
    print("Seeding inventory...")
    items = [
        (II1, "5W-30 Full Synthetic Oil 5qt", "OIL-5W30-5QT", "Oils",
         24, 12, 8.99, 18.99, VEN1),
        (II2, "Oil Filter — Universal Fit",   "FILTER-OIL-UNI", "Filters",
         30, 15, 3.50, 9.99, VEN2),
        (II3, "Brake Pads — Front Premium",   "BP-FRONT-PREM", "Brakes",
         8, 4, 28.00, 69.99, VEN2),
        (II4, "Brake Rotors — Front (pair)",  "BR-FRONT-PAIR", "Brakes",
         4, 2, 62.00, 139.99, VEN2),
        (II5, "Throttle Position Sensor — F-150 5.0L", "TPS-F150-5L", "Electrical",
         0, 2, 55.00, 119.99, VEN1),   # out of stock — on order
        (II6, "Air Filter — Standard",        "FILTER-AIR-STD", "Filters",
         20, 8, 6.00, 24.99, VEN3),
        (II7, "Cabin Air Filter",             "FILTER-CAB-STD", "Filters",
         14, 6, 7.50, 29.99, VEN3),
        (II8, "ATF Transmission Fluid (1gal)", "ATF-1GAL", "Misc",
         6, 3, 12.00, 34.99, VEN1),
    ]
    await conn.executemany("""
        INSERT INTO inventory_items
          (id, shop_id, name, sku, category, quantity, reorder_at,
           cost_price, sell_price, vendor_id)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
    """, [(i[0], SHOP_ID) + i[1:] for i in items])


async def seed_purchase_orders(conn: asyncpg.Connection) -> None:
    print("Seeding purchase orders...")
    await conn.executemany("""
        INSERT INTO purchase_orders
          (id, shop_id, vendor_id, po_number, status, items, total, notes,
           ordered_at, received_at)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
    """, [
        (
            PO1, SHOP_ID, VEN1, "PO-2026-041",
            "ordered",
            j([{"name": "Throttle Position Sensor — F-150 5.0L",
                "sku": "TPS-F150-5L", "qty": 1, "unit_cost": 55.00}]),
            55.00,
            "Urgent — JC-003 is awaiting this part",
            ts(1, 14, 0), None,
        ),
        (
            PO2, SHOP_ID, VEN2, "PO-2026-039",
            "received",
            j([
                {"name": "Brake Pads — Front Premium", "sku": "BP-FRONT-PREM",
                 "qty": 2, "unit_cost": 28.00},
                {"name": "Brake Rotors — Front (pair)", "sku": "BR-FRONT-PAIR",
                 "qty": 2, "unit_cost": 62.00},
            ]),
            180.00,
            None,
            ts(5, 10, 0), ts(4, 15, 30),
        ),
    ])


async def seed_job_card_columns(conn: asyncpg.Connection) -> None:
    print("Seeding job card columns...")
    await conn.executemany("""
        INSERT INTO job_card_columns (id, shop_id, name, position)
        VALUES ($1,$2,$3,$4)
    """, [
        (JCC1, SHOP_ID, "Scheduled",      1),
        (JCC2, SHOP_ID, "In Progress",    2),
        (JCC3, SHOP_ID, "Awaiting Parts", 3),
        (JCC4, SHOP_ID, "Done",           4),
    ])


async def seed_job_cards(conn: asyncpg.Connection) -> None:
    print("Seeding job cards...")
    # JC1 — James Parker — Front brake service — Done
    jc1_services = j([
        {"description": "Front Brake Pad & Rotor Replacement",
         "labor_hours": 2.5, "labor_rate": 95.0, "labor_cost": 237.50},
    ])
    jc1_parts = j([
        {"name": "Brake Pads — Front Premium", "sku": "BP-FRONT-PREM",
         "qty": 1, "unit_cost": 28.00, "sell_price": 69.99,
         "inventory_item_id": II3},
        {"name": "Brake Rotors — Front (pair)", "sku": "BR-FRONT-PAIR",
         "qty": 1, "unit_cost": 62.00, "sell_price": 139.99,
         "inventory_item_id": II4},
    ])

    # JC2 — Sarah Chen — Transmission flush — In Progress
    jc2_services = j([
        {"description": "Transmission Fluid Flush & Fill",
         "labor_hours": 3.0, "labor_rate": 95.0, "labor_cost": 285.00},
        {"description": "Diagnostic Scan — Transmission Codes",
         "labor_hours": 1.0, "labor_rate": 95.0, "labor_cost": 95.00},
    ])
    jc2_parts = j([
        {"name": "ATF Transmission Fluid (1gal)", "sku": "ATF-1GAL",
         "qty": 4, "unit_cost": 12.00, "sell_price": 34.99,
         "inventory_item_id": II8},
    ])

    # JC3 — Marcus Johnson — Throttle Position Sensor — Awaiting Parts
    jc3_services = j([
        {"description": "Throttle Position Sensor Replacement",
         "labor_hours": 1.5, "labor_rate": 95.0, "labor_cost": 142.50},
        {"description": "Diagnostic Scan",
         "labor_hours": 0.5, "labor_rate": 95.0, "labor_cost": 47.50},
    ])
    jc3_parts = j([
        {"name": "Throttle Position Sensor — F-150 5.0L", "sku": "TPS-F150-5L",
         "qty": 1, "unit_cost": 55.00, "sell_price": 119.99,
         "inventory_item_id": II5},
    ])

    # JC4 — Emily Rodriguez — Oil Change + Tire Rotation — Done
    jc4_services = j([
        {"description": "Oil Change — Full Synthetic 5W-30",
         "labor_hours": 0.5, "labor_rate": 95.0, "labor_cost": 47.50},
        {"description": "Tire Rotation",
         "labor_hours": 0.5, "labor_rate": 95.0, "labor_cost": 47.50},
    ])
    jc4_parts = j([
        {"name": "5W-30 Full Synthetic Oil 5qt", "sku": "OIL-5W30-5QT",
         "qty": 1, "unit_cost": 8.99, "sell_price": 18.99,
         "inventory_item_id": II1},
        {"name": "Oil Filter — Universal Fit", "sku": "FILTER-OIL-UNI",
         "qty": 1, "unit_cost": 3.50, "sell_price": 9.99,
         "inventory_item_id": II2},
    ])

    # JC5 — David Kim — A/C Service — Scheduled
    jc5_services = j([
        {"description": "A/C System Inspection & Recharge",
         "labor_hours": 1.5, "labor_rate": 95.0, "labor_cost": 142.50},
    ])
    jc5_parts = j([])

    rows = [
        (JC1, SHOP_ID, "JC-001", C1, V1, JCC4,
         j([TECH_ID]), jc1_services, jc1_parts,
         "Customer reported spongy pedal and grinding noise when braking. "
         "Inspected: front pads worn to 1mm, rotors warped. Replaced pads + rotors.",
         "closed", ts(4, 9, 0)),
        (JC2, SHOP_ID, "JC-002", C2, V2, JCC2,
         j([TECH_ID]), jc2_services, jc2_parts,
         "P0715 code — turbine speed sensor fault. Flushing transmission fluid first.",
         "active", ts(1, 10, 30)),
        (JC3, SHOP_ID, "JC-003", C3, V3, JCC3,
         j([TECH_ID]), jc3_services, jc3_parts,
         "P0121 code — TPS voltage out of range. Ordered TPS from NAPA ETA May 2.",
         "active", ts(2, 8, 0)),
        (JC4, SHOP_ID, "JC-004", C4, V4, JCC4,
         j([TECH_ID]), jc4_services, jc4_parts,
         "Routine oil change 5W-30 + tire rotation. All torqued to spec.",
         "closed", ts(6, 11, 0)),
        (JC5, SHOP_ID, "JC-005", C5, V5, JCC1,
         j([TECH_ID]), jc5_services, jc5_parts,
         "A/C not cooling — appointment May 5. Check refrigerant level + compressor.",
         "active", ts(0, 9, 0)),
    ]
    await conn.executemany("""
        INSERT INTO job_cards
          (id, shop_id, number, customer_id, vehicle_id, column_id,
           technician_ids, services, parts, notes, status, created_at)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
    """, rows)


async def seed_invoices(conn: asyncpg.Connection) -> None:
    print("Seeding invoices...")
    # INV1 — James Parker — Paid
    inv1_lines = j([
        {"description": "Brake Pads — Front Premium", "qty": 1,
         "unit_price": 69.99, "amount": 69.99},
        {"description": "Brake Rotors — Front (pair)", "qty": 1,
         "unit_price": 139.99, "amount": 139.99},
        {"description": "Labor — Brake Service (2.5 hrs @ $95/hr)", "qty": 1,
         "unit_price": 237.50, "amount": 237.50},
        {"description": "Shop Supplies & Disposal Fee", "qty": 1,
         "unit_price": 25.00, "amount": 25.00},
        {"description": "Texas Sales Tax (6%)", "qty": 1,
         "unit_price": 15.02, "amount": 15.02},
    ])

    # INV2 — Sarah Chen — Pending (in progress)
    inv2_lines = j([
        {"description": "ATF Transmission Fluid (4 gal)", "qty": 4,
         "unit_price": 34.99, "amount": 139.96},
        {"description": "Labor — Transmission Flush (3 hrs @ $95/hr)", "qty": 1,
         "unit_price": 285.00, "amount": 285.00},
        {"description": "Labor — Diagnostic Scan (1 hr @ $95/hr)", "qty": 1,
         "unit_price": 95.00, "amount": 95.00},
        {"description": "Diagnostic Fee", "qty": 1,
         "unit_price": 75.00, "amount": 75.00},
    ])

    # INV3 — Emily Rodriguez — Paid
    inv3_lines = j([
        {"description": "5W-30 Full Synthetic Oil (5 qt)", "qty": 1,
         "unit_price": 18.99, "amount": 18.99},
        {"description": "Oil Filter", "qty": 1,
         "unit_price": 9.99, "amount": 9.99},
        {"description": "Labor — Oil Change (0.5 hr @ $95/hr)", "qty": 1,
         "unit_price": 47.50, "amount": 47.50},
        {"description": "Labor — Tire Rotation (0.5 hr @ $95/hr)", "qty": 1,
         "unit_price": 47.50, "amount": 47.50},
        {"description": "Shop Supplies", "qty": 1,
         "unit_price": 10.00, "amount": 10.00},
        {"description": "Texas Sales Tax (6%)", "qty": 1,
         "unit_price": 64.52, "amount": 64.52},
    ])

    rows = [
        (INV1, SHOP_ID, JC1, "INV-2026-001", C1, V1,
         "paid", inv1_lines, 472.48, 0.0600, 487.50, 487.50,
         date(2026, 4, 30), ts(3, 16, 0)),
        (INV2, SHOP_ID, JC2, "INV-2026-002", C2, V2,
         "pending", inv2_lines, 594.96, 0.0600, 1240.00, 0.0,
         date(2026, 5, 5), ts(1, 15, 0)),
        (INV3, SHOP_ID, JC4, "INV-2026-003", C4, V4,
         "paid", inv3_lines, 133.98, 0.0600, 198.50, 198.50,
         date(2026, 4, 26), ts(5, 17, 0)),
    ]
    await conn.executemany("""
        INSERT INTO invoices
          (id, shop_id, job_card_id, number, customer_id, vehicle_id,
           status, line_items, subtotal, tax_rate, total, amount_paid,
           due_date, created_at)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
    """, rows)


async def seed_payment_events(conn: asyncpg.Connection) -> None:
    print("Seeding payment events...")
    await conn.executemany("""
        INSERT INTO invoice_payment_events
          (id, invoice_id, amount, method, recorded_by, recorded_at, notes)
        VALUES ($1,$2,$3,$4,$5,$6,$7)
    """, [
        (PE1, INV1, 487.50, "cash", OWNER_ID, ts(3, 17, 0),
         "Paid in full at pickup"),
        (PE2, INV3, 198.50, "card", OWNER_ID, ts(5, 17, 30),
         "Visa ending 4242"),
    ])


async def seed_inspection_sessions(conn: asyncpg.Connection) -> None:
    print("Seeding inspection sessions...")
    await conn.executemany("""
        INSERT INTO inspection_sessions
          (id, shop_id, technician_id, status, vehicle, transcript,
           created_at, completed_at)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
    """, [
        (
            IS1, SHOP_ID, TECH_ID, "complete",
            j({"year": 2019, "make": "Toyota", "model": "Camry", "vin": "2T1BURHE0KC185042",
               "color": "White", "mileage": 52340}),
            "Inspecting the 2019 Toyota Camry, VIN 2T1BURHE0KC185042, mileage 52,340. "
            "Starting with the brakes. Front pads are worn down to about 1 millimeter, "
            "well below the 3mm wear limit. I can see metal-to-metal contact starting. "
            "Front rotors are warped — I'll measure but they need replacement. "
            "Rear brakes look okay, about 5mm remaining. Tire tread is good, around 7/32. "
            "Fluids are all within spec. Engine looks clean, no leaks. "
            "Air filter is due for replacement at next service.",
            ts(4, 8, 30), ts(4, 9, 15),
        ),
        (
            IS2, SHOP_ID, TECH_ID, "complete",
            j({"year": 2018, "make": "Honda", "model": "Civic", "vin": "19XFC2F59JE201348",
               "color": "Rallye Red", "mileage": 38120}),
            "Inspecting the 2018 Honda Civic. Mileage 38,120. "
            "Customer is here for routine oil change and tire rotation. "
            "Oil is dark but no metal shavings. Drain plug is clean. "
            "Installing new oil filter and 5W-30 synthetic. "
            "Tires rotated front to rear. All lugs torqued to 80 ft-lbs. "
            "Quick visual: brakes look great, pads at 7mm. "
            "No leaks, no issues. Vehicle is ready.",
            ts(6, 10, 0), ts(6, 10, 45),
        ),
        (
            IS3, SHOP_ID, TECH_ID, "processing",
            j({"year": 2021, "make": "BMW", "model": "330i", "vin": "3MW5R7J03M8C11234",
               "color": "Mineral Gray", "mileage": 41800}),
            "Scanning the 2021 BMW 330i, VIN ending C11234. Pulling codes now. "
            "Got P0715 — Input Turbine Speed Sensor Circuit. "
            "P0730 as well — Incorrect Gear Ratio. "
            "Transmission feels sluggish between 2nd and 3rd. "
            "Fluid looks burnt, dark brown. Going to recommend full ATF flush. "
            "Price for ATF flush plus labor is going in the estimate.",
            ts(1, 10, 0), None,
        ),
    ])


async def seed_media_files(conn: asyncpg.Connection) -> None:
    print("Seeding media files...")
    await conn.executemany("""
        INSERT INTO media_files (id, session_id, type, tag, s3_url, filename)
        VALUES ($1,$2,$3,$4,$5,$6)
    """, [
        (MF1, IS1, "photo", "vin",
         "https://demo-assets.cityautocare.com/inspections/is1/vin.jpg",
         "vin.jpg"),
        (MF2, IS1, "photo", "odometer",
         "https://demo-assets.cityautocare.com/inspections/is1/odometer.jpg",
         "odometer.jpg"),
        (MF3, IS1, "photo", "damage",
         "https://demo-assets.cityautocare.com/inspections/is1/brake_wear.jpg",
         "brake_wear.jpg"),
        (MF4, IS2, "photo", "vin",
         "https://demo-assets.cityautocare.com/inspections/is2/vin.jpg",
         "vin.jpg"),
    ])


async def seed_reports(conn: asyncpg.Connection) -> None:
    print("Seeding reports...")
    r1_findings = j([
        {"part": "Front Brake Pads", "severity": "high",
         "notes": "Worn to 1mm — metal-to-metal contact. Immediate replacement required.",
         "photo_url": "https://demo-assets.cityautocare.com/inspections/is1/brake_wear.jpg"},
        {"part": "Front Brake Rotors", "severity": "high",
         "notes": "Warped — lateral runout exceeds 0.002\". Replacement required."},
        {"part": "Air Filter", "severity": "low",
         "notes": "Clogged — recommend replacement at next service interval."},
    ])
    r1_estimate = j({"line_items": [
        {"part": "Front Brake Pad & Rotor Replacement",
         "labor_hours": 2.5, "labor_rate": 95.0, "labor_cost": 237.50,
         "parts_cost": 209.98, "total": 447.48},
        {"part": "Shop Supplies & Disposal",
         "labor_hours": 0.0, "labor_rate": 0.0, "labor_cost": 0.0,
         "parts_cost": 25.00, "total": 25.00},
    ]})

    r2_findings = j([
        {"part": "Engine Oil", "severity": "low",
         "notes": "Dark but within service interval. Changed with this visit."},
        {"part": "Brake Pads (Front)", "severity": "low",
         "notes": "7mm remaining — in good condition."},
        {"part": "Tires", "severity": "low",
         "notes": "Even wear, approximately 8/32 remaining. Good for another 20k miles."},
    ])
    r2_estimate = j({"line_items": [
        {"part": "Oil Change — 5W-30 Synthetic",
         "labor_hours": 0.5, "labor_rate": 95.0, "labor_cost": 47.50,
         "parts_cost": 28.98, "total": 76.48},
        {"part": "Tire Rotation",
         "labor_hours": 0.5, "labor_rate": 95.0, "labor_cost": 47.50,
         "parts_cost": 0.0, "total": 47.50},
    ]})

    await conn.executemany("""
        INSERT INTO reports
          (id, session_id, vehicle_id, summary, title, status,
           findings, estimate, estimate_total, vehicle,
           share_token, sent_to, created_at)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
    """, [
        (
            R1, IS1, V1,
            "Front brakes require immediate attention — pads at 1mm, rotors warped. "
            "Brake replacement performed same day. Vehicle safe and ready.",
            "Brake Inspection — 2019 Toyota Camry",
            "final",
            r1_findings,
            r1_estimate,
            472.48,
            j({"year": 2019, "make": "Toyota", "model": "Camry",
               "vin": "2T1BURHE0KC185042", "mileage": 52340}),
            RS1,
            j({"email": "james.parker@gmail.com"}),
            ts(4, 9, 20),
        ),
        (
            R2, IS2, V4,
            "Routine maintenance completed — oil change and tire rotation. "
            "Vehicle is in excellent condition for its mileage.",
            "Routine Service — 2018 Honda Civic",
            "final",
            r2_findings,
            r2_estimate,
            123.98,
            j({"year": 2018, "make": "Honda", "model": "Civic",
               "vin": "19XFC2F59JE201348", "mileage": 38120}),
            RS2,
            j({"email": "emily.r@gmail.com"}),
            ts(6, 10, 50),
        ),
    ])


async def seed_quotes(conn: asyncpg.Connection) -> None:
    print("Seeding quotes...")
    q1_lines = j([
        {"type": "parts", "description": "Brake Pads — Front Premium",
         "qty": 1, "unit_price": 69.99, "total": 69.99},
        {"type": "parts", "description": "Brake Rotors — Front (pair)",
         "qty": 1, "unit_price": 139.99, "total": 139.99},
        {"type": "labor", "description": "Brake Service (2.5 hrs)",
         "qty": 2.5, "unit_price": 95.00, "total": 237.50},
    ])
    q2_lines = j([
        {"type": "parts", "description": "ATF Transmission Fluid (4 gal)",
         "qty": 4, "unit_price": 34.99, "total": 139.96},
        {"type": "labor", "description": "Transmission Flush (3 hrs)",
         "qty": 3, "unit_price": 95.00, "total": 285.00},
        {"type": "labor", "description": "Diagnostic Scan (1 hr)",
         "qty": 1, "unit_price": 95.00, "total": 95.00},
    ])
    await conn.executemany("""
        INSERT INTO quotes (id, session_id, status, line_items, total, created_at)
        VALUES ($1,$2,$3,$4,$5,$6)
    """, [
        (Q1, IS1, "final", q1_lines, 447.48, ts(4, 9, 25)),
        (Q2, IS3, "draft", q2_lines, 519.96, ts(1, 10, 15)),
    ])


async def seed_appointments(conn: asyncpg.Connection) -> None:
    print("Seeding appointments...")
    await conn.executemany("""
        INSERT INTO appointments
          (id, shop_id, customer_id, vehicle_id, starts_at, ends_at,
           service_requested, status, notes, source,
           customer_name, customer_phone, customer_email, job_card_id)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
    """, [
        (
            A1, SHOP_ID, C5, V5,
            dt(4, 9, 0), dt(4, 11, 0),
            "A/C System Inspection & Recharge",
            "confirmed",
            "Customer says A/C stopped blowing cold last week. Audi A4.",
            "manual",
            "David Kim", "(512) 555-0105", "david.kim@gmail.com",
            JC5,
        ),
        (
            A2, SHOP_ID, C6, V6,
            dt(6, 10, 0), dt(6, 11, 0),
            "Full Inspection",
            "pending",
            "Booked via online booking link. New customer.",
            "booking_link",
            "Linda Thompson", "(512) 555-0106", "lthompson@yahoo.com",
            None,
        ),
        (
            A3, SHOP_ID, C7, V7,
            dt(11, 14, 0), dt(11, 15, 0),
            "Oil Change",
            "pending",
            "Overdue by 14 months — follow-up after reminder SMS sent.",
            "manual",
            "Robert Martinez", "(512) 555-0107", "rmartinez@hotmail.com",
            None,
        ),
    ])


async def seed_service_reminder_configs(conn: asyncpg.Connection) -> None:
    print("Seeding service reminder configs...")
    await conn.executemany("""
        INSERT INTO service_reminder_configs
          (id, shop_id, service_type, window_start_months, window_end_months,
           sms_enabled, email_enabled, message_template)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
    """, [
        (SRC1, SHOP_ID, "Oil Change", 3, 6, True, True,
         "Hi {first_name}, your {vehicle} is due for an oil change. "
         "Book now: {booking_link}"),
        (SRC2, SHOP_ID, "Tire Rotation", 6, 12, True, True,
         "Hi {first_name}, time for a tire rotation on your {vehicle}. "
         "Book now: {booking_link}"),
        (SRC3, SHOP_ID, "Full Service", 10, 14, True, True,
         "Hi {first_name}, your {vehicle} is due for a full service. "
         "Book now: {booking_link}"),
        (SRC4, SHOP_ID, "AC Check", 10, 14, True, False,
         "Hi {first_name}, time to check the AC on your {vehicle}. "
         "Book now: {booking_link}"),
    ])


async def seed_service_reminders(conn: asyncpg.Connection) -> None:
    print("Seeding service reminders...")
    # Robert's Silverado — oil change overdue 14 months
    last_service_robert = datetime(2025, 3, 1, 10, 0, tzinfo=timezone.utc)
    # James — tire rotation upcoming (last done April 25, 2026 with brake service)
    last_service_james = datetime(2026, 4, 25, 9, 0, tzinfo=timezone.utc)
    # Emily — already booked follow-up
    last_service_emily = datetime(2026, 4, 25, 10, 45, tzinfo=timezone.utc)
    # Sarah — full service coming up
    last_service_sarah = datetime(2025, 7, 15, 11, 0, tzinfo=timezone.utc)

    await conn.executemany("""
        INSERT INTO service_reminders
          (id, shop_id, customer_id, vehicle_id, config_id, service_type,
           status, last_sent_at, last_service_at, send_count)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
    """, [
        (SR1, SHOP_ID, C7, V7, SRC1, "Oil Change",
         "active", ts(3, 9, 0), last_service_robert, 2),
        (SR2, SHOP_ID, C1, V1, SRC2, "Tire Rotation",
         "active", None, last_service_james, 0),
        (SR3, SHOP_ID, C4, V4, SRC1, "Oil Change",
         "booked", ts(6, 11, 0), last_service_emily, 1),
        (SR4, SHOP_ID, C2, V2, SRC3, "Full Service",
         "active", ts(14, 9, 0), last_service_sarah, 1),
    ])


async def seed_time_entries(conn: asyncpg.Connection) -> None:
    print("Seeding time entries...")
    await conn.executemany("""
        INSERT INTO time_entries
          (id, shop_id, user_id, job_card_id, task_type,
           started_at, ended_at, duration_minutes, notes)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
    """, [
        (TE1, SHOP_ID, TECH_ID, JC1, "Repair",
         ts(4, 9, 0), ts(4, 11, 30), 150,
         "Front brake pad and rotor replacement — R&R both sides"),
        (TE2, SHOP_ID, TECH_ID, JC4, "Repair",
         ts(6, 10, 0), ts(6, 11, 0), 60,
         "Oil change 5W-30 + tire rotation"),
        (TE3, SHOP_ID, TECH_ID, JC2, "Repair",
         ts(1, 10, 30), None, None,
         "Transmission flush in progress"),
        (TE4, SHOP_ID, TECH_ID, JC3, "Diagnosis",
         ts(2, 8, 0), ts(2, 8, 30), 30,
         "Scan codes — P0121 confirmed TPS fault. Part ordered."),
    ])


async def seed_expenses(conn: asyncpg.Connection) -> None:
    print("Seeding expenses...")
    await conn.executemany("""
        INSERT INTO expenses
          (id, shop_id, description, amount, category, vendor,
           expense_date, qb_synced)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
    """, [
        (EX1, SHOP_ID, "Shop supplies — rags, gloves, penetrating oil",
         47.32, "Misc", "Home Depot", date(2026, 4, 28), False),
        (EX2, SHOP_ID, "Brake parts — PO-2026-039 (pads + rotors × 2)",
         180.00, "Parts", "AutoZone", date(2026, 4, 25), False),
        (EX3, SHOP_ID, "April electricity & water",
         312.18, "Utilities", "Austin Energy", date(2026, 4, 1), True),
        (EX4, SHOP_ID, "Alignment rack — annual calibration service",
         225.00, "Equipment", "Hunter Engineering", date(2026, 3, 15), True),
    ])


async def seed_campaigns(conn: asyncpg.Connection) -> None:
    print("Seeding campaigns...")
    await conn.executemany("""
        INSERT INTO campaigns
          (id, shop_id, name, status, message_body, channel,
           audience_segment, send_at, sent_at, stats, created_at)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
    """, [
        (
            CAM1, SHOP_ID,
            "Spring A/C Check — 2026",
            "sent",
            "Summer's coming! Get your A/C checked before the heat hits. "
            "Book a free A/C inspection at City Auto Care: cityautocare.com/book "
            "Reply STOP to opt out.",
            "sms",
            j({"service_type": "AC Check", "months_overdue_min": 8}),
            ts(10, 10, 0), ts(10, 10, 5),
            j({"sent_count": 47, "opened_count": 31, "booked_count": 8}),
            ts(11, 9, 0),
        ),
        (
            CAM2, SHOP_ID,
            "Mother's Day Oil Change Special",
            "Show Mom some love this Mother's Day! $20 off any oil change "
            "May 6–12 at City Auto Care. Book: cityautocare.com/book",
            "draft",
            "email",
            j({"service_type": "Oil Change", "months_overdue_min": 3}),
            None, None,
            j({"sent_count": 0, "opened_count": 0, "booked_count": 0}),
            ts(0, 11, 0),
        ),
    ])


async def seed_shop_agents(conn: asyncpg.Connection) -> None:
    print("Seeding shop agents...")
    sa_prompt = lambda role, focus: (
        f"You are the {role} at City Auto Care, an AI assistant with access to shop tools. "
        f"Your focus: {focus}. "
        "Always be concise, professional, and helpful. Use your tools to provide accurate information."
    )
    agents = [
        (SA1, SHOP_ID, "Service Advisor", "Front desk · Customer intake", "#d97706",
         "SA", sa_prompt("Service Advisor",
             "customer communication, appointment scheduling, invoice status, and job card updates"),
         j(["shop_data", "quote_builder"]), 0),
        (SA2, SHOP_ID, "Technician", "Inspections · Diagnostics · Repairs", "#3b82f6",
         "TK", sa_prompt("Technician",
             "vehicle inspections, diagnostic codes, labor time estimates, and VIN lookups"),
         j(["vin_lookup", "shop_data", "quote_builder"]), 1),
        (SA3, SHOP_ID, "Parts Manager", "Parts sourcing · Inventory", "#06b6d4",
         "PM", sa_prompt("Parts Manager",
             "parts availability, pricing, inventory levels, purchase orders, and vendor contacts"),
         j(["parts_search", "shop_data"]), 2),
        (SA4, SHOP_ID, "Bookkeeper", "Invoices · Payments · Accounting", "#22c55e",
         "BK", sa_prompt("Bookkeeper",
             "invoices, payments, expenses, and financial reporting"),
         j(["shop_data"]), 3),
        (SA5, SHOP_ID, "Manager", "Operations · Reporting · Marketing", "#a855f7",
         "MG", sa_prompt("Manager",
             "shop operations, team performance, marketing campaigns, and business metrics"),
         j(["shop_data", "quote_builder"]), 4),
    ]
    await conn.executemany("""
        INSERT INTO shop_agents
          (id, shop_id, name, role_tagline, accent_color, initials,
           system_prompt, tools, sort_order)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
    """, agents)


async def seed_chat_messages(conn: asyncpg.Connection) -> None:
    print("Seeding chat messages...")
    await conn.executemany("""
        INSERT INTO chat_messages
          (id, user_id, agent_id, role, content, tool_calls, created_at)
        VALUES ($1,$2,$3,$4,$5,$6,$7)
    """, [
        (
            CM1, OWNER_ID, str(SA1), "user",
            j([{"type": "text", "text": "What's the status on Sarah Chen's BMW?"}]),
            None,
            ts(1, 11, 0),
        ),
        (
            CM2, OWNER_ID, str(SA1), "assistant",
            j([{"type": "text",
                "text": "Sarah Chen's 2021 BMW 330i (JC-002) is currently in progress. "
                        "Dan Rivera is doing a transmission fluid flush — P0715 code triggered it. "
                        "Invoice INV-2026-002 is drafted at $1,240.00, due May 5. "
                        "No payment received yet."}]),
            j([{"name": "shop_data", "input": {"query": "Sarah Chen job card"},
                "output": {"found": True, "card": "JC-002"}}]),
            ts(1, 11, 1),
        ),
        (
            CM3, OWNER_ID, str(SA2), "user",
            j([{"type": "text",
                "text": "What's the ETA on Marcus Johnson's TPS part from NAPA?"}]),
            None,
            ts(1, 14, 0),
        ),
        (
            CM4, OWNER_ID, str(SA2), "assistant",
            j([{"type": "text",
                "text": "PO-2026-041 was placed yesterday with NAPA for the Throttle Position Sensor "
                        "(TPS-F150-5L, $55). Status: ordered, no received date yet. "
                        "NAPA rep Kevin Walsh (512-555-6001) should have an ETA. "
                        "Marcus's F-150 (JC-003) is parked in bay 3 waiting on that part."}]),
            None,
            ts(1, 14, 1),
        ),
    ])


async def seed_customer_messages(conn: asyncpg.Connection) -> None:
    print("Seeding customer messages...")
    await conn.executemany("""
        INSERT INTO customer_messages
          (id, vehicle_id, report_id, direction, channel, body,
           external_id, sent_at, created_at)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
    """, [
        (
            CMSG1, V1, R1, "out", "email",
            "Hi James — your brake inspection report is ready. "
            "View it here: https://app.cityautocare.com/r/" + RS1,
            "sg-msg-001",
            ts(4, 9, 25), ts(4, 9, 25),
        ),
        (
            CMSG2, V4, R2, "out", "email",
            "Hi Emily — your service report is ready. "
            "View it here: https://app.cityautocare.com/r/" + RS2,
            "sg-msg-002",
            ts(6, 10, 55), ts(6, 10, 55),
        ),
        (
            CMSG3, V4, R2, "in", "email",
            "Thanks! Everything looks great. See you next time!",
            "sg-inbound-003",
            ts(6, 14, 0), ts(6, 14, 0),
        ),
    ])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    raw_url = os.environ.get("DATABASE_URL", "")
    if not raw_url:
        print("ERROR: DATABASE_URL env var is required.", file=sys.stderr)
        sys.exit(1)

    # asyncpg expects postgresql:// not postgresql+asyncpg://
    pg_url = re.sub(r"^postgresql\+asyncpg://", "postgresql://", raw_url)

    print(f"Connecting to database...")
    conn: asyncpg.Connection = await asyncpg.connect(pg_url)

    try:
        async with conn.transaction():
            await nuke(conn)

            await seed_shop_and_users(conn)
            await seed_shop_settings(conn)
            await seed_booking_config(conn)
            await seed_customers(conn)
            await seed_vehicles(conn)
            await seed_vendors(conn)
            await seed_inventory(conn)
            await seed_purchase_orders(conn)
            await seed_job_card_columns(conn)
            await seed_job_cards(conn)
            await seed_invoices(conn)
            await seed_payment_events(conn)
            await seed_inspection_sessions(conn)
            await seed_media_files(conn)
            await seed_reports(conn)
            await seed_quotes(conn)
            await seed_appointments(conn)
            await seed_service_reminder_configs(conn)
            await seed_service_reminders(conn)
            await seed_time_entries(conn)
            await seed_expenses(conn)
            await seed_campaigns(conn)
            await seed_shop_agents(conn)
            await seed_chat_messages(conn)
            await seed_customer_messages(conn)

        print("\nSeed complete.")
        print("  Shop:      City Auto Care")
        print("  Login:     owner@shop.com / testpass  (or tech@shop.com / testpass)")
        print("  Customers: 7  |  Vehicles: 7  |  Job Cards: 5  |  Invoices: 3")
        print("  Agents: 5  |  Appointments: 3  |  Campaigns: 2  |  Reports: 2")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
