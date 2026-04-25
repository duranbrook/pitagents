from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.graph_factory import build_react_graph
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

_PROMPT = (Path(__file__).parent / "prompts" / "assistant.txt").read_text()

_TOOL_SCHEMAS = VIN_TOOL_SCHEMAS + QUOTE_TOOL_SCHEMAS


async def _execute_tool(name: str, inp: dict, db: AsyncSession) -> dict:
    if name == "lookup_vin":
        return await lookup_vin(inp["vin"])
    if name == "extract_vin_from_image":
        return await extract_vin_from_image(inp["image_url"])
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


assistant_graph = build_react_graph(
    system_prompt=_PROMPT,
    tool_schemas=_TOOL_SCHEMAS,
    tool_executor=_execute_tool,
)
