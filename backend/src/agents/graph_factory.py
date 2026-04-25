"""Factory that builds a LangGraph ReAct loop for any chat agent."""
import asyncio
import json
from typing import Callable, Awaitable, Any

import anthropic
from langgraph.graph import StateGraph, END
from langgraph.types import RunnableConfig, StreamWriter

from src.agents.state import AgentState
import src.agents.llm as _llm
from src.agents.llm import MODEL, MAX_TOKENS
from src.agents.nodes.classify_intent import make_classify_intent_node
from src.agents.nodes.assemble_prompt import make_assemble_prompt_node
from src.agents.nodes.validate_response import make_validate_response_node

ToolExecutor = Callable[[str, dict, Any], Awaitable[dict]]


def build_react_graph(
    system_prompt: str,
    tool_schemas: list[dict],
    tool_executor: ToolExecutor | None,
    intent_labels: list[str],
    prompt_blocks: dict[str, str],
):
    """Return a compiled LangGraph ReAct agent.

    Graph nodes: classify_intent → assemble_prompt → call_llm ↔ execute_tools → validate_response

    system_prompt: fallback used by call_llm when assembled_prompt is empty
    intent_labels: label set for this agent
    prompt_blocks: {"base": "...", "<LABEL>": "..."} blocks assembled per intent
    """

    async def call_llm(
        state: AgentState,
        writer: StreamWriter,
        config: RunnableConfig,
    ) -> dict:
        system = state.get("assembled_prompt") or system_prompt
        kwargs: dict = dict(
            model=MODEL,
            system=system,
            max_tokens=MAX_TOKENS,
            messages=list(state["messages"]),
        )
        if tool_schemas:
            kwargs["tools"] = tool_schemas

        for attempt in range(3):
            try:
                async with _llm.client.messages.stream(**kwargs) as stream:
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
        # done event is emitted by validate_response, not here
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
        return "execute_tools" if state.get("stop_reason") == "tool_use" else "validate_response"

    classify_intent = make_classify_intent_node(intent_labels)
    assemble_prompt = make_assemble_prompt_node(prompt_blocks)
    validate_response = make_validate_response_node(system_prompt, tool_schemas)

    builder = StateGraph(AgentState)
    builder.add_node("classify_intent", classify_intent)
    builder.add_node("assemble_prompt", assemble_prompt)
    builder.add_node("call_llm", call_llm)
    builder.add_node("execute_tools", execute_tools)
    builder.add_node("validate_response", validate_response)
    builder.set_entry_point("classify_intent")
    builder.add_edge("classify_intent", "assemble_prompt")
    builder.add_edge("assemble_prompt", "call_llm")
    builder.add_conditional_edges("call_llm", should_continue)
    builder.add_edge("execute_tools", "call_llm")
    builder.add_edge("validate_response", END)

    return builder.compile()
