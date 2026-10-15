from app.services.vector_store import vector_store

RUNBOOKS_DATA = [
    {
        "title": "Runbook: Checkout Service NullPointer & Auth Failure Triage",
        "service": "checkout-service",
        "doc_type": "RUNBOOK",
        "content": (
            "Symptoms: Spike in HTTP 500 errors after deployments on /api/v1/checkout. "
            "Stack trace points to TenantInterceptor or OrderController NullPointerException. "
            "Action Plan: "
            "1. Check if the session context is missing tenant headers. "
            "2. If regression occurred post-deploy, immediately execute rollback command: "
            "'helm rollback checkout-service-prod'. "
            "3. Notify #incident-checkout on Slack."
        )
    },
    {
        "title": "Runbook: HikariCP Connection Pool Exhaustion on Postgres Services",
        "service": "users-service",
        "doc_type": "RUNBOOK",
        "content": (
            "Symptoms: Microservice logs 'Connection is not available, request timed out after 30000ms' "
            "or 'FATAL: remaining connection slots are reserved for non-replication superuser connections'. "
            "Remediation: "
            "1. Inspect active database queries: 'SELECT pid, query, state FROM pg_stat_activity WHERE state != 'idle';' "
            "2. Identify long-running unindexed transactions locking connections. "
            "3. Temporarily scale up max_connections on PgBouncer or restart hung worker pods."
        )
    },
    {
        "title": "Post-Mortem: Q3 Stripe Gateway Latency Outage",
        "service": "payment-gateway-proxy",
        "doc_type": "PAST_POSTMORTEM",
        "content": (
            "Historical Incident Report (INC-4029): Upstream Stripe payment gateway suffered a degradation, "
            "causing request latency to spike from 200ms to 9000ms. "
            "Root Cause: Missing socket timeout configuration caused all Tomcat threads to hang waiting for responses. "
            "Resolution: Configured CircuitBreaker with 3000ms threshold and fallback error response. "
            "Verify CircuitBreaker state (HALF_OPEN / OPEN) in Prometheus metrics."
        )
    }
]

def seed():
    print("Connecting to DB and initializing schema...")
    vector_store.init_db()

    with vector_store.get_connection() as conn:
        with conn.cursor() as cur:
            #Check if alreadt seeded
            cur.execute("SELECT COUNT(*) FROM runbooks;")
            count=cur.fetchone()[0]
            if count>0:
                print(f"DB already contains {count} runbook entries. Skipping seed")
                return

            print("Generating embeddings and insert runbooks...")
            for doc in RUNBOOKS_DATA:
                print(f" Embedding doc: {doc['title']}...")
                embedding=vector_store.get_embedding(f"{doc['title']}\n{doc['content']}")
                cur.execute("""
                    INSERT INTO runbooks (title,service,doc_type,content,embedding)
                    VALUES (%s,%s,%s,%s,%s);
""",(doc['title'],doc['service'],doc['doc_type'],doc['content'],embedding))

            conn.commit()
            print("Successfully seeded runbooks into pgvector!")

if __name__=="__main__":
    seed()