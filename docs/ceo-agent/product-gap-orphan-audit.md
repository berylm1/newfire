# Product Gap, Missing Feature, and Orphan Feature Audit

Purpose: satisfy CEO directive lane **B** by comparing NewFire's documented product promises against the currently GitHub-governed source in this repository.

Issue: [#11 CEO directive: product gap, missing feature, and orphan feature audit](https://github.com/berylm1/newfire/issues/11)

## Executive summary

NewFire has a credible backend foundation, but the product is not yet fully reportable as production-complete because several load-bearing pieces are either outside the confirmed GitHub control plane, only partially wired end-to-end, or documented as future workflow automation without a customer-facing implementation path.

Highest-value findings:

1. **GitHub/source-control gap blocks full CEO auditability.** `backend-source.md` says the frontend, NSS services, MCP server, and SDK live in separate local repos or Mac paths with unknown/absent GitHub remotes. This prevents a true end-to-end audit across frontend/API/backend/agent/deployment.
2. **Onboarding is backend-present but not yet product-complete.** The backend exposes `/onboarding/chat` and `/onboarding/activate`, but activation trusts submitted agent data rather than a persisted, validated AI interview artifact, and provisioning success/failure is not yet turned into a guided customer recovery flow.
3. **Agent task execution is asynchronous but not yet operationally closed-loop.** `/agent/delegate`, `/agent/tasks`, and Paperclip/OpenHands hooks exist, but completion notification depends on a user polling the task endpoint; recurring workflow triggers and SLA/reporting dashboards remain documented gaps.
4. **Scaffolds exist without promotion/retirement decisions.** `backend-source.md` explicitly calls out MCP server and SDK scaffolds, and the repository docs describe frontend/NSS surfaces whose active source is not in this repo.
5. **Product gap reporting should be PR-first.** The right next step is not to edit production or merge broad rewrites; it is to convert the top gaps into contained implementation issues and PRs with verification evidence.

## Evidence scanned

- `backend-source.md`
- `Things that need to change.md`
- `docs/ceo-agent/service-inventory.md`
- `docs/ceo-agent/performance-and-readiness-scorecard.md`
- `newfire-backend/src/server.js`
- `newfire-backend/src/paperclip.js`
- `newfire-backend/src/orchestrator.js`
- `newfire-backend/src/webhooks.js`
- `newfire-backend/src/db.js`
- repository file inventory and backend route inventory

## Gap matrix

### G-001 — Full platform source is not under one verified GitHub control plane

- **Expected behavior:** The CEO can ask the agent to inspect, secure, benchmark, and improve every NewFire service from GitHub-governed source.
- **Observed implementation:** `newfire-backend/` is present in this repo, but `backend-source.md` lists frontend, NSS control/runner/portal/router, MCP, and SDK sources in external local paths or separate local repos. Remote status is unknown for several; frontend previously had no remote configured.
- **Evidence paths:** `backend-source.md:7-17`, `backend-source.md:38-56`, `backend-source.md:71-76`.
- **Severity:** Critical for CEO reporting and OpenClaw-for-all-GitHub governance.
- **Recommended PR:** Add a source-control manifest and import/remote-verification plan that refuses implementation on untracked load-bearing services until each service has a GitHub-backed repo or approved vendored baseline.
- **Converted issue:** #27.

### G-002 — Frontend product journeys are described but not auditable in this repository

- **Expected behavior:** Landing, login, dashboard, chat, developer portal, onboarding, admin dashboard, team dashboard, and agent-task UI should be inspectable and testable with backend routes.
- **Observed implementation:** `backend-source.md` documents those pages, but no `newfire-frontend/src` files exist in this repo. Backend routes exist, but UI flow quality cannot be verified from this PR control plane.
- **Evidence paths:** `backend-source.md:38-44`, repository file inventory found no tracked frontend source under `newfire-frontend/src`.
- **Severity:** High.
- **Recommended PR:** Bring frontend source under GitHub control or add a verified sibling-repo link plus cross-repo audit procedure; then add E2E journey tests for auth/onboarding/chat/billing/tasks.

### G-003 — Onboarding interview to provisioned company is only partially productized

- **Expected behavior:** Signup should lead to a guided AI interview, persisted interview answers, validated agent recommendations, company creation, Paperclip/OpenClaw provisioning, and a clear user-facing success/retry state.
- **Observed implementation:** `/onboarding/chat` calls Ollama directly. `/onboarding/activate` accepts `companyName`, `description`, and `agents` from the request body and calls `createCompanyForUser`. Paperclip provisioning is fail-soft and records status, but there is no persisted interview artifact or customer recovery workflow in the backend route.
- **Evidence paths:** `newfire-backend/src/server.js:1049-1089`, `newfire-backend/src/paperclip.js:110-167`, `Things that need to change.md:190-200`.
- **Severity:** High.
- **Recommended PR:** Add an onboarding session table/harness, server-side recommendation schema validation, activation from persisted interview data, provisioning status endpoint, and retry/recovery path.
- **Converted issue:** #28.

### G-004 — Agent task completion depends on frontend polling, not backend orchestration

- **Expected behavior:** Customer-delegated coding/agent tasks should have reliable lifecycle transitions, completion events, timeout/SLA tracking, and notifications even if the user closes the browser.
- **Observed implementation:** `/agent/delegate` persists task rows and `/agent/tasks/:id` polls Paperclip. Completion webhook emission is first-observed and explicitly waits for SPA polling.
- **Evidence paths:** `newfire-backend/src/server.js:633-777`, especially `newfire-backend/src/server.js:723-727`.
- **Severity:** High.
- **Recommended PR:** Add a backend task reconciliation worker or scheduled poller with idempotent completion events, timeout marking, and SLA metrics.
- **Converted issue:** #29.

### G-005 — Recurring workflow automation trigger layer is not productized

- **Expected behavior:** Clients can configure repeatable business workflows such as weekly content batches, intake triage, or legal pre-research with schedule/trigger controls.
- **Observed implementation:** Docs say OpenClaw cron covers simple schedules, but a productized trigger UI/layer remains undecided.
- **Evidence paths:** `Things that need to change.md:183-189`, `Things that need to change.md:212-215`.
- **Severity:** Medium-high.
- **Recommended PR:** Design a workflow trigger model, backend CRUD routes, Paperclip/OpenClaw dispatch integration, and frontend controls after source-control gap is resolved.

### G-006 — MCP server and SDK are scaffolds without promotion or retirement decision

- **Expected behavior:** Scaffolds should either be promoted into supported product surfaces with tests/docs or retired from the launch plan.
- **Observed implementation:** `backend-source.md` calls MCP and SDK scaffold-only/not-published surfaces.
- **Evidence paths:** `backend-source.md:15-16`, `backend-source.md:53-56`.
- **Severity:** Medium.
- **Recommended PR:** Create a scaffold decision record: promote MCP for controlled tools and SDK for customer integrations, or explicitly remove them from CEO readiness scope until after launch.

### G-007 — Billing exists but lacks full customer/revenue flow proof

- **Expected behavior:** Pricing tier selection, checkout, webhook tier activation, portal management, downgrade/cancel behavior, and UI messaging should be covered as one E2E revenue flow.
- **Observed implementation:** Backend routes exist for `/tiers`, `/billing/checkout`, `/billing/portal`, and `/webhooks/stripe`, but the current audit has not verified UI and full E2E coverage.
- **Evidence paths:** `newfire-backend/src/server.js:589-631`, `newfire-backend/src/server.js:779-893`, `docs/ceo-agent/performance-and-readiness-scorecard.md:155-157`.
- **Severity:** Medium-high.
- **Recommended PR:** Add Stripe test-mode E2E harness with checkout/session mocks, webhook signature fixtures, tenant tier assertions, and frontend pricing/dashboard verification once frontend source is controlled.

### G-008 — Demo chat is useful but hardcoded to one sample business

- **Expected behavior:** Demo surface should either be explicitly a fixed marketing demo or support per-demo business configuration.
- **Observed implementation:** `/demo/chat` hardcodes `Brand Brightly`, `demo_marketing_agency`, and NewFire conversion copy.
- **Evidence paths:** `newfire-backend/src/server.js:909-1045`.
- **Severity:** Medium.
- **Recommended PR:** Add a demo configuration table or clearly keep this as a marketing-only demo and exclude it from customer production readiness scoring.

### G-009 — Admin/CRM/ROI surfaces exist but need role and business-flow tests

- **Expected behavior:** Admin/CRM/ROI should support safe internal operations with tested role boundaries and audit trails.
- **Observed implementation:** Multiple admin routes exist, but product audit did not find a full admin workflow test harness on `main`.
- **Evidence paths:** `newfire-backend/src/server.js:219-540`.
- **Severity:** Medium.
- **Recommended PR:** Add admin role-boundary and CRUD regression tests after PR #25-style test harness lands.

## Orphan / scaffold / partial list

- **Frontend source:** Documented as React/Vite app, but absent from this repo. Decision: **complete source-control integration** before claiming full UI readiness.
- **NSS control/runner/portal/router:** Documented services with separate source locations. Decision: **verify GitHub remotes or import baseline** before agent implementation.
- **MCP server scaffold:** Documented scaffold only. Decision: **promote or defer** with explicit CEO scope label.
- **Client SDK scaffold:** Documented not published. Decision: **promote or defer** with explicit package/test/release checklist.
- **Recurring workflow trigger layer:** Product idea documented but not implemented as customer-facing controls. Decision: **design then implement** after core task lifecycle closes.
- **Demo chat:** Hardcoded marketing demo. Decision: **keep as marketing demo** unless CEO wants it generalized.

## Top 3 implementation issues created

1. **#27 — Source-control manifest for full platform auditability**
   - Blocks CEO promise to inspect and improve any codebase unless all load-bearing services are GitHub-governed.
2. **#28 — Productize onboarding interview to provisioned company flow**
   - Converts onboarding from request-body activation to persisted/validated/recoverable workflow.
3. **#29 — Add backend agent task reconciliation worker**
   - Makes delegated tasks operationally closed-loop without relying on a user watching the UI.

## CEO reporting line

> We completed the first product gap and orphan-feature audit. The biggest blocker is not backend code volume; it is full platform governability. The backend is now visible, but frontend/NSS/MCP/SDK source-control status must be resolved, onboarding must become a persisted validated flow, and agent task execution needs backend reconciliation so it is reliable without browser polling.

## Next recommended sequence

1. Resolve #27 first so the agent can truthfully audit all GitHub-governed services.
2. Then implement #28 onboarding completion because it is a direct customer conversion path.
3. Then implement #29 task reconciliation because it makes agent work reliable and reportable.
4. Continue #20 performance benchmarking after source-control and lifecycle gaps are converted into testable services.
