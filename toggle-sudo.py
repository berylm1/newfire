#!/usr/bin/env python3
"""
Admin script: toggle passwordless sudo for one developer account.

This is the per-person on/off switch — no manual visudo editing needed
each time someone's use case changes.

Usage:
  python3 toggle-sudo.py <username> on
  python3 toggle-sudo.py <username> off

Example:
  python3 toggle-sudo.py dev-ludun on
    -> grants dev-ludun full passwordless sudo on both servers

  python3 toggle-sudo.py dev-ludun off
    -> revokes it again

What "on" means:
  Functionally root-equivalent access for that account on both servers —
  no password, no command restrictions. Treat it the same as handing
  someone the root password.

Requirements:
  - Run from a machine with working admin SSH access to both servers.
"""

import sys
import subprocess

SERVERS = [
    {"host": "100.79.80.119", "admin_user": "newwaveclaw", "label": "america"},
    {"host": "100.88.112.5",  "admin_user": "newwave-dgx", "label": "ghana"},
]


def fail(msg):
    print(f"Error: {msg}")
    sys.exit(1)


def run_remote(host, admin_user, command):
    target = f"{admin_user}@{host}"
    return subprocess.run(
        ["ssh", "-o", "ConnectTimeout=10", target, command],
        capture_output=True, text=True
    )


def enable_sudo(server, username):
    host, admin_user, label = server["host"], server["admin_user"], server["label"]
    sudoers_file = f"/etc/sudoers.d/{username}-full"
    line = f"{username} ALL=(ALL) NOPASSWD: ALL"

    # Write to a temp file first and validate with visudo -c before
    # installing it — a bad sudoers file can otherwise break sudo entirely.
    cmd = (
        f"echo '{line}' | sudo tee {sudoers_file}.tmp > /dev/null && "
        f"sudo chmod 0440 {sudoers_file}.tmp && "
        f"sudo visudo -c -f {sudoers_file}.tmp && "
        f"sudo mv {sudoers_file}.tmp {sudoers_file}"
    )
    result = run_remote(host, admin_user, cmd)
    if result.returncode != 0:
        fail(f"[{label}] Failed to enable sudo for {username}:\n{result.stderr.strip()}")
    print(f"[{label}] Passwordless sudo ENABLED for {username}.")


def disable_sudo(server, username):
    host, admin_user, label = server["host"], server["admin_user"], server["label"]
    sudoers_file = f"/etc/sudoers.d/{username}-full"

    result = run_remote(host, admin_user, f"sudo rm -f {sudoers_file}")
    if result.returncode != 0:
        fail(f"[{label}] Failed to disable sudo for {username}:\n{result.stderr.strip()}")
    print(f"[{label}] Passwordless sudo DISABLED for {username}.")


def main():
    if len(sys.argv) != 3 or sys.argv[2] not in ("on", "off"):
        fail("Usage: python3 toggle-sudo.py <username> on|off")

    username = sys.argv[1].strip()
    state = sys.argv[2].strip()

    print("=" * 50)
    print(f" {'Enabling' if state == 'on' else 'Disabling'} passwordless sudo: {username}")
    print("=" * 50)

    for server in SERVERS:
        if state == "on":
            enable_sudo(server, username)
        else:
            disable_sudo(server, username)

    print("")
    print("Done.")
    if state == "on":
        print(f"{username} now has unrestricted passwordless sudo on both servers.")
        print(f"Revoke any time with:  python3 toggle-sudo.py {username} off")


if __name__ == "__main__":
    main()
