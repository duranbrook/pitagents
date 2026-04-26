import asyncio
import json
import logging

import anthropic

from src.config import settings

logger = logging.getLogger(__name__)

PROMPT = """You are a vehicle repair expert assistant. Analyze the technician's observations below (transcript and/or inspection photos) and extract repair findings.

Return a JSON object with exactly this structure:
{{
  "summary": "<one or two sentence summary of the overall vehicle condition>",
  "findings": [
    {{
      "part": "<name of the part or system>",
      "severity": "<high | medium | low>",
      "notes": "<brief description of the issue>"
    }}
  ]
}}

Return only valid JSON — no markdown fences, no extra text.

Transcript:
{transcript}"""

_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY.get_secret_value())


async def extract_repair_findings(
    transcript: str,
    image_urls: list[str] | None = None,
) -> dict:
    """Extract structured repair findings from a technician transcript and/or photos.

    Returns dict with 'summary' (str) and 'findings' (list of {part, severity, notes}).
    """
    if not transcript.strip() and not image_urls:
        return {"summary": "", "findings": []}

    safe_transcript = transcript.replace("{", "{{").replace("}", "}}")
    text_block = {"type": "text", "text": PROMPT.format(transcript=safe_transcript or "No verbal transcript provided.")}

    # Build content: images first, then text prompt
    content: list[dict] = []
    if image_urls:
        for url in image_urls:
            content.append({
                "type": "image",
                "source": {"type": "url", "url": url},
            })
    content.append(text_block)

    response = await asyncio.to_thread(
        _client.messages.create,
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": content}],
    )

    try:
        raw = response.content[0].text.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        return json.loads(raw)
    except (json.JSONDecodeError, IndexError, KeyError):
        logger.warning("extract_findings: failed to parse JSON. raw=%s", response.content[0].text[:300] if response.content else "empty")
        return {"summary": transcript[:500], "findings": []}
