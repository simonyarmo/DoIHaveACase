import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy import DateTime

from database import Base

case_status = SAEnum(
    "intake",
    "researching",
    "assessment",
    "action_plan",
    "demand_sent",
    "filed",
    "hearing_scheduled",
    "resolved",
    "closed_no_case",
    name="case_status",
)

dispute_type_enum = SAEnum(
    "security_deposit",
    "habitability",
    "lease_violation",
    name="dispute_type",
)

resolution_type_enum = SAEnum(
    "settled",
    "won",
    "lost",
    "withdrawn",
    "no_case",
    name="resolution_type",
)


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(case_status, default="intake")
    dispute_type: Mapped[str] = mapped_column(dispute_type_enum, default="security_deposit")
    state: Mapped[str | None] = mapped_column(String(2))
    county: Mapped[str | None] = mapped_column(String)
    foundry_kb_id: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution_type: Mapped[str | None] = mapped_column(resolution_type_enum)
