"""
End-to-end smoke test: full inspection flow through the FastAPI app.
Uses in-memory stores (no real DB/S3/Deepgram/Claude).
"""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock, patch
from src.api.main import app
from src.api.auth import create_access_token

@pytest.mark.asyncio
async def test_full_inspection_flow():
    token = create_access_token({"sub": "owner-1", "role": "owner"})
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Create session
        resp = await ac.post("/sessions", json={
            "shop_id": "shop-1",
            "labor_rate": 120.0,
            "pricing_flag": "shop"
        }, headers=headers)
        assert resp.status_code == 200
        session_id = resp.json()["session_id"]

        # 2. Upload audio
        with patch("src.api.sessions.StorageService") as MockStorage:
            MockStorage.return_value.upload = AsyncMock(return_value="bucket/audio.mp3")
            resp = await ac.post(
                f"/sessions/{session_id}/media",
                data={"media_type": "audio", "tag": "general"},
                files={"file": ("audio.mp3", b"fake-audio", "audio/mpeg")},
                headers=headers
            )
        assert resp.status_code == 200

        # 3. Trigger agent (mocked)
        with patch("src.api.sessions.run_inspection_agent", new_callable=AsyncMock) as mock_agent:
            mock_agent.return_value = {
                "status": "complete",
                "transcript": "replace front brakes",
                "vehicle": {"year": "2019", "make": "Honda", "model": "Civic"},
                "findings": {"summary": "Brakes worn.", "findings": []},
                "estimate": {"line_items": [], "total": 240.0},
            }
            resp = await ac.post(f"/sessions/{session_id}/generate", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "processing"

        # 4. Get session
        resp = await ac.get(f"/sessions/{session_id}", headers=headers)
        assert resp.status_code == 200
        assert "session_id" in resp.json()
