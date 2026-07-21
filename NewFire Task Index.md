# NewFire Task Index

Purpose: track NewFire implementation tasks, especially production/CEO requests that need follow-through.

## Open tasks

- [[2026-06-02 - Nightly GitHub Code Review Agent from Patrick]] — CEO request to create a nightly GitHub code-review/implementation agent that audits NewFire for bugs, performance issues, business-role gaps, orphan/scaffolded features, generic CRUD-only modules, disconnected features, and incomplete end-to-end flows; target report email by 4:00 AM.
- [[2026-06-02 - Minisforum Nightly Code Agent Deployment Plan]] — corrected deployment plan: the real agent should run on the NewFire Minisforum system, not on the Raspberry Pi.
- [[2026-06-04 - CEO Agent Continuation Implementation Plan]] — next implementation plan: continue from issue #2, inspect/salvage the partial OpenHands run, then move through branch/PR review safely.
- [[2026-06-04 - CEO Agent Issue 2 PR Notes]] — PR notes for the first governed implementation branch replacing the OpenClaw classifier stub with tested routing logic.
- [[2026-06-04 - CEO Agent Issue 4 RAG Memory Plan PR Notes]] — issue #4 docs/design PR for RAG + persistent memory, including source-control blocker and rollout plan.
- [[2026-06-04 - CEO Agent Backend Source Control PR Notes]] — PR #9 vendors the load-bearing backend baseline into GitHub under `newfire-backend/`, giving issue #3/#4 implementation work a governed source-control path.
- [[2026-06-04 - CEO Directive Full Platform Readiness Agent]] — new CEO directive decomposed into six governed agent lanes: codebase intelligence, gap/orphan audit, security, performance, testing/resilience, and production-readiness scoring.
- [[2026-06-05 - CEO Report Operating Brief]] — CEO-ready reporting frame for lanes (a)-(f), PR #21 evidence status, and issue #22 for a GitHub-wide OpenClaw agent control plane.
- [[2026-06-05 - CEO Agent Issue 17 Security Controls PR Notes]] — PR #24 implements baseline backend HTTP security controls: CORS allowlist, Helmet headers, request IDs, and auth/API rate limits.
- [[2026-06-05 - CEO Agent Issue 18 Tenant RBAC Harness PR Notes]] — PR #25 adds backend tenant/RBAC integration coverage for signup/login, company creation, tenant assignment, tenant-scoped agent access, and cross-tenant denial.
- [[2026-06-05 - CEO Agent Issue 19 Webhook Security Regression PR Notes]] — PR #26 adds webhook invalid-signature, malformed-payload, secret non-leakage, and duplicate event idempotency regression coverage.
- [[2026-06-05 - CEO Agent Issue 11 Product Gap Audit PR Notes]] — PR #30 adds issue #11 product gap/orphan audit and creates implementation issues #27, #28, and #29.
- [[2026-06-05 - CEO Agent Issue 27 Source-Control Audit Gate PR Notes]] — PR #31 adds the source-control manifest and strict audit gate; currently confirms 4 governed surfaces and 5 source-control blockers.
- [[2026-06-05 - CEO Agent Issue 16 Dependency Hardening PR Notes]] — PR #23 reduces backend package-lock audit from 11 moderate/high vulnerabilities to 0 reported vulnerabilities.

## Related NewFire notes

- [[NewFire Mission and May 1 Goal]]
- [[MiniMax M3 Hybrid Architecture for NewFire]]
