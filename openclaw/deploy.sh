#!/usr/bin/env bash
# OpenClaw v1 PR 1 deploy script.
# Run ON america from the directory containing this script + the openclaw tarball.
#
# What it does:
#   1. Reads DB_PASSWORD from the existing newfire-backend env so we never
#      paste the secret over SSH.
#   2. Materializes /home/newwaveclaw/openclaw-docker/ as the deploy root.
#   3. Writes .env-secrets with DB_PASSWORD and OPENCLAW_DEV_EMAIL (since the
#      CF Access policy is not yet up; dev-bypass keeps the service usable for
#      smoke tests until you create the policy and we swap to CF_ACCESS_AUD).
#   4. Applies the migration against newfire-db.
#   5. docker compose build + up -d.
#   6. Health and whoami smoke tests on loopback.

set -euo pipefail

DEPLOY_ROOT="/home/newwaveclaw/openclaw-docker"
BACKEND_ENV="/home/newwaveclaw/newfire-backend-docker/.env"
BUNDLE="/tmp/openclaw-v1-pr1.tar.gz"

red()    { printf '\033[31m%s\033[0m\n' "$*"; }
green()  { printf '\033[32m%s\033[0m\n' "$*"; }
blue()   { printf '\033[34m%s\033[0m\n' "$*"; }
yellow() { printf '\033[33m%s\033[0m\n' "$*"; }

blue "==> 1. extract bundle"
mkdir -p "$DEPLOY_ROOT"
tar -xzf "$BUNDLE" -C "$DEPLOY_ROOT"
green "    extracted to $DEPLOY_ROOT"

blue "==> 2. compose DB password from backend env (no SSH paste)"
if [ ! -r "$BACKEND_ENV" ]; then
  red "Cannot read $BACKEND_ENV (need sudo?). Trying with sudo..."
  DBP=$(sudo grep -E '^DB_PASSWORD=' "$BACKEND_ENV" | head -1 | cut -d= -f2-)
else
  DBP=$(grep -E '^DB_PASSWORD=' "$BACKEND_ENV" | head -1 | cut -d= -f2-)
fi
if [ -z "$DBP" ]; then
  red "Could not extract DB_PASSWORD. Set it manually in $DEPLOY_ROOT/.env-secrets."
  exit 1
fi
green "    DB_PASSWORD pulled (length=${#DBP})"

blue "==> 3. write .env-secrets"
umask 077
cat > "$DEPLOY_ROOT/.env-secrets" <<EOF
DB_PASSWORD=$DBP
# CF_ACCESS_AUD goes here AFTER you create the Cloudflare Access policy.
# For now, dev-bypass keeps the service callable from loopback so we can verify.
CF_ACCESS_AUD=
OPENCLAW_DEV_EMAIL=chisoba.9090@gmail.com
EOF
chmod 600 "$DEPLOY_ROOT/.env-secrets"
green "    secrets written, 0600 perms"

blue "==> 4. apply migration"
docker exec -i newfire-db psql -U newfire -d newfire < "$DEPLOY_ROOT/migrations/001_openclaw_schema.sql" 2>&1 | tail -8
green "    migration applied"

blue "==> 5. build image"
cd "$DEPLOY_ROOT"
docker compose build 2>&1 | tail -5

blue "==> 6. start container"
docker compose up -d
sleep 4
docker ps --filter "name=openclaw" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

blue "==> 7. health check"
for i in $(seq 1 20); do
  if curl -sf http://127.0.0.1:5500/v1/health > /dev/null; then
    green "    health OK after ${i}s"
    break
  fi
  sleep 1
done
curl -s http://127.0.0.1:5500/v1/health | python3 -m json.tool

blue "==> 8. whoami smoke (dev bypass active)"
curl -s http://127.0.0.1:5500/v1/whoami | python3 -m json.tool

blue "==> 9. dispatch smoke"
curl -s -X POST http://127.0.0.1:5500/v1/dispatch \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Edit this file and rename the function"}' \
  | python3 -m json.tool

yellow ""
yellow "Done. Service is up on http://127.0.0.1:5500."
yellow "Next: create CF Access policy for claw.newfire.app, fill CF_ACCESS_AUD,"
yellow "remove OPENCLAW_DEV_EMAIL, then 'docker compose up -d' again."
