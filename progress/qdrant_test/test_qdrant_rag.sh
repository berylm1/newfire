#!/usr/bin/env bash
# Qdrant + nomic-embed-text smoke test, run on DGX Spark.
# Uses the Tailscale IP because Qdrant binds there, not loopback.

set -euo pipefail

QDRANT_URL="${QDRANT_URL:-http://100.88.112.5:6333}"
QDRANT_API_KEY="${QDRANT_API_KEY:-d249ea4b4478e20c45fdf06d4ce33894407dc5a9cbe83c0a68dd4b01da0900f6}"
OLLAMA_URL="${OLLAMA_URL:-http://127.0.0.1:11434}"
COLLECTION="${COLLECTION:-funmi_legal}"
EMBED_MODEL="${EMBED_MODEL:-nomic-embed-text}"

AUTH=(-H "api-key: $QDRANT_API_KEY")

pass() { printf '  PASS %s\n' "$1"; }
fail() { printf '  FAIL %s\n' "$1"; exit 1; }
hdr()  { printf '\n== %s ==\n' "$1"; }

hdr "1. Qdrant reachable"
curl -fsS "${AUTH[@]}" "$QDRANT_URL/healthz" >/dev/null && pass "healthz ok" || fail "Qdrant unreachable at $QDRANT_URL"

hdr "2. Collection exists and is green"
RESP=$(curl -fsS "${AUTH[@]}" "$QDRANT_URL/collections/$COLLECTION") || fail "cannot read collection $COLLECTION"
echo "$RESP" | grep -q '"status":"green"' && pass "collection green" || fail "not green: $RESP"

hdr "3. Vector shape"
DIM=$(echo "$RESP" | python3 -c 'import sys,json; d=json.load(sys.stdin); v=d["result"]["config"]["params"]["vectors"]; print(v["size"] if "size" in v else list(v.values())[0]["size"])')
[[ "$DIM" == "768" ]] && pass "dim 768 matches nomic-embed-text" || fail "expected 768, got $DIM"

COUNT=$(echo "$RESP" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d["result"]["points_count"])')
[[ "$COUNT" -gt 0 ]] && pass "points_count = $COUNT" || fail "collection empty"

hdr "4. Embedding model"
curl -fsS "$OLLAMA_URL/api/tags" | grep -q "$EMBED_MODEL" && pass "$EMBED_MODEL loaded" || fail "$EMBED_MODEL missing"

hdr "5. Embed a legal query"
QUERY="What are the filing deadlines for an I-130 petition?"
EMBED=$(curl -fsS "$OLLAMA_URL/api/embeddings" -H 'Content-Type: application/json' -d "$(python3 -c "import json; print(json.dumps({'model':'$EMBED_MODEL','prompt':'$QUERY'}))")")
VEC=$(echo "$EMBED" | python3 -c 'import sys,json; print(json.dumps(json.load(sys.stdin)["embedding"]))')
[[ -n "$VEC" && "$VEC" != "null" ]] && pass "embedding length $(echo "$VEC" | python3 -c 'import sys,json; print(len(json.load(sys.stdin)))')" || fail "embed call failed"

hdr "6. Semantic search"
SEARCH=$(python3 -c "import json,sys; print(json.dumps({'vector': json.loads('''$VEC'''), 'limit': 3, 'with_payload': True}))")
RESULT=$(curl -fsS "${AUTH[@]}" -X POST "$QDRANT_URL/collections/$COLLECTION/points/search" -H 'Content-Type: application/json' -d "$SEARCH")
HITS=$(echo "$RESULT" | python3 -c 'import sys,json; print(len(json.load(sys.stdin)["result"]))')
[[ "$HITS" -ge 1 ]] && pass "search returned $HITS hits" || fail "0 hits"

echo "$RESULT" | python3 -c '
import sys, json
d = json.load(sys.stdin)
for i, h in enumerate(d["result"]):
    payload = json.dumps(h.get("payload", {}))[:220]
    score = round(h["score"], 3)
    print("    [" + str(i+1) + "] score=" + str(score) + "  payload=" + payload)
'

hdr "7. Snapshot API"
SNAPS=$(curl -fsS "${AUTH[@]}" "$QDRANT_URL/collections/$COLLECTION/snapshots")
N=$(echo "$SNAPS" | python3 -c 'import sys,json; print(len(json.load(sys.stdin)["result"]))')
pass "snapshot api ok, $N snapshot(s)"

echo
echo "Qdrant + RAG push verified end to end."
