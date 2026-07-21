#!/usr/bin/env python3
"""
Admin script: fully onboard a new developer in one command.

This replaces the manual process of:
  1. SSHing into each server to create a restricted account
  2. Hand-editing the ACL JSON to grant access

Run this once per new developer:
  python3 onboard-developer.py <email> <short-username>

Example:
  python3 onboard-developer.py newperson@gmail.com jane
    -> creates 'dev-jane' on america and ghana (no sudo, in 'devteam' group)
    -> adds an ACL rule so newperson@gmail.com can SSH in as dev-jane

What this does NOT do (Tailscale has no public API for it):
  Send the initial tailnet invite. You still do that once, manually:
    Admin console -> Settings -> Users -> Invite users
  Everything after that point — account creation, permissions, SSH access —
  is handled by this script.

Requirements:
  - Run this from a machine that already has working admin SSH access
    to both servers via Tailscale (i.e. you can already run
    `ssh newwaveclaw@100.79.80.119` without issues).
  - Environment variables set:
      TAILSCALE_API_KEY   (API token with ACL read/write scope —
                            generate at https://login.tailscale.com/admin/settings/keys)
      TAILSCALE_TAILNET   (your tailnet name, shown in the admin console URL)

Security note:
  This script can create accounts on your servers and modify network
  access policy. Keep it and your API key somewhere only you can run it
  from — don't share the API key.
"""

import os
import re
import sys
import json
import subprocess
import urllib.request
import urllib.error

SERVERS = [
    {"host": "100.79.80.119", "admin_user": "newwaveclaw", "label": "america"},
    {"host": "100.88.112.5",  "admin_user": "newwave-dgx", "label": "ghana"},
]

API_KEY = os.environ.get("TAILSCALE_API_KEY")
TAILNET = os.environ.get("TAILSCALE_TAILNET")


def fail(msg):
    print(f"Error: {msg}")
    sys.exit(1)


def run_remote(host, admin_user, command):
    """Run a command on a remote server over Tailscale SSH (no keys needed)."""
    target = f"{admin_user}@{host}"
    return subprocess.run(
        ["ssh", "-o", "ConnectTimeout=10", target, command],
        capture_output=True, text=True
    )


def create_user_on_server(server, username):
    host, admin_user, label = server["host"], server["admin_user"], server["label"]

    print(f"[{label}] Checking if '{username}' already exists...")
    check = run_remote(host, admin_user, f"id {username}")
    if check.returncode == 0:
        print(f"[{label}] '{username}' already exists — skipping creation.")
        return

    print(f"[{label}] Creating '{username}' (no sudo, group: devteam)...")
    cmd = (
        "sudo groupadd -f devteam && "
        f"sudo adduser --disabled-password --gecos '' {username} && "
        f"sudo usermod -aG devteam {username}"
    )
    result = run_remote(host, admin_user, cmd)
    if result.returncode != 0:
        fail(f"[{label}] Failed to create user:\n{result.stderr.strip()}")

    print(f"[{label}] '{username}' created.")


def api_request(url, method, data=None):
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, method=method, data=body)
    req.add_header("Authorization", f"Bearer {API_KEY}")
    req.add_header("Accept", "application/json")
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        fail(f"Tailscale API returned {e.code}: {e.read().decode('utf-8')}")


def update_acl(email, username):
    if not API_KEY or not TAILNET:
        fail("Missing TAILSCALE_API_KEY or TAILSCALE_TAILNET environment variables.")

    url = f"https://api.tailscale.com/api/v2/tailnet/{TAILNET}/acl"

    print("Fetching current ACL...")
    acl = api_request(url, "GET")

    # If this person was previously on a shared group (e.g. group:team for
    # a shared 'dev' account), remove them — they now have their own
    # individual rule below instead.
    for group_name, members in acl.get("groups", {}).items():
        if email in members:
            members.remove(email)
            print(f"Removed {email} from {group_name} (replaced by individual access).")

    ssh_rules = acl.setdefault("ssh", [])
    existing = next((r for r in ssh_rules if r.get("src") == [email]), None)

    if existing:
        print(f"Existing SSH rule found for {email} — updating it.")
        if username not in existing.get("users", []):
            existing.setdefault("users", []).append(username)
    else:
        print(f"Adding new SSH rule: {email} -> {username}")
        ssh_rules.append({
            "action": "accept",
            "src": [email],
            "dst": ["tag:server"],
            "users": [username],
        })

    api_request(url, "POST", acl)
    print("ACL updated.")


def main():
    if len(sys.argv) != 3:
        fail("Usage: python3 onboard-developer.py <email> <short-username>")

    email = sys.argv[1].strip()
    short_name = sys.argv[2].strip().lower()

    if not re.match(r"^[a-z0-9_-]+$", short_name):
        fail("Username must be lowercase letters, numbers, hyphens, or underscores only.")

    username = f"dev-{short_name}"

    print("=" * 50)
    print(f" Onboarding: {email}  ->  {username}")
    print("=" * 50)

    for server in SERVERS:
        create_user_on_server(server, username)

    update_acl(email, username)

    print("")
    print("=" * 50)
    print(" Done")
    print("=" * 50)
    print(f"{email} can SSH in as '{username}' once they:")
    print("  1. Accept a tailnet invite (still manual — Admin console ->")
    print("     Settings -> Users -> Invite users)")
    print("  2. Install Tailscale and log in")
    print("")
    print("Tell them to connect with:")
    for server in SERVERS:
        print(f"  ssh {username}@{server['host']}   # {server['label']}")
    print("")
    print(f"Or have them run the dev-onboard script with their username:")
    print(f"  ./dev-onboard.sh {username}")


if __name__ == "__main__":
    main()
