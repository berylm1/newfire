# Minisforum X1 Pro 370 -- Upgrade to Production OpenClaw

## Current State

The Minisforum is already running Ubuntu Linux at `192.168.1.157` with the following Docker containers:

| Container       | Port  | Status  |
|-----------------|-------|---------|
| openclaw-gw     | 18789 | Running |
| openhands-app   | 3000  | Running |
| opencode-app    | 3002  | Running |
| ollama          | 11434 | Running |

**Goal**: Migrate from ad-hoc Docker containers to a properly managed OpenClaw installation via the Ansible installer, with systemd services, agent sandboxing, security hardening, and hooks.

## Step 1: Backup Current State

Before making changes, back up your current configuration:

```bash
# SSH into the Minisforum
ssh newwaveclaw@192.168.1.157

# Create a backup directory
mkdir -p ~/homelab-backup/$(date +%Y%m%d)
cd ~/homelab-backup/$(date +%Y%m%d)

# Backup all Docker container configs
docker inspect openclaw-gw > openclaw-gw-inspect.json
docker inspect openhands-app > openhands-app-inspect.json
docker inspect opencode-app > opencode-app-inspect.json
docker inspect ollama > ollama-inspect.json

# Backup any Docker volumes
docker volume ls > volumes.txt
for vol in $(docker volume ls -q); do
  echo "Backing up volume: $vol"
  docker run --rm -v "$vol":/data -v "$(pwd)":/backup \
    alpine tar czf "/backup/vol-${vol}.tar.gz" -C /data .
done

# Backup Docker Compose files if any
find /home/newwaveclaw -name "docker-compose*.yml" -exec cp {} . \;

# Backup any existing OpenClaw config
cp ~/.openclaw/config.json ./openclaw-config-backup.json 2>/dev/null || true
cp ~/.openclaw/openclaw.json ./openclaw-json-backup.json 2>/dev/null || true

echo "Backup complete at $(pwd)"
```

## Step 2: Stop Existing Containers

```bash
# Gracefully stop existing containers
docker stop openclaw-gw openhands-app opencode-app ollama

# Verify they are stopped
docker ps

# Do NOT remove them yet -- we keep them as fallback until the new setup works
```

## Step 3: Install OpenClaw via Ansible Installer

```bash
# Run the official OpenClaw Ansible installer
# This will install OpenClaw system-wide with proper service management
curl -fsSL https://raw.githubusercontent.com/openclaw/openclaw-ansible/main/install.sh | bash
```

**What the installer does:**
- Installs Ansible if not already present
- Creates the `openclaw` system user and group
- Installs OpenClaw binaries to `/opt/openclaw/`
- Sets up systemd service units
- Configures Docker integration
- Creates default configuration at `/etc/openclaw/`
- Sets up log directories at `/var/log/openclaw/`

Watch the installer output for any errors. Common prerequisites it may install:
- Python 3.10+
- Ansible
- Docker CE (if not already installed)
- jq, curl, git

## Step 4: Switch to the OpenClaw User

```bash
# Switch to the openclaw system user
sudo su - openclaw

# Verify you are the openclaw user
whoami
# Expected: openclaw

# Check the home directory
pwd
# Expected: /home/openclaw or /var/lib/openclaw
```

## Step 5: Run the Onboarding Daemon

```bash
# As the openclaw user, run the onboard command with daemon installation
openclaw onboard --install-daemon
```

This interactive process will:
1. Ask for your preferred authentication method
2. Configure the OpenClaw gateway daemon
3. Set up systemd service for auto-start
4. Create the initial `openclaw.json` configuration
5. Start the OpenClaw gateway on port 18789

Answer the prompts:
- **Auth method**: Choose `apiKey` for now (can add more later)
- **Default model provider**: `ollama` (local, we will add OpenRouter later)
- **Gateway port**: `18789` (keep the same as before)
- **Enable agent sandboxing**: `yes`

## Step 6: Configure the Hooks System

The hooks system allows OpenClaw to trigger actions on events (task start, completion, failure, etc.).

```bash
# Edit the OpenClaw configuration
# The config location depends on the installer, check:
ls /etc/openclaw/openclaw.json 2>/dev/null || ls ~/.openclaw/openclaw.json

# Use the appropriate path below. We will use /etc/openclaw/openclaw.json
sudo nano /etc/openclaw/openclaw.json
```

Add or update the hooks section in `openclaw.json`:

```json
{
  "gateway": {
    "port": 18789,
    "host": "0.0.0.0",
    "logLevel": "info"
  },
  "hooks": {
    "enabled": true,
    "endpoints": [
      {
        "name": "task-logger",
        "url": "http://localhost:9090/hooks/task-event",
        "events": ["task.started", "task.completed", "task.failed"],
        "method": "POST",
        "headers": {
          "Content-Type": "application/json",
          "X-Hook-Secret": "CHANGE_ME_TO_A_RANDOM_SECRET"
        },
        "timeout": 5000,
        "retries": 3
      },
      {
        "name": "metrics-collector",
        "url": "http://localhost:9091/metrics/ingest",
        "events": ["model.request", "model.response", "model.error"],
        "method": "POST",
        "headers": {
          "Content-Type": "application/json"
        },
        "timeout": 3000,
        "retries": 1
      }
    ],
    "deadLetter": {
      "enabled": true,
      "path": "/var/log/openclaw/dead-letters/"
    }
  },
  "agents": {
    "defaults": {
      "model": {
        "primary": "ollama/llama3.1:70b",
        "fallback": "openrouter/anthropic/claude-sonnet-4-5"
      },
      "sandbox": {
        "enabled": true,
        "runtime": "docker",
        "memoryLimit": "2g",
        "cpuLimit": "2.0",
        "networkMode": "bridge",
        "timeout": 3600
      }
    },
    "list": []
  },
  "security": {
    "apiKeys": {
      "enabled": true,
      "keys": []
    },
    "rateLimiting": {
      "enabled": true,
      "requestsPerMinute": 60,
      "requestsPerHour": 1000
    }
  }
}
```

Generate a random hook secret:
```bash
# Generate a secure random secret for hooks
openssl rand -hex 32
# Copy the output and replace CHANGE_ME_TO_A_RANDOM_SECRET in the config above
```

## Step 7: Configure Agent Sandboxing

OpenClaw uses Docker-based isolation for agent execution. Each agent task runs in its own container with resource limits.

```bash
# Create the sandbox network (isolated from host network)
docker network create \
  --driver bridge \
  --subnet 172.20.0.0/16 \
  --opt com.docker.network.bridge.enable_icc=false \
  openclaw-sandbox

# Create the sandbox base image
cat << 'DOCKERFILE' | docker build -t openclaw-sandbox-base -
FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    curl \
    git \
    python3 \
    python3-pip \
    nodejs \
    npm \
    jq \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash sandboxuser
USER sandboxuser
WORKDIR /home/sandboxuser

# Agents run as non-root inside the sandbox
DOCKERFILE
```

Update the sandbox configuration in `openclaw.json`:

```json
{
  "agents": {
    "defaults": {
      "sandbox": {
        "enabled": true,
        "runtime": "docker",
        "image": "openclaw-sandbox-base:latest",
        "network": "openclaw-sandbox",
        "memoryLimit": "2g",
        "cpuLimit": "2.0",
        "pidsLimit": 256,
        "readOnlyRootfs": false,
        "tmpfsSize": "512m",
        "timeout": 3600,
        "autoRemove": true,
        "volumes": {
          "workdir": {
            "type": "tmpfs",
            "destination": "/workspace",
            "options": "size=1g"
          }
        },
        "securityOpt": [
          "no-new-privileges:true"
        ],
        "capDrop": ["ALL"],
        "capAdd": ["NET_BIND_SERVICE"]
      }
    }
  }
}
```

## Step 8: Restart OpenClaw with New Configuration

```bash
# Restart the OpenClaw service to pick up config changes
sudo systemctl restart openclaw

# Check the service status
sudo systemctl status openclaw

# View logs for any errors
sudo journalctl -u openclaw -f --no-pager -n 50
```

Verify the gateway is responding:
```bash
# Test the gateway health endpoint
curl -s http://localhost:18789/health | jq .

# Expected output:
# {
#   "status": "healthy",
#   "version": "x.x.x",
#   "uptime": "...",
#   "agents": { "registered": 0, "active": 0 },
#   "hooks": { "enabled": true, "endpoints": 2 }
# }
```

## Step 9: Set Up Firewall (UFW)

```bash
# Install UFW if not already present
sudo apt install -y ufw

# Reset UFW to defaults (deny incoming, allow outgoing)
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (critical -- do this FIRST before enabling)
sudo ufw allow ssh
# Or explicitly: sudo ufw allow 22/tcp

# Allow OpenClaw Gateway
sudo ufw allow 18789/tcp comment "OpenClaw Gateway"

# Allow OpenHands
sudo ufw allow 3000/tcp comment "OpenHands Agent UI"

# Allow OpenCode
sudo ufw allow 3002/tcp comment "OpenCode Agent UI"

# Allow Tailscale (Tailscale manages its own firewall, but ensure UDP is open)
sudo ufw allow in on tailscale0

# Allow internal traffic from DGX Spark
sudo ufw allow from 192.168.1.158 comment "DGX Spark"

# Allow APISIX (will be set up later)
sudo ufw allow 9080/tcp comment "APISIX HTTP"
sudo ufw allow 9443/tcp comment "APISIX HTTPS"

# Enable the firewall
sudo ufw enable

# Verify the rules
sudo ufw status verbose
```

**Expected output:**
```
Status: active
Logging: on (low)
Default: deny (incoming), allow (outgoing), disabled (routed)
New profiles: skip

To                         Action      From
--                         ------      ----
22/tcp                     ALLOW IN    Anywhere
18789/tcp                  ALLOW IN    Anywhere
3000/tcp                   ALLOW IN    Anywhere
3002/tcp                   ALLOW IN    Anywhere
Anywhere on tailscale0     ALLOW IN    Anywhere
Anywhere                   ALLOW IN    192.168.1.158
9080/tcp                   ALLOW IN    Anywhere
9443/tcp                   ALLOW IN    Anywhere
```

## Step 10: Enable fail2ban

```bash
# Install fail2ban
sudo apt install -y fail2ban

# Create a local config (never edit the main jail.conf)
sudo tee /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
# Ban for 1 hour after 5 failed attempts within 10 minutes
bantime = 3600
findtime = 600
maxretry = 5
backend = systemd

# Email notifications (optional, requires mail agent)
# destemail = your@email.com
# sender = fail2ban@homelab
# action = %(action_mwl)s

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 7200

[openclaw-gateway]
enabled = true
port = 18789
filter = openclaw-gateway
logpath = /var/log/openclaw/gateway.log
maxretry = 10
findtime = 300
bantime = 1800
EOF

# Create a basic filter for OpenClaw (adjust regex based on actual log format)
sudo tee /etc/fail2ban/filter.d/openclaw-gateway.conf << 'EOF'
[Definition]
failregex = ^.*\[WARN\].*unauthorized.*from\s+<HOST>.*$
            ^.*\[ERROR\].*authentication\s+failed.*<HOST>.*$
ignoreregex =
EOF

# Enable and start fail2ban
sudo systemctl enable --now fail2ban

# Check status
sudo fail2ban-client status
sudo fail2ban-client status sshd
```

## Step 11: Enable User Linger

User linger allows systemd user services to run even when the user is not logged in. This is important for the `openclaw` user's services.

```bash
# Enable linger for the openclaw user
sudo loginctl enable-linger openclaw

# Verify linger is enabled
ls /var/lib/systemd/linger/
# Should show: openclaw

# Enable linger for your own user too (for any user-level services)
sudo loginctl enable-linger newwaveclaw

# Verify
loginctl show-user openclaw | grep Linger
# Expected: Linger=yes
```

## Step 12: Clean Up Old Docker Containers

Once you have verified the new OpenClaw installation works correctly:

```bash
# Verify the new setup is working
curl -s http://localhost:18789/health | jq .status
# Expected: "healthy"

# Now remove the old Docker containers
docker rm openclaw-gw openhands-app opencode-app

# Keep the Ollama container if it is still being used by the new setup,
# or remove it if OpenClaw now manages Ollama:
# docker rm ollama

# Clean up unused Docker images
docker image prune -f

# Clean up unused Docker networks
docker network prune -f
```

## Step 13: Verify the Complete Setup

Run through these verification checks:

```bash
# 1. OpenClaw gateway is running and healthy
curl -s http://localhost:18789/health | jq .

# 2. Systemd service is active
sudo systemctl is-active openclaw

# 3. Firewall is enforcing
sudo ufw status

# 4. fail2ban is protecting SSH
sudo fail2ban-client status sshd

# 5. Linger is enabled
loginctl show-user openclaw | grep Linger

# 6. Sandbox network exists
docker network inspect openclaw-sandbox | jq '.[0].Name'

# 7. Tailscale is connected
tailscale status

# 8. Can reach DGX Spark (if already recovered)
ping -c 1 192.168.1.158

# 9. Check resource usage
free -h
docker stats --no-stream
```

## Rollback Plan

If the upgrade fails and you need to revert to the old Docker containers:

```bash
# Stop the new OpenClaw service
sudo systemctl stop openclaw
sudo systemctl disable openclaw

# Restart old containers
docker start openclaw-gw openhands-app opencode-app ollama

# Verify they are running
docker ps

# Test
curl -s http://localhost:18789/health
```

---

**Next step**: Proceed to `03_INTEGRATION_PATTERNS.md` to configure how agents communicate.
