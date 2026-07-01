#!/usr/bin/env node

/**
 * Metrics Endpoint Benchmark
 * 
 * Benchmarks the /metrics endpoint of the NewFire backend.
 * This endpoint exposes Prometheus metrics and may involve database queries.
 * 
 * ⚠️ SAFE FOR PRODUCTION: Read-only endpoint, but use staging for load testing.
 */

import autocannon from 'autocannon';
import { parseAutocannonResult, printResults, checkThresholds } from '../lib/results.js';
import { defaultSettings, thresholds } from '../config/env.example.js';

const BENCHMARK_NAME = 'Metrics Endpoint';

async function runMetricsBenchmark(url = 'http://localhost:3200/metrics') {
  console.log(`\n🚀 Starting ${BENCHMARK_NAME} Benchmark`);
  console.log(`   Target: ${url}`);
  console.log(`   Duration: ${defaultSettings.duration}s`);
  console.log(`   Connections: ${defaultSettings.connections}\n`);

  try {
    const result = await autocannon({
      url,
      duration: defaultSettings.duration,
      connections: defaultSettings.connections,
      pipelining: defaultSettings.pipelining,
      timeout: defaultSettings.timeout,
      method: 'GET'
    });

    const parsed = parseAutocannonResult(result);
    printResults(BENCHMARK_NAME, parsed);
    
    const checks = checkThresholds(parsed, thresholds);
    console.log('\n✅ Threshold Checks:');
    console.log(`   p50 Latency: ${checks.latency.p50.value}ms (threshold: ${checks.latency.p50.threshold}ms) - ${checks.latency.p50.passed ? '✅ PASS' : '❌ FAIL'}`);
    console.log(`   p95 Latency: ${checks.latency.p95.value}ms (threshold: ${checks.latency.p95.threshold}ms) - ${checks.latency.p95.passed ? '✅ PASS' : '❌ FAIL'}`);
    console.log(`   Error Rate:  ${checks.errorRate.value} (threshold: ${checks.errorRate.threshold}) - ${checks.errorRate.passed ? '✅ PASS' : '❌ FAIL'}`);

    return { name: BENCHMARK_NAME, result: parsed, checks, passed: Object.values(checks).flatMap(v => Object.values(v)).every(c => c.passed) };
  } catch (error) {
    console.error(`❌ Benchmark failed: ${error.message}`);
    throw error;
  }
}

// Run if executed directly
const url = process.argv[2] || 'http://localhost:3200/metrics';
runMetricsBenchmark(url).catch(process.exit(1));
