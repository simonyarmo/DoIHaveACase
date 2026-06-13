import asyncio
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select

from agents.intake_agent import run_intake_research
from agents.lease_parser_agent import parse_lease
from api.dependencies import CurrentUserDep, DbDep
from config import settings
from models.agent_session import AgentSession
from models.case import Case
from models.case_detail import CaseDetailsSecurityDeposit
from models.case_party import CaseParty
from models.conversation import ConversationMessage
from models.document import Document
from models.user import User
from schemas.cases import (
    CaseDetailResponse,
    CaseDetailsOut,
    CaseOut,
    CaseUpdateRequest,
    ConversationMessageOut,
    DocumentOut,
    PartyOut,
    SubmitResponse,
    TenantInfo,
)
from services import blob_storage

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


async def _get_case_or_404(db: DbDep, case_id: str, user_id: uuid.UUID) -> Case:
    try:
        case_uuid = uuid.UUID(case_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    case = await db.get(Case, case_uuid)
    if case is None or case.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return case


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
