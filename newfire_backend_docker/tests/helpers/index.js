/**
 * Test helpers index
 * Export all test utilities for easy importing
 */

export { TestClient, createTestClient } from './TestClient.js';
export { DatabaseHelper, createTestPool, TEST_SCHEMA_SQL } from './DatabaseHelper.js';
export {
  generateTestToken,
  generateExpiredToken,
  generateInvalidSignatureToken,
  decodeToken,
  verifyToken,
  hashPassword,
  comparePassword,
  generateUserPayload,
  generateAdminPayload,
} from './AuthHelper.js';

export {
  TEST_CONFIG,
  MOCK_SERVICES,
  TEST_USERS,
  generateTestEmail,
  generateTestCompanyName,
  generateTestAgentName,
} from '../setup.js';