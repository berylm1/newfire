#!/usr/bin/env python3
"""Verify MCP SSE server by completing handshake and listing tools.

Usage: python3 mcp_verify.py [base_url] [api_key]
"""
import sys
import json
import re
import time
import threading
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://100.88.112.5:7333"
KEY = sys.argv[2] if len(sys.argv) > 2 else ""

session_id = None
stop = threading.Event()
inbox = []


def sse_reader():
    """Long-lived SSE listener. Captures session_id and any tool responses."""
    global session_id
    req = urllib.request.Request(f"{BASE}/sse", headers={"Authorization": f"Bearer {KEY}"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        event_type = None
        for raw in resp:
            if stop.is_set():
                return
            line = raw.decode(errors="replace").rstrip("\n")
            if not line:
                event_type = None
                continue
            if line.startswith("event:"):
                event_type = line[6:].strip()
            elif line.startswith("data:"):
                payload = line[5:].strip()
                if event_type == "endpoint":
                    m = re.search(r"session_id=([a-f0-9]+)", payload)
                    if m:
                        session_id = m.group(1)
                elif event_type == "message":
                    try:
                        inbox.append(json.loads(payload))
                    except Exception:
                        pass


def post(method, params=None, _id=1):
    body = {"jsonrpc": "2.0", "id": _id, "method": method}
    if params is not None:
        body["params"] = params
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{BASE}/messages/?session_id={session_id}",
        data=data,
        method="POST",
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        return r.status, r.read().decode()


def wait_response(_id, timeout=4.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        for m in inbox:
            if m.get("id") == _id:
                return m
        time.sleep(0.1)
    return None


t = threading.Thread(target=sse_reader, daemon=True)
t.start()

for _ in range(30):
    if session_id:
        break
    time.sleep(0.1)

if not session_id:
    print("FAIL: no session_id from SSE within 3s")
    sys.exit(1)

print(f"PASS session_id captured: {session_id[:16]}...")

print("-- initialize --")
status, body = post("initialize", {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "verify", "version": "0.1"}}, _id=1)
print(f"  POST {status}")
resp = wait_response(1)
if not resp:
    print("FAIL: initialize did not return over SSE")
    sys.exit(2)
si = resp.get("result", {}).get("serverInfo", {})
print(f"PASS server: {si.get('name', '?')} v{si.get('version', '?')}")

print("-- notifications/initialized --")
post("notifications/initialized", {})

print("-- tools/list --")
status, body = post("tools/list", {}, _id=2)
print(f"  POST {status}")
resp = wait_response(2)
if not resp:
    print("FAIL: tools/list did not return")
    sys.exit(3)

tools = resp.get("result", {}).get("tools", [])
print(f"PASS {len(tools)} tool(s) exposed:")
for t in tools:
    name = t.get("name")
    desc = (t.get("description") or "")[:100]
    print(f"    - {name}: {desc}")

stop.set()
print("")
print("MCP server verified.")
