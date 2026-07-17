#!/usr/bin/env bash
# Stop the router test cleanly. Leaves /opt/llamacpp-router/router.log in place
# for review, but kills the screen session and confirms the port is free.

set -euo pipefail

PORT="${PORT:-9094}"
SCREEN_NAME="${SCREEN_NAME:-llama-router}"
ROUTER_DIR="${ROUTER_DIR:-/opt/llamacpp-router}"

if screen -ls 2>/dev/null | grep -q "\.${SCREEN_NAME}\b"; then
  screen -S "$SCREEN_NAME" -X quit || true
  echo "killed screen session $SCREEN_NAME"
else
  echo "no screen session $SCREEN_NAME to kill"
fi

sleep 2
if ss -ltn "( sport = :$PORT )" 2>/dev/null | grep -q ":$PORT"; then
  echo "WARN: port $PORT still bound. Inspect with: sudo ss -ltnp | grep $PORT"
  exit 1
fi

echo "port $PORT free, router stopped cleanly."
echo "log preserved at: $ROUTER_DIR/router.log"
