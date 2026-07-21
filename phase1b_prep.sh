#!/bin/bash
# Phase 1.b PREP: pull vLLM Blackwell-nightly image and download Nemotron-3-Super NVFP4 checkpoint.
# This is the LONG step (~30-90 min, network-dependent). Run in tmux or screen well BEFORE the actual swap.
# Zero impact on running services. Doesn't touch Nano Omni or any active route.
set -euo pipefail

IMAGE="vllm/vllm-openai:cu130-nightly"
MODEL_ID="nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4"
HF_CACHE="${HOME}/.cache/huggingface"
LOG="${HOME}/phase1b_prep.log"

echo "[$(date -Iseconds)] Phase 1.b prep starting" | tee "$LOG"

echo "=== Step 1/4: Disk space check ===" | tee -a "$LOG"
df -h ~ | tee -a "$LOG"
NEEDED_GB=80
AVAIL_GB=$(df --output=avail -BG ~ | tail -1 | tr -dc '0-9')
if [ "$AVAIL_GB" -lt "$NEEDED_GB" ]; then
  echo "WARN: only ${AVAIL_GB}GB free in home, need ${NEEDED_GB}GB for NVFP4 checkpoint." | tee -a "$LOG"
fi

echo "" | tee -a "$LOG"
echo "=== Step 2/4: Verify Docker + NVIDIA container toolkit ===" | tee -a "$LOG"
docker --version | tee -a "$LOG"
docker run --rm --gpus all nvcr.io/nvidia/cuda:12.6.0-base-ubuntu22.04 nvidia-smi --query-gpu=name --format=csv,noheader 2>&1 | tee -a "$LOG" || {
  echo "ERROR: Docker GPU passthrough not working. Fix nvidia-container-toolkit before continuing." | tee -a "$LOG"
  exit 1
}

echo "" | tee -a "$LOG"
echo "=== Step 3/4: Pull vLLM Blackwell-nightly image ===" | tee -a "$LOG"
docker pull "$IMAGE" 2>&1 | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo "=== Step 4/4: Download NVFP4 checkpoint via huggingface-cli ===" | tee -a "$LOG"
mkdir -p "$HF_CACHE"
VENV="${HOME}/hf-venv"
if [ ! -x "${VENV}/bin/huggingface-cli" ]; then
  echo "Creating venv at ${VENV} and installing huggingface_hub[cli]..." | tee -a "$LOG"
  python3 -m venv "$VENV" 2>&1 | tee -a "$LOG"
  "${VENV}/bin/pip" install --upgrade pip 2>&1 | tee -a "$LOG"
  "${VENV}/bin/pip" install --upgrade 'huggingface_hub[cli]' hf_transfer 2>&1 | tee -a "$LOG"
fi
echo "Starting download (67GB, this is the long step). Using HF_HUB_ENABLE_HF_TRANSFER=1 for speed." | tee -a "$LOG"
HF_HUB_ENABLE_HF_TRANSFER=1 "${VENV}/bin/huggingface-cli" download "$MODEL_ID" \
  --local-dir "${HF_CACHE}/hub/${MODEL_ID//\//--}" 2>&1 | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo "[$(date -Iseconds)] Phase 1.b prep DONE. Now ready to run start_super_vllm.sh." | tee -a "$LOG"
echo "Total size:" | tee -a "$LOG"
du -sh "${HF_CACHE}/hub/${MODEL_ID//\//--}" 2>&1 | tee -a "$LOG"
