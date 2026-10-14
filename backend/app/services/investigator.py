from google import genai
from app.config import settings
from app.models.incident import IncidentDetail
from app.models.investigation import InvestigationReport

class IncidentInvestigator:
    def __init__(self):
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not set. Please add it to your .env file.")

        self.client=genai.Client(api_key=settings.GEMINI_API_KEY)

    def investigate(self,incident:IncidentDetail)->InvestigationReport:
        logs_text="\n".join([
            f"[{log.timestamp.isoformat()}] [{log.level.value}] {log.service}:{log.message}"
            for log in incident.logs
        ])

        metrics_text="\n".join([f"- {k}: {v}" for k,v in incident.metrics_snapshot.items()])

        system_instruction=(
            "You are Zero500, a Principal Site Reliability Engineer (SRE). "
            "Your job is to perform autonomous root cause analysis (RCA) on production incidents. "
            "Analyze the provided incident details, logs, and telemetry metrics. "
            "Ground your conclusions strictly on the evidence provided. Do not hallucinate."
        )

        user_prompt=f"""
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
            contents=[system_instruction,user_prompt],
            config={
                "response_mime_type":"application/json",
                "response_schema":InvestigationReport,
                "temperature":0.1,
            },
        )

        return response.parsed

investigator_service=IncidentInvestigator()