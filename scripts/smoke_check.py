"""Zero500 post-deployment smoke test.

This is a live, end-to-end sanity suite that runs against a *running*
backend (default ``http://127.0.0.1:8000/api/v1``). It is intentionally
kept separate from the pytest suite in ``backend/tests/``:

* the pytest suite mocks the database and Gemini and runs offline/in CI;
* this script exercises real HTTP against a deployed instance and therefore
  needs a real Neon database and a real Gemini API key (see ``backend/.env``).

Run after a deploy or before a release to verify the live stack:

    python scripts/smoke_check.py

Exit code 0 = all probes passed; non-zero = one or more probes failed.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:8000/api/v1"

COLORS = {"INFO": "\033[94m", "PASS": "\033[92m", "FAIL": "\033[91m", "RESET": "\033[0m"}


def log(msg: str, status: str = "INFO") -> None:
    print(f"{COLORS.get(status, '')}[{status}] {msg}{COLORS['RESET']}")


def request(path, method="GET", data=None, timeout=120):
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, method=method)
    req.add_header("Content-Type", "application/json")
    body = json.dumps(data).encode("utf-8") if data else None

    try:
        with urllib.request.urlopen(req, data=body, timeout=timeout) as res:
            return res.status, json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8"))
        except Exception:
            return e.code, {"error": str(e)}
    except Exception as e:
        return 500, {"error": str(e)}


def run_sanity_suite() -> int:
    print("=" * 60)
    print("🚀 ZERO500 POST-DEPLOYMENT SMOKE SUITE")
    print("=" * 60)
    failures = 0

    # 1. Health Probe
    status, data = request("/health")
    if status == 200 and data.get("database") == "connected":
        log("1. Health Probe: database & API verified.", "PASS")
    else:
        log(f"1. Health Probe failed: {data}", "FAIL")
        failures += 1

    # 2. Ingest Dynamic Incident
    test_incident = {
        "id": "INC-SMOKE-01",
        "title": "Smoke Test: Kafka Partition Lag & Consumer Timeout",
        "service": "order-pipeline",
        "severity": "HIGH",
        "status": "INVESTIGATING",
        "created_at": "2026-10-19T10:00:00Z",
        "description": "Kafka consumer groups failing to commit offsets.",
        "metrics_snapshot": {"consumer_lag": 14200, "uncommitted_offsets": 850},
        "logs": [
            {
                "timestamp": "2026-10-19T09:58:00Z",
                "level": "WARN",
                "service": "order-pipeline",
                "message": "CommitFailedException: Consumer group rebalance in progress.",
            },
            {
                "timestamp": "2026-10-19T09:59:12Z",
                "level": "ERROR",
                "service": "order-pipeline",
                "message": "OffsetCommitTimeout: Failed to commit offsets within 15000ms.",
            },
        ],
    }
    status, data = request("/incidents/ingest", method="POST", data=test_incident)
    if status == 200 and data.get("id") == "INC-SMOKE-01":
        log("2. Live Webhook Ingestion: Incident persisted to database.", "PASS")
    else:
        log(f"2. Ingestion failed: {data}", "FAIL")
        failures += 1

    # 3. Read-After-Write Verification
    status, data = request("/incidents/INC-SMOKE-01")
    if status == 200 and len(data.get("logs", [])) == 2:
        log("3. Read-After-Write: Verified persistent incident logs.", "PASS")
    else:
        log(f"3. Read-After-Write failed: {data}", "FAIL")
        failures += 1

    # 4. pgvector Semantic Search
    status, data = request("/runbooks/search?query=database%20connection%20exhaustion&limit=1")
    if status == 200 and len(data.get("matches", [])) > 0:
        top_match = data["matches"][0]
        log(
            f"4. Vector Search: Matched '{top_match['title']}' "
            f"(Score: {top_match['similarity_score']}).",
            "PASS",
        )
    else:
        log(f"4. Vector search failed: {data}", "FAIL")
        failures += 1

    # 5. Gemini Structured RCA Investigation
    log("5. Running live Gemini AI Investigation (inference in progress)...", "INFO")
    status, data = request("/incidents/INC-SMOKE-01/investigate", method="POST")
    if status == 200 and data.get("confidence_score") is not None and len(data.get("evidence", [])) > 0:
        log(
            f"5. AI Investigation succeeded! Confidence: "
            f"{data['confidence_score']*100}% | "
            f"Cause: {data['suspected_root_cause'][:60]}...",
            "PASS",
        )
    else:
        log(f"5. AI Investigation failed: {data}", "FAIL")
        failures += 1

    # 6. Benchmark Evaluation Suite
    log("6. Running Benchmark Harness (Evaluating 3 test cases)...", "INFO")
    status, data = request("/evaluations/run", method="POST", timeout=300)
    if status == 200 and data.get("retrieval_recall") is not None:
        log(
            f"6. Benchmark Passed: "
            f"Recall={data.get('retrieval_recall') * 100:.0f}%, "
            f"Faithfulness={data.get('average_faithfulness') * 100:.0f}%, "
            f"Accuracy={data.get('average_diagnosis_accuracy') * 100:.0f}%.",
            "PASS",
        )
    else:
        log(f"6. Evaluation suite failed: {data}", "FAIL")
        failures += 1

    # 7. Rate Limiter Shield Verification
    log("7. Testing Rate Limiter Shield (triggering rapid requests)...", "INFO")
    hit_429 = False
    for _ in range(6):
        status, _ = request("/incidents/INC-SMOKE-01/investigate", method="POST")
        if status == 429:
            hit_429 = True
            break
        time.sleep(0.1)

    if hit_429:
        log("7. Quota Shield Active: HTTP 429 received on quota threshold.", "PASS")
    else:
        log("7. Rate limiter warning: Did not hit 429 within 6 calls.", "FAIL")
        failures += 1

    print("=" * 60)
    if failures == 0:
        log("🎉 ALL 7 SMOKE PROBES PASSED.", "PASS")
        return 0
    log(f"⚠️ SMOKE PROBES FAILED: {failures} probe(s) failed.", "FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(run_sanity_suite())
