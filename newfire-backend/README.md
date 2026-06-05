# NewFire Backend

Load-bearing Express/Postgres backend for NewFire.

## Source-control safety

This repository intentionally tracks source code, migrations, package metadata, and workflow templates only.

Do **not** commit:

- `.env` or `.env.*` files
- production database dumps or backups
- private keys, certificates, or API tokens
- client source documents or uploaded knowledge files
- generated logs, build output, or `node_modules/`

Production/runtime secrets must come from host environment variables or deployment secret stores.

## Important runtime note

The backend requires `DB_PASSWORD` at startup. Other integrations such as OpenClaw, APISIX, Qdrant, Ollama, Stripe, and Paperclip should be configured by environment variables in the deployment environment.

## Security controls

The backend applies baseline HTTP security middleware at startup:

- `helmet` security headers, with `X-Powered-By` disabled.
- explicit CORS allowlist via `CORS_ALLOWED_ORIGINS` or `ALLOWED_ORIGINS` as a comma-separated list.
- `X-Request-ID` propagation/generation for request tracing.
- global API rate limiting via `API_RATE_LIMIT_WINDOW_MS` and `API_RATE_LIMIT_MAX`.
- stricter auth endpoint rate limiting via `AUTH_RATE_LIMIT_WINDOW_MS` and `AUTH_RATE_LIMIT_MAX`.
- `TRUST_PROXY_HOPS` for deployments behind a reverse proxy/load balancer.

If no CORS env var is supplied, the default browser origins are `https://newfire.app`, `https://www.newfire.app`, `http://localhost:3000`, and `http://localhost:5173`. Non-browser/server-to-server requests without an `Origin` header remain allowed.

## Governed agent workflow

All CEO-agent changes must use:

```text
GitHub issue -> branch -> tests -> PR -> human review -> merge
```

No agent should push directly to `main`, deploy, restart services, run production migrations, or edit secrets.
