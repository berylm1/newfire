#!/usr/bin/env bash
# =============================================================================
# verify_network_isolation.sh
# Run this ON a homelab machine (Minisforum or DGX Spark) to verify isolation.
# =============================================================================

set -euo pipefail

# =============== CONFIGURE THESE ===============
GLINET_GATEWAY="192.168.10.1"       # GL.iNet router LAN IP (after isolation)
FIOS_ROUTER="192.168.1.1"           # Fios router IP (upstream, personal network)
OTHER_HOMELAB_IP="192.168.10.11"    # The OTHER homelab machine's IP
INTERNET_TEST_IP="8.8.8.8"
INTERNET_TEST_URL="https://httpbin.org/ip"

# Services expected on THIS machine (adjust per machine)
EXPECTED_PORTS=(9080 18789 3000 3003)  # APISIX, OpenClaw, OpenHands, Grafana
# ================================================

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

PASS="${GREEN}[PASS]${NC}"
FAIL="${RED}[FAIL]${NC}"
WARN="${YELLOW}[WARN]${NC}"
INFO="${CYAN}[INFO]${NC}"

echo ""
echo "========================================"
echo "  NewFire Homelab - Isolation Verifier"
echo "  $(date)"
echo "  Host: $(hostname)"
echo "========================================"
echo ""

# [1] Internet connectivity
echo -e "${INFO} Test 1: Internet connectivity"

if ping -c 2 -W 3 "$INTERNET_TEST_IP" &>/dev/null; then
    echo -e "  ${PASS} Can ping $INTERNET_TEST_IP (Google DNS)"
else
    echo -e "  ${FAIL} Cannot ping $INTERNET_TEST_IP — no internet?"
fi

if curl -sf --max-time 5 "$INTERNET_TEST_URL" &>/dev/null; then
    echo -e "  ${PASS} Can reach $INTERNET_TEST_URL (HTTP works)"
else
    echo -e "  ${FAIL} Cannot reach $INTERNET_TEST_URL"
fi
echo ""

# [2] Other homelab machine
echo -e "${INFO} Test 2: Reach other homelab machine ($OTHER_HOMELAB_IP)"

if ping -c 2 -W 3 "$OTHER_HOMELAB_IP" &>/dev/null; then
    echo -e "  ${PASS} Can ping $OTHER_HOMELAB_IP"
else
    echo -e "  ${FAIL} Cannot ping $OTHER_HOMELAB_IP — check cables/IPs"
fi
echo ""

# [3] GL.iNet router
echo -e "${INFO} Test 3: Reach GL.iNet gateway ($GLINET_GATEWAY)"

if ping -c 2 -W 3 "$GLINET_GATEWAY" &>/dev/null; then
    echo -e "  ${PASS} Can ping $GLINET_GATEWAY"
else
    echo -e "  ${FAIL} Cannot ping $GLINET_GATEWAY — wrong gateway IP?"
fi
echo ""

# [4] Fios router (should be blocked or NAT'd)
echo -e "${INFO} Test 4: Reach Fios router ($FIOS_ROUTER)"
echo -e "         (Reachable is OK — it's upstream. But personal devices should NOT reach us.)"

if ping -c 2 -W 3 "$FIOS_ROUTER" &>/dev/null; then
    echo -e "  ${WARN} Can ping $FIOS_ROUTER — expected (GL.iNet routes through it)"
    echo -e "         The important test is the REVERSE: run verify_isolation_from_personal.sh"
    echo -e "         from a device on the Fios network."
else
    echo -e "  ${PASS} Cannot ping $FIOS_ROUTER — strong isolation in place"
fi
echo ""

# [5] Local services
echo -e "${INFO} Test 5: Local services (Docker + ports)"

if command -v docker &>/dev/null; then
    RUNNING=$(docker ps --format '{{.Names}}' 2>/dev/null | wc -l | tr -d ' ')
    echo -e "  ${INFO} Docker containers running: $RUNNING"
    docker ps --format '  {{.Names}} ({{.Status}})' 2>/dev/null || true
else
    echo -e "  ${WARN} Docker not found on this machine"
fi
echo ""

for PORT in "${EXPECTED_PORTS[@]}"; do
    if ss -tlnp 2>/dev/null | grep -q ":${PORT} " || \
       netstat -tlnp 2>/dev/null | grep -q ":${PORT} "; then
        echo -e "  ${PASS} Port $PORT is listening"
    else
        echo -e "  ${WARN} Port $PORT is NOT listening (may not run on this machine)"
    fi
done
echo ""

# [6] Summary
echo "========================================"
echo "  Verification complete."
echo "  Remember: run verify_isolation_from_personal.sh"
echo "  from your Mac on the Fios network to confirm"
echo "  personal devices CANNOT reach this machine."
echo "========================================"
echo ""
