#!/bin/bash
# Stop the vLLM Super container cleanly. Rollback for Phase 1.b.
set -u

CONTAINER_NAME="vllm-super-nvfp4"

if ! docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
  echo "Container ${CONTAINER_NAME} not present. Nothing to stop."
  exit 0
fi

echo "Stopping ${CONTAINER_NAME}..."
docker rm -f "$CONTAINER_NAME"

sleep 3
echo "Done. GPU memory should free within 10 seconds."
echo "Verify with: nvidia-smi --query-gpu=utilization.gpu --format=csv"
