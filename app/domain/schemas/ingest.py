from datetime import datetime
from pydantic import BaseModel


class MaterialUploadResponse(BaseModel):
    material_id: int
    file_name: str
    status: str
    message: str


class MaterialStatusResponse(BaseModel):
    material_id: int
    file_name: str
    file_type: str
    status: str
    chunk_count: int | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
