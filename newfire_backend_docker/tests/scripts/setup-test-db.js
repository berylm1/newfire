/**
 * Setup Test Database Script
 * 
 * This script creates and initializes the test database for tenant/RBAC testing.
 * Run this before running tests to ensure the test database is properly set up.
 * 
 * Usage:
 *   node scripts/setup-test-db.js
 * 
 * Environment variables:
 *   TEST_DB_HOST - Database host (default: localhost)
 *   TEST_DB_PORT - Database port (default: 5432)
 *   TEST_DB_USER - Database user (default: postgres)
 *   TEST_DB_PASSWORD - Database password (default: postgres)
 *   TEST_DB_NAME - Database name (default: newfire_test)
 */

import pg from 'pg';
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const { Pool } = pg;

// Get database configuration from environment
const dbConfig = {
  host: process.env.TEST_DB_HOST || 'localhost',
  port: parseInt(process.env.TEST_DB_PORT || '5432'),
  user: process.env.TEST_DB_USER || 'postgres',
  password: process.env.TEST_DB_PASSWORD || 'postgres',
  database: process.env.TEST_DB_NAME || 'newfire_test',
};

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

/**
 * Create the test database if it doesn't exist
 */
async function createDatabaseIfNotExists() {
  // Connect to postgres database to create test database
  const adminPool = new Pool({
    ...dbConfig,
    database: 'postgres', // Connect to default postgres database
  });

  try {
    // Check if database exists
    const result = await adminPool.query(
      `SELECT 1 FROM pg_database WHERE datname = $1`,
      [dbConfig.database]
    );

    if (result.rows.length === 0) {
      console.log(`Creating database: ${dbConfig.database}`);
      await adminPool.query(`CREATE DATABASE ${dbConfig.database}`);
      console.log('Database created successfully');
    } else {
      console.log(`Database ${dbConfig.database} already exists`);
    }
  } finally {
    await adminPool.end();
  }
}

/**
 * Initialize database schema
 */
async function initializeSchema() {
  const pool = new Pool(dbConfig);

  try {
    // Read schema file
    const schemaPath = join(__dirname, '../helpers/schema.sql');
    const schema = readFileSync(schemaPath, 'utf-8');

    console.log('Initializing database schema...');
    await pool.query(schema);
    console.log('Schema initialized successfully');
  } finally {
    await pool.end();
  }
}

/**
 * Grant permissions (if needed)
 */
async function grantPermissions() {
  const pool = new Pool(dbConfig);

  try {
    // Grant necessary permissions
    await pool.query(`GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ${dbConfig.user}`);
    await pool.query(`GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ${dbConfig.user}`);
    console.log('Permissions granted');
  } finally {
    await pool.end();
  }
}

/**
 * Verify setup
 */
async function verifySetup() {
  const pool = new Pool(dbConfig);

  try {
    // Check tables exist
    const tables = await pool.query(`
      SELECT table_name 
      FROM information_schema.tables 
      WHERE table_schema = 'public'
    `);

    const expectedTables = ['users', 'companies', 'agents', 'conversations', 'client_notes'];
    const actualTables = tables.rows.map(r => r.table_name);

    console.log('\nVerification:');
    console.log(`Found tables: ${actualTables.join(', ')}`);

    const missing = expectedTables.filter(t => !actualTables.includes(t));
    if (missing.length > 0) {
      console.error(`Missing tables: ${missing.join(', ')}`);
      return false;
    }

    console.log('All expected tables found');
    return true;
  } finally {
    await pool.end();
  }
}

/**
 * Main setup function
 */
async function main() {
  console.log('='.repeat(50));
  console.log('NewFire Backend Test Database Setup');
  console.log('='.repeat(50));
  console.log(`Host: ${dbConfig.host}:${dbConfig.port}`);
  console.log(`Database: ${dbConfig.database}`);
  console.log(`User: ${dbConfig.user}`);
  console.log('');

  try {
    await createDatabaseIfNotExists();
    await initializeSchema();
    await grantPermissions();
    
    const success = await verifySetup();
    
    if (success) {
      console.log('\n' + '='.repeat(50));
      console.log('Test database setup complete!');
      console.log('='.repeat(50));
      console.log('\nYou can now run tests with:');
      console.log('  npm test');
      process.exit(0);
    } else {
      console.error('\nTest database setup failed verification');
      process.exit(1);
    }
  } catch (error) {
    console.error('\nError setting up test database:', error.message);
    console.error('Make sure PostgreSQL is running and you have permissions.');
    process.exit(1);
  }
}

main();