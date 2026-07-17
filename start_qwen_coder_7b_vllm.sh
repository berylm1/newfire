#!/bin/bash
# Qwen2.5-Coder-7B-Instruct (BF16, official) via vLLM v0.20.0 on :8001.
# Pair: tool-caller for DeepSeek-R1-Distill on :8000.
# Hermes-style tool-call format. No reasoning parser needed (no <think> blocks).
set -euo pipefail

IMAGE="vllm/vllm-openai:v0.20.0"
PORT=8001
CONTAINER_NAME="vllm-qwen-coder"
HF_CACHE="${HOME}/.cache/huggingface"
MODEL_PATH="/root/.cache/huggingface/hub/Qwen--Qwen2.5-Coder-7B-Instruct"
LOG="${HOME}/vllm-qwen-coder.log"

if ss -tlnp 2>/dev/null | grep -q ":$PORT "; then
  echo "ERROR: Port $PORT already in use." ; exit 1
fi

docker rm -f "$CONTAINER_NAME" 2>/dev/null || true

echo "[$(date -Iseconds)] launching $CONTAINER_NAME on :$PORT"

docker run -d --rm \
  --name "$CONTAINER_NAME" \
  --gpus all \
  --ipc=host \
  --shm-size=4g \
  -p ${PORT}:8000 \
  -v "${HF_CACHE}:/root/.cache/huggingface" \
  "$IMAGE" \
  --model "$MODEL_PATH" \
  --served-model-name qwen2.5-coder-7b \
  --max-model-len 32768 \
  --gpu-memory-utilization 0.20 \
  --enable-auto-tool-choice \
  --tool-call-parser hermes \
  --kv-cache-dtype fp8 \
  --host 0.0.0.0 \
  --port 8000

echo "Container started."
docker logs -f "$CONTAINER_NAME" 2>&1 | tee "$LOG" &
echo "Log tailer PID: $!"
