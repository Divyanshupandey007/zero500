"""Integration tests for the ``POST /incidents/{id}/investigate`` endpoint.

The FastAPI app is exercised with TestClient while the Gemini client and the
database are fully mocked, so no real API call or network request is made.
"""

from limits.storage import MemoryStorage

from app.main import app
from app.services.incident_repository import incident_repo
from app.services.investigator import investigator_service


def test_investigate_returns_schema_valid_response(client, incident, report, mocker):
    mocker.patch.object(incident_repo, "get_incident_by_id", return_value=incident)
    mocker.patch.object(investigator_service, "investigate", return_value=report)

    response = client.post("/api/v1/incidents/INC-TEST-01/investigate")

    assert response.status_code == 200
    data = response.json()
    assert data["incident_id"] == "INC-TEST-01"
    assert isinstance(data["confidence_score"], (int, float))
    assert 0.0 <= data["confidence_score"] <= 1.0
    assert "evidence" in data
    assert "suspected_root_cause" in data
    assert "executive_summary" in data
    investigator_service.investigate.assert_called_once_with(incident)


def test_investigate_returns_404_when_incident_missing(client, mocker):
    mocker.patch.object(incident_repo, "get_incident_by_id", return_value=None)

    response = client.post("/api/v1/incidents/INC-DOES-NOT-EXIST/investigate")

    assert response.status_code == 404


def test_investigate_respects_five_requests_per_minute_rate_limit(
    client, incident, report, mocker
):
    # Reset the in-memory SlowAPI storage so this test is deterministic
    # regardless of earlier requests to rate-limited routes.
    app.state.limiter._storage = MemoryStorage()

    mocker.patch.object(incident_repo, "get_incident_by_id", return_value=incident)
    mocker.patch.object(investigator_service, "investigate", return_value=report)

    # First request in the window should succeed.
    first = client.post("/api/v1/incidents/INC-TEST-01/investigate")
    assert first.status_code == 200

    # Hammer the endpoint: the 5/minute SlowAPI limit must eventually 429.
    status_codes = [
        client.post("/api/v1/incidents/INC-TEST-01/investigate").status_code
        for _ in range(7)
    ]
    assert 429 in status_codes, f"expected a 429 within the window, got {status_codes}"
    # Not every request is rate-limited; the service still answers when under quota.
    assert 200 in status_codes
