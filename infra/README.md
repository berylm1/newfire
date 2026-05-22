# infra/

Deployment artifacts for services that run on america (Minisforum control plane).

Edit files here on the Mac. SCP to america to apply. Never paste multi-line content over SSH.

## Layout

- **codeep/**: Codeep TUI coding agent, exposed at `codeep.newfire.app` via ttyd + cloudflared.
- **dev-hub/**: Static landing page at `dev.newfire.app` that links to every developer tool.
- **cloudflared/**: Snapshot of `/etc/cloudflared/config.yml` from america. Authoritative copy lives on the host, so this directory is the tracked mirror.

## Deploying

Each service dir contains a `run.sh` script. The general pattern is:

```bash
# from this Mac, in the service dir
scp Dockerfile run.sh nginx.conf newwaveclaw@100.79.80.119:/home/newwaveclaw/<service>-build/
ssh newwaveclaw@100.79.80.119 'cd <service>-build && ./run.sh'
```

When editing the cloudflared config, do **not** push directly. Pull the live config, edit, validate, install, restart:

```bash
ssh newwaveclaw@100.79.80.119 'sudo cat /etc/cloudflared/config.yml' > config.yml
# edit config.yml
scp config.yml newwaveclaw@100.79.80.119:/tmp/cf-new.yml
ssh newwaveclaw@100.79.80.119 '
  sudo cp /etc/cloudflared/config.yml /etc/cloudflared/config.yml.bak.$(date +%Y%m%d-%H%M%S) &&
  sudo install -m 644 -o root -g root /tmp/cf-new.yml /etc/cloudflared/config.yml &&
  sudo systemctl restart cloudflared
'
```

## Security gates per surface

| URL | Gate |
|---|---|
| dev.newfire.app | None at edge (hub is public; destinations are individually gated) |
| codeep.newfire.app | Cloudflare Access (One-time PIN) |
| opencode.newfire.app | Cloudflare Access |
| openhands.newfire.app | Cloudflare Access |
| workspace.newfire.app | Filebrowser app login only; CF Access not yet configured (open follow-up) |
| api.newfire.app | APISIX per-consumer key |
