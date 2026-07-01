/**
 * Jest Configuration for NewFire Backend Tenant/RBAC Tests
 * 
 * This configuration enables ES modules support and sets up the test environment
 */

export default {
  // Test environment
  testEnvironment: 'node',
  
  // Enable ES modules support
  transform: {},
  
  // Module file extensions
  moduleFileExtensions: ['js', 'json'],
  
  // Test patterns
  testMatch: ['**/tests/**/*.test.js'],
  
  // Coverage collection
  collectCoverageFrom: [
    'src/**/*.js',
    '!src/**/*.test.js',
    '!**/node_modules/**',
  ],
  
  // Setup files
  setupFilesAfterEnv: ['./tests/setup.js'],
  
  // Test timeout (30 seconds for integration tests)
  testTimeout: 30000,
  
  // Verbose output
  verbose: true,
  
  // Run tests in random order to catch hidden dependencies
  randomize: true,
  
  // Force exit after tests complete (for databases/connections)
  forceExit: true,
  
  // Clear mocks between tests
  clearMocks: true,
  
  // Detect open handles (for debugging)
  detectOpenHandles: true,
  
  // Report test results
  reporters: [
    'default',
    ['jest-junit', {
      outputDirectory: 'test-results',
      outputName: 'results.xml',
      classNameTemplate: '{classname}',
      titleTemplate: '{title}',
      ancestorSeparator: ' > ',
      usePathForSuiteName: true,
    }],
  ],
};