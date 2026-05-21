#!/usr/bin/env bash
set -euo pipefail

BASE="${RAG_BASE:-http://localhost:8200}"
TENANT="${TENANT:-funmi}"

echo "=== healthz ==="
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${BASE}/healthz")
if [ "$STATUS" != "200" ]; then
  echo "FAIL: healthz returned $STATUS" >&2
  exit 1
fi
echo "OK (200)"

echo "=== ingest ==="
CONTENT_B64=$(python3 -c "import base64; print(base64.b64encode(b'Test immigration memo about asylum procedures and credible fear interviews.').decode())")
INGEST_RESP=$(curl -s -X POST "${BASE}/rag/ingest" \
  -H "Content-Type: application/json" \
  -H "X-Consumer-Username: ${TENANT}" \
  -d "{
    \"tenant_id\": \"${TENANT}\",
    \"filename\": \"smoke_test.txt\",
    \"content_b64\": \"${CONTENT_B64}\",
    \"title\": \"Smoke Test Memo\",
    \"jurisdiction\": \"US-BIA\",
    \"doc_type\": \"memo\",
    \"citation\": \"Smoke Test v. 1\",
    \"source_doc\": \"smoke_test.txt\"
  }")
echo "Ingest response: ${INGEST_RESP}"

SKIPPED=$(python3 -c "import sys,json; d=json.loads('${INGEST_RESP}'); print(d.get('skipped', False))" 2>/dev/null || echo "False")
CHUNKS=$(python3 -c "import sys,json; d=json.loads('${INGEST_RESP}'); print(d.get('chunks_ingested', 0))" 2>/dev/null || echo "0")
if [ "$SKIPPED" = "False" ] && [ "$CHUNKS" = "0" ]; then
  echo "FAIL: ingest returned 0 chunks and was not skipped" >&2
  exit 1
fi
echo "OK (chunks=${CHUNKS} skipped=${SKIPPED})"

echo "=== query ==="
QUERY_RESP=$(curl -s -X POST "${BASE}/rag/query" \
  -H "Content-Type: application/json" \
  -H "X-Consumer-Username: ${TENANT}" \
  -d "{
    \"tenant_id\": \"${TENANT}\",
    \"query\": \"asylum procedures credible fear\",
    \"top_k\": 5
  }")
echo "Query response: ${QUERY_RESP}"

RESULT_COUNT=$(python3 -c "import json; d=json.loads('${QUERY_RESP}'); print(len(d.get('results', [])))" 2>/dev/null || echo "0")
if [ "$RESULT_COUNT" = "0" ]; then
  echo "FAIL: query returned empty results" >&2
  exit 1
fi
echo "OK (results=${RESULT_COUNT})"

echo "=== all checks passed ==="
