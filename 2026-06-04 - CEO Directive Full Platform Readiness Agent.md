# 2026-06-04 - CEO Directive Full Platform Readiness Agent

## CEO directive

Build the agent capability to:

1. Introspect, research, and understand any codebase.
2. Recommend gaps, missing features, orphan features, and code-quality fixes.
3. Identify security holes, ask how the platform can be compromised externally and internally, recommend improvements, and implement end to end.
4. Identify service-level performance bottlenecks, benchmark against industry standards, recommend improvements, and implement end to end.
5. Perform extensive end-to-end, regression, load, QA, chaos, integration testing, and fix discovered issues.
6. Provide a production-readiness and completion score for every service and feature.

## Interpretation

This is not a single code change. It is a standing CEO-agent operating system for NewFire. The agent needs six repeatable lanes:

- **Codebase intelligence lane** — map repos, services, routes, dependencies, tests, deployments, and ownership.
- **Product gap lane** — detect missing, generic, duplicate, disconnected, scaffold-only, and orphan features.
- **Security lane** — model internal/external compromise paths, then turn validated risks into hardening PRs.
- **Performance lane** — benchmark each service against concrete targets and turn bottlenecks into optimization PRs.
- **Quality/resilience lane** — expand E2E, regression, integration, load, QA, and chaos testing.
- **Readiness score lane** — score every service/feature with evidence, blockers, and next PRs.

## Guardrails

- No direct push to `main`.
- No direct production source edits.
- No deployment, service restart, migration, or secret change without explicit approval.
- Every implementation must be tied to a GitHub issue and PR.
- Findings are not enough; each high-confidence finding should become a contained issue with acceptance criteria and tests.

## Initial repo/service map from today

Inspected branch: `chore/backend-source-control-baseline` in `berylm1/newfire`, commit `d9df272`.

Current tracked surfaces include:

- `newfire-backend/` — Express/Postgres backend baseline, added in PR #9.
- `openclaw/` — OpenClaw service and classifier tests.
- `newfire_backend_docker/` — backend Docker/deployment artifacts.
- `infra/` — Cloudflare/codeep/dev-hub deployment artifacts.
- `blueprint/`, `progress/`, top-level docs — architecture and operating notes.

Large backend hotspots to inspect first:

- `newfire-backend/src/server.js` — 1109 lines.
- `newfire-backend/src/orchestrator.js` — 925 lines.
- `newfire-backend/src/ceo.js` — CEO/review agent logic.
- `newfire-backend/src/auth.js`, `tenant.js`, `webhooks.js`, `paperclip.js`, `db.js` — security/multi-tenant-critical areas.

## GitHub issue queue created from directive

The directive should be implemented as an issue queue, not one giant PR:

1. [#10 Platform codebase intelligence inventory](https://github.com/berylm1/newfire/issues/10).
2. [#11 Product gap/orphan feature audit](https://github.com/berylm1/newfire/issues/11).
3. [#12 Security threat model and hardening backlog](https://github.com/berylm1/newfire/issues/12).
4. [#13 Performance benchmark and bottleneck audit](https://github.com/berylm1/newfire/issues/13).
5. [#14 Testing/resilience expansion plan](https://github.com/berylm1/newfire/issues/14).
6. [#15 Production readiness/completion scorecard](https://github.com/berylm1/newfire/issues/15).

## Next implementation sequence

1. Review/merge PR #9 so backend source is officially tracked.
2. Run the codebase intelligence inventory first; it becomes the evidence map for all later audits.
3. Run security and tenant/RBAC work immediately after, because auth, tenancy, webhooks, and agent execution are compromise-sensitive.
4. Add benchmark/load tooling only after endpoints and service boundaries are mapped.
5. Produce the readiness scorecard after the first evidence pass, then update it after each PR.

## Evidence pass PR

Created PR: [#21 docs: add CEO readiness evidence pass](https://github.com/berylm1/newfire/pull/21).

What it contains:

- `scripts/ceo_readiness_audit.py` — read-only static scanner for service, route, env-var, and line-count inventory.
- `docs/ceo-agent/service-inventory.md` — evidence for issue #10.
- `docs/ceo-agent/security-threat-model.md` — initial threat model and hardening backlog for issue #12.
- `docs/ceo-agent/testing-resilience-matrix.md` — test/resilience matrix for issue #14.
- `docs/ceo-agent/performance-and-readiness-scorecard.md` — benchmark plan and scorecard snapshot for issues #13/#15.

Verification from PR branch:

- Scanner output: 4 service surfaces, 45 backend routes, 46 backend env dependencies.
- Syntax checks passed for key backend files: `server.js`, `auth.js`, `tenant.js`, `orchestrator.js`.
- Python compile check passed for the scanner.
- PR is open, clean, and mergeable.

Follow-up implementation issues:

- #16 dependency hardening.
- #17 CORS/security headers/auth rate limiting.
- #18 tenant/RBAC integration harness.
- #19 webhook signature/replay/idempotency tests.
- #20 local/staging benchmark harness.

## CEO-facing why

The CEO is asking for NewFire to become self-auditing and self-improving: the agent should understand the whole platform, expose hidden product/security/performance risks, convert them into governed work, implement fixes safely, and report whether each service is production-ready.
