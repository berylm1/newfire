#!/usr/bin/env python3
"""NewFire CEO readiness static inventory helper.

Read-only scanner for the governed CEO-agent workflow. It intentionally avoids
network scans, production load tests, deploys, migrations, restarts, and secret
reads. It summarizes tracked source files so follow-up audits can be evidence-
based and repeatable.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {'.git', 'node_modules', '.next', 'dist', 'build', '.cache', '.turbo', 'coverage', '__pycache__', '.venv', 'venv'}
CODE_EXTS = {'.js', '.py', '.sql', '.sh', '.yml', '.yaml', '.json', '.md'}
ROUTE_RX = re.compile(r"\b(?:app|router)\.(get|post|put|patch|delete|use)\s*\(\s*['\"]([^'\"]+)")
ENV_RX = re.compile(r'process\.env\.([A-Z0-9_]+)')


def skip(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)


def line_counts() -> dict[str, dict[str, int]]:
    counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for path in ROOT.rglob('*'):
        if not path.is_file() or skip(path):
            continue
        ext = path.suffix.lower() or path.name.lower()
        if ext not in CODE_EXTS:
            continue
        lines = path.read_text(errors='ignore').splitlines()
        counts[ext][0] += 1
        counts[ext][1] += len(lines)
    return {k: {'files': v[0], 'lines': v[1]} for k, v in sorted(counts.items(), key=lambda kv: -kv[1][1])}


def backend_routes() -> list[dict[str, str]]:
    routes = []
    for path in sorted((ROOT / 'newfire-backend' / 'src').glob('*.js')):
        text = path.read_text(errors='ignore')
        for match in ROUTE_RX.finditer(text):
            routes.append({'file': str(path.relative_to(ROOT)), 'method': match.group(1).upper(), 'path': match.group(2)})
    return routes


def backend_env() -> dict[str, list[str]]:
    envs: dict[str, set[str]] = defaultdict(set)
    for path in (ROOT / 'newfire-backend').rglob('*'):
        if not path.is_file() or skip(path):
            continue
        text = path.read_text(errors='ignore')
        for match in ENV_RX.finditer(text):
            envs[match.group(1)].add(str(path.relative_to(ROOT)))
    return {k: sorted(v) for k, v in sorted(envs.items())}


def service_inventory() -> list[dict[str, object]]:
    services = [
        {
            'service': 'newfire-backend',
            'path': 'newfire-backend/',
            'runtime': 'Node.js / Express / Postgres',
            'entrypoints': ['src/server.js', 'src/auth.js', 'src/orchestrator.js', 'src/tenant.js'],
            'health': 'GET /health',
            'deployment': 'newfire_backend_docker/docker-compose.yml -> newfire-backend container :3200',
            'risk': 'High: auth, tenancy, billing, webhooks, model routing, agent task delegation',
        },
        {
            'service': 'openclaw',
            'path': 'openclaw/',
            'runtime': 'Python / FastAPI / Postgres',
            'entrypoints': ['app/main.py', 'app/auth.py', 'app/classifier.py', 'app/routes/'],
            'health': 'GET /v1/health',
            'deployment': 'openclaw/docker-compose.yml; Cloudflare Access gated public URL',
            'risk': 'High: developer-agent routing and execution surface',
        },
        {
            'service': 'newfire_backend_docker',
            'path': 'newfire_backend_docker/',
            'runtime': 'Docker Compose deployment artifact',
            'entrypoints': ['docker-compose.yml', 'Dockerfile'],
            'health': 'container health via backend /health',
            'deployment': 'Minisforum america worker',
            'risk': 'Medium: production configuration and runtime secret boundaries',
        },
        {
            'service': 'infra',
            'path': 'infra/',
            'runtime': 'Cloudflare/codeep/dev-hub deployment docs/artifacts',
            'entrypoints': ['infra/README.md'],
            'health': 'manual/operator checks',
            'deployment': 'Cloudflare and homelab infrastructure',
            'risk': 'Medium: ingress and operator control-plane assumptions',
        },
    ]
    return services


def main() -> None:
    data = {
        'services': service_inventory(),
        'line_counts': line_counts(),
        'backend_routes': backend_routes(),
        'backend_env': backend_env(),
    }
    print(json.dumps(data, indent=2))


if __name__ == '__main__':
    main()
