from ai_core.clients.base import BaseEmbeddingClient
from ai_core.rag.chunker import Chunk


class LMSRetriever:
    def __init__(self, qdrant, embed_client: BaseEmbeddingClient):
        self.qdrant = qdrant
        self.embed = embed_client

    async def retrieve(
        self,
        query: str,
        course_id: int = None,
        lecture_id: int = None,
        material_ids: list[int] = None,
        top_k: int = 20,
    ) -> list[dict]:
        vectors = await self.embed.embed([query])
        query_vec = vectors[0]

        filter_params = {}
        if course_id is not None:
            filter_params["course_id"] = course_id
        if lecture_id is not None:
            filter_params["lecture_id"] = lecture_id

        results = self.qdrant.search(
            vector=query_vec,
            filter_params=filter_params,
            material_ids=material_ids,
            top_k=top_k,
        )
        return results
