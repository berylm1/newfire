/**
 * Authentication Tests - Signup, Login, and JWT Token Tests
 * 
 * Tests cover:
 * - User registration with valid/invalid data
 * - Login with correct/incorrect credentials
 * - JWT token validation and expiry
 * - Protected route access
 */

import { jest } from '@jest/globals';
import { TestClient, generateTestEmail, hashPassword, generateTestToken, generateUserPayload } from './helpers/index.js';

describe('Authentication - Signup', () => {
  let client;

  beforeEach(() => {
    client = new TestClient();
  });

  afterEach(() => {
    client.clearAuth();
  });

  test('should signup a new user with valid data', async () => {
    const email = generateTestEmail('signup');
    const password = 'SecurePass123!';
    const name = 'Test User';

    const result = await client.signup(email, password, name);

    expect(result).toBeDefined();
    expect(result.email || result.user?.email).toBe(email);
    expect(result.name || result.user?.name).toBe(name);
    // Token should be returned on successful signup
    expect(result.token).toBeDefined();
  });

  test('should reject signup with invalid email format', async () => {
    const email = 'invalid-email';
    const password = 'SecurePass123!';
    const name = 'Test User';

    await expect(client.signup(email, password, name))
      .rejects.toThrow();
  });

  test('should reject signup with weak password', async () => {
    const email = generateTestEmail('weakpass');
    const password = '123'; // Too short
    const name = 'Test User';

    await expect(client.signup(email, password, name))
      .rejects.toThrow();
  });

  test('should reject signup with duplicate email', async () => {
    const email = generateTestEmail('duplicate');
    const password = 'SecurePass123!';
    const name = 'Test User';

    // First signup should succeed
    await client.signup(email, password, name);

    // Second signup with same email should fail
    const secondClient = new TestClient();
    await expect(secondClient.signup(email, password, name))
      .rejects.toThrow();
  });

  test('should reject signup with missing required fields', async () => {
    const client = new TestClient();

    // Missing email
    await expect(client.signup(null, 'SecurePass123!', 'Test'))
      .rejects.toThrow();

    // Missing password
    await expect(client.signup(generateTestEmail('nopass'), null, 'Test'))
      .rejects.toThrow();

    // Missing name
    await expect(client.signup(generateTestEmail('noname'), 'SecurePass123!', null))
      .rejects.toThrow();
  });

  test('should return proper token structure on signup', async () => {
    const email = generateTestEmail('token');
    const password = 'SecurePass123!';
    const name = 'Token Test User';

    const result = await client.signup(email, password, name);

    // Verify token structure
    expect(result.token).toBeDefined();
    expect(typeof result.token).toBe('string');
    expect(result.token.split('.')).toHaveLength(3); // JWT has 3 parts

    // Verify user info is returned
    expect(result.user).toBeDefined();
    expect(result.user.email).toBe(email);
    expect(result.user.name).toBe(name);
    expect(result.user.role).toBe('user');
  });
});

describe('Authentication - Login', () => {
  let client;
  let testEmail;
  let testPassword;
  let testName;

  beforeAll(async () => {
    // Create a user to test login
    client = new TestClient();
    testEmail = generateTestEmail('login');
    testPassword = 'LoginTest123!';
    testName = 'Login Test User';
    
    await client.signup(testEmail, testPassword, testName);
    client.clearAuth(); // Clear token so we can test fresh login
  });

  afterAll(async () => {
    client.clearAuth();
  });

  test('should login with valid credentials', async () => {
    const loginClient = new TestClient();
    const result = await loginClient.login(testEmail, testPassword);

    expect(result).toBeDefined();
    expect(result.token).toBeDefined();
    expect(result.user).toBeDefined();
    expect(result.user.email).toBe(testEmail);
    expect(result.user.name).toBe(testName);
  });

  test('should set token on successful login', async () => {
    const loginClient = new TestClient();
    await loginClient.login(testEmail, testPassword);

    expect(loginClient.token).toBeDefined();
    expect(typeof loginClient.token).toBe('string');
  });

  test('should reject login with incorrect password', async () => {
    const loginClient = new TestClient();
    
    await expect(loginClient.login(testEmail, 'WrongPassword123!'))
      .rejects.toThrow();
  });

  test('should reject login with non-existent email', async () => {
    const loginClient = new TestClient();
    
    await expect(loginClient.login('nonexistent@test.local', 'AnyPassword123!'))
      .rejects.toThrow();
  });

  test('should reject login with empty credentials', async () => {
    const loginClient = new TestClient();
    
    await expect(loginClient.login('', ''))
      .rejects.toThrow();
  });

  test('should preserve user context after login', async () => {
    const loginClient = new TestClient();
    await loginClient.login(testEmail, testPassword);

    expect(loginClient.userId).toBeDefined();
    expect(loginClient.companyId).toBeDefined(); // May be null for new users
  });
});

describe('Authentication - Protected Routes', () => {
  let client;

  beforeEach(() => {
    client = new TestClient();
  });

  test('should allow access to protected routes with valid token', async () => {
    // Signup to get a token
    await client.signup(
      generateTestEmail('protected'),
      'SecurePass123!',
      'Protected User'
    );

    // Get current user info (protected route)
    const me = await client.getMe();
    expect(me).toBeDefined();
    expect(me.email).toBeDefined();
  });

  test('should reject access to protected routes without token', async () => {
    // Try to access protected route without login
    await expect(client.getMe())
      .rejects.toThrow();
  });

  test('should reject access to protected routes with invalid token', async () => {
    client.setToken('invalid-token');
    
    await expect(client.getMe())
      .rejects.toThrow();
  });

  test('should reject access to protected routes with malformed token', async () => {
    client.setToken('not.a.valid.jwt.token');
    
    await expect(client.getMe())
      .rejects.toThrow();
  });
});

describe('Authentication - Token Validation', () => {
  test('should decode valid JWT token', async () => {
    const client = new TestClient();
    await client.signup(
      generateTestEmail('decode'),
      'SecurePass123!',
      'Decode User'
    );

    // Verify token is a valid JWT
    expect(client.token).toBeDefined();
    const parts = client.token.split('.');
    expect(parts).toHaveLength(3);
  });

  test('should include user claims in token', async () => {
    const email = generateTestEmail('claims');
    const client = new TestClient();
    const result = await client.signup(email, 'SecurePass123!', 'Claims User');

    // Verify token contains expected claims (decode without verification)
    const decoded = JSON.parse(Buffer.from(result.token.split('.')[1], 'base64').toString());
    expect(decoded.email).toBe(email);
    expect(decoded.userId).toBeDefined();
  });

  test('should set token expiration', async () => {
    const client = new TestClient();
    await client.signup(
      generateTestEmail('expiry'),
      'SecurePass123!',
      'Expiry User'
    );

    const decoded = JSON.parse(Buffer.from(client.token.split('.')[1], 'base64').toString());
    expect(decoded.exp).toBeDefined();
    expect(decoded.iat).toBeDefined();
    expect(decoded.exp).toBeGreaterThan(decoded.iat);
  });
});

describe('Authentication - Session Management', () => {
  test('should maintain separate sessions for different users', async () => {
    const client1 = new TestClient();
    const client2 = new TestClient();

    const email1 = generateTestEmail('session1');
    const email2 = generateTestEmail('session2');

    await client1.signup(email1, 'Pass123!', 'User One');
    await client2.signup(email2, 'Pass123!', 'User Two');

    // Each client should have its own token
    expect(client1.token).not.toBe(client2.token);

    // Each should see only their own user info
    const me1 = await client1.getMe();
    const me2 = await client2.getMe();
    
    expect(me1.email).toBe(email1);
    expect(me2.email).toBe(email2);
  });

  test('should clear auth state on logout', async () => {
    const client = new TestClient();
    await client.signup(
      generateTestEmail('logout'),
      'SecurePass123!',
      'Logout User'
    );

    expect(client.token).toBeDefined();

    client.clearAuth();
    expect(client.token).toBeNull();
    expect(client.userId).toBeNull();
    expect(client.companyId).toBeNull();
  });
});