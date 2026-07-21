#!/bin/bash
# Qwen3-Coder-Next NVFP4 (GadflyII community quant) via vLLM v0.20.0 on :8001.
# Pair: code/action side of the auto-router. 80B MoE with ~3B active.
set -euo pipefail

IMAGE="vllm/vllm-openai:v0.20.0"
PORT=8001
CONTAINER_NAME="vllm-coder"
HF_CACHE="${HOME}/.cache/huggingface"
MODEL_PATH="/root/.cache/huggingface/hub/GadflyII--Qwen3-Coder-Next-NVFP4"
LOG="${HOME}/vllm-coder.log"

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
  -e VLLM_NVFP4_GEMM_BACKEND=marlin \
  "$IMAGE" \
  --model "$MODEL_PATH" \
  --served-model-name qwen3-coder-next \
  --max-model-len 32768 \
  --gpu-memory-utilization 0.50 \
  --trust-remote-code \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_coder \
  --kv-cache-dtype fp8 \
  --host 0.0.0.0 \
  --port 8000

docker logs -f "$CONTAINER_NAME" 2>&1 | tee "$LOG" &
echo "Log tailer PID: $!"
