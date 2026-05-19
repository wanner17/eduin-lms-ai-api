import httpx
from fastapi import APIRouter, Depends

from app.core.config import settings
from app.core.deps import verify_api_key

router = APIRouter()


async def _ping(url: str, name: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{url}/health")
            return {"name": name, "status": "ok", "code": r.status_code}
    except Exception as e:
        return {"name": name, "status": "error", "detail": str(e)}


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "env": settings.ENV,
        "mock_clients": settings.USE_MOCK_CLIENTS,
    }


@router.get("/model-status", dependencies=[Depends(verify_api_key)])
async def model_status():
    results = await _ping(settings.LLM_ENDPOINT, "llm")
    embed = await _ping(settings.EMBEDDING_ENDPOINT, "embedding")
    rerank = await _ping(settings.RERANKER_ENDPOINT, "reranker")
    return {
        "llm": results,
        "embedding": embed,
        "reranker": rerank,
    }
