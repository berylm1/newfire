"""Benchmark tests for Conflicts service.

Benchmarks:
- Conflict check latency (single party)
- Batch conflict check latency
- Database size scaling

SLO Targets (from 09_PERFORMANCE_BENCHMARK.md):
- Check latency: p50 < 10ms, p95 < 100ms
- Throughput: > 500 checks/s
"""

import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from fastapi.testclient import TestClient
from tenants.legal.services.conflicts_service import main


class TestBenchmarkConflictsService:
    """Benchmark suite for Conflicts service operations."""
    
    def test_check_single_party_latency(self):
        """Benchmark conflict check latency for single party name."""
        # Warm up
        main.check_conflicts(main.CheckRequest(party_names=["Marcus Whitfield"]))
        
        # Benchmark
        times = []
        for _ in range(1000):
            start = time.perf_counter()
            main.check_conflicts(main.CheckRequest(party_names=["Marcus Whitfield"]))
            elapsed = (time.perf_counter() - start) * 1000  # ms
            times.append(elapsed)
        
        times.sort()
        p50 = times[499]  # 50th percentile
        p95 = times[949]  # 95th percentile
        
        print("\nSingle Party Check Latency:")
        print(f"  p50: {p50:.3f}ms (target: <10ms)")
        print(f"  p95: {p95:.3f}ms (target: <100ms)")
        
        # SLO assertions
        assert p50 < 10, f"p50 latency {p50:.3f}ms exceeds target of 10ms"
        assert p95 < 100, f"p95 latency {p95:.3f}ms exceeds target of 100ms"
    
    def test_check_batch_party_latency(self):
        """Benchmark conflict check latency for multiple party names."""
        party_names = [
            "Marcus Whitfield",
            "Greenline Logistics",
            "Dana Okafor",
            "Unknown Person",
            "Another Unknown",
        ]
        
        # Warm up
        main.check_conflicts(main.CheckRequest(party_names=party_names[:2]))
        
        # Benchmark
        times = []
        for _ in range(500):
            start = time.perf_counter()
            main.check_conflicts(main.CheckRequest(party_names=party_names))
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        
        times.sort()
        p50 = times[249]
        p95 = times[474]
        
        print("\nBatch Check Latency (5 parties):")
        print(f"  p50: {p50:.3f}ms (target: <50ms)")
        print(f"  p95: {p95:.3f}ms (target: <200ms)")
        
        # Target: < 50ms for 5 parties
        assert p50 < 50, f"p50 latency {p50:.3f}ms exceeds target of 50ms"
        assert p95 < 200, f"p95 latency {p95:.3f}ms exceeds target of 200ms"
    
    def test_check_scaling_with_db_size(self):
        """Benchmark how check latency scales with database size."""
        # Current database has 3 entries
        # Test with synthetic larger datasets
        
        party_names = ["Marcus Whitfield", "Greenline Logistics"]
        
        # Simulate larger database
        original_db = main.SYNTHETIC_CONFLICTS_DB.copy()
        
        for multiplier in [1, 10, 100]:
            # Expand database
            main.SYNTHETIC_CONFLICTS_DB = original_db.copy()
            for i in range((multiplier - 1) * 3):
                main.SYNTHETIC_CONFLICTS_DB.append({
                    "name": f"Person {i}",
                    "role": "unknown",
                    "matter": "test matter",
                })
            
            # Benchmark
            times = []
            for _ in range(100):
                start = time.perf_counter()
                main.check_conflicts(main.CheckRequest(party_names=party_names))
                elapsed = (time.perf_counter() - start) * 1000
                times.append(elapsed)
            
            times.sort()
            p50 = times[49]
            
            print(f"\nScaling Test ({len(main.SYNTHETIC_CONFLICTS_DB)} entries):")
            print(f"  p50: {p50:.3f}ms")
            
            # Restore
            main.SYNTHETIC_CONFLICTS_DB = original_db.copy()
    
    def test_concurrent_throughput(self):
        """Benchmark concurrent check throughput."""
        party_names = [
            "Marcus Whitfield",
            "Greenline Logistics",
            "Dana Okafor",
            "Unknown Person",
        ]
        
        def check_once():
            return main.check_conflicts(main.CheckRequest(party_names=party_names))
        
        # Warm up
        check_once()
        
        # Benchmark concurrent checks
        start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=8) as executor:
            list(executor.map(lambda _: check_once(), range(1000)))
        total_time = time.perf_counter() - start
        
        throughput = 1000 / total_time
        
        print("\nConcurrent Throughput (8 threads):")
        print(f"  Total time for 1000 checks: {total_time:.2f}s")
        print(f"  Throughput: {throughput:.2f} checks/s (target: >500/s)")
        
        # SLO assertion
        assert throughput > 500, f"Throughput {throughput:.2f} checks/s below target of 500"


def test_conflicts_service_health():
    """Verify Conflicts service health endpoint."""
    client = TestClient(main.app)
    response = client.get("/health")
    
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
