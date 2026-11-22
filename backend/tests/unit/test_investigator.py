"""Unit tests for the incident investigator service.

The Gemini client and the vector store are mocked so no real API call or
database query is made.
"""

from unittest.mock import MagicMock

from app.models.incident import (
    IncidentDetail,
    LogEntry,
    LogLevel,
    Severity,
)
from app.models.investigation import InvestigationReport
from app.services import vector_store as vector_store_module
from app.services.investigator import investigator_service


def _make_incident(incident_id: str = "INC-INV-01") -> IncidentDetail:
    return IncidentDetail(
        id=incident_id,
        title="Checkout 500s after deploy",
        service="checkout-service",
        severity=Severity.CRITICAL,
        status="INVESTIGATING",
        created_at="2026-01-01T00:00:00+00:00",
        description="500s on /checkout",
        metrics_snapshot={"error_rate": 0.25},
        logs=[
            LogEntry(
                timestamp="2026-01-01T00:00:00+00:00",
                level=LogLevel.ERROR,
                service="checkout-service",
                message="NullPointerException at OrderController",
                metadata={},
            )
        ],
    )


def test_investigate_returns_parsed_report(mocker):
    """investigate() should call Gemini, enrich with retrieved runbooks."""

    fake_report = InvestigationReport(
        incident_id="INC-INV-01",
        executive_summary="Summary.",
        suspected_root_cause="Root cause.",
        confidence_score=0.8,
        matched_runbooks=[],
        evidence=[],
        remediation_plan=[],
        requires_human_escalation=False,
    )

    investigator_service.client = MagicMock()
    investigator_service.client.models.generate_content.return_value = (
        MagicMock(parsed=fake_report)
    )

    retrieved = [
        {
            "title": "Runbook: X",
            "doc_type": "RUNBOOK",
            "content": "...",
            "similarity_score": 0.9,
        }
    ]
    mocker.patch.object(
        vector_store_module.vector_store,
        "search_similar_docs",
        return_value=retrieved,
    )

    investigator_service._cache.clear()
    report = investigator_service.investigate(_make_incident())

    assert report.incident_id == "INC-INV-01"
    assert report.confidence_score == 0.8
    assert report.matched_runbooks[0].title == "Runbook: X"
    investigator_service.client.models.generate_content.assert_called_once()


def test_investigate_uses_cache(mocker):
    """A second investigate() for the same incident within TTL returns cached."""

    fake_report = InvestigationReport(
        incident_id="INC-INV-02",
        executive_summary="Summary.",
        suspected_root_cause="Root cause.",
        confidence_score=0.5,
        matched_runbooks=[],
        evidence=[],
        remediation_plan=[],
        requires_human_escalation=False,
    )

    investigator_service.client = MagicMock()
    investigator_service.client.models.generate_content.return_value = (
        MagicMock(parsed=fake_report)
    )

    mocker.patch.object(
        vector_store_module.vector_store,
        "search_similar_docs",
        return_value=[],
    )

    investigator_service._cache.clear()
    incident = _make_incident(incident_id="INC-INV-02")
    first = investigator_service.investigate(incident)
    second = investigator_service.investigate(incident)

    assert first is second
    investigator_service.client.models.generate_content.assert_called_once()
