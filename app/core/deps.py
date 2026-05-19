from fastapi import Header, HTTPException
from ai_core.clients.base import BaseLLMClient, BaseEmbeddingClient, BaseRerankerClient
from app.core.config import settings


def get_llm_client() -> BaseLLMClient:
    if settings.USE_MOCK_CLIENTS:
        from ai_core.clients.mock import MockLLMClient
        return MockLLMClient()
    from ai_core.clients.llm_client import LlamaCppClient
    return LlamaCppClient(endpoint=settings.LLM_ENDPOINT, timeout=settings.LLM_TIMEOUT)


def get_embedding_client() -> BaseEmbeddingClient:
    if settings.USE_MOCK_CLIENTS:
        from ai_core.clients.mock import MockEmbeddingClient
        return MockEmbeddingClient(dim=settings.EMBEDDING_DIM)
    from ai_core.clients.embedding_client import BGEEmbeddingClient
    return BGEEmbeddingClient(endpoint=settings.EMBEDDING_ENDPOINT, timeout=settings.EMBEDDING_TIMEOUT)


def get_reranker_client() -> BaseRerankerClient:
    if settings.USE_MOCK_CLIENTS:
        from ai_core.clients.mock import MockRerankerClient
        return MockRerankerClient()
    from ai_core.clients.reranker_client import BGERerankerClient
    return BGERerankerClient(endpoint=settings.RERANKER_ENDPOINT, timeout=settings.RERANKER_TIMEOUT)


async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != settings.LMS_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True
