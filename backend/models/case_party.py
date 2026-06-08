import uuid
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from database import Base


class CaseParty(Base):
    __tablename__ = "case_parties"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String, nullable=False)
    full_legal_name: Mapped[str] = mapped_column(String, nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String)
    address: Mapped[str | None] = mapped_column(String)
    served: Mapped[bool] = mapped_column(Boolean, default=False)
    served_date: Mapped[date | None] = mapped_column(Date)
    served_method: Mapped[str | None] = mapped_column(String)
    proof_of_service_doc_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
