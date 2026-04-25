import operator
from typing import Annotated, TypedDict


class AgentState(TypedDict):
    messages: Annotated[list[dict], operator.add]
    tool_calls_log: Annotated[list[dict], operator.add]
    stop_reason: str
    intent: str           # set by classify_intent node
    assembled_prompt: str # set by assemble_prompt node
