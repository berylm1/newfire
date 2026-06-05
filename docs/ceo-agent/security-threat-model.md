# Security Threat Model and Hardening Backlog

Scope: initial read-only threat model for the tracked NewFire source. This does not claim penetration-test coverage. It identifies compromise paths that must be tested/hardened through governed PRs.

## External compromise paths

### 1. Authentication abuse

Potential paths:

- Signup/login brute force.
- Credential stuffing.
- Long-lived JWT theft/replay.
- Missing lockout/throttle behavior.

Current evidence:

- `auth.js` requires `JWT_SECRET` of at least 32 chars.
- Passwords use bcrypt.
- No backend package or middleware currently shows explicit auth rate limiting.

Recommended implementation:

- Add auth-specific rate limiting.
- Add failed-login telemetry.
- Add tests for invalid token, expired token, missing token, and repeated failed login attempts.

### 2. Permissive CORS / browser-origin abuse

Potential paths:

- Browser-origin abuse if API is exposed cross-origin without allowlist.
- Token leakage impact increases if any origin can call API with bearer tokens.

Current evidence:

- `server.js` uses `app.use(cors())` with default behavior.

Recommended implementation:

- Add explicit production CORS allowlist.
- Fail closed when `NODE_ENV=production` and allowed origins are not configured.
- Add tests for allowed and disallowed origins.

### 3. Missing security headers

Potential paths:

- Clickjacking, MIME sniffing, browser feature abuse, weak default response posture.

Current evidence:

- `helmet` is not in `package.json`.

Recommended implementation:

- Add `helmet` with production-safe defaults.
- Verify headers in integration tests.

### 4. Dependency vulnerabilities

Evidence from `npm audit --package-lock-only` in `newfire-backend/`:

- Total: 11 vulnerabilities.
- High: 4.
- Moderate: 7.
- Notable chains:
  - `bcrypt` -> `@mapbox/node-pre-gyp` -> `tar` high path-traversal advisories.
  - `express` / `body-parser` -> `qs` moderate DoS advisory.
  - `prisma` / `@prisma/dev` -> `hono`, `@hono/node-server`, `fast-uri` advisories.

Recommended implementation:

- Open a dependency-hardening PR.
- Prefer controlled dependency upgrade with lockfile diff and syntax/regression checks.
- Re-run `npm audit --package-lock-only` and document residuals.

### 5. Webhook abuse

Potential paths:

- Unsigned or weakly signed inbound webhooks.
- Replay of valid webhook payloads.
- Duplicate processing/idempotency failure.
- SSE stream exposure.

Current evidence:

- `webhooks.js` and Stripe raw-body path exist.
- Dedicated regression tests are not yet present.

Recommended implementation:

- Add invalid signature, stale timestamp, replay, duplicate delivery, and SSE authorization tests.

### 6. Tenant/RBAC bypass

Potential paths:

- User accesses another tenant/company's agents, chat history, tasks, Qdrant collection, metrics, billing portal, or webhooks.
- Admin/dev routes reachable by non-admin users.

Current evidence:

- Issue #3 already tracks tenant/RBAC integration tests.
- Backend source is now tracked after PR #9 merge, so implementation can proceed safely.

Recommended implementation:

- Complete issue #3 first among security implementation work.

### 7. Agent execution and internal pivot

Potential paths:

- `/dev/openhands` accepts instruction/repo/branch/task input and reaches a shim service.
- Agent workers may receive Git tokens or repo URLs.
- OpenClaw/Paperclip/OpenHands can become internal compromise bridges if authorization, sandboxing, or token scoping is weak.

Recommended implementation:

- Add tests for role gates on developer endpoints.
- Restrict allowed repo hosts/branches where possible.
- Ensure no persistent GitHub token storage on worker.
- Add timeout and failure-mode tests.

## Internal compromise paths

- Production host secret leakage from env files or logs.
- Overprivileged DB user.
- CI/GitHub token misuse.
- Agent sandbox escape or repo write outside allowed checkout.
- Docker network lateral movement from backend to Postgres/Qdrant/APISIX/OpenClaw.
- Metrics or admin endpoints exposed outside intended network.

## Prioritized hardening backlog

1. Tenant/RBAC integration tests (#18; also related to original #3).
2. Dependency hardening for `newfire-backend` audit findings (#16).
3. Explicit CORS allowlist and security headers (#17).
4. Auth rate limiting and invalid-token regression tests (#17/#18).
5. Webhook replay/signature/idempotency tests (#19).
6. Agent execution boundary tests and repo-token handling review.
7. Metrics/admin ingress exposure verification.

## Non-goals for this pass

- No destructive scans.
- No credential guessing.
- No production load or chaos tests.
- No secret reads or changes.
