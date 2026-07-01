#!/usr/bin/env node

/**
 * Webhooks Benchmark
 * 
 * Benchmarks the webhook endpoints including:
 * - POST /webhooks/inbox - Inbound webhook processing
 * - HMAC signature validation
 * 
 * Tests webhook handler performance under load.
 * 
 * ⚠️ WARNING: This benchmark sends webhooks with HMAC signatures.
 * Ensure you're testing against a staging environment.
 */

import autocannon from 'autocannon';
import crypto from 'crypto';
import { parseAutocannonResult, printResults, checkThresholds } from '../lib/results.js';
import { defaultSettings, thresholds } from '../config/env.example.js';

const BENCHMARK_NAME = 'Webhook Endpoints';

/**
 * Generate HMAC-SHA256 signature for webhook payload
 */
function generateHmacSignature(payload, secret = 'test-webhook-secret') {
  return crypto
    .createHmac('sha256', secret)
    .update(JSON.stringify(payload))
    .digest('hex');
}

/**
 * Generate a test webhook payload
 */
function generateWebhookPayload(index = 0) {
  return {
    event: 'test.event',
    timestamp: new Date().toISOString(),
    data: {
      id: `bench-${Date.now()}-${index}`,
      type: 'benchmark_test',
      source: 'autocannon-load-test'
    }
  };
}

async function runWebhooksBenchmark(baseUrl = 'http://localhost:3200') {
  const webhookUrl = `${baseUrl}/webhooks/inbox`;
  const secret = process.env.WEBHOOK_SECRET || 'test-webhook-secret';
  
  // Pre-generate a test payload and signature
  const payload = generateWebhookPayload();
  const signature = generateHmacSignature(payload, secret);

  console.log(`\n🚀 Starting ${BENCHMARK_NAME} Benchmark`);
  console.log(`   Target: ${webhookUrl}`);
  console.log(`   Duration: ${defaultSettings.duration}s`);
  console.log(`   Connections: ${defaultSettings.connections}\n`);

  try {
    const result = await autocannon({
      url: webhookUrl,
      duration: defaultSettings.duration,
      connections: defaultSettings.connections,
      pipelining: defaultSettings.pipelining,
      timeout: defaultSettings.timeout,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Webhook-Signature': signature
      },
      body: JSON.stringify(payload)
    });

    const parsed = parseAutocannonResult(result);
    printResults(BENCHMARK_NAME, parsed);
    
    const checks = checkThresholds(parsed, thresholds);
    console.log('\n✅ Threshold Checks:');
    console.log(`   p50 Latency: ${checks.latency.p50.value}ms (threshold: ${checks.latency.p50.threshold}ms) - ${checks.latency.p50.passed ? '✅ PASS' : '❌ FAIL'}`);
    console.log(`   p95 Latency: ${checks.latency.p95.value}ms (threshold: ${checks.latency.p95.threshold}ms) - ${checks.latency.p95.passed ? '✅ PASS' : '❌ FAIL'}`);
    console.log(`   Error Rate:  ${checks.errorRate.value} (threshold: ${checks.errorRate.threshold}) - ${checks.errorRate.passed ? '✅ PASS' : '❌ FAIL'}`);

    console.log('\n📝 Note: HMAC signature validation adds overhead to this test.');
    console.log('   The webhook secret must match the server configuration.\n');

    return { name: BENCHMARK_NAME, result: parsed, checks, passed: Object.values(checks).flatMap(v => Object.values(v)).every(c => c.passed) };
  } catch (error) {
    console.error(`❌ Benchmark failed: ${error.message}`);
    throw error;
  }
}

// Run if executed directly
const baseUrl = process.argv[2] || 'http://localhost:3200';
runWebhooksBenchmark(baseUrl).catch(process.exit(1));
