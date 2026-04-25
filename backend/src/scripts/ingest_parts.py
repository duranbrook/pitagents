#!/usr/bin/env python
"""Ingest a parts CSV file into the Qdrant 'parts' collection.

Usage:
    python -m src.scripts.ingest_parts \\
        --file path/to/parts.csv \\
        --gemini-api-key AIza... \\
        [--mapping path/to/mapping.json] \\
        [--qdrant-url http://localhost:6333] \\
        [--qdrant-api-key ""] \\
        [--dry-run]
"""
import argparse
import csv
import json
import uuid

import google.generativeai as genai
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Distance, VectorParams

EMBED_MODEL = "models/text-embedding-004"
EMBED_DIM = 768
BATCH_SIZE = 100  # Gemini batch limit is lower than OpenAI's

DEFAULT_MAPPING = {
    "description": "part_name",
    "part_number": "manufacturer_number",
    "brand": "brand",
    "category": "category",
    "unit_price": "regular_price",
    "make": None,
}


def _load_mapping(path: str | None) -> dict:
    if not path:
        return DEFAULT_MAPPING
    with open(path) as f:
        return json.load(f)


def _get(row: dict, mapping: dict, field: str) -> str:
    col = mapping.get(field)
    return row.get(col, "") if col else ""


def _ensure_collection(qdrant: QdrantClient) -> None:
    existing = {c.name for c in qdrant.get_collections().collections}
    if "parts" in existing:
        info = qdrant.get_collection("parts")
        current_dim = info.config.params.vectors.size
        if current_dim != EMBED_DIM:
            print(f"'parts' collection has dim={current_dim}, expected {EMBED_DIM}. Recreating.")
            qdrant.delete_collection("parts")
            existing.discard("parts")
    if "parts" not in existing:
        qdrant.create_collection(
            collection_name="parts",
            vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
        )
        print("Created 'parts' collection.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest parts CSV into Qdrant")
    parser.add_argument("--file", required=True)
    parser.add_argument("--mapping", default=None)
    parser.add_argument("--qdrant-url", default="http://localhost:6333")
    parser.add_argument("--qdrant-api-key", default="")
    parser.add_argument("--gemini-api-key", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    genai.configure(api_key=args.gemini_api_key)
    mapping = _load_mapping(args.mapping)
    qdrant = QdrantClient(url=args.qdrant_url, api_key=args.qdrant_api_key or None)

    if not args.dry_run:
        _ensure_collection(qdrant)

    with open(args.file, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    print(f"Loaded {len(rows)} rows from {args.file}")

    batch: list[dict] = []
    total = 0

    for i, row in enumerate(rows):
        part_number = _get(row, mapping, "part_number")
        description = _get(row, mapping, "description")
        brand = _get(row, mapping, "brand")
        category = _get(row, mapping, "category")
        make = _get(row, mapping, "make")
        try:
            unit_price = float(_get(row, mapping, "unit_price") or 0)
        except ValueError:
            unit_price = 0.0

        embed_text = f"{description} {category}".strip()
        if not embed_text or not part_number:
            continue

        batch.append({
            "part_number": part_number,
            "description": description,
            "brand": brand,
            "category": category,
            "make": make.upper() if make else "",
            "unit_price": unit_price,
            "_embed_text": embed_text,
        })

        is_last = (i == len(rows) - 1)
        if len(batch) >= BATCH_SIZE or (is_last and batch):
            texts = [r["_embed_text"] for r in batch]

            if not args.dry_run:
                resp = genai.embed_content(
                    model=EMBED_MODEL,
                    content=texts,
                    task_type="retrieval_document",
                )
                vectors = resp["embedding"]
                points = [
                    PointStruct(
                        id=str(uuid.uuid5(uuid.NAMESPACE_OID, r["part_number"])),
                        vector=v,
                        payload={k: r[k] for k in r if not k.startswith("_")},
                    )
                    for r, v in zip(batch, vectors)
                ]
                qdrant.upsert(collection_name="parts", points=points)

            total += len(batch)
            print(f"Progress: {total}/{len(rows)}")
            batch = []

    print(f"Done. {'Would upsert' if args.dry_run else 'Upserted'} {total} parts.")


if __name__ == "__main__":
    main()
