from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class ActionPriority(str,Enum):
    IMMEDIATE="IMMEDIATE"
    SHORT_TERM="SHORT_TERM"
    LONG_TERM="LONG_TERM"

class EvidenceItem(BaseModel):
    source:str=Field(description="Log line timestamp, metric name or reference")
    detail:str=Field(description="Why this piece of data supports the diagnosis")

class RemediationStep(BaseModel):
    action:str=Field(description="Action to take, e.g., 'Roll back deployment to v2.4.0")
    priority:ActionPriority
    description:str=Field(description="Detailed explanation of the fix, referencing runbook if applicable")
    runbook_reference:Optional[str]=Field(default=None,description="Title of the runbook this step was derived from")

class MatchedRunbook(BaseModel):
    title:str
    doc_type:str
    similarity_score:float

class InvestigationReport(BaseModel):
    incident_id:str
    executive_summary:str=Field(description="One-sentence plain language summary of the failure")
    suspected_root_cause:str=Field(description="Technical root cause analysis with casual chain")
    confidence_score:float=Field(ge=0.0,le=1.0,description="Confidence between 0.0 and 1.0")
    matched_runbooks:List[MatchedRunbook]=Field(default_factory=List,description="Runbooks retrieved from vector database")
    evidence:List[EvidenceItem]=Field(description="Direct evidence cited from the provided telemetry")
    remediation_plan:List[RemediationStep]=Field(description="Ordered action plan to mitigate and resolve")
    requires_human_escalation:bool=Field(description="Whether an SRE lead or security team must intervene immediately")