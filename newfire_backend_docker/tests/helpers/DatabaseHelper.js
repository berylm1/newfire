/**
 * Database Helper - Test database setup and teardown utilities
 * Provides database operations for test isolation
 */

import pg from 'pg';

const { Pool } = pg;

/**
 * Test database configuration
 */
const getTestDbConfig = () => ({
  host: process.env.TEST_DB_HOST || 'localhost',
  port: parseInt(process.env.TEST_DB_PORT || '5432'),
  user: process.env.TEST_DB_USER || 'postgres',
  password: process.env.TEST_DB_PASSWORD || 'postgres',
  database: process.env.TEST_DB_NAME || 'newfire_test',
  max: 5,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 10000,
});

/**
 * Create a database connection pool for tests
 */
export function createTestPool() {
  return new Pool(getTestDbConfig());
}

/**
 * Schema initialization for test database
 * Creates all tables needed for tenant/RBAC testing
 */
export const TEST_SCHEMA_SQL = `
-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'user',
    onboarded BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT now()
);

-- Companies table (tenants)
CREATE TABLE IF NOT EXISTS companies (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    paperclip_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT now()
);

-- Agents table
CREATE TABLE IF NOT EXISTS agents (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
    agent_id VARCHAR(100) NOT NULL,
    name VARCHAR(255) NOT NULL,
    role TEXT,
    description TEXT,
    system_prompt TEXT,
    model VARCHAR(100) DEFAULT 'gemma4:26b',
    provider VARCHAR(50) DEFAULT 'local',
    openclaw_worker_id VARCHAR(255),
    icon VARCHAR(50) DEFAULT 'MessageSquare',
    color VARCHAR(100) DEFAULT 'from-blue-500 to-blue-600',
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT now()
);

-- Conversations table
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    agent_id VARCHAR(100) NOT NULL,
    messages JSONB DEFAULT '[]',
    updated_at TIMESTAMP DEFAULT now()
);

-- Client notes table
CREATE TABLE IF NOT EXISTS client_notes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    key VARCHAR(100) NOT NULL,
    value TEXT,
    updated_by INTEGER REFERENCES users(id),
    updated_at TIMESTAMP DEFAULT now()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_agents_company_id ON agents(company_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user_agent ON conversations(user_id, agent_id);
CREATE INDEX IF NOT EXISTS idx_companies_user_id ON companies(user_id);
`;

/**
 * Database helper class for test operations
 */
export class DatabaseHelper {
  constructor(pool = null) {
    this.pool = pool || createTestPool();
  }

  /**
   * Initialize test database with schema
   */
  async initializeDatabase() {
    const client = await this.pool.connect();
    try {
      await client.query(TEST_SCHEMA_SQL);
      console.log('Test database schema initialized');
    } finally {
      client.release();
    }
  }

  /**
   * Clean all data from test tables
   * Called between tests to ensure isolation
   */
  async cleanTables() {
    const client = await this.pool.connect();
    try {
      await client.query('BEGIN');
      // Delete in order to respect foreign key constraints
      await client.query('DELETE FROM client_notes');
      await client.query('DELETE FROM conversations');
      await client.query('DELETE FROM agents');
      await client.query('DELETE FROM companies');
      await client.query('DELETE FROM users');
      await client.query('COMMIT');
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  /**
   * Insert a test user directly into database
   */
  async insertUser(userData) {
    const { email, password_hash, name, role = 'user' } = userData;
    const result = await this.pool.query(
      `INSERT INTO users (email, password_hash, name, role) 
       VALUES ($1, $2, $3, $4) 
       RETURNING id, email, name, role, created_at`,
      [email, password_hash, name, role]
    );
    return result.rows[0];
  }

  /**
   * Insert a test company directly into database
   */
  async insertCompany(companyData) {
    const { user_id, name, description = '' } = companyData;
    const result = await this.pool.query(
      `INSERT INTO companies (user_id, name, description) 
       VALUES ($1, $2, $3) 
       RETURNING id, user_id, name, description, created_at`,
      [user_id, name, description]
    );
    return result.rows[0];
  }

  /**
   * Insert a test agent directly into database
   */
  async insertAgent(agentData) {
    const {
      company_id,
      agent_id,
      name,
      role = null,
      description = null,
      system_prompt = null,
      model = 'gemma4:26b',
      provider = 'local',
    } = agentData;

    const result = await this.pool.query(
      `INSERT INTO agents (company_id, agent_id, name, role, description, system_prompt, model, provider) 
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8) 
       RETURNING *`,
      [company_id, agent_id, name, role, description, system_prompt, model, provider]
    );
    return result.rows[0];
  }

  /**
   * Get user by email
   */
  async getUserByEmail(email) {
    const result = await this.pool.query(
      'SELECT * FROM users WHERE email = $1',
      [email]
    );
    return result.rows[0] || null;
  }

  /**
   * Get company by ID
   */
  async getCompanyById(companyId) {
    const result = await this.pool.query(
      'SELECT * FROM companies WHERE id = $1',
      [companyId]
    );
    return result.rows[0] || null;
  }

  /**
   * Get agents by company ID
   */
  async getAgentsByCompanyId(companyId) {
    const result = await this.pool.query(
      'SELECT * FROM agents WHERE company_id = $1',
      [companyId]
    );
    return result.rows;
  }

  /**
   * Check if user has access to specific company
   */
  async userHasAccessToCompany(userId, companyId) {
    const result = await this.pool.query(
      'SELECT 1 FROM companies WHERE id = $1 AND user_id = $2',
      [companyId, userId]
    );
    return result.rows.length > 0;
  }

  /**
   * Check if agent belongs to company
   */
  async agentBelongsToCompany(agentId, companyId) {
    const result = await this.pool.query(
      'SELECT 1 FROM agents WHERE id = $1 AND company_id = $2',
      [agentId, companyId]
    );
    return result.rows.length > 0;
  }

  /**
   * Close database connection
   */
  async close() {
    await this.pool.end();
  }
}

export default DatabaseHelper;