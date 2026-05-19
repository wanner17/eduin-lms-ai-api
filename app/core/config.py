from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENV: str = "local"

    # AI model server endpoints
    LLM_ENDPOINT: str = "http://localhost:8080"
    EMBEDDING_ENDPOINT: str = "http://localhost:8001"
    RERANKER_ENDPOINT: str = "http://localhost:8002"

    # LLM params
    LLM_MODEL: str = "qwen2.5-7b"
    LLM_MAX_TOKENS: int = 2048
    LLM_TEMPERATURE: float = 0.1
    LLM_TIMEOUT: int = 120

    # Embedding params
    EMBEDDING_DIM: int = 1024
    EMBEDDING_TIMEOUT: int = 30

    # Reranker params
    RERANKER_TIMEOUT: int = 30
    RERANKER_TOP_N: int = 3

    # Retrieval params
    RETRIEVAL_TOP_K: int = 20

    # Vector DB & Cache
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION: str = "lms_materials"
    REDIS_URL: str = "redis://localhost:6379"

    # LMS integration
    LMS_API_KEY: str = "changeme"
    LMS_WEBHOOK_URL: str = ""

    # File upload
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 100

    # 모델 서버 오프라인 시 mock 사용 (로컬 테스트용)
    USE_MOCK_CLIENTS: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
