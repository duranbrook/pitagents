from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.graph_factory import build_react_graph
from src.agents.tools.shop_tools import (
    SHOP_TOOL_SCHEMAS,
    list_sessions, get_session_detail, get_report,
    lookup_customer, get_customer_vehicles, find_sessions_by_vehicle,
)
from src.agents.prompts.tom_blocks import TOM_BLOCKS

_FALLBACK_PROMPT = (Path(__file__).parent / "prompts" / "tom.txt").read_text()

INTENT_LABELS = [
    "ANALYTICS_SESSIONS", "ANALYTICS_REVENUE", "ANALYTICS_TECHNICIAN", "GENERAL",
]


async def _execute_tool(name: str, inp: dict, db: AsyncSession) -> dict:
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


tom_graph = build_react_graph(
    system_prompt=_FALLBACK_PROMPT,
    tool_schemas=SHOP_TOOL_SCHEMAS,
    tool_executor=_execute_tool,
    intent_labels=INTENT_LABELS,
    prompt_blocks=TOM_BLOCKS,
)
