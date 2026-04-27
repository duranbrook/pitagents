import asyncio
import json
import logging

import anthropic

from src.config import settings

logger = logging.getLogger(__name__)

PROMPT = """You are a vehicle repair expert assistant. Your task has two parts:

PART 1 — EXAMINE EACH PHOTO
For every numbered photo image provided, look at it carefully and note:
- Which specific vehicle part or system is shown (e.g. lower control arm, front bumper, brake rotor, headlamp)
- What condition issue is visible (wear, damage, leak, corrosion, etc.)

PART 2 — EXTRACT FINDINGS WITH PHOTO ASSIGNMENT
Cross-reference your photo observations with the technician's transcript. Create one finding per distinct issue. For each finding, assign the single best photo that shows that issue by writing its exact URL from the list below.

{photo_url_list}Rules:
- Each photo URL may be assigned to at most ONE finding (the one it most clearly documents)
- If a photo doesn't clearly show any specific issue, leave it unassigned (do not force it)
- If a finding has no matching photo, set photo_url to null
- Do not invent issues not visible in photos or mentioned in the transcript

Return ONLY a JSON object with exactly this structure (no markdown fences, no extra text):
{{
  "summary": "<one or two sentence summary of the overall vehicle condition>",
  "findings": [
    {{
      "part": "<specific part name — e.g. 'lower control arm (right)', 'front bumper', 'left headlamp'>",
      "severity": "<high | medium | low>",
      "notes": "<brief description of the visible issue>",
      "photo_url": "<exact URL from the list above that best shows this issue, or null>"
    }}
  ]
}}

Transcript:
{transcript}"""

_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY.get_secret_value())


async def extract_repair_findings(
    transcript: str,
    image_urls: list[str] | None = None,
) -> dict:
    """Extract structured repair findings from a technician transcript and/or photos.

    Returns dict with 'summary' (str) and 'findings' (list of {part, severity, notes, photo_url}).
    photo_url is the S3 URL of the photo that best illustrates each finding, or None.
    """
    if not transcript.strip() and not image_urls:
        return {"summary": "", "findings": []}

    safe_transcript = transcript.replace("{", "{{").replace("}", "}}")

    # Tell Claude the exact URLs so it can reference them in photo_url fields
    if image_urls:
        url_lines = "\n".join(f"  Photo {i+1}: {url}" for i, url in enumerate(image_urls))
        photo_url_list = f"Inspection photos provided (use these exact URLs in photo_url):\n{url_lines}\n\n"
    else:
        photo_url_list = ""

    text_block = {
        "type": "text",
        "text": PROMPT.format(
            transcript=safe_transcript or "No verbal transcript provided.",
            photo_url_list=photo_url_list,
        ),
    }

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
        model="claude-sonnet-4-6",
        max_tokens=2048,
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
