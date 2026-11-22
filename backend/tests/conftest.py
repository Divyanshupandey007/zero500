"""Shared pytest fixtures for the Zero500 backend test suite.

All fixtures run against a fully mocked backend: no real PostgreSQL/Neon
connection and no real Gemini API call are ever made, so the suite can run
offline and in CI with zero external network calls.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.incident import (
    IncidentDetail,
    LogEntry,
    LogLevel,
    Severity,
)
from app.models.investigation import InvestigationReport, MatchedRunbook
from app.services.incident_repository import incident_repo
from app.services.investigator import investigator_service
from app.services.vector_store import vector_store


def _make_incident(incident_id: str = "INC-TEST-01") -> IncidentDetail:
    return IncidentDetail(
        id=incident_id,
        title="Test incident",
        service="test-service",
        severity=Severity.HIGH,
        status="INVESTIGATING",
        created_at="2026-01-01T00:00:00+00:00",
        description="A test incident.",
        metrics_snapshot={"error_rate": 0.05},
        logs=[
            LogEntry(
                timestamp="2026-01-01T00:00:00+00:00",
                level=LogLevel.ERROR,
                service="test-service",
                message="Something went wrong",
                metadata={},
            )
        ],
    )


def _make_report(incident_id: str = "INC-TEST-01") -> InvestigationReport:
    return InvestigationReport(
        incident_id=incident_id,
        executive_summary="A test summary.",
        suspected_root_cause="A test root cause.",
        confidence_score=0.9,
        matched_runbooks=[
            MatchedRunbook(
                title="Runbook: Test",
                doc_type="RUNBOOK",
                similarity_score=0.91,
            )
        ],
        evidence=[
            {"source": "2026-01-01 ERROR", "detail": "Something went wrong"}
        ],
        remediation_plan=[],
        requires_human_escalation=False,
    )


@pytest.fixture(autouse=True)
def _no_real_db_init(mocker: Any) -> None:
    """Prevent the FastAPI lifespan from touching a real database."""
    mocker.patch.object(vector_store, "init_db", return_value=None)
    mocker.patch.object(
        incident_repo, "seed_initial_incidents_if_empty", return_value=None
    )


@pytest.fixture
def client(mocker: Any) -> TestClient:
    """A TestClient backed by mocked DB/Gemini singletons.

    The route-level singletons (imported by name into ``app.api.routes``) are
    the same module-level objects used by ``app.main``, so patching their
    methods here is enough to make every endpoint run without a database or
    the Gemini API.
    """
    # DB connections become no-op context managers.
    mocker.patch.object(vector_store, "get_connection")
    mocker.patch.object(incident_repo, "get_connection")

    # Gemini-backed investigation is replaced with a deterministic mock.
    mocker.patch.object(investigator_service, "investigate")

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def incident() -> IncidentDetail:
    return _make_incident()


@pytest.fixture
def report() -> InvestigationReport:
    return _make_report()
