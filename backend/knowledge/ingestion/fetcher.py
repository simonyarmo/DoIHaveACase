"""Fetches raw state law content from official government and court sources."""

import httpx

_TIMEOUT = httpx.Timeout(30.0)
_HEADERS = {"User-Agent": "DepositShield-Ingestion/1.0"}


async def fetch_source(url: str) -> str:
    """Fetch raw text content from an official source URL."""
    async with httpx.AsyncClient(follow_redirects=True, timeout=_TIMEOUT, headers=_HEADERS) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text
