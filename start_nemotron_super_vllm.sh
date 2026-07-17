#!/bin/bash
# Phase 1.c EXEC: Nemotron-3-Super-120B-A12B NVFP4 via vLLM v0.20.0 on :8000.
# Path A.1: mount ~/.cache/huggingface where the 75GB checkpoint already lives.
# Env vars enable Blackwell-native FlashInfer FP4 MoE backend (the post-fp8-crash correction).
set -euo pipefail

IMAGE="vllm/vllm-openai:v0.20.0"
PORT=8000
CONTAINER_NAME="vllm-super"
HF_CACHE="${HOME}/.cache/huggingface"
MODEL_PATH="/root/.cache/huggingface/hub/nvidia--NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4"
LOG="${HOME}/vllm-super.log"

if ss -tlnp 2>/dev/null | grep -q ":$PORT "; then
  echo "ERROR: Port $PORT already in use." ; exit 1
fi

docker rm -f "$CONTAINER_NAME" 2>/dev/null || true

echo "[$(date -Iseconds)] launching $CONTAINER_NAME on :$PORT"
echo "image:       $IMAGE"
echo "model path:  $MODEL_PATH"
echo "hf-cache:    $HF_CACHE  (bind-mounted to /root/.cache/huggingface)"

docker run -d --rm \
  --name "$CONTAINER_NAME" \
  --gpus all \
  --ipc=host \
  --shm-size=8g \
  -p ${PORT}:8000 \
  -v "${HF_CACHE}:/root/.cache/huggingface" \
  -e VLLM_USE_FLASHINFER_MOE_FP4=1 \
  -e VLLM_FLASHINFER_MOE_BACKEND=throughput \
  "$IMAGE" \
  --model "$MODEL_PATH" \
  --served-model-name nemotron-super \
  --max-model-len 65536 \
  --gpu-memory-utilization 0.65 \
  --trust-remote-code \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_coder \
  --reasoning-parser nemotron_v3 \
  --kv-cache-dtype fp8 \
  --host 0.0.0.0 \
  --port 8000

echo ""
echo "Container started. Stream logs:"
echo "  docker logs -f $CONTAINER_NAME"
echo ""
echo "Ready when:"
echo "  curl -s http://127.0.0.1:${PORT}/v1/models | head"

docker logs -f "$CONTAINER_NAME" 2>&1 | tee "$LOG" &
echo "Log tailer PID: $!"
