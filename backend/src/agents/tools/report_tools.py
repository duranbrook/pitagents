"""Report-building tools for the Report agent."""
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update as sa_update
from src.models.report import Report
from src.models.vehicle import Vehicle

REPORT_TOOL_SCHEMAS = [
    {
        "name": "create_report",
        "description": (
            "Create a new draft report in the database linked to a vehicle. "
            "The report starts with no session, empty findings, and an empty estimate. "
            "Returns the new report ID."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "vehicle_id": {
                    "type": "string",
                    "description": "UUID of the vehicle this report is for",
                }
            },
            "required": ["vehicle_id"],
        },
    },
    {
        "name": "add_report_item",
        "description": (
            "Add a line item to an existing report's estimate. "
            "Each item captures the repair description, labor hours, labor rate, and parts cost. "
            "Recalculates the estimate total after adding the item."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "report_id": {
                    "type": "string",
                    "description": "UUID of the report to add the item to",
                },
                "part": {
                    "type": "string",
                    "description": "Description of the repair or part (e.g. 'Replace front brake pads')",
                },
                "labor_hours": {
                    "type": "number",
                    "description": "Estimated labor hours for this item",
                },
                "labor_rate": {
                    "type": "number",
                    "description": "Labor rate in dollars per hour",
                },
                "parts_cost": {
                    "type": "number",
                    "description": "Cost of parts in dollars",
                },
            },
            "required": ["report_id", "part", "labor_hours", "labor_rate", "parts_cost"],
        },
    },
    {
        "name": "list_report_items",
        "description": (
            "List all line items on a report's estimate, along with the running total."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "report_id": {
                    "type": "string",
                    "description": "UUID of the report to retrieve",
                }
            },
            "required": ["report_id"],
        },
    },
]


async def create_report(vehicle_id: str, db: AsyncSession) -> dict:
    try:
        vid = uuid.UUID(vehicle_id)
    except ValueError:
        return {"error": f"Invalid vehicle_id: {vehicle_id}"}

    result = await db.execute(select(Vehicle).where(Vehicle.id == vid))
    vehicle = result.scalar_one_or_none()
    if not vehicle:
        return {"error": f"Vehicle {vehicle_id} not found"}

    report = Report(
        session_id=None,
        vehicle_id=vid,
        status="draft",
        findings=[],
        estimate={"line_items": []},
        estimate_total=0,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return {"report_id": str(report.id)}


async def add_report_item(
    report_id: str,
    part: str,
    labor_hours: float,
    labor_rate: float,
    parts_cost: float,
    db: AsyncSession,
) -> dict:
    try:
        rid = uuid.UUID(report_id)
    except ValueError:
        return {"error": f"Invalid report_id: {report_id}"}

    result = await db.execute(select(Report).where(Report.id == rid))
    report = result.scalar_one_or_none()
    if not report:
        return {"error": f"Report {report_id} not found"}

    estimate_data = dict(report.estimate or {"line_items": []})
    line_items = list(estimate_data.get("line_items") or [])

    item = {
        "part": part,
        "labor_hours": labor_hours,
        "labor_rate": labor_rate,
        "labor_cost": round(labor_hours * labor_rate, 2),
        "parts_cost": parts_cost,
        "total": round(labor_hours * labor_rate + parts_cost, 2),
    }
    line_items.append(item)
    estimate_data["line_items"] = line_items
    new_total = round(sum(i["total"] for i in line_items), 2)

    await db.execute(
        sa_update(Report)
        .where(Report.id == rid)
        .values(estimate=estimate_data, estimate_total=new_total)
    )
    await db.commit()

    return {
        "report_id": report_id,
        "line_items": line_items,
        "total": new_total,
    }


async def list_report_items(report_id: str, db: AsyncSession) -> dict:
    try:
        rid = uuid.UUID(report_id)
    except ValueError:
        return {"error": f"Invalid report_id: {report_id}"}

    result = await db.execute(select(Report).where(Report.id == rid))
    report = result.scalar_one_or_none()
    if not report:
        return {"error": f"Report {report_id} not found"}

    estimate = report.estimate or {"line_items": []}
    line_items = list(estimate.get("line_items") or [])
    total = float(report.estimate_total) if report.estimate_total is not None else 0.0

    return {
        "report_id": report_id,
        "line_items": line_items,
        "total": total,
    }
