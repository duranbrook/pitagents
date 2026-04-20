import httpx

NHTSA_URL = "https://vpic.nhtsa.dot.gov/api/vehicles/decodevinvalues/{vin}?format=json"


async def lookup_vehicle_by_vin(vin: str) -> dict:
    """Returns {vin, year, make, model, trim} or {} if invalid/not found."""
    if not vin or len(vin) != 17:
        return {}
    async with httpx.AsyncClient() as client:
        r = await client.get(NHTSA_URL.format(vin=vin))
        data = r.json()
    results = data.get("Results", [{}])[0]
    return {
        "vin": vin,
        "year": results.get("ModelYear", ""),
        "make": results.get("Make", ""),
        "model": results.get("Model", ""),
        "trim": results.get("Trim", ""),
    }
