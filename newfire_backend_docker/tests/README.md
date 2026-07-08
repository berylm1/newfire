# NewFire Backend Tenant/RBAC Integration Test Harness

This directory contains a comprehensive test harness for testing tenant isolation and Role-Based Access Control (RBAC) in the NewFire backend.

## Overview

The test harness covers the following security-critical areas:

1. **Authentication Tests** (`auth.test.js`) - User signup, login, JWT token validation
2. **Company/Tenant Tests** (`company.test.js`) - Company creation, management, and isolation
3. **Agent Access Tests** (`agent.test.js`) - Agent creation, retrieval, and tenant-scoped access
4. **Cross-Tenant Denial Tests** (`crossTenant.test.js`) - Critical RBAC security tests verifying tenant isolation

## Acceptance Criteria Met

✅ **Add backend test framework/script** - Complete test harness with Jest
✅ **Cover signup, login, company creation** - Auth and Company tests
✅ **Cover agent access** - Agent tests with tenant scoping
✅ **Cover cross-tenant denial** - Comprehensive isolation tests
✅ **Tests run locally without production DB/secrets** - Uses isolated test database

## Quick Start

### Prerequisites

- Node.js 18+ with ES modules support
- PostgreSQL 14+ (for database tests)
- Access to a running NewFire backend (optional, for integration tests)

### Installation

```bash
cd tests
npm install
```

### Setup Test Database

```bash
# Create the test database
createdb newfire_test

# Initialize the schema
psql -d newfire_test -f helpers/schema.sql

# Or use the setup script
node scripts/setup-test-db.js
```

### Running Tests

```bash
# Run all tests
npm test

# Run specific test suites
npm test -- auth.test.js
npm test -- company.test.js
npm test -- agent.test.js
npm test -- crossTenant.test.js

# Run with coverage
npm run test:coverage

# Run in watch mode
npm run test:watch
```

### Using the Test Runner Script

```bash
# Run all tests
bash tests/run-tests.sh

# Run specific test suite
bash tests/run-tests.sh --mode auth
bash tests/run-tests.sh --mode company
bash tests/run-tests.sh --mode agent
bash tests/run-tests.sh --mode cross-tenant

# Custom database configuration
bash tests/run-tests.sh --db-host localhost --db-port 5432 --db-name newfire_test
```

## Configuration

Tests can be configured via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `TEST_API_URL` | Backend API URL | `http://localhost:3200` |
| `TEST_DB_HOST` | Database host | `localhost` |
| `TEST_DB_PORT` | Database port | `5432` |
| `TEST_DB_USER` | Database user | `postgres` |
| `TEST_DB_PASSWORD` | Database password | `postgres` |
| `TEST_DB_NAME` | Database name | `newfire_test` |
| `JWT_SECRET` | JWT signing secret | `test-jwt-secret-for-testing-only` |
| `TEST_VERBOSE` | Enable verbose logging | Not set (quiet mode) |

## Test Structure

```
tests/
├── setup.js                    # Test environment configuration
├── package.json                # Test dependencies and scripts
├── run-tests.sh               # Shell script for running tests
├── helpers/
│   ├── index.js               # Helper exports
│   ├── TestClient.js          # HTTP client for API testing
│   ├── DatabaseHelper.js      # Database operations for tests
│   ├── AuthHelper.js          # JWT and password utilities
│   └── schema.sql             # Database schema for tests
├── scripts/
│   ├── setup-test-db.js      # Database setup script
│   └── teardown-test-db.js    # Database cleanup script
├── auth.test.js              # Authentication tests
├── company.test.js           # Company/Tenant tests
├── agent.test.js             # Agent access tests
└── crossTenant.test.js       # Cross-tenant denial tests
```

## Test Descriptions

### Authentication Tests (`auth.test.js`)

| Test | Description |
|------|-------------|
| Signup with valid data | New user registration succeeds |
| Signup with invalid email | Rejects malformed email addresses |
| Signup with weak password | Enforces password strength requirements |
| Signup with duplicate email | Prevents duplicate accounts |
| Login with valid credentials | JWT token returned on success |
| Login with wrong password | Rejects incorrect credentials |
| Protected route access | Requires valid JWT token |
| Token structure validation | Verifies JWT format and claims |

### Company/Tenant Tests (`company.test.js`)

| Test | Description |
|------|-------------|
| Company creation | Creates new tenant entity |
| User-company association | Links user to company on creation |
| Company listing | Returns only user's companies |
| Company update | Modifies company details |
| Multi-tenant isolation | Companies are scoped to owners |
| Admin company operations | Admin can list/delete any company |

### Agent Access Tests (`agent.test.js`)

| Test | Description |
|------|-------------|
| Agent creation | Creates agent within company scope |
| Agent retrieval | Gets agent by ID |
| Agent listing | Returns only company's agents |
| Agent update | Modifies agent configuration |
| Agent deletion | Removes agent from company |
| Tenant isolation | Agents are scoped to companies |
| Chat integration | Sends/receives messages |

### Cross-Tenant Denial Tests (`crossTenant.test.js`)

These are **security-critical** tests. Any failure indicates a potential data leak.

| Test | Description |
|------|-------------|
| Company access denial | Cannot access other tenant's company |
| Company update denial | Cannot modify other tenant's company |
| Agent access denial | Cannot access other tenant's agents |
| Agent update denial | Cannot modify other tenant's agents |
| Chat denial | Cannot chat with other tenant's agents |
| Conversation isolation | Conversations are tenant-scoped |
| Invalid ID handling | Rejects SQL injection attempts |
| Edge cases | Handles rapid switching, concurrency |

## Test Data Management

Tests use the following patterns for data isolation:

### Unique Test Data

```javascript
import { generateTestEmail, generateTestCompanyName } from './helpers';

test('creates company', async () => {
  const email = generateTestEmail();  // unique per test
  const companyName = generateTestCompanyName();
  // ...
});
```

### Database Cleanup

Each test file includes `beforeEach` to clean tables:

```javascript
beforeEach(async () => {
  await dbHelper.cleanTables();
});
```

### Test Isolation

Tests are designed to:
- Run in any order (no dependencies between tests)
- Use unique data (timestamps + random suffixes)
- Clean up after themselves
- Be idempotent

## Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL is running
pg_isready -h localhost -p 5432

# Create database manually
createdb newfire_test

# Test connection
psql -d newfire_test -c "SELECT 1"
```

### Backend Not Reachable

```bash
# Start backend locally
cd /path/to/newfire-backend
npm start

# Or use mock server for unit tests
```

### Test Failures

If tests fail, check:
1. Database is accessible with provided credentials
2. Backend API is running (or mock is configured)
3. Schema is initialized (`psql -d newfire_test -f helpers/schema.sql`)
4. Environment variables are set correctly

## Development

### Adding New Tests

1. Create a new test file: `tests/<feature>.test.js`
2. Import helpers: `import { TestClient, generateTestEmail } from './helpers';`
3. Use the test structure:

```javascript
describe('Feature', () => {
  let client;
  let dbHelper;

  beforeAll(async () => {
    dbHelper = new DatabaseHelper();
    await dbHelper.initializeDatabase();
  });

  beforeEach(async () => {
    client = new TestClient();
    await dbHelper.cleanTables();
    // Setup test data
  });

  afterAll(async () => {
    await dbHelper.close();
  });

  test('should do something', async () => {
    // Arrange
    await client.signup(generateTestEmail(), 'Pass123!', 'User');
    
    // Act
    const result = await client.someAction();
    
    // Assert
    expect(result).toBeDefined();
  });
});
```

### Running Specific Tests

```bash
# Single test
npm test -- --testNamePattern="should signup"

# Multiple patterns
npm test -- --testNamePattern="signup|login"

# Debug mode
npm test -- --inspect-brk
```

## CI/CD Integration

The test harness can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run Tenant/RBAC Tests
  run: |
    cd newfire_backend_docker/tests
    npm install
    node scripts/setup-test-db.js
    npm test
    node scripts/teardown-test-db.js
  env:
    TEST_DB_HOST: localhost
    TEST_DB_PASSWORD: ${{ secrets.TEST_DB_PASSWORD }}
```

## Security Notes

- Tests use a separate database (`newfire_test`) from production
- JWT secrets in tests are for testing only
- No real user data should be used in tests
- Cross-tenant denial tests are critical for security validation
- All tests should pass before deploying to production

## License

Proprietary - NewFire Project