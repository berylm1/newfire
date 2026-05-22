#!/usr/bin/env bash
# Deploy script run ON america (Minisforum) after the build context is SCP'd over.
# Adds ttyd web-terminal wrapper so codeep is reachable through cloudflared at
# codeep.newfire.app. Port 7681 bound to 127.0.0.1 only (cloudflared bridges to edge).
set -euo pipefail

IMAGE="newfire/codeep:local"
CONTAINER="codeep"
WORKSPACE_DIR="/mnt/cephfs-mgmt/codeep-workspaces"
NETWORK="newfire_shared"
HOST_TTYD_PORT="127.0.0.1:7681"

echo "==> Ensuring workspace dir exists on CephFS"
sudo mkdir -p "$WORKSPACE_DIR"
sudo chown -R 1000:1000 "$WORKSPACE_DIR"

echo "==> Building image $IMAGE (with ttyd + tmux)"
docker build -t "$IMAGE" .

echo "==> Stopping any existing $CONTAINER container"
docker rm -f "$CONTAINER" 2>/dev/null || true

echo "==> Starting $CONTAINER on $NETWORK with ttyd bound to $HOST_TTYD_PORT"
docker run -d \
  --name "$CONTAINER" \
  --restart unless-stopped \
  --network "$NETWORK" \
  -p "$HOST_TTYD_PORT:7681" \
  -v "$WORKSPACE_DIR":/workspace \
  --user 1000:1000 \
  "$IMAGE"

echo "==> Waiting 3s for container to settle"
sleep 3

echo "==> Container status:"
docker ps --filter "name=$CONTAINER" --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'

echo ""
echo "==> Verifying ttyd responds on $HOST_TTYD_PORT"
curl -sf -o /dev/null -w "ttyd HTTP %{http_code}\n" "http://${HOST_TTYD_PORT}/" || \
  { echo "FAIL: ttyd did not respond"; docker logs --tail 30 "$CONTAINER"; exit 1; }

echo ""
echo "==> Smoke test: vLLM reachable from inside container"
docker exec "$CONTAINER" sh -c 'curl -s --max-time 5 http://192.168.1.158:8000/v1/models | head -c 200' || \
  echo "WARN: vLLM smoke test failed (codeep may still work if vLLM is briefly down)"

echo ""
echo ""
echo "Done."
echo "  TUI access:     docker exec -it $CONTAINER tmux attach -t codeep"
echo "  Web (local):    http://${HOST_TTYD_PORT}/"
echo "  Web (public):   https://codeep.newfire.app/  (after cloudflared ingress + CF Access)"
