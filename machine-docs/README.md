# Machine Documentation Index

This folder contains clean, takeover-ready documentation for every machine in the
NewFire network. Each file describes what is installed, what is running, how it is
accessed, and what a new operator needs to know to take over.

| Machine | Role | Docs |
| --- | --- | --- |
| `newwaveclaw` | Primary control / orchestration node (x86_64, Ubuntu 24.04) | [newwaveclaw.md](newwaveclaw.md) |
| `spark-a439` (DGX Spark) | GPU inference node (NVIDIA GB10, aarch64, Ubuntu 24.04) | [dgx-spark.md](dgx-spark.md) |

### Cross-cutting reference

| Topic | Docs |
| --- | --- |
| Cloudflare tunnel, Tailscale, Docker, AI agents, all projects, router/LAN | [infrastructure.md](infrastructure.md) |

## How to use these docs

- These files are **living documentation**. Update them whenever a service is
  added, removed, or its access path changes.
- Secrets are **never** stored here. See each machine's *Secrets & Security*
  section for what to provision before taking over.
- All machines are joined to the same Tailscale network
  (`tail3a833f.ts.net`). Hostnames and Tailscale IPs are listed per machine.

## Network map (Tailscale)

| Tailscale IP | Hostname | OS | Notes |
| --- | --- | --- | --- |
| `100.79.80.119` | `america` (newwaveclaw) | Linux | Primary node, tagged `tagged-devices` |
| `100.88.112.5` | `ghana` (spark-a439 / DGX Spark) | Linux | GPU inference node |
| `100.120.107.95` | `berylpi5-newfire` | Linux | Raspberry Pi 5 edge device |
| `100.107.229.67` | `beryls-macbook-air` | macOS | Operator laptop |

## Conventions

- Ports shown are what was observed at documentation time. Firewall / Cloudflare
  Tunnel fronting may change the public exposure.
- "Restarting" in `docker ps` means the container's restart policy is looping —
  treat as a broken service and check logs.
