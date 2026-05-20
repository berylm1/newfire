# AI Homelab Setup -- Complete Implementation Checklist

Print this checklist and work through it step by step. Check off each item as you complete it.

---

## Phase 0: Prerequisites

- [ ] **Hardware gathered**
  - [ ] USB flash drive (32 GB+, USB 3.0)
  - [ ] External display with HDMI cable
  - [ ] Wired USB keyboard
  - [ ] Both machines powered on and connected to LAN via Ethernet

- [ ] **Accounts and API keys ready**
  - [ ] NVIDIA Developer account (for DGX recovery image download)
  - [ ] Tailscale account (https://tailscale.com)
  - [ ] OpenRouter account and API key (https://openrouter.ai/settings/keys)
  - [ ] OpenRouter credits loaded (or plan to use free-tier models)

- [ ] **Network verified**
  - [ ] Minisforum reachable at 192.168.1.157
  - [ ] Minisforum SSH working: `ssh newwaveclaw@192.168.1.157`
  - [ ] Minisforum Tailscale IP confirmed: 100.79.80.119
  - [ ] DGX Spark visible on network at 192.168.1.158 (may not respond to SSH yet)

- [ ] **Current state documented**
  - [ ] Verified running containers on Minisforum: `docker ps`
  - [ ] Noted openclaw-gw on port 18789
  - [ ] Noted openhands-app on port 3000
  - [ ] Noted opencode-app on port 3002
  - [ ] Noted ollama on port 11434

---

## Phase 1: DGX Spark Recovery (01_DGX_SPARK_RECOVERY.md)

- [ ] **Download recovery image**
  - [ ] Navigated to https://nvidia.com/en-us/drivers/dgx-spark-recovery-software/
  - [ ] Signed in with NVIDIA Developer account
  - [ ] Downloaded recovery image (~15-25 GB)
  - [ ] Verified checksum (if provided)

- [ ] **Create bootable USB**
  - [ ] Identified USB drive device: `diskutil list`
  - [ ] Unmounted USB drive: `diskutil unmountDisk /dev/diskN`
  - [ ] Wrote image to USB: `sudo dd if=recovery.img of=/dev/rdiskN bs=4m status=progress`
  - [ ] Ejected USB: `diskutil eject /dev/diskN`

- [ ] **Boot DGX Spark to UEFI**
  - [ ] Connected USB keyboard to DGX Spark
  - [ ] Connected external display to DGX Spark
  - [ ] Inserted bootable USB drive
  - [ ] Powered on and pressed Esc/Del/F2 to enter UEFI

- [ ] **Configure UEFI**
  - [ ] Restored defaults
  - [ ] Enabled Secure Boot
  - [ ] Set boot override to USB drive
  - [ ] Saved and exited

- [ ] **Run recovery**
  - [ ] Selected Factory Reset / Full System Restore
  - [ ] Confirmed target disk (4 TB NVMe)
  - [ ] Waited for recovery to complete (~20-45 min)
  - [ ] Removed USB and rebooted

- [ ] **First boot setup**
  - [ ] Selected timezone
  - [ ] Created user account (username: _______________, password: stored securely)
  - [ ] Completed initial setup

- [ ] **Verify recovery**
  - [ ] `cat /etc/os-release` shows DGX OS
  - [ ] `nvidia-smi` shows GB10 GPU with 128 GB
  - [ ] `df -h` shows ~4 TB storage
  - [ ] `ip addr show` shows network connectivity

- [ ] **Configure SSH**
  - [ ] SSH server installed and running: `sudo systemctl status ssh`
  - [ ] SSH accessible from Minisforum: `ssh user@192.168.1.158`
  - [ ] SSH key copied: `ssh-copy-id user@192.168.1.158`

- [ ] **Install Tailscale**
  - [ ] Tailscale installed: `curl -fsSL https://tailscale.com/install.sh | sh`
  - [ ] Tailscale authenticated: `sudo tailscale up`
  - [ ] DGX Tailscale IP noted: _______________
  - [ ] Cross-machine ping works (LAN and Tailscale)

- [ ] **Post-recovery housekeeping**
  - [ ] System packages updated: `sudo apt update && sudo apt upgrade -y`
  - [ ] Docker installed and working
  - [ ] NVIDIA container toolkit verified: `docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi`

---

## Phase 2: Minisforum Upgrade (02_MINISFORUM_UPGRADE.md)

- [ ] **Backup current state**
  - [ ] Created backup directory
  - [ ] Docker container configs backed up
  - [ ] Docker volumes backed up
  - [ ] Docker Compose files backed up
  - [ ] Any OpenClaw config backed up

- [ ] **Stop existing containers**
  - [ ] `docker stop openclaw-gw openhands-app opencode-app ollama`
  - [ ] Verified all stopped: `docker ps`

- [ ] **Install OpenClaw via Ansible**
  - [ ] Ran installer: `curl -fsSL https://raw.githubusercontent.com/openclaw/openclaw-ansible/main/install.sh | bash`
  - [ ] Installer completed without errors
  - [ ] OpenClaw binaries present at /opt/openclaw/

- [ ] **Switch to openclaw user**
  - [ ] `sudo su - openclaw`
  - [ ] Verified: `whoami` returns `openclaw`

- [ ] **Run onboard daemon**
  - [ ] `openclaw onboard --install-daemon`
  - [ ] Answered prompts (auth, model provider, port, sandboxing)
  - [ ] Daemon started successfully

- [ ] **Configure hooks system**
  - [ ] Edited openclaw.json with hooks configuration
  - [ ] Generated random hook secret: `openssl rand -hex 32`
  - [ ] Updated secret in config

- [ ] **Configure agent sandboxing**
  - [ ] Created sandbox network: `docker network create openclaw-sandbox`
  - [ ] Built sandbox base image
  - [ ] Updated sandbox config in openclaw.json

- [ ] **Restart and verify OpenClaw**
  - [ ] `sudo systemctl restart openclaw`
  - [ ] `sudo systemctl status openclaw` shows active
  - [ ] `curl http://localhost:18789/health` returns healthy

- [ ] **Set up firewall (UFW)**
  - [ ] UFW installed
  - [ ] SSH allowed (port 22)
  - [ ] OpenClaw allowed (port 18789)
  - [ ] OpenHands allowed (port 3000)
  - [ ] OpenCode allowed (port 3002)
  - [ ] Tailscale interface allowed
  - [ ] DGX Spark IP allowed (192.168.1.158)
  - [ ] APISIX allowed (ports 9080, 9443)
  - [ ] UFW enabled: `sudo ufw enable`
  - [ ] Rules verified: `sudo ufw status verbose`

- [ ] **Enable fail2ban**
  - [ ] fail2ban installed
  - [ ] jail.local created with SSH and OpenClaw jails
  - [ ] OpenClaw filter created
  - [ ] fail2ban running: `sudo fail2ban-client status`

- [ ] **Enable user linger**
  - [ ] `sudo loginctl enable-linger openclaw`
  - [ ] `sudo loginctl enable-linger newwaveclaw`
  - [ ] Verified: `ls /var/lib/systemd/linger/`

- [ ] **Clean up old containers**
  - [ ] New setup verified working
  - [ ] Old containers removed
  - [ ] Images pruned: `docker image prune -f`

---

## Phase 3: Integration Patterns (03_INTEGRATION_PATTERNS.md)

Choose at least one pattern. Pattern 2 (Webhook) is recommended for production.

### Pattern 1: Model Provider (Optional)

- [ ] Configured OpenCode as model provider in openclaw.json
- [ ] Set `agents.defaults.model.primary = "opencode/claude-opus-4-6"`
- [ ] Tested model query through OpenClaw

### Pattern 2: Webhook-Based Task Delegation (Recommended)

- [ ] **OpenCode plugin installed**
  - [ ] `npm install @laceletho/plugin-openclaw`
  - [ ] Plugin configured in opencode.json
  - [ ] Webhook port 9090 configured

- [ ] **OpenClaw webhook agents configured**
  - [ ] opencode-webhook agent added to openclaw.json agents.list
  - [ ] openhands-webhook agent added to openclaw.json agents.list
  - [ ] Callback URLs configured

- [ ] **Environment variables set**
  - [ ] OPENCLAW_WEBHOOK_SECRET generated and stored
  - [ ] OPENCODE_CALLBACK_SECRET generated and stored
  - [ ] Added to /etc/openclaw/env
  - [ ] Services restarted

- [ ] **Webhook flow tested**
  - [ ] Test task sent to webhook endpoint
  - [ ] 202 Accepted response received
  - [ ] Callback received by OpenClaw

### Pattern 3: ACP Agents (Optional -- for persistent sessions)

- [ ] ACP runtimes configured in openclaw.json
- [ ] ACP agents defined (opencode, openhands)
- [ ] Agents spawned: `/acp spawn opencode --mode persistent --thread auto`
- [ ] Status verified: `/acp status`
- [ ] Test message sent and response received

---

## Phase 4: DGX Spark Full Setup (04_DGX_SPARK_SETUP.md)

- [ ] **Phase 4.1: NemoClaw initialized**
  - [ ] NemoClaw installed on DGX
  - [ ] Cluster initialized: `nvidia-nemoclaw init --cluster-name home-lab`
  - [ ] Cluster status verified: healthy
  - [ ] API configured to listen on 0.0.0.0:8080
  - [ ] Auth token created for Minisforum

- [ ] **Phase 4.2: Minisforum connected to DGX**
  - [ ] `openclaw onboard --backend nvidia-nemoclaw --cluster-address 192.168.1.158:8080`
  - [ ] Backend listed: `openclaw backends list`
  - [ ] openclaw.json updated with dgx-spark backend

- [ ] **Phase 4.3: Tenant namespaces created**
  - [ ] Tenant-AI-Research created (50 GB limit)
  - [ ] Tenant-DevOps created (50 GB limit)
  - [ ] Namespaces listed: `nvidia-nemoclaw namespace list`

- [ ] **Phase 4.3: Models deployed**
  - [ ] GLM-5 deployed to Tenant-AI-Research (40 GB, FP16)
  - [ ] GLM-5 status: running
  - [ ] DeepSeek-R1 deployed to Tenant-DevOps (40 GB, FP16)
  - [ ] DeepSeek-R1 status: running
  - [ ] Model inference tested: `curl http://localhost:8001/v1/chat/completions`

- [ ] **Phase 4.4: Agent workers deployed on DGX**
  - [ ] OpenCode worker deployed to Tenant-DevOps
  - [ ] OpenHands worker deployed to Tenant-AI-Research
  - [ ] Workers accessible from Minisforum
  - [ ] Workers registered in OpenClaw as ACP agents

- [ ] **Phase 4.5: Ollama on DGX**
  - [ ] Ollama installed and running on DGX
  - [ ] Configured to listen on 0.0.0.0
  - [ ] Models pulled (llama3.1:70b, codellama:70b, etc.)
  - [ ] GPU acceleration verified: `ollama ps`

- [ ] **Phase 4.6: Smart routing configured**
  - [ ] Routing rules added to openclaw.json
  - [ ] DGX preferred for large models
  - [ ] Minisforum used for small models
  - [ ] OpenRouter as fallback

---

## Phase 5: OpenRouter Integration (05_OPENROUTER_INTEGRATION.md)

- [ ] **OpenRouter API key working**
  - [ ] Key tested: `curl https://openrouter.ai/api/v1/models -H "Authorization: Bearer $KEY"`
  - [ ] Credits confirmed available

- [ ] **OpenClaw + OpenRouter**
  - [ ] `openclaw onboard --auth-choice apiKey --token-provider openrouter --token "$KEY"`
  - [ ] Provider configured in openclaw.json
  - [ ] Model list populated (Claude, Gemini, DeepSeek, Grok, etc.)
  - [ ] Provider pinning configured (deepinfra, inceptron, nebius)

- [ ] **Multi-key support (optional)**
  - [ ] Multiple API keys generated
  - [ ] Load balancing configured
  - [ ] Budget limits set per key

- [ ] **OpenCode + OpenRouter**
  - [ ] `ocode openrouter --model x-ai/grok-4-fast:free`
  - [ ] OpenCode config updated with presets
  - [ ] Tested with free model
  - [ ] Tested with paid model

- [ ] **Smart routing active**
  - [ ] Tiered routing configured (local DGX -> local CPU -> cloud)
  - [ ] Fallback behavior tested (stop DGX model, verify cloud fallback)
  - [ ] Model aliases working (default, code, reasoning, creative, fast)

- [ ] **Cost management**
  - [ ] Daily budget set ($10 or your preference)
  - [ ] Monthly budget set
  - [ ] Alert thresholds configured
  - [ ] Cost monitoring working: `openclaw costs show`

---

## Phase 6: APISIX Metering (06_APISIX_METERING.md)

- [ ] **APISIX installed**
  - [ ] `curl -sL https://run.api7.ai/apisix/quickstart | sh`
  - [ ] APISIX container running
  - [ ] etcd container running
  - [ ] Admin API responding on port 9180
  - [ ] Admin API key changed from default

- [ ] **Inference route created**
  - [ ] dgx-inference-metered route configured
  - [ ] key-auth plugin enabled
  - [ ] ai-proxy plugin enabled
  - [ ] ai-rate-limiting plugin enabled

- [ ] **Consumers created**
  - [ ] personal consumer (unlimited, for self)
  - [ ] app-a consumer (1M tokens/day)
  - [ ] app-b consumer (500K tokens/day)
  - [ ] API keys generated for each consumer
  - [ ] Consumer keys securely stored

- [ ] **Training workload metering**
  - [ ] Redis container deployed
  - [ ] dgx-training-metered route created
  - [ ] GPU hour tracking via serverless functions
  - [ ] GPU hour queries working

- [ ] **Observability**
  - [ ] Prometheus plugin enabled globally
  - [ ] Metrics endpoint responding: `curl http://localhost:9091/apisix/prometheus/metrics`
  - [ ] Prometheus container deployed (optional)
  - [ ] Grafana container deployed (optional)

- [ ] **Testing complete**
  - [ ] Metered inference request successful
  - [ ] Rate limiting enforced (429 on excess)
  - [ ] Unauthorized access rejected (401)
  - [ ] Metering headers present in responses

---

## Phase 7: Verification and Testing

### End-to-End Smoke Tests

- [ ] **Test 1: Local inference via OpenClaw**
  ```
  curl http://localhost:18789/api/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{"model": "default", "messages": [{"role": "user", "content": "Hello"}]}'
  ```
  - [ ] Response received from DGX model

- [ ] **Test 2: Cloud fallback**
  - [ ] Stop a DGX model temporarily
  - [ ] Repeat Test 1
  - [ ] Verify response comes from OpenRouter (check X-Route header)
  - [ ] Restart DGX model

- [ ] **Test 3: Agent task delegation**
  ```
  curl -X POST http://localhost:9090/tasks \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $WEBHOOK_SECRET" \
    -d '{"taskId": "verify_001", "prompt": "Write hello world in Python", "callbackUrl": "http://localhost:18789/api/v1/tasks/callback"}'
  ```
  - [ ] Task accepted (202)
  - [ ] Task completed callback received

- [ ] **Test 4: Metered third-party access**
  ```
  curl -X POST http://localhost:9080/v1/chat/completions \
    -H "X-API-Key: <consumer-key>" \
    -H "Content-Type: application/json" \
    -d '{"model": "deepseek-r1", "messages": [{"role": "user", "content": "Hello"}]}'
  ```
  - [ ] Response received with metering headers
  - [ ] Token count recorded

- [ ] **Test 5: Cross-machine Tailscale access**
  - [ ] From external device on Tailscale: access OpenClaw at 100.79.80.119:18789
  - [ ] From external device on Tailscale: access OpenHands at 100.79.80.119:3000
  - [ ] From external device on Tailscale: access APISIX at 100.79.80.119:9080

### Security Verification

- [ ] Firewall active on Minisforum: `sudo ufw status`
- [ ] fail2ban active: `sudo fail2ban-client status sshd`
- [ ] No unnecessary ports exposed: `sudo ss -tlnp`
- [ ] API keys are unique and securely stored
- [ ] No default passwords remain on DGX Spark
- [ ] APISIX admin key changed from default
- [ ] Webhook secrets are random and not hardcoded

### Resource Health

- [ ] Minisforum RAM usage < 70%: `free -h`
- [ ] DGX Spark GPU memory healthy: `nvidia-smi`
- [ ] Disk usage < 75% on both machines: `df -h`
- [ ] All critical services auto-start on reboot:
  - [ ] `sudo systemctl is-enabled openclaw`
  - [ ] `sudo systemctl is-enabled docker`
  - [ ] `sudo systemctl is-enabled ssh`
  - [ ] `sudo systemctl is-enabled fail2ban`
  - [ ] `sudo systemctl is-enabled ufw`
  - [ ] (DGX) `sudo systemctl is-enabled ollama`

---

## Quick Reference Card

Once everything is set up, this is your quick reference:

```
MINISFORUM (Control Plane): 192.168.1.157 / 100.79.80.119
  SSH:      ssh newwaveclaw@192.168.1.157
  OpenClaw: http://192.168.1.157:18789
  OpenHands: http://192.168.1.157:3000
  OpenCode: http://192.168.1.157:3002
  APISIX:   http://192.168.1.157:9080
  Prometheus: http://192.168.1.157:9090
  Grafana:  http://192.168.1.157:3003

DGX SPARK (Compute Engine): 192.168.1.158 / <Tailscale IP>
  SSH:      ssh <user>@192.168.1.158
  NemoClaw: http://192.168.1.158:8080
  GLM-5:    http://192.168.1.158:8001
  DeepSeek: http://192.168.1.158:8002
  Ollama:   http://192.168.1.158:11434

Key Commands:
  openclaw status              -- Check OpenClaw health
  openclaw backends list       -- List compute backends
  /acp status                  -- Check ACP agents
  nvidia-nemoclaw cluster status -- Check DGX cluster
  nvidia-nemoclaw model list   -- List deployed models
  docker stats                 -- Container resource usage
  sudo ufw status              -- Firewall rules
  tailscale status             -- VPN connectivity
```

---

## Notes and Customizations

Use this space to record any deviations, custom settings, or issues encountered:

```
Date: ___________
DGX Spark username: ___________
DGX Spark Tailscale IP: ___________
APISIX admin key stored at: ___________
OpenRouter daily budget: $___________

Notes:
_____________________________________________
_____________________________________________
_____________________________________________
_____________________________________________
_____________________________________________
```
