from fastapi import APIRouter,HTTPException
from typing import List
from app.models.incident import IncidentSummary,IncidentDetail
from app.data.synthetic import SYNTHETIC_INCIDENTS
from app.models.investigation import InvestigationReport
from app.services.investigator import investigator_service
from app.services.vector_store import vector_store
from app.models.evaluation import EvaluationSuiteReport
from app.services.evaluator import evaluation_engine

router=APIRouter(prefix="/api/v1")

@router.get("/health",tags=["System"])
def health_check():
    return {"status":"ok","app":"Zero500"}

@router.get("/incidents",response_model=List[IncidentSummary],tags=["Incidents"])
def list_incidents():
    """List of all demo incidents."""
    return[
        IncidentSummary(
            id=inc.id,
            title=inc.title,
            service=inc.service,
            severity=inc.severity,
            created_at=inc.created_at,
            status=inc.status,
        )
        for inc in SYNTHETIC_INCIDENTS
    ]

@router.get("/incidents/{incident_id}",response_model=IncidentDetail,tags=["Incidents"])
def get_incident(incident_id:str):
    """Retrieve full incident details including logs and metrics."""
    for inc in SYNTHETIC_INCIDENTS:
        if inc.id.lower()==incident_id.lower():
            return inc
    raise HTTPException(status_code=404,detail="Incident not found")

@router.post("/incidents/{incident_id}/investigate",response_model=InvestigationReport,tags=["Investigation"])
def investigate_incident(incident_id:str):
    """Trigger an AI investigation for a given incident."""
    target_incident=None
    for inc in SYNTHETIC_INCIDENTS:
        if inc.id.lower()==incident_id.lower():
            target_incident=inc
            break

    if not target_incident:
        raise HTTPException(status_code=404,detail="Incident not found")

    try:
        report=investigator_service.investigate(target_incident)
        return report
    except Exception as e:
        raise HTTPException(status_code=500,detail=f"Investigation failed: {str(e)}")

@router.get("/runbooks/search",tags=["Knowledge Base"])
def search_runbooks(query:str,limit:int=2):
    """Semantic vector search over SRE runbooks using pgvector"""
    try:
        results=vector_store.search_similar_docs(query,limit=limit)
        return {"query":query,"matches":results}
    except Exception as e:
        raise HTTPException(status_code=500,detail=f"Search failed: {str(e)}")

@router.post("/evaluations/run",response_model=EvaluationSuiteReport,tags=["Evaluation"])
def run_evaluation_suite():
    """Execute the automated evaluation suite against ground-truth benchmarks"""
    try:
        report=evaluation_engine.run_suite()
        return report
    except Exception as e:
        raise HTTPException(status_code=500,detail=f"Evaluation failed: {str(e)}")