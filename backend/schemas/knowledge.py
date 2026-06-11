from datetime import datetime

from pydantic import BaseModel


class IngestResponse(BaseModel):
    status: str
    estimated_seconds: int


class KnowledgeStatusResponse(BaseModel):
    state: str
    status: str
    pending_review: bool
    last_verified: datetime | None = None
    next_review: datetime | None = None
