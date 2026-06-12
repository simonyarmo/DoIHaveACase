"""Foundry IQ knowledge-base retrieval and per-case findings storage.

`query_knowledge_base` is a thin async wrapper over `services/search_index.py`
(each shared Foundry IQ knowledge base is an Azure AI Search index — see that
module's docstring). The underlying SDK calls are synchronous, so they're run
via `asyncio.to_thread` to avoid blocking the event loop.

Per-case findings (landlord verification, state-law summaries, lease parse
results, etc.) are stored in Postgres via `models.case_kb_document` instead —
see `services/search_index.py`'s docstring for why.
"""

import asyncio
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.case_kb_document import CaseKBDocument
from services import search_index

logger = logging.getLogger(__name__)


def _escape(value: str) -> str:
    return value.replace("'", "''")


async def query_knowledge_base(index_name: str, query_text: str, *, category: str | None = None, top: int = 5) -> list[dict]:
    """Search `index_name` for `query_text`, optionally filtered to `category`.

    Returns a list of `{title, content, source_url, section, category}`
    chunks. Returns `[]` (rather than raising) if the index doesn't exist or
    the search call fails.
    """

    def _search() -> list[dict]:
        filter_expr = f"category eq '{_escape(category)}'" if category else None

        client = search_index.get_search_client(index_name)
        results = client.search(
            search_text=query_text,
            filter=filter_expr,
            top=top,
            select=["title", "content", "source_url", "section", "category"],
        )
        return [
            {
                "title": r.get("title"),
                "content": r.get("content"),
                "source_url": r.get("source_url"),
                "section": r.get("section"),
                "category": r.get("category"),
            }
            for r in results
        ]

    try:
        return await asyncio.to_thread(_search)
    except Exception:
        logger.exception("Foundry IQ query failed for index %r", index_name)
        return []


async def add_document_to_case_kb(db: AsyncSession, case_id: str, doc_key: str, title: str, content: str, doc_type: str) -> None:
    """Upsert a finding (landlord verification, state-law summary, lease parse
    result, etc.) into `case_kb_documents`, keyed by `(case_id, doc_key)` so
    re-running research updates the existing row instead of duplicating it.
    """
    existing = (
        await db.execute(
            select(CaseKBDocument).where(CaseKBDocument.case_id == uuid.UUID(case_id), CaseKBDocument.doc_key == doc_key)
        )
    ).scalar_one_or_none()

    if existing is None:
        db.add(CaseKBDocument(case_id=uuid.UUID(case_id), doc_key=doc_key, title=title, content=content, doc_type=doc_type))
    else:
        existing.title = title
        existing.content = content
        existing.doc_type = doc_type

    await db.flush()


async def get_case_kb_documents(db: AsyncSession, case_id: str) -> list[dict]:
    """Return all `case_kb_documents` rows for `case_id`, as `{title, content, category}` dicts.

    Per-case findings are a handful of short documents — no semantic search
    is needed, the chat handler just includes all of them as context.
    """
    rows = (
        await db.execute(select(CaseKBDocument).where(CaseKBDocument.case_id == uuid.UUID(case_id)))
    ).scalars().all()
    return [{"title": row.title, "content": row.content, "category": row.doc_type} for row in rows]
