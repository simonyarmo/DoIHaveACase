import uuid
from datetime import date, datetime

from pydantic import BaseModel


class CaseOut(BaseModel):
    id: uuid.UUID
    status: str
    dispute_type: str
    state: str | None = None
    county: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CaseDetailsOut(BaseModel):
    # Property
    property_address: str | None = None
    property_state: str | None = None
    property_county: str | None = None
    property_type: str | None = None

    # Landlord
    landlord_type: str | None = None
    landlord_name_as_entered: str | None = None
    landlord_legal_name: str | None = None
    landlord_sos_verified: bool = False
    landlord_registered_agent: str | None = None
    landlord_address: str | None = None
    landlord_sos_status: str | None = None
    landlord_sos_lookup_date: datetime | None = None

    # Deposit
    deposit_amount: float | None = None
    amount_returned: float | None = None
    date_returned: date | None = None
    move_in_date: date | None = None
    move_out_date: date | None = None
    keys_returned_date: date | None = None
    forwarding_address: str | None = None
    forwarding_address_proof: bool = False

    # Communication
    landlord_communication: str = "none"
    itemization_received: bool = False
    itemization_date: date | None = None
    demand_letter_sent: bool = False
    demand_letter_date: date | None = None
    demand_letter_delivery: str | None = None

    # Notice
    notice_provided: bool | None = None
    notice_date: date | None = None
    notice_method: str | None = None
    notice_days: int | None = None
    lease_required_notice_days: int | None = None

    # Computed by research agent
    days_overdue: int | None = None
    deadline_date: date | None = None
    violation_confirmed: bool | None = None
    bad_faith_indicators: list[str] | None = None
    estimated_recovery_min: float | None = None
    estimated_recovery_max: float | None = None
    penalty_multiplier: float | None = None

    # Computed by assessment agent
    case_strength: str | None = None
    findings_good: list[dict] | None = None
    findings_caution: list[dict] | None = None
    findings_bad: list[dict] | None = None
    defenses_likely: list[dict] | None = None
    exceeds_jurisdiction: bool | None = None
    jurisdiction_options: list[str] | None = None
    recommended_path: str | None = None
    notice_compliant: bool | None = None
    notice_risk_amount: float | None = None

    model_config = {"from_attributes": True}


class CaseDetailsUpdate(BaseModel):
    """Partial update for `case_details_security_deposit` — used by intake Steps 2-4.

    Only fields the user can fill in directly; agent-computed fields (SOS
    verification, deadline, recovery estimates, etc.) are set by `intake_agent`.
    """

    property_address: str | None = None
    property_state: str | None = None
    property_county: str | None = None
    property_type: str | None = None

    landlord_type: str | None = None
    landlord_name_as_entered: str | None = None
    landlord_address: str | None = None

    deposit_amount: float | None = None
    amount_returned: float | None = None
    date_returned: date | None = None
    move_in_date: date | None = None
    move_out_date: date | None = None
    keys_returned_date: date | None = None
    forwarding_address: str | None = None
    forwarding_address_proof: bool | None = None

    landlord_communication: str | None = None
    itemization_received: bool | None = None
    itemization_date: date | None = None
    demand_letter_sent: bool | None = None
    demand_letter_date: date | None = None
    demand_letter_delivery: str | None = None

    notice_provided: bool | None = None
    notice_date: date | None = None
    notice_method: str | None = None
    notice_days: int | None = None


class TenantInfo(BaseModel):
    """Step 1 — maps to a `case_parties` row with role='tenant' (and `users.phone_number`)."""

    full_legal_name: str | None = None
    address: str | None = None
    phone: str | None = None


class CaseUpdateRequest(BaseModel):
    state: str | None = None
    county: str | None = None
    tenant: TenantInfo | None = None
    details: CaseDetailsUpdate | None = None


class PartyOut(BaseModel):
    id: uuid.UUID
    role: str
    full_legal_name: str
    entity_type: str | None = None
    address: str | None = None

    model_config = {"from_attributes": True}


class DocumentOut(BaseModel):
    id: uuid.UUID
    type: str
    status: str
    file_name: str | None = None
    file_type: str | None = None
    file_size: int | None = None
    uploaded_at: datetime | None = None

    model_config = {"from_attributes": True}


class CaseDetailResponse(BaseModel):
    case: CaseOut
    details: CaseDetailsOut
    parties: list[PartyOut]
    documents: list[DocumentOut]


class SubmitResponse(BaseModel):
    status: str
    session_id: uuid.UUID


class ConversationMessageOut(BaseModel):
    id: uuid.UUID
    role: str
    message_type: str
    content: str | None = None
    form_schema: dict | None = None
    form_response: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class StrengthBars(BaseModel):
    violation_clear: int
    bad_faith_case: int
    evidence_quality: int
    procedural_risk: int


class TimelineEventOut(BaseModel):
    id: uuid.UUID
    event_type: str
    title: str
    description: str | None = None
    event_date: date | None = None
    is_deadline: bool
    completed: bool
    completed_at: datetime | None = None
    document_id: uuid.UUID | None = None
    source: str

    model_config = {"from_attributes": True}


class AssessmentResponse(BaseModel):
    case: CaseOut
    details: CaseDetailsOut
    strength_bars: StrengthBars
    timeline_events: list[TimelineEventOut]


class CaseSummary(BaseModel):
    id: uuid.UUID
    status: str
    state: str | None = None
    county: str | None = None
    property_address: str | None = None
    estimated_recovery_min: float | None = None
    estimated_recovery_max: float | None = None
    case_strength: str | None = None
    created_at: datetime
