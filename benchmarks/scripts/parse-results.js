#!/usr/bin/env node

/**
 * Benchmark Results Parser
 * 
 * Parses autocannon JSON output and generates formatted reports.
 * Usage: node scripts/parse-results.js < results.json
 */

import { parseAutocannonResult, checkThresholds, generateMarkdownReport } from '../lib/results.js';
import { thresholds } from '../config/env.example.js';
import { readFileSync } from 'fs';

function main() {
  const args = process.argv.slice(2);
  
  if (args.length === 0) {
    // Try to read from stdin
    let input = '';
    process.stdin.on('data', chunk => input += chunk);
    process.stdin.on('end', () => {
      if (input) {
        const result = JSON.parse(input);
        const parsed = parseAutocannonResult(result);
        const checks = checkThresholds(parsed, thresholds);
        console.log(JSON.stringify({ parsed, checks }, null, 2));
      } else {
        printUsage();
      }
    });
  } else if (args[0] === '--help' || args[0] === '-h') {
    printUsage();
  } else if (args[0] === '--report') {
    // Generate markdown report from multiple result files
    const reportArgs = args.slice(1);
    const results = reportArgs.map(file => {
      const content = readFileSync(file, 'utf-8');
      const data = JSON.parse(content);
      const parsed = parseAutocannonResult(data);
      return { name: file.replace('.json', ''), result: parsed };
    });
    console.log(generateMarkdownReport(results, thresholds));
  } else {
    // Read from file
    const file = args[0];
    const content = readFileSync(file, 'utf-8');
    const result = JSON.parse(content);
    const parsed = parseAutocannonResult(result);
    const checks = checkThresholds(parsed, thresholds);
    
    console.log('\nParsed Results:');
    console.log(JSON.stringify(parsed, null, 2));
    
    console.log('\nThreshold Checks:');
    console.log(JSON.stringify(checks, null, 2));
  }
}

function printUsage() {
  console.log(`
Benchmark Results Parser

Usage:
  node scripts/parse-results.js < results.json    Parse JSON from stdin
  node scripts/parse-results.js results.json     Parse JSON from file
  node scripts/parse-results.js --report r1.json r2.json r3.json  Generate markdown report

Examples:
  # Run autocannon and save results
  autocannon -j http://localhost:3200/health > health.json
  
  # Parse the results
  node scripts/parse-results.js health.json
  
  # Generate comparison report
  node scripts/parse-results.js --report health.json metrics.json auth.json
  `);
}

main();
