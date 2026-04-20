"""Estimate generation tool with pricing flag support."""

from __future__ import annotations

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
    """Return estimated labor hours for a given part name.

    Checks the lowercase part name against each keyword in DEFAULT_LABOR_HOURS.
    Returns the matching hours, or 1.0 if no keyword matches.
    """
    lower = part_name.lower()
    for keyword, hours in DEFAULT_LABOR_HOURS.items():
        if keyword in lower:
            return hours
    return 1.0


async def fetch_alldata_estimate(vehicle: dict, findings: list, api_key: str) -> dict:
    """Fetch pricing estimate from the ALLDATA API.

    Raises:
        NotImplementedError: ALLDATA API is not yet provisioned.
    """
    raise NotImplementedError("ALLDATA API not yet provisioned")


async def generate_estimate(
    vehicle: dict,
    findings: list,
    labor_rate: float,
    pricing_flag: str,
    alldata_api_key: str | None = None,
) -> dict:
    """Generate a repair cost estimate.

    If pricing_flag is "alldata" and alldata_api_key is provided, delegates to
    fetch_alldata_estimate. Otherwise builds line items using shop labor pricing.

    Returns:
        dict with keys: line_items (list), total (float), currency (str "USD").
        When using the alldata path the return value is whatever fetch_alldata_estimate
        returns (caller-supplied in tests; real implementation would include currency).
    """
    if pricing_flag == "alldata" and alldata_api_key:
        return await fetch_alldata_estimate(vehicle, findings, alldata_api_key)

    # Shop pricing path
    line_items: list[dict] = []
    for finding in findings:
        part = finding.get("part", "")
        severity = finding.get("severity", "")
        labor_hrs = _estimate_labor_hours(part)
        labor_cost = round(labor_hrs * labor_rate, 2)
        parts_cost = 0.0
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
