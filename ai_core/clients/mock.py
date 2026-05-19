"""
모델 서버 오프라인 시 테스트용 mock clients.
config.py에서 USE_MOCK_CLIENTS=true 설정 시 deps.py에서 자동 선택.
"""
from .base import BaseLLMClient, BaseEmbeddingClient, BaseRerankerClient


class MockLLMClient(BaseLLMClient):
    async def generate(self, prompt: str, **kwargs) -> str:
        return (
            "이것은 테스트 답변입니다[출처1]. "
            "실제 모델 서버 연결 시 정확한 답변이 제공됩니다[출처2]."
        )


class MockEmbeddingClient(BaseEmbeddingClient):
    def __init__(self, dim: int = 1024):
        self.dim = dim

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * self.dim for _ in texts]


class MockRerankerClient(BaseRerankerClient):
    async def rerank(self, query: str, passages: list[str]) -> list[float]:
        # 순서 그대로 내림차순 점수 반환
        n = len(passages)
        return [1.0 - (i / n) for i in range(n)]
