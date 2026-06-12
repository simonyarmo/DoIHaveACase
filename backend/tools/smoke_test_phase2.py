"""Phase 2 smoke test — knowledge bases and ingestion pipeline.

Run from `backend/` with the venv active:

    python tools/smoke_test_phase2.py

Exercises (without needing a running uvicorn server or Celery worker):
  - GET /knowledge/status/{TX,CA,FL}  — seeded statuses
  - POST /knowledge/ingest/ZZ         — unsupported state -> 404
  - POST /knowledge/ingest/CA         — on-demand ingest -> {"status": "ingesting", ...}
  - GET /knowledge/status/TX (no auth) -> 401
  - Azure AI Search index document counts
  - Azure Blob Storage blob presence

Triggering /knowledge/ingest/CA flips CA's `law_freshness` row to
status="ingesting"; this script re-runs seed mode for CA at the end to
restore it to "ready" with a correct `next_review`.

Requires AZURE_*, SUPABASE_*, and CELERY_* settings in `backend/.env` to be
configured (same as the running app).
"""

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from httpx import ASGITransport, AsyncClient
from jose import jwt

from config import settings
from database import async_session_factory
from knowledge.ingestion import pipeline
from main import app
from services import blob_storage, search_index

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name}" + (f" - {detail}" if detail else ""))


def make_token() -> str:
    return jwt.encode(
        {
            "sub": "00000000-0000-0000-0000-000000000001",
            "email": "smoke-test@example.com",
            "aud": "authenticated",
            "exp": int(time.time()) + 3600,
        },
        settings.supabase_jwt_secret,
        algorithm="HS256",
    )


async def check_api() -> None:
    token = make_token()
    headers = {"Authorization": f"Bearer {token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for state, expected_status in [("TX", "ready"), ("CA", "ready"), ("FL", "stub")]:
            r = await client.get(f"/knowledge/status/{state}", headers=headers)
            body = r.json() if r.status_code == 200 else {}
            check(
                f"GET /knowledge/status/{state} -> {expected_status}",
                r.status_code == 200 and body.get("status") == expected_status,
                f"got {r.status_code} {body}",
            )

        r = await client.post("/knowledge/ingest/ZZ", headers=headers)
        check("POST /knowledge/ingest/ZZ -> 404 (unsupported state)", r.status_code == 404, f"got {r.status_code}")

        r = await client.post("/knowledge/ingest/CA", headers=headers)
        body = r.json() if r.status_code == 200 else {}
        check(
            "POST /knowledge/ingest/CA -> ingesting",
            r.status_code == 200 and body == {"status": "ingesting", "estimated_seconds": 120},
            f"got {r.status_code} {body}",
        )

        r = await client.get("/knowledge/status/TX")
        check("GET /knowledge/status/TX without auth -> 401", r.status_code == 401, f"got {r.status_code}")


def check_search_indexes() -> None:
    expected_counts = {
        settings.foundry_kb_state_law: 34,  # 17 sections each for TX and CA
        settings.foundry_kb_court_procedures: 2,
        settings.foundry_kb_document_templates: 6,
    }
    for index_name, expected_count in expected_counts.items():
        try:
            count = search_index.get_search_client(index_name).get_document_count()
        except Exception as exc:  # noqa: BLE001 - report as a failed check, not a crash
            check(f"Azure AI Search index {index_name!r} reachable", False, f"error: {exc}")
            continue
        check(f"Azure AI Search index {index_name!r} has {expected_count} docs", count == expected_count, f"{count} docs")


def check_blobs() -> None:
    container = settings.azure_blob_container_knowledge
    container_client = blob_storage.get_blob_service_client().get_container_client(container)
    try:
        blob_names = {b.name for b in container_client.list_blobs()}
    except Exception as exc:  # noqa: BLE001 - report as a failed check, not a crash
        check(f"Blob container {container!r} reachable", False, f"error: {exc}")
        return

    for expected_blob in [
        "state-law/TX.md",
        "document-templates/demand_letter.yaml",
        "document-templates/small_claims_petition.yaml",
        "document-templates/amended_petition.yaml",
        "document-templates/motion_to_amend.yaml",
        "document-templates/motion_default_judgment.yaml",
        "document-templates/evidence_cover_sheet.yaml",
    ]:
        check(f"Blob {container}/{expected_blob} exists", expected_blob in blob_names)


async def restore_ca_seed_state() -> None:
    """POST /knowledge/ingest/CA above left law_freshness.CA at status='ingesting';
    re-run seed mode to restore it to 'ready' with a correct next_review.
    """
    async with async_session_factory() as db:
        await pipeline.run_seed(db, "CA")


async def run_async_checks() -> None:
    # Both functions touch the async SQLAlchemy engine, which pools connections
    # tied to the running event loop — run them in the same asyncio.run() call
    # to avoid "Event loop is closed" errors on the pooled connection.
    await check_api()
    await restore_ca_seed_state()


def main() -> int:
    asyncio.run(run_async_checks())
    check_search_indexes()
    check_blobs()

    failed = [name for name, ok, _ in results if not ok]
    print()
    print(f"{len(results) - len(failed)}/{len(results)} checks passed")
    if failed:
        print("FAILED:")
        for name in failed:
            print(f"  - {name}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
