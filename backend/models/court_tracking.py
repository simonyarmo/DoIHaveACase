import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from database import Base


class CourtTracking(Base):
    __tablename__ = "court_tracking"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    court_name: Mapped[str | None] = mapped_column(String)
    court_case_number: Mapped[str | None] = mapped_column(String)
    court_portal_url: Mapped[str | None] = mapped_column(String)
    last_checked: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    check_frequency: Mapped[int] = mapped_column(Integer, default=360)
    last_status: Mapped[str | None] = mapped_column(String)
    entries: Mapped[dict | None] = mapped_column(JSONB)
    new_entries_found: Mapped[bool] = mapped_column(Boolean, default=False)
    alert_sent: Mapped[bool] = mapped_column(Boolean, default=False)
