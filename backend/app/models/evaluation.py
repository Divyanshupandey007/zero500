from pydantic import BaseModel, Field
from typing import List,Dict

class TestCaseResult(BaseModel):
    incident_id:str
    retrieval_success:bool=Field(description="Was the correct runbook retrieved in Top-k?")
    faithfulness_score:float=Field(ge=0.0,le=1.0,description="Ratio of cited evidence items that actually exist in telemetry")
    diagnosis_alignment_score:float=Field(ge=0.0,le=1.0,description="Semantic match between predicted root cause and ground truth (LLM Judge)")
    latency_seconds:float
    details:Dict[str,str]

class EvaluationSuiteReport(BaseModel):
    total_test_case:int
    retrieval_recall:float=Field(description="Percentage of cases where ground truth runbook was retrieved")
    average_faithfulness:float=Field(description="Average evidence grounding score across all tests")
    average_diagnosis_accuracy:float=Field(description="Average LLM-as-a-judge score")
    average_latency_seconds:float
    test_cases:List[TestCaseResult]