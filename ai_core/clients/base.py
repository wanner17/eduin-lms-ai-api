from abc import ABC, abstractmethod


class BaseLLMClient(ABC):
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str: ...


class BaseEmbeddingClient(ABC):
    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class BaseRerankerClient(ABC):
    @abstractmethod
    async def rerank(self, query: str, passages: list[str]) -> list[float]: ...
