#!/bin/bash
# Test Runner Script for NewFire Backend Tenant/RBAC Tests
# This script runs the tenant/RBAC integration tests locally without production DB

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
TEST_DB_HOST="${TEST_DB_HOST:-localhost}"
TEST_DB_PORT="${TEST_DB_PORT:-5432}"
TEST_DB_USER="${TEST_DB_USER:-postgres}"
TEST_DB_PASSWORD="${TEST_DB_PASSWORD:-postgres}"
TEST_DB_NAME="${TEST_DB_NAME:-newfire_test}"
TEST_API_URL="${TEST_API_URL:-http://localhost:3200}"
RUN_MODE="${RUN_MODE:-all}"  # all, auth, company, agent, cross-tenant

# Print colored message
print_msg() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[FAIL]${NC} $1"
}

# Show usage
usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --mode MODE       Test mode: all, auth, company, agent, cross-tenant (default: all)"
    echo "  --db-host HOST    Database host (default: localhost)"
    echo "  --db-port PORT    Database port (default: 5432)"
    echo "  --db-user USER    Database user (default: postgres)"
    echo "  --db-pass PASS    Database password (default: postgres)"
    echo "  --db-name NAME    Database name (default: newfire_test)"
    echo "  --api-url URL     Backend API URL (default: http://localhost:3200)"
    echo "  --help            Show this help message"
    echo ""
    echo "Environment variables:"
    echo "  TEST_DB_HOST, TEST_DB_PORT, TEST_DB_USER, TEST_DB_PASSWORD"
    echo "  TEST_DB_NAME, TEST_API_URL, RUN_MODE"
    exit 0
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --mode)
            RUN_MODE="$2"
            shift 2
            ;;
        --db-host)
            TEST_DB_HOST="$2"
            shift 2
            ;;
        --db-port)
            TEST_DB_PORT="$2"
            shift 2
            ;;
        --db-user)
            TEST_DB_USER="$2"
            shift 2
            ;;
        --db-pass)
            TEST_DB_PASSWORD="$2"
            shift 2
            ;;
        --db-name)
            TEST_DB_NAME="$2"
            shift 2
            ;;
        --api-url)
            TEST_API_URL="$2"
            shift 2
            ;;
        --help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Export environment variables for tests
export TEST_DB_HOST TEST_DB_PORT TEST_DB_USER TEST_DB_PASSWORD TEST_DB_NAME TEST_API_URL

print_msg "Starting NewFire Backend Tenant/RBAC Test Suite"
print_msg "================================================"
echo ""

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    print_warning "node_modules not found. Installing dependencies..."
    npm install
fi

# Check database connectivity
print_msg "Checking database connectivity..."
if command -v psql &> /dev/null; then
    if PGPASSWORD="$TEST_DB_PASSWORD" psql -h "$TEST_DB_HOST" -p "$TEST_DB_PORT" -U "$TEST_DB_USER" -d "$TEST_DB_NAME" -c "SELECT 1" &> /dev/null; then
        print_success "Database connection successful"
    else
        print_warning "Could not connect to database. Tests requiring DB may fail."
        print_msg "To set up test database, run:"
        echo "  createdb $TEST_DB_NAME"
        echo "  psql -d $TEST_DB_NAME -f tests/helpers/schema.sql"
    fi
else
    print_warning "psql not found. Skipping database connectivity check."
fi

# Check backend connectivity
print_msg "Checking backend API connectivity..."
if curl -s -f "$TEST_API_URL/health" &> /dev/null; then
    print_success "Backend API is reachable at $TEST_API_URL"
else
    print_warning "Backend API not reachable at $TEST_API_URL"
    print_msg "Tests requiring the API may fail. To start backend locally:"
    echo "  cd /path/to/newfire-backend && npm start"
fi

echo ""

# Determine which tests to run
TEST_PATTERN=""
case $RUN_MODE in
    auth)
        TEST_PATTERN="**/auth.test.js"
        print_msg "Running Authentication tests..."
        ;;
    company)
        TEST_PATTERN="**/company.test.js"
        print_msg "Running Company/Tenant tests..."
        ;;
    agent)
        TEST_PATTERN="**/agent.test.js"
        print_msg "Running Agent Access tests..."
        ;;
    cross-tenant)
        TEST_PATTERN="**/crossTenant.test.js"
        print_msg "Running Cross-Tenant Denial tests..."
        ;;
    all)
        TEST_PATTERN="**/*.test.js"
        print_msg "Running all Tenant/RBAC tests..."
        ;;
    *)
        print_error "Unknown test mode: $RUN_MODE"
        exit 1
        ;;
esac

echo ""

# Run tests
cd "$(dirname "$0")/.."
npm test -- --testPathPattern="$TEST_PATTERN" --verbose "$@"

# Capture exit code
TEST_EXIT_CODE=$?

echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    print_success "All tests passed!"
else
    print_error "Some tests failed. Exit code: $TEST_EXIT_CODE"
fi

exit $TEST_EXIT_CODE