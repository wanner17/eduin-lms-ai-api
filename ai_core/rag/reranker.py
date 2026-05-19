from ai_core.clients.base import BaseRerankerClient


class Reranker:
    def __init__(self, client: BaseRerankerClient):
        self.client = client

    async def rerank(self, query: str, chunks: list[dict], top_n: int = 5) -> list[dict]:
        if not chunks:
            return []

        passages = [c["text"] for c in chunks]
        scores = await self.client.rerank(query=query, passages=passages)

        ranked = sorted(
            zip(chunks, scores),
            key=lambda x: x[1],
            reverse=True,
        )
        return [chunk for chunk, _ in ranked[:top_n]]
