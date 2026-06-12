"""Validates extracted state law markdown against the schema defined in
`.claude/docs/phase-02-law-schema.md` and flags material legal changes for
human review before publishing.
"""

import re
from dataclasses import dataclass, field

SCHEMA_SECTIONS = [
    "1. STATUTE REFERENCE",
    "2. DEPOSIT LIMITS",
    "3. HOLDING REQUIREMENTS",
    "4. MOVE-OUT NOTICE REQUIREMENTS",
    "5. RETURN DEADLINE",
    "6. ITEMIZATION REQUIREMENTS",
    "7. ALLOWABLE DEDUCTIONS",
    "7a. WEAR AND TEAR DEFINITION",
    "8. PENALTIES FOR WRONGFUL WITHHOLDING",
    "8a. BAD FAITH DEFINITION",
    "9. DEMAND LETTER",
    "10. FILING INFORMATION",
    "11. SERVICE OF PROCESS",
    "12. LOCAL VARIATIONS",
    "13. AGENT DECISION RULES",
    "14. COMMON LANDLORD DEFENSES",
    "15. REVISION HISTORY",
]

# Sections whose content materially affects agent legal reasoning — any
# change here must go through human review before publishing.
CRITICAL_SECTIONS = [
    "2. DEPOSIT LIMITS",
    "5. RETURN DEADLINE",
    "7. ALLOWABLE DEDUCTIONS",
    "8. PENALTIES FOR WRONGFUL WITHHOLDING",
    "10. FILING INFORMATION",
    "13. AGENT DECISION RULES",
]

REQUIRED_HEADER_FIELDS = ["Last Verified", "Source", "Next Review Due", "Status"]

_HEADER_PATTERN = re.compile(r"^## (Last Verified|Source|Next Review Due|Status): (.+)$", re.MULTILINE)
_SECTION_PATTERN = re.compile(r"^## (\d+a?\. .+)$", re.MULTILINE)


@dataclass
class ValidationResult:
    is_valid: bool
    needs_review: bool
    missing_sections: list[str] = field(default_factory=list)
    missing_header_fields: list[str] = field(default_factory=list)
    changed_critical_sections: list[str] = field(default_factory=list)


def extract_header(markdown: str) -> dict[str, str]:
    """Extract the four header fields: Last Verified, Source, Next Review Due, Status."""
    return {key: value.strip() for key, value in _HEADER_PATTERN.findall(markdown)}


def extract_sections(markdown: str) -> dict[str, str]:
    """Split markdown into {section_heading: body} by '## N. NAME' headings."""
    matches = list(_SECTION_PATTERN.finditer(markdown))
    sections: dict[str, str] = {}
    for i, match in enumerate(matches):
        heading = match.group(1).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)
        sections[heading] = markdown[start:end].strip()
    return sections


def validate_markdown(markdown: str, *, existing_markdown: str | None = None) -> ValidationResult:
    """Check schema completeness and diff critical sections against the existing version, if any."""
    sections = extract_sections(markdown)
    missing = [name for name in SCHEMA_SECTIONS if name not in sections]

    header = extract_header(markdown)
    missing_header = [name for name in REQUIRED_HEADER_FIELDS if name not in header]

    changed_critical: list[str] = []
    if existing_markdown:
        existing_sections = extract_sections(existing_markdown)
        for name in CRITICAL_SECTIONS:
            if sections.get(name, "") != existing_sections.get(name, ""):
                changed_critical.append(name)

    return ValidationResult(
        is_valid=not missing and not missing_header,
        needs_review=bool(changed_critical),
        missing_sections=missing,
        missing_header_fields=missing_header,
        changed_critical_sections=changed_critical,
    )
