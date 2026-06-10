# NewFire RAG and Persistent Memory Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task. Keep all backend implementation work on tracked GitHub branches/PRs; do not edit untracked production source directly.

**Goal:** Turn NewFire agents from prompt-only chatbots into grounded, tenant-aware assistants that can retrieve client knowledge and remember useful cross-session facts without exposing production data or secrets.

**Architecture:** NewFire already has partial RAG plumbing: per-company Qdrant collection names, Qdrant collection creation, seed scripts, `retrieveContext()`, and chat prompt injection. The missing work is to make ingestion, retrieval, memory extraction, source governance, tests, and rollout explicit and safe. The MVP should ship as a small backend + docs + tests sequence after the load-bearing backend source is put under GitHub control.

**Tech Stack:** Express/Node backend, PostgreSQL, Qdrant, Ollama `nomic-embed-text`, OpenClaw/OpenRouter/Ollama chat routing, APISIX, Docker Compose, pytest/shell smoke tests for infra docs, and Node integration tests for backend behavior.

---

## Current state found

### Tracked in this GitHub repo

- `newfire_backend_docker/SEEDING_GUIDE.md` documents manual Qdrant content seeding.
- `newfire_backend_docker/seed_company_content.sh` chunks plaintext files, embeds with Ollama, and upserts into `company_<id>` Qdrant collections.
- `newfire_backend_docker/backfill_collections.py` and `.sh` backfill `qdrant_collection` values and seed identity chunks from company/agent rows.
- `newfire_backend_docker/docker-compose.yml` exposes `QDRANT_URL`, `QDRANT_API_KEY`, `OLLAMA_URL`, `EMBED_MODEL`, and `RAG_TOP_K` to the backend container.
- `progress/qdrant_test/` contains older Qdrant and MCP smoke tests.
- `Things that need to change.md` still marks vector DB/RAG/persistent memory as a gap; this should be updated once MVP work lands.
- `backend-source.md` says the load-bearing backend source lives outside this repo.

### Load-bearing backend source located on Minisforum

Actual source paths found at `/home/newwaveclaw/newfire-backend/`:

- `src/orchestrator.js`
  - `ensureQdrantCollection(companyId)` creates `company_<id>` collections.
  - `retrieveContext(collection, queryText, opts)` embeds the user query, searches Qdrant, and applies `company_id` payload filter.
  - `formatContextBlock(hits)` injects retrieved context into the model prompt.
  - `chatWithAgent(userId, agentId, messages, opts)` already accepts tenant `companyId` and performs agent lookup.
- `src/db.js`
  - owns schema initialization for `users`, `companies`, `agents`, `conversations`, and `chat_metrics`.
- `src/server.js`
  - chat routes call `tenantContext` then `chatWithAgent()`.
- `src/tenant.js`
  - provides tenant context and cache invalidation.

### Governance blocker

`/home/newwaveclaw/newfire-backend` is currently not a Git repo on the Minisforum. Do **not** implement backend changes there directly as part of the CEO agent workflow. First, put backend source under GitHub control or vendor the backend into this repo. Until then, issue #4 should remain docs/design only.

---

## Definitions

### RAG knowledge

Client-approved business facts that should ground answers:

- services and service boundaries
- exact pricing, hours, policies, FAQs
- tone samples
- approved legal/business disclaimers
- uploaded source documents
- owner-approved internal notes

### Persistent memory

Small, durable facts learned from conversations or owner actions that improve future sessions:

- preferred customer name/pronouns
- client-specific preferences, e.g. "prefers SMS follow-up"
- recurring context, e.g. "asked about premium package twice"
- owner-approved notes, e.g. "quote approved on 2026-06-02"

Persistent memory is **not** raw chat transcript storage. Conversation history already exists in `conversations`. Memory should be compact, auditable, tenant-scoped, and deletable.

---

## Security and privacy requirements

1. Every vector point must be tenant-scoped with `company_id` payload.
2. Retrieval must always filter by the active `companyId` from `tenantContext`.
3. Production seeding must never require copying client data into this repo.
4. Source documents must be stored outside Git; commit only schemas, fixtures, and scripts.
5. Do not expose or add secrets in docs, code, test fixtures, or PR body.
6. For legal-sensitive clients such as Funmi, retrieved context must not route to cloud models unless explicitly allowed by policy.
7. Every generated answer based on retrieved context must be able to identify source snippets or source IDs in logs/admin UI.
8. Deletion must remove vector points, memory rows, chat history, and backups according to the client privacy policy.

---

## MVP architecture

```text
Client content / owner notes
  ↓
Ingestion service or admin upload
  ↓
Chunker + metadata normalizer
  ↓
Ollama embeddings: nomic-embed-text
  ↓
Qdrant collection: company_<company_id>
  ↓
Chat request with tenantContext companyId
  ↓
retrieveContext(collection, query, { companyId })
  ↓
Context block with citations/source IDs
  ↓
Model call, with cloud-routing policy check
  ↓
Response + retrieval metadata recorded
  ↓
Optional memory extractor queues compact facts for owner/admin review
```

---

## Data model proposal

Add SQL migrations in the backend repo after source control is fixed.

### `knowledge_sources`

Tracks original source files/notes without storing raw files in Git.

```sql
CREATE TABLE IF NOT EXISTS knowledge_sources (
  id BIGSERIAL PRIMARY KEY,
  company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  source_type VARCHAR(40) NOT NULL DEFAULT 'manual',
  source_uri TEXT,
  checksum_sha256 VARCHAR(64),
  status VARCHAR(30) NOT NULL DEFAULT 'active',
  created_by INTEGER REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_knowledge_sources_company
ON knowledge_sources(company_id, status, created_at DESC);
```

### `knowledge_chunks`

Maps Qdrant point IDs back to auditable source chunks.

```sql
CREATE TABLE IF NOT EXISTS knowledge_chunks (
  id BIGSERIAL PRIMARY KEY,
  company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  source_id BIGINT REFERENCES knowledge_sources(id) ON DELETE CASCADE,
  qdrant_collection VARCHAR(255) NOT NULL,
  qdrant_point_id VARCHAR(100) NOT NULL,
  chunk_index INTEGER NOT NULL,
  text_preview TEXT,
  token_estimate INTEGER,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(qdrant_collection, qdrant_point_id)
);

CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_company_source
ON knowledge_chunks(company_id, source_id, chunk_index);
```

### `agent_memories`

Stores compact durable facts, separate from raw conversation history.

```sql
CREATE TABLE IF NOT EXISTS agent_memories (
  id BIGSERIAL PRIMARY KEY,
  company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
  agent_id VARCHAR(100),
  subject_type VARCHAR(40) NOT NULL DEFAULT 'customer',
  subject_key TEXT,
  fact TEXT NOT NULL,
  confidence NUMERIC(4,3) NOT NULL DEFAULT 0.700,
  status VARCHAR(30) NOT NULL DEFAULT 'pending_review',
  source_conversation_id BIGINT REFERENCES conversations(id) ON DELETE SET NULL,
  created_by VARCHAR(40) NOT NULL DEFAULT 'system',
  approved_by INTEGER REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_memories_lookup
ON agent_memories(company_id, agent_id, subject_type, subject_key, status, updated_at DESC);
```

### `rag_events`

Records retrieval for debugging, ROI, and safety audits without storing full private payloads unnecessarily.

```sql
CREATE TABLE IF NOT EXISTS rag_events (
  id BIGSERIAL PRIMARY KEY,
  company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
  agent_id VARCHAR(100),
  query_preview TEXT,
  hit_count INTEGER NOT NULL DEFAULT 0,
  top_score NUMERIC(8,6),
  source_chunk_ids BIGINT[] DEFAULT '{}',
  model VARCHAR(120),
  provider VARCHAR(40),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rag_events_company_created
ON rag_events(company_id, created_at DESC);
```

---

## Implementation tasks

### Task 0: Put backend source under GitHub control

**Objective:** Make backend changes PR-reviewable before touching production source.

**Files:**

- Either create a new repo for `/home/newwaveclaw/newfire-backend`, or add it under a tracked directory in `berylm1/newfire`.
- Update `backend-source.md` with the chosen remote.

**Steps:**

1. Confirm no secrets are committed: `.env`, private keys, local DB dumps, client docs, and generated logs must stay ignored.
2. Add `.gitignore` if missing.
3. Push a baseline branch to GitHub.
4. Open a source-control PR or repository setup note.

**Verification:**

```bash
git status --short
git remote -v
git ls-files | grep -E '(^|/)\.env|id_rsa|secret|client-data' && exit 1 || true
```

Expected: backend source is reviewable in GitHub and secrets are absent.

---

### Task 1: Add RAG/memory migrations

**Objective:** Add the schema above without touching live production DB manually.

**Files:**

- Create: `migrations/YYYYMMDD_rag_memory.sql`
- Modify: `src/db.js` only if the app still uses boot-time schema creation for these tables.

**Steps:**

1. Write migration for `knowledge_sources`, `knowledge_chunks`, `agent_memories`, and `rag_events`.
2. Add indexes and foreign keys.
3. Add rollback notes if there is no migration runner yet.
4. Run migration against a local/dev Postgres only.

**Verification:**

```bash
npm test -- --runInBand
psql "$DEV_DATABASE_URL" -f migrations/YYYYMMDD_rag_memory.sql
psql "$DEV_DATABASE_URL" -c "\dt knowledge_sources knowledge_chunks agent_memories rag_events"
```

Expected: tables exist in dev only; no production DB changes from the PR agent.

---

### Task 2: Extract ingestion/chunking into backend code

**Objective:** Replace shell-only seeding with a reusable, testable ingestion module.

**Files:**

- Create: `src/knowledge/chunker.js`
- Create: `src/knowledge/ingest.js`
- Test: `tests/knowledge/chunker.test.js`
- Test: `tests/knowledge/ingest.test.js`

**Behavior:**

- Split on blank lines first.
- Pack paragraphs into default ~800 character chunks.
- Preserve metadata: `company_id`, `source_id`, `source_file`, `chunk_index`, `kind`, `created_at`.
- Return deterministic chunk IDs for tests.
- Reject empty files and oversized single chunks with clear errors.

**Verification:**

```bash
npm test -- tests/knowledge/chunker.test.js tests/knowledge/ingest.test.js
```

Expected: deterministic chunk tests pass without Qdrant or Ollama network access by mocking embedding/upsert calls.

---

### Task 3: Add admin ingestion endpoint or CLI wrapper

**Objective:** Provide a governed way to seed client knowledge without manual ad-hoc shell steps.

**Files:**

- Create: `src/routes/knowledge.js` or add route section in `src/server.js`
- Modify: `src/orchestrator.js` if ingestion helpers live there temporarily
- Test: `tests/knowledge/routes.test.js`
- Docs: update `newfire_backend_docker/SEEDING_GUIDE.md`

**Endpoint proposal:**

```http
POST /admin/companies/:companyId/knowledge-sources
Authorization: Bearer <admin JWT>
Content-Type: application/json

{
  "title": "Pricing and FAQ",
  "source_type": "manual",
  "content": "plain text only for MVP"
}
```

**Rules:**

- Admin-only for MVP.
- `companyId` must exist.
- Store source metadata in `knowledge_sources`.
- Embed and upsert chunks to Qdrant.
- Store chunk audit rows in `knowledge_chunks`.
- Never log raw content.

**Verification:**

```bash
npm test -- tests/knowledge/routes.test.js
```

Expected: non-admin denied, admin accepted, rows created, Qdrant upsert mocked.

---

### Task 4: Make retrieval auditable and citation-ready

**Objective:** Ensure every answer can show what it used.

**Files:**

- Modify: `src/orchestrator.js`
- Test: `tests/rag/retrieve-context.test.js`

**Changes:**

- Return retrieval hits with `source_id`, `chunk_id`, `source_file`, `score`, and `text`.
- Keep `company_id` payload filter mandatory.
- Insert a `rag_events` row per retrieval attempt.
- Include source labels in the context block.
- If there are no hits, instruct the model not to invent specifics.

**Verification:**

```bash
npm test -- tests/rag/retrieve-context.test.js
```

Expected: cross-company payloads are ignored; event row records hit count and source chunks.

---

### Task 5: Add memory extraction with review gate

**Objective:** Add persistent memory without letting the model silently store unapproved facts.

**Files:**

- Create: `src/memory/extract.js`
- Create: `src/memory/store.js`
- Test: `tests/memory/extract.test.js`
- Test: `tests/memory/store.test.js`

**MVP behavior:**

- Start rule-based, not model-based:
  - explicit user preferences: "remember that", "I prefer", "call me"
  - owner/admin notes
  - repeated unanswered facts can become `pending_review`
- Store as `pending_review` unless created by admin/owner action.
- Retrieval only uses `approved` memory.
- Add admin list/approve/delete endpoints later.

**Verification:**

```bash
npm test -- tests/memory/extract.test.js tests/memory/store.test.js
```

Expected: extracted facts are compact, tenant-scoped, and default to `pending_review`.

---

### Task 6: Inject approved memories into chat context

**Objective:** Make agents remember durable facts while respecting tenant and agent scope.

**Files:**

- Modify: `src/orchestrator.js`
- Test: `tests/memory/chat-memory.test.js`

**Rules:**

- Fetch approved memories for `(company_id, agent_id OR null, subject_key if known)`.
- Limit memory block to a small max, e.g. 8 facts or 1000 chars.
- Put memory below higher-priority system safety rules.
- Do not let memory override source-grounded business policies.

**Verification:**

```bash
npm test -- tests/memory/chat-memory.test.js
```

Expected: approved memory appears in prompt; pending/deleted/cross-tenant memory does not.

---

### Task 7: Cloud-routing privacy policy for RAG hits

**Objective:** Prevent sensitive retrieved context from being sent to cloud models when policy forbids it.

**Files:**

- Modify: `src/orchestrator.js`
- Test: `tests/rag/cloud-policy.test.js`

**Rules:**

- If retrieved chunks have `sensitivity: legal` or company `allow_cloud_models = false`, force local provider or return a clear policy error if no local model is available.
- Log policy decision without logging raw context.
- Keep Funmi privacy rules explicit in docs.

**Verification:**

```bash
npm test -- tests/rag/cloud-policy.test.js
```

Expected: sensitive retrieved context never selects OpenRouter/Anthropic/OpenAI.

---

### Task 8: Update operational docs and manual smoke tests

**Objective:** Make the feature operable without guessing.

**Files:**

- Modify: `newfire_backend_docker/SEEDING_GUIDE.md`
- Modify: `progress/qdrant_test/README.md`
- Create: `docs/RAG_MEMORY_RUNBOOK.md` or equivalent repo-local runbook

**Include:**

- how to seed a dev tenant
- how to verify Qdrant health
- how to run local mocked tests
- how to run manual dev-only end-to-end smoke test
- how to delete a tenant's knowledge/memory
- what not to commit

---

## Follow-up GitHub issues to create

1. **Source-control backend repository before RAG implementation**
   - Required blocker for issues #3 and #4.
2. **Add RAG/memory database migrations**
   - Tables: `knowledge_sources`, `knowledge_chunks`, `agent_memories`, `rag_events`.
3. **Extract reusable knowledge ingestion module**
   - Move shell script behavior into testable backend code.
4. **Add admin knowledge-source ingestion endpoint**
   - Admin-only MVP for plaintext content.
5. **Add retrieval audit events and citation metadata**
   - Make RAG observable and reviewable.
6. **Add persistent memory extraction with approval workflow**
   - Start rule-based and pending-review by default.
7. **Enforce local-only routing for sensitive RAG context**
   - Especially legal-sensitive clients.
8. **Add RAG/memory deletion and retention workflow**
   - Tenant offboarding, GDPR-style deletion, and backup policy.

---

## Acceptance criteria for issue #4

This design issue is complete when:

- this plan is committed in GitHub;
- it names exact code paths and services to change;
- it separates MVP tasks from later enhancements;
- it identifies the backend source-control blocker;
- it lists follow-up implementation issues;
- it avoids production data access and secret exposure.

---

## Later enhancements, not MVP

- Client self-serve file upload UI.
- Google Drive/Notion/Airtable connectors.
- Automatic stale-content detection.
- Model-based memory summarization after rule-based memory is proven.
- Human-in-the-loop approval dashboard for memory and outgoing legal drafts.
- Per-client vector collection backups and restore workflows.
- MCP exposure of tenant-safe `qdrant_search` after auth/allowlist review.
- ROI dashboard metrics: grounded-answer rate, hallucination avoidance, time saved, deflection rate.

---

## Rollout sequence

1. **Docs PR now:** this issue #4 plan only.
2. **Governance PR:** backend source-control setup.
3. **Schema PR:** migrations and no-op model helpers.
4. **Ingestion PR:** testable chunking and mocked Qdrant writes.
5. **Retrieval PR:** audit events and citations.
6. **Memory PR:** pending-review durable facts.
7. **Policy PR:** local-only sensitive RAG routing.
8. **Runbook PR:** deletion, seeding, and smoke-test operations.

This keeps the CEO agent aligned with the core rule: governed branch/PR implementation, no direct production edits.
