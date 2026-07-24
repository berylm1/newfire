"""Locust load testing file for NewFire backend.

Run with:
    locust -f tests/benchmarks/locustfile.py --host=http://localhost:3200

For headless mode:
    locust -f tests/benchmarks/locustfile.py --host=http://localhost:3200 \
        --headless -u 100 -r 10 -t 60s --csv=benchmark_results
"""

import random
import time
from locust import HttpUser, task, between, events


class BackendUser(HttpUser):
    """Simulates a user interacting with the NewFire backend."""
    
    wait_time = between(0.5, 2)
    
    def on_start(self):
        """Called when a simulated user starts."""
        # Simple health check
        self.client.get("/backend/health")
    
    @task(3)
    def chat_completion(self):
        """Simulate a chat completion request (most common operation)."""
        start = time.perf_counter()
        
        # Mock chat request
        payload = {
            "model": "qwen3-coder-30b",
            "messages": [
                {"role": "user", "content": "Write a simple hello world function"}
            ],
            "stream": False,
        }
        
        with self.client.post(
            "/backend/chat/completions",
            json=payload,
            catch_response=True,
            name="/chat/completions"
        ) as response:
            elapsed = (time.perf_counter() - start) * 1000
            
            if response.elapsed.total_seconds() > 10:
                response.failure(f"Too slow: {elapsed:.0f}ms")
            elif response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status {response.status_code}")
    
    @task(2)
    def rag_search(self):
        """Simulate a RAG search request."""
        start = time.perf_counter()
        
        payload = {
            "query": "contract law agreements",
            "top_k": 5,
        }
        
        with self.client.post(
            "/backend/rag/search",
            json=payload,
            catch_response=True,
            name="/rag/search"
        ) as response:
            elapsed = (time.perf_counter() - start) * 1000
            
            if elapsed > 500:
                response.failure(f"Too slow: {elapsed:.0f}ms")
            elif response.status_code in [200, 404]:  # 404 ok if not implemented
                response.success()
            else:
                response.failure(f"Got status {response.status_code}")
    
    @task(1)
    def conflicts_check(self):
        """Simulate a conflicts check request."""
        start = time.perf_counter()
        
        party_names = [
            random.choice([
                "Marcus Whitfield",
                "Greenline Logistics",
                "Dana Okafor",
                "Unknown Person",
            ])
        ]
        
        payload = {
            "party_names": party_names,
        }
        
        with self.client.post(
            "/backend/conflicts/check",
            json=payload,
            catch_response=True,
            name="/conflicts/check"
        ) as response:
            elapsed = (time.perf_counter() - start) * 1000
            
            if elapsed > 100:
                response.failure(f"Too slow: {elapsed:.0f}ms")
            elif response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Got status {response.status_code}")
    
    @task(1)
    def activity_log_write(self):
        """Simulate an activity log write."""
        start = time.perf_counter()
        
        payload = {
            "event_type": random.choice(["email_sent", "call", "meeting"]),
            "urgency": random.choice(["low", "medium", "high"]),
            "summary": f"Test event {random.randint(1, 1000)}",
        }
        
        with self.client.post(
            "/backend/activity/events",
            json=payload,
            catch_response=True,
            name="/activity/events"
        ) as response:
            elapsed = (time.perf_counter() - start) * 1000
            
            if elapsed > 50:
                response.failure(f"Too slow: {elapsed:.0f}ms")
            elif response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Got status {response.status_code}")


class HeavyLoadUser(HttpUser):
    """Simulates heavy load for stress testing."""
    
    wait_time = between(0.1, 0.5)
    
    @task
    def rapid_chat_requests(self):
        """Send rapid chat requests to stress test."""
        payload = {
            "model": "qwen3-coder-30b",
            "messages": [{"role": "user", "content": "hi"}],
            "stream": False,
        }
        
        self.client.post("/backend/chat/completions", json=payload, name="stress_chat")


# Track metrics
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Log when test starts."""
    print(f"Load test starting with {environment.runner.user_count if hasattr(environment.runner, 'user_count') else 'N/A'} users")


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Track all requests for custom metrics."""
    pass


@events.quitting.add_listener
def on_quitting(environment, **kwargs):
    """Log summary when test ends."""
    if environment.stats.total.fail_ratio > 0.05:
        print(f"\n⚠️  WARNING: Failure rate {environment.stats.total.fail_ratio:.1%} exceeds 5% threshold")
    else:
        print(f"\n✅ Test completed with {environment.stats.total.fail_ratio:.1%} failure rate")
