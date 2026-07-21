#!/usr/bin/env node

/**
 * OpenClaw Benchmark
 * 
 * Benchmarks the OpenClaw multi-agent orchestrator endpoints.
 * Tests:
 * - GET /health - OpenClaw health check
 * - POST /api/agent/run - Agent execution
 * - POST /api/agent/delegate - Task delegation
 * - WebSocket connections for streaming responses
 * 
 * OpenClaw runs on port 18789 (Minisforum control plane).
 * 
 * ⚠️ WARNING: This benchmark triggers agent executions which may involve
 * LLM calls, tool invocations, and sandbox operations. Use staging environment.
 */

import autocannon from 'autocannon';
import crypto from 'crypto';
import { parseAutocannonResult, printResults, checkThresholds } from '../lib/results.js';
import { defaultSettings, thresholds } from '../config/env.example.js';

const BENCHMARK_NAME = 'OpenClaw';

/**
 * Generate test token for OpenClaw API
 */
function generateOpenClawToken() {
  const secret = process.env.OPENCLAW_TOKEN || 'test-openclaw-token';
  const payload = {
    sub: 'benchmark-agent',
    scope: 'agent:run',
    exp: Math.floor(Date.now() / 1000) + 3600
  };
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
 * Generate a stub agent task payload
 */
function generateAgentTask(index = 0) {
  return {
    task_id: `bench-task-${Date.now()}-${index}`,
    prompt: `Benchmark test task ${index}. Respond with "OK".`,
    model: 'stub-model',
    tools: [],
    max_steps: 3,
    stream: false
  };
}

/**
 * Generate delegation payload for multi-agent coordination
 */
function generateDelegationPayload() {
  return {
    delegation_id: `bench-delegation-${Date.now()}`,
    task: {
      type: 'coordinate',
      description: 'Benchmark coordination test',
      sub_agents: [
        { id: 'agent-1', role: 'researcher' },
        { id: 'agent-2', role: 'executor' }
      ]
    },
    coordination: {
      strategy: 'sequential',
      fallback: 'any_available'
    }
  };
}

/**
 * Run OpenClaw health endpoint benchmark
 */
async function runHealthBenchmark(openclawUrl) {
  const healthUrl = `${openclawUrl}/health`;
  
  console.log(`\n🔍 OpenClaw Health Benchmark`);
  console.log(`   Target: ${healthUrl}\n`);

  try {
    const result = await autocannon({
      url: healthUrl,
      duration: defaultSettings.duration,
      connections: defaultSettings.connections,
      pipelining: defaultSettings.pipelining,
      timeout: defaultSettings.timeout,
      method: 'GET'
    });

    const parsed = parseAutocannonResult(result);
    printResults('OpenClaw Health', parsed);
    
    return { name: 'OpenClaw Health', result: parsed };
  } catch (error) {
    console.error(`❌ Health benchmark failed: ${error.message}`);
    throw error;
  }
}

/**
 * Run OpenClaw agent execution benchmark
 */
async function runAgentBenchmark(openclawUrl) {
  const agentUrl = `${openclawUrl}/api/agent/run`;
  const token = generateOpenClawToken();
  const payload = generateAgentTask();
  
  console.log(`\n🤖 OpenClaw Agent Execution Benchmark`);
  console.log(`   Target: ${agentUrl}`);
  console.log(`   Duration: ${defaultSettings.duration}s`);
  console.log(`   Connections: ${defaultSettings.connections}\n`);

  try {
    const result = await autocannon({
      url: agentUrl,
      duration: defaultSettings.duration,
      connections: defaultSettings.connections,
      pipelining: 1, // Agent runs are typically sequential
      timeout: defaultSettings.timeout * 3, // Longer timeout for agent execution
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(payload)
    });

    const parsed = parseAutocannonResult(result);
    printResults('OpenClaw Agent Execution', parsed);
    
    const checks = checkThresholds(parsed, thresholds);
    console.log('\n✅ Threshold Checks:');
    console.log(`   p50 Latency: ${checks.latency.p50.value}ms (threshold: ${checks.latency.p50.threshold}ms) - ${checks.latency.p50.passed ? '✅ PASS' : '❌ FAIL'}`);
    console.log(`   p95 Latency: ${checks.latency.p95.value}ms (threshold: ${checks.latency.p95.threshold}ms) - ${checks.latency.p95.passed ? '✅ PASS' : '❌ FAIL'}`);
    console.log(`   Error Rate:  ${checks.errorRate.value} (threshold: ${checks.errorRate.threshold}) - ${checks.errorRate.passed ? '✅ PASS' : '❌ FAIL'}`);

    console.log('\n📝 Note: Agent execution benchmarks typically show higher latency');
    console.log('   due to LLM inference and tool execution overhead.\n');

    return { name: 'OpenClaw Agent Execution', result: parsed, checks };
  } catch (error) {
    console.error(`❌ Agent benchmark failed: ${error.message}`);
    throw error;
  }
}

/**
 * Run OpenClaw delegation benchmark (multi-agent coordination)
 */
async function runDelegationBenchmark(openclawUrl) {
  const delegateUrl = `${openclawUrl}/api/agent/delegate`;
  const token = generateOpenClawToken();
  const payload = generateDelegationPayload();
  
  console.log(`\n🔄 OpenClaw Delegation Benchmark`);
  console.log(`   Target: ${delegateUrl}`);
  console.log(`   Duration: ${defaultSettings.duration}s`);
  console.log(`   Connections: ${defaultSettings.connections}\n`);

  try {
    const result = await autocannon({
      url: delegateUrl,
      duration: defaultSettings.duration,
      connections: defaultSettings.connections,
      pipelining: 1,
      timeout: defaultSettings.timeout * 5, // Longer timeout for delegation
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(payload)
    });

    const parsed = parseAutocannonResult(result);
    printResults('OpenClaw Delegation', parsed);
    
    return { name: 'OpenClaw Delegation', result: parsed };
  } catch (error) {
    console.error(`❌ Delegation benchmark failed: ${error.message}`);
    throw error;
  }
}

/**
 * Main benchmark runner
 */
async function runOpenClawBenchmark(openclawUrl = 'http://localhost:18789', mode = 'all') {
  console.log('='.repeat(60));
  console.log('OpenClaw Performance Benchmark Suite');
  console.log('='.repeat(60));
  console.log(`\n⚠️  WARNING: These benchmarks trigger actual agent executions.`);
  console.log(`   Use only in STAGING environments, not production.\n`);

  const results = [];

  if (mode === 'all' || mode === 'health') {
    results.push(await runHealthBenchmark(openclawUrl));
  }
  
  if (mode === 'all' || mode === 'agent') {
    results.push(await runAgentBenchmark(openclawUrl));
  }
  
  if (mode === 'all' || mode === 'delegate') {
    results.push(await runDelegationBenchmark(openclawUrl));
  }

  console.log('\n' + '='.repeat(60));
  console.log('Benchmark Summary');
  console.log('='.repeat(60));
  
  for (const result of results) {
    const rps = (result.result.requests.total / result.result.summary.duration).toFixed(2);
    console.log(`\n${result.name}:`);
    console.log(`  p50: ${result.result.latency.p50}ms | p95: ${result.result.latency.p95}ms | RPS: ${rps} | Errors: ${result.result.errors.rate}`);
  }

  return results;
}

// Parse command line args
const openclawUrl = process.argv[2] || 'http://localhost:18789';
const mode = process.argv[3] || 'all';

// Run benchmark
runOpenClawBenchmark(openclawUrl, mode).catch(process.exit(1));
