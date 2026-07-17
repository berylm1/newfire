# Tailscale Developer Onboarding Guide — Minisforum & DGX Spark

*Scripts and step-by-step instructions for adding new developers to the NewFire tailnet (Minisforum worker + DGX Spark GPU backend)*

---

## 📁 **Existing Scripts Location**

All Tailscale-related onboarding scripts are in:
```
/home/beryl/.hermes/scripts/
```

| Script | Purpose |
|--------|---------|
| `hourly-github-sync.sh` | Syncs farmer-data-collection repo (has SSH USER fix) |

---

## 🎯 **Quick Overview: How Tailscale Access Works**

```
┌─────────────────────────────────────────────────────────────┐
│                    NEWFIRE TAILNET                          │
│  (newwaveclaw@outlook.com account)                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Admin Console: https://login.tailscale.com/admin/machines │
│                                                             │
│  Devices on tailnet:                                        │
│  • farm-connect (Minisforum)  → 100.79.80.119              │
│  • spark-a439 (DGX Spark)     → 100.88.112.5               │
│  • [New developer device]     → [Auto-assigned IP]         │
│                                                             │
│  Access: SSH via Tailscale IP (no VPN needed)              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📝 **Step-by-Step: Adding a New Developer**

### **Prerequisites (You do this once as admin)**

1. **Add developer to Tailscale organization**
   - Go to: https://login.tailscale.com/admin/machines
   - Click **"Invite user"** → enter their email
   - They'll receive an email to join

2. **Add their device to the tailnet** (they do this)
   - They install Tailscale on their device
   - Sign in with their email (the one you invited)
   - Device automatically joins the NewFire tailnet

---

### **For the New Developer: Device Setup by Platform**

#### **macOS (MacBook Air/Pro)**
```bash
# 1. Install Tailscale
brew install --cask tailscale

# OR download from: https://tailscale.com/download/mac

# 2. Open Tailscale app → Sign in with their email
# 3. Approve the "NewFire" tailnet join request in browser
# 4. Enable SSH access (optional but recommended):
#    System Settings → General → Sharing → Remote Login → ON
```

#### **Linux (Ubuntu/Debian/Fedora/Arch)**
```bash
# 1. Install Tailscale
curl -fsSL https://tailscale.com/install.sh | sh

# 2. Start and authenticate
sudo tailscale up

# 3. Opens browser → sign in with their email
# 4. Approve NewFire tailnet

# 5. (Optional) Allow SSH access
sudo tailscale set --ssh
```

#### **Windows**
```powershell
# 1. Install Tailscale
winget install Tailscale.Tailscale

# OR download from: https://tailscale.com/download/windows

# 2. Open Tailscale app → Sign in with their email
# 3. Approve NewFire tailnet join request in browser
```

#### **iOS / Android**
```
1. Install "Tailscale" from App Store / Play Store
2. Open app → Sign in with their email
3. Approve NewFire tailnet
4. Toggle "Connect" switch ON
```

---

## 🔑 **After Device is Connected: SSH Access Setup**

### **For the New Developer (on their new device)**

```bash
# 1. Find the target device's Tailscale IP
tailscale status
# Look for: farm-connect (Minisforum), spark-a439 (DGX)

# 2. SSH to Minisforum
ssh newwaveclaw@100.79.80.119

# 3. SSH to DGX Spark (jump through Minisforum)
ssh newwaveclaw@100.79.80.119 "ssh newwave-dgx@100.88.112.5"
```

---

## 📋 **Onboarding Checklist for New Developer**

Give this checklist to each new developer:

### **☐ Day 1: Device Connection**
- [ ] Install Tailscale on their device
- [ ] Sign in with their work email
- [ ] Approve "NewFire" tailnet in browser
- [ ] Verify `tailscale status` shows all team devices
- [ ] Test ping to Minisforum: `ping 100.79.80.119`

### **☐ Day 1: SSH Keys (One-time setup)**
```bash
# On their local machine:
ssh-keygen -t ed25519 -C "their.email@company.com"

# Copy public key to Minisforum:
ssh-copy-id newwaveclaw@100.79.80.119
```

### **☐ Day 1: GitHub Access**
- [ ] Add to `newwaveclaw` GitHub organization (if needed)
- [ ] Clone farmer-data-collection: `git clone git@github.com:berylm1/farmer-data-collection.git`
- [ ] Run `./scripts/setup-dev-env.sh` (if exists)

### **☐ Day 1: Hermes Access (for AI agents)**
```bash
# Install Hermes on their device:
curl -fsSL https://get.hermes-agent.dev | bash

# Copy shared config (has DGX Spark model providers):
scp newwaveclaw@100.79.80.119:~/.hermes/config.yaml ~/.hermes/config.yaml

# Test model access:
hermes -z "hello" --provider custom:dgx-spark-ollama --model qwen3-coder-30b-64k
```

### **☐ Day 1: Verify Everything Works**
- [ ] SSH to Minisforum without password
- [ ] Can reach DGX Spark via jump
- [ ] Hermes can use DGX Spark models
- [ ] Can run `git push` to farmer-data-collection

---

## 🛠️ **Helper Scripts to Create/Share**

### **1. Quick Connect Script (save as `~/connect-minisforum-dgx.sh`)**
```bash
#!/usr/bin/env bash
# Quick Tailscale status + SSH test for new developers
# Run: bash connect-minisforum-dgx.sh

echo "=== Tailscale Status ==="
tailscale status --peers=false

echo -e "\n=== Testing SSH to Minisforum ==="
ssh -o ConnectTimeout=5 -o BatchMode=yes newwaveclaw@100.79.80.119 'echo "✓ Minisforum OK: $(hostname)"' || echo "✗ Minisforum failed"

echo -e "\n=== Testing SSH to DGX Spark (via Minisforum) ==="
ssh -o ConnectTimeout=10 -o BatchMode=yes newwaveclaw@100.79.80.119 "ssh -o ConnectTimeout=5 -o BatchMode=yes newwave-dgx@100.88.112.5 'echo \"✓ DGX Spark OK: \$(hostname)\"'" || echo "✗ DGX Spark failed"

echo -e "\n=== Your Tailscale IP ==="
tailscale ip -4
```

### **2. Hermes Config Sync Script (save as `~/sync-hermes-config.sh`)**
```bash
#!/usr/bin/env bash
# Sync Hermes config from Minisforum to current device
# Run: bash sync-hermes-config.sh

MINISFORUM_USER="newwaveclaw"
MINISFORUM_IP="100.79.80.119"

echo "Syncing Hermes config from Minisforum..."
scp "${MINISFORUM_USER}@${MINISFORUM_IP}:~/.hermes/config.yaml" ~/.hermes/config.yaml

echo "Verifying custom providers..."
hermes model | grep -E "(dgx-spark|nemotron|qwen3)"

echo "Testing model access..."
hermes -z "Say OK" --provider custom:dgx-spark-llamacpp --model nemotron-nano-omni --timeout 30
```

### **3. Full Environment Setup Script (save as `~/setup-minisforum-dgx-dev.sh`)**
```bash
#!/usr/bin/env bash
# Complete Minisforum + DGX Spark development environment setup
# Run ONCE on new developer machine: bash setup-minisforum-dgx-dev.sh

set -euo pipefail

echo "=== Minisforum + DGX Spark Development Environment Setup ==="

# 1. Tailscale check
echo "1. Checking Tailscale..."
if ! command -v tailscale &> /dev/null; then
    echo "Installing Tailscale..."
    curl -fsSL https://tailscale.com/install.sh | sh
fi
tailscale up --accept-dns=false

# 2. SSH keys
echo "2. Setting up SSH keys..."
if [ ! -f ~/.ssh/id_ed25519 ]; then
    ssh-keygen -t ed25519 -C "$(git config user.email)" -N ""
fi

# 3. Copy key to Minisforum
echo "  Copying key to Minisforum..."
ssh-copy-id -o StrictHostKeyChecking=accept-new newwaveclaw@100.79.80.119 || true

# 4. Install Hermes
echo "3. Installing Hermes..."
if ! command -v hermes &> /dev/null; then
    curl -fsSL https://get.hermes-agent.dev | bash
    export PATH="$HOME/.local/bin:$PATH"
fi

# 5. Sync Hermes config
echo "4. Syncing Hermes config (DGX Spark models)..."
scp newwaveclaw@100.79.80.119:~/.hermes/config.yaml ~/.hermes/config.yaml
en

# 6. Verify
echo -e "\n=== Verification ==="
tailscale ip -4
hermes model | grep -E "(dgx-spark|nemotron|qwen3)"
echo "Setup complete! Run 'hermes -z \"test\" --provider custom:dgx-spark-ollama --model qwen3-coder-30b-64k' to test"
```

---

## 📍 **Key IPs to Remember**

| Device | Hostname | Tailscale IP | SSH User |
|--------|----------|-------------|----------|
| Minisforum (Worker) | farm-connect | 100.79.80.119 | newwaveclaw |
| DGX Spark (GPU) | spark-a439 | 100.88.112.5 | newwave-dgx (via Minisforum) |

---

## 🆘 **Troubleshooting Common Issues**

| Issue | Fix |
|-------|-----|
| "Permission denied (publickey)" | Run `ssh-copy-id user@ip` again; check `~/.ssh/authorized_keys` on target |
| "Connection refused" | Target device offline? Check `tailscale status`; ensure Tailscale is running |
| "Host key verification failed" | `ssh-keygen -R <ip>` then reconnect with `-o StrictHostKeyChecking=accept-new` |
| Can't reach DGX Spark | Must jump via Minisforum: `ssh user@minisforum "ssh user@dgx"` |
| Hermes "model not found" | Re-sync config: `scp newwaveclaw@100.79.80.119:~/.hermes/config.yaml ~/.hermes/config.yaml` |
| Tailscale "login expired" | Run `tailscale up` again and re-authenticate in browser |

---

## 📞 **Admin Commands (For You)**

```bash
# See all devices on tailnet
tailscale status --peers --json | jq -r '.Peer[] | "\(.TailscaleIPs[0])\t\(.HostName)\t\(.OS)\t\(.Online)"'

# Revoke device access (if developer leaves)
# Go to: https://login.tailscale.com/admin/machines → click device → "Remove"

# Force re-auth on a device
tailscale logout && tailscale up

# Share a device with another tailnet (advanced)
tailscale share --user=email@domain.com --device=device-name
```

---

## 📁 **Where to Store These Scripts**

Save the helper scripts above to:
```
/home/beryl/.hermes/scripts/onboard-minisforum-dgx-dev.sh
/home/beryl/.hermes/scripts/sync-hermes-config.sh
/home/beryl/.hermes/scripts/connect-minisforum-dgx.sh
```

Then any developer can run:
```bash
# From Minisforum (once they have SSH access):
ssh newwaveclaw@100.79.80.119 'cat ~/.hermes/scripts/onboard-minisforum-dgx-dev.sh' | bash
```

---

*Last updated: 2026-06-15 — NewFire tailnet onboarding guide (Minisforum + DGX Spark focus)*