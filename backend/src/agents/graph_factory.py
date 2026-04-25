"""Factory that builds a LangGraph ReAct loop for any chat agent."""

import asyncio
import json
from typing import Callable, Awaitable, Any

import anthropic
from langgraph.graph import StateGraph, END
from langgraph.types import RunnableConfig, StreamWriter

from src.agents.state import AgentState
from src.config import settings

_anthropic_client = anthropic.AsyncAnthropic(
    api_key=settings.ANTHROPIC_API_KEY.get_secret_value()
)

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 4096

ToolExecutor = Callable[[str, dict, Any], Awaitable[dict]]


def build_react_graph(
    system_prompt: str,
    tool_schemas: list[dict],
    tool_executor: ToolExecutor | None,
):
    """Return a compiled LangGraph ReAct agent.

    Streams custom events via StreamWriter:
      {"type": "token",      "content": str}
      {"type": "tool_start", "tool": str, "input": dict}
      {"type": "tool_end",   "tool": str, "output": dict}
      {"type": "done",       "tool_calls": list, "_messages": list}

    tool_executor signature: async (name, input_dict, db) -> dict
    db is taken from config["configurable"]["db"] at call time.
    """

    async def call_llm(
        state: AgentState,
        writer: StreamWriter,
        config: RunnableConfig,
    ) -> dict:
        kwargs: dict = dict(
            model=MODEL,
            system=system_prompt,
            max_tokens=MAX_TOKENS,
            messages=list(state["messages"]),
        )
        if tool_schemas:
            kwargs["tools"] = tool_schemas

        for attempt in range(3):
            try:
                async with _anthropic_client.messages.stream(**kwargs) as stream:
                    async for text in stream.text_stream:
                        writer({"type": "token", "content": text})
                    final = await stream.get_final_message()
                break
            except anthropic.APIStatusError as exc:
                if exc.status_code == 529 and attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise

        assistant_content = []
        for block in final.content:
            if block.type == "text":
                assistant_content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                assistant_content.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })

        new_msg = {"role": "assistant", "content": assistant_content}

        if final.stop_reason != "tool_use":
            all_messages = list(state["messages"]) + [new_msg]
            writer({
                "type": "done",
                "tool_calls": list(state["tool_calls_log"]),
                "_messages": all_messages,
            })

        return {"messages": [new_msg], "stop_reason": final.stop_reason}

    async def execute_tools(
        state: AgentState,
        writer: StreamWriter,
        config: RunnableConfig,
    ) -> dict:
        db = config.get("configurable", {}).get("db")
        last_msg = state["messages"][-1]
        blocks = last_msg.get("content", [])

        tool_uses = [b for b in blocks if b.get("type") == "tool_use"]
        if not tool_uses:
            return {"messages": [], "tool_calls_log": []}

        tool_results = []
        new_log_entries = []

        for tu in tool_uses:
            name, inp, tu_id = tu["name"], tu["input"], tu["id"]
            writer({"type": "tool_start", "tool": name, "input": inp})
            output = await tool_executor(name, inp, db)
            writer({"type": "tool_end", "tool": name, "output": output})
            new_log_entries.append({"name": name, "input": inp, "output": output})
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tu_id,
                "content": json.dumps(output),
            })

        tool_results_msg = {"role": "user", "content": tool_results}
        return {
            "messages": [tool_results_msg],
            "tool_calls_log": new_log_entries,
        }

    def should_continue(state: AgentState) -> str:
        return "execute_tools" if state.get("stop_reason") == "tool_use" else END

    builder = StateGraph(AgentState)
    builder.add_node("call_llm", call_llm)
    builder.add_node("execute_tools", execute_tools)
    builder.set_entry_point("call_llm")
    builder.add_conditional_edges("call_llm", should_continue)
    builder.add_edge("execute_tools", "call_llm")

    return builder.compile()
