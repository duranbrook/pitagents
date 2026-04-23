from pathlib import Path
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from src.agents.base import stream_response
from src.agents.tools.shop_tools import (
    SHOP_TOOL_SCHEMAS,
    list_sessions,
    get_session_detail,
    get_report,
)

_PROMPT = (Path(__file__).parent / "prompts" / "tom.txt").read_text()


async def stream_tom(
    history: list[dict],
    user_content: list[dict],
    db: AsyncSession,
) -> AsyncGenerator[dict, None]:
    async def _tool_executor(name: str, inp: dict) -> dict:
        if name == "list_sessions":
            return await list_sessions(db, limit=inp.get("limit", 10))
        if name == "get_session_detail":
            return await get_session_detail(db, inp["session_id"])
        if name == "get_report":
            return await get_report(db, inp["session_id"])
        return {"error": f"Unknown tool: {name}"}

    async for event in stream_response(
        system_prompt=_PROMPT,
        tool_schemas=SHOP_TOOL_SCHEMAS,
        tool_executor=_tool_executor,
        history=history,
        user_content=user_content,
    ):
        yield event
