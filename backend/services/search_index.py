"""Foundry IQ knowledge base client.

Each Foundry IQ knowledge base referenced in the phase docs
(`kb-state-law-security-deposit`, `kb-court-procedures`,
`kb-document-templates`, and per-case `kb-case-{case_id}`) is implemented as
an Azure AI Search index, using the credentials already provisioned in
`AZURE_SEARCH_ENDPOINT` / `AZURE_SEARCH_API_KEY`. The index name is the
knowledge base's `foundry_source_id`.
"""

from functools import lru_cache

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SimpleField,
)

from config import settings


def _credential() -> AzureKeyCredential:
    return AzureKeyCredential(settings.azure_search_api_key)


@lru_cache
def get_index_client() -> SearchIndexClient:
    return SearchIndexClient(endpoint=settings.azure_search_endpoint, credential=_credential())


def get_search_client(index_name: str) -> SearchClient:
    return SearchClient(endpoint=settings.azure_search_endpoint, index_name=index_name, credential=_credential())


def _knowledge_base_fields() -> list[SearchField]:
    return [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name="title", type=SearchFieldDataType.String),
        SearchableField(name="content", type=SearchFieldDataType.String),
        SimpleField(name="category", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SimpleField(name="section", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="source_url", type=SearchFieldDataType.String),
        SimpleField(name="last_verified", type=SearchFieldDataType.String, filterable=True, sortable=True),
    ]


def ensure_knowledge_base_index(index_name: str) -> None:
    """Create the knowledge base index if it doesn't already exist."""
    client = get_index_client()
    existing = {idx.name for idx in client.list_indexes()}
    if index_name in existing:
        return
    client.create_index(SearchIndex(name=index_name, fields=_knowledge_base_fields()))


def upload_documents(index_name: str, documents: list[dict]) -> None:
    """Upsert documents into a knowledge base index, creating the index first if needed."""
    ensure_knowledge_base_index(index_name)
    get_search_client(index_name).merge_or_upload_documents(documents=documents)


def create_case_knowledge_base(case_id: str) -> str:
    """Create a per-case knowledge base, isolating that case's data at the retrieval layer.

    Returns the `foundry_source_id` (index name) for the new knowledge base.
    """
    index_name = f"kb-case-{case_id}"
    ensure_knowledge_base_index(index_name)
    return index_name
