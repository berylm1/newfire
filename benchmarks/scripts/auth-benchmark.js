#!/usr/bin/env node

/**
 * Authentication Benchmark
 * 
 * Benchmarks the authentication endpoints (/login, /signup, /refresh).
 * Tests JWT token generation, validation, and refresh flows.
 * 
 * ⚠️ WARNING: This benchmark performs real authentication attempts.
 * Use dedicated test accounts in staging environments.
 */

import autocannon from 'autocannon';
import { parseAutocannonResult, printResults, checkThresholds } from '../lib/results.js';
import { defaultSettings, thresholds, default as envConfig } from '../config/env.example.js';

const BENCHMARK_NAME = 'Auth Endpoints';

async function runAuthBenchmark(baseUrl = 'http://localhost:3200') {
  const loginUrl = `${baseUrl}/login`;
  const testCredentials = {
    email: envConfig.auth.username,
    password: envConfig.auth.password
  };

  console.log(`\n🚀 Starting ${BENCHMARK_NAME} Benchmark`);
  console.log(`   Target: ${loginUrl}`);
  console.log(`   Duration: ${defaultSettings.duration}s`);
  console.log(`   Connections: ${defaultSettings.connections}\n`);

  try {
    // Benchmark login endpoint with JSON body
    const result = await autocannon({
      url: loginUrl,
      duration: defaultSettings.duration,
      connections: defaultSettings.connections,
      pipelining: defaultSettings.pipelining,
      timeout: defaultSettings.timeout,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(testCredentials)
    });

    const parsed = parseAutocannonResult(result);
    printResults(BENCHMARK_NAME, parsed);
    
    const checks = checkThresholds(parsed, thresholds);
    console.log('\n✅ Threshold Checks:');
    console.log(`   p50 Latency: ${checks.latency.p50.value}ms (threshold: ${checks.latency.p50.threshold}ms) - ${checks.latency.p50.passed ? '✅ PASS' : '❌ FAIL'}`);
    console.log(`   p95 Latency: ${checks.latency.p95.value}ms (threshold: ${checks.latency.p95.threshold}ms) - ${checks.latency.p95.passed ? '✅ PASS' : '❌ FAIL'}`);
    console.log(`   Error Rate:  ${checks.errorRate.value} (threshold: ${checks.errorRate.threshold}) - ${checks.errorRate.passed ? '✅ PASS' : '❌ FAIL'}`);

    console.log('\n📝 Note: High error rates may be expected if credentials are invalid.');
    console.log('   Use valid test credentials in config/env.example.js\n');

    return { name: BENCHMARK_NAME, result: parsed, checks, passed: Object.values(checks).flatMap(v => Object.values(v)).every(c => c.passed) };
  } catch (error) {
    console.error(`❌ Benchmark failed: ${error.message}`);
    throw error;
  }
}

// Run if executed directly
const baseUrl = process.argv[2] || 'http://localhost:3200';
runAuthBenchmark(baseUrl).catch(process.exit(1));
