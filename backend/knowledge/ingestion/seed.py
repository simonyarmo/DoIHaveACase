"""CLI entry point: seed `law_freshness`, the Foundry IQ state law knowledge
base, and the document template knowledge base.

Usage: python -m knowledge.ingestion.seed
"""

import asyncio
from pathlib import Path

from database import async_session_factory
from knowledge.ingestion import pipeline, uploader
from knowledge.ingestion.sources import registry

TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "documents" / "templates"


async def main() -> None:
    async with async_session_factory() as db:
        for state in registry.list_states():
            result = await pipeline.run_seed(db, state)
            print(result)

    template_paths = sorted(TEMPLATES_DIR.glob("*.yaml"))
    registered = uploader.register_document_templates(template_paths)
    print({"document_templates": registered})


if __name__ == "__main__":
    asyncio.run(main())
