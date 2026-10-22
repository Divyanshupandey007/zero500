from typing import Literal
from pydantic import BaseModel,Field

class CreateRunbook(BaseModel):
    title:str=Field(min_length=1,description="Description title of the runbook or post-mortem")
    service:str=Field(min_length=1,description="Target microservice name")
    doc_type:Literal["RUNBOOK","PAST_POSTMORTEM"]=Field(default="RUNBOOK")
    content:str=Field(min_length=1,description="Markdown/plain-text troubleshooting steps and CLI commands")