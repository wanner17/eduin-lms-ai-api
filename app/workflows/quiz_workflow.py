import json
import re
from typing import TypedDict

from langgraph.graph import StateGraph

from ai_core.clients.base import BaseLLMClient, BaseEmbeddingClient
from ai_core.vectorstore.qdrant_wrapper import QdrantWrapper


class QuizState(TypedDict):
    material_id: str
    course_id: int | None
    quiz_type: str        # mcq / ox / short / essay
    difficulty: str       # easy / medium / hard
    count: int
    chunks: list[dict]
    questions: list[dict]


PROMPTS = {
    "mcq": """당신은 교육 문제 출제 전문가입니다. 아래 강의자료를 바탕으로 객관식(4지선다) 문제를 정확히 {count}개 생성하세요.
난이도: {difficulty}
※ 반드시 {count}개를 모두 생성해야 합니다. {count}개 미만이면 안 됩니다.

강의자료:
{context}

출력 규칙:
- JSON 배열만 출력하세요. 다른 텍스트 없이 배열로만 응답하세요.
- 배열 원소 수: 정확히 {count}개
- 각 문제는 서로 다른 주제/개념을 다루세요.

[
  {{
    "question": "문제 내용",
    "options": {{"A": "보기1", "B": "보기2", "C": "보기3", "D": "보기4"}},
    "answer": "A",
    "explanation": "왜 A가 정답인지 설명",
    "keywords": ["키워드1", "키워드2"],
    "source_page": 1
  }}
]""",

    "ox": """당신은 교육 문제 출제 전문가입니다. 아래 강의자료를 바탕으로 OX 문제를 정확히 {count}개 생성하세요.
난이도: {difficulty}
※ 반드시 {count}개를 모두 생성해야 합니다. {count}개 미만이면 안 됩니다.

강의자료:
{context}

출력 규칙:
- JSON 배열만 출력하세요. 다른 텍스트 없이 배열로만 응답하세요.
- 배열 원소 수: 정확히 {count}개
- O와 X 문제를 골고루 섞으세요.

[
  {{
    "question": "명제 형태의 문제 (O인지 X인지 판단하세요)",
    "answer": "O",
    "explanation": "해설",
    "keywords": ["키워드1"],
    "source_page": 1
  }}
]""",

    "short": """당신은 교육 문제 출제 전문가입니다. 아래 강의자료를 바탕으로 단답형 문제를 정확히 {count}개 생성하세요.
난이도: {difficulty}
※ 반드시 {count}개를 모두 생성해야 합니다. {count}개 미만이면 안 됩니다.

강의자료:
{context}

출력 규칙:
- JSON 배열만 출력하세요. 다른 텍스트 없이 배열로만 응답하세요.
- 배열 원소 수: 정확히 {count}개
- 각 문제는 서로 다른 개념을 물어보세요.

[
  {{
    "question": "빈칸이나 단답으로 답할 수 있는 문제",
    "answer": "정답 (간결하게)",
    "explanation": "해설",
    "keywords": ["키워드1"],
    "source_page": 1
  }}
]""",

    "essay": """당신은 교육 문제 출제 전문가입니다. 아래 강의자료를 바탕으로 서술형 문제를 정확히 {count}개 생성하세요.
난이도: {difficulty}
※ 반드시 {count}개를 모두 생성해야 합니다. {count}개 미만이면 안 됩니다.

강의자료:
{context}

출력 규칙:
- JSON 배열만 출력하세요. 다른 텍스트 없이 배열로만 응답하세요.
- 배열 원소 수: 정확히 {count}개
- 각 문제는 깊은 이해와 서술을 요구하는 형태로 만드세요.

[
  {{
    "question": "서술형 문제 내용",
    "answer": "모범 답안 (2-5문장)",
    "explanation": "해설 및 핵심 포인트",
    "scoring_criteria": "채점기준 (항목별 배점 포함)",
    "keywords": ["키워드1", "키워드2"],
    "source_page": 1
  }}
]""",
}


def _build_context(chunks: list[dict]) -> str:
    ctx = ""
    for c in chunks:
        page = c.get("page", "?")
        text = c.get("text", "")
        ctx += f"[p.{page}] {text}\n\n"
    return ctx.strip()


def _extract_json(text: str) -> list[dict]:
    # LLM 응답에서 JSON 배열 추출
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        return json.loads(match.group())
    return json.loads(text)


def build_quiz_graph(
    qdrant: QdrantWrapper,
    embed_client: BaseEmbeddingClient,
    llm_client: BaseLLMClient,
    retrieval_top_k: int = 15,
    max_tokens: int = 4096,
):
    async def retrieve_node(state: QuizState) -> QuizState:
        # material_id 기반으로 핵심 청크 검색
        # 빈 쿼리 대신 "핵심 개념 요약" 으로 검색
        vectors = await embed_client.embed(["핵심 개념 주요 내용 요약"])
        query_vec = vectors[0]

        filter_params = {"material_id": state["material_id"]}
        if state.get("course_id"):
            filter_params["course_id"] = state["course_id"]

        chunks = qdrant.search(
            vector=query_vec,
            filter_params=filter_params,
            top_k=retrieval_top_k,
        )
        return {**state, "chunks": chunks}

    async def generate_node(state: QuizState) -> QuizState:
        chunks = state["chunks"]
        if not chunks:
            return {**state, "questions": []}

        context = _build_context(chunks)
        prompt_template = PROMPTS.get(state["quiz_type"], PROMPTS["mcq"])
        target_count = state["count"]
        # scale max_tokens with count so long lists don't get truncated
        dynamic_max_tokens = min(max_tokens, max(2048, target_count * 600))

        questions: list[dict] = []
        remaining = target_count

        for attempt in range(3):
            prompt = prompt_template.format(
                count=remaining,
                difficulty=state["difficulty"],
                context=context,
            )
            raw = await llm_client.generate(
                prompt, max_tokens=dynamic_max_tokens, temperature=0.3 + attempt * 0.1
            )
            try:
                parsed = _extract_json(raw)
                for q in parsed:
                    q["quiz_type"] = state["quiz_type"]
                    q["difficulty"] = state["difficulty"]
                    q["material_id"] = state["material_id"]
                questions.extend(parsed)
            except Exception:
                pass

            if len(questions) >= target_count:
                break
            remaining = target_count - len(questions)

        return {**state, "questions": questions[:target_count]}

    g = StateGraph(QuizState)
    g.add_node("retrieve", retrieve_node)
    g.add_node("generate", generate_node)
    g.set_entry_point("retrieve")
    g.add_edge("retrieve", "generate")
    g.set_finish_point("generate")

    return g.compile()
