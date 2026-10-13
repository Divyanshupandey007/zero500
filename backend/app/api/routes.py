from fastapi import APIRouter,HTTPException
from typing import List
from app.models.incident import IncidentSummary,IncidentDetail
from app.data.synthetic import SYNTHETIC_INCIDENTS

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