"""Benchmark tests for Activity Log service.

Benchmarks:
- Event write latency
- Event read latency
- Concurrent write throughput

SLO Targets (from 09_PERFORMANCE_BENCHMARK.md):
- Write latency: p50 < 5ms, p95 < 50ms
- Read latency: p50 < 10ms, p95 < 100ms
- Throughput: > 1000 writes/s
"""

import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from fastapi.testclient import TestClient


@pytest.fixture
def temp_log_path(tmp_path, monkeypatch):
    """Create a temporary log path for each test."""
    log_file = tmp_path / "activity_log.jsonl"
    monkeypatch.setattr(
        "tenants.legal.services.activity_log_service.main.LOG_PATH",
        str(log_file)
    )
    return log_file


class TestBenchmarkActivityLogService:
    """Benchmark suite for Activity Log service operations."""
    
    def test_write_event_latency(self, temp_log_path):
        """Benchmark event write latency."""
        from tenants.legal.services.activity_log_service import main
        
        # Warm up
        main.create_event(main.EventIn(
            event_type="test",
            urgency="low",
            summary="warmup"
        ))
        
        # Benchmark
        times = []
        for _ in range(1000):
            start = time.perf_counter()
            main.create_event(main.EventIn(
                event_type="email_sent",
                urgency="low",
                summary="test email"
            ))
            elapsed = (time.perf_counter() - start) * 1000  # ms
            times.append(elapsed)
        
        times.sort()
        p50 = times[499]  # 50th percentile
        p95 = times[949]  # 95th percentile
        
        print("\nWrite Event Latency:")
        print(f"  p50: {p50:.3f}ms (target: <5ms)")
        print(f"  p95: {p95:.3f}ms (target: <50ms)")
        
        # SLO assertions
        assert p50 < 5, f"p50 latency {p50:.3f}ms exceeds target of 5ms"
        assert p95 < 50, f"p95 latency {p95:.3f}ms exceeds target of 50ms"
    
    def test_read_events_latency(self, temp_log_path):
        """Benchmark event read latency (get_todays_events)."""
        from tenants.legal.services.activity_log_service import main
        
        # Create some events first
        for i in range(100):
            main.create_event(main.EventIn(
                event_type="test_event",
                urgency="medium",
                summary=f"Test event {i}"
            ))
        
        # Warm up
        main.get_todays_events()
        
        # Benchmark
        times = []
        for _ in range(500):
            start = time.perf_counter()
            main.get_todays_events()
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        
        times.sort()
        p50 = times[249]
        p95 = times[474]
        
        print("\nRead Events Latency (100 events):")
        print(f"  p50: {p50:.3f}ms (target: <10ms)")
        print(f"  p95: {p95:.3f}ms (target: <100ms)")
        
        # SLO assertions
        assert p50 < 10, f"p50 latency {p50:.3f}ms exceeds target of 10ms"
        assert p95 < 100, f"p95 latency {p95:.3f}ms exceeds target of 100ms"
    
    def test_concurrent_write_throughput(self, temp_log_path):
        """Benchmark concurrent write throughput."""
        from tenants.legal.services.activity_log_service import main
        
        def write_once(i):
            return main.create_event(main.EventIn(
                event_type="concurrent_test",
                urgency="low",
                summary=f"Concurrent event {i}"
            ))
        
        # Warm up
        write_once(0)
        
        # Benchmark concurrent writes
        start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=8) as executor:
            list(executor.map(write_once, range(5000)))
        total_time = time.perf_counter() - start
        
        throughput = 5000 / total_time
        
        print("\nConcurrent Write Throughput (8 threads):")
        print(f"  Total time for 5000 writes: {total_time:.2f}s")
        print(f"  Throughput: {throughput:.2f} writes/s (target: >1000/s)")
        
        # SLO assertion
        assert throughput > 1000, f"Throughput {throughput:.2f} writes/s below target of 1000"
    
    def test_large_log_read_scaling(self, temp_log_path):
        """Benchmark how read latency scales with log size."""
        from tenants.legal.services.activity_log_service import main
        
        for log_size in [100, 1000, 10000]:
            # Pre-populate log
            temp_log_path.unlink(missing_ok=True)
            with open(temp_log_path, "w") as f:
                for i in range(log_size):
                    record = {
                        "type": "scaled_test",
                        "urgency": "low",
                        "summary": f"Event {i}",
                        "timestamp": "2020-01-01T00:00:00+00:00",  # All old events
                    }
                    f.write(json.dumps(record) + "\n")
            
            # Benchmark read
            times = []
            for _ in range(50):
                start = time.perf_counter()
                main.get_todays_events()
                elapsed = (time.perf_counter() - start) * 1000
                times.append(elapsed)
            
            times.sort()
            p50 = times[24]
            
            print(f"\nRead Scaling Test ({log_size} events):")
            print(f"  p50: {p50:.3f}ms")


def test_activity_log_service_health(temp_log_path):
    """Verify Activity Log service health endpoint."""
    from tenants.legal.services.activity_log_service import main
    
    client = TestClient(main.app)
    response = client.get("/health")
    
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
