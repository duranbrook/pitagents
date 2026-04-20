import asyncio
import json

import anthropic

from src.config import settings

PROMPT = """You are a vehicle repair expert assistant. Analyze the following technician transcript and extract repair findings.

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

# Module-level client singleton
_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY.get_secret_value())


async def extract_repair_findings(transcript: str) -> dict:
    """Extract structured repair findings from a technician transcript using Claude Haiku.

    Returns a dict with 'summary' (str) and 'findings' (list of dicts with
    'part', 'severity', 'notes').  Returns empty structure for blank transcripts
    and a fallback structure on JSON parse errors.
    """
    if not transcript.strip():
        return {"summary": "", "findings": []}

    response = await asyncio.to_thread(
        _client.messages.create,
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": PROMPT.format(transcript=transcript.replace("{", "{{").replace("}", "}}"))}],
    )

    try:
        return json.loads(response.content[0].text)
    except (json.JSONDecodeError, IndexError, KeyError):
        return {"summary": transcript[:500], "findings": []}
