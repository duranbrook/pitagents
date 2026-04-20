import asyncio
import json
import anthropic

from src.config import settings

_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY.get_secret_value())


def _image_content(urls: list[str], prompt: str) -> list[dict]:
    content = []
    for url in urls[:3]:  # max 3 frames per call
        content.append({"type": "image", "source": {"type": "url", "url": url}})
    content.append({"type": "text", "text": prompt})
    return content


async def extract_vin_from_frames(frame_urls: list[str]) -> str:
    """Extract VIN number from video frames using Claude Vision."""
    if not frame_urls:
        return ""
    prompt = 'Find the VIN number in these images. Return ONLY JSON: {"vin": "..."} or {"vin": ""} if not visible.'
    content = _image_content(frame_urls, prompt)
    try:
        response = await asyncio.to_thread(
            _client.messages.create,
            model="claude-sonnet-4-6",
            max_tokens=256,
            messages=[{"role": "user", "content": content}],
        )
        data = json.loads(response.content[0].text)
        return data.get("vin", "")
    except (json.JSONDecodeError, IndexError):
        return ""


async def read_odometer(frame_urls: list[str]) -> int | None:
    """Read odometer mileage from video frames using Claude Vision."""
    if not frame_urls:
        return None
    prompt = 'Read the odometer mileage. Return ONLY JSON: {"mileage": 12345} or {"mileage": null} if not visible.'
    content = _image_content(frame_urls, prompt)
    try:
        response = await asyncio.to_thread(
            _client.messages.create,
            model="claude-sonnet-4-6",
            max_tokens=128,
            messages=[{"role": "user", "content": content}],
        )
        data = json.loads(response.content[0].text)
        return data.get("mileage")
    except (json.JSONDecodeError, IndexError):
        return None


async def read_tire_size(frame_urls: list[str]) -> str:
    """Read tire size from video frames using Claude Vision."""
    if not frame_urls:
        return ""
    prompt = 'Read the tire size from the sidewall (format like 225/55R17). Return ONLY JSON: {"tire_size": "..."} or {"tire_size": ""} if not visible.'
    content = _image_content(frame_urls, prompt)
    try:
        response = await asyncio.to_thread(
            _client.messages.create,
            model="claude-sonnet-4-6",
            max_tokens=128,
            messages=[{"role": "user", "content": content}],
        )
        data = json.loads(response.content[0].text)
        return data.get("tire_size", "")
    except (json.JSONDecodeError, IndexError):
        return ""


async def analyze_damage(frame_urls: list[str]) -> list[str]:
    """Analyze visible vehicle damage from video frames using Claude Vision."""
    if not frame_urls:
        return []
    prompt = 'List any visible vehicle damage. Return ONLY JSON: {"damage": ["description 1"]} or {"damage": []} if none.'
    content = _image_content(frame_urls, prompt)
    try:
        response = await asyncio.to_thread(
            _client.messages.create,
            model="claude-sonnet-4-6",
            max_tokens=512,
            messages=[{"role": "user", "content": content}],
        )
        data = json.loads(response.content[0].text)
        return data.get("damage", [])
    except (json.JSONDecodeError, IndexError):
        return []
