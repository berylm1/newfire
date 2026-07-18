# Context Management Vault

This Obsidian vault stores all project context, infrastructure docs, and service documentation to avoid context compression in AI sessions.

## Structure

```
obsidian-vault/
├── 00-Inbox/          # Quick notes, ideas, pending items
├── 01-Projects/       # Project-specific documentation
├── 02-Infrastructure/ # Server, network, Docker docs
├── 03-Monitoring/     # Grafana, Prometheus, Loki configs
├── 04-Services/       # Service-specific documentation
├── 05-Templates/      # Note templates
└── .obsidian/         # Obsidian settings
```

## Quick Links

- [[Project-Status]] - Current state of all services
- [[Infrastructure-Overview]] - Server architecture
- [[Docker-Setup]] - Container orchestration details
- [[Monitoring-Stack]] - Observability setup
- [[Alerts-Configuration]] - Alert rules and notifications

## Usage

When starting a new AI session, reference this vault for:
1. Current service status
2. Network topology
3. Configuration files
4. Troubleshooting history
5. Architecture decisions

This prevents context compression and maintains continuity across sessions.
