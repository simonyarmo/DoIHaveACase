import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from database import Base


class LeaseParseResult(Base):
    __tablename__ = "lease_parse_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    parsed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    tenant_legal_name: Mapped[str | None] = mapped_column(String)
    landlord_legal_name: Mapped[str | None] = mapped_column(String)
    property_address: Mapped[str | None] = mapped_column(String)
    lease_start_date: Mapped[date | None] = mapped_column(Date)
    lease_end_date: Mapped[date | None] = mapped_column(Date)
    deposit_amount: Mapped[float | None] = mapped_column(Numeric(10, 2))
    notice_required_days: Mapped[int | None] = mapped_column(Integer)
    notice_method: Mapped[str | None] = mapped_column(String)
    pet_policy: Mapped[str | None] = mapped_column(String)
    early_termination_clause: Mapped[str | None] = mapped_column(Text)
    maintenance_responsibilities: Mapped[str | None] = mapped_column(Text)
    notice_compliant: Mapped[bool | None] = mapped_column(Boolean)
    flagged_clauses: Mapped[dict | None] = mapped_column(JSONB)
    raw_parse_output: Mapped[dict | None] = mapped_column(JSONB)
    confidence_score: Mapped[float | None] = mapped_column(Numeric(4, 2))
