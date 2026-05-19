from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    import os
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    yield


app = FastAPI(
    title="LMS AI API",
    version="0.1.0",
    description="LMS 연동 AI 학습 보조 API 서버",
    lifespan=lifespan,
)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "x-api-key",
        }
    }
    for path in schema["paths"].values():
        for method in path.values():
            method["security"] = [{"ApiKeyAuth": []}]
    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# routers
from app.api.v1 import admin, ingest, qa, quiz, summary  # noqa: E402
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(ingest.router, prefix="/api/v1/ingest", tags=["ingest"])
app.include_router(qa.router, prefix="/api/v1/qa", tags=["qa"])
app.include_router(quiz.router, prefix="/api/v1/quiz", tags=["quiz"])
app.include_router(summary.router, prefix="/api/v1/summary", tags=["summary"])


@app.get("/", tags=["root"])
async def root():
    return {"service": "LMS AI API", "version": "0.1.0", "env": settings.ENV}
