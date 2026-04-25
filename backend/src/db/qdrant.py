from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams
from openai import AsyncOpenAI
from src.config import settings

_qdrant = AsyncQdrantClient(
    url=settings.QDRANT_URL,
    api_key=settings.QDRANT_API_KEY.get_secret_value() or None,
)

_openai = AsyncOpenAI(api_key=settings.OPENAI_API_KEY.get_secret_value())

EMBED_MODEL = "text-embedding-3-small"
EMBED_DIM = 1536

COLLECTIONS = {
    "parts": VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
    "few_shots": VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
    "feedback_bank": VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
}

qdrant = _qdrant


async def embed(text: str) -> list[float]:
    resp = await _openai.embeddings.create(model=EMBED_MODEL, input=text)
    return resp.data[0].embedding


async def ensure_collections() -> None:
    for name, params in COLLECTIONS.items():
        if not await _qdrant.collection_exists(name):
            await _qdrant.create_collection(collection_name=name, vectors_config=params)
