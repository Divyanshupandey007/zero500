EVAL_GROUND_TRUTH = [
    {
        "incident_id": "INC-5001",
        "expected_runbook_keyword": "Checkout Service NullPointer",
        "ground_truth_root_cause": (
            "Deployment v2.4.1 introduced a regression where session object is null in "
            "TenantInterceptor or OrderController, causing a NullPointerException."
        ),
        "expected_immediate_action": "rollback"
    },
    {
        "incident_id": "INC-5002",
        "expected_runbook_keyword": "HikariCP Connection Pool Exhaustion",
        "ground_truth_root_cause": (
            "The users-service saturated the HikariCP database connection pool (100/100) and "
            "Postgres max_connections was reached, preventing non-superuser connections."
        ),
        "expected_immediate_action": "restart"
    },
    {
        "incident_id": "INC-5003",
        "expected_runbook_keyword": "Stripe Gateway Latency",
        "ground_truth_root_cause": (
            "High latency from external Stripe payment gateway triggered client socket timeouts "
            "and placed the circuit breaker into HALF_OPEN state."
        ),
        "expected_immediate_action": "circuit breaker"
    }
]