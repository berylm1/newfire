#!/bin/bash
# Phase 1.b EXEC: launch vLLM-Blackwell-nightly serving Nemotron-3-Super-120B-A12B NVFP4 on :30002.
# Prereq: phase1b_prep.sh ran successfully (image pulled, model downloaded).
# Co-resident with Nano Omni on :30000 should be OK memory-wise (~67GB vLLM + ~32GB Nano = ~99GB on 119GB).
# Tight but workable. Monitor first 5 min closely.
set -euo pipefail

IMAGE="vllm/vllm-openai:cu130-nightly"
MODEL_ID="nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4"
# Local path inside the container (HF_CACHE is mounted to /root/.cache/huggingface).
# We downloaded with --local-dir which uses flat layout, so we point vLLM at the directory.
MODEL_PATH="/root/.cache/huggingface/hub/nvidia--NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4"
PORT=30002
CONTAINER_NAME="vllm-super-nvfp4"
HF_CACHE="${HOME}/.cache/huggingface"
LOG="${HOME}/vllm-super.log"

# Pre-flight: make sure nothing is already on this port
if ss -tlnp 2>/dev/null | grep -q ":$PORT "; then
  echo "ERROR: Port $PORT already in use."
  exit 1
fi

# Pre-flight: stop any leftover container of the same name
docker rm -f "$CONTAINER_NAME" 2>/dev/null || true

echo "Launching vLLM (image: $IMAGE)"
echo "Model: $MODEL_ID"
echo "Port: $PORT (container exposes 8000 internally)"
echo "Logs streaming to: $LOG"

# NVIDIA-prescribed env vars to avoid the 2026-04-30 crash class (FlashInfer MoE FP4 on sm_121)
docker run -d --rm \
  --name "$CONTAINER_NAME" \
  --gpus all \
  --ipc=host \
  --shm-size=8g \
  -p ${PORT}:8000 \
  -v "${HF_CACHE}:/root/.cache/huggingface" \
  -e VLLM_NVFP4_GEMM_BACKEND=marlin \
  -e VLLM_USE_FLASHINFER_MOE_FP4=0 \
  -e FLASHINFER_FUSED_MOE_DISABLE_CUTLASS=1 \
  "$IMAGE" \
  --model "$MODEL_PATH" \
  --served-model-name nemotron-super-vllm \
  --quantization fp4 \
  --kv-cache-dtype fp8 \
  --max-model-len 65536 \
  --mamba_ssm_cache_dtype float32 \
  --tool-call-parser qwen3_coder \
  --enable-auto-tool-choice \
  --enable-prefix-caching \
  --gpu-memory-utilization 0.75 \
  --host 0.0.0.0 \
  --port 8000

echo ""
echo "Container started. Tailing logs (Ctrl+C to detach, container keeps running):"
echo "  docker logs -f $CONTAINER_NAME"
echo ""
echo "Server will be ready when /v1/models returns 200:"
echo "  curl -s http://127.0.0.1:${PORT}/v1/models"
echo ""
echo "To stop: docker rm -f $CONTAINER_NAME"

docker logs -f "$CONTAINER_NAME" 2>&1 | tee "$LOG" &
TAILER_PID=$!
echo "Log tailer PID: $TAILER_PID (kill if you want logs to stop scrolling)"
