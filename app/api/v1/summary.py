from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.core.deps import get_embedding_client, get_llm_client, verify_api_key
from app.workflows.summary_workflow import build_summary_graph
from ai_core.vectorstore.qdrant_wrapper import QdrantWrapper

router = APIRouter()

ALLOWED_TYPES = {"overview", "keywords", "flashcard"}


class SummaryRequest(BaseModel):
    material_id: str
    course_id: int | None = None
    summary_type: str = "overview"


class SummaryResponse(BaseModel):
    material_id: str
    summary_type: str
    result: dict


@router.post("/generate", response_model=SummaryResponse, dependencies=[Depends(verify_api_key)])
async def generate_summary(req: SummaryRequest):
    if req.summary_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 요약 유형: {req.summary_type}. 허용: {ALLOWED_TYPES}")

    qdrant = QdrantWrapper(
        url=settings.QDRANT_URL,
        collection=settings.QDRANT_COLLECTION,
        vector_size=settings.EMBEDDING_DIM,
    )

    graph = build_summary_graph(
        qdrant=qdrant,
        embed_client=get_embedding_client(),
        llm_client=get_llm_client(),
        retrieval_top_k=20,
        max_tokens=settings.LLM_MAX_TOKENS,
    )

    result_state = await graph.ainvoke({
        "material_id": req.material_id,
        "course_id": req.course_id,
        "summary_type": req.summary_type,
        "chunks": [],
        "result": {},
    })

    result = result_state.get("result", {})
    if not result:
        raise HTTPException(status_code=422, detail="요약 생성 실패. 자료가 READY 상태인지 확인하세요.")

    return SummaryResponse(
        material_id=req.material_id,
        summary_type=req.summary_type,
        result=result,
    )
