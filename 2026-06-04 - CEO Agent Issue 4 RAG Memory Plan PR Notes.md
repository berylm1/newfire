# 2026-06-04 - CEO Agent Issue #4 RAG/Memory Plan PR Notes

## PR

- GitHub PR: https://github.com/berylm1/newfire/pull/8
- Branch: `docs/issue-4-rag-memory-plan`
- Remote commit: `235ff34 docs: add RAG memory implementation plan`
- Issue: #4 — Create RAG/memory implementation plan from current NewFire gaps

## What happened

After issue #2 produced the first governed implementation PR, the next queue item was issue #3 for tenant/RBAC tests.

Issue #3 was safely blocked because the load-bearing backend source exists on the Minisforum at:

`/home/newwaveclaw/newfire-backend/`

but that directory is not currently a GitHub-backed repo on the worker. Editing it directly would bypass the CEO-agent rule of branch → PR → human review. I commented on issue #3 and labelled it `needs-human`.

Then I moved to issue #4, which is docs/design-first and safe to do in the GitHub repo.

## Files added

- `RAG_MEMORY_IMPLEMENTATION_PLAN.md`

## Plan covers

- Current tracked RAG/Qdrant artifacts:
  - `newfire_backend_docker/SEEDING_GUIDE.md`
  - `seed_company_content.sh`
  - `backfill_collections.py/.sh`
  - `progress/qdrant_test/`
- Current backend source paths:
  - `src/orchestrator.js`
  - `src/db.js`
  - `src/server.js`
  - `src/tenant.js`
- Governance blocker: backend source must enter GitHub before implementation.
- MVP architecture for RAG + persistent memory.
- Proposed tables:
  - `knowledge_sources`
  - `knowledge_chunks`
  - `agent_memories`
  - `rag_events`
- Security/privacy requirements.
- Follow-up implementation issue list.
- Rollout order from docs → source control → schema → ingestion → retrieval → memory → privacy policy → runbook.

## Verification

- Documentation-only PR.
- PR state: open.
- Mergeability: clean.
- No production data accessed.
- No secrets added.
- No deployment, restart, migration, or live gateway/database mutation.

## Important note

The local Minisforum branch has a local commit from the first commit attempt (`b7cdcb3`), but the actual remote PR branch was created through the GitHub API because HTTPS git push on the worker lacked credentials. Remote PR branch is valid and points to `235ff34`.

This is acceptable for the docs PR, but the worker Git auth should be fixed before relying on normal `git push` for future code PRs.

## Next recommended CEO-agent task

Before implementation-heavy issue #3/#4 work can continue, create a governance/source-control task:

**Put `/home/newwaveclaw/newfire-backend` under GitHub control without committing secrets.**

After that, resume:

1. Issue #3 tenant/RBAC tests.
2. Issue #4 RAG/memory schema and ingestion implementation tasks.
3. Issue #5 demo/dev access docs cleanup if we need another safe docs-only task while source control is being fixed.
