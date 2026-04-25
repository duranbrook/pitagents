#!/usr/bin/env python
"""Seed initial few-shot examples into the Qdrant 'few_shots' collection.

Usage:
    python -m src.scripts.seed_few_shots \\
        --openai-api-key sk-... \\
        [--qdrant-url http://localhost:6333] \\
        [--qdrant-api-key ""]
"""
import argparse
import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Distance, VectorParams
from openai import OpenAI

EMBED_MODEL = "text-embedding-3-small"
EMBED_DIM = 1536

FEW_SHOTS = [
    {"agent_id": "assistant", "intent": "VIN_LOOKUP",
     "question": "Can you look up this VIN for me? 1HGBH41JXMN109186",
     "ideal_response": "Sure! Let me look that up for you right now."},
    {"agent_id": "assistant", "intent": "VIN_LOOKUP",
     "question": "What car is this? VIN 2T1BURHE0JC012345",
     "ideal_response": "I'll run that VIN through the lookup to get the vehicle details."},
    {"agent_id": "assistant", "intent": "QUOTE_BUILD",
     "question": "Can you build a quote for a brake job on a 2019 Honda Civic?",
     "ideal_response": "I'll create a quote for that. Let me look up brake pad and rotor prices first."},
    {"agent_id": "assistant", "intent": "QUOTE_BUILD",
     "question": "Add front brake pads and rotors to the current quote",
     "ideal_response": "I'll search the parts catalog for front brake pads and rotors and add them to your quote."},
    {"agent_id": "assistant", "intent": "PARTS_LOOKUP",
     "question": "How much do spark plugs cost?",
     "ideal_response": "Let me search the parts catalog for spark plugs and get you the current price."},
    {"agent_id": "assistant", "intent": "PARTS_LOOKUP",
     "question": "What's the price for an oil filter?",
     "ideal_response": "I'll look up oil filters in the parts catalog right now."},
    {"agent_id": "assistant", "intent": "LABOR_ESTIMATE",
     "question": "How much would labor cost for a timing belt replacement?",
     "ideal_response": "I'll estimate that using the shop's current labor rate."},
    {"agent_id": "assistant", "intent": "DIAGNOSTIC",
     "question": "My car makes a grinding noise when I brake",
     "ideal_response": "That grinding noise is likely worn brake pads or rotors. What year/make/model is the vehicle?"},
    {"agent_id": "tom", "intent": "ANALYTICS_SESSIONS",
     "question": "How many inspections did we complete this week?",
     "ideal_response": "Let me pull up the inspection session data for this week."},
    {"agent_id": "tom", "intent": "ANALYTICS_SESSIONS",
     "question": "Which inspections are still in progress?",
     "ideal_response": "I'll query for sessions that haven't been completed yet."},
    {"agent_id": "tom", "intent": "ANALYTICS_REVENUE",
     "question": "What was our total revenue from finalized quotes this month?",
     "ideal_response": "Let me look up finalized quotes and sum the totals for this month."},
    {"agent_id": "tom", "intent": "ANALYTICS_TECHNICIAN",
     "question": "Who completed the most inspections last week?",
     "ideal_response": "I'll check session records to see which technician led last week."},
]


def _ensure_collection(qdrant: QdrantClient) -> None:
    existing = {c.name for c in qdrant.get_collections().collections}
    if "few_shots" not in existing:
        qdrant.create_collection(
            collection_name="few_shots",
            vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
        )
        print("Created 'few_shots' collection.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed few-shot examples into Qdrant")
    parser.add_argument("--qdrant-url", default="http://localhost:6333")
    parser.add_argument("--qdrant-api-key", default="")
    parser.add_argument("--openai-api-key", required=True)
    args = parser.parse_args()

    qdrant = QdrantClient(url=args.qdrant_url, api_key=args.qdrant_api_key or None)
    openai_client = OpenAI(api_key=args.openai_api_key)

    _ensure_collection(qdrant)

    questions = [fs["question"] for fs in FEW_SHOTS]
    resp = openai_client.embeddings.create(model=EMBED_MODEL, input=questions)
    vectors = [e.embedding for e in resp.data]

    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=v,
            payload=fs,
        )
        for fs, v in zip(FEW_SHOTS, vectors)
    ]
    qdrant.upsert(collection_name="few_shots", points=points)
    print(f"Seeded {len(points)} few-shot examples into 'few_shots' collection.")


if __name__ == "__main__":
    main()
