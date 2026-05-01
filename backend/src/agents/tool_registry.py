"""
Static registry of all tool bundles available to shop agents.
Each entry maps tool_id -> metadata + LangGraph integration.
Tool IDs are stored in ShopAgent.tools (list[str]).
"""
from src.agents.tools.vin_tools import VIN_TOOL_SCHEMAS, lookup_vin, extract_vin_from_image
from src.agents.tools.quote_tools import (
    QUOTE_TOOL_SCHEMAS,
    lookup_part_price,
    estimate_labor,
    create_quote,
    create_quote_item,
    list_quote_items,
    finalize_quote,
)
from src.agents.tools.parts_tools import PARTS_TOOL_SCHEMAS, semantic_parts_search
from src.agents.tools.shop_tools import (
    SHOP_TOOL_SCHEMAS,
    list_sessions,
    get_session_detail,
    get_report,
    lookup_customer,
    get_customer_vehicles,
    find_sessions_by_vehicle,
)
from sqlalchemy.ext.asyncio import AsyncSession


async def _exec_vin(name: str, inp: dict, db: AsyncSession) -> dict:
    if name == "lookup_vin":
        return await lookup_vin(inp["vin"])
    if name == "extract_vin_from_image":
        return await extract_vin_from_image(inp["image_url"])
    return {"error": f"Unknown tool: {name}"}


async def _exec_quote(name: str, inp: dict, db: AsyncSession) -> dict:
    if name == "lookup_part_price":
        return await lookup_part_price(inp["part_name"])
    if name == "estimate_labor":
        return await estimate_labor(inp["task_name"], inp["hours"], db)
    if name == "create_quote":
        return await create_quote(db, inp.get("session_id"))
    if name == "create_quote_item":
        return await create_quote_item(
            inp["quote_id"], inp["item_type"], inp["description"],
            inp["qty"], inp["unit_price"], db,
        )
    if name == "list_quote_items":
        return await list_quote_items(inp["quote_id"], db)
    if name == "finalize_quote":
        return await finalize_quote(inp["quote_id"], db)
    return {"error": f"Unknown tool: {name}"}


async def _exec_parts(name: str, inp: dict, db: AsyncSession) -> dict:
    if name == "semantic_parts_search":
        return await semantic_parts_search(inp["query"], inp.get("make"), inp.get("top_k", 3))
    return {"error": f"Unknown tool: {name}"}


async def _exec_shop(name: str, inp: dict, db: AsyncSession) -> dict:
    if name == "list_sessions":
        return await list_sessions(db, limit=inp.get("limit", 10))
    if name == "get_session_detail":
        return await get_session_detail(db, inp["session_id"])
    if name == "get_report":
        return await get_report(db, inp["session_id"])
    if name == "lookup_customer":
        return await lookup_customer(db, inp["name"])
    if name == "get_customer_vehicles":
        return await get_customer_vehicles(db, inp["customer_id"])
    if name == "find_sessions_by_vehicle":
        return await find_sessions_by_vehicle(db, inp["vehicle_id"])
    return {"error": f"Unknown tool: {name}"}


TOOL_REGISTRY: dict[str, dict] = {
    "vin_lookup": {
        "label": "VIN Lookup",
        "description": "Identify any vehicle by VIN number or image",
        "schemas": VIN_TOOL_SCHEMAS,
        "executor": _exec_vin,
        "tool_names": {"lookup_vin", "extract_vin_from_image"},
    },
    "quote_builder": {
        "label": "Quotes & Estimates",
        "description": "Build and finalize repair cost estimates",
        "schemas": QUOTE_TOOL_SCHEMAS,
        "executor": _exec_quote,
        "tool_names": {
            "lookup_part_price", "estimate_labor", "create_quote",
            "create_quote_item", "list_quote_items", "finalize_quote",
        },
    },
    "parts_search": {
        "label": "Parts Search",
        "description": "Search the parts catalog by name or OEM code",
        "schemas": PARTS_TOOL_SCHEMAS,
        "executor": _exec_parts,
        "tool_names": {"semantic_parts_search"},
    },
    "shop_data": {
        "label": "Customer & Vehicle Records",
        "description": "Look up customers, vehicles, sessions, and reports",
        "schemas": SHOP_TOOL_SCHEMAS,
        "executor": _exec_shop,
        "tool_names": {
            "list_sessions", "get_session_detail", "get_report",
            "lookup_customer", "get_customer_vehicles", "find_sessions_by_vehicle",
        },
    },
}


def build_tool_schemas_and_executor(tool_ids: list[str]):
    """Return (combined_schemas, combined_executor) for a list of tool IDs."""
    schemas: list[dict] = []
    bundles = [TOOL_REGISTRY[tid] for tid in tool_ids if tid in TOOL_REGISTRY]
    for bundle in bundles:
        schemas.extend(bundle["schemas"])

    async def executor(name: str, inp: dict, db) -> dict:
        for bundle in bundles:
            if name in bundle["tool_names"]:
                return await bundle["executor"](name, inp, db)
        return {"error": f"Unknown tool: {name}"}

    return schemas, executor
