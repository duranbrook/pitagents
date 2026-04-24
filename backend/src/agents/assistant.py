from pathlib import Path
from collections.abc import AsyncGenerator
from src.agents.base import stream_response
from src.agents.tools.vin_tools import VIN_TOOL_SCHEMAS, lookup_vin, extract_vin_from_image

_PROMPT = (Path(__file__).parent / "prompts" / "assistant.txt").read_text()

async def _tool_executor(name: str, inp: dict) -> dict:
    if name == "lookup_vin":
        return await lookup_vin(inp["vin"])
    if name == "extract_vin_from_image":
        return await extract_vin_from_image(inp["image_url"])
    return {"error": f"Unknown tool: {name}"}


async def stream_assistant(
    history: list[dict],
    user_content: list[dict],
) -> AsyncGenerator[dict, None]:
    async for event in stream_response(
        system_prompt=_PROMPT,
        tool_schemas=VIN_TOOL_SCHEMAS,
        tool_executor=_tool_executor,
        history=history,
        user_content=user_content,
    ):
        yield event
