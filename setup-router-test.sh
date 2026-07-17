#!/usr/bin/env bash
# llama.cpp router-mode test deployment for the DGX Spark (ghana).
# Idempotent: re-running cleans up the previous test process first.
#
# What it does (in order):
#   1. Verifies llama-server is recent enough to support --models router flag.
#      (If not, prints the rebuild command and exits 2 so we can decide.)
#   2. Ensures the test workspace at /opt/llamacpp-router exists.
#   3. Drops in the staged models.ini.
#   4. Starts llama-server in router mode on 127.0.0.1:9094 under a screen
#      session named `llama-router`, so it survives the SSH disconnect but
#      stays loopback-only (no LAN, no public exposure).
#   5. Waits up to 60s for /v1/models to respond, then prints the registry.
#
# Run ON the DGX (ghana). Push this from Mac with:
#   scp setup-router-test.sh models.ini newwave-dgx@ghana:/tmp/
#   ssh newwave-dgx@ghana 'bash /tmp/setup-router-test.sh'

set -euo pipefail

PORT="${PORT:-9094}"
BIND="${BIND:-127.0.0.1}"
ROUTER_DIR="${ROUTER_DIR:-/opt/llamacpp-router}"
MODELS_INI_SRC="${MODELS_INI_SRC:-/tmp/models.ini}"
SCREEN_NAME="${SCREEN_NAME:-llama-router}"
LLAMA_BIN_CANDIDATES=(
  "${LLAMA_BIN:-}"
  "/usr/local/bin/llama-server"
  "/home/newwave-dgx/llama.cpp/build/bin/llama-server"
  "$HOME/llama.cpp/build/bin/llama-server"
)
LLAMA_BIN=""
for c in "${LLAMA_BIN_CANDIDATES[@]}"; do
  if [ -n "$c" ] && [ -x "$c" ]; then LLAMA_BIN="$c"; break; fi
done

red()    { printf '\033[31m%s\033[0m\n' "$*"; }
green()  { printf '\033[32m%s\033[0m\n' "$*"; }
yellow() { printf '\033[33m%s\033[0m\n' "$*"; }
blue()   { printf '\033[34m%s\033[0m\n' "$*"; }

blue "==> Step 1: verify llama-server presence and router-mode support"
if [ -z "$LLAMA_BIN" ]; then
  red "No llama-server binary found in any candidate path:"
  for c in "${LLAMA_BIN_CANDIDATES[@]}"; do [ -n "$c" ] && red "    $c"; done
  red "Rebuild from https://github.com/ggerganov/llama.cpp or set LLAMA_BIN env var."
  exit 1
fi

HELP_TEXT=$("$LLAMA_BIN" --help 2>&1 || true)
if ! echo "$HELP_TEXT" | grep -q "models-preset"; then
  red "This llama-server build does NOT support router mode (no --models-preset flag)."
  yellow "Rebuild it. Suggested commands (run as your usual user, not root):"
  cat <<'EOF'
    cd ~ && git clone https://github.com/ggerganov/llama.cpp || true
    cd llama.cpp && git fetch --all && git checkout master && git pull
    cmake -B build -DGGML_CUDA=ON -DLLAMA_CURL=ON
    cmake --build build -j --target llama-server
EOF
  exit 2
fi
green "    llama-server found at $LLAMA_BIN with router-mode support."

blue "==> Step 2: prepare workspace at $ROUTER_DIR"
sudo mkdir -p "$ROUTER_DIR"
sudo chown "$(id -u):$(id -g)" "$ROUTER_DIR"

if [ ! -f "$MODELS_INI_SRC" ]; then
  red "models.ini not found at $MODELS_INI_SRC. Did you scp it?"
  exit 1
fi
cp "$MODELS_INI_SRC" "$ROUTER_DIR/models.ini"
green "    workspace ready, models.ini staged."

blue "==> Step 3: stop any prior test session named $SCREEN_NAME"
if screen -ls 2>/dev/null | grep -q "\.${SCREEN_NAME}\b"; then
  screen -S "$SCREEN_NAME" -X quit || true
  yellow "    killed previous screen session."
else
  green "    no previous session to clean."
fi
if ss -ltn "( sport = :$PORT )" 2>/dev/null | grep -q ":$PORT"; then
  red "Port $PORT is already bound by another process. Refusing to clobber."
  red "Inspect with:  sudo ss -ltnp | grep $PORT"
  exit 3
fi

blue "==> Step 4: launch llama-server in router mode (loopback only)"
if ! command -v screen >/dev/null 2>&1; then
  red "screen not installed. Install with: sudo apt-get install -y screen"
  exit 1
fi
screen -dmS "$SCREEN_NAME" bash -c "\
  cd $ROUTER_DIR && \
  exec $LLAMA_BIN --models-preset $ROUTER_DIR/models.ini \
                  --models-max 2 \
                  --host $BIND --port $PORT \
                  2>&1 | tee -a $ROUTER_DIR/router.log"
green "    screen session '$SCREEN_NAME' launched. Logs: $ROUTER_DIR/router.log"

blue "==> Step 5: wait for /v1/models to respond (max 60s)"
for i in $(seq 1 60); do
  if curl -sf "http://$BIND:$PORT/v1/models" >/dev/null 2>&1; then
    green "    router up after ${i}s."
    break
  fi
  sleep 1
  if [ "$i" = "60" ]; then
    red "    router did NOT come up. Tail of log:"
    tail -n 50 "$ROUTER_DIR/router.log" || true
    exit 4
  fi
done

blue "==> Registry advertised by router:"
curl -s "http://$BIND:$PORT/v1/models" | python3 -m json.tool || true

cat <<EOF

================================================================================
DONE. Router is live at http://$BIND:$PORT (loopback only).

Next: run the smoke test to switch between the three models and time the swaps:
  bash /tmp/smoke-test.sh

To watch the log live:
  tail -f $ROUTER_DIR/router.log

To attach the screen session:
  screen -r $SCREEN_NAME    (Ctrl-A then D to detach)

To stop everything:
  bash /tmp/teardown.sh
================================================================================
EOF
