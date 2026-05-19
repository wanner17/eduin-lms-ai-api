import httpx
from tenacity import retry, stop_after_attempt, wait_fixed
from .base import BaseRerankerClient


class BGERerankerClient(BaseRerankerClient):
    def __init__(self, endpoint: str, timeout: int = 30):
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    async def rerank(self, query: str, passages: list[str]) -> list[float]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(
                f"{self.endpoint}/rerank",
                json={"query": query, "passages": passages},
            )
            r.raise_for_status()
            data = r.json()
            if "scores" in data:
                return data["scores"]
            return [item["score"] for item in data["results"]]
