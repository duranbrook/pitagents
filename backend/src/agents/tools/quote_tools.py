"""Quote-building tools for the Quote agent."""
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.models.quote import Quote
from src.models.report import Report
from src.models.shop import Shop

PARTS_CATALOG = [
    {"part": "Brake Pads (Front)", "part_number": "BP-F-001", "unit_price": 89.99},
    {"part": "Brake Pads (Rear)", "part_number": "BP-R-001", "unit_price": 79.99},
    {"part": "Brake Rotor (Front)", "part_number": "BR-F-001", "unit_price": 129.99},
    {"part": "Brake Rotor (Rear)", "part_number": "BR-R-001", "unit_price": 109.99},
    {"part": "Oil Filter", "part_number": "OF-001", "unit_price": 12.99},
    {"part": "Air Filter", "part_number": "AF-001", "unit_price": 24.99},
    {"part": "Cabin Air Filter", "part_number": "CAF-001", "unit_price": 19.99},
    {"part": "Wiper Blades", "part_number": "WB-001", "unit_price": 34.99},
    {"part": "Spark Plugs (set of 4)", "part_number": "SP-001", "unit_price": 49.99},
    {"part": "Battery", "part_number": "BAT-001", "unit_price": 179.99},
    {"part": "Serpentine Belt", "part_number": "SB-001", "unit_price": 64.99},
    {"part": "Coolant", "part_number": "COOL-001", "unit_price": 29.99},
]

TEST_SHOP_ID = "00000000-0000-0000-0000-000000000099"
FALLBACK_LABOR_RATE = 120.00

QUOTE_TOOL_SCHEMAS = [
    {
        "name": "lookup_part_price",
        "description": (
            "Look up the price of a part by name from the shop's parts catalog. "
            "Uses case-insensitive substring matching. Returns part name, part number, and unit price."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "part_name": {
                    "type": "string",
                    "description": "Name or partial name of the part to look up (e.g. 'brake pads', 'oil filter')",
                }
            },
            "required": ["part_name"],
        },
    },
    {
        "name": "estimate_labor",
        "description": (
            "Estimate the labor cost for a repair task given the task name and estimated hours. "
            "Fetches the shop's labor rate from the database and returns the total labor cost."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "task_name": {
                    "type": "string",
                    "description": "Name of the labor task (e.g. 'Replace front brake pads')",
                },
                "hours": {
                    "type": "number",
                    "description": "Estimated number of labor hours for the task",
                },
            },
            "required": ["task_name", "hours"],
        },
    },
    {
        "name": "create_quote",
        "description": (
            "Create a new draft quote in the database, optionally linked to a vehicle (via vehicle_id) "
            "or an inspection session (via session_id). Returns the new quote ID."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "vehicle_id": {
                    "type": "string",
                    "description": "UUID of the vehicle this quote is for (use when you know the vehicle from a VIN lookup)",
                },
                "session_id": {
                    "type": "string",
                    "description": "Optional UUID of an inspection session to link this quote to",
                },
            },
            "required": [],
        },
    },
    {
        "name": "create_quote_item",
        "description": (
            "Add a line item (part or labor) to an existing quote. "
            "Recalculates the quote total after adding the item."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "quote_id": {
                    "type": "string",
                    "description": "UUID of the quote to add the item to",
                },
                "item_type": {
                    "type": "string",
                    "description": "Type of line item: 'part' or 'labor'",
                    "enum": ["part", "labor"],
                },
                "description": {
                    "type": "string",
                    "description": "Human-readable description of the line item",
                },
                "qty": {
                    "type": "number",
                    "description": "Quantity (for parts) or hours (for labor)",
                },
                "unit_price": {
                    "type": "number",
                    "description": "Unit price per item or per hour",
                },
            },
            "required": ["quote_id", "item_type", "description", "qty", "unit_price"],
        },
    },
    {
        "name": "list_quote_items",
        "description": (
            "List all line items on a quote, along with the quote status and running total."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "quote_id": {
                    "type": "string",
                    "description": "UUID of the quote to retrieve",
                }
            },
            "required": ["quote_id"],
        },
    },
    {
        "name": "finalize_quote",
        "description": (
            "Finalize a draft quote by setting its status to 'final'. "
            "If the quote is linked to an inspection session, also updates the session report's estimate total."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "quote_id": {
                    "type": "string",
                    "description": "UUID of the quote to finalize",
                }
            },
            "required": ["quote_id"],
        },
    },
]


async def lookup_part_price(part_name: str) -> dict:
    needle = part_name.lower().strip()
    for entry in PARTS_CATALOG:
        if needle in entry["part"].lower():
            return {
                "part": entry["part"],
                "part_number": entry["part_number"],
                "unit_price": entry["unit_price"],
            }
    return {"error": f"Part not found: {part_name}"}


async def estimate_labor(task_name: str, hours: float, db: AsyncSession) -> dict:
    shop_uid = uuid.UUID(TEST_SHOP_ID)
    result = await db.execute(select(Shop).where(Shop.id == shop_uid))
    shop = result.scalar_one_or_none()
    rate = float(shop.labor_rate) if shop and shop.labor_rate is not None else FALLBACK_LABOR_RATE
    return {
        "task": task_name,
        "hours": hours,
        "rate": rate,
        "total": round(hours * rate, 2),
    }


async def create_quote(
    db: AsyncSession,
    session_id: str | None = None,
    vehicle_id: str | None = None,
) -> dict:
    sid = None
    if session_id:
        try:
            sid = uuid.UUID(session_id)
        except ValueError:
            return {"error": f"Invalid session_id: {session_id}"}

    vid = None
    if vehicle_id:
        try:
            vid = uuid.UUID(vehicle_id)
        except ValueError:
            return {"error": f"Invalid vehicle_id: {vehicle_id}"}

    quote = Quote(session_id=sid, vehicle_id=vid)
    db.add(quote)
    await db.commit()
    await db.refresh(quote)
    return {"quote_id": str(quote.id), "status": quote.status}


async def create_quote_item(
    quote_id: str,
    item_type: str,
    description: str,
    qty: float,
    unit_price: float,
    db: AsyncSession,
) -> dict:
    try:
        qid = uuid.UUID(quote_id)
    except ValueError:
        return {"error": f"Invalid quote_id: {quote_id}"}

    if item_type not in ("part", "labor"):
        return {"error": f"item_type must be 'part' or 'labor', got: {item_type!r}"}

    result = await db.execute(select(Quote).where(Quote.id == qid))
    quote = result.scalar_one_or_none()
    if not quote:
        return {"error": f"Quote {quote_id} not found"}

    item = {
        "type": item_type,
        "description": description,
        "qty": qty,
        "unit_price": unit_price,
        "total": round(qty * unit_price, 2),
    }
    new_items = list(quote.line_items or []) + [item]
    quote.line_items = new_items
    quote.total = sum(i["total"] for i in new_items)
    await db.commit()
    await db.refresh(quote)
    return {
        "quote_id": str(quote.id),
        "line_items": list(quote.line_items),
        "total": float(quote.total),
    }


async def list_quote_items(quote_id: str, db: AsyncSession) -> dict:
    try:
        qid = uuid.UUID(quote_id)
    except ValueError:
        return {"error": f"Invalid quote_id: {quote_id}"}

    result = await db.execute(select(Quote).where(Quote.id == qid))
    quote = result.scalar_one_or_none()
    if not quote:
        return {"error": f"Quote {quote_id} not found"}

    return {
        "quote_id": str(quote.id),
        "status": quote.status,
        "line_items": list(quote.line_items or []),
        "total": float(quote.total) if quote.total is not None else 0.0,
    }


async def finalize_quote(quote_id: str, db: AsyncSession) -> dict:
    try:
        qid = uuid.UUID(quote_id)
    except ValueError:
        return {"error": f"Invalid quote_id: {quote_id}"}

    result = await db.execute(select(Quote).where(Quote.id == qid))
    quote = result.scalar_one_or_none()
    if not quote:
        return {"error": f"Quote {quote_id} not found"}

    quote.status = "final"
    total = float(quote.total) if quote.total is not None else 0.0

    if quote.session_id:
        report_result = await db.execute(
            select(Report).where(Report.session_id == quote.session_id)
        )
        report = report_result.scalar_one_or_none()
        if report:
            report.estimate_total = total

    await db.commit()
    await db.refresh(quote)
    return {"quote_id": str(quote.id), "status": "final", "total": total}
