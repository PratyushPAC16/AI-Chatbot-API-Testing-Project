"""
Test Logger
===========
Logs every API test interaction to:
  - JSON log files  (logs/test_log_<date>.json)
  - SQLite database (logs/test_results.db)

Features:
  - Request / response capture
  - Latency tracking
  - AI accuracy scores
  - Error recording
  - Structured bug reports
"""

import json
import sqlite3
import logging
import traceback
from datetime import datetime, date
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Optional, Any
from enum import Enum


# ─── Enums ───────────────────────────────────────────────────────────────────

class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH     = "HIGH"
    MEDIUM   = "MEDIUM"
    LOW      = "LOW"


class TestStatus(str, Enum):
    __test__ = False
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"
    WARN = "WARN"


# ─── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class TestLogEntry:
    __test__ = False
    test_name:       str
    endpoint:        str
    method:          str
    status:          TestStatus
    http_status:     Optional[int]    = None
    latency_ms:      Optional[float]  = None
    accuracy_score:  Optional[float]  = None
    request_body:    Optional[dict]   = None
    response_body:   Optional[Any]    = None
    error_message:   Optional[str]    = None
    timestamp:       str              = field(default_factory=lambda: datetime.utcnow().isoformat())
    tags:            list             = field(default_factory=list)


@dataclass
class BugReport:
    title:                str
    severity:             Severity
    steps_to_reproduce:   list[str]
    expected_behavior:    str
    actual_behavior:      str
    endpoint:             str
    request_body:         Optional[dict]  = None
    response_body:        Optional[Any]   = None
    http_status:          Optional[int]   = None
    environment:          str             = "localhost:5001"
    reporter:             str             = "Automated QA Framework"
    timestamp:            str             = field(default_factory=lambda: datetime.utcnow().isoformat())
    bug_id:               str             = field(default_factory=lambda: f"BUG-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}")


# ─── Logger ───────────────────────────────────────────────────────────────────

class TestLogger:
    """
    Central logging system for the AI Chatbot API Testing Framework.
    Writes to both a JSON file and a SQLite database.
    """
    __test__ = False

    LOG_DIR = Path("logs")
    DB_PATH = LOG_DIR / "test_results.db"

    def __init__(self):
        self.LOG_DIR.mkdir(exist_ok=True)
        self.json_log_path = self.LOG_DIR / f"test_log_{date.today()}.json"
        self._entries: list[dict] = []
        self._bugs:    list[dict] = []
        self._init_db()

        # Python stdlib logger (console output)
        logging.basicConfig(
            level   = logging.INFO,
            format  = "%(asctime)s [%(levelname)s] %(message)s",
            datefmt = "%Y-%m-%d %H:%M:%S",
        )
        self.log = logging.getLogger("QAFramework")

    # ── DB setup ──────────────────────────────────────────────────────────────

    def _init_db(self):
        """Create SQLite tables if they don't exist."""
        with sqlite3.connect(self.DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS test_results (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_name       TEXT NOT NULL,
                    endpoint        TEXT NOT NULL,
                    method          TEXT NOT NULL,
                    status          TEXT NOT NULL,
                    http_status     INTEGER,
                    latency_ms      REAL,
                    accuracy_score  REAL,
                    request_body    TEXT,
                    response_body   TEXT,
                    error_message   TEXT,
                    timestamp       TEXT NOT NULL,
                    tags            TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS bug_reports (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    bug_id          TEXT NOT NULL,
                    title           TEXT NOT NULL,
                    severity        TEXT NOT NULL,
                    endpoint        TEXT NOT NULL,
                    http_status     INTEGER,
                    expected        TEXT,
                    actual          TEXT,
                    environment     TEXT,
                    reporter        TEXT,
                    timestamp       TEXT NOT NULL,
                    full_json       TEXT
                )
            """)
            conn.commit()

    # ── Logging ───────────────────────────────────────────────────────────────

    def log_test(self, entry: TestLogEntry):
        """Record a single test result."""
        data = asdict(entry)
        self._entries.append(data)
        self._flush_json()
        self._write_db(data)

        emoji = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️", "SKIP": "⏭️"}.get(entry.status, "?")
        self.log.info(
            f"{emoji} [{entry.status}] {entry.test_name} | "
            f"{entry.method} {entry.endpoint} | "
            f"HTTP {entry.http_status} | "
            f"{entry.latency_ms or 'N/A'} ms | "
            f"Accuracy: {entry.accuracy_score or 'N/A'}"
        )

    def _write_db(self, data: dict):
        with sqlite3.connect(self.DB_PATH) as conn:
            conn.execute("""
                INSERT INTO test_results
                    (test_name, endpoint, method, status, http_status,
                     latency_ms, accuracy_score, request_body, response_body,
                     error_message, timestamp, tags)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                data["test_name"],
                data["endpoint"],
                data["method"],
                data["status"],
                data.get("http_status"),
                data.get("latency_ms"),
                data.get("accuracy_score"),
                json.dumps(data.get("request_body")),
                json.dumps(data.get("response_body")),
                data.get("error_message"),
                data["timestamp"],
                json.dumps(data.get("tags", [])),
            ))
            conn.commit()

    def _flush_json(self):
        """Overwrite the daily JSON log with current entries."""
        with open(self.json_log_path, "w") as f:
            json.dump({"test_run": str(date.today()), "entries": self._entries}, f, indent=2)

    # ── Bug reporting ─────────────────────────────────────────────────────────

    def file_bug(self, report: BugReport):
        """File a structured bug report."""
        data = asdict(report)
        self._bugs.append(data)

        # Save individual bug file
        bug_dir = Path("bug_reports")
        bug_dir.mkdir(exist_ok=True)
        bug_path = bug_dir / f"{report.bug_id}.json"
        with open(bug_path, "w") as f:
            json.dump(data, f, indent=2)

        # Write to DB
        with sqlite3.connect(self.DB_PATH) as conn:
            conn.execute("""
                INSERT INTO bug_reports
                    (bug_id, title, severity, endpoint, http_status,
                     expected, actual, environment, reporter, timestamp, full_json)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (
                report.bug_id, report.title, report.severity,
                report.endpoint, report.http_status,
                report.expected_behavior, report.actual_behavior,
                report.environment, report.reporter, report.timestamp,
                json.dumps(data),
            ))
            conn.commit()

        self.log.warning(f"🐛 [{report.severity}] Bug filed: {report.bug_id} – {report.title}")
        return report.bug_id

    # ── Summary ───────────────────────────────────────────────────────────────

    def summary(self) -> dict:
        """Return a summary of the current test session."""
        total  = len(self._entries)
        passed = sum(1 for e in self._entries if e["status"] == "PASS")
        failed = sum(1 for e in self._entries if e["status"] == "FAIL")
        warned = sum(1 for e in self._entries if e["status"] == "WARN")

        latencies = [e["latency_ms"] for e in self._entries if e.get("latency_ms")]
        avg_latency = round(sum(latencies) / len(latencies), 2) if latencies else 0

        accuracies = [e["accuracy_score"] for e in self._entries if e.get("accuracy_score")]
        avg_accuracy = round(sum(accuracies) / len(accuracies), 4) if accuracies else None

        return {
            "total":           total,
            "passed":          passed,
            "failed":          failed,
            "warned":          warned,
            "pass_rate":       f"{passed/total:.0%}" if total else "0%",
            "avg_latency_ms":  avg_latency,
            "avg_accuracy":    avg_accuracy,
            "bugs_filed":      len(self._bugs),
            "log_file":        str(self.json_log_path),
        }

    def print_summary(self):
        s = self.summary()
        print("\n" + "=" * 50)
        print("  TEST SESSION SUMMARY")
        print("=" * 50)
        for k, v in s.items():
            print(f"  {k:<20}: {v}")
        print("=" * 50 + "\n")

    # ── Query helpers ─────────────────────────────────────────────────────────

    def get_failures(self) -> list[dict]:
        """Return all failed test entries."""
        return [e for e in self._entries if e["status"] == "FAIL"]

    def query_db(self, sql: str) -> list[tuple]:
        """Run a raw SQL query against the results DB."""
        with sqlite3.connect(self.DB_PATH) as conn:
            cursor = conn.execute(sql)
            return cursor.fetchall()


# ─── CLI demo ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logger = TestLogger()

    # Log a passing test
    logger.log_test(TestLogEntry(
        test_name    = "test_health_endpoint",
        endpoint     = "/health",
        method       = "GET",
        status       = TestStatus.PASS,
        http_status  = 200,
        latency_ms   = 45.3,
        tags         = ["smoke", "health"],
    ))

    # Log a failing test with bug report
    logger.log_test(TestLogEntry(
        test_name     = "test_empty_message",
        endpoint      = "/api/v1/chat",
        method        = "POST",
        status        = TestStatus.FAIL,
        http_status   = 200,    # Bug: should be 422 but returned 200
        latency_ms    = 110.5,
        request_body  = {"message": ""},
        response_body = {"response": "I understand your query."},
        error_message = "Expected HTTP 422 for empty message, got 200",
        tags          = ["edge-case", "regression"],
    ))

    logger.file_bug(BugReport(
        title               = "Empty message returns 200 instead of 422",
        severity            = Severity.HIGH,
        steps_to_reproduce  = [
            "POST /api/v1/chat with body: {\"message\": \"\"}",
            "Observe HTTP 200 response",
        ],
        expected_behavior   = "HTTP 422 with validation error",
        actual_behavior     = "HTTP 200 with a generic response",
        endpoint            = "/api/v1/chat",
        http_status         = 200,
        request_body        = {"message": ""},
        response_body       = {"response": "I understand your query."},
    ))

    logger.print_summary()
