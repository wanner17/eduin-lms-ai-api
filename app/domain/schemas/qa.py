from pydantic import BaseModel


class CitationSchema(BaseModel):
    index: int
    material_name: str
    page: int
    section: str
    text: str


class QAAskRequest(BaseModel):
    query: str
    course_id: int | None = None
    lecture_id: int | None = None
    material_ids: list[int] | None = None
    student_id: str | None = None
    session_id: str | None = None


class QAAskResponse(BaseModel):
    answer: str
    citations: list[CitationSchema]
    session_id: str | None = None
