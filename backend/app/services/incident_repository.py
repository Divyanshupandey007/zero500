import json
from typing import List,Optional
import psycopg
from app.config import settings
from app.models.incident import IncidentDetail,IncidentSummary,LogEntry,Severity,LogLevel
from app.data.synthetic import SYNTHETIC_INCIDENTS

class IncidentRepository:
    def get_connection(self):
        return psycopg.connect(settings.DATABASE_URL)

    def seed_initial_incidents_if_empty(self):
        """Seeds the 3 demo incidents of table is empty"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM incidents;")
                if cur.fetchone()[0]==0:
                    for inc in SYNTHETIC_INCIDENTS:
                        self.save_incident(inc)
                    conn.commit()

    def save_incident(self,inc:IncidentDetail):
        """Insert or update an incident and its associated logs"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO incidents(id,title,service,severity,status,description,metrics_snapshot,created_at)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT(id) DO UPDATE SET
                        title=EXCLUDED.title,
                        status=EXCLUDED.status,
                        metrics_snapshot=EXCLUDED.metrics_snapshot;
                """,(
                    inc.id,inc.title,inc.service,inc.severity.value,inc.status,inc.description,json.dumps(inc.metrics_snapshot),inc.created_at
                ))

                cur.execute("DELETE FROM incident_logs WHERE incident_id=%s;",(inc.id,))

                for log in inc.logs:
                    cur.execute("""
                        INSERT INTO incident_logs(incident_id,timestamp,level,service,message,metadata)
                        VALUES (%s,%s,%s,%s,%s,%s);
                        """,(inc.id,log.timestamp,log.level.value,log.service,log.message,json.dumps(log.metadata)
                             ))

                conn.commit()

    def list_all_summaries(self)->List[IncidentSummary]:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id,title,service,severity,status,created_at
                    FROM incidents
                    ORDER BY created_at DESC;
                """)
                rows=cur.fetchall()
                return[
                    IncidentSummary(
                        id=r[0],
                        title=r[1],
                        service=r[2],
                        severity=Severity(r[3]),
                        status=r[4],
                        created_at=r[5]
                    )
                    for r in rows
                ]

    def get_incident_by_id(self,incident_id:str)->Optional[IncidentDetail]:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id,title,service,severity,status,description,metrics_snapshot,created_at
                    FROM incidents WHERE LOWER(id)=LOWER(%s);
                """,(incident_id,))
                row=cur.fetchone()
                if not row:
                    return None

                cur.execute("""
                    SELECT timestamp,level,service,message,metadata
                    FROM incident_logs
                    WHERE LOWER(incident_id)=LOWER(%s)
                    ORDER BY timestamp ASC;
                """,(incident_id,))
                log_rows=cur.fetchall()
                logs=[
                    LogEntry(
                        timestamp=lr[0],
                        level=LogLevel(lr[1]),
                        service=lr[2],
                        message=lr[3],
                        metadata=lr[4] if isinstance(lr[4],dict) else {}
                    )
                    for lr in log_rows
                ]

        return IncidentDetail(
            id=row[0],
            title=row[1],
            service=row[2],
            severity=Severity(row[3]),
            status=row[4],
            description=row[5],
            metrics_snapshot=row[6] if isinstance(row[6],dict) else {},
            created_at=row[7],
            logs=logs
        )

incident_repo=IncidentRepository()