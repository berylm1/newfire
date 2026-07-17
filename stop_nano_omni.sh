#!/bin/bash
# Stop the Nano Omni llama-server cleanly so Super can have the GPU memory.
# This temporarily breaks the nss-elite route in LiteLLM (fallback chain handles it).
set -u

PIDS=$(pgrep -f 'llama-server.*nemotron-nano-omni' 2>/dev/null || true)
if [ -z "$PIDS" ]; then
  echo "Nano Omni llama-server is not running. Nothing to stop."
  exit 0
fi

echo "Found Nano Omni PIDs: $PIDS"
for PID in $PIDS; do
  echo "Sending SIGTERM to $PID"
  kill "$PID" 2>/dev/null || true
done

sleep 3

REMAINING=$(pgrep -f 'llama-server.*nemotron-nano-omni' 2>/dev/null || true)
if [ -n "$REMAINING" ]; then
  echo "Still running, force-killing: $REMAINING"
  for PID in $REMAINING; do
    kill -9 "$PID" 2>/dev/null || true
  done
  sleep 2
fi

if pgrep -f 'llama-server.*nemotron-nano-omni' > /dev/null; then
  echo "ERROR: Nano Omni still running."
  exit 1
fi

echo "Nano Omni stopped. GPU memory should free in 5-10 seconds."
echo "Verify with: nvidia-smi"
