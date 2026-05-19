import re
from dataclasses import dataclass


@dataclass
class Citation:
    index: int
    material_name: str
    page: int
    section: str
    text: str


_MAX_CHUNK_CHARS = 400   # per-chunk text limit
_MAX_TOTAL_CHARS = 3000  # total context hard cap


def build_citation_prompt(query: str, chunks: list[dict]) -> str:
    ctx = ""
    total = 0
    for i, c in enumerate(chunks, start=1):
        material = c.get("file_name", "알 수 없는 자료")
        page = c.get("page", "?")
        section = c.get("section_title", "")
        section_str = f" — {section}" if section else ""
        text = c["text"][:_MAX_CHUNK_CHARS]
        entry = f"[출처{i}] {material} p.{page}{section_str}\n{text}\n\n"
        if total + len(entry) > _MAX_TOTAL_CHARS:
            break
        ctx += entry
        total += len(entry)

    return f"""아래 강의자료를 바탕으로 질문에 정확히 답하세요.
반드시 [출처N] 형태로 근거를 표시하세요.
강의자료에 없는 내용은 추측하거나 답변하지 마세요.

{ctx.strip()}

질문: {query}
답변:"""


def extract_citations(answer: str, chunks: list[dict]) -> list[Citation]:
    cited_indices = [int(m) - 1 for m in re.findall(r"\[출처(\d+)\]", answer)]
    citations = []
    seen = set()
    for idx in cited_indices:
        if idx in seen or idx >= len(chunks):
            continue
        seen.add(idx)
        c = chunks[idx]
        citations.append(Citation(
            index=idx + 1,
            material_name=c.get("file_name", ""),
            page=c.get("page", 0),
            section=c.get("section_title", ""),
            text=c.get("text", ""),
        ))
    return citations
