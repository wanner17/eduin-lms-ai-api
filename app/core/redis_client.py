import json
import redis.asyncio as aioredis
from app.core.config import settings

_redis: aioredis.Redis | None = None
_memory_store: dict = {}  # Redis 없을 때 fallback

INGEST_KEY = "ingest:{material_id}"
INGEST_TTL = 60 * 60 * 24


def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


async def set_ingest_status(material_id: str, status: str, **extra):
    key = INGEST_KEY.format(material_id=material_id)
    data = {"status": status, "material_id": material_id, **extra}
    try:
        await get_redis().set(key, json.dumps(data, ensure_ascii=False), ex=INGEST_TTL)
    except Exception:
        _memory_store[key] = data


async def get_ingest_status(material_id: str) -> dict | None:
    key = INGEST_KEY.format(material_id=material_id)
    try:
        val = await get_redis().get(key)
        return json.loads(val) if val else _memory_store.get(key)
    except Exception:
        return _memory_store.get(key)
