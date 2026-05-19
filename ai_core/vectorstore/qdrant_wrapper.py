from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    HasIdCondition,
    MatchValue,
    PointStruct,
    VectorParams,
)
from ai_core.rag.chunker import Chunk


class QdrantWrapper:
    def __init__(self, url: str, collection: str = "lms_materials", vector_size: int = 1024):
        self.client = QdrantClient(url=url)
        self.collection = collection
        self.vector_size = vector_size

    def ensure_collection(self):
        if not self.client.collection_exists(self.collection):
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
            )

    def upsert_chunks(
        self,
        chunks: list[Chunk],
        embeddings: list[list[float]],
        extra_metadata: dict = None,
    ):
        points = []
        for i, (chunk, vec) in enumerate(zip(chunks, embeddings)):
            payload = {
                "text": chunk.text,
                "page": chunk.page,
                "chunk_index": chunk.chunk_index,
                "material_id": chunk.material_id,
                "section_title": chunk.section_title,
                **(extra_metadata or {}),
                **chunk.metadata,
            }
            point_id = self._make_id(chunk.material_id, chunk.chunk_index)
            points.append(PointStruct(id=point_id, vector=vec, payload=payload))

        self.client.upsert(collection_name=self.collection, points=points)

    def search(
        self,
        vector: list[float],
        filter_params: dict = None,
        material_ids: list[int] = None,
        top_k: int = 20,
    ) -> list[dict]:
        query_filter = self._build_filter(filter_params or {}, material_ids)
        results = self.client.search(
            collection_name=self.collection,
            query_vector=vector,
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
        )
        return [
            {**hit.payload, "_score": hit.score, "_id": hit.id}
            for hit in results
        ]

    def delete_by_material(self, material_id: str):
        self.client.delete(
            collection_name=self.collection,
            points_selector=Filter(
                must=[FieldCondition(key="material_id", match=MatchValue(value=material_id))]
            ),
        )

    def _build_filter(self, params: dict, material_ids: list[str] = None) -> Filter | None:
        conditions = []
        for key, val in params.items():
            if val is not None:
                conditions.append(FieldCondition(key=key, match=MatchValue(value=val)))
        if material_ids:
            conditions.append(
                Filter(
                    should=[
                        FieldCondition(key="material_id", match=MatchValue(value=mid))
                        for mid in material_ids
                    ]
                )
            )
        return Filter(must=conditions) if conditions else None

    @staticmethod
    def _make_id(material_id: str, chunk_index: int) -> str:
        import uuid
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{material_id}_{chunk_index}"))
