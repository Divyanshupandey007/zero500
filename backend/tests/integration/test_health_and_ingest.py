"""Integration tests for ``/health`` and ``POST /incidents/ingest``.

Happy-path and bad-payload cases are covered with the database fully mocked,
so no real PostgreSQL connection is required.
"""

from app.services.incident_repository import incident_repo
from app.services.vector_store import vector_store

INGEST_PAYLOAD = {
    "id": "INC-INGEST-01",
    "title": "Ingested telemetry incident",
    "service": "order-pipeline",
    "severity": "HIGH",
    "status": "INVESTIGATING",
    "created_at": "2026-01-01T00:00:00+00:00",
    "description": "Kafka consumer groups failing to commit offsets.",
    "metrics_snapshot": {"consumer_lag": 14200},
    "logs": [
        {
            "timestamp": "2026-01-01T00:00:00+00:00",
            "level": "ERROR",
            "service": "order-pipeline",
            "message": "OffsetCommitTimeout: failed to commit offsets.",
        }
    ],
}


def test_health_returns_healthy_when_database_reachable(client):
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"


def test_health_returns_degraded_when_database_unreachable(client, mocker):
    mocker.patch.object(
        incident_repo, "get_connection", side_effect=RuntimeError("down")
    )

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert "error" in data


def test_ingest_incident_happy_path(client):
    response = client.post("/api/v1/incidents/ingest", json=INGEST_PAYLOAD)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "INC-INGEST-01"
    assert data["title"] == "Ingested telemetry incident"
    assert data["service"] == "order-pipeline"


def test_ingest_incident_rejects_bad_payload(client):
    response = client.post("/api/v1/incidents/ingest", json={"not": "an incident"})

    assert response.status_code == 422


def test_search_runbooks_returns_matches(client, mocker):
    mocker.patch.object(
        vector_store,
        "search_similar_docs",
        return_value=[
            {
                "id": 1,
                "title": "Runbook: HikariCP Connection Pool Exhaustion",
                "doc_type": "RUNBOOK",
                "content": "Check pg_stat_activity.",
                "similarity_score": 0.675,
            }
        ],
    )

    response = client.get("/api/v1/runbooks/search?query=connection%20pool&limit=1")

    assert response.status_code == 200
    data = response.json()
    assert len(data["matches"]) == 1
    assert data["matches"][0]["title"].startswith("Runbook: HikariCP")


def test_list_incidents_returns_summaries(client, mocker):
    from datetime import datetime

    from app.models.incident import IncidentSummary

    mocker.patch.object(
        incident_repo,
        "list_all_summaries",
        return_value=[
            IncidentSummary(
                id="INC-5001",
                title="Checkout 500s",
                service="checkout-service",
                severity="HIGH",
                created_at=datetime(2026, 1, 1, tzinfo=None),
                status="INVESTIGATING",
            )
        ],
    )

    response = client.get("/api/v1/incidents")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "INC-5001"


def test_get_incident_returns_detail(client, mocker, incident):
    mocker.patch.object(incident_repo, "get_incident_by_id", return_value=incident)

    response = client.get("/api/v1/incidents/INC-TEST-01")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "INC-TEST-01"
    assert data["service"] == "test-service"


def test_get_incident_returns_404_when_missing(client, mocker):
    mocker.patch.object(incident_repo, "get_incident_by_id", return_value=None)

    response = client.get("/api/v1/incidents/INC-MISSING")

    assert response.status_code == 404


def test_create_runbook_indexes_document(client, mocker):
    mocker.patch.object(vector_store, "add_runbook", return_value=42)

    response = client.post(
        "/api/v1/runbooks",
        json={
            "title": "New Runbook",
            "service": "svc",
            "doc_type": "RUNBOOK",
            "content": "Do this then that.",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 42
    assert data["status"] == "indexed"
