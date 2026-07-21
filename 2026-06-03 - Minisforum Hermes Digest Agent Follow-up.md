# 2026-06-03 - Minisforum Hermes Digest Agent Follow-up

## Context
Today we worked on the NewFire Minisforum production-worker nightly review flow.

## What worked today
- The NewFire nightly read-only review script generated reports under `~/newfire-agent/reports/` on the Minisforum.
- The OpenClaw Compose check failure was fixed by creating a local `openclaw/.env-secrets` from `.env-secrets.example`.
- The newest report showed all three Compose syntax checks as OK: backend, OpenClaw, and n8n.

## What blocked us
- Direct email sending through `newwaveclaw@outlook.com` via `msmtp` failed because Microsoft returned: `SmtpClientAuthentication is disabled for the Mailbox`.
- Raspberry Pi/Hermes could not SSH to the Minisforum because the Pi is on the personal Tailscale tailnet (`chisoba.9090@`) while the Minisforum/NewFire machine is under the `newwaveclaw@outlook.com` Tailscale network.

## Later-today implementation target
At 6pm, resume work on creating a dedicated NewFire digest agent:

1. Give the Raspberry Pi/Hermes access to the Minisforum over Tailscale/SSH.
2. Install or finish configuring Hermes on the Minisforum.
3. Create a `newfire-digest` workflow that reads the latest nightly report and produces a concise executive digest.
4. Schedule the digest with systemd or Hermes cron.
5. Start with local/Telegram delivery first; add email delivery later once the sender path is resolved.
6. For email, prefer sending only to `newwaveclaw@outlook.com`, then use an Outlook rule to forward digest emails to `pmunis@gmail.com` if needed.

## Pi access details captured
- Pi hostname: `berylpi5`
- Pi user: `beryl`
- Pi Tailscale IP on personal tailnet: `100.83.157.78`
- Pi SSH public key for Minisforum access: `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIGAdXwGW8JzjcXa9Rv5SpD3Z1bJVejQRCOjOUxUw79LE hermes-pi-to-newfire-minisforum`
