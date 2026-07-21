# 2026-06-04 - CEO Agent Backend Source Control PR Notes

## Purpose

Put the load-bearing NewFire backend under GitHub branch/PR control so CEO-agent implementation work does not edit production source directly.

## Why this matters

The nightly CEO agent is supposed to audit and improve NewFire safely: issue → branch → tests → PR → human review. Issue #3 (tenant/RBAC integration tests) and the implementation side of issue #4 (RAG/memory) were blocked because the backend source existed on the Minisforum production worker but was not GitHub-backed.

## What changed

- Attempted to create a separate private GitHub repo, `newfire-backend`, but GitHub returned `403 Forbidden` for repo creation with the available token.
- Used the safe fallback: vendored the committed backend baseline into the existing `berylm1/newfire` repo under `newfire-backend/`.
- Updated repo `backend-source.md` so the tracked backend source location is discoverable.
- Preserved the production mirror boundary: future backend implementation should branch/PR from the tracked repo path, not edit `/home/newwaveclaw/newfire-backend` directly.

## GitHub PR

- PR: https://github.com/berylm1/newfire/pull/9
- Branch: `chore/backend-source-control-baseline`
- Commit: `d9df272 chore: vendor backend source-control baseline`
- Status at creation: open, mergeable clean, no check runs reported.

## Verification performed

- `node --check newfire-backend/src/*.js`
- `bash -n newfire-backend/scripts/openhands-cli`
- Lightweight committed-secret scan: no obvious secrets found.

## Safety constraints

- Do not merge without human review.
- Do not deploy, restart services, run migrations, or edit secrets from this PR.
- Keep issue #3 and issue #4 implementation work in governed branches after this baseline is reviewed/merged.

## Next actions

1. Human reviews PR #9 and confirms the backend baseline is safe to merge.
2. Once merged, reopen/unblock issue #3 tenant/RBAC integration tests.
3. Use the tracked backend source for the issue #4 RAG/memory schema and ingestion implementation after plan review.
4. Continue CEO-agent governance: issues first, branches/PRs only, no direct production edits.
