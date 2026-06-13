import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from database import Base


class CaseDetailsSecurityDeposit(Base):
    __tablename__ = "case_details_security_deposit"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    # Property
    property_address: Mapped[str | None] = mapped_column(String)
    property_state: Mapped[str | None] = mapped_column(String(2))
    property_county: Mapped[str | None] = mapped_column(String)
    property_type: Mapped[str | None] = mapped_column(String)

    # Landlord
    landlord_type: Mapped[str | None] = mapped_column(String)
    landlord_name_as_entered: Mapped[str | None] = mapped_column(String)
    landlord_legal_name: Mapped[str | None] = mapped_column(String)
    landlord_sos_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    landlord_registered_agent: Mapped[str | None] = mapped_column(String)
    landlord_address: Mapped[str | None] = mapped_column(String)
    landlord_sos_status: Mapped[str | None] = mapped_column(String)
    landlord_sos_lookup_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Deposit
    deposit_amount: Mapped[float | None] = mapped_column(Numeric(10, 2))
    amount_returned: Mapped[float | None] = mapped_column(Numeric(10, 2), default=0)
    date_returned: Mapped[date | None] = mapped_column(Date)
    move_in_date: Mapped[date | None] = mapped_column(Date)
    move_out_date: Mapped[date | None] = mapped_column(Date)
    keys_returned_date: Mapped[date | None] = mapped_column(Date)
    forwarding_address: Mapped[str | None] = mapped_column(String)
    forwarding_address_proof: Mapped[bool] = mapped_column(Boolean, default=False)

    # Communication
    landlord_communication: Mapped[str] = mapped_column(String, default="none")
    itemization_received: Mapped[bool] = mapped_column(Boolean, default=False)
    itemization_date: Mapped[date | None] = mapped_column(Date)
    demand_letter_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    demand_letter_date: Mapped[date | None] = mapped_column(Date)
    demand_letter_delivery: Mapped[str | None] = mapped_column(String)

    # Notice
    notice_provided: Mapped[bool | None] = mapped_column(Boolean)
    notice_date: Mapped[date | None] = mapped_column(Date)
    notice_method: Mapped[str | None] = mapped_column(String)
    notice_days: Mapped[int | None] = mapped_column(Integer)
    lease_required_notice_days: Mapped[int | None] = mapped_column(Integer)

    # Computed (set by agent after research)
    days_overdue: Mapped[int | None] = mapped_column(Integer)
    deadline_date: Mapped[date | None] = mapped_column(Date)
    violation_confirmed: Mapped[bool | None] = mapped_column(Boolean)
    bad_faith_indicators: Mapped[dict | None] = mapped_column(JSONB)
    estimated_recovery_min: Mapped[float | None] = mapped_column(Numeric(10, 2))
    estimated_recovery_max: Mapped[float | None] = mapped_column(Numeric(10, 2))
    penalty_multiplier: Mapped[float | None] = mapped_column(Numeric(4, 1))
