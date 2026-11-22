"""Unit tests for the ``InvestigationReport`` Pydantic v2 contract.

Validates that well-formed LLM output is accepted and that malformed or
incomplete output is rejected, using inline fixture JSON for both cases.
"""

import json

import pytest
from pydantic import ValidationError

from app.models.investigation import (
    ActionPriority,
    EvidenceItem,
    InvestigationReport,
    MatchedRunbook,
)

VALID_REPORT_FIXTURE = {
    "incident_id": "INC-5001",
    "executive_summary": "Checkout service 500s after v2.4.1 deploy.",
    "suspected_root_cause": "Null tenant session in TenantInterceptor post-deploy.",
    "confidence_score": 0.92,
    "matched_runbooks": [
        {
            "title": "Runbook: Checkout Service NullPointer & Auth Failure Triage",
            "doc_type": "RUNBOOK",
            "similarity_score": 0.91,
        }
    ],
    "evidence": [
        {
            "source": "2026-10-12T14:22:05Z ERROR",
            "detail": "NullPointerException at OrderController.process line 84",
        }
    ],
    "remediation_plan": [
        {
            "action": "Roll back checkout-service to v2.4.0",
            "priority": "IMMEDIATE",
            "description": "Revert the deployment that introduced the null session.",
            "runbook_reference": "Runbook: Checkout Service NullPointer & Auth Failure Triage",
        }
    ],
    "requires_human_escalation": False,
}

MALFORMED_FIXTURES = [
    {
        "name": "missing required incident_id",
        "data": {**VALID_REPORT_FIXTURE, "incident_id": None},
    },
    {
        "name": "confidence_score out of range (> 1.0)",
        "data": {**VALID_REPORT_FIXTURE, "confidence_score": 1.5},
    },
    {
        "name": "confidence_score out of range (< 0.0)",
        "data": {**VALID_REPORT_FIXTURE, "confidence_score": -0.1},
    },
    {
        "name": "missing required evidence list",
        "data": {k: v for k, v in VALID_REPORT_FIXTURE.items() if k != "evidence"},
    },
    {
        "name": "remediation step with invalid priority enum",
        "data": {
            **VALID_REPORT_FIXTURE,
            "remediation_plan": [
                {
                    "action": "Do something",
                    "priority": "NOT_A_PRIORITY",
                    "description": "Fix it",
                }
            ],
        },
    },
    {
        "name": "matched runbook missing similarity_score",
        "data": {
            **VALID_REPORT_FIXTURE,
            "matched_runbooks": [
                {"title": "X", "doc_type": "RUNBOOK"}
            ],
        },
    },
]


def test_valid_report_parses_from_fixture() -> None:
    report = InvestigationReport.model_validate(VALID_REPORT_FIXTURE)
    assert report.incident_id == "INC-5001"
    assert report.confidence_score == 0.92
    assert len(report.matched_runbooks) == 1
    assert report.matched_runbooks[0].title.startswith("Runbook: Checkout")
    assert len(report.evidence) == 1
    assert report.evidence[0].source.endswith("ERROR")
    assert report.remediation_plan[0].priority == ActionPriority.IMMEDIATE


def test_valid_report_round_trips_to_dict() -> None:
    report = InvestigationReport.model_validate(VALID_REPORT_FIXTURE)
    data = report.model_dump()
    assert data["incident_id"] == "INC-5001"
    assert data["confidence_score"] == 0.92


@pytest.mark.parametrize("case", MALFORMED_FIXTURES, ids=[c["name"] for c in MALFORMED_FIXTURES])
def test_malformed_report_is_rejected(case: dict) -> None:
    with pytest.raises(ValidationError):
        InvestigationReport.model_validate(case["data"])


def test_evidence_item_requires_source_and_detail() -> None:
    with pytest.raises(ValidationError):
        EvidenceItem(source="x")


def test_matched_runbook_requires_all_fields() -> None:
    with pytest.raises(ValidationError):
        MatchedRunbook(title="only title")


def test_round_trip_through_json() -> None:
    report = InvestigationReport.model_validate(VALID_REPORT_FIXTURE)
    reparsed = InvestigationReport.model_validate_json(
        json.dumps(report.model_dump())
    )
    assert reparsed.incident_id == report.incident_id
    assert reparsed.confidence_score == report.confidence_score
