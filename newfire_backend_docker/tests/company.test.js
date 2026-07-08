/**
 * Company/Tenant Tests - Company Creation and Management Tests
 * 
 * Tests cover:
 * - Company creation with valid/invalid data
 * - User association with companies
 * - Company listing and retrieval
 * - Company update and delete operations
 * - Multi-tenant isolation at company level
 */

import { jest } from '@jest/globals';
import { TestClient, generateTestEmail, generateTestCompanyName, DatabaseHelper, hashPassword } from './helpers/index.js';

describe('Company - Creation', () => {
  let client;
  let dbHelper;

  beforeAll(async () => {
    dbHelper = new DatabaseHelper();
    await dbHelper.initializeDatabase();
  });

  beforeEach(async () => {
    client = new TestClient();
    await dbHelper.cleanTables();
  });

  afterAll(async () => {
    await dbHelper.close();
  });

  test('should create a company with valid data', async () => {
    // First signup a user
    await client.signup(
      generateTestEmail('company'),
      'SecurePass123!',
      'Company Owner'
    );

    // Create company
    const companyName = generateTestCompanyName();
    const company = await client.createCompany(companyName, 'Test company description');

    expect(company).toBeDefined();
    expect(company.id).toBeDefined();
    expect(company.name).toBe(companyName);
    expect(company.description).toBe('Test company description');
    expect(company.user_id || company.owner_id).toBeDefined();
  });

  test('should associate user with company on creation', async () => {
    // Signup user
    await client.signup(
      generateTestEmail('assoc'),
      'SecurePass123!',
      'Assoc User'
    );

    // Create company
    const company = await client.createCompany(generateTestCompanyName());

    // Verify user is associated with company
    const user = await client.getMe();
    expect(user.company_id || user.companyId).toBe(company.id);
  });

  test('should require authentication to create company', async () => {
    const unauthenticatedClient = new TestClient();
    
    await expect(
      unauthenticatedClient.createCompany(generateTestCompanyName())
    ).rejects.toThrow();
  });

  test('should reject company creation with empty name', async () => {
    await client.signup(
      generateTestEmail('emptyname'),
      'SecurePass123!',
      'Test User'
    );

    await expect(
      client.createCompany('')
    ).rejects.toThrow();
  });

  test('should reject company creation with duplicate name for same user', async () => {
    await client.signup(
      generateTestEmail('dupcompany'),
      'SecurePass123!',
      'Test User'
    );

    // Create first company
    await client.createCompany('Unique Company Name');

    // Try to create second company with same name
    await expect(
      client.createCompany('Unique Company Name')
    ).rejects.toThrow();
  });

  test('should allow same company name for different users', async () => {
    const client1 = new TestClient();
    const client2 = new TestClient();

    await client1.signup(generateTestEmail('same1'), 'Pass123!', 'User 1');
    await client2.signup(generateTestEmail('same2'), 'Pass123!', 'User 2');

    // Both users can create company with same name
    const company1 = await client1.createCompany('Same Name Company');
    const company2 = await client2.createCompany('Same Name Company');

    expect(company1.id).not.toBe(company2.id);
    expect(company1.name).toBe(company2.name);
  });
});

describe('Company - Retrieval', () => {
  let ownerClient;
  let dbHelper;

  beforeAll(async () => {
    dbHelper = new DatabaseHelper();
    await dbHelper.initializeDatabase();
  });

  beforeEach(async () => {
    ownerClient = new TestClient();
    await dbHelper.cleanTables();
    
    // Setup: Create user and company
    await ownerClient.signup(
      generateTestEmail('retrieve'),
      'SecurePass123!',
      'Owner User'
    );
    await ownerClient.createCompany(generateTestCompanyName());
  });

  afterAll(async () => {
    await dbHelper.close();
  });

  test('should get company by ID for owner', async () => {
    const company = await ownerClient.getCompany(ownerClient.companyId);

    expect(company).toBeDefined();
    expect(company.id).toBe(ownerClient.companyId);
  });

  test('should list companies for authenticated user', async () => {
    const companies = await ownerClient.listCompanies();

    expect(companies).toBeDefined();
    expect(Array.isArray(companies)).toBe(true);
    expect(companies.length).toBeGreaterThan(0);
  });

  test('should include company details in list response', async () => {
    const companies = await ownerClient.listCompanies();

    companies.forEach(company => {
      expect(company.id).toBeDefined();
      expect(company.name).toBeDefined();
    });
  });

  test('should reject company retrieval without authentication', async () => {
    const unauthenticatedClient = new TestClient();
    
    await expect(
      unauthenticatedClient.getCompany(ownerClient.companyId)
    ).rejects.toThrow();
  });
});

describe('Company - Update', () => {
  let client;
  let dbHelper;

  beforeAll(async () => {
    dbHelper = new DatabaseHelper();
    await dbHelper.initializeDatabase();
  });

  beforeEach(async () => {
    client = new TestClient();
    await dbHelper.cleanTables();
    
    await client.signup(
      generateTestEmail('update'),
      'SecurePass123!',
      'Update User'
    );
    await client.createCompany(generateTestCompanyName());
  });

  afterAll(async () => {
    await dbHelper.close();
  });

  test('should update company name', async () => {
    const newName = 'Updated Company Name';
    const updated = await client.updateCompany(client.companyId, { name: newName });

    expect(updated).toBeDefined();
    expect(updated.name).toBe(newName);
  });

  test('should update company description', async () => {
    const newDescription = 'Updated description text';
    const updated = await client.updateCompany(client.companyId, { description: newDescription });

    expect(updated).toBeDefined();
    expect(updated.description).toBe(newDescription);
  });

  test('should reject update for non-existent company', async () => {
    await expect(
      client.updateCompany(99999, { name: 'Test' })
    ).rejects.toThrow();
  });

  test('should require authentication to update company', async () => {
    const unauthenticatedClient = new TestClient();
    
    await expect(
      unauthenticatedClient.updateCompany(client.companyId, { name: 'Test' })
    ).rejects.toThrow();
  });
});

describe('Company - Multi-Tenant Isolation', () => {
  let dbHelper;

  beforeAll(async () => {
    dbHelper = new DatabaseHelper();
    await dbHelper.initializeDatabase();
  });

  beforeEach(async () => {
    await dbHelper.cleanTables();
  });

  afterAll(async () => {
    await dbHelper.close();
  });

  test('should not see other tenant companies in list', async () => {
    // Create two separate users with companies
    const client1 = new TestClient();
    const client2 = new TestClient();

    await client1.signup(generateTestEmail('iso1'), 'Pass123!', 'User 1');
    await client1.createCompany('Tenant 1 Company');

    await client2.signup(generateTestEmail('iso2'), 'Pass123!', 'User 2');
    await client2.createCompany('Tenant 2 Company');

    // Each should only see their own company
    const companies1 = await client1.listCompanies();
    const companies2 = await client2.listCompanies();

    expect(companies1.length).toBe(1);
    expect(companies1[0].name).toBe('Tenant 1 Company');

    expect(companies2.length).toBe(1);
    expect(companies2[0].name).toBe('Tenant 2 Company');
  });

  test('should not allow access to other tenant company by ID', async () => {
    const client1 = new TestClient();
    const client2 = new TestClient();

    await client1.signup(generateTestEmail('acc1'), 'Pass123!', 'User 1');
    const company1 = await client1.createCompany('Tenant 1 Company');

    await client2.signup(generateTestEmail('acc2'), 'Pass123!', 'User 2');
    await client2.createCompany('Tenant 2 Company');

    // Client 2 should not be able to access Client 1's company
    await expect(client2.getCompany(company1.id)).rejects.toThrow();
  });

  test('should not allow update to other tenant company', async () => {
    const client1 = new TestClient();
    const client2 = new TestClient();

    await client1.signup(generateTestEmail('upd1'), 'Pass123!', 'User 1');
    const company1 = await client1.createCompany('Tenant 1 Company');

    await client2.signup(generateTestEmail('upd2'), 'Pass123!', 'User 2');
    await client2.createCompany('Tenant 2 Company');

    // Client 2 should not be able to update Client 1's company
    await expect(
      client2.updateCompany(company1.id, { name: 'Hacked!' })
    ).rejects.toThrow();
  });

  test('should create separate data for each tenant', async () => {
    const client1 = new TestClient();
    const client2 = new TestClient();

    const email1 = generateTestEmail('data1');
    const email2 = generateTestEmail('data2');

    await client1.signup(email1, 'Pass123!', 'User 1');
    await client1.createCompany('Company 1');

    await client2.signup(email2, 'Pass123!', 'User 2');
    await client2.createCompany('Company 2');

    // Each should see their own user and company
    const me1 = await client1.getMe();
    const me2 = await client2.getMe();

    expect(me1.email).toBe(email1);
    expect(me2.email).toBe(email2);
    expect(me1.company_id).not.toBe(me2.company_id);
  });
});

describe('Company - Admin Operations', () => {
  let dbHelper;

  beforeAll(async () => {
    dbHelper = new DatabaseHelper();
    await dbHelper.initializeDatabase();
  });

  beforeEach(async () => {
    await dbHelper.cleanTables();
  });

  afterAll(async () => {
    await dbHelper.close();
  });

  test('should allow admin to list all companies', async () => {
    // Create admin user
    const adminClient = new TestClient();
    await adminClient.signup(
      generateTestEmail('admin'),
      'SecurePass123!',
      'Admin User'
    );

    // Create multiple companies with different users
    for (let i = 0; i < 3; i++) {
      const userClient = new TestClient();
      await userClient.signup(generateTestEmail(`user${i}`), 'Pass123!', `User ${i}`);
      await userClient.createCompany(`Company ${i}`);
    }

    // Admin should see all companies
    const allCompanies = await adminClient.listCompanies();
    expect(allCompanies.length).toBeGreaterThanOrEqual(3);
  });

  test('should allow admin to delete company', async () => {
    const adminClient = new TestClient();
    await adminClient.signup(
      generateTestEmail('admindel'),
      'SecurePass123!',
      'Admin User'
    );

    const userClient = new TestClient();
    await userClient.signup(generateTestEmail('deluser'), 'Pass123!', 'Delete User');
    const company = await userClient.createCompany('To Be Deleted');

    // Admin deletes company
    await adminClient.deleteCompany(company.id);

    // Company should no longer exist
    await expect(userClient.getCompany(company.id)).rejects.toThrow();
  });

  test('should not allow regular user to delete company', async () => {
    const client1 = new TestClient();
    await client1.signup(generateTestEmail('nondel'), 'Pass123!', 'User 1');
    const company = await client1.createCompany('Company');

    const client2 = new TestClient();
    await client2.signup(generateTestEmail('nondel2'), 'Pass123!', 'User 2');

    // Regular user should not be able to delete other's company
    await expect(client2.deleteCompany(company.id)).rejects.toThrow();
  });
});