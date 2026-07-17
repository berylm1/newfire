#!/usr/bin/env python3
"""
Migrate content out of the legacy 'Network STARTUP' note.

1. Create architecture notes in NewFire / 02 Architecture for the reusable parts:
   - Subdomain status + security check
   - Tailnet topology
   - Prometheus + Grafana monitoring
2. Create an URGENT cred rotation playbook in NewFire / 03 Active Projects.
3. Move 'Network STARTUP' from iCloud root into NewFire / 00 Inbox so it stops
   sitting in the top of Notes. Do not delete; user verifies before deletion.
"""

import subprocess
import sys

ACCOUNT = "Personal"
PARENT = "NewFire"

NOTES = [
    # ---------- 02 Architecture (extracted from Network STARTUP) ----------
    ("02 Architecture", "newfire.app Subdomain Status and Security",
     """<div>Extracted from the legacy Network STARTUP note (terminal screenshot of dev-dashboard-demo-prep).</div>
<br>
<div><b>Subdomain status</b></div>
<ul>
<li><b>newfire.app</b> 200 (with auth) Main site + app</li>
<li><b>app.newfire.app</b> 200 (with auth) Client portal</li>
<li><b>dev.newfire.app</b> 200 (with auth) Developer portal (NSS UI)</li>
<li><b>api.newfire.app</b> 404 APISIX, needs route</li>
<li><b>files.newfire.app</b> 207 WebDAV working</li>
<li><b>dash.newfire.app</b> Waiting Paperclip AI not installed yet</li>
</ul>
<br>
<div><b>Security posture</b></div>
<ul>
<li>All traffic encrypted with Cloudflare TLS</li>
<li>Basic auth gate blocks unauthorized access</li>
<li>Cloudflare provides DDoS protection automatically</li>
<li>No ports opened on router; cloudflared tunnel is outbound-only</li>
<li>Survives reboots (systemd service enabled)</li>
</ul>
<br>
<div><b>Open route work</b></div>
<ul>
<li>api.newfire.app needs an APISIX route mapping before it returns 200</li>
<li>dash.newfire.app waits on Paperclip AI install</li>
</ul>"""),

    ("02 Architecture", "Tailnet Topology",
     """<div>Tailscale mesh between the two homelab machines and admin laptop. Extracted from Network STARTUP.</div>
<br>
<div><b>Core homelab nodes</b></div>
<ul>
<li><b>america</b> (Minisforum X1 Pro 370 control plane) Tailscale IP 100.79.80.119, SSH user newwaveclaw</li>
<li><b>ghana</b> (NVIDIA DGX Spark compute) Tailscale IP 100.88.112.5, SSH user newwave-dgx</li>
</ul>
<br>
<div><b>Other ts.net devices observed</b></div>
<ul>
<li>console-ql-inet (GL-iNet router, Nigeria edge)</li>
<li>basement-ultra (laptop / workstation)</li>
<li>newwaveclaw (admin Mac primary identity)</li>
<li>gem-room, sapri-am30 (Mac devices on tailnet)</li>
<li>opencode tunnel (transient, from OpenCode container)</li>
</ul>
<br>
<div><b>LAN side</b></div>
<div>192.168.1.x subnet behind the GL-X3000 router (called nigeria in early docs).</div>
<br>
<div><b>Access pattern</b></div>
<ul>
<li>From Mac: ssh newwaveclaw@america (Tailscale routes the name)</li>
<li>From Mac: ssh newwave-dgx@ghana</li>
<li>Public ingress: only via Cloudflare tunnel, never direct port forward</li>
</ul>"""),

    ("02 Architecture", "Prometheus + Grafana Monitoring",
     """<div>Monitoring layer on Minisforum, scraping both machines. Extracted from Network STARTUP.</div>
<br>
<div><b>prometheus.yml scrape targets</b></div>
<ul>
<li>host.docker.internal:9100 (Minisforum node-exporter, label machine=minisforum)</li>
<li>minisforum cAdvisor (label machine=minisforum)</li>
<li>100.88.112.5:9100 (DGX Spark node-exporter, label machine=dgx-spark)</li>
<li>localhost:9090 inside DGX Spark cAdvisor container (label machine=dgx-spark)</li>
</ul>
<br>
<div><b>Web UIs (Tailscale-only, not public)</b></div>
<ul>
<li>Prometheus: http://100.79.80.119:9090</li>
<li>Grafana: http://100.79.80.119:3003</li>
</ul>
<br>
<div><b>Reload after config change</b></div>
<div>From Mac: <code>scp ~/Desktop/prometheus/prometheus.yml newwaveclaw@america:/home/lab2026/</code> then <code>ssh newwaveclaw@100.79.80.119 "docker restart prometheus"</code></div>
<br>
<div><b>Open items</b></div>
<ul>
<li>Grafana admin password was in the legacy note plaintext; rotate per the Credential Rotation playbook before treating Grafana as trusted.</li>
<li>No ROI dashboard panel yet (Gap Map item).</li>
<li>Log rotation and resource limits still flagged as a hardening task.</li>
</ul>"""),

    # ---------- 03 Active Projects (urgent playbook) ----------
    ("03 Active Projects", "Credential Rotation (URGENT)",
     """<div><b>Status:</b> IN PROGRESS</div>
<div><b>Why now:</b> the legacy "Network STARTUP" note carried plaintext production credentials in iCloud. Treat every credential in that note as compromised baseline until rotated. iCloud-synced plaintext does not meet your security-first rule.</div>
<br>
<div><b>Definition of done</b></div>
<ul>
<li>Every credential listed below rotated and verified</li>
<li>New values stored in Apple Keychain (or 1Password), never in Notes</li>
<li>Network STARTUP note sanitized (credential block deleted) or the whole note deleted</li>
<li>This note moved to 05 Decisions with status DONE and a short post-mortem</li>
</ul>
<br>
<div><b>What to rotate (in priority order)</b></div>
<ol>
<li><b>APISIX admin key.</b> On america: edit /usr/local/apisix/conf/config.yaml, replace admin_key value, restart apisix. Update OpenClaw and any consumer that uses APISIX_KEY env var. Verify with: <code>curl -H "X-API-KEY: NEW_KEY" http://127.0.0.1:9180/apisix/admin/routes</code></li>
<li><b>OpenRouter API key.</b> Log in at openrouter.ai, revoke the exposed key, create a new one. Update on america wherever OPENROUTER_API_KEY is set (OpenClaw config, any container env). Restart affected services.</li>
<li><b>Grafana admin password.</b> http://100.79.80.119:3003, change admin password in user settings.</li>
<li><b>Minisforum system password.</b> ssh newwaveclaw@america, run <code>passwd</code>. Confirm SSH still works from a new terminal before closing the old one.</li>
<li><b>DGX Spark system password.</b> ssh newwave-dgx@ghana, run <code>passwd</code>. Same SSH confirmation step.</li>
<li><b>Microsoft (Outlook) account.</b> Change password, enable 2FA if not already on.</li>
<li><b>Cloudflare account.</b> Change password, enable 2FA, audit API tokens, revoke any unused.</li>
</ol>
<br>
<div><b>Where to store new credentials</b></div>
<ul>
<li>Default: Apple Keychain (Keychain Access app, File &gt; New Password Item, store as "newfire.<i>service</i>" so search finds them)</li>
<li>Or 1Password if you adopt a manager</li>
<li>On-host .env files: chmod 600, owned by the service user only</li>
<li>NEVER in Apple Notes again, even temporarily</li>
</ul>
<br>
<div><b>Verification steps before marking each item done</b></div>
<ul>
<li>SSH from a fresh terminal after each password change</li>
<li>APISIX admin call with the new key returns 200</li>
<li>OpenRouter API call with the new key returns 200 (try a cheap chat completion)</li>
<li>Grafana login works with new password from a private window</li>
</ul>
<br>
<div><b>Post-mortem (fill in when done)</b></div>
<ul>
<li>How long the creds were exposed in iCloud (note creation date to rotation date)</li>
<li>Devices signed into that iCloud (other surfaces that might have cached the plaintext)</li>
<li>What we will not do again (decision to enshrine in 05 Decisions)</li>
</ul>"""),
]


def osa(script: str):
    return subprocess.run(["osascript", "-e", script], capture_output=True, text=True)


def esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def ensure_note(folder: str, title: str, body_html: str):
    full_body = f"<h1>{title}</h1>\n{body_html}"
    body_esc = esc(full_body)
    title_esc = esc(title)
    script = f'''
    tell application "Notes"
        tell account "{ACCOUNT}"
            tell folder "{PARENT}"
                tell folder "{folder}"
                    if not (exists note named "{title_esc}") then
                        make new note with properties {{name:"{title_esc}", body:"{body_esc}"}}
                    end if
                end tell
            end tell
        end tell
    end tell
    '''
    return osa(script)


def move_legacy_note():
    """Move 'Network STARTUP' from account root into NewFire/00 Inbox."""
    script = f'''
    tell application "Notes"
        tell account "{ACCOUNT}"
            set targetFolder to folder "00 Inbox" of folder "{PARENT}"
            set legacyNote to first note whose name is "Network STARTUP"
            move legacyNote to targetFolder
        end tell
    end tell
    '''
    return osa(script)


def main():
    print("Migrating Network STARTUP content into NewFire tree.")
    print()

    for folder, title, body in NOTES:
        r = ensure_note(folder, title, body)
        if r.returncode != 0:
            print(f"FAIL note {folder} / {title}: {r.stderr}", file=sys.stderr)
            continue
        print(f"[ok] note: {folder} / {title}")

    print()
    print("Moving 'Network STARTUP' into NewFire / 00 Inbox.")
    r = move_legacy_note()
    if r.returncode != 0:
        print(f"FAIL move: {r.stderr}", file=sys.stderr)
        sys.exit(1)
    print("[ok] move complete")
    print()
    print("Done. Open the Credential Rotation note in 03 Active Projects to execute.")


if __name__ == "__main__":
    main()
