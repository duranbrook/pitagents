import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.tools.frames import extract_frames


@pytest.mark.asyncio
async def test_extract_frames_no_video_url():
    """When URL download fails (httpx raises), extract_frames propagates the error."""
    with patch("src.tools.frames.httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=Exception("network error")
        )
        with pytest.raises(Exception, match="network error"):
            await extract_frames("https://bad-url/video.mp4", "session-1")


@pytest.mark.asyncio
async def test_extract_frames_returns_empty_when_no_frames():
    """When ffmpeg produces no .jpg files, return empty list."""
    with patch("src.tools.frames.httpx.AsyncClient") as MockClient, \
         patch("src.tools.frames.subprocess.run") as mock_run, \
         patch("src.tools.frames.StorageService"):
        # Mock video download
        mock_resp = MagicMock()
        mock_resp.content = b"fake-video-bytes"
        MockClient.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)
        mock_run.return_value = MagicMock(returncode=0)

        result = await extract_frames("https://s3/video.mp4", "session-1")

    assert result == []
