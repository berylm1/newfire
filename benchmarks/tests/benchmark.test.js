/**
 * Benchmark Scripts Test Suite
 * 
 * Validates that benchmark scripts are correctly structured and importable.
 * These tests don't execute actual benchmarks but verify code structure.
 * 
 * Run with: node tests/benchmark.test.js
 */

import { readFileSync, existsSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const rootDir = resolve(__dirname, '..');

let passed = 0;
let failed = 0;

function test(name, fn) {
  try {
    fn();
    console.log(`  ✅ ${name}`);
    passed++;
  } catch (error) {
    console.log(`  ❌ ${name}`);
    console.log(`     Error: ${error.message}`);
    failed++;
  }
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message || 'Assertion failed');
  }
}

/**
 * Test that benchmark scripts exist and have correct structure
 */
function testScripts() {
  console.log('\n📁 Benchmark Scripts Structure');
  
  const scripts = [
    'health-benchmark.js',
    'metrics-benchmark.js',
    'auth-benchmark.js',
    'webhooks-benchmark.js',
    'chat-benchmark.js',
    'openclaw-benchmark.js',
    'parse-results.js'
  ];

  for (const script of scripts) {
    test(`${script} exists`, () => {
      const scriptPath = resolve(rootDir, 'scripts', script);
      assert(existsSync(scriptPath), `Script ${script} not found`);
    });

    test(`${script} has valid structure`, () => {
      const scriptPath = resolve(rootDir, 'scripts', script);
      const content = readFileSync(scriptPath, 'utf-8');
      
      // Check for shebang
      assert(content.includes('#!/usr/bin/env node'), 'Missing shebang');
      
      // Check for ES module syntax
      assert(content.includes('import '), 'Missing ES module imports');
      
      // Check for autocannon import (except parse-results)
      if (script !== 'parse-results.js') {
        assert(content.includes('autocannon'), 'Missing autocannon import');
      }
      
      // Check for either async function or regular function (parse-results uses main())
      assert(
        content.includes('async function') || 
        content.includes('async ()') ||
        content.includes('function main'),
        'Missing function definition'
      );
    });
  }
}

/**
 * Test lib modules
 */
function testLibrary() {
  console.log('\n📚 Library Modules');
  
  test('lib/results.js exists', () => {
    const path = resolve(rootDir, 'lib', 'results.js');
    assert(existsSync(path), 'lib/results.js not found');
  });

  test('parseAutocannonResult function exists', async () => {
    const { parseAutocannonResult } = await import('../lib/results.js');
    assert(typeof parseAutocannonResult === 'function', 'Function not exported');
  });

  test('checkThresholds function exists', async () => {
    const { checkThresholds } = await import('../lib/results.js');
    assert(typeof checkThresholds === 'function', 'Function not exported');
  });

  test('printResults function exists', async () => {
    const { printResults } = await import('../lib/results.js');
    assert(typeof printResults === 'function', 'Function not exported');
  });

  test('generateMarkdownReport function exists', async () => {
    const { generateMarkdownReport } = await import('../lib/results.js');
    assert(typeof generateMarkdownReport === 'function', 'Function not exported');
  });

  test('parseAutocannonResult correctly parses mock data', async () => {
    const { parseAutocannonResult } = await import('../lib/results.js');
    
    const mockResult = {
      requests: { total: 1000, average: 33.33, mean: 33.33 },
      latency: { p50: 10, p75: 15, p90: 20, p95: 25, p99: 30, p999: 40, mean: 12, stddev: 5, min: 1, max: 50 },
      throughput: { average: 1000000 },
      errors: 5,
      non2xx: 3,
      duration: 30,
      connections: 10,
      pipelining: 1
    };

    const parsed = parseAutocannonResult(mockResult);
    
    assert(parsed.latency.p50 === 10, 'p50 mismatch');
    assert(parsed.latency.p95 === 25, 'p95 mismatch');
    assert(parsed.latency.p99 === 30, 'p99 mismatch');
    assert(parsed.requests.total === 1000, 'Total requests mismatch');
    assert(parsed.errors.count === 8, 'Error count mismatch');
    assert(parsed.errors.rate === '0.80%', 'Error rate mismatch');
  });

  test('checkThresholds correctly validates against thresholds', async () => {
    const { parseAutocannonResult, checkThresholds } = await import('../lib/results.js');
    
    const mockResult = {
      requests: { total: 1000, average: 33.33, mean: 33.33 },
      latency: { p50: 10, p75: 15, p90: 20, p95: 25, p99: 30, p999: 40, mean: 12, stddev: 5, min: 1, max: 50 },
      throughput: { average: 1000000 },
      errors: 0,
      non2xx: 0,
      duration: 30,
      connections: 10,
      pipelining: 1
    };

    const thresholds = {
      latency: { p50: 100, p95: 500, p99: 1000 },
      errorRate: 1.0,
      rps: 50
    };

    const parsed = parseAutocannonResult(mockResult);
    const checks = checkThresholds(parsed, thresholds);

    assert(checks.latency.p50.passed === true, 'p50 threshold failed');
    assert(checks.latency.p95.passed === true, 'p95 threshold failed');
    assert(checks.latency.p99.passed === true, 'p99 threshold failed');
    assert(checks.errorRate.passed === true, 'error rate threshold failed');
  });
}

/**
 * Test configuration exports
 */
function testConfiguration() {
  console.log('\n⚙️  Configuration');
  
  test('config/env.example.js exists', () => {
    const path = resolve(rootDir, 'config', 'env.example.js');
    assert(existsSync(path), 'config/env.example.js not found');
  });

  test('environments configuration exports', async () => {
    const { environments } = await import('../config/env.example.js');
    
    assert(environments !== undefined, 'environments not exported');
    assert(environments.local !== undefined, 'local environment not defined');
    assert(environments.staging !== undefined, 'staging environment not defined');
    
    // Check local environment has required fields
    assert(environments.local.backendUrl !== undefined, 'backendUrl not defined');
    assert(environments.local.openclawUrl !== undefined, 'openclawUrl not defined');
  });

  test('defaultSettings exports', async () => {
    const { defaultSettings } = await import('../config/env.example.js');
    
    assert(defaultSettings !== undefined, 'defaultSettings not exported');
    assert(defaultSettings.duration === 30, 'duration mismatch');
    assert(defaultSettings.connections === 10, 'connections mismatch');
  });

  test('thresholds exports', async () => {
    const { thresholds } = await import('../config/env.example.js');
    
    assert(thresholds !== undefined, 'thresholds not exported');
    assert(thresholds.latency.p50 === 100, 'p50 threshold mismatch');
    assert(thresholds.latency.p95 === 500, 'p95 threshold mismatch');
    assert(thresholds.latency.p99 === 1000, 'p99 threshold mismatch');
    assert(thresholds.errorRate === 1.0, 'errorRate threshold mismatch');
  });
}

/**
 * Test package.json structure
 */
function testPackage() {
  console.log('\n📦 Package Configuration');
  
  test('package.json exists and valid', () => {
    const packagePath = resolve(rootDir, 'package.json');
    const pkg = JSON.parse(readFileSync(packagePath, 'utf-8'));
    
    assert(pkg.name === '@newfire/benchmarks', 'Package name mismatch');
    assert(pkg.type === 'module', 'type should be module');
    assert(pkg.dependencies.autocannon !== undefined, 'autocannon not in dependencies');
    assert(pkg.dependencies.axios !== undefined, 'axios not in dependencies');
  });

  test('package.json has benchmark scripts', () => {
    const packagePath = resolve(rootDir, 'package.json');
    const pkg = JSON.parse(readFileSync(packagePath, 'utf-8'));
    
    assert(pkg.scripts['benchmark:health'] !== undefined, 'benchmark:health not defined');
    assert(pkg.scripts['benchmark:metrics'] !== undefined, 'benchmark:metrics not defined');
    assert(pkg.scripts['benchmark:auth'] !== undefined, 'benchmark:auth not defined');
    assert(pkg.scripts['benchmark:webhooks'] !== undefined, 'benchmark:webhooks not defined');
    assert(pkg.scripts['benchmark:chat'] !== undefined, 'benchmark:chat not defined');
    assert(pkg.scripts['benchmark:openclaw'] !== undefined, 'benchmark:openclaw not defined');
    assert(pkg.scripts['benchmark:all'] !== undefined, 'benchmark:all not defined');
  });
}

/**
 * Test README documentation
 */
function testDocumentation() {
  console.log('\n📖 Documentation');
  
  test('README.md exists', () => {
    const readmePath = resolve(rootDir, 'README.md');
    assert(existsSync(readmePath), 'README.md not found');
  });

  test('README contains required sections', () => {
    const readmePath = resolve(rootDir, 'README.md');
    const content = readFileSync(readmePath, 'utf-8');
    
    assert(content.includes('# NewFire Benchmark Harness'), 'Missing title');
    assert(content.includes('Production Warning') || content.includes('⚠️'), 'Missing warning section');
    assert(content.includes('DO NOT RUN'), 'Missing production warning');
    assert(content.includes('p50') || content.includes('p50 Latency'), 'Missing p50 metric');
    assert(content.includes('p95') || content.includes('p95 Latency'), 'Missing p95 metric');
    assert(content.includes('Error Rate'), 'Missing error rate section');
  });

  test('README includes endpoints documentation', () => {
    const readmePath = resolve(rootDir, 'README.md');
    const content = readFileSync(readmePath, 'utf-8');
    
    assert(content.includes('/health'), 'Missing /health endpoint');
    assert(content.includes('/metrics'), 'Missing /metrics endpoint');
    assert(content.includes('/webhooks'), 'Missing /webhooks endpoint');
    assert(content.includes('OpenClaw'), 'Missing OpenClaw section');
  });
}

// Run all tests
console.log('='.repeat(60));
console.log('Benchmark Test Suite');
console.log('='.repeat(60));

testScripts();
testLibrary();
testConfiguration();
testPackage();
testDocumentation();

console.log('\n' + '='.repeat(60));
console.log(`Results: ${passed} passed, ${failed} failed`);
console.log('='.repeat(60));

if (failed > 0) {
  process.exit(1);
}
