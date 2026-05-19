import json
import re
from typing import TypedDict

from langgraph.graph import StateGraph

from ai_core.clients.base import BaseLLMClient, BaseEmbeddingClient
from ai_core.vectorstore.qdrant_wrapper import QdrantWrapper


class SummaryState(TypedDict):
    material_id: str
    course_id: int | None
    summary_type: str   # overview / keywords / flashcard
    chunks: list[dict]
    result: dict


PROMPTS = {
    "overview": """당신은 교육 자료 요약 전문가입니다. 아래 강의자료를 바탕으로 핵심 내용을 요약하세요.

강의자료:
{context}

다음 JSON 형식으로만 응답하세요:
{{
  "title": "단원/주제 제목",
  "summary": "전체 내용 요약 (3-5문장)",
  "sections": [
    {{
      "heading": "소제목",
      "points": ["핵심 포인트1", "핵심 포인트2"]
    }}
  ],
  "key_concepts": ["핵심개념1", "핵심개념2", "핵심개념3"]
}}""",

    "keywords": """당신은 교육 자료 분석 전문가입니다. 아래 강의자료에서 시험에 나올 핵심 키워드와 개념을 추출하세요.

강의자료:
{context}

다음 JSON 형식으로만 응답하세요:
{{
  "keywords": [
    {{
      "term": "용어",
      "definition": "정의 (1-2문장)",
      "importance": "high|medium|low",
      "source_page": 1
    }}
  ]
}}""",

    "flashcard": """당신은 교육 자료 전문가입니다. 아래 강의자료를 바탕으로 암기용 플래시카드를 생성하세요.

강의자료:
{context}

다음 JSON 형식으로만 응답하세요:
{{
  "flashcards": [
    {{
      "front": "질문 또는 용어",
      "back": "답변 또는 정의",
      "hint": "힌트 (선택)",
      "source_page": 1
    }}
  ]
}}""",
}


def _build_context(chunks: list[dict]) -> str:
    ctx = ""
    for c in chunks:
        page = c.get("page", "?")
        text = c.get("text", "")
        ctx += f"[p.{page}] {text}\n\n"
    return ctx.strip()


def _extract_json_obj(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group())
    return json.loads(text)


def build_summary_graph(
    qdrant: QdrantWrapper,
    embed_client: BaseEmbeddingClient,
    llm_client: BaseLLMClient,
    retrieval_top_k: int = 20,
    max_tokens: int = 4096,
):
    async def retrieve_node(state: SummaryState) -> SummaryState:
        vectors = await embed_client.embed(["핵심 개념 주요 내용 요약 정리"])
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

    async def generate_node(state: SummaryState) -> SummaryState:
        chunks = state["chunks"]
        if not chunks:
            return {**state, "result": {}}

        context = _build_context(chunks)
        prompt_template = PROMPTS.get(state["summary_type"], PROMPTS["overview"])
        prompt = prompt_template.format(context=context)

        raw = await llm_client.generate(prompt, max_tokens=max_tokens, temperature=0.2)

        try:
            result = _extract_json_obj(raw)
        except Exception:
            result = {"raw": raw}

        return {**state, "result": result}

    g = StateGraph(SummaryState)
    g.add_node("retrieve", retrieve_node)
    g.add_node("generate", generate_node)
    g.set_entry_point("retrieve")
    g.add_edge("retrieve", "generate")
    g.set_finish_point("generate")

    return g.compile()
