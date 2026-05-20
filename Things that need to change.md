Whiteboard → NewFire Homelab Map                                                                                  
                                         
  Going column by column. ✅ = covered, ⚠️  = partial/planned, ❌ = gap.                                             
                                                                                                                    
  1. Fundamentals                                                                                                   
                                                                                                                    
  Conceptual layer — no infra mapping. You're fluent here. ✅                                                       
                                                                                                                    
  2. Data — BIGGEST GAP                                                                                             
                                                            
  ┌──────────────┬────────┬────────────────────────────────────────────────────────────────────┐                    
  │     Item     │ Status │                               Notes                                │
  ├──────────────┼────────┼────────────────────────────────────────────────────────────────────┤
  │ Embedding    │ ✅     │ nomic-embed-text on DGX                                            │
  ├──────────────┼────────┼────────────────────────────────────────────────────────────────────┤
  │ Vector DB    │ ❌     │ Nothing deployed. Where do embeddings live?                        │                    
  ├──────────────┼────────┼────────────────────────────────────────────────────────────────────┤                    
  │ Knowledge DB │ ❌     │ Funmi has case docs, Sherifah has brand assets — no filing cabinet │                    
  ├──────────────┼────────┼────────────────────────────────────────────────────────────────────┤                    
  │ RAG          │ ❌     │ Funmi's legal research agent can't cite her own precedents         │
  ├──────────────┼────────┼────────────────────────────────────────────────────────────────────┤                    
  │ Fine-tuning  │ N/A    │ not needed yet                                                     │
  └──────────────┴────────┴────────────────────────────────────────────────────────────────────┘                    
                                                            
  Debug: agents look smart but are amnesiac about client-specific content. Add Qdrant or Chroma + a RAG pipeline    
  before onboarding Funmi.
                                                                                                                    
  3. Intelligence Layer                                     

  ┌─────────────────────┬─────────────────────────────────────────────────────────────┐
  │        Item         │                           Status                            │
  ├─────────────────────┼─────────────────────────────────────────────────────────────┤
  │ System prompts      │ ✅ per-agent in Paperclip                                   │
  ├─────────────────────┼─────────────────────────────────────────────────────────────┤
  │ Memory (persistent) │ ❌ context window only, no cross-session memory             │                             
  ├─────────────────────┼─────────────────────────────────────────────────────────────┤                             
  │ Multimodal          │ ⚠️  Whisper audio ✅, no image/video                         │                             
  ├─────────────────────┼─────────────────────────────────────────────────────────────┤                             
  │ Guardrails          │ ⚠️  Warden planned in Claude Corp; legal disclaimers planned │
  └─────────────────────┴─────────────────────────────────────────────────────────────┘                             
   
  Debug: "Memory" on the board means long-term — currently every conversation starts cold.                          
                                                            
  4. Models & Providers — STRONGEST COLUMN ✅                                                                       
                                                            
  Ollama (local) + OpenRouter (cloud) + smart routing in OpenClaw. Whisper for voice. Matches the board's "don't    
  fall in love with one model" principle exactly.           
                                                                                                                    
  5. Infrastructure & Connectivity                          

  ┌──────────────────┬───────────────────────────────────────────────────────────────┐
  │       Item       │                            Status                             │
  ├──────────────────┼───────────────────────────────────────────────────────────────┤
  │ API              │ ✅ APISIX                                                     │
  ├──────────────────┼───────────────────────────────────────────────────────────────┤
  │ Webhooks         │ ❌ no inbound triggers from client tools (Gmail, forms, CRMs) │
  ├──────────────────┼───────────────────────────────────────────────────────────────┤                              
  │ Endpoint         │ ⚠️  Caddy + zrok2 in progress                                  │
  ├──────────────────┼───────────────────────────────────────────────────────────────┤                              
  │ MCP              │ ❌ not deployed — would let clients plug their own tools in   │
  ├──────────────────┼───────────────────────────────────────────────────────────────┤                              
  │ Function calling │ ✅ OpenClaw + gog CLI                                         │
  ├──────────────────┼───────────────────────────────────────────────────────────────┤                              
  │ SDK              │ ❌ no client-facing SDK                                       │
  └──────────────────┴───────────────────────────────────────────────────────────────┘                              
   
  Debug: the system is reachable but not reactive. Without webhooks, automations can't fire from real-world events. 
                                                            
  6. Agents & Automation                                                                                            
                                                            
  ┌──────────────────────┬────────────────────────────────────────────────────────────────────┐
  │         Item         │                               Status                               │
  ├──────────────────────┼────────────────────────────────────────────────────────────────────┤
  │ Agent                │ ✅                                                                 │
  ├──────────────────────┼────────────────────────────────────────────────────────────────────┤
  │ Orchestration        │ ✅ OpenClaw                                                        │
  ├──────────────────────┼────────────────────────────────────────────────────────────────────┤                     
  │ Multi-agent workflow │ ⚠️  Claude Corp + CongaLine planned                                 │
  ├──────────────────────┼────────────────────────────────────────────────────────────────────┤                     
  │ Human-in-the-loop    │ ❌ who approves Funmi's legal drafts before they leave the system? │
  ├──────────────────────┼────────────────────────────────────────────────────────────────────┤                     
  │ Tool use             │ ✅                                                                 │
  └──────────────────────┴────────────────────────────────────────────────────────────────────┘                     
                                                            
  Debug: HITL is a legal/compliance risk for Funmi specifically.                                                    
   
  7. No-Code Builder Tools — SECOND BIGGEST GAP                                                                     
                                                            
  Nothing on this layer. Sherifah and Funmi won't write JSON configs. The board's point ("right tool in the right   
  situation") means clients need a visual builder. Options: 
  - Embed n8n as the workflow layer inside Paperclip                                                                
  - Build a minimal flow UI in the Paperclip dashboard                                                              
  - Use Flowwise for RAG pipelines specifically       
                                                                                                                    
  Without this, every workflow change = a ticket to you.                                                            
                                                                                                                    
  8. Business Layer                                                                                                 
                                                                                                                    
  ┌──────────────────────┬───────────────────────────────────────────────────────────┐
  │         Item         │                          Status                           │
  ├──────────────────────┼───────────────────────────────────────────────────────────┤
  │ Use case             │ ✅ clear for both pilots                                  │
  ├──────────────────────┼───────────────────────────────────────────────────────────┤
  │ ROI                  │ ❌ not measured — no "hours saved" or "$ saved" dashboard │                              
  ├──────────────────────┼───────────────────────────────────────────────────────────┤                              
  │ Prompt engineering   │ ⚠️  per-agent, no versioning/A-B testing                   │                              
  ├──────────────────────┼───────────────────────────────────────────────────────────┤                              
  │ AI stack             │ ✅                                                        │
  ├──────────────────────┼───────────────────────────────────────────────────────────┤                              
  │ AI avatars (persona) │ ❌ Sherifah's receptionist has no defined voice/face      │
  ├──────────────────────┼───────────────────────────────────────────────────────────┤                              
  │ AI strategy          │ ✅ Launch Plan exists                                     │
  └──────────────────────┴───────────────────────────────────────────────────────────┘                              
                                                            
  Priority Order to Fix (Build Wisely)                                                                              
                                                            
  1. Vector DB + RAG — unblocks Funmi entirely (Qdrant, ~1 day)                                                     
  2. n8n inside Paperclip — unblocks recurring-task automation for both clients
  3. Webhooks layer — lets real events (new email, form submit) fire agents                                         
  4. HITL approval queue — required before Funmi goes live                                                          
  5. Persistent memory — so agents "know" the client across sessions
  6. ROI dashboard — hours saved, $ saved, per client (Grafana panel)                                               
  7. MCP server — strategic: future-proofs client integrations                                                      
  8. AI avatars — brand polish for Sherifah's receptionist        


Tools that we have been given: 

Tools Used to Build the AI Homelab                                                                                
   
  Hardware                                                                                                          
                                                            
  - Minisforum X1 Pro 370 (america, 100.79.80.119) — control plane, Ryzen AI 9 HX 370 + Radeon 890M + 50 TOPS NPU   
  - NVIDIA DGX Spark (ghana, 100.88.112.5) — GPU compute engine
  - GL-X3000 router (nigeria, 100.76.78.50) — networking                                                            
                                                                                                                    
  Orchestration & Agent Layer                                                                                       
                                                                                                                    
  - OpenClaw (:18789) — gateway/orchestrator, smart model routing, fallback, cron, flows                            
  - OpenHands (:3000, DGX) — autonomous agent with GPU      
  - OpenCode (:3002) — coding agent worker                                                                          
  - NemoClaw (gRPC :8080, DGX) — per-client sandbox isolation
  - Paperclip AI (:3100) — company/agent management, budgets, audit logs                                            
  - Claude Corp — file-based autonomous overnight daemon                                                            
  - CongaLine (:8642–8647) — fleet management, per-client Docker containers                                         
  - LLMtary — pentest app on DGX for pre-launch security audit                                                      
                                                                                                                    
  Models & Inference                                                                                                
                                                                                                                    
  - Ollama (:11434 on both machines) — deepseek-r1:32b/70b, glm4:9b, qwen2.5:7b, gemma3                             
  - OpenRouter — Claude Sonnet 4.5, DeepSeek R1, GLM-5.1, minimax-m2.7, Nemotron Nano
  - Whisper medium (:9000, DGX) — speech-to-text                                                                    
  - nomic-embed-text — embeddings                                                                                   
                                                                                                                    
  Gateway, Networking, Security                                                                                     
                                                            
  - APISIX (:9080, admin :9180) — auth, rate limiting, metering, 3 consumer keys                                    
  - zrok2 v2.0.1 (:18080/:8080) — self-hosted tunneling     
  - OpenZiti (controller :1280, router :3022) — zero-trust overlay                                                  
  - Tailscale — private mesh                                                                                        
  - Caddy — TLS overlay (planned)                                                                                   
  - UFW + fail2ban — host firewall                                                                                  
  - Mesibo / Telegram — mobile chat delivery                                                                        
                                                                                                                    
  Observability & Data                                                                                              
                                                                                                                    
  - Prometheus (:9090), Grafana (:3003)                                                                             
  - PostgreSQL, RabbitMQ, InfluxDB (zrok2 stack)
                                                                                                                    
  Dev & Ops                                                                                                         
                                                                                                                    
  - Docker / Docker Compose — container runtime for most services                                                   
  - WebDAV plugin — Finder/Files access via OpenClaw        
                                                                                                                    
  Memory snapshots are 2–21 days old; verify current state if you need live details.   


 Based on the 20-day plan (today is Day 10 of 20) and the backend architecture decided Apr 17, here's what's still 
  needed to actually deliver "reduce repeatable tasks + optimize workflow" for Sherifah and Funmi.                  
                                                                                                                    
  Directly Tied to Workflow Automation                                                                              
                                                                                                                    
  1. Claude Corp daemon (Phase 3, Apr 22-23) — the core value prop. Runs autonomous overnight SLUMBER cycles        
  (content batches for Sherifah, legal pre-research for Funmi) with Warden quality gates. This is what makes "set it
   and forget it" real.                                                                                             
  2. CongaLine fleet (Days 9-10, Apr 19-20) — per-client isolated agent containers (ports 8642-8647). Without it,
  clients share infrastructure and can't scale independently.                                                       
  3. Cron automation + agent templates — listed in homelab "next steps" Week 3. Templates let new clients spin up
  repeatable workflows (inbox triage, content drafting, intake) without custom engineering each time.               
  4. Onboarding interview + backend pipeline — the Apr 17 architecture: signup → AI interview → parse
  recommendations → auto-create Paperclip company + OpenClaw workers + APISIX consumer + NemoClaw sandbox. Not yet  
  built.                                                    
                                                                                                                    
  Client Delivery Layer                                                                                             
   
  5. Mesibo or Telegram channel (Day 8, Apr 18) — mobile chat delivery. Both pilot clients need phone access; agents
   are useless if clients can't reach them.                 
  6. OpenClaw WebDAV plugin (Day 4) — Finder/Files drag-and-drop for legal doc drafts and marketing assets.         
  7. NewFire frontend onboarding wizard — Week 2 item. Real signup, dashboard, persistent agents (replacing         
  localStorage hacks).                                                                                              
                                                                                                                    
  Launch Blockers (not automation, but required)                                                                    
                                                            
  8. Domain + Caddy TLS (Days 2-3) — newfire.ai with wildcard subdomains; professional trust for paying clients.    
  9. LLMtary security audit (Days 14-15) — pentest before real client data touches the system.
  10. Grafana budget tracker + client dashboards + alerts (Day 16) — visibility into per-agent spend and SLAs.      
  11. Stripe billing (Week 4) — commercial model.                                                                   
  12. Operational runbook + E2E tests (Days 17-18).                                                                 
                                                                                                                    
  Gap Worth Flagging                                                                                                
                                                            
  The plan doesn't yet name a workflow/trigger engine for recurring business tasks (e.g., "every Monday 9am,        
  generate Sherifah's weekly content batch"). OpenClaw cron covers simple schedules, but productized repeatable-task
   automation for clients likely needs a trigger UI in Paperclip or a dedicated layer. Worth deciding before Week 3 
  agent templates. 


