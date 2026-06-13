import asyncio
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select

from agents.assessment_agent import run_assessment
from agents.intake_agent import run_intake_research
from agents.lease_parser_agent import parse_lease
from api.dependencies import CurrentUserDep, DbDep
from api.dependencies import get_case_or_404 as _get_case_or_404
from config import settings
from models.agent_session import AgentSession
from models.case import Case
from models.case_detail import CaseDetailsSecurityDeposit
from models.case_party import CaseParty
from models.conversation import ConversationMessage
from models.document import Document
from models.lease_parse import LeaseParseResult
from models.timeline import TimelineEvent
from models.user import User
from schemas.cases import (
    AssessmentResponse,
    CaseDetailResponse,
    CaseDetailsOut,
    CaseOut,
    CaseSummary,
    CaseUpdateRequest,
    ConversationMessageOut,
    DocumentOut,
    PartyOut,
    StrengthBars,
    SubmitResponse,
    TenantInfo,
    TimelineEventOut,
)
from services import blob_storage
from tools.assessment_rules import compute_strength_bars

router = APIRouter(prefix="/cases", tags=["cases"])

ALLOWED_DOCUMENT_TYPES = {
    "lease",
    "move_in_inspection",
    "move_out_inspection",
    "photos_move_in",
    "photos_move_out",
    "communications",
    "forwarding_proof",
    "deposit_proof",
}

# Fixed action-plan step order — `timeline_events.event_type` for agent-generated
# plans, used to render the action plan in a stable sequence on the assessment screen.
_TIMELINE_EVENT_ORDER = {
    "demand_letter_required": 0,
    "deadline": 1,
    "filing_required": 2,
    "service_required": 3,
    "hearing": 4,
}


async def _build_detail_response(db: DbDep, case: Case) -> CaseDetailResponse:
    details = (
        await db.execute(select(CaseDetailsSecurityDeposit).where(CaseDetailsSecurityDeposit.case_id == case.id))
    ).scalar_one_or_none()
    parties = (await db.execute(select(CaseParty).where(CaseParty.case_id == case.id))).scalars().all()
    documents = (await db.execute(select(Document).where(Document.case_id == case.id))).scalars().all()

    return CaseDetailResponse(
        case=CaseOut.model_validate(case),
        details=CaseDetailsOut.model_validate(details) if details is not None else CaseDetailsOut(),
        parties=[PartyOut.model_validate(party) for party in parties],
        documents=[DocumentOut.model_validate(document) for document in documents],
    )


async def _upsert_tenant(db: DbDep, case: Case, current_user: User, tenant: TenantInfo) -> None:
    party = (
        await db.execute(select(CaseParty).where(CaseParty.case_id == case.id, CaseParty.role == "tenant"))
    ).scalar_one_or_none()

    if party is None:
        if tenant.full_legal_name is not None:
            db.add(
                CaseParty(case_id=case.id, role="tenant", full_legal_name=tenant.full_legal_name, address=tenant.address)
            )
    else:
        if tenant.full_legal_name is not None:
            party.full_legal_name = tenant.full_legal_name
        if tenant.address is not None:
            party.address = tenant.address

    if tenant.phone is not None:
        current_user.phone_number = tenant.phone


@router.get("", response_model=list[CaseSummary])
async def list_cases(current_user: CurrentUserDep, db: DbDep) -> list[CaseSummary]:
    """Cases for the current user, newest first — powers the Dashboard."""
    rows = (
        await db.execute(
            select(Case, CaseDetailsSecurityDeposit)
            .join(CaseDetailsSecurityDeposit, CaseDetailsSecurityDeposit.case_id == Case.id, isouter=True)
            .where(Case.user_id == current_user.id)
            .order_by(Case.created_at.desc())
        )
    ).all()
    return [
        CaseSummary(
            id=case.id,
            status=case.status,
            state=case.state,
            county=case.county,
            property_address=details.property_address if details else None,
            estimated_recovery_min=details.estimated_recovery_min if details else None,
            estimated_recovery_max=details.estimated_recovery_max if details else None,
            case_strength=details.case_strength if details else None,
            created_at=case.created_at,
        )
        for case, details in rows
    ]


@router.post("", response_model=CaseOut, status_code=status.HTTP_201_CREATED)
async def create_case(current_user: CurrentUserDep, db: DbDep) -> CaseOut:
    """Create a new case and its (empty) details row."""
    case = Case(user_id=current_user.id)
    db.add(case)
    await db.flush()

    db.add(CaseDetailsSecurityDeposit(case_id=case.id))

    await db.commit()
    return CaseOut.model_validate(case)


@router.get("/{case_id}", response_model=CaseDetailResponse)
async def get_case(case_id: str, current_user: CurrentUserDep, db: DbDep) -> CaseDetailResponse:
    case = await _get_case_or_404(db, case_id, current_user.id)
    return await _build_detail_response(db, case)


@router.patch("/{case_id}", response_model=CaseDetailResponse)
async def update_case(case_id: str, payload: CaseUpdateRequest, current_user: CurrentUserDep, db: DbDep) -> CaseDetailResponse:
    case = await _get_case_or_404(db, case_id, current_user.id)

    if payload.state is not None:
        case.state = payload.state.upper()
    if payload.county is not None:
        case.county = payload.county
    case.updated_at = datetime.now(timezone.utc)

    if payload.tenant is not None:
        await _upsert_tenant(db, case, current_user, payload.tenant)

    if payload.details is not None:
        details = (
            await db.execute(select(CaseDetailsSecurityDeposit).where(CaseDetailsSecurityDeposit.case_id == case.id))
        ).scalar_one_or_none()
        if details is None:
            details = CaseDetailsSecurityDeposit(case_id=case.id)
            db.add(details)
        for field, value in payload.details.model_dump(exclude_unset=True).items():
            setattr(details, field, value)

    await db.commit()
    return await _build_detail_response(db, case)


@router.post("/{case_id}/documents", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    case_id: str,
    current_user: CurrentUserDep,
    db: DbDep,
    file: UploadFile = File(...),
    type: str = Form(...),
) -> DocumentOut:
    case = await _get_case_or_404(db, case_id, current_user.id)

    if type not in ALLOWED_DOCUMENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"'{type}' is not a recognized document type. Must be one of: {sorted(ALLOWED_DOCUMENT_TYPES)}",
        )

    data = await file.read()
    document = Document(
        case_id=case.id,
        type=type,
        status="uploaded",
        file_name=file.filename,
        file_type=file.content_type,
        file_size=len(data),
        uploaded_at=datetime.now(timezone.utc),
    )
    db.add(document)
    await db.flush()

    storage_path = f"{case.id}/{document.id}-{file.filename}"
    await asyncio.to_thread(
        blob_storage.upload_bytes,
        settings.azure_blob_container_documents,
        storage_path,
        data,
        file.content_type or "application/octet-stream",
    )
    document.storage_path = storage_path

    await db.commit()

    if type == "lease":
        parse_lease.delay(str(document.id), str(case.id))

    return DocumentOut.model_validate(document)


@router.get("/{case_id}/messages", response_model=list[ConversationMessageOut])
async def list_messages(case_id: str, current_user: CurrentUserDep, db: DbDep) -> list[ConversationMessageOut]:
    """Conversation history for the chat panel — progress messages from the
    research agent plus any prior chat turns, oldest first."""
    case = await _get_case_or_404(db, case_id, current_user.id)
    messages = (
        await db.execute(
            select(ConversationMessage).where(ConversationMessage.case_id == case.id).order_by(ConversationMessage.created_at)
        )
    ).scalars().all()
    return [ConversationMessageOut.model_validate(message) for message in messages]


@router.post("/{case_id}/submit", response_model=SubmitResponse)
async def submit_case(case_id: str, current_user: CurrentUserDep, db: DbDep) -> SubmitResponse:
    case = await _get_case_or_404(db, case_id, current_user.id)

    details = (
        await db.execute(select(CaseDetailsSecurityDeposit).where(CaseDetailsSecurityDeposit.case_id == case.id))
    ).scalar_one_or_none()
    if details is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Case has no details to research")

    if case.status == "researching":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Research is already in progress for this case")

    if case.state is None and details.property_state is not None:
        case.state = details.property_state.upper()
    if case.county is None and details.property_county is not None:
        case.county = details.property_county

    missing = []
    if not case.state:
        missing.append("state")
    if details.deposit_amount is None:
        missing.append("details.deposit_amount")
    if details.move_out_date is None:
        missing.append("details.move_out_date")
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Case is missing required fields for research", "missing_fields": missing},
        )

    case.status = "researching"
    case.updated_at = datetime.now(timezone.utc)

    session = AgentSession(case_id=case.id, session_type="intake_research", status="running")
    db.add(session)
    await db.flush()
    await db.commit()

    run_intake_research.delay(str(case.id), str(session.id))

    return SubmitResponse(status="researching", session_id=session.id)


@router.get("/{case_id}/assessment", response_model=AssessmentResponse)
async def get_assessment(case_id: str, current_user: CurrentUserDep, db: DbDep) -> AssessmentResponse:
    case = await _get_case_or_404(db, case_id, current_user.id)

    details = (
        await db.execute(select(CaseDetailsSecurityDeposit).where(CaseDetailsSecurityDeposit.case_id == case.id))
    ).scalar_one_or_none()

    if details is None:
        details_out = CaseDetailsOut()
        strength_bars = StrengthBars(violation_clear=0, bad_faith_case=0, evidence_quality=0, procedural_risk=0)
    else:
        lease = (
            await db.execute(
                select(LeaseParseResult).where(LeaseParseResult.case_id == case.id).order_by(LeaseParseResult.parsed_at.desc())
            )
        ).scalars().first()
        details_out = CaseDetailsOut.model_validate(details)
        strength_bars = StrengthBars(**compute_strength_bars(details, lease_parsed=lease is not None))

    events = (await db.execute(select(TimelineEvent).where(TimelineEvent.case_id == case.id))).scalars().all()
    events = sorted(events, key=lambda e: _TIMELINE_EVENT_ORDER.get(e.event_type, 99))

    return AssessmentResponse(
        case=CaseOut.model_validate(case),
        details=details_out,
        strength_bars=strength_bars,
        timeline_events=[TimelineEventOut.model_validate(event) for event in events],
    )


@router.post("/{case_id}/assessment/refresh", status_code=status.HTTP_202_ACCEPTED)
async def refresh_assessment(case_id: str, current_user: CurrentUserDep, db: DbDep) -> dict:
    case = await _get_case_or_404(db, case_id, current_user.id)

    if case.status == "researching":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Research is still in progress for this case")

    run_assessment.delay(str(case.id))
    return {"status": "queued"}
