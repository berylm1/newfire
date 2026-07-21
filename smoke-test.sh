#!/usr/bin/env bash
# Smoke test for llama.cpp router mode.
# Cycles through the three registered models, prints the time-to-first-token
# and total wall time per swap, so we can see the unload+reload cost honestly.
#
# Run ON ghana after setup-router-test.sh succeeded:
#   bash /tmp/smoke-test.sh

set -euo pipefail

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-9094}"
URL="http://$HOST:$PORT/v1/chat/completions"

green()  { printf '\033[32m%s\033[0m\n' "$*"; }
blue()   { printf '\033[34m%s\033[0m\n' "$*"; }
yellow() { printf '\033[33m%s\033[0m\n' "$*"; }
red()    { printf '\033[31m%s\033[0m\n' "$*"; }

probe() {
  local model="$1"
  local prompt="$2"
  local body
  body=$(jq -nc --arg m "$model" --arg p "$prompt" '{
    model:$m,
    messages:[{role:"user", content:$p}],
    max_tokens: 64,
    temperature: 0.2
  }')

  blue "==> ask $model"
  local t0 t1
  t0=$(date +%s.%N)
  local resp
  resp=$(curl -s -X POST "$URL" \
              -H "Content-Type: application/json" \
              -d "$body")
  t1=$(date +%s.%N)
  local elapsed
  elapsed=$(awk -v a="$t1" -v b="$t0" 'BEGIN{printf "%.2f", a-b}')

  local content
  content=$(echo "$resp" | jq -r '.choices[0].message.content // (.error.message // "<no content>")')
  green "    ${elapsed}s wall time"
  echo "    --> ${content:0:200}"
  echo
}

blue "==> sanity: GET /v1/models"
curl -s "http://$HOST:$PORT/v1/models" | jq '.data[].id'
echo

blue "==> round 1: cold loads (each model unloads the prior one)"
probe gemma3-4b      "Say hello in one sentence."
probe qwen-coder-7b  "Write a Python function that returns the sum of a list."
probe deepseek-r1-8b "If A implies B and B implies C, what does A imply?"

blue "==> round 2: re-prompt to measure warm vs cold"
probe gemma3-4b      "Name three colors."
probe qwen-coder-7b  "What does the Go keyword 'defer' do? One line."
probe deepseek-r1-8b "Is 91 prime? Show one-line reasoning."

cat <<EOF

================================================================================
Smoke test complete.

Reading the timings:
  - In round 1, each call pays the full GGUF load cost (cold).
  - In round 2, the SECOND call to the same model after a different one was
    used in between pays cold-load again (router only keeps one resident
    by default).
  - If you want hot-swapping, raise --models-max on the server flags.

Tail the router log for load events:
  tail -n 80 /opt/llamacpp-router/router.log | grep -i 'load\|unload'
================================================================================
EOF
