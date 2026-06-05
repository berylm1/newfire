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

## Governed agent workflow

All CEO-agent changes must use:

```text
GitHub issue -> branch -> tests -> PR -> human review -> merge
```

No agent should push directly to `main`, deploy, restart services, run production migrations, or edit secrets.
