from google import genai
from google.genai import types
from app.config import settings
from app.models.incident import IncidentDetail
from app.models.investigation import InvestigationReport,MatchedRunbook
from app.services.vector_store import vector_store

class IncidentInvestigator:
    def __init__(self):
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not set. Please add it to your .env file.")

        self.client=genai.Client(api_key=settings.GEMINI_API_KEY)

    def build_retrieval_query(self,incident:IncidentDetail)->str:
        """Extract the most salient symptoms to query the vector database"""
        error_messages=[log.message for log in incident.logs if log.level.value in ("ERROR","FATAL","WARN")]
        sample_errors=" ".join(error_messages[:2])
        return f"{incident.title} {incident.service} {sample_errors}"

    def investigate(self,incident:IncidentDetail)->InvestigationReport:
        # Retrieval step
        retrieval_query=self.build_retrieval_query(incident)
        retrieved_docs=vector_store.search_similar_docs(retrieval_query,limit=2)

        runbooks_context="\n\n".join([
            f"--- [Retrieved {doc['doc_type']}: {doc['title']} (Similarity): {doc['similarity_score']})] ---\n{doc['content']}" for doc in retrieved_docs])

        # Telemetry preparation
        logs_text="\n".join([
            f"[{log.timestamp.isoformat()}] [{log.level.value}] {log.service}:{log.message}"
            for log in incident.logs
        ])

        metrics_text="\n".join([f"- {k}: {v}" for k,v in incident.metrics_snapshot.items()])

        system_instruction=(
            "You are Zero500, a Principal Site Reliability Engineer (SRE). "
            "Your job is to perform autonomous root cause analysis (RCA) on production incidents. "
            "You have access to live telemetry (logs and metrics) AND organizational knowledge (Runbooks/Post-Mortems). "
            "Correlate the live telemetry with the retrieved runbooks to provide a high-confidence diagnosis "
            "and an actionable remediation plan. If a runbook provides exact diagnostic or fix commands, cite them."
        )

        user_prompt=f"""
        LIVE INCIDENT TELEMETRY:
Incident ID: {incident.id}
Title: {incident.title}
Service: {incident.service}
Severity: {incident.severity.value}
Description; {incident.description}

Telemetry Metrics: {metrics_text}

Application Logs:{logs_text}

Perform a deep investigation and return a structured incident report.
"""

        response=self.client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=InvestigationReport,
                temperature=0.1,
            ),
        )

        report:InvestigationReport= response.parsed

        report.matched_runbooks=[
            MatchedRunbook(
                title=doc["title"],
                doc_type=doc["doc_type"],
                similarity_score=doc["similarity_score"]
            )
            for doc in retrieved_docs
        ]

        return report

investigator_service=IncidentInvestigator()