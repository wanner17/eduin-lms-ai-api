import uuid
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.config import settings
from app.core.deps import get_embedding_client, get_reranker_client, get_llm_client, verify_api_key
from app.workflows.qa_workflow import build_qa_graph
from ai_core.vectorstore.qdrant_wrapper import QdrantWrapper
from ai_core.rag.citation import Citation

router = APIRouter()


class CitationSchema(BaseModel):
    index: int
    material_name: str
    page: int
    section: str
    text: str


class QAAskRequest(BaseModel):
    query: str
    course_id: int | None = None
    lecture_id: int | None = None
    material_ids: list[int] | None = None
    student_id: str | None = None
    session_id: str | None = None


class QAAskResponse(BaseModel):
    answer: str
    citations: list[CitationSchema]
    session_id: str


@router.post("/ask", response_model=QAAskResponse, dependencies=[Depends(verify_api_key)])
async def ask(req: QAAskRequest):
    qdrant = QdrantWrapper(
        url=settings.QDRANT_URL,
        collection=settings.QDRANT_COLLECTION,
        vector_size=settings.EMBEDDING_DIM,
    )

    graph = build_qa_graph(
        qdrant=qdrant,
        embed_client=get_embedding_client(),
        reranker_client=get_reranker_client(),
        llm_client=get_llm_client(),
        retrieval_top_k=settings.RETRIEVAL_TOP_K,
        reranker_top_n=settings.RERANKER_TOP_N,
        max_tokens=settings.LLM_MAX_TOKENS,
    )

    result = await graph.ainvoke({
        "query": req.query,
        "course_id": req.course_id,
        "lecture_id": req.lecture_id,
        "material_ids": req.material_ids,
        "retrieved_chunks": [],
        "reranked_chunks": [],
        "answer": "",
        "citations": [],
    })

    return QAAskResponse(
        answer=result["answer"],
        citations=[
            CitationSchema(
                index=c.index,
                material_name=c.material_name,
                page=c.page,
                section=c.section,
                text=c.text,
            )
            for c in result["citations"]
        ],
        session_id=req.session_id or str(uuid.uuid4()),
    )
