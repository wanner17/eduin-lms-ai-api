# LMS AI API — 전체 아키텍처 설계

---

## 1. 전체 시스템 아키텍처

```
[기존 LMS Frontend]
        ↓
[기존 LMS Backend]  →  REST/HTTP  →  [LMS AI API Server]
                                              ↓
                              ┌───────────────────────────┐
                              │     ai-core (shared lib)  │
                              │  embed / rerank / llm / rag│
                              └───────────────────────────┘
                                     ↓         ↓         ↓
                              [Embed Server] [Reranker] [LLM Server]
                              (BGE-M3)      (BGE-R)    (Qwen/llama.cpp)
                                              ↓
                              [Qdrant]   [PostgreSQL]   [Redis]
```

---

## 2. 디렉토리 구조

```
eduin-lms-ai-api/
├── app/
│   ├── main.py
│   ├── api/
│   │   └── v1/
│   │       ├── ingest.py        # 자료 업로드
│   │       ├── qa.py            # 질의응답
│   │       ├── quiz.py          # 문제 생성
│   │       ├── summary.py       # 요약/시험대비
│   │       ├── tutor.py         # AI 튜터
│   │       └── admin.py         # 관리자
│   ├── core/
│   │   ├── config.py            # 환경별 설정
│   │   └── deps.py              # DI
│   ├── domain/                  # LMS 도메인
│   │   ├── models/              # PostgreSQL ORM
│   │   │   ├── course.py
│   │   │   ├── lecture.py
│   │   │   ├── material.py
│   │   │   ├── quiz.py
│   │   │   └── student_progress.py
│   │   ├── services/            # LMS 비즈니스 로직
│   │   │   ├── ingest_service.py
│   │   │   ├── qa_service.py
│   │   │   ├── quiz_service.py
│   │   │   └── tutor_service.py
│   │   └── schemas/             # Pydantic
│   ├── workflows/               # LangGraph
│   │   ├── qa_workflow.py
│   │   ├── quiz_workflow.py
│   │   └── tutor_workflow.py
│   └── workers/                 # Celery tasks
│       ├── celery_app.py
│       ├── ingest_worker.py
│       └── embed_worker.py
│
├── ai_core/                     # 공통 AI Core (패키지화 가능)
│   ├── clients/
│   │   ├── base.py
│   │   ├── llm_client.py
│   │   ├── embedding_client.py
│   │   └── reranker_client.py
│   ├── rag/
│   │   ├── chunker.py
│   │   ├── retriever.py
│   │   ├── reranker.py
│   │   └── citation.py
│   └── vectorstore/
│       └── qdrant_wrapper.py
│
├── configs/
│   ├── .env.local
│   ├── .env.production
│   └── settings.py
│
├── docker/
│   ├── docker-compose.yml
│   ├── docker-compose.local.yml
│   └── Dockerfile
│
└── tests/
```

---

## 3. AI Core vs LMS Domain 분리 기준

### ai_core (모델 무관, 도메인 무관)
- `embedding_client` — embed text
- `reranker_client` — score passages
- `llm_client` — generate text
- `chunker` — split docs
- `retriever` — vector search
- `citation` — extract source info
- `qdrant_wrapper` — collection CRUD

### domain/ (LMS 특화)
- course/lecture/material 구조
- quiz 생성 로직 (문제 타입별 프롬프트)
- student progress tracking
- tutor context (오답 히스토리)
- ingestion → material 연결

> **규칙**: ai_core는 LMS 개념 몰라야 한다. `embed(texts)` 반환, LMS가 어디 쓸지 결정.

---

## 4. Abstraction Layer

```python
# ai_core/clients/base.py
from abc import ABC, abstractmethod

class BaseLLMClient(ABC):
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str: ...

class BaseEmbeddingClient(ABC):
    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]: ...

class BaseRerankerClient(ABC):
    @abstractmethod
    async def rerank(self, query: str, passages: list[str]) -> list[float]: ...
```

```python
# ai_core/clients/llm_client.py
import httpx
from .base import BaseLLMClient

class LlamaCppClient(BaseLLMClient):
    def __init__(self, endpoint: str, model: str = None):
        self.endpoint = endpoint
        self.model = model

    async def generate(self, prompt: str, **kwargs) -> str:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{self.endpoint}/completion",
                json={"prompt": prompt, "max_tokens": kwargs.get("max_tokens", 1024)},
                timeout=60
            )
            return r.json()["content"]

class OpenAICompatClient(BaseLLMClient):
    """fallback for local test model (ollama, lm-studio)"""
    def __init__(self, endpoint: str, model: str):
        self.endpoint = endpoint
        self.model = model

    async def generate(self, prompt: str, **kwargs) -> str:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{self.endpoint}/v1/chat/completions",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}]
                }
            )
            return r.json()["choices"][0]["message"]["content"]
```

```python
# ai_core/clients/embedding_client.py
class BGEEmbeddingClient(BaseEmbeddingClient):
    def __init__(self, endpoint: str):
        self.endpoint = endpoint

    async def embed(self, texts: list[str]) -> list[list[float]]:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{self.endpoint}/embed",
                json={"texts": texts},
                timeout=30
            )
            return r.json()["embeddings"]
```

```python
# ai_core/clients/reranker_client.py
class BGERerankerClient(BaseRerankerClient):
    def __init__(self, endpoint: str):
        self.endpoint = endpoint

    async def rerank(self, query: str, passages: list[str]) -> list[float]:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{self.endpoint}/rerank",
                json={"query": query, "passages": passages},
                timeout=30
            )
            return r.json()["scores"]
```

```python
# app/core/deps.py — DI로 client 주입
from ai_core.clients.llm_client import LlamaCppClient
from ai_core.clients.embedding_client import BGEEmbeddingClient
from ai_core.clients.reranker_client import BGERerankerClient
from app.core.config import settings

def get_llm_client() -> BaseLLMClient:
    return LlamaCppClient(endpoint=settings.LLM_ENDPOINT)

def get_embedding_client() -> BaseEmbeddingClient:
    return BGEEmbeddingClient(endpoint=settings.EMBEDDING_ENDPOINT)

def get_reranker_client() -> BaseRerankerClient:
    return BGERerankerClient(endpoint=settings.RERANKER_ENDPOINT)
```

---

## 5. 환경별 Config 전략

```python
# app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ENV: str = "local"

    # AI endpoints — 이것만 바꾸면 환경 전환
    LLM_ENDPOINT: str = "http://localhost:8080"
    EMBEDDING_ENDPOINT: str = "http://localhost:8001"
    RERANKER_ENDPOINT: str = "http://localhost:8002"

    # DB
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost/lms_ai"
    QDRANT_URL: str = "http://localhost:6333"
    REDIS_URL: str = "redis://localhost:6379"

    # LLM params
    LLM_MODEL: str = "qwen2.5-7b"
    LLM_MAX_TOKENS: int = 2048

    # LMS 연동
    LMS_API_KEY: str = "changeme"
    LMS_WEBHOOK_URL: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
```

```bash
# .env.local
LLM_ENDPOINT=http://gpu-server:8080
EMBEDDING_ENDPOINT=http://gpu-server:8001
RERANKER_ENDPOINT=http://gpu-server:8002
QDRANT_URL=http://localhost:6333
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/lms_ai_dev

# .env.production
LLM_ENDPOINT=http://internal-llm:8080
EMBEDDING_ENDPOINT=http://internal-embed:8001
RERANKER_ENDPOINT=http://internal-rerank:8002
QDRANT_URL=http://qdrant-service:6333
DATABASE_URL=postgresql+asyncpg://user:pass@db-server/lms_ai
```

> 로직 코드 변경 없이 env 파일만 교체. 배포 시 `--env-file .env.production`

---

## 6. Ingestion Pipeline

```
[파일 업로드 API]
      ↓
[파일 저장 + DB material 레코드 생성]
      ↓
[Celery task 발행 → Redis queue]
      ↓
[ingest_worker]
      ↓
┌─────────────────────────────────────────────┐
│ 1. 파싱: PDF→PyMuPDF / PPTX→python-pptx /  │
│         DOCX→python-docx                   │
│ 2. 페이지/슬라이드 단위 추출               │
│ 3. chunking                                │
│ 4. embedding (→ embedding_server)          │
│ 5. Qdrant upsert (with metadata)           │
│ 6. DB status 업데이트                      │
└─────────────────────────────────────────────┘
      ↓
[status: READY]
```

```python
# app/workers/ingest_worker.py
@celery_app.task
def process_material(material_id: int):
    material = db.get(Material, material_id)

    # 파싱
    pages = parse_file(material.file_path, material.file_type)

    # chunking
    chunks = chunker.chunk(pages, material_id=material_id)

    # embed
    embeddings = embedding_client.embed([c.text for c in chunks])

    # qdrant upsert
    qdrant.upsert_chunks(
        collection="lms_materials",
        chunks=chunks,
        embeddings=embeddings,
        metadata={
            "material_id": material_id,
            "course_id": material.course_id,
            "lecture_id": material.lecture_id,
        }
    )

    material.status = "READY"
    db.commit()
```

---

## 7. Chunking 전략

```python
# ai_core/rag/chunker.py
from dataclasses import dataclass

@dataclass
class Chunk:
    text: str
    page: int           # 페이지/슬라이드 번호
    material_id: int
    section_title: str  # 섹션/챕터명 (있으면)
    chunk_index: int
    metadata: dict

class HierarchicalChunker:
    def __init__(self, chunk_size=512, overlap=64):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, pages: list, **kwargs) -> list[Chunk]:
        chunks = []
        for page in pages:
            text = page.text
            if len(text) <= self.chunk_size:
                # 짧은 페이지 → 통째로
                chunks.append(Chunk(text=text, page=page.number, ...))
            else:
                # 분할, 앞 청크 끝 overlap 유지
                for i, c in enumerate(self._split(text)):
                    chunks.append(Chunk(text=c, page=page.number, chunk_index=i, ...))
        return chunks
```

**전략 요약:**
- PDF: PyMuPDF로 페이지 단위 추출 → chunk
- PPTX: 슬라이드 단위 추출 → 슬라이드 번호 보존
- chunk_size=512 token, overlap=64 token
- 짧은 페이지(<200 token) → 이웃 페이지 병합
- 섹션 제목 감지 시 metadata에 포함 (citation에 활용)

---

## 8. Retrieval 전략

```python
# ai_core/rag/retriever.py
class LMSRetriever:
    def __init__(self, qdrant, embed_client):
        self.qdrant = qdrant
        self.embed = embed_client

    async def retrieve(
        self,
        query: str,
        course_id: int = None,
        lecture_id: int = None,
        material_ids: list[int] = None,
        top_k: int = 20
    ) -> list:
        query_vec = await self.embed.embed([query])

        # filter → 해당 강의/과목으로 검색 범위 제한
        filters = build_qdrant_filter(
            course_id=course_id,
            lecture_id=lecture_id,
            material_ids=material_ids
        )

        return self.qdrant.search(
            collection="lms_materials",
            vector=query_vec[0],
            filter=filters,
            top_k=top_k
        )
```

> **핵심**: filter 필수. course_id/lecture_id 없이 전체 검색 → 다른 강의 자료 혼입 위험.

---

## 9. Reranking 전략

```python
# ai_core/rag/reranker.py
class Reranker:
    def __init__(self, client):
        self.client = client

    async def rerank(self, query: str, chunks: list, top_n: int = 5) -> list:
        scores = await self.client.rerank(
            query=query,
            passages=[c.text for c in chunks]
        )
        ranked = sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)
        return [chunk for chunk, _ in ranked[:top_n]]
```

> retrieval top_k=20 → rerank → top_n=5 → LLM

---

## 10. Citation 설계

```python
# ai_core/rag/citation.py
from dataclasses import dataclass

@dataclass
class Citation:
    material_name: str
    page: int
    section: str
    chunk_text: str
    score: float

def build_citation_prompt(query: str, chunks: list) -> str:
    ctx = ""
    for i, c in enumerate(chunks):
        ctx += f"[출처{i+1}] {c.material_name} p.{c.page}\n{c.text}\n\n"

    return f"""다음 강의자료를 바탕으로 질문에 답하세요.
답변 시 반드시 [출처N] 형태로 근거를 표시하세요.
출처 외 내용은 추측하지 마세요.

{ctx}

질문: {query}
답변:"""
```

**응답 구조:**
```json
{
  "answer": "딥러닝은 신경망 기반 학습입니다[출처1]. 역전파 알고리즘으로 학습[출처2].",
  "citations": [
    {"material": "머신러닝개론.pdf", "page": 12, "section": "2.3 딥러닝", "text": "딥러닝은..."},
    {"material": "머신러닝개론.pdf", "page": 15, "section": "2.4 역전파", "text": "역전파는..."}
  ]
}
```

---

## 11. LangGraph Workflow

### QA Workflow

```python
# app/workflows/qa_workflow.py
from langgraph.graph import StateGraph
from typing import TypedDict

class QAState(TypedDict):
    query: str
    course_id: int
    lecture_id: int
    retrieved_chunks: list
    reranked_chunks: list
    citations: list
    answer: str

def build_qa_graph():
    g = StateGraph(QAState)

    g.add_node("retrieve", retrieve_node)
    g.add_node("rerank", rerank_node)
    g.add_node("generate", generate_node)

    g.set_entry_point("retrieve")
    g.add_edge("retrieve", "rerank")
    g.add_edge("rerank", "generate")
    g.set_finish_point("generate")

    return g.compile()

async def retrieve_node(state: QAState) -> QAState:
    chunks = await retriever.retrieve(
        query=state["query"],
        course_id=state["course_id"],
        lecture_id=state["lecture_id"]
    )
    return {**state, "retrieved_chunks": chunks}

async def rerank_node(state: QAState) -> QAState:
    chunks = await reranker.rerank(state["query"], state["retrieved_chunks"])
    return {**state, "reranked_chunks": chunks}

async def generate_node(state: QAState) -> QAState:
    prompt = build_citation_prompt(state["query"], state["reranked_chunks"])
    answer = await llm.generate(prompt)
    citations = extract_citations(answer, state["reranked_chunks"])
    return {**state, "answer": answer, "citations": citations}
```

### Quiz Workflow

```python
# app/workflows/quiz_workflow.py
class QuizState(TypedDict):
    material_id: int
    quiz_type: str       # mcq / ox / short / essay
    difficulty: str
    retrieved_chunks: list
    questions: list

def build_quiz_graph():
    g = StateGraph(QuizState)
    g.add_node("retrieve_key_content", retrieve_key_content_node)
    g.add_node("generate_questions", generate_questions_node)
    g.add_node("validate_questions", validate_questions_node)
    g.set_entry_point("retrieve_key_content")
    g.add_edge("retrieve_key_content", "generate_questions")
    g.add_edge("generate_questions", "validate_questions")
    g.set_finish_point("validate_questions")
    return g.compile()
```

**LangGraph 사용 위치 요약:**

| 기능 | 그래프 구조 |
|------|-----------|
| QA | retrieve → rerank → generate |
| Quiz | retrieve → generate → validate |
| Tutor | classify → retrieve → explain (분기) |
| Summary | chunk_select → summarize → format |

> 단순 체인이면 LangGraph 안 써도 됨. 분기/루프 있을 때 진가 발휘.

---

## 12. PostgreSQL Schema

```sql
-- 과목
CREATE TABLE courses (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    code VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 강의
CREATE TABLE lectures (
    id SERIAL PRIMARY KEY,
    course_id INTEGER REFERENCES courses(id),
    title VARCHAR(200),
    order_index INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 강의자료
CREATE TABLE materials (
    id SERIAL PRIMARY KEY,
    lecture_id INTEGER REFERENCES lectures(id),
    course_id INTEGER REFERENCES courses(id),
    file_name VARCHAR(300),
    file_path VARCHAR(500),
    file_type VARCHAR(20),     -- pdf/pptx/docx
    status VARCHAR(20) DEFAULT 'PENDING',  -- PENDING/PROCESSING/READY/FAILED
    chunk_count INTEGER,
    qdrant_collection VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 퀴즈
CREATE TABLE quizzes (
    id SERIAL PRIMARY KEY,
    material_id INTEGER REFERENCES materials(id),
    quiz_type VARCHAR(20),     -- mcq/ox/short/essay
    difficulty VARCHAR(10),    -- easy/medium/hard
    question TEXT,
    options JSONB,             -- mcq 보기
    answer TEXT,
    explanation TEXT,
    keywords TEXT[],
    scoring_criteria TEXT,     -- 서술형 채점기준
    source_page INTEGER,
    source_chunk_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 학생 진도
CREATE TABLE student_progress (
    id SERIAL PRIMARY KEY,
    student_id VARCHAR(100),
    course_id INTEGER REFERENCES courses(id),
    lecture_id INTEGER REFERENCES lectures(id),
    material_id INTEGER REFERENCES materials(id),
    last_accessed TIMESTAMP,
    quiz_attempts JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- AI 대화 로그
CREATE TABLE chat_sessions (
    id SERIAL PRIMARY KEY,
    student_id VARCHAR(100),
    course_id INTEGER REFERENCES courses(id),
    session_type VARCHAR(20),  -- qa/tutor/quiz
    messages JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 작업 큐 추적
CREATE TABLE ingest_jobs (
    id SERIAL PRIMARY KEY,
    material_id INTEGER REFERENCES materials(id),
    celery_task_id VARCHAR(200),
    status VARCHAR(20),
    error_message TEXT,
    started_at TIMESTAMP,
    finished_at TIMESTAMP
);
```

---

## 13. Qdrant Collection 전략

**단일 collection 전략 (MVP 추천):**

```python
collection_name = "lms_materials"

# payload 구조 (필터용)
payload = {
    "material_id": 42,
    "course_id": 5,
    "lecture_id": 12,
    "file_name": "딥러닝기초.pdf",
    "page": 7,
    "section": "2.3 활성화함수",
    "chunk_index": 2,
    "text": "ReLU는 음수를 0으로..."
}
```

```python
# ai_core/vectorstore/qdrant_wrapper.py
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Filter, FieldCondition, MatchValue,
    VectorParams, Distance
)

class QdrantWrapper:
    def __init__(self, url: str):
        self.client = QdrantClient(url=url)

    def ensure_collection(self, name: str, vector_size: int = 1024):
        if not self.client.collection_exists(name):
            self.client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
            )

    def search(self, collection: str, vector, filter_params: dict, top_k: int = 20):
        filters = self._build_filter(filter_params)
        return self.client.search(
            collection_name=collection,
            query_vector=vector,
            query_filter=filters,
            limit=top_k,
            with_payload=True
        )

    def _build_filter(self, params: dict) -> Filter:
        conditions = []
        for key, val in params.items():
            if val is not None:
                conditions.append(FieldCondition(key=key, match=MatchValue(value=val)))
        return Filter(must=conditions) if conditions else None
```

> 나중에 multi-tenant 납품 시 course_id별 별도 collection 전환 가능. wrapper가 있어서 코드 변경 최소화.

---

## 14. API Endpoint 설계

```
# Ingest
POST   /api/v1/ingest/materials              # 자료 업로드
GET    /api/v1/ingest/materials/{id}/status  # 처리 상태
DELETE /api/v1/ingest/materials/{id}         # 자료 삭제

# QA
POST   /api/v1/qa/ask                        # 질의응답
GET    /api/v1/qa/sessions/{session_id}      # 세션 조회

# Quiz
POST   /api/v1/quiz/generate                 # 문제 생성
GET    /api/v1/quiz/{quiz_id}                # 문제 조회
POST   /api/v1/quiz/grade                    # 서술형 채점

# Summary
POST   /api/v1/summary/generate              # 시험대비 자료 생성

# Tutor
POST   /api/v1/tutor/explain                 # 개념 설명
POST   /api/v1/tutor/wrong-answer            # 오답 분석

# Admin
GET    /api/v1/admin/health                  # 서버 상태
GET    /api/v1/admin/model-status            # 모델 서버 상태
GET    /api/v1/admin/jobs                    # 작업 큐 현황
POST   /api/v1/admin/collections/rebuild     # 컬렉션 재구축
```

### 요청/응답 예시

```json
// POST /api/v1/qa/ask — Request
{
  "query": "활성화 함수란?",
  "course_id": 5,
  "lecture_id": 12,
  "student_id": "student_001",
  "session_id": "sess_abc123"
}

// POST /api/v1/qa/ask — Response
{
  "answer": "활성화 함수는 뉴런 출력을 비선형 변환합니다[출처1].",
  "citations": [
    {
      "material_name": "딥러닝기초.pdf",
      "page": 7,
      "section": "2.3 활성화함수",
      "text": "활성화 함수는..."
    }
  ],
  "session_id": "sess_abc123"
}

// POST /api/v1/quiz/generate — Request
{
  "material_id": 42,
  "quiz_types": ["mcq", "ox", "short"],
  "count": 5,
  "difficulty": "medium"
}

// POST /api/v1/quiz/generate — Response
{
  "quizzes": [
    {
      "id": 101,
      "type": "mcq",
      "question": "ReLU의 특징은?",
      "options": ["A. 음수 → 0", "B. 음수 → -1", "C. 모두 양수", "D. 선형 변환"],
      "answer": "A",
      "explanation": "ReLU는 음수 입력을 0으로 변환합니다.",
      "source_page": 8,
      "difficulty": "medium"
    }
  ]
}
```

---

## 15. Worker 구조

```python
# app/workers/celery_app.py
from celery import Celery

app = Celery(
    "lms_ai",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1"
)

app.conf.task_routes = {
    "workers.ingest_worker.*": {"queue": "ingest"},
    "workers.embed_worker.*": {"queue": "embed"},
}
```

```bash
# 큐 분리 실행
celery worker -Q ingest --concurrency=2
celery worker -Q embed --concurrency=4
```

**비동기 처리 흐름:**
```
POST /ingest/materials
      ↓
[FastAPI] → 파일 저장 → DB 레코드 → celery.delay(material_id)
      ↓ 즉시 반환
{ "material_id": 42, "status": "PENDING" }

[Celery Worker] 백그라운드 처리
      ↓
GET /ingest/materials/42/status → { "status": "READY" }
```

---

## 16. Docker Compose 전략

```yaml
# docker-compose.yml (운영 기반)
version: "3.9"

services:
  api:
    build: .
    env_file: .env.production
    ports:
      - "8000:8000"
    depends_on: [db, redis, qdrant]

  worker-ingest:
    build: .
    command: celery -A app.workers.celery_app worker -Q ingest --concurrency=2
    env_file: .env.production
    depends_on: [redis, db]

  worker-embed:
    build: .
    command: celery -A app.workers.celery_app worker -Q embed --concurrency=4
    env_file: .env.production
    depends_on: [redis]

  db:
    image: postgres:16
    environment:
      POSTGRES_DB: lms_ai
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine

  qdrant:
    image: qdrant/qdrant:latest
    volumes:
      - qdrant_storage:/qdrant/storage
    ports:
      - "6333:6333"

volumes:
  pgdata:
  qdrant_storage:
```

```yaml
# docker-compose.local.yml (override)
services:
  api:
    env_file: .env.local
    volumes:
      - .:/app
    command: uvicorn app.main:app --reload --host 0.0.0.0

  worker-ingest:
    env_file: .env.local
    volumes:
      - .:/app
```

```bash
# 로컬 실행
docker compose -f docker-compose.yml -f docker-compose.local.yml up

# 운영 실행
docker compose up -d
```

---

## 17. LMS 연동 방식

```python
# app/core/deps.py — API Key 인증
async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != settings.LMS_API_KEY:
        raise HTTPException(status_code=401)
    return True
```

```python
# 기존 LMS Backend에서 호출 예시 (Java/Spring)
POST http://lms-ai-api:8000/api/v1/qa/ask
Authorization: Bearer {API_KEY}
Content-Type: application/json
```

**Webhook 패턴 (ingestion 완료 알림):**
```python
# ingest 완료 시 LMS에 알림
POST {settings.LMS_WEBHOOK_URL}/ai/material-ready
{ "material_id": 42, "status": "READY", "chunk_count": 87 }
```

---

## 18. 최소 관리자 페이지

FastAPI + Jinja2로 구현 (별도 React 불필요):

```
/admin                    # 대시보드 (모델 상태 요약)
/admin/materials          # 자료 목록 + 임베딩 상태
/admin/materials/upload   # 업로드 테스트
/admin/quiz/test          # 문제 생성 테스트
/admin/qa/test            # 질문 테스트
/admin/health             # embed/rerank/llm ping 상태
/admin/jobs               # celery 작업 현황
```

---

## 19. MVP 범위 정의

### MVP (2-3주)
1. 자료 업로드 + ingestion pipeline (PDF만)
2. 기본 QA (retrieve → rerank → generate → citation)
3. MCQ 문제 생성
4. PostgreSQL schema (material, quiz)
5. Docker Compose 기본 구성
6. `/admin/health` 포함 기본 관리 페이지

### Phase 2 (4-6주 후)
- PPTX/DOCX 지원
- OX/단답/서술형 문제
- 시험대비 자료 생성
- Tutor (오답 분석)
- Student progress tracking
- Celery worker 분리

### Phase 3 (납품 준비)
- 멀티 테넌트 (course isolation 강화)
- 모니터링 (Prometheus/Grafana)
- Rate limiting
- API 문서 정리

---

## 20. MSA 분리 가능성 고려

현재: monorepo, single FastAPI app

**지금부터 지켜야 할 것:**
- service 간 직접 함수 호출 금지 → interface 통해
- DB 테이블 간 JOIN 최소화 → service 경계 명확히
- `ingest_service`, `qa_service`, `quiz_service` 독립적으로 동작 가능하게

나중에 분리 시:
```
lms-ai-ingest-service  (FastAPI, 독립 배포)
lms-ai-qa-service      (FastAPI, 독립 배포)
lms-ai-quiz-service    (FastAPI, 독립 배포)
```

ai_core는 공통 패키지(`eduin-ai-core`)로 공유.

---

## 21. 모델 서버 재사용 시 주의점

1. **resource 충돌**: 기존 RAG API와 동일 llama.cpp 공유 → 동시 요청 폭주 시 OOM/timeout
   - 해결: max_concurrent 설정. LMS용 별도 llama.cpp 인스턴스 고려

2. **Qdrant collection 분리**: 기존 `rag_documents` vs 신규 `lms_materials` 이름 구분

3. **embedding 버전 고정**: BGE-M3 버전 변경 시 기존 벡터 무효화
   - 버전 metadata 포함, 재임베딩 감지 가능하게

4. **timeout 설정**: LLM 응답 60-120초 가정, httpx timeout 넉넉히

5. **circuit breaker**: 모델 서버 다운 시 hang 방지
   ```python
   from tenacity import retry, stop_after_attempt, wait_fixed

   @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
   async def generate(self, prompt: str):
       ...
   ```

---

## 22. 기존 RAG 서버와 공존 전략

```
[사내 GPU 서버]
├── llama-server    포트 8080  ← 공통 사용
├── embed-server    포트 8001  ← 공통 사용
├── reranker-server 포트 8002  ← 공통 사용
├── qdrant          포트 6333  ← 공통 (collection 분리)
│
├── [기존 RAG API]  포트 8100
└── [LMS AI API]   포트 8200  ← 신규
```

**Qdrant collection 네이밍:**
```
기존: rag_proposals, rag_documents
신규: lms_materials, lms_quizzes
```

**PostgreSQL DB 분리:**
```
기존: rag_db
신규: lms_ai_db
```

---

## 23. Sequence Diagram

### QA 흐름

```
LMS Backend        LMS AI API         ai_core           Model Servers
     │                  │                │                    │
     │  POST /qa/ask     │                │                    │
     │────────────────→  │                │                    │
     │                  │  embed(query)   │                    │
     │                  │───────────────→│  POST /embed       │
     │                  │                │──────────────────→ │
     │                  │                │←──────────────────  │
     │                  │  retrieve(vec)  │                    │
     │                  │───────────────→│  qdrant.search     │
     │                  │  rerank(chunks) │                    │
     │                  │───────────────→│  POST /rerank      │
     │                  │                │──────────────────→ │
     │                  │                │←──────────────────  │
     │                  │  generate(prompt)│                   │
     │                  │───────────────→│  POST /completion  │
     │                  │                │──────────────────→ │
     │                  │                │←──────────────────  │
     │  response+citations│              │                    │
     │←────────────────  │                │                    │
```

### Ingestion 흐름

```
LMS Backend        LMS AI API         Redis/Celery       Model Servers
     │                  │                │                    │
     │  POST /materials  │                │                    │
     │────────────────→  │                │                    │
     │                  │  save file      │                    │
     │                  │  DB insert      │                    │
     │  {id, PENDING}   │  task.delay()  │                    │
     │←────────────────  │───────────────→│                    │
     │                  │                │  parse file        │
     │                  │                │  chunk             │
     │                  │                │  POST /embed ────→ │
     │                  │                │←──────────────────  │
     │                  │                │  qdrant upsert     │
     │                  │                │  DB status=READY   │
     │  GET /status     │                │                    │
     │────────────────→  │                │                    │
     │  {status: READY} │                │                    │
     │←────────────────  │                │                    │
```

---

## 24. 로컬 개발 전략

```bash
# 1. 로컬 infra만 Docker로
docker compose up db redis qdrant

# 2. 모델 서버는 사내 GPU 서버 직접 호출
# .env.local:
# LLM_ENDPOINT=http://gpu-server:8080
# EMBEDDING_ENDPOINT=http://gpu-server:8001

# 3. FastAPI 직접 실행 (hot reload)
uvicorn app.main:app --reload

# 4. Celery worker 로컬 실행
celery -A app.workers.celery_app worker --loglevel=info
```

**모델 서버 오프라인 시 테스트:**
```python
class MockLLMClient(BaseLLMClient):
    async def generate(self, prompt: str, **kwargs) -> str:
        return "테스트 답변입니다. [출처1]"

class MockEmbeddingClient(BaseEmbeddingClient):
    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 1024 for _ in texts]
```

---

## 25. 공공기관/납품 고려사항

1. **데이터 격리**: 기관별 course_id/tenant_id 완전 분리
2. **Air-gap 환경**: 외부 API 의존성 없음 (OpenAI 등 불가). 현재 스택 완벽 적합
3. **감사 로그**: 모든 AI 답변 + citation 로그 보존 (`chat_sessions` 테이블)
4. **온프레미스**: Docker Compose로 완전 자급 배포 가능
5. **API 문서**: OpenAPI(Swagger) 자동 생성 → 연동 계약서 역할
6. **모델 교체 용이성**: abstraction layer 덕분에 모델 교체 시 비즈니스 로직 무변경
7. **보안**: API Key 인증, 내부망 배포, HTTPS 필수

---

## 26. 시작 순서 추천

1. `ai_core/clients/` 3개 client 구현 + mock
2. `ai_core/rag/` chunker + retriever + reranker
3. DB schema + Qdrant collection 생성
4. ingestion worker (PDF만)
5. `/api/v1/qa/ask` endpoint
6. Docker Compose
7. quiz 생성 endpoint
8. 나머지 순차 추가

> **과설계 금지**: LangGraph는 QA부터 단순 체인으로 시작, 복잡해지면 분기 추가.
