from datetime import datetime, timezone
from app.models.incident import IncidentDetail, LogEntry, LogLevel, Severity

SYNTHETIC_INCIDENTS = [
    IncidentDetail(
        id="INC-5001",
        title="Elevated HTTP 500 errors on /api/v1/checkout post-deployment",
        service="checkout-service",
        severity=Severity.CRITICAL,
        status="INVESTIGATING",
        created_at=datetime(2026, 10, 12, 14, 23, 0, tzinfo=timezone.utc),
        description="Spike in 500 status codes immediately following release v2.4.1 deployment to production.",
        metrics_snapshot={
            "error_rate_percentage": 24.5,
            "latency_p99_ms": 1240,
            "pod_restart_count": 0
        },
        logs=[
            LogEntry(
                timestamp=datetime(2026, 10, 12, 14, 21, 10, tzinfo=timezone.utc),
                level=LogLevel.INFO,
                service="checkout-service",
                message="Deployment v2.4.1 rollout complete on cluster us-east-1."
            ),
            LogEntry(
                timestamp=datetime(2026, 10, 12, 14, 22, 5, tzinfo=timezone.utc),
                level=LogLevel.ERROR,
                service="checkout-service",
                message="NullPointerException: Cannot read field 'tenant_id' because 'session' is null at OrderController.process(OrderController.java:84)"
            ),
            LogEntry(
                timestamp=datetime(2026, 10, 12, 14, 22, 12, tzinfo=timezone.utc),
                level=LogLevel.ERROR,
                service="checkout-service",
                message="Handler dispatch failed; nested exception is java.lang.NullPointerException at TenantInterceptor.preHandle"
            )
        ]
    ),
    IncidentDetail(
        id="INC-5002",
        title="PostgreSQL connection pool exhausted on users-service",
        service="users-service",
        severity=Severity.HIGH,
        status="INVESTIGATING",
        created_at=datetime(2026, 10, 12, 11, 5, 0, tzinfo=timezone.utc),
        description="Users microservice failing health checks; unable to acquire database connection from HikariCP pool.",
        metrics_snapshot={
            "active_connections": 100,
            "max_connections": 100,
            "connection_timeout_ms": 30000
        },
        logs=[
            LogEntry(
                timestamp=datetime(2026, 10, 12, 11, 3, 20, tzinfo=timezone.utc),
                level=LogLevel.WARN,
                service="users-service",
                message="HikariPool-1 - Connection is not available, request timed out after 30000ms."
            ),
            LogEntry(
                timestamp=datetime(2026, 10, 12, 11, 4, 15, tzinfo=timezone.utc),
                level=LogLevel.ERROR,
                service="users-service",
                message="org.postgresql.util.PSQLException: FATAL: remaining connection slots are reserved for non-replication superuser connections"
            )
        ]
    ),
    IncidentDetail(
        id="INC-5003",
        title="Third-party payment gateway latency triggering cascading timeout",
        service="payment-gateway-proxy",
        severity=Severity.MEDIUM,
        status="INVESTIGATING",
        created_at=datetime(2026, 10, 12, 8, 45, 0, tzinfo=timezone.utc),
        description="Outbound calls to external Stripe gateway exceeding standard 2500ms timeout threshold.",
        metrics_snapshot={
            "gateway_latency_p95_ms": 8400,
            "circuit_breaker_state": "HALF_OPEN",
            "dropped_requests": 142
        },
        logs=[
            LogEntry(
                timestamp=datetime(2026, 10, 12, 8, 43, 0, tzinfo=timezone.utc),
                level=LogLevel.WARN,
                service="payment-gateway-proxy",
                message="Upstream gateway response time degraded: average 6200ms."
            ),
            LogEntry(
                timestamp=datetime(2026, 10, 12, 8, 44, 11, tzinfo=timezone.utc),
                level=LogLevel.ERROR,
                service="payment-gateway-proxy",
                message="ClientRequestTimeoutException: SocketTimeoutException reading from https://api.stripe.com/v1/charges after 5000ms"
            )
        ]
    )
]