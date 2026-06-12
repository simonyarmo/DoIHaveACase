import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from database import Base


class CaseKBDocument(Base):
    """Per-case findings (landlord verification, state-law summaries, lease
    parse results, etc.), used to build chat context for `/ws/cases/{case_id}`.

    Stored in Postgres rather than an Azure AI Search index — per-case
    findings are a handful of short documents, so a fetch-all (no semantic
    ranking needed) is sufficient, and this avoids Azure AI Search's
    free-tier 3-index cap (already consumed by the shared knowledge bases).
    """

    __tablename__ = "case_kb_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    doc_key: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    doc_type: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
