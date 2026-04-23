"""Shop DB query tools for the Tom agent."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.models.session import InspectionSession
from src.models.report import Report

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
    result = await db.execute(select(InspectionSession).where(InspectionSession.id == session_id))
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
    result = await db.execute(select(Report).where(Report.session_id == session_id))
    report = result.scalar_one_or_none()
    if not report:
        return {"error": f"No report found for session {session_id}"}
    return {
        "id": str(report.id),
        "summary": report.summary,
        "findings": report.findings,
        "estimate_total": float(report.estimate_total) if report.estimate_total else None,
    }
