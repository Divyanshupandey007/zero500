from pydantic import BaseModel, Field
from typing import List,Optional
from datetime import datetime
from enum import Enum

class Severity(str,Enum):
    LOW="LOW"
    MEDIUM="MEDIUM"
    HIGH="HIGH"
    CRITICAL="CRITICAL"

class LogLevel(str,Enum):
    INFO="INFO"
    WARN="WARN"
    ERROR="ERROR"
    FATAL="FATAL"

class LogEntry(BaseModel):
    timestamp:datetime
    level:LogLevel
    service:str
    message:str
    metadata: Optional[dict]=Field(default_factory=dict)

class IncidentSummary(BaseModel):
    id:str
    title:str
    service:str
    severity:Severity
    created_at:datetime
    status:str

class IncidentDetail(IncidentSummary):
    description:str
    logs:List[LogEntry]
    metrics_snapshot:dict