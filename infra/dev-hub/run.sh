#!/usr/bin/env bash
# Deploy NewFire dev hub on america.
# Idempotent: rebuilds image, stops old container, starts new one bound to 127.0.0.1:4003.
# cloudflared dev.newfire.app rule is expected to point at http://localhost:4003 (see ../cloudflared/config.yml).
set -euo pipefail

IMAGE="newfire/devhub:local"
CONTAINER="newfire-devhub"
HOST_PORT="127.0.0.1:4003"

echo "==> Building image $IMAGE"
docker build -t "$IMAGE" .

echo "==> Stopping any existing $CONTAINER"
docker rm -f "$CONTAINER" 2>/dev/null || true

echo "==> Starting $CONTAINER on $HOST_PORT"
docker run -d \
  --name "$CONTAINER" \
  --restart unless-stopped \
  -p "$HOST_PORT:80" \
  "$IMAGE"

echo "==> Waiting 2s for nginx to settle"
sleep 2

echo "==> Local health check"
curl -sf -o /dev/null -w "devhub HTTP %{http_code}\n" "http://${HOST_PORT}/healthz" || \
  { echo "FAIL: devhub did not respond"; docker logs --tail 30 "$CONTAINER"; exit 1; }

echo ""
echo "Done."
echo "  Local:  http://${HOST_PORT}/"
echo "  Public: https://dev.newfire.app/  (after cloudflared rule swap)"
