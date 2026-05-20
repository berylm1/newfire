#!/usr/bin/env bash
# =============================================================================
# verify_isolation_from_personal.sh
# Run this from a PERSONAL device (Mac on Fios network) to confirm it
# CANNOT reach the homelab machines. All tests should FAIL = isolation works.
# =============================================================================

set -euo pipefail

# =============== CONFIGURE THESE ===============
MINISFORUM_IP="192.168.10.10"   # Minisforum IP on GL.iNet subnet
DGX_SPARK_IP="192.168.10.11"   # DGX Spark IP on GL.iNet subnet
GLINET_LAN_IP="192.168.10.1"   # GL.iNet LAN-side IP

# Services that should be unreachable
TEST_PORTS=(9080 18789 3000 3003 22)  # APISIX, OpenClaw, OpenHands, Grafana, SSH
# ================================================

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

PASS="${GREEN}[PASS]${NC}"
FAIL="${RED}[FAIL]${NC}"
INFO="${CYAN}[INFO]${NC}"

ISSUES=0

echo ""
echo "========================================"
echo "  NewFire - Personal Device Isolation Test"
echo "  $(date)"
echo "  Host: $(hostname)"
echo "  Goal: NONE of these should be reachable"
echo "========================================"
echo ""

# [1] Ping tests
for IP in "$MINISFORUM_IP" "$DGX_SPARK_IP" "$GLINET_LAN_IP"; do
    echo -e "${INFO} Pinging $IP ..."
    if ping -c 2 -W 3 "$IP" &>/dev/null; then
        echo -e "  ${FAIL} CAN ping $IP — isolation is NOT working!"
        ((ISSUES++))
    else
        echo -e "  ${PASS} Cannot ping $IP — good, isolated"
    fi
done
echo ""

# [2] Port tests
echo -e "${INFO} Testing ports on Minisforum ($MINISFORUM_IP) ..."
for PORT in "${TEST_PORTS[@]}"; do
    # Use nc (netcat) with 3-second timeout
    if nc -z -w 3 "$MINISFORUM_IP" "$PORT" &>/dev/null; then
        echo -e "  ${FAIL} Port $PORT is REACHABLE — isolation broken!"
        ((ISSUES++))
    else
        echo -e "  ${PASS} Port $PORT is unreachable — good"
    fi
done
echo ""

echo -e "${INFO} Testing ports on DGX Spark ($DGX_SPARK_IP) ..."
for PORT in "${TEST_PORTS[@]}"; do
    if nc -z -w 3 "$DGX_SPARK_IP" "$PORT" &>/dev/null; then
        echo -e "  ${FAIL} Port $PORT is REACHABLE — isolation broken!"
        ((ISSUES++))
    else
        echo -e "  ${PASS} Port $PORT is unreachable — good"
    fi
done
echo ""

# [3] Summary
echo "========================================"
if [ "$ISSUES" -eq 0 ]; then
    echo -e "  ${PASS} ALL CLEAR — Network isolation is working!"
    echo "  Personal devices cannot reach the homelab."
else
    echo -e "  ${FAIL} ISSUES FOUND: $ISSUES tests failed"
    echo "  Your homelab is reachable from the personal network."
    echo "  Check GL.iNet firewall rules and subnet config."
fi
echo "========================================"
echo ""
