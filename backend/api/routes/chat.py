"""Per-case WebSocket — research progress relay + chat.

`WS /ws/cases/{case_id}?token=<supabase-jwt>`

Registered directly on the app (not `protected_router`, since FastAPI's
`Depends`-based auth doesn't apply to WebSocket routes) and authenticates by
decoding the Supabase JWT passed as a query parameter.

Runs two concurrent loops for the lifetime of the connection:
- **Progress relay**: forwards `intake_agent`/`lease_parser_agent` progress
  events (published via `services.progress_bus`) to the client as JSON.
- **Chat**: receives `{"type": "message", "content": "..."}` (or
  `{"type": "form_response", "form_response": {...}}`) from the client,
  persists it to `conversation_messages`, and streams the assistant's reply
  back token-by-token.
"""

import asyncio
import logging
import uuid

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import _decode_supabase_jwt
from database import async_session_factory
from models.case import Case
from models.conversation import ConversationMessage
from services import llm_client, progress_bus
from services.users import get_or_create_local_user
from tools import foundry_iq

logger = logging.getLogger(__name__)

router = APIRouter()

_CHAT_HISTORY_LIMIT = 20


@router.websocket("/ws/cases/{case_id}")
async def case_chat(websocket: WebSocket, case_id: str) -> None:
    await websocket.accept()

    token = websocket.query_params.get("token")
    if token is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    async with async_session_factory() as db:
        try:
            payload = _decode_supabase_jwt(token)
        except HTTPException:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        supabase_user_id = payload.get("sub")
        email = payload.get("email")
        if supabase_user_id is None or email is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        try:
            case_uuid = uuid.UUID(case_id)
        except ValueError:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        user = await get_or_create_local_user(
            db, user_id=supabase_user_id, email=email, full_name=(payload.get("user_metadata") or {}).get("full_name")
        )

        case = await db.get(Case, case_uuid)
        if case is None or case.user_id != user.id:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        try:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(_relay_progress(websocket, case_id))
                tg.create_task(_chat_loop(websocket, db, case_id))
        except* WebSocketDisconnect:
            pass


async def _relay_progress(websocket: WebSocket, case_id: str) -> None:
    async for event in progress_bus.subscribe(case_id):
        await websocket.send_json(event)


async def _chat_loop(websocket: WebSocket, db: AsyncSession, case_id: str) -> None:
    while True:
        data = await websocket.receive_json()
        message_type = data.get("type")
        if message_type == "message":
            await _handle_chat_message(websocket, db, case_id, data.get("content") or "")
        elif message_type == "form_response":
            await _handle_form_response(db, websocket, case_id, data.get("form_response"))


async def _handle_form_response(db: AsyncSession, websocket: WebSocket, case_id: str, form_response: dict | None) -> None:
    db.add(
        ConversationMessage(case_id=uuid.UUID(case_id), role="user", message_type="form_response", form_response=form_response)
    )
    await db.commit()
    await websocket.send_json({"type": "done"})


async def _handle_chat_message(websocket: WebSocket, db: AsyncSession, case_id: str, content: str) -> None:
    db.add(ConversationMessage(case_id=uuid.UUID(case_id), role="user", message_type="text", content=content))
    await db.commit()

    context_chunks = await foundry_iq.get_case_kb_documents(db, case_id)
    if context_chunks:
        context_text = "\n\n".join(f"{chunk.get('title')}: {chunk.get('content')}" for chunk in context_chunks)
    else:
        context_text = "No additional case context available."

    history = (
        await db.execute(
            select(ConversationMessage)
            .where(ConversationMessage.case_id == uuid.UUID(case_id), ConversationMessage.message_type == "text")
            .order_by(ConversationMessage.created_at.desc())
            .limit(_CHAT_HISTORY_LIMIT)
        )
    ).scalars().all()

    messages = [
        {
            "role": "system",
            "content": (
                "You are DepositShield's case assistant, helping a tenant understand their "
                "security-deposit dispute. Answer using the case context below when relevant.\n\n"
                f"Case context:\n{context_text}"
            ),
        }
    ]
    for msg in reversed(history):
        role = "user" if msg.role == "user" else "assistant"
        messages.append({"role": role, "content": msg.content or ""})

    reply_parts: list[str] = []
    async for token in llm_client.chat_completion_stream(messages):
        reply_parts.append(token)
        await websocket.send_json({"type": "token", "content": token})

    db.add(ConversationMessage(case_id=uuid.UUID(case_id), role="assistant", message_type="text", content="".join(reply_parts)))
    await db.commit()
    await websocket.send_json({"type": "done"})
