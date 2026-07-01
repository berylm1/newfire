#!/usr/bin/env node

/**
 * Chat API Benchmark
 * 
 * Benchmarks the chat/completion endpoints with mock/stub chat flows.
 * Tests:
 * - POST /chat - Main chat endpoint
 * - POST /completions - LLM completion endpoint
 * 
 * Uses stub responses when LLM backends are unavailable.
 * 
 * ⚠️ WARNING: This benchmark may trigger actual LLM calls if backend routing
 * is not configured to stub mode. Use staging with controlled LLM backends.
 */

import autocannon from 'autocannon';
import crypto from 'crypto';
import { parseAutocannonResult, printResults, checkThresholds } from '../lib/results.js';
import { defaultSettings, thresholds, default as envConfig } from '../config/env.example.js';

const BENCHMARK_NAME = 'Chat API';

/**
 * Generate a simple JWT for authentication
 */
function generateTestToken(payload, secret = 'test-jwt-secret') {
  const header = { alg: 'HS256', typ: 'JWT' };
  const encodedHeader = Buffer.from(JSON.stringify(header)).toString('base64url');
  const encodedPayload = Buffer.from(JSON.stringify(payload)).toString('base64url');
  const signature = crypto
    .createHmac('sha256', secret)
    .update(`${encodedHeader}.${encodedPayload}`)
    .digest('base64url');
  return `${encodedHeader}.${encodedPayload}.${signature}`;
}

/**
 * Generate a mock chat request payload
 */
function generateChatRequest(index = 0) {
  return {
    messages: [
      { role: 'system', content: 'You are a helpful assistant.' },
      { role: 'user', content: `Test message ${index}: What is 2+2?` }
    ],
    model: 'stub-model',
    max_tokens: 50,
    temperature: 0.7,
    stream: false
  };
}

async function runChatBenchmark(baseUrl = 'http://localhost:3200') {
  const chatUrl = `${baseUrl}/chat`;
  
  // Generate test token for auth
  const testToken = generateTestToken({ 
    sub: 'benchmark-user', 
    company_id: 'test-company',
    exp: Math.floor(Date.now() / 1000) + 3600 
  });

  // Generate test payload
  const payload = generateChatRequest();
  const payloadStr = JSON.stringify(payload);

  console.log(`\n🚀 Starting ${BENCHMARK_NAME} Benchmark`);
  console.log(`   Target: ${chatUrl}`);
  console.log(`   Duration: ${defaultSettings.duration}s`);
  console.log(`   Connections: ${defaultSettings.connections}`);
  console.log(`   Auth: JWT Bearer Token (test)\n`);

  try {
    const result = await autocannon({
      url: chatUrl,
      duration: defaultSettings.duration,
      connections: defaultSettings.connections,
      pipelining: defaultSettings.pipelining,
      timeout: defaultSettings.timeout,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${testToken}`
      },
      body: payloadStr
    });

    const parsed = parseAutocannonResult(result);
    printResults(BENCHMARK_NAME, parsed);
    
    const checks = checkThresholds(parsed, thresholds);
    console.log('\n✅ Threshold Checks:');
    console.log(`   p50 Latency: ${checks.latency.p50.value}ms (threshold: ${checks.latency.p50.threshold}ms) - ${checks.latency.p50.passed ? '✅ PASS' : '❌ FAIL'}`);
    console.log(`   p95 Latency: ${checks.latency.p95.value}ms (threshold: ${checks.latency.p95.threshold}ms) - ${checks.latency.p95.passed ? '✅ PASS' : '❌ FAIL'}`);
    console.log(`   Error Rate:  ${checks.errorRate.value} (threshold: ${checks.errorRate.threshold}) - ${checks.errorRate.passed ? '✅ PASS' : '❌ FAIL'}`);

    console.log('\n📝 Note: Chat endpoints typically have higher latency than simple API calls.');
    console.log('   This is expected when LLM inference is involved.\n');

    return { name: BENCHMARK_NAME, result: parsed, checks, passed: Object.values(checks).flatMap(v => Object.values(v)).every(c => c.passed) };
  } catch (error) {
    console.error(`❌ Benchmark failed: ${error.message}`);
    throw error;
  }
}

/**
 * Alternative benchmark: Test with SSE streaming (chat completions)
 */
async function runStreamingBenchmark(baseUrl = 'http://localhost:3200') {
  const completionsUrl = `${baseUrl}/v1/chat/completions`;
  
  const testToken = generateTestToken({ 
    sub: 'benchmark-user', 
    company_id: 'test-company',
    exp: Math.floor(Date.now() / 1000) + 3600 
  });

  const payload = {
    model: 'stub-model',
    messages: [{ role: 'user', content: 'Hello' }],
    stream: true
  };

  console.log(`\n🚀 Starting Streaming Chat Benchmark`);
  console.log(`   Target: ${completionsUrl}`);
  console.log(`   Note: Streaming responses may have different performance characteristics\n`);

  try {
    const result = await autocannon({
      url: completionsUrl,
      duration: defaultSettings.duration,
      connections: defaultSettings.connections,
      pipelining: 1, // Streaming doesn't benefit from pipelining
      timeout: defaultSettings.timeout * 2, // Double timeout for streaming
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${testToken}`
      },
      body: JSON.stringify(payload)
    });

    const parsed = parseAutocannonResult(result);
    printResults('Streaming Chat', parsed);
    
    return { name: 'Streaming Chat', result: parsed };
  } catch (error) {
    console.error(`❌ Streaming benchmark failed: ${error.message}`);
    throw error;
  }
}

// Run if executed directly
const baseUrl = process.argv[2] || 'http://localhost:3200';
const mode = process.argv[3] || 'chat';

if (mode === 'streaming') {
  runStreamingBenchmark(baseUrl).catch(process.exit(1));
} else {
  runChatBenchmark(baseUrl).catch(process.exit(1));
}
