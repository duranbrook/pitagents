import re
import asyncio
import json
import logging

import anthropic

from src.config import settings

logger = logging.getLogger(__name__)

PROMPT = """You are a vehicle repair expert assistant. Work through the following steps, writing your reasoning for each step before producing the final answer.

STEP 1 — COUNT THE ISSUES
Read the transcript and look at every photo. Write a numbered list of every distinct issue you find. Each entry on the list is one specific problem on one specific part.
Example:
  1. Lower control arm (right) — cracked bushing
  2. Front bumper — paint missing, deep gouge
  3. Left headlamp — cracked lens with moisture

STEP 2 — MAP PHOTOS TO ISSUES
{photo_url_list}For each issue from Step 1, decide which photo (if any) best shows it. Write the mapping:
  Issue 1 → Photo N (URL: ...)
  Issue 2 → Photo N (URL: ...)
  Issue 3 → no photo
Each photo may be assigned to only ONE issue.

STEP 3 — OUTPUT JSON
Using your Step 1 issue list and Step 2 photo mapping, output a JSON object.
Each issue from Step 1 becomes one entry in "findings". Do NOT merge separate issues.

Output the JSON inside <json> tags:
<json>
{{
  "summary": "<one or two sentence overall summary>",
  "findings": [
    {{
      "part": "<specific part name from Step 1>",
      "severity": "<high | medium | low>",
      "notes": "<one sentence describing the exact visible issue>",
      "photo_url": "<exact URL from Step 2 mapping, or null>"
    }}
  ]
}}
</json>

Transcript:
{transcript}"""

_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY.get_secret_value())


async def extract_repair_findings(
    transcript: str,
    image_urls: list[str] | None = None,
    image_s3_urls: list[str] | None = None,
) -> dict:
    """Extract structured repair findings from a technician transcript and/or photos.

    Args:
        image_urls: Presigned URLs for Claude to download the images (may expire).
        image_s3_urls: Stable original S3 URLs used as the identifier in photo_url.
                       If omitted, image_urls are used as identifiers too.

    Returns dict with 'summary' (str) and 'findings' (list of {part, severity, notes, photo_url}).
    photo_url is the stable S3 URL of the photo that best illustrates each finding, or None.
    """
    if not transcript.strip() and not image_urls:
        return {"summary": "", "findings": []}

    safe_transcript = transcript.replace("{", "{{").replace("}", "}}")

    # reference_urls are what Claude writes in photo_url — stable S3 URLs, not presigned ones.
    reference_urls = image_s3_urls if image_s3_urls else image_urls
    # presigned_to_ref lets us map back if Claude writes the presigned URL anyway.
    presigned_to_ref: dict[str, str] = {}
    if image_urls and reference_urls:
        for presigned, ref in zip(image_urls, reference_urls):
            presigned_to_ref[presigned] = ref

    if reference_urls:
        url_lines = "\n".join(f"  Photo {i+1}: {url}" for i, url in enumerate(reference_urls))
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

    # Build content: images first (presigned so Claude can download), then text prompt
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
        raw = response.content[0].text
        # Extract JSON from <json>...</json> tags (preferred path)
        tag_match = re.search(r"<json>\s*([\s\S]*?)\s*</json>", raw)
        if tag_match:
            result = json.loads(tag_match.group(1))
        else:
            # Fallback: strip markdown fences
            stripped = raw.strip()
            if stripped.startswith("```"):
                stripped = stripped.split("```", 2)[1]
                if stripped.startswith("json"):
                    stripped = stripped[4:]
                stripped = stripped.strip()
                result = json.loads(stripped)
            else:
                # Last resort: find first {...} block
                brace_match = re.search(r"\{[\s\S]*\}", stripped)
                if brace_match:
                    result = json.loads(brace_match.group())
                else:
                    raise ValueError("no JSON found")

        # Normalize photo_url to stable S3 URLs.
        # Claude may write the presigned URL (or strip its query string) — map both back.
        if presigned_to_ref:
            for finding in result.get("findings", []):
                pu = finding.get("photo_url")
                if not pu:
                    continue
                # Exact match (Claude wrote presigned URL verbatim)
                if pu in presigned_to_ref:
                    finding["photo_url"] = presigned_to_ref[pu]
                    continue
                # Bare URL match (Claude stripped query string from presigned URL)
                bare = pu.split("?")[0]
                for presigned, ref in presigned_to_ref.items():
                    if presigned.split("?")[0] == bare or ref.split("?")[0] == bare:
                        finding["photo_url"] = ref
                        break

        return result
    except Exception:
        logger.warning("extract_findings: failed to parse JSON. raw=%s", response.content[0].text[:300] if response.content else "empty")
        return {"summary": transcript[:500], "findings": []}
