from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.graph_factory import build_react_graph
from src.agents.tools.shop_tools import (
    SHOP_TOOL_SCHEMAS,
    list_sessions,
    get_session_detail,
    get_report,
)
from src.agents.prompts.tom_blocks import TOM_BLOCKS

_PROMPT = (Path(__file__).parent / "prompts" / "tom.txt").read_text()


async def _execute_tool(name: str, inp: dict, db: AsyncSession) -> dict:
    if name == "list_sessions":
        return await list_sessions(db, limit=inp.get("limit", 10))
    if name == "get_session_detail":
        return await get_session_detail(db, inp["session_id"])
    if name == "get_report":
        return await get_report(db, inp["session_id"])
    return {"error": f"Unknown tool: {name}"}


tom_graph = build_react_graph(
    system_prompt=_PROMPT,
    tool_schemas=SHOP_TOOL_SCHEMAS,
    tool_executor=_execute_tool,
    intent_labels=list(TOM_BLOCKS.keys()),
    prompt_blocks=TOM_BLOCKS,
)
