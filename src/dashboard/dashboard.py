"""
QA Dashboard – Flask Application
==================================
Visualizes test results from the SQLite database and JSON logs.

Routes:
  /              – Dashboard home (charts + KPIs)
  /api/stats     – JSON stats for the frontend charts
  /api/bugs      – List of filed bug reports
  /api/tests     – Raw test results

Run: python src/dashboard/dashboard.py
Then open: http://localhost:5050
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

DB_PATH   = Path("logs/test_results.db")
LOG_DIR   = Path("logs")
BUG_DIR   = Path("bug_reports")


# ─── DB helper ───────────────────────────────────────────────────────────────

def query(sql: str, params=()) -> list[dict]:
    """Run a SELECT and return list of row dicts."""
    if not DB_PATH.exists():
        return []
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]


# ─── API endpoints ────────────────────────────────────────────────────────────

@app.route("/api/stats")
def api_stats():
    """Aggregate statistics for the dashboard with filtering."""
    status_filter   = request.args.get("status", "ALL")
    endpoint_filter = request.args.get("endpoint", "ALL")
    days_filter     = request.args.get("days", "ALL")

    sql = "SELECT * FROM test_results WHERE 1=1"
    params = []

    if status_filter != "ALL":
        sql += " AND status = ?"
        params.append(status_filter)

    if endpoint_filter != "ALL":
        sql += " AND endpoint = ?"
        params.append(endpoint_filter)

    if days_filter != "ALL":
        try:
            days = int(days_filter)
            sql += " AND timestamp >= datetime('now', ?)"
            params.append(f"-{days} days")
        except ValueError:
            pass

    sql += " ORDER BY timestamp DESC LIMIT 500"
    results = query(sql, tuple(params))

    # Fetch unique endpoints across the whole DB for the dropdown
    all_endpoints = query("SELECT DISTINCT endpoint FROM test_results WHERE endpoint IS NOT NULL")
    available_endpoints = [r["endpoint"] for r in all_endpoints]

    if not results and status_filter == "ALL" and endpoint_filter == "ALL" and days_filter == "ALL":
        return jsonify({"error": "No test data found. Run tests first."})

    total   = len(results)
    passed  = sum(1 for r in results if r["status"] == "PASS")
    failed  = sum(1 for r in results if r["status"] == "FAIL")
    warned  = sum(1 for r in results if r["status"] == "WARN")

    latencies  = [r["latency_ms"]     for r in results if r.get("latency_ms")]
    accuracies = [r["accuracy_score"]  for r in results if r.get("accuracy_score")]

    # Group by endpoint
    endpoint_counts = {}
    for r in results:
        ep = r["endpoint"]
        if ep:
            endpoint_counts[ep] = endpoint_counts.get(ep, 0) + 1

    # Group by status over time (last 20 tests from filtered results)
    recent = results[:20]

    # Reverse recent so older is left, newer is right on charts
    recent_chronological = recent[::-1]

    return jsonify({
        "available_endpoints": available_endpoints,
        "summary": {
            "total":         total,
            "passed":        passed,
            "failed":        failed,
            "warned":        warned,
            "pass_rate":     round(passed / total * 100, 1) if total else 0,
            "avg_latency":   round(sum(latencies) / len(latencies), 1) if latencies else 0,
            "avg_accuracy":  round(sum(accuracies) / len(accuracies) * 100, 1) if accuracies else None,
        },
        "latency_chart": {
            "labels": [r["test_name"][:20] for r in recent_chronological],
            "data":   [r["latency_ms"] or 0 for r in recent_chronological],
        },
        "status_pie": {
            "labels": ["PASS", "FAIL", "WARN"],
            "data":   [passed, failed, warned],
        },
        "accuracy_chart": {
            "labels": [r["test_name"][:20] for r in recent_chronological if r.get("accuracy_score")],
            "data":   [round(r["accuracy_score"] * 100, 1) for r in recent_chronological if r.get("accuracy_score")],
        },
        "endpoints": {
            "labels": list(endpoint_counts.keys()),
            "data":   list(endpoint_counts.values()),
        },
        "recent_failures": [
            {
                "test": r["test_name"],
                "endpoint": r["endpoint"],
                "error": r["error_message"],
                "timestamp": r["timestamp"],
            }
            for r in results if r["status"] == "FAIL"
        ][:5],
    })


@app.route("/api/bugs")
def api_bugs():
    """Return list of bug reports."""
    bugs = query("SELECT * FROM bug_reports ORDER BY timestamp DESC")
    return jsonify(bugs)


@app.route("/api/tests")
def api_tests():
    """Return raw test results (last 100)."""
    results = query("SELECT * FROM test_results ORDER BY timestamp DESC LIMIT 100")
    return jsonify(results)


# ─── Dashboard HTML ───────────────────────────────────────────────────────────

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI Chatbot QA Dashboard</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
  :root {
    --bg:      #0d1117;
    --surface: #161b22;
    --border:  #30363d;
    --text:    #e6edf3;
    --muted:   #8b949e;
    --green:   #3fb950;
    --red:     #f85149;
    --yellow:  #d29922;
    --blue:    #58a6ff;
    --purple:  #bc8cff;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'Courier New', monospace;
    min-height: 100vh;
  }
  header {
    padding: 20px 32px;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 12px;
  }
  header h1 { font-size: 1.2rem; letter-spacing: 0.05em; margin-right: auto; }
  
  .filter-bar {
    display: flex;
    gap: 16px;
    align-items: center;
  }
  .filter-bar select {
    background: var(--bg);
    color: var(--text);
    border: 1px solid var(--border);
    padding: 6px 12px;
    border-radius: 4px;
    font-family: inherit;
    font-size: 0.85rem;
    cursor: pointer;
  }
  .filter-bar select:focus {
    outline: none;
    border-color: var(--blue);
  }

  header .badge {
    background: var(--green);
    color: #000;
    font-size: 0.65rem;
    padding: 2px 8px;
    border-radius: 10px;
    font-weight: bold;
    margin-left: 16px;
  }
  .ts { font-size: 0.75rem; color: var(--muted); margin-left: 8px; }
  main { padding: 28px 32px; max-width: 1400px; margin: 0 auto; }

  /* KPI Cards */
  .kpi-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 16px;
    margin-bottom: 28px;
  }
  .kpi-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 20px 16px;
  }
  .kpi-card .label { font-size: 0.7rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 8px; }
  .kpi-card .value { font-size: 2rem; font-weight: bold; }
  .kpi-card.green .value { color: var(--green); }
  .kpi-card.red   .value { color: var(--red); }
  .kpi-card.blue  .value { color: var(--blue); }
  .kpi-card.yellow .value { color: var(--yellow); }
  .kpi-card.purple .value { color: var(--purple); }

  /* Chart grid */
  .chart-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    margin-bottom: 28px;
  }
  .chart-grid.wide { grid-template-columns: 2fr 1fr; }
  .chart-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 20px;
  }
  .chart-card h2 { font-size: 0.75rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 16px; }
  .chart-card canvas { max-height: 220px; }

  /* Failures table */
  .failures-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 28px;
  }
  .failures-card h2 { font-size: 0.75rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 14px; }
  table { width: 100%; border-collapse: collapse; font-size: 0.8rem; }
  th { color: var(--muted); text-align: left; padding: 6px 10px; border-bottom: 1px solid var(--border); font-weight: normal; }
  td { padding: 8px 10px; border-bottom: 1px solid #21262d; }
  td.red { color: var(--red); }
  .loading { color: var(--muted); text-align: center; padding: 40px; }
  .error   { color: var(--red); text-align: center; padding: 20px; }
</style>
</head>
<body>
<header>
  <span>⬡</span>
  <h1>AI CHATBOT QA DASHBOARD</h1>
  
  <div class="filter-bar">
    <select id="filter-days" onchange="loadData()">
      <option value="ALL">All Time</option>
      <option value="1">Last 24h</option>
      <option value="7">Last 7 Days</option>
      <option value="30">Last 30 Days</option>
    </select>
    
    <select id="filter-status" onchange="loadData()">
      <option value="ALL">All Status</option>
      <option value="PASS">PASS</option>
      <option value="FAIL">FAIL</option>
      <option value="WARN">WARN</option>
    </select>
    
    <select id="filter-endpoint" onchange="loadData()">
      <option value="ALL">All Endpoints</option>
    </select>
  </div>

  <span class="badge">LIVE</span>
  <span class="ts" id="ts">Loading...</span>
</header>
<main>
  <div class="loading" id="loader">⏳ Fetching test data...</div>

  <div id="content" style="display:none">
    <!-- KPI cards -->
    <div class="kpi-grid" id="kpi-grid"></div>

    <!-- Charts row 1 -->
    <div class="chart-grid wide">
      <div class="chart-card">
        <h2>⏱ Response Latency (ms) – Recent Tests</h2>
        <canvas id="latencyChart"></canvas>
      </div>
      <div class="chart-card">
        <h2>● Test Status Distribution</h2>
        <canvas id="pieChart"></canvas>
      </div>
    </div>

    <!-- Charts row 2 -->
    <div class="chart-grid">
      <div class="chart-card">
        <h2>🎯 AI Accuracy Score (%) – Recent Tests</h2>
        <canvas id="accuracyChart"></canvas>
      </div>
      <div class="chart-card">
        <h2>📡 Requests by Endpoint</h2>
        <canvas id="endpointChart"></canvas>
      </div>
    </div>

    <!-- Recent failures -->
    <div class="failures-card">
      <h2>❌ Recent Failures</h2>
      <table>
        <thead>
          <tr><th>Test</th><th>Endpoint</th><th>Error</th><th>Timestamp</th></tr>
        </thead>
        <tbody id="failures-body">
          <tr><td colspan="4" class="loading">Loading...</td></tr>
        </tbody>
      </table>
    </div>
  </div>
  <div class="error" id="error-msg" style="display:none"></div>
</main>

<script>
const COLORS = {
  green:  '#3fb950', red: '#f85149', yellow: '#d29922',
  blue:   '#58a6ff', purple: '#bc8cff', muted: '#8b949e'
};

// Keep track of chart instances so we can destroy them before redrawing
window.charts = {};

function makeKpi(label, value, colorClass) {
  return `<div class="kpi-card ${colorClass}">
    <div class="label">${label}</div>
    <div class="value">${value}</div>
  </div>`;
}

function makeChart(id, type, labels, data, color, label) {
  if (window.charts[id]) {
    window.charts[id].destroy();
  }
  
  const ctx = document.getElementById(id).getContext('2d');
  window.charts[id] = new Chart(ctx, {
    type,
    data: {
      labels,
      datasets: [{
        label,
        data,
        backgroundColor: Array.isArray(color) ? color : color + '33',
        borderColor:     Array.isArray(color) ? color : color,
        borderWidth: 2,
        tension: 0.4,
        fill: type === 'line',
        pointRadius: 4,
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { labels: { color: '#8b949e', font: { size: 11 } } } },
      scales: type !== 'pie' && type !== 'doughnut' ? {
        x: { ticks: { color: '#8b949e', font: { size: 10 } }, grid: { color: '#21262d' } },
        y: { ticks: { color: '#8b949e', font: { size: 10 }, beginAtZero: true }, grid: { color: '#21262d' } },
      } : {},
    }
  });
}

function updateEndpointDropdown(endpoints) {
  const select = document.getElementById('filter-endpoint');
  const currentVal = select.value;
  
  // Keep ALL option
  let html = '<option value="ALL">All Endpoints</option>';
  endpoints.forEach(ep => {
    html += `<option value="${ep}">${ep}</option>`;
  });
  select.innerHTML = html;
  
  // Restore selection if it still exists
  if (endpoints.includes(currentVal) || currentVal === 'ALL') {
    select.value = currentVal;
  } else {
    select.value = 'ALL';
  }
}

async function loadData() {
  try {
    const status   = document.getElementById('filter-status').value;
    const endpoint = document.getElementById('filter-endpoint').value;
    const days     = document.getElementById('filter-days').value;
    
    const params = new URLSearchParams({ status, endpoint, days });
    const res  = await fetch('/api/stats?' + params.toString());
    const data = await res.json();
    
    if (data.error) {
       // If filtering resulted in empty set, clear charts but keep dashboard up
       if (data.error.includes("No test data found") && (status !== 'ALL' || endpoint !== 'ALL' || days !== 'ALL')) {
         document.getElementById('kpi-grid').innerHTML = '<div style="grid-column: 1/-1; padding: 20px; color: var(--muted)">No results match the current filters.</div>';
         ['latencyChart', 'pieChart', 'accuracyChart', 'endpointChart'].forEach(id => {
            if (window.charts[id]) window.charts[id].destroy();
         });
         document.getElementById('failures-body').innerHTML = '<tr><td colspan="4" style="color:#3fb950;padding:12px">✅ No failures matching filters</td></tr>';
         return;
       }
       throw new Error(data.error);
    }

    document.getElementById('loader').style.display  = 'none';
    document.getElementById('content').style.display = 'block';
    document.getElementById('error-msg').style.display = 'none';
    document.getElementById('ts').textContent = 'Updated: ' + new Date().toLocaleTimeString();

    // Update endpoint dropdown with available options from the backend
    if (data.available_endpoints) {
      updateEndpointDropdown(data.available_endpoints);
    }

    const s = data.summary;
    document.getElementById('kpi-grid').innerHTML = [
      makeKpi('Total Tests',    s.total,                         'blue'),
      makeKpi('Passed',         s.passed,                        'green'),
      makeKpi('Failed',         s.failed,                        'red'),
      makeKpi('Warned',         s.warned,                        'yellow'),
      makeKpi('Pass Rate',      s.pass_rate + '%',               s.pass_rate >= 80 ? 'green' : (s.pass_rate > 0 ? 'red' : 'muted')),
      makeKpi('Avg Latency',    s.avg_latency + 'ms',            s.avg_latency < 500 ? 'green' : 'yellow'),
      s.avg_accuracy != null ? makeKpi('Avg Accuracy', s.avg_accuracy + '%', s.avg_accuracy >= 70 ? 'green' : 'yellow') : '',
    ].join('');

    makeChart('latencyChart', 'line',
      data.latency_chart.labels, data.latency_chart.data,
      COLORS.blue, 'Latency (ms)'
    );

    makeChart('pieChart', 'doughnut',
      data.status_pie.labels, data.status_pie.data,
      [COLORS.green, COLORS.red, COLORS.yellow], 'Tests'
    );

    if (data.accuracy_chart.labels.length > 0) {
      makeChart('accuracyChart', 'bar',
        data.accuracy_chart.labels, data.accuracy_chart.data,
        COLORS.purple, 'Accuracy (%)'
      );
    } else if (window.charts['accuracyChart']) {
        window.charts['accuracyChart'].destroy();
    }

    makeChart('endpointChart', 'bar',
      data.endpoints.labels, data.endpoints.data,
      COLORS.yellow, 'Request Count'
    );

    const tbody = document.getElementById('failures-body');
    if (data.recent_failures.length === 0) {
      tbody.innerHTML = '<tr><td colspan="4" style="color:#3fb950;padding:12px">✅ No recent failures matching filters</td></tr>';
    } else {
      tbody.innerHTML = data.recent_failures.map(f => `
        <tr>
          <td>${f.test}</td>
          <td style="color:#58a6ff">${f.endpoint}</td>
          <td class="red">${f.error || '–'}</td>
          <td style="color:#8b949e;font-size:0.75rem">${f.timestamp?.slice(0,19) || '–'}</td>
        </tr>
      `).join('');
    }

  } catch (err) {
    document.getElementById('loader').style.display    = 'none';
    document.getElementById('error-msg').style.display = 'block';
    document.getElementById('error-msg').textContent   =
      '❌ ' + err.message + ' — Run the test suite first: pytest tests/ -v';
  }
}

// Ensure loadData is bound to window so onchange handlers can see it
window.loadData = loadData;

loadData();
setInterval(loadData, 15000);   // Refresh every 15 seconds
</script>
</body>
</html>"""


@app.route("/")
def dashboard():
    return render_template_string(DASHBOARD_HTML)


if __name__ == "__main__":
    print("📊 QA Dashboard running at http://localhost:5050")
    app.run(host="0.0.0.0", port=5050, debug=True)
