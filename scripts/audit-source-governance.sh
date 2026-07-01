#!/usr/bin/env bash
# Source Control Governance Audit Script
# 
# This script validates that all production services have proper GitHub governance
# as required by the CEO directive. It reads the source-control-manifest.yaml
# and fails if any production service lacks a GitHub remote.
#
# Exit codes:
#   0 - All production services are GitHub-governed
#   1 - One or more production services lack GitHub governance
#
# Usage:
#   ./scripts/audit-source-governance.sh [--verbose] [--manifest PATH]
#
# Options:
#   --verbose    Show detailed output for all services, not just failures
#   --manifest   Path to the source-control manifest (default: source-control-manifest.yaml)

set -euo pipefail

VERBOSE=false
MANIFEST_PATH="source-control-manifest.yaml"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --verbose)
            VERBOSE=true
            shift
            ;;
        --manifest)
            MANIFEST_PATH="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [--verbose] [--manifest PATH]"
            echo ""
            echo "Audit source control governance for NewFire platform services."
            echo "Fails if any production service lacks a GitHub remote."
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if manifest exists
if [[ ! -f "$MANIFEST_PATH" ]]; then
    echo -e "${RED}ERROR: Source control manifest not found: $MANIFEST_PATH${NC}" >&2
    exit 1
fi

echo "=============================================="
echo "  NewFire Source Control Governance Audit"
echo "=============================================="
echo ""
echo "Manifest: $MANIFEST_PATH"
echo ""

# Parse YAML and extract service information
# This uses a simple grep-based approach since we may not have yq installed
SERVICES=$(grep -A 15 "^  - service:" "$MANIFEST_PATH" | grep "^  - service:" | sed 's/.*- service: //' | tr -d ' ')

# Counters
TOTAL_SERVICES=0
PRODUCTION_SERVICES=0
PRODUCTION_GOVERNED=0
PRODUCTION_UNGOVERNED=0

# Arrays to store details
declare -a UNGOVERNED_SERVICES=()
declare -a GOVERNANCE_ISSUES=()

# Process each service block
# We need to extract service name, risk_level, github_governed, and repo_url from each block
parse_service_blocks() {
    local in_service=false
    local current_service=""
    local current_risk=""
    local current_governed=""
    local current_repo=""
    
    while IFS= read -r line; do
        # Check for new service block
        if [[ $line =~ ^[[:space:]]*-[[:space:]]service:[[:space:]]*(.+)$ ]]; then
            # Process previous service if exists
            if [[ -n "$current_service" ]]; then
                process_service "$current_service" "$current_risk" "$current_governed" "$current_repo"
            fi
            current_service="${BASH_REMATCH[1]}"
            current_risk=""
            current_governed=""
            current_repo=""
            in_service=true
        elif $in_service; then
            if [[ $line =~ ^[[:space:]]+risk_level:[[:space:]]*(.+)$ ]]; then
                current_risk="${BASH_REMATCH[1]}"
            elif [[ $line =~ ^[[:space:]]+github_governed:[[:space:]]*(.+)$ ]]; then
                current_governed="${BASH_REMATCH[1]}"
            elif [[ $line =~ ^[[:space:]]+repo_url:[[:space:]]*(.+)$ ]]; then
                current_repo="${BASH_REMATCH[1]}"
            fi
        fi
    done < "$MANIFEST_PATH"
    
    # Process last service
    if [[ -n "$current_service" ]]; then
        process_service "$current_service" "$current_risk" "$current_governed" "$current_repo"
    fi
}

process_service() {
    local service="$1"
    local risk="$2"
    local governed="$3"
    local repo="$4"
    
    ((TOTAL_SERVICES++)) || true
    
    if [[ "$risk" == "production" ]]; then
        ((PRODUCTION_SERVICES++)) || true
        
        if [[ "$governed" == "true" ]] || [[ "$repo" != "null" && -n "$repo" ]]; then
            ((PRODUCTION_GOVERNED++)) || true
            if $VERBOSE; then
                echo -e "${GREEN}[PASS]${NC} $service (production) - GitHub governed"
            fi
        else
            ((PRODUCTION_UNGOVERNED++)) || true
            UNGOVERNED_SERVICES+=("$service")
            GOVERNANCE_ISSUES+=("$service: lacks GitHub remote")
            
            echo -e "${RED}[FAIL]${NC} $service (production) - NOT GitHub governed"
            echo "        Local path: $(grep -A 3 "service: $service" "$MANIFEST_PATH" | grep "local_path:" | sed 's/.*local_path: //')"
            
            if [[ "$repo" == "null" || -z "$repo" ]]; then
                echo "        Issue: repo_url is null or missing"
            fi
            echo ""
        fi
    elif $VERBOSE; then
        echo -e "${YELLOW}[SKIP]${NC} $service ($risk) - Not production"
    fi
}

# Run the parser
parse_service_blocks

# Summary
echo ""
echo "=============================================="
echo "  Audit Summary"
echo "=============================================="
echo ""
echo "Total services in manifest: $TOTAL_SERVICES"
echo "Production services: $PRODUCTION_SERVICES"
echo "  - GitHub governed: $PRODUCTION_GOVERNED"
echo "  - NOT governed:    $PRODUCTION_UNGOVERNED"
echo ""

if [[ $PRODUCTION_UNGOVERNED -gt 0 ]]; then
    echo -e "${RED}AUDIT FAILED${NC}"
    echo ""
    echo "The following production services lack GitHub governance:"
    for service in "${UNGOVERNED_SERVICES[@]}"; do
        echo "  - $service"
    done
    echo ""
    echo "Required action: Configure GitHub remotes for these services or document approved vendored baselines."
    echo "See: https://github.com/berylm1/newfire/issues/27"
    exit 1
else
    echo -e "${GREEN}AUDIT PASSED${NC}"
    echo ""
    echo "All production services are GitHub-governed."
    exit 0
fi
