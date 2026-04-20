"""Tests for the LangGraph inspection agent orchestrator."""

import pytest
from unittest.mock import AsyncMock, patch

SESSION = {
    "session_id": "test-123",
    "audio_url": "https://s3/test/audio.mp3",
    "video_url": "https://s3/test/video.mp4",
    "video_frame_urls": ["https://s3/test/frame1.jpg"],
    "labor_rate": 120.0,
    "pricing_flag": "shop",
}

MOCK_VIN = "1HGBH41JXMN109186"
MOCK_VEHICLE = {
    "vin": MOCK_VIN,
    "year": "2021",
    "make": "Honda",
    "model": "Civic",
    "trim": "LX",
}
MOCK_FINDINGS = {
    "summary": "Front brakes worn.",
    "findings": [{"part": "brake pads", "severity": "high", "notes": "worn"}],
}
MOCK_ESTIMATE = {"line_items": [{"part": "brake pads", "line_total": 240.0}], "total": 240.0, "currency": "USD"}


@pytest.mark.asyncio
async def test_agent_produces_report():
    """Agent runs all steps and produces a complete report."""
    with (
        patch("src.agent.graph.extract_audio_transcript", new=AsyncMock(return_value="replace front brakes")),
        patch("src.agent.graph.extract_repair_findings", new=AsyncMock(return_value=MOCK_FINDINGS)),
        patch("src.agent.graph.extract_vin_from_frames", new=AsyncMock(return_value=MOCK_VIN)),
        patch("src.agent.graph.read_odometer", new=AsyncMock(return_value=45000)),
        patch("src.agent.graph.read_tire_size", new=AsyncMock(return_value="225/55R17")),
        patch("src.agent.graph.analyze_damage", new=AsyncMock(return_value=["scratch on door"])),
        patch("src.agent.graph.lookup_vehicle_by_vin", new=AsyncMock(return_value=MOCK_VEHICLE)),
        patch("src.agent.graph.generate_estimate", new=AsyncMock(return_value=MOCK_ESTIMATE)),
    ):
        from src.agent.graph import run_inspection_agent

        result = await run_inspection_agent(SESSION)

    assert result["status"] == "complete"
    assert result["vehicle"]["vin"] == MOCK_VIN
    assert result["transcript"] == "replace front brakes"
    assert result["estimate"]["total"] == 240.0


@pytest.mark.asyncio
async def test_agent_no_audio_url():
    """Agent handles missing audio_url by setting empty transcript."""
    session = {**SESSION, "audio_url": None}

    with (
        patch("src.agent.graph.extract_audio_transcript", new=AsyncMock(return_value="")),
        patch("src.agent.graph.extract_repair_findings", new=AsyncMock(return_value={"summary": "", "findings": []})),
        patch("src.agent.graph.extract_vin_from_frames", new=AsyncMock(return_value="")),
        patch("src.agent.graph.read_odometer", new=AsyncMock(return_value=None)),
        patch("src.agent.graph.read_tire_size", new=AsyncMock(return_value="")),
        patch("src.agent.graph.analyze_damage", new=AsyncMock(return_value=[])),
        patch("src.agent.graph.lookup_vehicle_by_vin", new=AsyncMock(return_value={})),
        patch("src.agent.graph.generate_estimate", new=AsyncMock(return_value={"line_items": [], "total": 0.0})),
    ):
        from src.agent.graph import run_inspection_agent

        result = await run_inspection_agent(session)

    assert result["status"] == "complete"
    assert result["transcript"] == ""


@pytest.mark.asyncio
async def test_agent_no_video_frames():
    """Agent handles missing video_frame_urls gracefully."""
    session = {**SESSION, "video_frame_urls": []}

    with (
        patch("src.agent.graph.extract_audio_transcript", new=AsyncMock(return_value="oil change needed")),
        patch("src.agent.graph.extract_repair_findings", new=AsyncMock(return_value={"summary": "oil change", "findings": [{"part": "oil", "severity": "low", "notes": "due"}]})),
        patch("src.agent.graph.extract_vin_from_frames", new=AsyncMock(return_value="")),
        patch("src.agent.graph.read_odometer", new=AsyncMock(return_value=None)),
        patch("src.agent.graph.read_tire_size", new=AsyncMock(return_value="")),
        patch("src.agent.graph.analyze_damage", new=AsyncMock(return_value=[])),
        patch("src.agent.graph.lookup_vehicle_by_vin", new=AsyncMock(return_value={})),
        patch("src.agent.graph.generate_estimate", new=AsyncMock(return_value={"line_items": [{"part": "oil", "line_total": 60.0}], "total": 60.0})),
    ):
        from src.agent.graph import run_inspection_agent

        result = await run_inspection_agent(session)

    assert result["status"] == "complete"
    assert result["vehicle"] == {}
