/**
 * Teardown Test Database Script
 * 
 * This script cleans up the test database after running tenant/RBAC tests.
 * It drops all test data but keeps the database structure for future test runs.
 * 
 * Usage:
 *   node scripts/teardown-test-db.js
 * 
 * Environment variables:
 *   TEST_DB_HOST - Database host (default: localhost)
 *   TEST_DB_PORT - Database port (default: 5432)
 *   TEST_DB_USER - Database user (default: postgres)
 *   TEST_DB_PASSWORD - Database password (default: postgres)
 *   TEST_DB_NAME - Database name (default: newfire_test)
 */

import pg from 'pg';

const { Pool } = pg;

// Get database configuration from environment
const dbConfig = {
  host: process.env.TEST_DB_HOST || 'localhost',
  port: parseInt(process.env.TEST_DB_PORT || '5432'),
  user: process.env.TEST_DB_USER || 'postgres',
  password: process.env.TEST_DB_PASSWORD || 'postgres',
  database: process.env.TEST_DB_NAME || 'newfire_test',
};

/**
 * Clean all data from test tables
 */
async function cleanTables() {
  const pool = new Pool(dbConfig);

  try {
    console.log('Cleaning test data...');
    
    // Delete in order to respect foreign key constraints
    await pool.query('DELETE FROM client_notes');
    console.log('  - Cleaned client_notes');
    
    await pool.query('DELETE FROM conversations');
    console.log('  - Cleaned conversations');
    
    await pool.query('DELETE FROM agents');
    console.log('  - Cleaned agents');
    
    await pool.query('DELETE FROM companies');
    console.log('  - Cleaned companies');
    
    await pool.query('DELETE FROM users');
    console.log('  - Cleaned users');
    
    // Reset sequences
    await pool.query('SELECT setval(\'users_id_seq\', 1, false)');
    await pool.query('SELECT setval(\'companies_id_seq\', 1, false)');
    await pool.query('SELECT setval(\'agents_id_seq\', 1, false)');
    await pool.query('SELECT setval(\'conversations_id_seq\', 1, false)');
    await pool.query('SELECT setval(\'client_notes_id_seq\', 1, false)');
    console.log('  - Reset sequences');
    
    console.log('Test data cleaned successfully');
  } finally {
    await pool.end();
  }
}

/**
 * Drop the entire test database
 */
async function dropDatabase() {
  // Connect to postgres database to drop test database
  const adminPool = new Pool({
    ...dbConfig,
    database: 'postgres',
  });

  try {
    // Terminate existing connections to the database
    await adminPool.query(`
      SELECT pg_terminate_backend(pg_stat_activity.pid)
      FROM pg_stat_activity
      WHERE pg_stat_activity.datname = $1
        AND pid <> pg_backend_pid()
    `, [dbConfig.database]);

    console.log(`Dropping database: ${dbConfig.database}`);
    await adminPool.query(`DROP DATABASE IF EXISTS ${dbConfig.database}`);
    console.log('Database dropped successfully');
  } finally {
    await adminPool.end();
  }
}

/**
 * Main teardown function
 */
async function main() {
  const action = process.argv[2] || 'clean';

  console.log('='.repeat(50));
  console.log('NewFire Backend Test Database Teardown');
  console.log('='.repeat(50));
  console.log(`Host: ${dbConfig.host}:${dbConfig.port}`);
  console.log(`Database: ${dbConfig.database}`);
  console.log('');

  try {
    if (action === 'drop') {
      console.log('Mode: FULL TEARDOWN (drop database)');
      await dropDatabase();
    } else {
      console.log('Mode: CLEAN (remove test data only)');
      await cleanTables();
    }
    
    console.log('\n' + '='.repeat(50));
    console.log('Teardown complete!');
    console.log('='.repeat(50));
    process.exit(0);
  } catch (error) {
    console.error('\nError during teardown:', error.message);
    process.exit(1);
  }
}

main();