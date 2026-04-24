from pathlib import Path
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from src.agents.base import stream_response
from src.agents.tools.quote_tools import (
    QUOTE_TOOL_SCHEMAS,
    lookup_part_price,
    estimate_labor,
    create_quote,
    create_quote_item,
    list_quote_items,
    finalize_quote,
)

_PROMPT = (Path(__file__).parent / "prompts" / "quote_agent.txt").read_text()


async def stream_quote(
    history: list[dict],
    user_content: list[dict],
    db: AsyncSession,
) -> AsyncGenerator[dict, None]:
    """Stream quote agent responses with tool execution."""

    async def _tool_executor(name: str, inp: dict) -> dict:
        if name == "lookup_part_price":
            return await lookup_part_price(inp["part_name"])
        elif name == "estimate_labor":
            return await estimate_labor(inp["task_name"], inp["hours"], db)
        elif name == "create_quote":
            return await create_quote(db, inp.get("session_id"))
        elif name == "create_quote_item":
            return await create_quote_item(
                inp["quote_id"], inp["item_type"], inp["description"],
                inp["qty"], inp["unit_price"], db
            )
        elif name == "list_quote_items":
            return await list_quote_items(inp["quote_id"], db)
        elif name == "finalize_quote":
            return await finalize_quote(inp["quote_id"], db)
        return {"error": f"Unknown tool: {name}"}

    async for event in stream_response(
        system_prompt=_PROMPT,
        tool_schemas=QUOTE_TOOL_SCHEMAS,
        tool_executor=_tool_executor,
        history=history,
        user_content=user_content,
    ):
        yield event
