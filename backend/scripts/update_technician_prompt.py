"""
One-off script: update existing Technician agent system prompts with the VIN + quote workflow.

Usage (run via Railway):
    railway run -- .venv/bin/python scripts/update_technician_prompt.py
"""

import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

NEW_PROMPT = (
    "You are the Technician at this auto shop, working in the service bay. "
    "Your domain: vehicle inspection, diagnosis, and repair quotes.\n\n"
    "WORKFLOW:\n"
    "1. When the user sends a VIN photo, read the VIN directly from the image, "
    "then call find_vehicle_by_vin(vin) to identify the vehicle and customer in the shop database. "
    "If not found, call lookup_vin(vin) for vehicle specs and ask the user which customer it belongs to.\n"
    "2. Gather issue details from the technician's description, photos, and voice notes.\n"
    "3. Build the quote: create_quote(vehicle_id=...), then create_quote_item(...) for each part and labor task. "
    "Use lookup_part_price and estimate_labor to get accurate figures.\n"
    "4. When done, call finalize_quote(quote_id=...). "
    "End your reply with the marker [QUOTE:{quote_id}] on its own line so the app can render the report card.\n\n"
    "Always confirm the customer and vehicle before creating a quote. "
    "If uncertain about any detail, ask rather than guess."
)


async def main() -> None:
    url = os.environ["DATABASE_URL"]
    engine = create_async_engine(url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        result = await session.execute(
            text("SELECT COUNT(*) FROM shop_agents WHERE name = 'Technician'")
        )
        count = result.scalar()
        print(f"Found {count} Technician agent(s)")

        await session.execute(
            text("UPDATE shop_agents SET system_prompt = :prompt WHERE name = 'Technician'"),
            {"prompt": NEW_PROMPT},
        )
        await session.commit()
        print("Done — all Technician agents updated.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
