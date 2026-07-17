#!/bin/bash
# Direct llama-server for Nemotron-3-Super-120B-A12B on DGX Spark.
# Phase 1 launcher. Single-stream, FP16 KV cache (safe defaults).
set -euo pipefail

MODEL_BLOB="/usr/share/ollama/.ollama/models/blobs/sha256-0fc53cc990a2cf4b540b21b8b5a7a7cb1bb21932378549d0250c50b6b316e05e"
LLAMA_BIN="/home/newwave-dgx/llama.cpp/build/bin/llama-server"
PORT=30001
LOG="/home/newwave-dgx/llama-super.log"
PIDFILE="/home/newwave-dgx/llama-super.pid"

if [ ! -f "$MODEL_BLOB" ]; then
  echo "ERROR: Model blob not found at $MODEL_BLOB"
  exit 1
fi

if [ ! -x "$LLAMA_BIN" ]; then
  echo "ERROR: llama-server not executable at $LLAMA_BIN"
  exit 1
fi

if ss -tlnp 2>/dev/null | grep -q ":$PORT "; then
  echo "ERROR: Port $PORT already in use. Stop the existing server first."
  exit 1
fi

echo "Model size: $(du -h "$MODEL_BLOB" | cut -f1)"
echo "Starting llama-server on port $PORT, logging to $LOG"
echo "This will take 2-5 minutes to load 86GB into GPU memory."

nohup "$LLAMA_BIN" \
  --model "$MODEL_BLOB" \
  --alias nemotron-super-direct \
  --host 127.0.0.1 \
  --port "$PORT" \
  --ctx-size 32768 \
  --n-gpu-layers 999 \
  -fa on \
  -ctk f16 -ctv f16 \
  --jinja \
  --log-file "$LOG" \
  > /home/newwave-dgx/llama-super.stdout.log 2>&1 &

echo $! > "$PIDFILE"
echo "Started PID $(cat "$PIDFILE")"
echo "Watch progress with: tail -f $LOG"
echo "Server will be ready when /health returns 200:"
echo "  curl -s http://127.0.0.1:$PORT/health"
