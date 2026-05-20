# Qdrant + RAG test battery

Two scripts, two hosts. Run in order.

## 1. On DGX Spark (ghana): vector store and embeddings

```
scp test_qdrant_rag.sh newwave-dgx@ghana:~/
ssh newwave-dgx@ghana 'bash ~/test_qdrant_rag.sh'
```

What it checks:
1. Qdrant `/healthz` is 200
2. `funmi_legal` collection exists and is green
3. Vector dim is 768 (nomic-embed-text)
4. Points are loaded (not empty)
5. Ollama has `nomic-embed-text`
6. End-to-end embed -> search returns ranked hits with payloads
7. Snapshot endpoint reachable (backup path alive)

## 2. On Minisforum (america): MCP and Paperclip wiring

```
scp test_mcp_tool.sh newwaveclaw@america:~/
ssh newwaveclaw@america 'bash ~/test_mcp_tool.sh'
```

What it checks:
1. OpenClaw lists a `qdrant` MCP tool
2. MCP `qdrant_search` call returns scored hits from `funmi_legal`
3. Paperclip `funmi-legal-research` agent answers and cites sources

## If something fails

- `test_qdrant_rag.sh` fails on step 3 with dim mismatch: the collection was
  created with a different embedding model. Check `ollama list` output and
  rebuild the collection with the right `size`.
- `test_qdrant_rag.sh` fails on step 3 with empty `points_count`: the seeding
  job did not finish or the data was written to a different collection name.
- `test_mcp_tool.sh` fails on step 1: MCP tool is not registered in OpenClaw's
  config. Check `/etc/openclaw/tools.json` on Minisforum.
- `test_mcp_tool.sh` fails on step 3 with no `source`: Paperclip agent prompt
  is not using the tool output, or the tool is registered but not attached to
  that agent. Check `paperclip/agents/funmi_legal_research.yaml`.

## Paths may drift

Today's gap map is from 2026-04-20 and the MCP registration paths are not in
any local doc I have. If any URL (`/v1/mcp/tools`, `/agents/run`) 404s, the
right fix is to read the current OpenClaw + Paperclip config on each host and
adjust the env vars at the top of the script.

Do not mark the gap map item "verified" until both scripts print `all green`.
