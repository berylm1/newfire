#!/bin/bash
# DeepSeek-R1-Distill-Llama-70B NVFP4 (PiehSoft community quant) via vLLM v0.20.0 on :8000.
# Dense Llama-70B (not MoE), so no FlashInfer FP4 MoE env vars needed.
# NVFP4 GEMM through Marlin kernel for Blackwell native FP4 path.
# Built-in deepseek_r1 reasoning parser separates <think>...</think> blocks.
set -euo pipefail

IMAGE="vllm/vllm-openai:v0.20.0"
PORT=8000
CONTAINER_NAME="vllm-dsr1"
HF_CACHE="${HOME}/.cache/huggingface"
MODEL_PATH="/root/.cache/huggingface/hub/PiehSoft--DeepSeek-R1-Distill-Llama-70B-NVFP4"
LOG="${HOME}/vllm-dsr1.log"

if ss -tlnp 2>/dev/null | grep -q ":$PORT "; then
  echo "ERROR: Port $PORT already in use." ; exit 1
fi

docker rm -f "$CONTAINER_NAME" 2>/dev/null || true

echo "[$(date -Iseconds)] launching $CONTAINER_NAME on :$PORT"

docker run -d --rm \
  --name "$CONTAINER_NAME" \
  --gpus all \
  --ipc=host \
  --shm-size=8g \
  -p ${PORT}:8000 \
  -v "${HF_CACHE}:/root/.cache/huggingface" \
  -e VLLM_NVFP4_GEMM_BACKEND=marlin \
  "$IMAGE" \
  --model "$MODEL_PATH" \
  --served-model-name deepseek-r1-distill-70b \
  --max-model-len 65536 \
  --gpu-memory-utilization 0.55 \
  --trust-remote-code \
  --enable-auto-tool-choice \
  --tool-call-parser llama3_json \
  --reasoning-parser deepseek_r1 \
  --kv-cache-dtype fp8 \
  --host 0.0.0.0 \
  --port 8000

echo "Container started."
docker logs -f "$CONTAINER_NAME" 2>&1 | tee "$LOG" &
echo "Log tailer PID: $!"
