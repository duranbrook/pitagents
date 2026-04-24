"""VIN-related tools for the Assistant agent."""
from src.tools.vin_lookup import lookup_vehicle_by_vin
from src.tools.vision import extract_vin_from_frames

# Anthropic tool schema definitions (passed to messages.create(tools=[...]))
VIN_TOOL_SCHEMAS = [
    {
        "name": "lookup_vin",
        "description": "Look up vehicle information (year, make, model, trim) from a VIN number using the NHTSA database.",
        "input_schema": {
            "type": "object",
            "properties": {
                "vin": {"type": "string", "description": "The 17-character Vehicle Identification Number"}
            },
            "required": ["vin"],
        },
    },
    {
        "name": "extract_vin_from_image",
        "description": (
            "Extract a VIN from an externally-hosted image the user has provided as a URL in their text. "
            "Do NOT use this tool if an image is already embedded in the current message — analyze it directly instead."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "image_url": {"type": "string", "description": "HTTPS URL of the image containing the VIN (not a data: URL)"}
            },
            "required": ["image_url"],
        },
    },
]


async def lookup_vin(vin: str) -> dict:
    vin = vin.upper().strip() if vin else vin
    if not vin or len(vin) != 17:
        return {"error": f"Invalid VIN: must be 17 characters, got '{vin}'"}
    return await lookup_vehicle_by_vin(vin)


async def extract_vin_from_image(image_url: str) -> dict:
    vin = await extract_vin_from_frames([image_url])
    return {"vin": vin} if vin else {"error": "No VIN found in image"}
