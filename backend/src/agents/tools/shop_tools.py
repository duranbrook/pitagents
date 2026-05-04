"""Shop DB query tools for the Tom agent."""
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from src.models.session import InspectionSession
from src.models.report import Report
from src.models.customer import Customer
from src.models.vehicle import Vehicle

SHOP_TOOL_SCHEMAS = [
    {
        "name": "list_sessions",
        "description": "List recent inspection sessions in the shop, with their status and vehicle info.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max results to return (default 10)"}
            },
            "required": [],
        },
    },
    {
        "name": "get_session_detail",
        "description": "Get full details of a specific inspection session including transcript and findings.",
        "input_schema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "UUID of the inspection session"}
            },
            "required": ["session_id"],
        },
    },
    {
        "name": "get_report",
        "description": "Get the completed report for an inspection session, including the estimate total.",
        "input_schema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "UUID of the inspection session"}
            },
            "required": ["session_id"],
        },
    },
    {
        "name": "lookup_customer",
        "description": "Search for a customer by name (case-insensitive partial match). Returns matching customers with their IDs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Customer name or partial name to search for"}
            },
            "required": ["name"],
        },
    },
    {
        "name": "get_customer_vehicles",
        "description": "Get all vehicles registered for a customer.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "UUID of the customer"}
            },
            "required": ["customer_id"],
        },
    },
    {
        "name": "find_sessions_by_vehicle",
        "description": "Find all inspection sessions for a specific vehicle. Use after get_customer_vehicles to get the vehicle_id.",
        "input_schema": {
            "type": "object",
            "properties": {
                "vehicle_id": {"type": "string", "description": "UUID of the vehicle"}
            },
            "required": ["vehicle_id"],
        },
    },
]


async def list_sessions(db: AsyncSession, limit: int = 10) -> list[dict]:
    result = await db.execute(
        select(InspectionSession).order_by(InspectionSession.created_at.desc()).limit(limit)
    )
    sessions = result.scalars().all()
    return [
        {
            "id": str(s.id),
            "status": s.status,
            "vehicle": s.vehicle,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in sessions
    ]


async def get_session_detail(db: AsyncSession, session_id: str) -> dict:
    try:
        uid = uuid.UUID(session_id)
    except ValueError:
        return {"error": f"Invalid session_id: {session_id}"}
    result = await db.execute(select(InspectionSession).where(InspectionSession.id == uid))
    session = result.scalar_one_or_none()
    if not session:
        return {"error": f"Session {session_id} not found"}
    return {
        "id": str(session.id),
        "status": session.status,
        "vehicle": session.vehicle,
        "transcript": session.transcript,
        "created_at": session.created_at.isoformat() if session.created_at else None,
    }


async def get_report(db: AsyncSession, session_id: str) -> dict:
    try:
        uid = uuid.UUID(session_id)
    except ValueError:
        return {"error": f"Invalid session_id: {session_id}"}
    result = await db.execute(select(Report).where(Report.session_id == uid))
    report = result.scalar_one_or_none()
    if not report:
        return {"error": f"No report found for session {session_id}"}
    return {
        "id": str(report.id),
        "summary": report.summary,
        "findings": report.findings,
        "estimate_total": float(report.estimate_total) if report.estimate_total else None,
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }


async def lookup_customer(db: AsyncSession, name: str) -> list[dict]:
    result = await db.execute(
        select(Customer).where(func.lower(Customer.name).contains(name.lower()))
    )
    customers = result.scalars().all()
    return [
        {
            "id": str(c.id),
            "name": c.name,
            "email": c.email,
            "phone": c.phone,
        }
        for c in customers
    ]


async def get_customer_vehicles(db: AsyncSession, customer_id: str) -> list[dict]:
    try:
        uid = uuid.UUID(customer_id)
    except ValueError:
        return [{"error": f"Invalid customer_id: {customer_id}"}]
    result = await db.execute(select(Vehicle).where(Vehicle.customer_id == uid))
    vehicles = result.scalars().all()
    return [
        {
            "id": str(v.id),
            "year": v.year,
            "make": v.make,
            "model": v.model,
            "trim": v.trim,
            "vin": v.vin,
            "color": v.color,
        }
        for v in vehicles
    ]


async def find_sessions_by_vehicle(db: AsyncSession, vehicle_id: str) -> list[dict]:
    result = await db.execute(
        select(InspectionSession)
        .where(InspectionSession.vehicle["vehicle_id"].as_string() == vehicle_id)
        .order_by(InspectionSession.created_at.desc())
    )
    sessions = result.scalars().all()
    return [
        {
            "id": str(s.id),
            "status": s.status,
            "vehicle": s.vehicle,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in sessions
    ]
