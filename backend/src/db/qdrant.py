import asyncio

import google.generativeai as genai
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams
from src.config import settings

_qdrant = AsyncQdrantClient(
    url=settings.QDRANT_URL,
    api_key=settings.QDRANT_API_KEY.get_secret_value() or None,
)

genai.configure(api_key=settings.GEMINI_API_KEY.get_secret_value())

EMBED_MODEL = "models/text-embedding-004"
EMBED_DIM = 768

COLLECTIONS = {
    "parts": VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
    "few_shots": VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
    "feedback_bank": VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
}

qdrant = _qdrant


async def embed(text: str) -> list[float]:
    result = await asyncio.to_thread(
        genai.embed_content,
        model=EMBED_MODEL,
        content=text,
        task_type="retrieval_query",
    )
    return result["embedding"]


async def ensure_collections() -> None:
    for name, params in COLLECTIONS.items():
        if not await _qdrant.collection_exists(name):
            await _qdrant.create_collection(collection_name=name, vectors_config=params)
