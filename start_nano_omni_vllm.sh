#!/bin/bash
# Nemotron-3-Nano-Omni-30B-A3B-Reasoning-NVFP4 (official NVIDIA) via vLLM v0.20.0 on :8001.
# Pair: reasoning/heavy side of the auto-router. 30B MoE, ~3B active. Same Nemotron-3 family as Super.
set -euo pipefail

IMAGE="vllm/vllm-openai:v0.20.0"
PORT=8001
CONTAINER_NAME="vllm-nano-omni"
HF_CACHE="${HOME}/.cache/huggingface"
MODEL_PATH="/root/.cache/huggingface/hub/nvidia--Nemotron-3-Nano-Omni-30B-A3B-Reasoning-NVFP4"
LOG="${HOME}/vllm-nano-omni.log"

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
  -e VLLM_USE_FLASHINFER_MOE_FP4=1 \
  -e VLLM_FLASHINFER_MOE_BACKEND=throughput \
  "$IMAGE" \
  --model "$MODEL_PATH" \
  --served-model-name nemotron-nano-omni \
  --max-model-len 32768 \
  --gpu-memory-utilization 0.40 \
  --trust-remote-code \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_coder \
  --reasoning-parser nemotron_v3 \
  --kv-cache-dtype fp8 \
  --host 0.0.0.0 \
  --port 8000

docker logs -f "$CONTAINER_NAME" 2>&1 | tee "$LOG" &
echo "Log tailer PID: $!"
