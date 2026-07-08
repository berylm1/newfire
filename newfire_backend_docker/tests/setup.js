/**
 * Test setup - runs before all tests
 * Configures test environment with isolated database and mock services
 */

// Test configuration - can be overridden via environment variables
const TEST_CONFIG = {
  // Backend API URL - use local backend or mock server
  API_URL: process.env.TEST_API_URL || 'http://localhost:3200',
  
  // Database configuration for test isolation
  // Tests use a separate test database to avoid polluting production data
  DB_HOST: process.env.TEST_DB_HOST || 'localhost',
  DB_PORT: process.env.TEST_DB_PORT || '5432',
  DB_USER: process.env.TEST_DB_USER || 'postgres',
  DB_PASSWORD: process.env.TEST_DB_PASSWORD || 'postgres',
  DB_NAME: process.env.TEST_DB_NAME || 'newfire_test',
  
  // JWT configuration
  JWT_SECRET: process.env.JWT_SECRET || 'test-jwt-secret-for-testing-only',
  
  // Test timeouts
  DEFAULT_TIMEOUT: 30000,
  LOGIN_TIMEOUT: 10000,
};

// Mock external services that tests should not hit
const MOCK_SERVICES = {
  OPENCLAW_URL: 'http://localhost:18789',
  OPENCLAW_TOKEN: 'mock-openclaw-token',
  APISIX_ADMIN_URL: 'http://localhost:9180',
  APISIX_ADMIN_KEY: 'mock-apisix-key',
  OLLAMA_URL: 'http://localhost:11434',
  QDRANT_URL: 'http://localhost:6333',
  QDRANT_API_KEY: 'mock-qdrant-key',
};

// Test data generators
const generateTestEmail = (prefix = 'test') => {
  const timestamp = Date.now();
  return `${prefix}_${timestamp}@test.newfire.local`;
};

const generateTestCompanyName = () => {
  return `Test Company ${Date.now()}`;
};

const generateTestAgentName = () => {
  return `Test Agent ${Date.now()}`;
};

// Test user fixtures - pre-defined users for specific test scenarios
const TEST_USERS = {
  ADMIN: {
    email: 'test_admin@test.newfire.local',
    password: 'AdminTest123!',
    name: 'Test Admin',
    role: 'admin',
  },
  USER: {
    email: 'test_user@test.newfire.local',
    password: 'UserTest123!',
    name: 'Test User',
    role: 'user',
  },
  OTHER_TENANT_USER: {
    email: 'other_tenant@test.newfire.local',
    password: 'OtherTenant123!',
    name: 'Other Tenant User',
    role: 'user',
  },
};

// Export configuration
global.TEST_CONFIG = TEST_CONFIG;
global.MOCK_SERVICES = MOCK_SERVICES;
global.TEST_USERS = TEST_USERS;
global.generateTestEmail = generateTestEmail;
global.generateTestCompanyName = generateTestCompanyName;
global.generateTestAgentName = generateTestAgentName;

// Suppress console noise during tests unless in verbose mode
if (!process.env.TEST_VERBOSE) {
  global.console = {
    ...console,
    log: jest.fn(),
    info: jest.fn(),
    debug: jest.fn(),
    warn: console.warn,
    error: console.error,
  };
}

console.log('Test environment configured');