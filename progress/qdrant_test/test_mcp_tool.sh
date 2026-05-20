#!/usr/bin/env bash
# Verify the Qdrant MCP tool is registered and callable from Paperclip / OpenClaw.
# Run on Minisforum (america), not on the Mac.
#
#   scp test_mcp_tool.sh newwaveclaw@america:~/
#   ssh newwaveclaw@america 'bash ~/test_mcp_tool.sh'

set -euo pipefail

OPENCLAW_URL="${OPENCLAW_URL:-http://127.0.0.1:18789}"
PAPERCLIP_URL="${PAPERCLIP_URL:-http://127.0.0.1:3100}"
COLLECTION="${COLLECTION:-funmi_legal}"

pass() { printf '  \033[32mPASS\033[0m %s\n' "$1"; }
fail() { printf '  \033[31mFAIL\033[0m %s\n' "$1"; exit 1; }
head() { printf '\n== %s ==\n' "$1"; }

head "1. OpenClaw exposes the MCP tool"
TOOLS=$(curl -fsS "$OPENCLAW_URL/v1/mcp/tools" 2>/dev/null || echo "")
if [[ -z "$TOOLS" ]]; then
  echo "  note: adjust OPENCLAW_URL or the /v1/mcp/tools path to match your build"
  fail "could not list MCP tools"
fi
echo "$TOOLS" | grep -q "qdrant" && pass "qdrant tool present" || fail "no qdrant tool in MCP registry"

head "2. Invoke the tool with a legal query"
BODY='{"tool":"qdrant_search","arguments":{"collection":"'"$COLLECTION"'","query":"What are the filing deadlines for an I-130 petition?","top_k":3}}'
RESP=$(curl -fsS -X POST "$OPENCLAW_URL/v1/mcp/call" -H 'Content-Type: application/json' -d "$BODY")
echo "$RESP" | python3 -m json.tool | head -40
echo "$RESP" | grep -q '"score"' && pass "tool returned scored hits" || fail "tool call returned no scores"

head "3. Paperclip agent path (Funmi legal-research agent)"
AGENT_BODY='{"agent":"funmi-legal-research","input":"I-130 filing deadlines for spouse petition"}'
if curl -fsS -X POST "$PAPERCLIP_URL/agents/run" -H 'Content-Type: application/json' -d "$AGENT_BODY" >/tmp/agent_out.json 2>/dev/null; then
  grep -q 'source' /tmp/agent_out.json && pass "agent response cites sources (RAG working end to end)" \
    || fail "agent ran but did not cite sources, RAG wiring may be missing"
else
  echo "  note: adjust PAPERCLIP_URL or the /agents/run path to match your build"
  fail "Paperclip agent call failed"
fi

echo
echo "MCP tool green. Paperclip can answer Funmi queries with retrieved context."
