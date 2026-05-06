# 🤖 AI Chatbot API Testing Framework

> **Industry-level QA automation framework** combining Postman, pytest, Locust, AI response validation, structured logging, and a real-time Flask dashboard.

[![CI](https://github.com/your-org/ai-chatbot-api-testing-framework/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/ai-chatbot-api-testing-framework/actions)
[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 📋 Table of Contents

- [Project Overview](#project-overview)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Component Guide](#component-guide)
  - [1. Mock API Server](#1-mock-api-server)
  - [2. Python Tests (pytest)](#2-python-tests-pytest)
  - [3. Postman + Newman](#3-postman--newman)
  - [4. AI Response Validator](#4-ai-response-validator)
  - [5. Load Testing (Locust)](#5-load-testing-locust)
  - [6. Logging System](#6-logging-system)
  - [7. QA Dashboard (Flask)](#7-qa-dashboard-flask)
  - [8. CI/CD (GitHub Actions)](#8-cicd-github-actions)
- [Test Coverage (50+ Tests)](#test-coverage-50-tests)
- [Bug Reports](#bug-reports)
- [Interview Q&A](#interview-qa)

---

## Project Overview

This framework tests AI chatbot REST APIs end-to-end:

| Layer | Tool | Purpose |
|---|---|---|
| API Client | `requests` | Fire HTTP requests programmatically |
| Test Runner | `pytest` | 50+ automated test cases |
| Collection | Postman / Newman | GUI + CLI test execution |
| AI Validation | Custom validator | Cosine similarity + keyword matching |
| Load Testing | Locust | Multi-user performance simulation |
| Logging | SQLite + JSON | Persist all request/response/accuracy data |
| Dashboard | Flask + Chart.js | Real-time visualization |
| CI/CD | GitHub Actions | Auto-run on every push |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  TEST ORCHESTRATION                      │
│  pytest CLI ──► conftest.py ──► test_*.py files         │
│  Newman CLI ──► Postman Collection JSON                  │
│  Locust     ──► locustfile.py                            │
└─────────────┬───────────────────────────────────────────┘
              │ HTTP requests
              ▼
┌─────────────────────────────────────────────────────────┐
│            MOCK CHATBOT API  (Flask :5001)               │
│  GET  /health                                            │
│  POST /api/v1/chat                                       │
│  GET|DELETE /api/v1/sessions/:id                        │
│  POST /api/v1/feedback                                   │
│  GET  /api/v1/history/:id                               │
└─────────────┬───────────────────────────────────────────┘
              │ responses
              ▼
┌──────────────────┐   ┌──────────────────┐   ┌──────────┐
│  ResponseValidator│  │    TestLogger     │   │ BugReport│
│  • keyword match  │  │  • JSON log file  │   │ • Severity│
│  • cosine sim     │  │  • SQLite DB      │   │ • Steps  │
│  • accuracy score │  │  • console log    │   │ • Expected│
└──────────────────┘   └──────────────────┘   └──────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────┐
│           QA DASHBOARD  (Flask :5050)                    │
│  Chart.js visualization of latency, accuracy, errors    │
└─────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ (for Newman)

### 1. Clone & Install

```bash
git clone https://github.com/your-org/ai-chatbot-api-testing-framework.git
cd ai-chatbot-api-testing-framework
pip install -r requirements.txt
npm install -g newman newman-reporter-htmlextra
```

### 2. Start the Mock API Server

```bash
python src/mock_server/app.py
# ✅ API running at http://localhost:5001
```

### 3. Run All Tests

```bash
# All pytest tests
pytest tests/ -v

# Specific suites
pytest tests/functional/   -v   # Functional only
pytest tests/edge_cases/   -v   # Edge cases only
pytest tests/regression/   -v   # Regression only

# With HTML report
pytest tests/ -v --html=reports/report.html --self-contained-html
```

### 4. Run Postman Tests via Newman

```bash
newman run postman/chatbot_api_collection.json \
  --environment postman/environment.json \
  --reporters cli,htmlextra \
  --reporter-htmlextra-export reports/newman_report.html
```

### 5. Load Testing with Locust

```bash
# Headless (30 seconds, 50 users)
locust -f locust/locustfile.py \
  --host=http://localhost:5001 \
  --users 50 --spawn-rate 5 \
  --run-time 30s --headless

# Web UI (open http://localhost:8089)
locust -f locust/locustfile.py --host=http://localhost:5001
```

### 6. Launch Dashboard

```bash
python src/dashboard/dashboard.py
# 📊 Dashboard at http://localhost:5050
```

---

## Project Structure

```
ai-chatbot-api-testing-framework/
├── src/
│   ├── mock_server/
│   │   └── app.py                 # Flask mock chatbot API
│   ├── validator/
│   │   └── response_validator.py  # AI accuracy scoring engine
│   ├── logger/
│   │   └── test_logger.py         # JSON + SQLite logging
│   └── dashboard/
│       └── dashboard.py           # Flask visualization dashboard
├── tests/
│   ├── conftest.py                # Shared pytest fixtures
│   ├── functional/
│   │   ├── test_functional.py     # 22 functional tests
│   │   └── test_ai_validation.py  # AI accuracy tests
│   ├── edge_cases/
│   │   └── test_edge_cases.py     # 25 edge case tests
│   └── regression/
│       └── test_regression.py     # 10 regression tests
├── postman/
│   ├── chatbot_api_collection.json
│   └── environment.json
├── locust/
│   └── locustfile.py              # Multi-user load test
├── bug_reports/
│   └── sample_bug_reports.json
├── github_actions/
│   └── ci.yml                     # GitHub Actions workflow
├── logs/                          # Auto-created on first test run
├── reports/                       # Test reports output here
├── requirements.txt
├── pytest.ini
└── README.md
```

---

## Component Guide

### 1. Mock API Server

`src/mock_server/app.py` — A Flask server simulating a real chatbot API.

**Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/api/v1/chat` | Send a message, get a response |
| GET | `/api/v1/sessions/:id` | Get session info |
| DELETE | `/api/v1/sessions/:id` | Delete a session |
| POST | `/api/v1/feedback` | Submit a rating |
| GET | `/api/v1/history/:id` | Get chat history |

**Validation built-in:**
- Rejects empty messages → 422
- Rejects payloads > 1000 chars → 413
- Rejects wrong Content-Type → 415
- Rejects toxic keywords → 400

---

### 2. Python Tests (pytest)

**Run all 50+ tests:**
```bash
pytest tests/ -v
```

**Key patterns used:**

```python
# Fixture injection (conftest.py)
def test_chat_returns_200(api_client, chat_endpoint):
    r = api_client.post(chat_endpoint, json={"message": "Hello"})
    assert r.status_code == 200

# Parametrize for data-driven testing
@pytest.mark.parametrize("message, expected, min_accuracy", SCENARIOS)
def test_response_accuracy(message, expected, min_accuracy):
    ...

# Custom assertion helpers
assert_response_time(response, max_ms=2000)
assert_json_keys(data, ["response", "session_id", "latency_ms"])
```

---

### 3. Postman + Newman

**Import into Postman:**
1. Open Postman → Import → `postman/chatbot_api_collection.json`
2. Import environment → `postman/environment.json`
3. Run collection manually or via Collection Runner

**Run from CLI (Newman):**
```bash
newman run postman/chatbot_api_collection.json \
  --environment postman/environment.json \
  --reporters cli,htmlextra,junit \
  --reporter-htmlextra-export reports/newman_report.html \
  --reporter-junit-export reports/newman_results.xml
```

---

### 4. AI Response Validator

`src/validator/response_validator.py`

Scores chatbot responses using two complementary methods:

**Method 1: Keyword Matching**
```
score = (keywords_from_expected found in actual) / total_expected_keywords
```

**Method 2: Cosine Similarity (TF vectors)**
```
similarity = dot(vec_a, vec_b) / (|vec_a| × |vec_b|)
```

**Combined Accuracy Score:**
```
accuracy = 0.40 × keyword_score + 0.60 × semantic_score
```

**Verdict thresholds:**
- ≥ 70% → **PASS**
- 40–69% → **WARN**
- < 40% → **FAIL**

**Usage:**
```python
from src.validator.response_validator import ResponseValidator

validator = ResponseValidator()
result = validator.validate(
    expected = "Hello! How can I assist you today?",
    actual   = "Hello! What can I help you with?",
)
print(result.accuracy_score)   # e.g. 0.82
print(result.verdict)          # PASS
print(result.matched_keywords) # ['hello', 'assist', 'today']
```

---

### 5. Load Testing (Locust)

`locust/locustfile.py` defines three user classes:

| User Class | % of Users | Wait Time | Behavior |
|---|---|---|---|
| `RegularChatUser` | 70% | 1–3s | Chat, health, history, feedback |
| `PowerUser` | 20% | 0.5–1.5s | Rapid chat + session deletes |
| `EdgeCaseUser` | 10% | 2–5s | Edge inputs + invalid JSON |

**Target metrics (SLA):**
- Avg response time < 500ms
- P95 response time < 1000ms
- Failure rate < 1%
- Throughput > 20 req/s

---

### 6. Logging System

`src/logger/test_logger.py` — Writes to both JSON and SQLite.

**JSON log** (`logs/test_log_YYYY-MM-DD.json`):
```json
{
  "test_run": "2024-01-01",
  "entries": [
    {
      "test_name": "test_health_endpoint",
      "endpoint": "/health",
      "method": "GET",
      "status": "PASS",
      "http_status": 200,
      "latency_ms": 45.3,
      "accuracy_score": null,
      "timestamp": "2024-01-01T10:00:00"
    }
  ]
}
```

**SQLite tables:** `test_results`, `bug_reports`

---

### 7. QA Dashboard (Flask)

`src/dashboard/dashboard.py` — Real-time visualization.

Open at **http://localhost:5050** after running tests.

**Charts displayed:**
- KPI cards: Total / Pass / Fail / Pass rate / Avg latency / Avg accuracy
- Line chart: Response latency over recent tests
- Pie chart: PASS / FAIL / WARN distribution
- Bar chart: AI accuracy scores
- Bar chart: Requests by endpoint
- Table: Recent test failures with error messages

---

### 8. CI/CD (GitHub Actions)

`.github/workflows/ci.yml` — Copy from `github_actions/ci.yml`.

**Pipeline jobs:**

```
push → python-tests → newman-tests → load-test (main only)
                ↓ (if failure)
              notify
```

**Setup:**
```bash
# Copy to .github/workflows/
mkdir -p .github/workflows
cp github_actions/ci.yml .github/workflows/ci.yml
git add .github/
git commit -m "Add CI/CD pipeline"
git push
```

---

## Test Coverage (50+ Tests)

| Suite | File | Count | Category |
|---|---|---|---|
| Health check | `test_functional.py` | 5 | Functional |
| Chat endpoint | `test_functional.py` | 9 | Functional |
| Sessions | `test_functional.py` | 4 | Functional |
| Feedback & History | `test_functional.py` | 4 | Functional |
| Empty / whitespace | `test_edge_cases.py` | 6 | Edge case |
| Large payloads | `test_edge_cases.py` | 5 | Edge case |
| Invalid JSON / headers | `test_edge_cases.py` | 5 | Edge case |
| Toxic prompts | `test_edge_cases.py` | 5 | Edge case |
| Special chars / methods | `test_edge_cases.py` | 4 | Edge case |
| AI validator unit | `test_ai_validation.py` | 10 | Unit |
| API accuracy | `test_ai_validation.py` | 8 | Integration |
| Regression | `test_regression.py` | 10 | Regression |
| **TOTAL** | | **75** | |

---

## Bug Reports

Bug reports are auto-generated in `bug_reports/` as individual JSON files.

**Severity levels:**

| Level | Criteria | Example |
|---|---|---|
| CRITICAL | Security, data loss, complete outage | Toxic content bypasses filter |
| HIGH | Core feature broken, no workaround | Empty message accepted |
| MEDIUM | Feature degraded, workaround exists | Feedback accepts rating=0 |
| LOW | Minor UX issue, cosmetic | Trailing whitespace in response |

**Sample bug report structure:**
```json
{
  "bug_id": "BUG-20240101-001",
  "title": "Empty message returns 200 instead of 422",
  "severity": "HIGH",
  "steps_to_reproduce": [...],
  "expected_behavior": "HTTP 422 with validation error",
  "actual_behavior": "HTTP 200 with generic response",
  "endpoint": "POST /api/v1/chat",
  "request_body": {"message": ""},
  "reporter": "Automated QA Framework"
}
```

---

## Interview Q&A

**Q1: What is the difference between functional and regression testing?**
Functional testing verifies that each feature works as specified. Regression testing re-runs previous tests after code changes to ensure nothing that worked before has broken. In this framework, `tests/functional/` covers features; `tests/regression/` re-checks previously fixed bugs like BUG-001 (empty message returning 200).

**Q2: How does the AI response validator work?**
It combines two signals: (1) keyword matching — what fraction of expected keywords appear in the actual response; (2) cosine similarity — how close the TF vectors of expected and actual text are. A weighted sum (40% keyword, 60% semantic) gives a 0–1 accuracy score. Verdict thresholds: ≥70%=PASS, 40–69%=WARN, <40%=FAIL.

**Q3: What metrics does Locust capture?**
Throughput (requests/second), average response time, median response time, 95th-percentile latency, and failure rate. These are compared against SLA thresholds: P95 < 1000ms, failure rate < 1%, RPS > 20.

**Q4: Why use both pytest AND Postman/Newman?**
pytest gives full programmatic control — parameterization, fixtures, custom assertions, AI validation, and logging integration. Postman gives a GUI for exploratory testing and is preferred by non-developer QA engineers. Newman lets Postman collections run in CI pipelines. Both approaches validate the same API, giving layered confidence.

**Q5: What is schema validation and why does it matter?**
Schema validation checks that the API response has the correct structure — expected fields present, correct data types, no missing keys. This catches contract violations: an API may return HTTP 200 but have a broken schema that would crash client applications.

**Q6: How would you extend this for a real AI chatbot (e.g., GPT-4)?**
Replace the mock server URL with the real API. Expand `VALIDATION_SCENARIOS` with real expected outputs. Add adversarial prompt tests. Integrate with a semantic embedding API (e.g., OpenAI embeddings) in the validator for higher-quality similarity. Add latency SLA monitoring and alert on regressions.

**Q7: What is the purpose of the conftest.py file?**
`conftest.py` is pytest's shared fixture file. Fixtures defined there are auto-injected into any test function that names them as parameters — no import needed. Session-scoped fixtures (like the requests.Session and Logger) are created once for the entire test run, improving performance.

**Q8: How do you handle flaky tests?**
Mark them with `@pytest.mark.flaky(reruns=3)` (with `pytest-rerunfailures`). Log flaky failures with the TestLogger so trends can be identified. Isolate root causes: often flakiness is due to timing issues (use `time.sleep` or retry logic), external dependencies, or test ordering issues (fix with isolated fixtures).

---

## License

MIT — free for personal and commercial use.

---

*Built with ❤️ for QA engineers who take their craft seriously.*
