# OpenZiti / NetFoundry Research for NewFire Homelab

**Date:** 2026-04-06
**Purpose:** Replace Tailscale with OpenZiti for zero-trust networking across the NewFire homelab

---

## Table of Contents

1. [What is OpenZiti vs NetFoundry](#1-what-is-openziti-vs-netfoundry)
2. [Prerequisites](#2-prerequisites)
3. [Architecture for This Homelab](#3-architecture-for-this-homelab)
4. [Step-by-Step Setup Plan](#4-step-by-step-setup-plan)
5. [How It Replaces Tailscale](#5-how-it-replaces-tailscale)
6. [Gotchas and Common Issues](#6-gotchas-and-common-issues)
7. [Sources](#7-sources)

---

## 1. What is OpenZiti vs NetFoundry

### The Relationship

- **OpenZiti** is the fully open-source zero-trust networking platform, licensed under Apache 2.0. It is the core technology, and all networking functionality lives here.
- **NetFoundry** is the company that created and sponsors OpenZiti. They offer a commercial, cloud-managed SaaS layer on top of OpenZiti.
- Think of it like: OpenZiti is to NetFoundry as Kubernetes is to a managed K8s service (GKE/EKS).

### What You Get with Each

| Feature | OpenZiti (Self-Hosted) | NetFoundry Cloud |
|---|---|---|
| **Cost** | Free forever | Free 30-day trial, then $5-$15/endpoint/month |
| **Controller** | You host and manage it | Hosted by NetFoundry |
| **Edge Routers** | You deploy them | Mix of NetFoundry PoPs + your own |
| **Admin Console (ZAC)** | Included, self-hosted | Included, cloud-hosted |
| **Support** | Community (Discourse forum) | 24/7 commercial support with SLAs |
| **Global PoPs** | None (your infrastructure only) | 100+ points of presence |
| **Uptime SLA** | Your responsibility | NetFoundry guarantees |

### NetFoundry Free Trial Limits

- 30 days
- 1 region
- Up to 10 endpoints
- Up to 1 TB data transfer
- Trial networks deactivated after 5 business days of inactivity

### Recommendation for This Homelab

**Use fully self-hosted OpenZiti.** You get:
- No cost, no endpoint limits, no data limits
- Complete control of your network and data
- No dependency on NetFoundry's service
- The same core technology. NetFoundry Cloud is just OpenZiti with a management layer

The only trade-off is you manage the controller yourself, which is straightforward with Docker.

---

## 2. Prerequisites

### System Requirements (Minisforum X1 Pro 370)

The Minisforum is more than capable. OpenZiti is lightweight:

- **CPU:** Minimal. The controller and router are Go binaries, very efficient
- **RAM:** ~256 MB for controller + router combined (trivial on your system)
- **Disk:** ~500 MB for binaries, configs, PKI, and logs
- **Docker:** Required (you already have this)
- **Docker Compose:** Required (you already have this)

### Network Requirements

**Ports OpenZiti needs (on the Minisforum):**

| Port | Purpose | Direction | Notes |
|---|---|---|---|
| **1280** | Controller API + ZAC admin console | Inbound | Only needs to be reachable by your routers and admin |
| **6262** | Controller control plane (router-to-controller) | Inbound | Internal, router mesh communication |
| **3022** | Edge Router listener (SDK/tunneler connections) | Inbound | Clients connect here to reach services |

**Critical point:** OpenZiti does NOT require any ports open on the public internet for a homelab-only setup. All three ports above only need to be reachable within your GL.iNet subnet. If you want external access (from outside your home), only port 3022 needs to be reachable from the internet (via port forwarding on your GL.iNet router), or you can use a public cloud relay router.

### Software to Install

Everything runs in Docker. You need:

1. `openziti/ziti-controller` (or the quickstart all-in-one image)
2. `openziti/ziti-router` (edge router, can be in the same compose stack)
3. `openziti/ziti-edge-tunnel` (tunneler for hosting services on the Minisforum and DGX Spark)
4. The `ziti` CLI binary (for administration, included in the controller container or available as a standalone install)

---

## 3. Architecture for This Homelab

### Conceptual Overview

```
                    YOUR LAPTOP / PHONE
                    (Ziti Desktop Edge client)
                           |
                           | (mTLS, port 3022)
                           v
 +-----------------------------------------------------+
 |           MINISFORUM X1 PRO 370 (Ubuntu)             |
 |                                                      |
 |  +---------------+    +------------------+           |
 |  | Ziti           |    | Ziti Edge Router |           |
 |  | Controller     |<-->| (port 3022)      |           |
 |  | (port 1280)    |    +------------------+           |
 |  | (port 6262)    |           |                      |
 |  +---------------+           |                      |
 |                               |                      |
 |  +---------------------------+--+                    |
 |  | ziti-edge-tunnel (run-host)  |                    |
 |  | Hosts services:              |                    |
 |  |  - APISIX (:9080)           |                    |
 |  |  - OpenClaw (:18789)        |                    |
 |  |  - OpenHands (:3000)        |                    |
 |  |  - Grafana (:3003)          |                    |
 |  +------------------------------+                    |
 +-----------------------------------------------------+
                           |
                     GL.iNet Router
                           |
 +-----------------------------------------------------+
 |              DGX SPARK (GPU Server)                  |
 |                                                      |
 |  +---------------------------+                       |
 |  | ziti-edge-tunnel (run-host)|                       |
 |  | Hosts GPU services         |                       |
 |  +---------------------------+                       |
 +-----------------------------------------------------+
```

### Key Components Mapped to Your Setup

#### Controller (runs on Minisforum)
- The brain of the network. Manages identities, services, policies, and PKI.
- Provides REST API and the ZAC web admin console.
- Only one controller needed for a homelab.

#### Edge Router (runs on Minisforum)
- The data plane. All traffic flows through edge routers.
- Clients (your laptop, phone) connect to the edge router to reach services.
- One router is sufficient for a homelab. It runs alongside the controller.
- The router has a built-in "tunnel" mode that can also host services directly.

#### Identities (one per device/client)
- Each device that participates in the network gets a cryptographic identity (x509 certificate).
- You will create identities for:
  - `minisforum-host` (the tunneler on the Minisforum that hosts services)
  - `dgx-spark-host` (the tunneler on the DGX Spark, if hosting GPU services)
  - `joba-laptop` (your laptop for accessing services)
  - `joba-phone` (your phone, optional)

#### Services (one per application you want to expose)
- Each application you want to access through OpenZiti is defined as a "service."
- Services have two configs:
  - **host.v1** tells the hosting tunneler where to forward traffic (e.g., `localhost:9080`)
  - **intercept.v1** tells the client tunneler how to intercept traffic (e.g., DNS name `apisix.ziti`)

#### Policies (authorization rules)
- **Service Policies** control which identities can access which services:
  - **Bind** policies: which identity can HOST a service (server side)
  - **Dial** policies: which identity can CONNECT TO a service (client side)
- **Edge Router Policies**: which identities can use which edge routers
- **Service Edge Router Policies**: which services can be accessed through which routers

### Services You Will Create

| Service Name | host.v1 (server side) | intercept.v1 (client side) | Hosted By |
|---|---|---|---|
| `apisix-gateway` | `tcp://localhost:9080` | `apisix.ziti:9080` | minisforum-host |
| `openclaw` | `tcp://localhost:18789` | `openclaw.ziti:18789` | minisforum-host |
| `openhands` | `tcp://localhost:3000` | `openhands.ziti:3000` | minisforum-host |
| `grafana` | `tcp://localhost:3003` | `grafana.ziti:3003` | minisforum-host |

---

## 4. Step-by-Step Setup Plan

### Phase 1: Deploy Controller + Edge Router on Minisforum (30 min)

#### Step 1.1: Create the project directory

```bash
mkdir -p /opt/openziti
cd /opt/openziti
```

#### Step 1.2: Download the all-in-one Docker Compose file

```bash
wget https://get.openziti.io/dock/all-in-one/compose.yml
```

#### Step 1.3: Create a `.env` file with your settings

```bash
cat > .env << 'EOF'
# Use the Minisforum's LAN IP (from GL.iNet subnet)
# Replace with your actual LAN IP
ZITI_CTRL_ADVERTISED_ADDRESS=192.168.8.100
ZITI_CTRL_ADVERTISED_PORT=1280
ZITI_ROUTER_ADVERTISED_ADDRESS=192.168.8.100
ZITI_ROUTER_PORT=3022
ZITI_PWD=CHANGE_ME_TO_A_STRONG_PASSWORD
EOF
```

**Important:** Replace `192.168.8.100` with the Minisforum's actual LAN IP on the GL.iNet subnet.

#### Step 1.4: Start the controller and router

```bash
docker compose up -d
```

#### Step 1.5: Verify it is running

```bash
# Check containers are up
docker compose ps

# Check the controller API is responding
curl -sk https://localhost:1280/edge/client/v1/version
```

#### Step 1.6: Access the ZAC admin console

Open a browser and go to: `https://192.168.8.100:1280/zac/`

- Accept the self-signed certificate warning
- Login with username `admin` and the password you set in `.env`

---

### Phase 2: Install the Ziti CLI (5 min)

The CLI is already inside the controller container. You can exec into it:

```bash
# Option A: Use the CLI from inside the container
docker compose exec quickstart ziti edge login \
  https://localhost:1280/edge/management/v1 \
  -u admin -p 'CHANGE_ME_TO_A_STRONG_PASSWORD' \
  --yes

# Option B: Install the CLI on the host (alternative)
curl -sS https://get.openziti.io/install.bash | sudo bash
```

For the rest of this guide, CLI commands assume you are inside the container:

```bash
docker compose exec quickstart bash
```

Once inside, authenticate:

```bash
ziti edge login localhost:1280 -u admin -p 'CHANGE_ME_TO_A_STRONG_PASSWORD' --yes
```

---

### Phase 3: Create Identities (10 min)

#### Step 3.1: Create the host identity for the Minisforum tunneler

```bash
ziti edge create identity "minisforum-host" \
  --role-attributes "homelab-hosts" \
  --jwt-output-file /persistent/minisforum-host.jwt
```

#### Step 3.2: Create the host identity for DGX Spark (if needed later)

```bash
ziti edge create identity "dgx-spark-host" \
  --role-attributes "homelab-hosts" \
  --jwt-output-file /persistent/dgx-spark-host.jwt
```

#### Step 3.3: Create a client identity for your laptop

```bash
ziti edge create identity "joba-laptop" \
  --role-attributes "homelab-clients" \
  --jwt-output-file /persistent/joba-laptop.jwt
```

**Important:** JWT tokens expire in 24 hours. Enroll them promptly after creation.

#### Step 3.4: Copy the JWT files out of the container

```bash
# Run from the host (not inside the container)
docker compose cp quickstart:/persistent/minisforum-host.jwt ./minisforum-host.jwt
docker compose cp quickstart:/persistent/joba-laptop.jwt ./joba-laptop.jwt
```

---

### Phase 4: Create Service Configs (15 min)

Run these inside the container (or with the host CLI if installed).

#### Step 4.1: Create host configs (server-side, tells tunneler where to forward)

```bash
# APISIX Gateway
ziti edge create config "apisix-host-config" host.v1 \
  '{"protocol":"tcp","address":"127.0.0.1","port":9080}'

# OpenClaw
ziti edge create config "openclaw-host-config" host.v1 \
  '{"protocol":"tcp","address":"127.0.0.1","port":18789}'

# OpenHands
ziti edge create config "openhands-host-config" host.v1 \
  '{"protocol":"tcp","address":"127.0.0.1","port":3000}'

# Grafana
ziti edge create config "grafana-host-config" host.v1 \
  '{"protocol":"tcp","address":"127.0.0.1","port":3003}'
```

**Note on address:** If the tunneler runs in Docker with `network_mode: host`, use `127.0.0.1`. If the tunneler runs in a Docker bridge network, use the Docker host IP or the container name of the target service. For simplicity, use `network_mode: host` for the tunneler.

#### Step 4.2: Create intercept configs (client-side, tells client how to reach service)

```bash
# APISIX Gateway
ziti edge create config "apisix-intercept-config" intercept.v1 \
  '{"protocols":["tcp"],"addresses":["apisix.ziti"],"portRanges":[{"low":9080,"high":9080}]}'

# OpenClaw
ziti edge create config "openclaw-intercept-config" intercept.v1 \
  '{"protocols":["tcp"],"addresses":["openclaw.ziti"],"portRanges":[{"low":18789,"high":18789}]}'

# OpenHands
ziti edge create config "openhands-intercept-config" intercept.v1 \
  '{"protocols":["tcp"],"addresses":["openhands.ziti"],"portRanges":[{"low":3000,"high":3000}]}'

# Grafana
ziti edge create config "grafana-intercept-config" intercept.v1 \
  '{"protocols":["tcp"],"addresses":["grafana.ziti"],"portRanges":[{"low":3003,"high":3003}]}'
```

---

### Phase 5: Create Services (10 min)

Link each service to its host + intercept config pair:

```bash
ziti edge create service "apisix-gateway" \
  -c "apisix-host-config,apisix-intercept-config" \
  --role-attributes "homelab-services"

ziti edge create service "openclaw" \
  -c "openclaw-host-config,openclaw-intercept-config" \
  --role-attributes "homelab-services"

ziti edge create service "openhands" \
  -c "openhands-host-config,openhands-intercept-config" \
  --role-attributes "homelab-services"

ziti edge create service "grafana" \
  -c "grafana-host-config,grafana-intercept-config" \
  --role-attributes "homelab-services"
```

---

### Phase 6: Create Policies (10 min)

#### Step 6.1: Bind policies (which identities can HOST services)

```bash
# Allow homelab-hosts to bind (host/serve) all homelab services
ziti edge create service-policy "homelab-bind-policy" Bind \
  --service-roles '#homelab-services' \
  --identity-roles '#homelab-hosts' \
  --semantic 'AnyOf'
```

#### Step 6.2: Dial policies (which identities can CONNECT to services)

```bash
# Allow homelab-clients to dial (connect to) all homelab services
ziti edge create service-policy "homelab-dial-policy" Dial \
  --service-roles '#homelab-services' \
  --identity-roles '#homelab-clients' \
  --semantic 'AnyOf'
```

#### Step 6.3: Edge Router policies (which identities can use which routers)

The all-in-one quickstart typically creates default router policies, but if needed:

```bash
# Allow all identities to use any edge router
ziti edge create edge-router-policy "default-router-policy" \
  --identity-roles '#all' \
  --edge-router-roles '#all'

# Allow all services to be accessed through any edge router
ziti edge create service-edge-router-policy "default-service-router-policy" \
  --service-roles '#all' \
  --edge-router-roles '#all'
```

---

### Phase 7: Deploy the Tunneler on Minisforum (15 min)

The tunneler hosts your services on the Ziti network. It runs as a Docker container in `run-host` mode.

#### Step 7.1: Enroll the minisforum-host identity

```bash
# From the host machine (not inside the controller container)
docker run --rm \
  -v /opt/openziti:/ziti \
  openziti/ziti-edge-tunnel enroll \
  --jwt /ziti/minisforum-host.jwt \
  --identity /ziti/minisforum-host.json
```

This creates `minisforum-host.json`, which is the enrolled identity file.

#### Step 7.2: Create a Docker Compose file for the tunneler

Create `/opt/openziti/tunneler-compose.yml`:

```yaml
services:
  ziti-host:
    image: openziti/ziti-host
    restart: unless-stopped
    network_mode: host
    volumes:
      - /opt/openziti/minisforum-host.json:/ziti-edge-tunnel/ziti_id.json
    environment:
      - ZITI_IDENTITY_BASENAME=ziti_id
```

**Why `network_mode: host`?** The tunneler needs to reach your local services (APISIX on :9080, etc.) on localhost. Host networking makes this seamless.

#### Step 7.3: Start the tunneler

```bash
docker compose -f /opt/openziti/tunneler-compose.yml up -d
```

#### Step 7.4: Verify the tunneler is connected

```bash
docker compose -f /opt/openziti/tunneler-compose.yml logs -f
```

Look for messages indicating successful connection to the controller and service hosting.

---

### Phase 8: Set Up Client Access on Your Laptop (15 min)

#### For macOS:

1. Download **Ziti Desktop Edge** from the Mac App Store (search "Ziti Desktop Edge")
2. Open the app
3. Transfer the `joba-laptop.jwt` file to your Mac (SCP, email, USB, etc.)
4. In the app, click "+" to add an identity
5. Select the JWT file
6. The app enrolls and connects automatically

#### For Windows:

1. Download from: https://github.com/openziti/desktop-edge-win/releases
2. Install and run as administrator
3. Add the JWT identity file through the GUI

#### For Linux (CLI):

```bash
# Install the tunneler
curl -sS https://get.openziti.io/install.bash | sudo bash -s ziti-edge-tunnel

# Enroll
ziti-edge-tunnel enroll --jwt joba-laptop.jwt --identity joba-laptop.json

# Run
sudo ziti-edge-tunnel run --identity joba-laptop.json
```

#### For mobile (iOS/Android):

OpenZiti has mobile apps available on the respective app stores. Search for "Ziti Mobile Edge."

---

### Phase 9: Test Everything (10 min)

Once your laptop's Ziti Desktop Edge is connected:

```bash
# Test APISIX
curl http://apisix.ziti:9080

# Test OpenClaw
curl http://openclaw.ziti:18789

# Test OpenHands
curl http://openhands.ziti:3000

# Test Grafana
curl http://grafana.ziti:3003
```

The Ziti tunneler on your laptop intercepts DNS for `*.ziti` addresses and routes traffic through the Ziti overlay network to the Minisforum.

You can also open these URLs in your browser directly.

---

## 5. How It Replaces Tailscale

### What Changes

| Aspect | Tailscale (Current) | OpenZiti (New) |
|---|---|---|
| **Access model** | VPN with full network access to the machine | Per-service, so only authorized services are visible |
| **Authentication** | SSO via identity provider | x509 certificates (per-device identity) |
| **Port exposure** | Services listen on tailnet IPs, all ports reachable | Services are "dark" with no open ports at all |
| **DNS** | `*.tailscale.net` or MagicDNS | `*.ziti` (custom, you control the names) |
| **Infrastructure** | Tailscale coordination server (cloud) | Your own controller on the Minisforum |
| **Data path** | Direct (DERP relay as fallback) | Through your edge router (all self-hosted) |
| **Client software** | Tailscale app | Ziti Desktop Edge app |
| **Cost** | Free for personal (limited nodes) | Free forever (self-hosted, unlimited) |

### What Stays the Same

- **SSH access**: You can still SSH into your machines. Create a Ziti service for SSH (port 22) on the Minisforum and DGX Spark. However, during the transition period, keep Tailscale running as a fallback.
- **GL.iNet router**: No changes needed to your router config for internal-only use.
- **Docker services**: Your existing Docker containers (APISIX, OpenClaw, etc.) keep running exactly as they are. The Ziti tunneler sits alongside them.

### Migration Strategy

1. **Day 1:** Deploy OpenZiti alongside Tailscale. Both work simultaneously.
2. **Day 2-7:** Test all services through OpenZiti. Verify everything works.
3. **Day 7+:** Once confident, create an SSH service in OpenZiti, then disable Tailscale.

**Do NOT remove Tailscale until OpenZiti SSH access is verified and working reliably.** Keep Tailscale as a backup for at least one week.

### Adding SSH as a Ziti Service (for Tailscale replacement)

```bash
# Host config for SSH on Minisforum
ziti edge create config "ssh-minisforum-host" host.v1 \
  '{"protocol":"tcp","address":"127.0.0.1","port":22}'

# Intercept config
ziti edge create config "ssh-minisforum-intercept" intercept.v1 \
  '{"protocols":["tcp"],"addresses":["minisforum.ziti"],"portRanges":[{"low":22,"high":22}]}'

# Service
ziti edge create service "ssh-minisforum" \
  -c "ssh-minisforum-host,ssh-minisforum-intercept" \
  --role-attributes "homelab-services"

# Then SSH via:
ssh user@minisforum.ziti
```

---

## 6. Gotchas and Common Issues

### 1. JWT Tokens Expire in 24 Hours

When you create an identity, the JWT enrollment token is valid for only 24 hours. If you do not enroll within that window, you must delete and recreate the identity. Plan to create identities and enroll them in the same session.

### 2. Advertised Address Must Be Reachable

The `ZITI_CTRL_ADVERTISED_ADDRESS` and `ZITI_ROUTER_ADVERTISED_ADDRESS` must be IP addresses or hostnames that your clients can actually reach. Common mistakes:
- Setting it to `localhost` or `127.0.0.1` because other machines cannot reach this
- Setting it to a Docker internal hostname, which is not reachable from outside Docker
- Use the Minisforum's LAN IP on the GL.iNet subnet (e.g., `192.168.8.100`)

### 3. Self-Signed Certificates (Browser Warnings)

The quickstart generates self-signed certificates. Your browser will show warnings when accessing the ZAC console. This is expected, so accept the warning. The certificates are still providing encryption.

### 4. DNS Resolution for .ziti Addresses

The Ziti tunneler runs its own DNS resolver (default on `100.64.0.2`). If your laptop has DNS issues:
- On macOS, the Desktop Edge app handles DNS automatically
- On Linux, the tunneler modifies `systemd-resolved` configuration
- If DNS does not resolve `*.ziti`, check that the tunneler is running and the identity is enrolled

### 5. Docker Network Mode Matters for the Tunneler

- Use `network_mode: host` if the tunneler needs to reach services on `localhost` (this is your case)
- Use `network_mode: bridge` if services are in the same Docker compose stack and you reference them by container name
- If you use bridge mode, the `host.v1` config address must point to the service's Docker IP or container name, not `127.0.0.1`

### 6. Certificate Expiry

OpenZiti certificates have expiration dates. The quickstart defaults are generous, but check periodically. Symptoms of expired certs:
- `failed to verify certificate` errors in logs
- `certificate has expired` messages
- Identities unable to connect

Fix: Renew certificates or re-deploy the controller with fresh PKI.

### 7. Firewall on the Minisforum

Make sure `ufw` (or whatever firewall you use) allows ports 1280, 6262, and 3022:

```bash
sudo ufw allow 1280/tcp comment "OpenZiti Controller"
sudo ufw allow 6262/tcp comment "OpenZiti Control Plane"
sudo ufw allow 3022/tcp comment "OpenZiti Edge Router"
```

### 8. Controller Must Start Before Routers

If you restart the Docker stack, the controller must be fully ready before the router tries to connect. The all-in-one compose file handles this with health checks, but if you split them into separate files, add `depends_on` with a health check condition.

### 9. External Access (From Outside Your Home Network)

If you want to access services from outside your home (e.g., from a coffee shop):
- **Option A:** Port-forward port 3022 on your GL.iNet router to the Minisforum. Set `ZITI_ROUTER_ADVERTISED_ADDRESS` to your home's public IP or a DDNS hostname.
- **Option B:** Deploy a small edge router on a cheap VPS (e.g., Oracle Cloud free tier) that acts as a relay. Both your home router and the VPS router connect outbound to the controller, so no port forwarding is needed.
- **Option C:** Keep Tailscale for external access and use OpenZiti only for service-level access internally.

### 10. Debugging: Enable Verbose Logs

```bash
# For the controller/router
docker compose logs -f quickstart

# For the tunneler
docker compose -f tunneler-compose.yml logs -f

# Set debug log level in the tunneler
# Add to environment in compose:
#   - ZITI_LOG=4
```

### 11. The "Four Policy" Requirement

A common frustration: you create a service and identity but traffic does not flow. OpenZiti requires ALL FOUR policy types to be satisfied:
1. Service Policy (Bind): identity authorized to host the service
2. Service Policy (Dial): identity authorized to connect to the service
3. Edge Router Policy: identity authorized to use the edge router
4. Service Edge Router Policy: service authorized to use the edge router

If any one of these is missing, traffic will not flow. The quickstart creates default router policies (#3 and #4), but you must always create #1 and #2.

### 12. Identity File Security

The enrolled identity JSON file (`minisforum-host.json`, `joba-laptop.json`) contains the private key. Treat it like an SSH private key:
- Do not commit to git
- Do not share
- Set permissions: `chmod 600 *.json`

---

## Quick Reference: Complete Command Sequence

For copy-paste convenience, here is the entire setup in order (after the Docker compose is running):

```bash
# === LOGIN ===
ziti edge login localhost:1280 -u admin -p 'YOUR_PASSWORD' --yes

# === IDENTITIES ===
ziti edge create identity "minisforum-host" --role-attributes "homelab-hosts" --jwt-output-file /persistent/minisforum-host.jwt
ziti edge create identity "joba-laptop" --role-attributes "homelab-clients" --jwt-output-file /persistent/joba-laptop.jwt

# === HOST CONFIGS ===
ziti edge create config "apisix-host-config" host.v1 '{"protocol":"tcp","address":"127.0.0.1","port":9080}'
ziti edge create config "openclaw-host-config" host.v1 '{"protocol":"tcp","address":"127.0.0.1","port":18789}'
ziti edge create config "openhands-host-config" host.v1 '{"protocol":"tcp","address":"127.0.0.1","port":3000}'
ziti edge create config "grafana-host-config" host.v1 '{"protocol":"tcp","address":"127.0.0.1","port":3003}'

# === INTERCEPT CONFIGS ===
ziti edge create config "apisix-intercept-config" intercept.v1 '{"protocols":["tcp"],"addresses":["apisix.ziti"],"portRanges":[{"low":9080,"high":9080}]}'
ziti edge create config "openclaw-intercept-config" intercept.v1 '{"protocols":["tcp"],"addresses":["openclaw.ziti"],"portRanges":[{"low":18789,"high":18789}]}'
ziti edge create config "openhands-intercept-config" intercept.v1 '{"protocols":["tcp"],"addresses":["openhands.ziti"],"portRanges":[{"low":3000,"high":3000}]}'
ziti edge create config "grafana-intercept-config" intercept.v1 '{"protocols":["tcp"],"addresses":["grafana.ziti"],"portRanges":[{"low":3003,"high":3003}]}'

# === SERVICES ===
ziti edge create service "apisix-gateway" -c "apisix-host-config,apisix-intercept-config" --role-attributes "homelab-services"
ziti edge create service "openclaw" -c "openclaw-host-config,openclaw-intercept-config" --role-attributes "homelab-services"
ziti edge create service "openhands" -c "openhands-host-config,openhands-intercept-config" --role-attributes "homelab-services"
ziti edge create service "grafana" -c "grafana-host-config,grafana-intercept-config" --role-attributes "homelab-services"

# === POLICIES ===
ziti edge create service-policy "homelab-bind-policy" Bind --service-roles '#homelab-services' --identity-roles '#homelab-hosts' --semantic 'AnyOf'
ziti edge create service-policy "homelab-dial-policy" Dial --service-roles '#homelab-services' --identity-roles '#homelab-clients' --semantic 'AnyOf'
ziti edge create edge-router-policy "default-router-policy" --identity-roles '#all' --edge-router-roles '#all'
ziti edge create service-edge-router-policy "default-service-router-policy" --service-roles '#all' --edge-router-roles '#all'
```

---

## 7. Sources

- [OpenZiti Introduction / What is OpenZiti](https://openziti.io/docs/learn/introduction/)
- [OpenZiti GitHub Repository](https://github.com/openziti/ziti)
- [Docker All-in-One Compose File](https://github.com/openziti/ziti/blob/main/quickstart/docker/all-in-one/compose.yml)
- [Local Docker Quickstart](https://openziti.io/docs/learn/quickstarts/network/local-with-docker)
- [Deploy Router with Docker](https://openziti.io/docs/guides/deployments/docker/router/)
- [Service Configurations (host.v1 / intercept.v1)](https://openziti.io/docs/learn/core-concepts/config-store/overview)
- [Your First Service (Zero Trust Host Access)](https://openziti.io/docs/learn/quickstarts/services/ztha)
- [Creating Service Policies](https://openziti.io/docs/learn/core-concepts/security/authorization/policies/creating-service-policies/)
- [Run the Tunneler with Docker](https://openziti.io/docs/reference/tunnelers/docker/)
- [Linux Tunneler Options and Modes](https://openziti.io/docs/reference/tunnelers/linux/linux-tunnel-options/)
- [Linux Tunneler Troubleshooting](https://openziti.io/docs/reference/tunnelers/linux/linux-tunnel-troubleshooting/)
- [OpenZiti Downloads Page](https://openziti.io/docs/downloads/)
- [NetFoundry Cloud for OpenZiti](https://netfoundry.io/products/netfoundry-platform/netfoundry-cloud-for-openziti/)
- [NetFoundry Pricing](https://netfoundry.io/products/netfoundry-pricing/)
- [NetFoundry vs Tailscale Comparison](https://netfoundry.io/resources/netfoundrys-openziti-vs-tailscale-a-technical-comparison/)
- [OpenZiti Component Architecture](https://netfoundry.io/docs/openziti/learn/introduction/components/)
- [Connection Security (mTLS)](https://netfoundry.io/docs/openziti/learn/core-concepts/security/connection-security/)
- [Enrollment Process](https://openziti.io/docs/learn/core-concepts/security/enrollment/)
- [Router as Local Gateway](https://netfoundry.io/docs/openziti/guides/topologies/gateway/router/)
- [Expired Certificate Troubleshooting](https://openziti.io/docs/guides/troubleshooting/pki-troubleshooting/troubleshoot-expired-certs/)
- [macOS Tunneler](https://openziti.io/docs/reference/tunnelers/macos/)
- [Windows Desktop Edge](https://github.com/openziti/desktop-edge-win)
- [OpenZiti Discourse Community Forum](https://openziti.discourse.group/)
