# 2026-06-03 - MacBook SSH Recovery Before OpenHands Push

Status: active blocker
Related: [[2026-06-03 - Tonight OpenHands Agent Push Plan]]

## Problem

Beryl reports SSH from MacBook to the NewFire Minisforum is not working. Since Pi/Hermes also times out to `newwaveclaw@100.79.80.119`, tonight's first task is to restore a reliable control path to the Minisforum before pushing the OpenHands agent route.

## Working hypothesis

Most likely causes, in order:

1. MacBook is not on the NewFire Tailscale tailnet where the Minisforum lives.
2. The Minisforum Tailscale IP changed or the machine is offline/asleep.
3. SSH service is stopped or blocked on the Minisforum.
4. Username/key mismatch.
5. Tailscale ACL/firewall prevents SSH even though the node is visible.

## MacBook diagnostic block

Run on MacBook Terminal:

```bash
whoami
hostname

# Is Tailscale installed and connected?
tailscale status

# What Tailscale IP does the MacBook have?
tailscale ip -4

# Can the MacBook reach the Minisforum Tailscale IP at all?
ping -c 3 100.79.80.119

# Is SSH port 22 reachable?
nc -vz 100.79.80.119 22

# Try SSH with verbose diagnostics
ssh -vvv -o ConnectTimeout=10 newwaveclaw@100.79.80.119
```

## Interpret results

- `tailscale status` does not show Minisforum/newwaveclaw machine: MacBook is on the wrong tailnet or not accepted into the NewFire tailnet.
- `ping` fails and `nc` times out: Tailscale route/tailnet/offline issue.
- `ping` works but `nc` fails: SSH service/firewall issue on Minisforum.
- `nc` works but `ssh` says permission denied: key/password/user auth issue.
- `ssh` says host key changed: verify host identity before accepting.

## If MacBook is on the wrong Tailscale account/tailnet

Open Tailscale on MacBook and check the signed-in account. NewFire Minisforum is under the NewFire tailnet/account, not the personal `chisoba.9090` tailnet.

Fix options:

1. Switch MacBook Tailscale account to the NewFire tailnet.
2. Invite the MacBook account/device into the NewFire tailnet.
3. Temporarily use another already-connected NewFire machine as the control host.

## If Minisforum is visible but SSH is blocked

On physical Minisforum or any working remote path, run:

```bash
hostname
whoami
ip addr | grep -A2 tailscale || true
sudo systemctl status ssh --no-pager
sudo systemctl enable --now ssh
sudo ufw status verbose
sudo ss -tlnp | grep ':22'
tailscale status
```

If Ubuntu SSH server is missing:

```bash
sudo apt update
sudo apt install -y openssh-server
sudo systemctl enable --now ssh
```

## If using Tailscale SSH instead of normal SSH

Try from MacBook:

```bash
tailscale ssh newwaveclaw@100.79.80.119
```

If this works, use it tonight and fix normal SSH later.

## Pi connection helper created

Hermes created a helper script on the Pi:

```bash
/home/beryl/.hermes/scripts/connect_newfire_tailnet.sh
```

Run it from the Pi terminal when physical/sudo access is available:

```bash
bash /home/beryl/.hermes/scripts/connect_newfire_tailnet.sh
```

The script:

1. Asks for the Pi sudo password locally.
2. Runs `sudo tailscale set --operator="$USER"` so Hermes can manage Tailscale afterward without handling the password.
3. Starts `tailscale login --nickname newfire --hostname berylpi5-newfire`.
4. Checks whether `newwaveclaw@100.79.80.119` is reachable by SSH.

## Tonight fallback if SSH cannot be restored quickly

If SSH is still blocked after 20–30 minutes:

1. Use GitHub web UI to create labels: `agent-ready`, `ceo-priority`, `needs-human`, `review-this`.
2. Use GitHub web UI to create the smoke-test issue.
3. Postpone Minisforum OpenHands execution until access is restored.
4. CEO update should say: access path to production worker is the blocker, not the agent design.

## Message to send back to Hermes

Paste the output of:

```bash
tailscale status
ping -c 3 100.79.80.119
nc -vz 100.79.80.119 22
ssh -vvv -o ConnectTimeout=10 newwaveclaw@100.79.80.119
```

Do not paste private keys or tokens.
