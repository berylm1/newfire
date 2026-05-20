# Phase 2: Network Isolation and Public Access Plan

## The Problem You're Solving

You want to sell AI services to small businesses (metered API access, AI agents for repetitive tasks) but your homelab currently sits on your home network. If you open it to the internet, attackers could reach your personal devices (laptops, phones, other access points).

## The Solution (Simple Terms)

### What You Have Now

```
Internet
  |
  +-- Fios Router (family/personal internet)
  |     +-- Phones, laptops, TV, etc.
  |
  +-- Brazil Router (second access point)
  |     +-- More personal devices
  |
  +-- GL.iNet Router (homelab)
        +-- Minisforum (control plane)
        +-- DGX Spark (compute)
        +-- Your Mac connects here too
```

All three routers share the same internet connection or are on the same network. A breach of the homelab could reach personal devices.

### What You Want

```
Internet
  |
  +-- Fios Router (personal, ISOLATED)
  |     +-- Family devices (completely separate)
  |
  +-- Brazil Router (personal, ISOLATED)
  |     +-- More personal devices (completely separate)
  |
  +-- GL.iNet Router (homelab, ISOLATED)
        +-- VLAN or separate subnet
        +-- Minisforum (control plane)
        +-- DGX Spark (compute)
        |
        +-- OpenZiti Overlay (zero trust tunnel)
              +-- Small Business A connects here
              +-- Small Business B connects here
              +-- Your Mac connects here
              +-- Nobody else can even SEE the network
```

## The Three Tools You Found (and What They Do)

### 1. OpenZiti (github.com/openziti/ziti)

**What it is:** A zero-trust networking overlay. Think of it as a private, invisible internet tunnel.

**Why it matters:** Right now, Tailscale lets anyone on your Tailscale network reach your services. OpenZiti goes further:
- Services are **invisible** to the internet (no open ports at all)
- Each user/app gets their own identity with specific permissions
- You control exactly who can reach which service
- Even if someone knows your IP, they can't see or reach anything

**Simple analogy:** Tailscale is like giving someone a key to your building. OpenZiti is like the building doesn't exist unless you have the right key, and even then you can only enter the rooms you're authorized for.

### 2. NetFoundry (netfoundry.io)

**What it is:** The managed/hosted version of OpenZiti. Same technology, but NetFoundry handles the infrastructure.

**Why it matters:** Instead of running your own OpenZiti controller (which is complex), NetFoundry gives you a dashboard to:
- Create networks
- Issue identities to clients
- Set up policies (who can access what)
- Monitor connections

**Simple analogy:** OpenZiti is like building your own phone network. NetFoundry is like getting a phone plan from a carrier that uses the same technology.

**Recommendation:** Start with NetFoundry (easier), migrate to self-hosted OpenZiti later if needed.

### 3. KubeClaw (github.com/iMerica/kubeclaw)

**What it is:** Kubernetes deployment for OpenClaw. It packages OpenClaw and its agents into Kubernetes containers that can scale up/down automatically.

**Why it matters:** Right now your system runs on bare Docker containers. If 50 small businesses start using your API simultaneously:
- Docker containers have fixed resources (can't auto-scale)
- No automatic failover if a container crashes
- Manual management of everything

KubeClaw on Kubernetes would:
- Auto-scale agent workers based on demand
- Restart crashed containers automatically
- Load balance across multiple machines
- Rolling updates with zero downtime

**Simple analogy:** Docker is like having 3 employees who each do one job. Kubernetes is like having a manager who hires/fires workers based on how busy the restaurant is.

## The Plan (Phases)

### Phase 2A: Network Isolation (Do This First)

Physically separate the homelab network from personal networks.

```
Internet (ISP)
  |
  +-- Fios Router ──── Personal devices (VLAN 10)
  |
  +-- Brazil Router ── Personal devices (VLAN 20)
  |
  +-- GL.iNet Router ─ Homelab ONLY (VLAN 30)
        |
        +-- Minisforum
        +-- DGX Spark
        +-- NO personal devices on this network
```

**How:**
1. Give the GL.iNet router its own subnet (e.g., 10.0.50.0/24)
2. Make sure there's no route between the homelab subnet and personal subnets
3. The GL.iNet router handles its own DHCP and firewall
4. Your Mac connects via Tailscale or OpenZiti (not directly on the homelab WiFi)

### Phase 2B: Zero Trust Access with OpenZiti/NetFoundry

Replace Tailscale with OpenZiti for production access.

```
Small Business A ──[OpenZiti tunnel]──> APISIX (:9080) ──> DGX Spark
Small Business B ──[OpenZiti tunnel]──> APISIX (:9080) ──> DGX Spark
Your Mac ──────────[OpenZiti tunnel]──> Everything (admin)

The internet sees: NOTHING
No open ports. No visible services. Zero attack surface.
```

**Steps:**
1. Sign up for NetFoundry (free tier available)
2. Create a network
3. Install OpenZiti edge router on the Minisforum
4. Create service definitions (APISIX on 9080, OpenClaw on 18789, etc.)
5. Create identities for each customer
6. Each customer installs a lightweight OpenZiti client (tunneler)
7. They can only reach the services you authorize

### Phase 2C: KubeClaw (Kubernetes for Scaling)

When you have multiple paying customers, move from Docker to Kubernetes.

```
GL.iNet Router
  |
  +-- Minisforum (K3s master node)
  |     +-- KubeClaw (OpenClaw pods, auto-scaling)
  |     +-- APISIX (ingress controller)
  |     +-- Prometheus + Grafana
  |
  +-- DGX Spark (K3s worker node)
        +-- GPU pods (model inference)
        +-- OpenHands pods
        +-- Auto-scaled based on demand
```

**Why K3s?** It's lightweight Kubernetes, perfect for 2 machines. Full Kubernetes is overkill.

### Phase 2D: KEDA Autoscaler

**What it is:** KEDA (Kubernetes Event-Driven Autoscaling) watches metrics and automatically scales pods up/down based on demand.

**Why it matters:** Without KEDA, you manually decide how many agent workers to run. With KEDA:
- API request queue gets long? KEDA spins up more OpenCode/OpenHands workers automatically
- Nobody using the system at 3 AM? KEDA scales down to save GPU memory for other models
- Sudden spike from a customer? KEDA responds in seconds, not minutes

**How it works with our architecture:**

```
Customer request arrives
  |
  +-- APISIX (metering) --> OpenClaw (routing) --> Agent Worker Pod
                                                      |
                                           KEDA watches: queue depth,
                                           GPU utilization, request rate
                                                      |
                                           Too many requests? --> Scale UP (more pods)
                                           Idle for 5 min? --> Scale DOWN (free resources)
```

**KEDA scalers we would use:**
- `prometheus` scaler: Scale based on APISIX request rate metrics
- `cron` scaler: Pre-scale during business hours, scale down at night
- Custom metrics: Scale based on GPU memory available on DGX Spark

**Example KEDA config (future):**
```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: opencode-worker-scaler
spec:
  scaleTargetRef:
    name: opencode-worker
  minReplicaCount: 1
  maxReplicaCount: 10
  triggers:
  - type: prometheus
    metadata:
      serverAddress: http://prometheus:9090
      metricName: apisix_http_status
      query: sum(rate(apisix_http_status{route="dgx-inference-metered"}[1m]))
      threshold: "5"    # Scale up when more than 5 req/sec
  - type: cron
    metadata:
      timezone: America/New_York
      start: 0 8 * * 1-5    # 8 AM weekdays
      end: 0 18 * * 1-5     # 6 PM weekdays
      desiredReplicas: "3"  # Pre-scale for business hours
```

**Simple analogy:** KEDA is like an automatic thermostat for your worker pods. It senses the temperature (demand) and adjusts the heating (workers) without you touching anything.

### Phase 2E: Multi-Tenant Isolation with NemoClaw

NemoClaw sandboxes provide isolation per tenant:
- Each tenant gets their own sandbox (Landlock + seccomp + network namespace)
- Separate filesystem, separate network, separate process space
- Per-tenant model access and resource quotas

```
NemoClaw on DGX Spark:
  |
  +-- Sandbox: tenant-a (Tenant A)
  |     GPU: 40 GB quota
  |     Models: deepseek-r1:32b-8k
  |     Network: isolated namespace
  |
  +-- Sandbox: tenant-b (Tenant B)
  |     GPU: 40 GB quota
  |     Models: glm4:9b
  |     Network: isolated namespace
  |
  +-- Sandbox: system (internal)
        GPU: 8 GB reserved
        Admin tools
```

This needs further exploration of NemoClaw's sandbox capabilities to confirm.

## Priority Order

| Priority | Task | When | Why |
|----------|------|------|-----|
| 1 | Network isolation (separate subnets) | Now | Protect personal devices before opening to the world |
| 2 | OpenZiti/NetFoundry | Next | Zero-trust access for customers, no open ports |
| 3 | NemoClaw multi-tenant sandboxes | Next | Per-tenant GPU isolation on DGX Spark |
| 4 | Per-customer APISIX consumers | Next | Billing, rate limiting per customer |
| 5 | KubeClaw on K3s | When you have 5+ customers | Auto-scaling, reliability |
| 6 | KEDA Autoscaler | After K3s | Event-driven scaling based on demand |

## What Small Businesses Get

When this is done, a small business customer gets:

1. **An API key** with metered access (tokens/day, rate limits)
2. **A secure tunnel** (OpenZiti) that connects them directly to your AI services
3. **Multiple AI models** to choose from (fast, reasoning, cloud)
4. **Agent workers** that can handle coding, dev, and automation tasks
5. **A dashboard** to monitor their usage
6. **Zero setup on their end** besides installing the OpenZiti tunneler app

And your personal network stays completely isolated and invisible.
