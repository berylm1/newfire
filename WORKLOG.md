# NewFire Worklog

Total hours logged: **60.8h** across 11 days.

| Date | Hours | Description |
|---|---|---|
| 2026-06-22 | 1h | add LangGraph workflow skeleton with human approval interrupt |
| | **1h** | *day total* |
| 2026-06-23 | 0h | remove hardcoded RAG MCP key default from mcp_verify.py |
| | **0h** | *day total* |
| 2026-06-24 | 2h | add 20-prompt eval harness across legal/nonprofit/tech tenants |
|  | 3h | build Hawthorn & Pell intake & conflict-check agent |
|  | 4h | add legal citation checker and nonprofit grant scout agents |
| | **9h** | *day total* |
| 2026-06-29 | 2h | build daily briefing agent for the legal tenant |
|  | 3h | split conflicts and activity log into services, wire vision intake and WhatsApp handler into shared feed |
| | **5h** | *day total* |
| 2026-07-01 | 2h | add pytest coverage for activity log and conflicts services |
|  | 0.5h | add auto-generated worklog from commit history |
|  | 4h | stand up vector DB and RAG service for document search |
|  | 0.1h | refresh worklog |
|  | 2h | add CI pipeline with local DGX-backed code review |
|  | 0.1h | refresh worklog |
|  | 0.3h | cap review script context and drop keep-alive to avoid hogging DGX memory |
|  | 0.1h | refresh worklog |
| | **9.1h** | *day total* |
| 2026-07-02 | 2h | add approval_service for durable HITL approval queue |
|  | 3h | make intake and citation-checker approvals durable across processes |
|  | 0.1h | refresh worklog |
|  | 1h | fix duplicate approvals and missing id on HITL resume |
|  | 0.1h | refresh worklog |
|  | 0.1h | document idempotent-create behavior in approval_service README |
|  | 0.1h | refresh worklog |
| | **6.4h** | *day total* |
| 2026-07-03 | 3.5h | add webhook_service for generic inbound triggers |
|  | 1h | add process_webhook_events poller |
|  | 0.1h | refresh worklog |
| | **4.6h** | *day total* |
| 2026-07-07 | 0.3h | document required production env vars for webhook_service and its poller |
|  | 0.1h | refresh worklog |
| | **0.4h** | *day total* |
| 2026-07-08 | 4h | add memory_service for cross-session client history |
|  | 0.1h | refresh worklog |
|  | 1.2h | fix client_key routing and recall error-handling in memory_service |
|  | 0.1h | refresh worklog |
| | **5.4h** | *day total* |
| 2026-07-14 | 5h | add case_service and notify_service foundation for immigration pivot |
|  | 2h | wire daily_briefing to case_service and notify_service |
|  | 1.3h | fix overdue key dates being silently dropped from the briefing |
|  | 0.1h | refresh worklog |
|  | 0.1h | fix ruff lint failure breaking CI since the webhook_service push |
|  | 0.1h | refresh worklog |
|  | 2h | add client_hub_service composing case and notify for Phase 3 |
|  | 0.1h | refresh worklog |
|  | 0.5h | allow browser CORS on client_hub_service for the demo UI |
|  | 0.1h | refresh worklog |
| | **11.3h** | *day total* |
| 2026-07-21 | 3.5h | add case_jeopardy_check rules engine for Phase 5 |
|  | 0.1h | refresh worklog |
|  | 5h | add visa_bulletin_service and visa_bulletin_check for Phase 8 |
| | **8.6h** | *day total* |
