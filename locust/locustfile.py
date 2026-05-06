"""
Locust Load Testing Script
===========================
Simulates multiple concurrent users hitting the Chatbot API.

Usage:
  # Headless (CLI):
  locust -f locust/locustfile.py --host=http://localhost:5001 \
         --users 50 --spawn-rate 5 --run-time 60s --headless

  # Web UI (interactive):
  locust -f locust/locustfile.py --host=http://localhost:5001
  # Then open http://localhost:8089

Metrics captured:
  - Throughput (req/s)
  - Average / median / 95th-percentile response time
  - Failure rate
"""

import json
import random
from locust import HttpUser, task, between, events
from datetime import datetime


# ─── Sample messages for realistic load simulation ────────────────────────────

SAMPLE_MESSAGES = [
    "Hello! How are you?",
    "What can you help me with?",
    "Tell me a joke",
    "What's the weather like today?",
    "Can you help me with a question?",
    "What time is it?",
    "Goodbye, see you later!",
    "I need some assistance please",
    "How does this chatbot work?",
    "What topics can you discuss?",
]

EDGE_MESSAGES = [
    "A" * 500,                   # Large but valid
    "こんにちは",                   # Unicode
    "   Hello   ",               # Padded whitespace
    "1234567890",                # Numeric
    "!@#$%^&*()",                # Special characters
]


# ─── User behaviour classes ───────────────────────────────────────────────────

class RegularChatUser(HttpUser):
    """
    Simulates a regular user sending chat messages.
    Wait 1–3 seconds between requests (realistic human pacing).
    """
    wait_time = between(1, 3)
    weight    = 70              # 70% of simulated users

    def on_start(self):
        """Called once per simulated user when they start."""
        # Check that the API is healthy before hammering it
        with self.client.get("/health", catch_response=True) as r:
            if r.status_code != 200:
                r.failure(f"Health check failed: {r.status_code}")

    @task(5)    # Weight: most common action
    def send_chat_message(self):
        """Send a random chat message."""
        message = random.choice(SAMPLE_MESSAGES)
        payload = {
            "message":    message,
            "session_id": f"locust-user-{self.environment.runner.user_count}",
        }
        with self.client.post(
            "/api/v1/chat",
            json          = payload,
            name          = "/api/v1/chat [regular]",
            catch_response= True,
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "response" not in data:
                    response.failure("Response missing 'response' field")
                elif response.elapsed.total_seconds() > 3:
                    response.failure(f"Too slow: {response.elapsed.total_seconds():.2f}s")
                else:
                    response.success()
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(2)
    def check_health(self):
        """Periodically check the health endpoint."""
        self.client.get("/health", name="/health")

    @task(1)
    def get_session_history(self):
        """Fetch chat history for a session."""
        self.client.get(
            f"/api/v1/history/locust-session-{random.randint(1, 100)}",
            name="/api/v1/history/[session_id]",
        )

    @task(1)
    def submit_feedback(self):
        """Submit feedback for a session."""
        self.client.post(
            "/api/v1/feedback",
            json={
                "session_id": f"locust-session-{random.randint(1, 100)}",
                "rating":      random.randint(1, 5),
                "comment":    "Automated load test feedback",
            },
            name="/api/v1/feedback",
        )


class PowerUser(HttpUser):
    """
    Simulates a power user sending messages rapidly.
    Shorter wait time, heavier load pattern.
    """
    wait_time = between(0.5, 1.5)
    weight    = 20              # 20% of simulated users

    @task(3)
    def rapid_chat(self):
        """Send rapid chat messages."""
        self.client.post(
            "/api/v1/chat",
            json = {
                "message":    random.choice(SAMPLE_MESSAGES),
                "session_id": "power-user-session",
            },
            name = "/api/v1/chat [power]",
        )

    @task(1)
    def delete_session(self):
        """Delete a session periodically."""
        self.client.delete(
            f"/api/v1/sessions/power-session-{random.randint(1, 10)}",
            name="/api/v1/sessions/[id] DELETE",
        )


class EdgeCaseUser(HttpUser):
    """
    Simulates users hitting edge cases.
    Helps test stability under unusual inputs.
    """
    wait_time = between(2, 5)
    weight    = 10              # 10% of simulated users

    @task(2)
    def send_edge_message(self):
        """Send an edge-case message."""
        self.client.post(
            "/api/v1/chat",
            json = {"message": random.choice(EDGE_MESSAGES)},
            name = "/api/v1/chat [edge]",
        )

    @task(1)
    def send_invalid_json(self):
        """Send malformed JSON to test error handling."""
        with self.client.post(
            "/api/v1/chat",
            data    = "{bad-json",
            headers = {"Content-Type": "application/json"},
            name    = "/api/v1/chat [invalid-json]",
            catch_response = True,
        ) as r:
            # We EXPECT a 400 error here — mark it as success for load purposes
            if r.status_code == 400:
                r.success()
            else:
                r.failure(f"Expected 400 for invalid JSON, got {r.status_code}")


# ─── Event hooks for custom reporting ────────────────────────────────────────

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print(f"\n🚀 Load test started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Target: {environment.host}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    stats = environment.runner.stats
    total = stats.total

    print("\n" + "═" * 55)
    print("  LOAD TEST RESULTS")
    print("═" * 55)
    print(f"  Total requests      : {total.num_requests}")
    print(f"  Failures            : {total.num_failures}")
    print(f"  Failure rate        : {total.fail_ratio:.1%}")
    print(f"  Avg response time   : {total.avg_response_time:.0f} ms")
    print(f"  Median response time: {total.median_response_time:.0f} ms")
    print(f"  95th percentile     : {total.get_response_time_percentile(0.95):.0f} ms")
    print(f"  Requests/sec (RPS)  : {total.current_rps:.1f}")
    print("═" * 55 + "\n")

    # Save to file
    import os
    os.makedirs("reports", exist_ok=True)
    report = {
        "timestamp":        datetime.utcnow().isoformat(),
        "total_requests":   total.num_requests,
        "total_failures":   total.num_failures,
        "failure_rate":     f"{total.fail_ratio:.1%}",
        "avg_response_ms":  round(total.avg_response_time, 2),
        "median_ms":        round(total.median_response_time, 2),
        "p95_ms":           round(total.get_response_time_percentile(0.95), 2),
        "rps":              round(total.current_rps, 2),
    }
    with open("reports/load_test_report.json", "w") as f:
        json.dump(report, f, indent=2)
    print("  📄 Report saved to reports/load_test_report.json")
