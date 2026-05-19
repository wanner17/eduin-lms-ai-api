from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.core.deps import get_embedding_client, get_llm_client, verify_api_key
from app.workflows.quiz_workflow import build_quiz_graph
from ai_core.vectorstore.qdrant_wrapper import QdrantWrapper

router = APIRouter()

ALLOWED_TYPES = {"mcq", "ox", "short", "essay"}
ALLOWED_DIFFICULTIES = {"easy", "medium", "hard"}


class QuizGenerateRequest(BaseModel):
    material_id: str
    course_id: int | None = None
    quiz_types: list[str] = ["mcq"]
    count: int = 5
    difficulty: str = "medium"


class QuizItem(BaseModel):
    quiz_type: str
    difficulty: str
    question: str
    options: dict | None = None       # mcq 보기
    answer: str | None = None
    explanation: str | None = None
    scoring_criteria: str | None = None  # 서술형 채점기준
    keywords: list[str] = []
    source_page: int | None = None
    material_id: str


class QuizGenerateResponse(BaseModel):
    material_id: str
    total: int
    quizzes: list[QuizItem]


@router.post("/generate", response_model=QuizGenerateResponse, dependencies=[Depends(verify_api_key)])
async def generate_quiz(req: QuizGenerateRequest):
    invalid_types = set(req.quiz_types) - ALLOWED_TYPES
    if invalid_types:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 문제 유형: {invalid_types}")

    if req.difficulty not in ALLOWED_DIFFICULTIES:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 난이도: {req.difficulty}")

    if not 1 <= req.count <= 20:
        raise HTTPException(status_code=400, detail="count는 1~20 사이")

    qdrant = QdrantWrapper(
        url=settings.QDRANT_URL,
        collection=settings.QDRANT_COLLECTION,
        vector_size=settings.EMBEDDING_DIM,
    )

    per_type = max(1, req.count // len(req.quiz_types))
    all_questions = []

    for quiz_type in req.quiz_types:
        graph = build_quiz_graph(
            qdrant=qdrant,
            embed_client=get_embedding_client(),
            llm_client=get_llm_client(),
            retrieval_top_k=15,
            max_tokens=settings.LLM_MAX_TOKENS,
        )
        result = await graph.ainvoke({
            "material_id": req.material_id,
            "course_id": req.course_id,
            "quiz_type": quiz_type,
            "difficulty": req.difficulty,
            "count": per_type,
            "chunks": [],
            "questions": [],
        })
        all_questions.extend(result["questions"])

    if not all_questions:
        raise HTTPException(status_code=422, detail="문제 생성 실패. 자료가 READY 상태인지 확인하세요.")

    quizzes = []
    for q in all_questions:
        quizzes.append(QuizItem(
            quiz_type=q.get("quiz_type", "mcq"),
            difficulty=q.get("difficulty", req.difficulty),
            question=q.get("question", ""),
            options=q.get("options"),
            answer=q.get("answer"),
            explanation=q.get("explanation"),
            scoring_criteria=q.get("scoring_criteria"),
            keywords=q.get("keywords", []),
            source_page=q.get("source_page"),
            material_id=req.material_id,
        ))

    return QuizGenerateResponse(
        material_id=req.material_id,
        total=len(quizzes),
        quizzes=quizzes,
    )
