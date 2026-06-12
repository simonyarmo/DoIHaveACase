"""Pushes ingested content to Azure Blob Storage and indexes it in the
relevant Foundry IQ knowledge base.
"""

from pathlib import Path

from config import settings
from knowledge.ingestion.sources.registry import CourtProcedureSource
from knowledge.ingestion.validator import extract_sections
from services import blob_storage, search_index

STATE_LAW_BLOB_PREFIX = "state-law"
PENDING_REVIEW_BLOB_PREFIX = "pending-review"
TEMPLATES_BLOB_PREFIX = "document-templates"


def get_existing_state_law(state: str) -> str | None:
    """Return the currently published markdown for `state`, or None if it hasn't been published yet."""
    return blob_storage.download_text(
        settings.azure_blob_container_knowledge, f"{STATE_LAW_BLOB_PREFIX}/{state.upper()}.md"
    )


def upload_state_law(state: str, markdown: str, source_url: str, last_verified: str) -> str:
    """Upload `markdown` to Blob Storage and index its sections in
    `kb-state-law-security-deposit`. Returns the `foundry_source_id`.
    """
    state = state.upper()
    blob_storage.upload_text(settings.azure_blob_container_knowledge, f"{STATE_LAW_BLOB_PREFIX}/{state}.md", markdown)

    documents = [
        {
            "id": f"{state}-{i:02d}",
            "title": f"{state} — {heading}",
            "content": body,
            "category": state,
            "section": heading,
            "source_url": source_url,
            "last_verified": last_verified,
        }
        for i, (heading, body) in enumerate(extract_sections(markdown).items())
    ]
    search_index.upload_documents(settings.foundry_kb_state_law, documents)

    return f"{settings.foundry_kb_state_law}/{state}"


def upload_court_procedures(state: str, court_procedures: list[CourtProcedureSource]) -> None:
    """Index county-level filing procedure sources in `kb-court-procedures`.

    Ensures the knowledge base index exists even for states with no
    registered court procedure sources yet.
    """
    if not court_procedures:
        search_index.ensure_knowledge_base_index(settings.foundry_kb_court_procedures)
        return

    documents = [
        {
            "id": f"{state.upper()}-{cp.county.lower()}",
            "title": f"{state.upper()} — {cp.county} County",
            "content": cp.description,
            "category": state.upper(),
            "section": cp.county,
            "source_url": cp.url,
            "last_verified": "",
        }
        for cp in court_procedures
    ]
    search_index.upload_documents(settings.foundry_kb_court_procedures, documents)


def upload_pending_review(state: str, markdown: str) -> str:
    """Write flagged content to the pending-review area without publishing it. Returns the blob URL."""
    return blob_storage.upload_text(
        settings.azure_blob_container_knowledge, f"{PENDING_REVIEW_BLOB_PREFIX}/{state.upper()}.md", markdown
    )


def register_document_templates(template_paths: list[Path]) -> list[str]:
    """Upload document template YAMLs to Blob Storage and index them in `kb-document-templates`.

    Returns the list of registered template ids (file stems).
    """
    documents = []
    for path in template_paths:
        content = path.read_text(encoding="utf-8")
        blob_storage.upload_text(
            settings.azure_blob_container_knowledge,
            f"{TEMPLATES_BLOB_PREFIX}/{path.name}",
            content,
            content_type="application/yaml",
        )
        documents.append(
            {
                "id": path.stem,
                "title": path.stem.replace("_", " ").title(),
                "content": content,
                "category": "document_template",
                "section": path.stem,
                "source_url": "",
                "last_verified": "",
            }
        )
    search_index.upload_documents(settings.foundry_kb_document_templates, documents)
    return [doc["id"] for doc in documents]
