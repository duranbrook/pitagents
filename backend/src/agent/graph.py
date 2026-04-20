"""LangGraph inspection agent orchestrator.

Linear flow:
    transcribe → vision → extract_findings → estimate → finalize → END

All tool imports are at module level so tests can patch them at src.agent.graph.*
"""

from __future__ import annotations

import asyncio

from langgraph.graph import StateGraph, END

from src.agent.state import AgentState

# Tool imports — patched in tests via src.agent.graph.*
from src.tools.transcribe import extract_audio_transcript
from src.tools.extract_findings import extract_repair_findings
from src.tools.vision import (
    extract_vin_from_frames,
    read_odometer,
    read_tire_size,
    analyze_damage,
)
from src.tools.vin_lookup import lookup_vehicle_by_vin
from src.tools.estimate import generate_estimate


# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------

async def _transcribe_node(state: AgentState) -> dict:
    """Transcribe audio if audio_url is present, else use empty string."""
    audio_url = state.get("audio_url")
    if audio_url:
        transcript = await extract_audio_transcript(audio_url)
    else:
        transcript = ""
    return {"transcript": transcript}


async def _vision_node(state: AgentState) -> dict:
    """Run all 4 vision tools in parallel, then look up vehicle by VIN."""
    frame_urls: list[str] = state.get("video_frame_urls") or []

    vin, mileage, tire_size, damage_notes = await asyncio.gather(
        extract_vin_from_frames(frame_urls),
        read_odometer(frame_urls),
        read_tire_size(frame_urls),
        analyze_damage(frame_urls),
    )

    vehicle: dict = {}
    if vin and len(vin) == 17:
        vehicle = await lookup_vehicle_by_vin(vin)

    return {
        "vehicle": vehicle,
        "mileage": mileage,
        "tire_size": tire_size,
        "damage_notes": damage_notes if damage_notes else [],
    }


async def _extract_findings_node(state: AgentState) -> dict:
    """Extract structured repair findings from the transcript."""
    transcript: str = state.get("transcript") or ""
    findings = await extract_repair_findings(transcript)
    return {"findings": findings}


async def _estimate_node(state: AgentState) -> dict:
    """Generate repair cost estimate from findings and vehicle data."""
    findings_dict: dict = state.get("findings") or {}
    findings_list: list = findings_dict.get("findings", [])

    if not findings_list:
        return {"estimate": {"line_items": [], "total": 0.0}}

    vehicle: dict = state.get("vehicle") or {}
    labor_rate: float = state.get("labor_rate", 100.0)
    pricing_flag: str = state.get("pricing_flag", "shop")
    alldata_api_key = state.get("alldata_api_key")

    estimate = await generate_estimate(
        vehicle=vehicle,
        findings=findings_list,
        labor_rate=labor_rate,
        pricing_flag=pricing_flag,
        alldata_api_key=alldata_api_key,
    )
    return {"estimate": estimate}


async def _finalize_node(state: AgentState) -> dict:
    """Mark the inspection session as complete."""
    return {"status": "complete"}


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def _build_graph() -> StateGraph:
    builder = StateGraph(AgentState)

    # Node names must not clash with AgentState field names.
    # "transcript", "findings", "vehicle", "mileage", "tire_size",
    # "damage_notes", "estimate", "status", "error" are all reserved.
    builder.add_node("step_transcribe", _transcribe_node)
    builder.add_node("step_vision", _vision_node)
    builder.add_node("step_findings", _extract_findings_node)
    builder.add_node("step_estimate", _estimate_node)
    builder.add_node("step_finalize", _finalize_node)

    builder.set_entry_point("step_transcribe")
    builder.add_edge("step_transcribe", "step_vision")
    builder.add_edge("step_vision", "step_findings")
    builder.add_edge("step_findings", "step_estimate")
    builder.add_edge("step_estimate", "step_finalize")
    builder.add_edge("step_finalize", END)

    return builder.compile()


_graph = _build_graph()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def run_inspection_agent(session_input: dict) -> AgentState:
    """Run the full inspection agent pipeline for a given session.

    Executes the graph nodes sequentially as plain async calls.  The
    LangGraph StateGraph (_graph) defines the graph structure and is
    available for introspection; execution is done directly to avoid a
    known incompatibility between langchain 1.2.x and langchain-core
    0.3.x that causes ainvoke() to raise AttributeError on `langchain.debug`.

    Args:
        session_input: dict matching AgentState fields.

    Returns:
        Final AgentState with status == "complete" on success.
    """
    state: AgentState = {
        "session_id": session_input.get("session_id", ""),
        "audio_url": session_input.get("audio_url"),
        "video_url": session_input.get("video_url"),
        "video_frame_urls": session_input.get("video_frame_urls", []),
        "labor_rate": session_input.get("labor_rate", 100.0),
        "pricing_flag": session_input.get("pricing_flag", "shop"),
        "alldata_api_key": session_input.get("alldata_api_key"),
        # Initial output values
        "transcript": None,
        "findings": None,
        "vehicle": None,
        "mileage": None,
        "tire_size": None,
        "damage_notes": [],
        "estimate": None,
        "status": "pending",
        "error": None,
    }

    # Execute nodes in linear order: same topology as the compiled graph.
    for node_fn in (
        _transcribe_node,
        _vision_node,
        _extract_findings_node,
        _estimate_node,
        _finalize_node,
    ):
        updates = await node_fn(state)
        state = {**state, **updates}  # type: ignore[assignment]

    return state
