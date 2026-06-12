"""LLM-assisted extraction of fetched state law content into the schema
defined in `.claude/docs/phase-02-law-schema.md`.
"""

from datetime import datetime, timedelta, timezone

from knowledge.ingestion.validator import SCHEMA_SECTIONS
from services import llm_client


def _system_prompt(state: str, source_url: str, review_frequency_days: int) -> str:
    today = datetime.now(timezone.utc).date()
    next_review = today + timedelta(days=review_frequency_days)
    sections = "\n".join(f"- {name}" for name in SCHEMA_SECTIONS)
    return (
        "You are a legal knowledge extraction engine for DepositShield, a tenant "
        "security-deposit dispute platform. Convert the supplied official statute text "
        "into a single markdown file that follows this exact schema. Field order, "
        "heading names, and section numbers are fixed — never rename, reorder, or omit "
        "a section. If the statute does not address a field, write "
        "'Not specified in statute' rather than guessing.\n\n"
        "The file must begin with this header block:\n"
        f"# {state} — Security Deposit Law\n"
        f"## Last Verified: {today.isoformat()}\n"
        f"## Source: {source_url}\n"
        f"## Next Review Due: {next_review.isoformat()}\n"
        "## Status: active\n\n"
        f"Required sections, in order, each as a level-2 heading ('## '):\n{sections}\n\n"
        "Separate each section with a horizontal rule ('---'). "
        "Output only the markdown file — no commentary."
    )


async def parse_state_law(
    state: str,
    source_url: str,
    raw_text: str,
    *,
    review_frequency_days: int,
    reference_markdown: str | None = None,
) -> str:
    """Extract `raw_text` into the state law markdown schema via the configured
    Azure OpenAI deployment. `reference_markdown` (e.g. TX.md) is supplied as a
    structural example for states being parsed for the first time.
    """
    messages = [{"role": "system", "content": _system_prompt(state, source_url, review_frequency_days)}]
    if reference_markdown:
        messages.append(
            {
                "role": "user",
                "content": (
                    f"Structural reference for another state — match this format exactly:\n\n{reference_markdown}"
                ),
            }
        )
    messages.append(
        {
            "role": "user",
            "content": f"State: {state}\nSource URL: {source_url}\n\nOfficial statute text:\n\n{raw_text[:60000]}",
        }
    )

    return await llm_client.chat_completion(messages, temperature=0.1)
