import asyncio
import json
import logging

import anthropic

from src.config import settings

logger = logging.getLogger(__name__)

PROMPT = """You are a vehicle repair expert assistant. Follow these steps exactly.

STEP 1 — DESCRIBE EACH PHOTO INDIVIDUALLY
Look at each numbered photo. For each one, write one line:
  "Photo N: [part shown] — [what the issue is]"
Example:
  "Photo 1: lower control arm (right) — visible crack in the bushing"
  "Photo 2: front bumper — deep gouge and paint missing"
  "Photo 3: left headlamp — lens cracked, moisture inside"

STEP 2 — CREATE ONE FINDING PER DISTINCT PART/ISSUE
CRITICAL RULE: Every photo that shows a different part must become its own separate finding.
Do NOT merge "lower control arm" and "front bumper" into one finding — they are two separate findings.
Do NOT merge issues just because they are on the same vehicle.
If you have 3 photos showing 3 different problems, you must produce at least 3 findings.

Also include any additional issues mentioned in the transcript that have no photo.

STEP 3 — ASSIGN THE PHOTO URL
For each finding, set photo_url to the exact URL of the photo that documents it.
Each URL may be assigned to at most one finding. If no photo matches, set photo_url to null.

{photo_url_list}STEP 4 — OUTPUT
Return ONLY the JSON below (no markdown fences, no extra text, no STEP 1 output):
{{
  "summary": "<one or two sentence summary of the overall vehicle condition>",
  "findings": [
    {{
      "part": "<specific part — e.g. 'lower control arm (right)', 'front bumper', 'left headlamp'>",
      "severity": "<high | medium | low>",
      "notes": "<one sentence describing the exact issue visible>",
      "photo_url": "<exact URL from the list above, or null>"
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
