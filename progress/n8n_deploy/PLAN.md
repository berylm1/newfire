  Full end-to-end test you can run yourself                                                                    
                                                            
  1. Go to https://newfire.app                                                                                 
  2. Click "Try a Live Demo" or sign up fresh at /signup    
  3. Complete onboarding (creates a free-tier company)                                                         
  4. Open Dashboard → click "Upgrade →" next to the tier badge → lands on /pricing                             
  5. Click "Start with Starter" or "Upgrade to Pro"                                                            
  6. Stripe Checkout opens in test mode                                                                        
  7. Use test card 4242 4242 4242 4242, any future expiry, any CVC, any ZIP                                    
  8. After pay, you land back on /dashboard?billing=success                                                    
  9. Webhook fires → backend updates your companies.tier to starter or pro, bumps monthly_budget_usd to $10 or 
  $50, flips allow_cloud_models appropriately                                                                  
  10. Dashboard reflects the new tier + budget on next load

Part 2
 Your end-to-end test path                                                                                    
  
  1. Go to https://newfire.app/pricing (signed in or not, doesn't matter)                                      
  2. Click "Start with Starter" or "Upgrade to Pro"                                                            
    - If not signed in → redirects to /signup?plan=X first                                                     
    - If signed in → hits /billing/checkout, backend creates a Stripe session, your browser redirects to Stripe
  3. On Stripe Checkout: use test card 4242 4242 4242 4242, any future expiry, any CVC, any ZIP                
  4. After payment → Stripe redirects you to /dashboard?billing=success                                        
  5. Stripe fires checkout.session.completed → your backend webhook validates the signature → updates          
  companies.tier + monthly_budget_usd + allow_cloud_models                                                     
  6. Reload Dashboard → tier badge shows starter or pro, budget is now $10 or $50, cloud allowed  


# n8n No-Code Builder Deployment Plan

**Target:** Minisforum (america, 100.79.80.119)
**Draft date:** 2026-04-20
**Gap map item:** #2 No-Code Workflow Builder (unblocks client self-serve)
**Review status:** DRAFT, not yet applied to server

## Why n8n, why now

Gap map priority #1 (Qdrant + RAG) closed today. #2 is the workflow builder, which
is what turns Sherifah and Funmi from ticket filers into self-serve operators.
n8n ships ~500 integrations out of the box and has a native HTTP Request node,
so it can call Paperclip agents without a custom SDK. The cost is brand dilution
(n8n UI, not NewFire UI); the benefit is hitting May 1 with a real builder.

## Tenant model

We already isolate per client through CongaLine. Follow the same pattern:

- One n8n container per client, not one shared instance with Projects
- Reason: community edition has thin project isolation; per container gives full
  data, credential, and workflow separation, plus a blast radius of one client
- Port plan (loopback only, never published to LAN):
  - `sherifah`: 127.0.0.1:5678
  - `funmi`:    127.0.0.1:5679
  - Reserve 5680 to 5689 for the next 10 clients
- Shared Postgres on Minisforum, one database per client (`n8n_sherifah`, `n8n_funmi`)
  - Schema isolation gives easy backup per client and clean delete on churn

## Network path

```
Client browser
   -> Caddy TLS (sherifah.newfire.ai)
   -> APISIX :9080 (key-auth + rate-limit + per-consumer)
   -> n8n container 127.0.0.1:5678 (sherifah)
```

Admin access for us goes through Ziti, not the public TLS path:

```
Our laptop (ziti tunnel)
   -> Ziti service `n8n-admin-sherifah`
   -> identity policy = newwaveclaw only
   -> 127.0.0.1:5678
```

Webhook inbound (for real-world triggers later) re-uses the public TLS path
plus a dedicated APISIX route `/webhook/*` with HMAC verification.

## Paperclip integration

Phase 1 (this sprint): use n8n's built-in HTTP Request node. Store a
per-client Paperclip API key as an n8n credential of type `Header Auth`.
Document a "call Paperclip agent" template workflow in each client instance.

Phase 2 (post-launch): publish `n8n-nodes-paperclip` so agents show up as
first-class nodes with a dropdown of available agents. Out of scope for May 1.

## Security posture (pre-launch checklist)

1. n8n container binds to `127.0.0.1` only, never `0.0.0.0`
2. `N8N_ENCRYPTION_KEY` unique per client, 64 hex chars, stored in
   `.env.<client>` with `chmod 600`, owner `newwaveclaw`
3. `N8N_SECURE_COOKIE=true`, `N8N_PROTOCOL=https`, `WEBHOOK_URL=https://<client>.newfire.ai`
4. Disable basic auth; use n8n built-in user management with email + password
   and require 2FA on the owner account
5. Postgres uses a per-client role with privileges limited to that client's DB
6. APISIX consumer per client with key-auth plugin and `limit-req` at 60 rpm
7. Ziti policy for admin paths; no SSH tunnel fallback committed to docs
8. UFW stays default deny inbound; only 80, 443, 22 (Ziti overlay reaches
   loopback directly, so we do not open 5678-5689 at the host firewall)
9. Backups: nightly `pg_dump` per client DB + n8n volume snapshot via restic to
   DGX Spark (`/mnt/backups/n8n/<client>/<date>.tar.zst`)
10. Log shipping: n8n container stdout -> Loki (existing), dashboard panel in
    Grafana `NewFire / n8n` for error rate and execution count per client

## Deployment order (dry run first)

1. Review this plan + compose + env template + APISIX config on the Mac
2. SCP staged files to `newwaveclaw@america:/home/newwaveclaw/n8n/`
3. SSH and run `./deploy.sh sherifah` with `--dry-run` flag, read output
4. Run without `--dry-run`, verify container health and loopback curl
5. Apply APISIX route JSON via admin API, verify 401 without key + 200 with key
6. Add Caddy vhost for `sherifah.newfire.ai`, verify cert issuance
7. Create Ziti admin service + policy, verify tunnel access
8. Repeat steps 3 to 7 for `funmi`
9. Smoke test: one "call Paperclip receptionist agent" workflow per client

Each step has a verify command in `deploy.sh`. Do not advance until the
previous verify passes.

## What I need from you before deploying

- Confirm the subdomain convention: `<client>.newfire.ai` or `<client>.app.newfire.ai`
- Confirm Postgres target: reuse the existing Paperclip Postgres, or new instance
- Confirm encryption key handling: generate on deploy, or pre-provision via
  Bitwarden / 1Password and paste into `.env.<client>` via SCP
- Which client goes first: Sherifah (marketing workflows are lower risk) or Funmi
  (legal, needs HITL which is gap #4 and not yet built, so probably not first)

My recommendation: Sherifah first, reuse Paperclip Postgres with new DB + role,
generate encryption keys on deploy and stash the output in 1Password manually.

## Files in this directory

- `PLAN.md` (this file)
- `docker-compose.yml` (template, client name via env)
- `.env.template` (per-client env, copy to `.env.sherifah` etc.)
- `apisix_routes.json` (routes + consumers + plugins)
- `deploy.sh` (SCP + remote docker compose up, with verify gates)
- `SECURITY_VERIFY.md` (post-deploy checks to tick off)
