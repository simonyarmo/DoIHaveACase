import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from database import Base


class LawFreshness(Base):
    __tablename__ = "law_freshness"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    state: Mapped[str] = mapped_column(String(2), unique=True, nullable=False)
    dispute_type: Mapped[str] = mapped_column(String, default="security_deposit")
    last_verified: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_review: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_frequency_days: Mapped[int] = mapped_column(Integer, default=90)
    last_pipeline_run: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_pipeline_status: Mapped[str | None] = mapped_column(String)
    last_pipeline_changes: Mapped[dict | None] = mapped_column(JSONB)
    pending_review: Mapped[bool] = mapped_column(Boolean, default=False)
    foundry_source_id: Mapped[str | None] = mapped_column(String)
    source_urls: Mapped[dict | None] = mapped_column(JSONB)
