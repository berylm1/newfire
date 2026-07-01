/**
 * Auth Helper - JWT token generation and validation utilities for tests
 */

import jwt from 'jsonwebtoken';
import bcrypt from 'bcryptjs';

/**
 * Generate a valid JWT token for testing
 */
export function generateTestToken(payload, options = {}) {
  const secret = options.secret || process.env.JWT_SECRET || 'test-jwt-secret-for-testing-only';
  const expiresIn = options.expiresIn || '1h';
  
  return jwt.sign(payload, secret, { expiresIn });
}

/**
 * Generate an expired JWT token (for testing token expiry)
 */
export function generateExpiredToken(payload, secret = 'test-jwt-secret-for-testing-only') {
  return jwt.sign(payload, secret, { expiresIn: '-1s' });
}

/**
 * Generate a token with invalid signature
 */
export function generateInvalidSignatureToken(payload) {
  return jwt.sign(payload, 'wrong-secret-key');
}

/**
 * Decode a JWT token without verification (for inspecting claims)
 */
export function decodeToken(token) {
  return jwt.decode(token);
}

/**
 * Verify a JWT token
 */
export function verifyToken(token, secret = 'test-jwt-secret-for-testing-only') {
  return jwt.verify(token, secret);
}

/**
 * Hash a password using bcrypt (matching backend implementation)
 */
export async function hashPassword(password, saltRounds = 10) {
  return bcrypt.hash(password, saltRounds);
}

/**
 * Compare password with hash
 */
export async function comparePassword(password, hash) {
  return bcrypt.compare(password, hash);
}

/**
 * Generate test user payload for JWT
 */
export function generateUserPayload(user) {
  return {
    userId: user.id,
    email: user.email,
    role: user.role,
    companyId: user.company_id || null,
  };
}

/**
 * Generate test admin payload for JWT
 */
export function generateAdminPayload(user) {
  return {
    userId: user.id,
    email: user.email,
    role: 'admin',
    companyId: user.company_id || null,
  };
}

export default {
  generateTestToken,
  generateExpiredToken,
  generateInvalidSignatureToken,
  decodeToken,
  verifyToken,
  hashPassword,
  comparePassword,
  generateUserPayload,
  generateAdminPayload,
};