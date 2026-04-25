"""Semantic parts search tool using Qdrant. Falls back to in-memory catalog."""
from qdrant_client.models import Filter, FieldCondition, MatchValue
from src.db.qdrant import qdrant, embed
from src.agents.tools.quote_tools import PARTS_CATALOG

PARTS_TOOL_SCHEMAS = [
    {
        "name": "semantic_parts_search",
        "description": (
            "Search the parts catalog by natural language description. "
            "Returns top matching parts with part number, description, brand, and price. "
            "Use this for any parts lookup — prefer it over guessing prices."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language description (e.g. 'front brake pads for BMW 3 series')",
                },
                "make": {
                    "type": "string",
                    "description": "Optional: vehicle make to filter results (e.g. 'BMW', 'Toyota')",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of results to return (default 3)",
                },
            },
            "required": ["query"],
        },
    }
]


async def semantic_parts_search(query: str, make: str | None = None, top_k: int = 3) -> dict:
    try:
        query_vector = await embed(query)

        filters = []
        if make:
            filters.append(FieldCondition(key="make", match=MatchValue(value=make.upper())))

        search_filter = Filter(must=filters) if filters else None

        hits = await qdrant.search(
            collection_name="parts",
            query_vector=query_vector,
            query_filter=search_filter,
            limit=top_k,
        )

        if hits:
            return {
                "results": [
                    {
                        "part_number": h.payload.get("part_number", ""),
                        "description": h.payload.get("description", ""),
                        "brand": h.payload.get("brand", ""),
                        "category": h.payload.get("category", ""),
                        "unit_price": h.payload.get("unit_price", 0.0),
                        "score": round(h.score, 3),
                    }
                    for h in hits
                ]
            }
    except Exception:
        pass

    # Fallback: in-memory catalog
    needle = query.lower().strip()
    for entry in PARTS_CATALOG:
        if needle in entry["part"].lower():
            return {
                "results": [{
                    "part_number": entry["part_number"],
                    "description": entry["part"],
                    "brand": "Generic",
                    "category": "Parts",
                    "unit_price": entry["unit_price"],
                    "score": 1.0,
                }]
            }

    return {"results": [], "message": f"No parts found matching: {query}"}
