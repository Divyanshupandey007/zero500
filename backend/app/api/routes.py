from fastapi import APIRouter,HTTPException,Request
from typing import List
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings
from app.models.incident import IncidentSummary,IncidentDetail
from app.data.synthetic import SYNTHETIC_INCIDENTS
from app.models.investigation import InvestigationReport
from app.services.investigator import investigator_service
from app.services.incident_repository import incident_repo
from app.services.vector_store import vector_store
from app.models.evaluation import EvaluationSuiteReport
from app.services.evaluator import evaluation_engine

limiter=Limiter(key_func=get_remote_address)
router=APIRouter(prefix="/api/v1")

@router.get("/health",tags=["System"])
def health_check():
    try:
        with incident_repo.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
        return {
            "status":"healthy",
            "database":"connected",
            "model":settings.GEMINI_MODEL
        }
    except Exception as e:
        return {
            "status":"degraded",
            "error":str(e)
        }

@router.get("/runbooks/search", tags=["Knowledge"])
def search_runbooks(query: str, limit: int = 2):
    try:
        matches = vector_store.search_similar_docs(query, limit=limit)
        return {"matches": matches}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/incidents",response_model=List[IncidentSummary],tags=["Incidents"])
def list_incidents():
    return incident_repo.list_all_summaries()

@router.get("/incidents/{incident_id}",response_model=IncidentDetail,tags=["Incidents"])
def get_incident(incident_id:str):
    inc=incident_repo.get_incident_by_id(incident_id)
    if not inc:
        raise HTTPException(status_code=404,detail="Incident not found")
    return inc

@router.post("/incidents/ingest",response_model=IncidentSummary,tags=["Incidents"])
def ingest_incident(incident:IncidentDetail):
    """
    Live Telemetry Webhook: Ingest arbitrary production incidents from AlertManager,Datadog, PagerDuty or UI
    """

    try:
        incident_repo.save_incident(incident)
        return IncidentSummary(
            id=incident.id,
            title=incident.title,
            service=incident.service,
            severity=incident.severity,
            created_at=incident.created_at,
            status=incident.status
        )
    except Exception as e:
        raise HTTPException(status_code=500,detail=f"Ingestion failed: {str(e)}")

@router.post("/incidents/{incident_id}/investigate",response_model=InvestigationReport,tags=["Investigation"])
@limiter.limit("5/minute")
def investigate_incident(request:Request,incident_id:str):
    inc=incident_repo.get_incident_by_id(incident_id)
    if not inc:
        raise HTTPException(status_code=404,detail="Incident not found")

    try:
        return investigator_service.investigate(inc)
    except Exception as e:
        raise HTTPException(status_code=500,detail=f"Investigation failed: {str(e)}")

@router.post("/evaluations/run",response_model=EvaluationSuiteReport,tags=["Evaluation"])
@limiter.limit("2/minute")
def run_evaluation_suite(request:Request):
    try:
        return evaluation_engine.run_suite()
    except Exception as e:
        raise HTTPException(status_code=500,detail=f"Evaluation failed: {str(e)}")