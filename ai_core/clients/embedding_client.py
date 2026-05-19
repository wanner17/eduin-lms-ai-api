import httpx
from tenacity import retry, stop_after_attempt, wait_fixed
from .base import BaseEmbeddingClient


class BGEEmbeddingClient(BaseEmbeddingClient):
    def __init__(self, endpoint: str, timeout: int = 30):
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    async def embed(self, texts: list[str]) -> list[list[float]]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(
                f"{self.endpoint}/embed",
                json={"texts": texts},
            )
            r.raise_for_status()
            return r.json()["embeddings"]
