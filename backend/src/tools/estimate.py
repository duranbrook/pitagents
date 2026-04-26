"""Estimate generation with Qdrant parts pricing lookup."""

from __future__ import annotations

from src.db.qdrant import qdrant, embed

DEFAULT_LABOR_HOURS: dict[str, float] = {
    "brake pads": 2.0,
    "cv axle": 2.5,
    "cv boot": 1.5,
    "air filter": 0.5,
    "oil change": 0.5,
    "tire rotation": 0.5,
    "battery": 0.5,
    "alternator": 2.0,
    "starter": 2.5,
    "water pump": 3.5,
}


def _estimate_labor_hours(part_name: str) -> float:
    lower = part_name.lower()
    for keyword, hours in DEFAULT_LABOR_HOURS.items():
        if keyword in lower:
            return hours
    return 1.0


async def _lookup_parts_price(part_name: str) -> float:
    """Search Qdrant 'parts' collection for a price estimate.

    Returns the unit_price from the closest matching part, or 0.0 if the
    collection is empty or the search fails.
    """
    try:
        vector = await embed(part_name)
        results = await qdrant.search(
            collection_name="parts",
            query_vector=vector,
            limit=1,
            with_payload=True,
        )
        if results:
            return float(results[0].payload.get("unit_price", 0.0))
    except Exception:
        pass
    return 0.0


async def fetch_alldata_estimate(vehicle: dict, findings: list, api_key: str) -> dict:
    raise NotImplementedError("ALLDATA API not yet provisioned")


async def generate_estimate(
    vehicle: dict,
    findings: list,
    labor_rate: float,
    pricing_flag: str,
    alldata_api_key: str | None = None,
) -> dict:
    """Generate a repair cost estimate.

    Parts costs are looked up via Qdrant semantic search against the ingested
    parts catalog. Falls back to 0.0 if the catalog is empty.
    """
    if pricing_flag == "alldata" and alldata_api_key:
        return await fetch_alldata_estimate(vehicle, findings, alldata_api_key)

    line_items: list[dict] = []
    for finding in findings:
        part = finding.get("part", "")
        severity = finding.get("severity", "")
        labor_hrs = _estimate_labor_hours(part)
        labor_cost = round(labor_hrs * labor_rate, 2)
        parts_cost = await _lookup_parts_price(part)
        line_total = round(labor_cost + parts_cost, 2)
        line_items.append(
            {
                "part": part,
                "severity": severity,
                "labor_hrs": labor_hrs,
                "labor_cost": labor_cost,
                "parts_cost": parts_cost,
                "line_total": line_total,
            }
        )

    total = round(sum(item["line_total"] for item in line_items), 2)
    return {"line_items": line_items, "total": total, "currency": "USD"}
