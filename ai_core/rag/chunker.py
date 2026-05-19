from dataclasses import dataclass, field


@dataclass
class Page:
    number: int
    text: str
    section_title: str = ""


@dataclass
class Chunk:
    text: str
    page: int
    chunk_index: int
    material_id: str
    section_title: str = ""
    metadata: dict = field(default_factory=dict)


class HierarchicalChunker:
    def __init__(self, chunk_size: int = 512, overlap: int = 64, min_merge_size: int = 200):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.min_merge_size = min_merge_size

    def chunk(self, pages: list[Page], material_id: str) -> list[Chunk]:
        chunks = []
        pending = ""  # 너무 짧은 페이지 병합 버퍼

        for page in pages:
            text = page.text.strip()
            if not text:
                continue

            # 짧은 페이지 → 이전 버퍼와 병합
            if len(text) < self.min_merge_size:
                pending += " " + text
                continue

            # 쌓인 버퍼 먼저 flush
            if pending.strip():
                chunks.append(Chunk(
                    text=pending.strip(),
                    page=page.number,
                    chunk_index=len(chunks),
                    material_id=material_id,
                    section_title=page.section_title,
                ))
                pending = ""

            # 페이지 크기에 따라 통째로 or 분할
            if len(text) <= self.chunk_size:
                chunks.append(Chunk(
                    text=text,
                    page=page.number,
                    chunk_index=len(chunks),
                    material_id=material_id,
                    section_title=page.section_title,
                ))
            else:
                for i, part in enumerate(self._sliding_window(text)):
                    chunks.append(Chunk(
                        text=part,
                        page=page.number,
                        chunk_index=len(chunks),
                        material_id=material_id,
                        section_title=page.section_title,
                        metadata={"split_index": i},
                    ))

        # 남은 버퍼
        if pending.strip() and chunks:
            chunks.append(Chunk(
                text=pending.strip(),
                page=pages[-1].number if pages else 0,
                chunk_index=len(chunks),
                material_id=material_id,
            ))

        return chunks

    def _sliding_window(self, text: str) -> list[str]:
        parts = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            parts.append(text[start:end])
            start += self.chunk_size - self.overlap
        return parts
