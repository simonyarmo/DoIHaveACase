#!/usr/bin/env python3
"""PreToolUse guard: block direct `git push` to main/master.

DepositShield ships phases through PRs (branch -> PR -> /code-review ->
merge, see CLAUDE.md). This hook blocks the one shell invocation that would
bypass that flow — pushing directly to the protected branch — without
getting in the way of pushing feature branches or any other git/gh usage.
"""
import json
import re
import subprocess
import sys

PROTECTED = {"main", "master"}

# `git push` only counts when it actually starts a shell command — i.e. at
# the start of the string or right after a command separator/opener — not
# when "git push ..." merely appears inside a quoted string, echo, comment,
# or commit message heredoc.
PUSH_INVOCATION = re.compile(
    r"(?:^|&&|\|\||[;|]|\$\(|`|\n)\s*git\s+push\b(?P<rest>.*)"
)


def current_branch() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def push_destination(rest: str) -> str | None:
    """Branch this push targets, or None if it should fall back to the
    current branch (`git push`, `git push origin`, `git push origin HEAD`)."""
    tokens = [t for t in rest.split() if not t.startswith("-")]
    if len(tokens) < 2:
        return None

    refspec = tokens[1]
    dest = refspec.split(":", 1)[-1]
    if dest.startswith("refs/heads/"):
        dest = dest[len("refs/heads/"):]
    return None if dest in ("", "HEAD") else dest


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    command = payload.get("tool_input", {}).get("command", "")
    match = PUSH_INVOCATION.search(command)
    if not match:
        return 0

    dest = push_destination(match.group("rest"))
    targets_protected = (dest in PROTECTED) if dest is not None else (current_branch() in PROTECTED)

    if targets_protected:
        sys.stderr.write(
            "Blocked: direct push to main/master.\n"
            "DepositShield ships phases through PRs — branch, push the "
            "branch, `gh pr create`, run /code-review, then merge. "
            "See the 'Phase completion workflow' section in CLAUDE.md.\n"
        )
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
