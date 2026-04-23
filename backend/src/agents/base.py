"""Shared streaming loop for all chat agents."""
import json
from collections.abc import AsyncGenerator
from typing import Callable, Awaitable
import anthropic
from src.config import settings

_anthropic_client = anthropic.AsyncAnthropic(
    api_key=settings.ANTHROPIC_API_KEY.get_secret_value()
)

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 4096


async def stream_response(
    system_prompt: str,
    tool_schemas: list[dict],
    tool_executor: Callable[[str, dict], Awaitable[dict]] | None,
    history: list[dict],
    user_content: list[dict],
) -> AsyncGenerator[dict, None]:
    """Stream an agent response, handling tool calls in a loop.

    Yields dicts:
      {"type": "token", "content": str}
      {"type": "tool_start", "tool": str, "input": dict}
      {"type": "tool_end", "tool": str, "output": dict}
      {"type": "done", "tool_calls": list[dict], "_messages": list[dict]}
    """
    messages = list(history) + [{"role": "user", "content": user_content}]
    tool_calls_log: list[dict] = []
    create_kwargs: dict = dict(
        model=MODEL,
        system=system_prompt,
        max_tokens=MAX_TOKENS,
        messages=messages,
    )
    if tool_schemas:
        create_kwargs["tools"] = tool_schemas

    while True:
        async with _anthropic_client.messages.stream(**create_kwargs) as stream:
            async for text in stream.text_stream:
                yield {"type": "token", "content": text}
            final = await stream.get_final_message()

        assistant_content = [b.model_dump() for b in final.content]
        messages.append({"role": "assistant", "content": assistant_content})

        tool_uses = [b for b in final.content if b.type == "tool_use"]
        if not tool_uses or tool_executor is None:
            break

        tool_results = []
        for tu in tool_uses:
            yield {"type": "tool_start", "tool": tu.name, "input": tu.input}
            output = await tool_executor(tu.name, tu.input)
            yield {"type": "tool_end", "tool": tu.name, "output": output}
            tool_calls_log.append({"name": tu.name, "input": tu.input, "output": output})
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tu.id,
                "content": json.dumps(output),
            })

        messages.append({"role": "user", "content": tool_results})
        create_kwargs["messages"] = messages

    yield {"type": "done", "tool_calls": tool_calls_log, "_messages": messages}
