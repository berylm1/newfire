#!/usr/bin/env bash
# Backfill qdrant_collection for legacy companies, create Qdrant collections,
# seed identity chunks from onboarding data.
#
# Idempotent. Pass --force to re-seed collections that already have points.
#
# Requires on Minisforum: docker (for newfire-db exec), curl, python3.

set -euo pipefail

: "${QDRANT_URL:=http://100.88.112.5:6333}"
: "${QDRANT_API_KEY:?QDRANT_API_KEY required}"
: "${OLLAMA_URL:=http://100.88.112.5:11434}"
: "${EMBED_MODEL:=nomic-embed-text}"

FORCE=${1:-}

psql_q() { docker exec newfire-db psql -U newfire -d newfire -tAF$'\t' -c "$1" < /dev/null; }

echo "[db] backfilling NULL qdrant_collection rows"
docker exec -i newfire-db psql -U newfire -d newfire -c \
  "UPDATE companies SET qdrant_collection = 'company_' || id WHERE qdrant_collection IS NULL"

create_coll() {
  local coll=$1
  local probe
  probe=$(curl -sS -o /dev/null -w '%{http_code}' "$QDRANT_URL/collections/$coll" -H "api-key: $QDRANT_API_KEY")
  if [[ "$probe" == "200" ]]; then
    echo "existed"
  else
    curl -sS -X PUT "$QDRANT_URL/collections/$coll" \
      -H "api-key: $QDRANT_API_KEY" -H 'Content-Type: application/json' \
      -d '{"vectors":{"size":768,"distance":"Cosine"}}' > /dev/null
    echo "created"
  fi
}

points_count() {
  local coll=$1
  curl -sS "$QDRANT_URL/collections/$coll" -H "api-key: $QDRANT_API_KEY" | \
    python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("result",{}).get("points_count", 0))'
}

embed() {
  local text=$1
  curl -sS "$OLLAMA_URL/api/embeddings" \
    -H 'Content-Type: application/json' \
    -d "$(python3 -c 'import json,sys; print(json.dumps({"model":sys.argv[1],"prompt":sys.argv[2]}))' "$EMBED_MODEL" "$text")" | \
    python3 -c 'import sys,json; print(json.dumps(json.load(sys.stdin)["embedding"]))'
}

upsert_one() {
  local coll=$1 idx=$2 text=$3 kind=$4 extra=${5:-\{\}}
  local vec
  vec=$(embed "$text")
  local body
  body=$(python3 -c '
import json, sys
coll, idx, text, kind, extra, vec = sys.argv[1:7]
payload = {"text": text, "kind": kind, "source_file": "onboarding", "needs_review": True, "chunk_index": int(idx)}
payload.update(json.loads(extra))
vec_list = json.loads(vec)
print(json.dumps({"points":[{"id": int(idx), "vector": vec_list, "payload": payload}]}))
' "$coll" "$idx" "$text" "$kind" "$extra" "$vec")
  curl -sS -X PUT "$QDRANT_URL/collections/$coll/points?wait=true" \
    -H "api-key: $QDRANT_API_KEY" -H 'Content-Type: application/json' \
    -d "$body" > /dev/null
}

echo "[process] iterating companies"
while IFS=$'\t' read -r cid cname cdesc coll; do
  [[ -z "$cid" ]] && continue
  echo ""
  echo "== company $cid: $cname -> $coll =="
  status=$(create_coll "$coll")
  echo "  collection $status"

  if [[ "$FORCE" != "--force" ]]; then
    existing=$(points_count "$coll")
    if [[ "$existing" -gt 0 ]]; then
      echo "  skip: $existing points exist (use --force to re-seed)"
      continue
    fi
  else
    echo "  force: clearing existing points"
    curl -sS -X POST "$QDRANT_URL/collections/$coll/points/delete" \
      -H "api-key: $QDRANT_API_KEY" -H 'Content-Type: application/json' \
      -d '{"filter":{"must":[]}}' > /dev/null 2>&1 || true
  fi

  idx=1
  if [[ -n "$cdesc" ]]; then
    upsert_one "$coll" "$idx" "$cname is $cdesc" "company_overview" "{}"
    idx=$((idx + 1))
  fi

  # Pull agents for this company
  while IFS=$'\t' read -r agent_id aname arole adesc; do
    [[ -z "$agent_id" ]] && continue
    text="Agent '$aname' works at $cname. Role: $arole. Scope: $adesc"
    extra=$(python3 -c 'import json,sys; print(json.dumps({"agent_id": sys.argv[1]}))' "$agent_id")
    upsert_one "$coll" "$idx" "$text" "agent_identity" "$extra"
    idx=$((idx + 1))
  done < <(psql_q "SELECT agent_id, name, role, description FROM agents WHERE company_id = $cid ORDER BY id")

  total=$((idx - 1))
  echo "  seeded $total chunks"
done < <(psql_q "SELECT id, name, description, qdrant_collection FROM companies ORDER BY id")

echo ""
echo "DONE"
