import os
import uuid
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.core.config import settings
from app.core.deps import verify_api_key
from app.core.redis_client import get_ingest_status, set_ingest_status, list_ingest_materials
from app.workers.ingest_worker import run_ingest

router = APIRouter()

ALLOWED_TYPES = {"pdf", "pptx", "docx"}


class MaterialUploadResponse(BaseModel):
    material_id: str
    file_name: str
    status: str
    message: str


class MaterialStatusResponse(BaseModel):
    material_id: str
    status: str
    file_name: str | None = None
    chunk_count: int | None = None
    error: str | None = None


@router.get("/materials", dependencies=[Depends(verify_api_key)])
async def list_materials():
    return await list_ingest_materials()


@router.post("/materials", response_model=MaterialUploadResponse, dependencies=[Depends(verify_api_key)])
async def upload_material(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    course_id: int = Form(...),
    lecture_id: int | None = Form(None),
):
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 파일 형식: {ext}. 허용: {ALLOWED_TYPES}")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    material_id = uuid.uuid4().hex
    save_name = f"{material_id}_{file.filename}"
    save_path = os.path.join(settings.UPLOAD_DIR, save_name)

    file_size = 0
    with open(save_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            file_size += len(chunk)
            if file_size > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
                f.close()
                os.remove(save_path)
                raise HTTPException(status_code=413, detail="파일 크기 초과")
            f.write(chunk)

    await set_ingest_status(material_id, "PENDING", file_name=file.filename)

    background_tasks.add_task(
        run_ingest,
        material_id=material_id,
        file_path=save_path,
        file_type=ext,
        file_name=file.filename,
        course_id=course_id,
        lecture_id=lecture_id,
    )

    return MaterialUploadResponse(
        material_id=material_id,
        file_name=file.filename,
        status="PENDING",
        message="업로드 완료. 임베딩 처리 중입니다.",
    )


@router.get("/materials/{material_id}/status", response_model=MaterialStatusResponse, dependencies=[Depends(verify_api_key)])
async def get_material_status(material_id: str):
    data = await get_ingest_status(material_id)
    if not data:
        raise HTTPException(status_code=404, detail="Material not found")
    return MaterialStatusResponse(**data)


@router.delete("/materials/{material_id}", dependencies=[Depends(verify_api_key)])
async def delete_material(material_id: str):
    data = await get_ingest_status(material_id)
    if not data:
        raise HTTPException(status_code=404, detail="Material not found")

    from ai_core.vectorstore.qdrant_wrapper import QdrantWrapper
    qdrant = QdrantWrapper(url=settings.QDRANT_URL, collection=settings.QDRANT_COLLECTION)
    qdrant.delete_by_material(material_id)

    from app.core.redis_client import get_redis
    await get_redis().delete(f"ingest:{material_id}")

    return {"message": f"Material {material_id} deleted"}
