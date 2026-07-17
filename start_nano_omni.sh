#!/bin/bash
# Restart the Nano Omni llama-server (rollback if Phase 1 fails or after Phase 1 done).
# Matches the original launch we saw in pgrep on 2026-05-12.
set -euo pipefail

LLAMA_BIN="/home/newwave-dgx/llama.cpp/build/bin/llama-server"
MODEL="/home/newwave-dgx/models/NVIDIA-Nemotron-3-Nano-Omni/nemotron-3-nano-omni-ga_v1.0-Q8_0.gguf"
LOG="/home/newwave-dgx/llama-server.log"
PORT=30000

if pgrep -f 'llama-server.*nemotron-nano-omni' > /dev/null; then
  echo "Nano Omni already running. Nothing to do."
  pgrep -af 'llama-server.*nemotron-nano-omni'
  exit 0
fi

if [ ! -f "$MODEL" ]; then
  echo "ERROR: Nano Omni model not found at $MODEL"
  exit 1
fi

echo "Starting Nano Omni on port $PORT"
nohup "$LLAMA_BIN" \
  --model "$MODEL" \
  --alias nemotron-nano-omni \
  --host 127.0.0.1 \
  --port "$PORT" \
  --ctx-size 32768 \
  --n-gpu-layers 999 \
  --jinja \
  --log-file "$LOG" \
  > /home/newwave-dgx/llama-server.stdout.log 2>&1 &

echo "Started PID $!"
echo "Ready when: curl -s http://127.0.0.1:$PORT/health returns 200"
