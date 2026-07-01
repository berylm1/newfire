/**
 * Benchmark Environment Configuration
 * 
 * ⚠️ IMPORTANT: These benchmarks are for LOCAL/STAGING environments ONLY!
 * 
 * DO NOT run against production without explicit approval.
 * These scripts generate significant load and can impact production performance.
 */

// Environment presets
export const environments = {
  local: {
    name: 'Local Development',
    backendUrl: 'http://localhost:3200',
    openclawUrl: 'http://localhost:18789',
    openhandsUrl: 'http://localhost:3000',
    // Local environment - no auth required typically
    auth: {
      username: 'test@example.com',
      password: 'testpassword123'
    }
  },
  staging: {
    name: 'Staging Environment',
    backendUrl: process.env.STAGING_BACKEND_URL || 'https://staging.newfire.app/backend',
    openclawUrl: process.env.STAGING_OPENCLAW_URL || 'http://172.17.0.1:18789',
    openhandsUrl: process.env.STAGING_OPENHANDS_URL || 'http://172.17.0.1:3000',
    auth: {
      username: process.env.BENCHMARK_USER || 'benchmark@newfire.app',
      password: process.env.BENCHMARK_PASSWORD || ''
    }
  }
};

// Default benchmark settings
export const defaultSettings = {
  // Duration in seconds
  duration: 30,
  // Concurrent connections
  connections: 10,
  // Requests per second per connection
  pipelining: 1,
  // Number of warmup requests
  warmupRequests: 10,
  // Timeout in milliseconds
  timeout: 30000,
  // Reconnect interval
  reconnectInterval: 0,
  // Workers for parallel execution
  workers: 1
};

// Benchmark thresholds (for pass/fail reporting)
export const thresholds = {
  // Latency thresholds in milliseconds
  latency: {
    p50: 100,
    p95: 500,
    p99: 1000
  },
  // Error rate threshold (percentage)
  errorRate: 1.0,
  // Requests per second minimum
  rps: 50,
  // Throughput (bytes per second)
  throughput: 1000000
};

// Export current environment based on NODE_ENV
const env = process.env.BENCHMARK_ENV || 'local';
export default environments[env] || environments.local;
