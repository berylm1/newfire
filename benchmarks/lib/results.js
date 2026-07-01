/**
 * Benchmark Results Parser and Formatter
 * 
 * Provides utilities for parsing autocannon output and generating reports.
 */

/**
 * Parse autocannon result into structured data
 */
export function parseAutocannonResult(result) {
  if (!result || typeof result !== 'object') {
    throw new Error('Invalid autocannon result');
  }

  const {
    requests = {},
    latency = {},
    throughput = {},
    errors = 0,
    non2xx = 0,
    duration,
    connections,
    pipelining
  } = result;

  const totalRequests = requests.total || 0;
  const errorCount = errors + non2xx;
  const errorRate = totalRequests > 0 ? (errorCount / totalRequests) * 100 : 0;

  return {
    summary: {
      duration,
      connections,
      pipelining,
      totalRequests,
      errorCount,
      errorRate: errorRate.toFixed(2) + '%',
      throughput: formatThroughput(throughput)
    },
    latency: {
      p50: latency.p50 || 0,
      p75: latency.p75 || 0,
      p90: latency.p90 || 0,
      p95: latency.p95 || 0,
      p99: latency.p99 || 0,
      p999: latency.p999 || 0,
      mean: latency.mean || 0,
      stdDev: latency.stddev || 0,
      min: latency.min || 0,
      max: latency.max || 0
    },
    requests: {
      total: totalRequests,
      average: requests.average || 0,
      mean: requests.mean || 0
    },
    errors: {
      count: errorCount,
      rate: errorRate.toFixed(2) + '%'
    }
  };
}

/**
 * Format throughput value
 */
function formatThroughput(throughput) {
  if (!throughput || !throughput.average) return '0 B/s';
  
  const bytes = throughput.average;
  if (bytes >= 1000000000) {
    return (bytes / 1000000000).toFixed(2) + ' GB/s';
  } else if (bytes >= 1000000) {
    return (bytes / 1000000).toFixed(2) + ' MB/s';
  } else if (bytes >= 1000) {
    return (bytes / 1000).toFixed(2) + ' KB/s';
  }
  return bytes.toFixed(2) + ' B/s';
}

/**
 * Check if results meet thresholds
 */
export function checkThresholds(result, thresholds) {
  const checks = {
    latency: {},
    errorRate: {},
    rps: {}
  };

  // Latency checks
  const { latency } = result;
  checks.latency.p50 = {
    value: latency.p50,
    threshold: thresholds.latency.p50,
    passed: latency.p50 <= thresholds.latency.p50
  };
  checks.latency.p95 = {
    value: latency.p95,
    threshold: thresholds.latency.p95,
    passed: latency.p95 <= thresholds.latency.p95
  };
  checks.latency.p99 = {
    value: latency.p99,
    threshold: thresholds.latency.p99,
    passed: latency.p99 <= thresholds.latency.p99
  };

  // Error rate check
  const errorRate = parseFloat(result.errors.rate);
  checks.errorRate = {
    value: result.errors.rate,
    threshold: `${thresholds.errorRate}%`,
    passed: errorRate <= thresholds.errorRate
  };

  // RPS check (calculated from total requests / duration)
  const rps = result.requests.total / result.summary.duration;
  checks.rps = {
    value: rps.toFixed(2),
    threshold: thresholds.rps,
    passed: rps >= thresholds.rps
  };

  return checks;
}

/**
 * Format results as markdown table row
 */
export function formatMarkdownRow(benchmarkName, result) {
  const { latency, errors, summary } = result;
  const rps = (result.requests.total / summary.duration).toFixed(2);
  
  return `| ${benchmarkName} | ${latency.p50}ms | ${latency.p95}ms | ${rps} | ${errors.rate} |`;
}

/**
 * Generate markdown report
 */
export function generateMarkdownReport(results, thresholds) {
  const rows = results.map(r => formatMarkdownRow(r.name, r.result));
  const checks = results.map(r => ({
    name: r.name,
    checks: checkThresholds(r.result, thresholds)
  }));

  let report = `# Benchmark Results\n\n`;
  report += `Generated: ${new Date().toISOString()}\n\n`;
  
  report += `## Summary Table\n\n`;
  report += `| Benchmark | p50 Latency | p95 Latency | RPS | Error Rate |\n`;
  report += `|-----------|-------------|-------------|-----|------------|\n`;
  report += rows.join('\n');
  report += '\n\n';

  report += `## Threshold Checks\n\n`;
  report += `| Benchmark | Metric | Value | Threshold | Status |\n`;
  report += `|-----------|--------|-------|-----------|--------|\n`;

  for (const check of checks) {
    for (const [metric, data] of Object.entries(check.checks)) {
      const status = data.passed ? '✅ PASS' : '❌ FAIL';
      report += `| ${check.name} | ${metric} | ${data.value} | ${data.threshold} | ${status} |\n`;
    }
  }

  return report;
}

/**
 * Print human-readable results
 */
export function printResults(benchmarkName, result) {
  console.log(`\n${'='.repeat(60)}`);
  console.log(`Benchmark: ${benchmarkName}`);
  console.log('='.repeat(60));
  
  console.log('\n📊 Latency (ms):');
  console.log(`  p50:  ${result.latency.p50}ms`);
  console.log(`  p75:  ${result.latency.p75}ms`);
  console.log(`  p90:  ${result.latency.p90}ms`);
  console.log(`  p95:  ${result.latency.p95}ms`);
  console.log(`  p99:  ${result.latency.p99}ms`);
  console.log(`  p999: ${result.latency.p999}ms`);
  console.log(`  mean: ${result.latency.mean}ms`);
  
  console.log('\n📈 Requests:');
  console.log(`  Total:  ${result.requests.total}`);
  console.log(`  RPS:    ${(result.requests.total / result.summary.duration).toFixed(2)}`);
  
  console.log('\n⚠️  Errors:');
  console.log(`  Count:  ${result.errors.count}`);
  console.log(`  Rate:   ${result.errors.rate}`);
  
  console.log('\n📦 Throughput:', result.summary.throughput);
}
