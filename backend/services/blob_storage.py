from functools import lru_cache

from azure.storage.blob import BlobServiceClient, ContentSettings

from config import settings


@lru_cache
def get_blob_service_client() -> BlobServiceClient:
    return BlobServiceClient.from_connection_string(settings.azure_blob_connection_string)


def _ensure_container(container: str) -> None:
    container_client = get_blob_service_client().get_container_client(container)
    if not container_client.exists():
        container_client.create_container()


def upload_text(container: str, blob_name: str, content: str, content_type: str = "text/markdown") -> str:
    """Upload text content to blob storage, creating the container if needed.

    Returns the blob URL.
    """
    _ensure_container(container)
    blob_client = get_blob_service_client().get_blob_client(container=container, blob=blob_name)
    blob_client.upload_blob(
        content.encode("utf-8"),
        overwrite=True,
        content_settings=ContentSettings(content_type=content_type),
    )
    return blob_client.url


def download_text(container: str, blob_name: str) -> str | None:
    """Download text content from blob storage, or None if the blob doesn't exist."""
    blob_client = get_blob_service_client().get_blob_client(container=container, blob=blob_name)
    if not blob_client.exists():
        return None
    return blob_client.download_blob().readall().decode("utf-8")


def upload_bytes(container: str, blob_name: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    """Upload binary content to blob storage, creating the container if needed.

    Returns the blob URL.
    """
    _ensure_container(container)
    blob_client = get_blob_service_client().get_blob_client(container=container, blob=blob_name)
    blob_client.upload_blob(
        data,
        overwrite=True,
        content_settings=ContentSettings(content_type=content_type),
    )
    return blob_client.url


def download_bytes(container: str, blob_name: str) -> bytes | None:
    """Download binary content from blob storage, or None if the blob doesn't exist."""
    blob_client = get_blob_service_client().get_blob_client(container=container, blob=blob_name)
    if not blob_client.exists():
        return None
    return blob_client.download_blob().readall()
