#!/bin/bash
# Phase 1.b PREP retry: just the 67GB NVFP4 download.
# The vLLM image was already pulled successfully on first attempt; this script only does Step 4.
# Uses a Python venv to sidestep PEP 668 (externally-managed-environment).
set -euo pipefail

MODEL_ID="nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4"
HF_CACHE="${HOME}/.cache/huggingface"
LOG="${HOME}/phase1b_prep.log"
VENV="${HOME}/hf-venv"

echo "[$(date -Iseconds)] download-only retry starting" | tee -a "$LOG"

mkdir -p "$HF_CACHE"

if [ ! -x "${VENV}/bin/huggingface-cli" ]; then
  echo "Creating venv at ${VENV} and installing huggingface_hub[cli]..." | tee -a "$LOG"
  python3 -m venv "$VENV" 2>&1 | tee -a "$LOG"
  "${VENV}/bin/pip" install --upgrade pip 2>&1 | tee -a "$LOG"
  "${VENV}/bin/pip" install --upgrade 'huggingface_hub[cli]' hf_transfer 2>&1 | tee -a "$LOG"
fi

echo "[$(date -Iseconds)] Starting 67GB download with hf_transfer enabled" | tee -a "$LOG"
HF_HUB_ENABLE_HF_TRANSFER=1 "${VENV}/bin/hf" download "$MODEL_ID" \
  --local-dir "${HF_CACHE}/hub/${MODEL_ID//\//--}" 2>&1 | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo "[$(date -Iseconds)] download DONE" | tee -a "$LOG"
du -sh "${HF_CACHE}/hub/${MODEL_ID//\//--}" 2>&1 | tee -a "$LOG"
