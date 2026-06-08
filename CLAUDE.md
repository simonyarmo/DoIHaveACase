# DepositShield

AI-powered legal guidance platform for tenant security-deposit disputes.
FastAPI/React/Supabase/Azure AI Foundry/Twilio. Built in 8 phases — see
`.claude/docs/INDEX.md` for the phase roadmap and `.claude/docs/phase-NN-*.md`
for each phase's spec (scaffold, schema, dependencies, etc.).

`main` currently contains the Phase 1 scaffold (backend skeleton, frontend
skeleton, auth, migrations, placeholder screens for every later-phase route).

## Phase completion workflow

When a phase's implementation is done and verified (it runs, typechecks, and
you've manually exercised the golden path), ship it through a PR rather than
committing straight to `main`:

1. **Branch**: `git checkout -b phase-NN-<short-description>` off `main`.
2. **Commit**: commit the phase's work with a message describing what the
   phase added (reference the phase doc, not implementation trivia).
3. **Push + open PR**: `git push -u origin phase-NN-<short-description>`,
   then `gh pr create --title "Phase NN: <description>" --body "..."`
   summarizing what the phase delivers and how to verify it.
4. **Review**: run `/code-review` (high effort) against the PR. Read every
   CONFIRMED and PLAUSIBLE finding it returns.
5. **Address findings**: fix anything CONFIRMED at medium-or-higher severity
   before merging. For PLAUSIBLE findings or low-severity cleanup items, use
   judgment — note in the PR which ones you're deferring and why, rather than
   silently dropping them. Push fixes to the same branch; re-run `/code-review`
   if you made non-trivial changes.
6. **Merge**: once the review is clean (no unresolved CONFIRMED issues at
   medium-or-higher severity), merge with `gh pr merge --squash --delete-branch`.

Direct pushes to `main`/`master` are blocked by a hook
(`.claude/hooks/guard-main-push.py`) — this workflow is the only path in.

### Notes
- `/code-review` is free to run as part of this flow. `/code-review ultra` /
  `/ultrareview` is a separate, billed, user-triggered cloud review — don't
  invoke it as part of an automated phase-completion flow.
- Don't merge with known CONFIRMED bugs just to "finish the phase" — a phase
  isn't done until its PR is mergeable on its own merits.
- If `gh` isn't authenticated yet, the PR step will fail with an auth error —
  that's a one-time `gh auth login` the user needs to run interactively.
