# NewFire AI: Launch Plan
## Target Launch Date: Thursday, May 1, 2026
## Today's Date: Saturday, April 4, 2026 (27 days remaining)

---

## Week 1: April 4-11 (Infrastructure Completion)

### Saturday April 4 (TODAY) - DONE
- [x] Built full two-machine AI infrastructure from scratch
- [x] OpenClaw gateway running with 3 agents, 4 model aliases, 4-tier fallback
- [x] DGX Spark GPU serving models (deepseek-r1:32b-8k, glm4:9b)
- [x] APISIX metered gateway with 3 consumers and API key auth
- [x] OpenHands (DGX Spark :3000) and OpenCode (Minisforum :3002) deployed
- [x] OpenRouter cloud fallback configured
- [x] Prometheus + Grafana monitoring stack
- [x] Passwordless SSH + sudo on both machines
- [x] Docker log rotation on both machines
- [x] All 8 end-to-end tests passing
- [x] Architecture diagrams and documentation created

### Sunday April 5
- [ ] Verify all services survived overnight (both machines)
- [ ] Run all 8 end-to-end tests
- [ ] Fix APISIX Prometheus metrics (debug port 9091 empty response)
- [ ] Create deepseek-r1:70b-4k context-limited variant and test it
- [ ] Buy networking rack/cage from Amazon for router + Minisforum + DGX Spark
- [ ] Plan physical network isolation (separate GL.iNet from Fios and Brazil routers)

### Monday April 6
- [ ] Physical network isolation: Move GL.iNet router to its own subnet
- [ ] Verify Minisforum and DGX Spark are on isolated network
- [ ] Verify personal devices on Fios/Brazil cannot reach homelab subnet
- [ ] Configure GL.iNet firewall rules (no inbound from other subnets)
- [ ] Research OpenZiti setup requirements

### Tuesday April 7
- [ ] Sign up for NetFoundry (managed OpenZiti)
- [ ] Create first OpenZiti network
- [ ] Install OpenZiti edge router on Minisforum
- [ ] Test: can you access APISIX through OpenZiti tunnel?

### Wednesday April 8
- [ ] Create OpenZiti service definitions for all exposed endpoints (APISIX :9080, OpenClaw :18789, OpenHands :3000, Grafana :3003)
- [ ] Create admin identity (for you) and test all services through OpenZiti
- [ ] Disable Tailscale for production services (keep for SSH only as backup)
- [ ] Verify: services are invisible from the internet (no open ports)

### Thursday April 9
- [ ] NemoClaw multi-tenant: Create second sandbox ("tenant-test")
- [ ] Verify sandbox isolation (tenant-test cannot see my-assistant data)
- [ ] Create APISIX route that maps per-tenant API keys to specific sandboxes
- [ ] Test: tenant-a key reaches sandbox-a, tenant-b key reaches sandbox-b

### Friday April 10
- [ ] End-to-end multi-tenant test with 2 sandboxes
- [ ] Stress test: send 50 concurrent requests through APISIX
- [ ] Monitor GPU memory and response times during load
- [ ] Document Week 1 progress, update all docs
- [ ] Set up the second computer as a backup/test environment (re-install everything following REBUILD_GUIDE.md)

---

## Week 2: April 11-17 (Frontend and Client Experience)

### Saturday April 12 (Note: April 11 is Friday, rest day or catch-up)
- [ ] Choose frontend framework (Next.js recommended)
- [ ] Set up newfire.ai domain (purchase if not owned)
- [ ] Create project repo for the frontend
- [ ] Design landing page wireframe (sections: hero, features, pricing, testimonials, sign up)

### Sunday April 13
- [ ] Build landing page (static, responsive)
- [ ] Build pricing page with 4 tiers (Free, Starter $29, Pro $99, Enterprise)
- [ ] Build sign-up form (email, password, business name, industry)
- [ ] Deploy to Vercel or Netlify for quick iteration

### Monday April 14
- [ ] Build client dashboard (authenticated area)
- [ ] Dashboard: Agent status panel (green/yellow/red indicators)
- [ ] Dashboard: Usage metrics (tokens used today, chart over time)
- [ ] Dashboard: Billing info (current plan, next billing date)

### Tuesday April 15
- [ ] Dashboard: Action center (review AI-drafted content, approve/reject buttons)
- [ ] Dashboard: Agent configuration (enable/disable agents, set schedules)
- [ ] Dashboard: API key management (view key, regenerate, copy)
- [ ] Connect dashboard to APISIX admin API for real data

### Wednesday April 16
- [ ] Build onboarding wizard (multi-step form)
- [ ] Step 1: Business profile (industry, size, pain points)
- [ ] Step 2: Agent selection (recommended agents based on profile)
- [ ] Step 3: Integration setup (connect email, calendar, social)
- [ ] Step 4: Confirmation and first agent activation

### Thursday April 17
- [ ] Build API documentation page (newfire.ai/docs)
- [ ] Document all endpoints: /v1/chat/completions, model list, usage stats
- [ ] Add code examples (Python, JavaScript, curl)
- [ ] Add authentication guide (how to use X-API-Key header)
- [ ] Build admin panel (your view, not client-facing)
- [ ] Full frontend review, fix bugs, test responsive on mobile
- [ ] Document Week 2 progress

---

## Week 3: April 18-24 (Integration, Agents, and Testing)

### Friday April 18
- [ ] Connect frontend sign-up to backend: auto-create APISIX consumer on sign-up
- [ ] Connect frontend sign-up to backend: auto-create NemoClaw sandbox on sign-up
- [ ] Connect frontend sign-up to backend: auto-create OpenClaw agents on sign-up
- [ ] Test full onboarding flow end-to-end

### Saturday April 19
- [ ] Build Sherifah's agent templates:
  - [ ] Lead Generation Agent template (CRM integration, lead scoring)
  - [ ] Marketing Content Agent template (newsletter, blog, social post generation)
  - [ ] Trend Research Agent template (web search, daily briefing)
  - [ ] Receptionist Agent template (call handling, appointment scheduling)

### Sunday April 20
- [ ] Build Funmi's agent templates:
  - [ ] Legal Research Agent template (law updates, case search)
  - [ ] Document Drafter Agent template (visa apps, legal briefs)
  - [ ] Client Intake Agent template (questionnaire, eligibility screening)
  - [ ] Case Tracker Agent template (deadline monitoring, status updates)

### Monday April 21
- [ ] Implement cron scheduling in OpenClaw for automated agents
- [ ] Test: agent runs at scheduled time, produces output, stores in workspace
- [ ] Test: client dashboard shows agent output for review
- [ ] Test: approve button publishes content

### Tuesday April 22
- [ ] Security audit:
  - [ ] Change all default passwords and keys
  - [ ] Review all open ports, close unnecessary ones
  - [ ] Test OpenZiti: verify no services reachable without identity
  - [ ] Test APISIX: verify 401 on all routes without key
  - [ ] Test NemoClaw: verify sandbox isolation (attempt cross-tenant access)
  - [ ] Run: `openclaw security audit --deep`

### Wednesday April 23
- [ ] Load testing: simulate 5 concurrent tenants
- [ ] Monitor: GPU memory, CPU usage, response times, error rates
- [ ] Identify bottlenecks and fix them
- [ ] Test fallback chain: stop DGX Spark Ollama, verify cloud fallback activates
- [ ] Test recovery: restart DGX Spark Ollama, verify system recovers

### Thursday April 24
- [ ] Onboard Ms. Sherifah as beta tester (real account, real agents)
- [ ] Walk her through the dashboard
- [ ] Activate her Lead Gen and Marketing agents
- [ ] Monitor her first 24 hours of automated operation
- [ ] Document Week 3 progress, collect feedback

---

## Week 4: April 25 - May 1 (Polish, Beta, and Launch)

### Friday April 25
- [ ] Collect Sherifah's feedback, fix issues
- [ ] Onboard Aunty Funmi as second beta tester
- [ ] Activate her Legal Research and Client Intake agents
- [ ] Monitor both tenants running simultaneously

### Saturday April 26
- [ ] Fix all bugs found during beta testing
- [ ] Performance optimization based on real usage data
- [ ] Update agent templates based on feedback
- [ ] Add any missing dashboard features clients requested

### Sunday April 27
- [ ] Final security audit (full checklist)
- [ ] Final load test (10 concurrent tenants simulation)
- [ ] Final frontend review (mobile, desktop, all browsers)
- [ ] Set up payment processing (Stripe integration with dashboard)
- [ ] Set up automated billing (APISIX usage data to Stripe)

### Monday April 28
- [ ] Create launch content:
  - [ ] Landing page copy finalized
  - [ ] "How It Works" video or walkthrough
  - [ ] Email announcement template
  - [ ] Social media posts for launch day

### Tuesday April 29
- [ ] Final system check: all 8 tests passing
- [ ] Final check: both beta tenants running smoothly
- [ ] Final check: OpenZiti, APISIX, NemoClaw, OpenClaw all healthy
- [ ] Final check: monitoring dashboards showing clean metrics
- [ ] Backup everything: config snapshots, database dumps

### Wednesday April 30
- [ ] Prepare launch announcement
- [ ] Pre-stage all social media posts
- [ ] Final dress rehearsal: sign up as a new test client, go through entire flow
- [ ] Early to bed. Big day tomorrow.

### Thursday May 1: LAUNCH DAY
- [ ] 7 AM: Run full system health check
- [ ] 8 AM: Verify both beta clients are operational
- [ ] 9 AM: Final go/no-go decision
- [ ] 10 AM: Publish landing page updates
- [ ] 10 AM: Send launch announcement email
- [ ] 10 AM: Post on social media
- [ ] All day: Monitor system health, respond to sign-ups
- [ ] 6 PM: Review Day 1 metrics (sign-ups, usage, errors)
- [ ] Evening: Celebrate. You built this.

---

## Tools Still to Add (Integrated Into Schedule Above)

| Tool | What It Does | When |
|------|-------------|------|
| Network rack/cage | Physical organization | Sunday April 5 |
| Network isolation | Separate homelab from personal network | Monday April 6 |
| OpenZiti / NetFoundry | Zero-trust network access | Tuesday-Wednesday April 7-8 |
| NemoClaw multi-tenant | Per-client sandbox isolation | Thursday-Friday April 9-10 |
| Second machine rebuild | Redundancy, replicate setup | Friday April 10 |
| Frontend (Next.js) | Client-facing website + dashboard | Week 2 (April 12-17) |
| Agent templates | Pre-built agent configs for common use cases | Week 3 (April 19-20) |
| Stripe | Payment processing | Sunday April 27 |
| KubeClaw + K3s | Kubernetes orchestration | Post-launch (when 5+ clients) |
| KEDA Autoscaler | Event-driven auto-scaling | Post-launch (when demand requires) |

---

## Daily Non-Negotiables

Every single day from now until May 1:

1. **Morning check (5 min)**: SSH into both machines, run health checks, verify all services up
2. **End of day commit**: Git commit all code changes, update progress docs
3. **Test what you built**: Never end the day without testing today's work
4. **Update the checklist**: Check off completed items, note blockers

---

## Key Milestones

| Date | Day | Milestone | Success Criteria |
|------|-----|-----------|-----------------|
| April 4 | Saturday | Infrastructure built | All 8 tests passing, 3-tier inference live (DONE) |
| April 10 | Friday | Infrastructure complete | Multi-tenant working, OpenZiti live, network isolated |
| April 17 | Thursday | Frontend complete | Landing page, dashboard, onboarding wizard, API docs all working |
| April 24 | Thursday | First beta client live | Sherifah using the platform with real agents |
| April 30 | Wednesday | Launch ready | All tests passing, 2 beta clients healthy, payments working |
| May 1 | Thursday | LAUNCH | newfire.ai is live and accepting new clients |
