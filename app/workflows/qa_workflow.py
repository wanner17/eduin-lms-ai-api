from typing import TypedDict
from langgraph.graph import StateGraph

from ai_core.clients.base import BaseLLMClient, BaseEmbeddingClient, BaseRerankerClient
from ai_core.rag.retriever import LMSRetriever
from ai_core.rag.reranker import Reranker
from ai_core.rag.citation import build_citation_prompt, extract_citations, Citation
from ai_core.vectorstore.qdrant_wrapper import QdrantWrapper


class QAState(TypedDict):
    query: str
    course_id: int | None
    lecture_id: int | None
    material_ids: list[int] | None
    retrieved_chunks: list[dict]
    reranked_chunks: list[dict]
    answer: str
    citations: list[Citation]


def build_qa_graph(
    qdrant: QdrantWrapper,
    embed_client: BaseEmbeddingClient,
    reranker_client: BaseRerankerClient,
    llm_client: BaseLLMClient,
    retrieval_top_k: int = 20,
    reranker_top_n: int = 5,
    max_tokens: int = 2048,
):
    retriever = LMSRetriever(qdrant=qdrant, embed_client=embed_client)
    reranker = Reranker(client=reranker_client)

    async def retrieve_node(state: QAState) -> QAState:
        chunks = await retriever.retrieve(
            query=state["query"],
            course_id=state.get("course_id"),
            lecture_id=state.get("lecture_id"),
            material_ids=state.get("material_ids"),
            top_k=retrieval_top_k,
        )
        return {**state, "retrieved_chunks": chunks}

    async def rerank_node(state: QAState) -> QAState:
        chunks = await reranker.rerank(
            query=state["query"],
            chunks=state["retrieved_chunks"],
            top_n=reranker_top_n,
        )
        return {**state, "reranked_chunks": chunks}

    async def generate_node(state: QAState) -> QAState:
        chunks = state["reranked_chunks"]
        if not chunks:
            return {
                **state,
                "answer": "관련 강의자료를 찾지 못했습니다. 자료가 업로드되었는지 확인해주세요.",
                "citations": [],
            }
        prompt = build_citation_prompt(state["query"], chunks)
        answer = await llm_client.generate(prompt, max_tokens=max_tokens)
        citations = extract_citations(answer, chunks)
        return {**state, "answer": answer, "citations": citations}

    g = StateGraph(QAState)
    g.add_node("retrieve", retrieve_node)
    g.add_node("rerank", rerank_node)
    g.add_node("generate", generate_node)

    g.set_entry_point("retrieve")
    g.add_edge("retrieve", "rerank")
    g.add_edge("rerank", "generate")
    g.set_finish_point("generate")

    return g.compile()
