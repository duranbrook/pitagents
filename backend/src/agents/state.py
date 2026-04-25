import operator
from typing import Annotated, TypedDict


class AgentState(TypedDict):
    messages: Annotated[list[dict], operator.add]
    tool_calls_log: Annotated[list[dict], operator.add]
    stop_reason: str
