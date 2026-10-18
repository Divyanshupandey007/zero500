import { Injectable, inject, signal, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of, throwError } from 'rxjs';
import { catchError, tap, delay } from 'rxjs/operators';
import {
  IncidentSummary,
  IncidentDetail,
  InvestigationReport,
  EvaluationSuiteReport
} from '../models/incident.model';
import { SystemMetadata, DEFAULT_SYSTEM_CONFIG } from '../core/config/system.config';

@Injectable({
  providedIn: 'root'
})
export class IncidentService {
  private readonly http = inject(HttpClient);
  public readonly baseUrl = 'http://localhost:8000/api/v1';

  // System Configuration & Metadata (Decoupled & Dynamic)
  public readonly systemConfig = signal<SystemMetadata>(DEFAULT_SYSTEM_CONFIG);

  // State Signals
  public readonly incidents = signal<IncidentSummary[]>([]);
  public readonly selectedIncident = signal<IncidentDetail | null>(null);
  public readonly investigationReports = signal<Record<string, InvestigationReport>>({});
  public readonly evaluationReport = signal<EvaluationSuiteReport | null>(null);

  // Loading & Network Signals
  public readonly isIncidentsLoading = signal<boolean>(false);
  public readonly isIncidentDetailLoading = signal<boolean>(false);
  public readonly isInvestigating = signal<boolean>(false);
  public readonly isEvaluating = signal<boolean>(false);
  public readonly isBackendConnected = signal<boolean>(false);
  public readonly isSimulatedMode = signal<boolean>(false);
  public readonly activeError = signal<string | null>(null);

  // Derived current incident investigation report
  public readonly currentReport = computed(() => {
    const selected = this.selectedIncident();
    if (!selected) return null;
    return this.investigationReports()[selected.id] || null;
  });

  // Mock / Synthetic Fallbacks matching the exact repository data
  private readonly fallbackIncidents: IncidentDetail[] = [
    {
      id: 'INC-5001',
      title: 'Elevated HTTP 500 errors on /api/v1/checkout post-deployment',
      service: 'checkout-service',
      severity: 'CRITICAL',
      status: 'INVESTIGATING',
      created_at: new Date(Date.now() - 1000 * 60 * 35).toISOString(),
      description: 'Spike in 500 status codes immediately following release v2.4.1 deployment to production.',
      metrics_snapshot: {
        error_rate_percentage: 24.5,
        latency_p99_ms: 1240,
        pod_restart_count: 0,
        active_threads: 420,
        cpu_utilization_pct: 68.2
      },
      logs: [
        {
          timestamp: new Date(Date.now() - 1000 * 60 * 37).toISOString(),
          level: 'INFO',
          service: 'checkout-service',
          message: 'Deployment v2.4.1 rollout complete on cluster us-east-1.'
        },
        {
          timestamp: new Date(Date.now() - 1000 * 60 * 36).toISOString(),
          level: 'ERROR',
          service: 'checkout-service',
          message: "NullPointerException: Cannot read field 'tenant_id' because 'session' is null at OrderController.process(OrderController.java:84)"
        },
        {
          timestamp: new Date(Date.now() - 1000 * 60 * 35).toISOString(),
          level: 'ERROR',
          service: 'checkout-service',
          message: 'Handler dispatch failed; nested exception is java.lang.NullPointerException at TenantInterceptor.preHandle'
        },
        {
          timestamp: new Date(Date.now() - 1000 * 60 * 34).toISOString(),
          level: 'WARN',
          service: 'checkout-service',
          message: 'Circuit breaker checkout-downstream-payment trips threshold (error rate > 20%)'
        }
      ]
    },
    {
      id: 'INC-5002',
      title: 'PostgreSQL connection pool exhausted on users-service',
      service: 'users-service',
      severity: 'HIGH',
      status: 'INVESTIGATING',
      created_at: new Date(Date.now() - 1000 * 60 * 120).toISOString(),
      description: 'Users microservice failing health checks; unable to acquire database connection from HikariCP pool.',
      metrics_snapshot: {
        active_connections: 100,
        max_connections: 100,
        connection_timeout_ms: 30000,
        waiting_threads_count: 78,
        db_cpu_usage_pct: 94.1
      },
      logs: [
        {
          timestamp: new Date(Date.now() - 1000 * 60 * 122).toISOString(),
          level: 'WARN',
          service: 'users-service',
          message: 'HikariPool-1 - Connection is not available, request timed out after 30000ms.'
        },
        {
          timestamp: new Date(Date.now() - 1000 * 60 * 121).toISOString(),
          level: 'ERROR',
          service: 'users-service',
          message: 'org.postgresql.util.PSQLException: FATAL: remaining connection slots are reserved for non-replication superuser connections'
        },
        {
          timestamp: new Date(Date.now() - 1000 * 60 * 120).toISOString(),
          level: 'ERROR',
          service: 'users-service',
          message: 'Failed to complete tenant auth query: connection pool starvation timeout'
        }
      ]
    },
    {
      id: 'INC-5003',
      title: 'Third-party payment gateway latency triggering cascading timeout',
      service: 'payment-gateway-proxy',
      severity: 'MEDIUM',
      status: 'INVESTIGATING',
      created_at: new Date(Date.now() - 1000 * 60 * 340).toISOString(),
      description: 'Outbound calls to external Stripe gateway exceeding standard 2500ms timeout threshold.',
      metrics_snapshot: {
        gateway_latency_p95_ms: 8400,
        circuit_breaker_state: 'HALF_OPEN',
        dropped_requests: 142,
        upstream_failure_pct: 38.6
      },
      logs: [
        {
          timestamp: new Date(Date.now() - 1000 * 60 * 342).toISOString(),
          level: 'WARN',
          service: 'payment-gateway-proxy',
          message: 'Upstream gateway response time degraded: average 6200ms.'
        },
        {
          timestamp: new Date(Date.now() - 1000 * 60 * 341).toISOString(),
          level: 'ERROR',
          service: 'payment-gateway-proxy',
          message: 'ClientRequestTimeoutException: SocketTimeoutException reading from https://api.stripe.com/v1/charges after 5000ms'
        },
        {
          timestamp: new Date(Date.now() - 1000 * 60 * 340).toISOString(),
          level: 'WARN',
          service: 'payment-gateway-proxy',
          message: 'Resilience4j circuit breaker state transitioned from CLOSED to HALF_OPEN'
        }
      ]
    }
  ];

  private readonly fallbackReports: Record<string, InvestigationReport> = {
    'INC-5001': {
      incident_id: 'INC-5001',
      executive_summary: 'Release v2.4.1 broke session context initialization, resulting in NullPointerException for all authenticated checkout transactions.',
      suspected_root_cause: 'Deployment v2.4.1 introduced a regression where the session object is null when TenantInterceptor executes before OrderController, causing a cascade of NullPointerExceptions and 24.5% HTTP 500 error spike.',
      confidence_score: 0.96,
      matched_runbooks: [
        {
          title: 'Runbook: Checkout Service NullPointer & Auth Failure Triage',
          doc_type: 'RUNBOOK',
          similarity_score: 0.894
        },
        {
          title: 'Post-Mortem: Q3 Deployment Interceptor Context Drop',
          doc_type: 'PAST_POSTMORTEM',
          similarity_score: 0.742
        }
      ],
      evidence: [
        {
          source: 'checkout-service log: OrderController.process line 84',
          detail: "Direct NullPointerException reading 'tenant_id' from uninitialized session context."
        },
        {
          source: 'Metrics: error_rate_percentage = 24.5%',
          detail: 'Error rate spiked from baseline 0.05% to 24.5% immediately following v2.4.1 deployment.'
        },
        {
          source: 'checkout-service log: TenantInterceptor.preHandle',
          detail: 'Shows interceptor failing to inject session attributes into request chain.'
        }
      ],
      remediation_plan: [
        {
          action: 'Roll back checkout-service deployment to stable v2.4.0',
          priority: 'IMMEDIATE',
          description: 'Execute instant rollback via Helm to restore healthy order processing: helm rollback checkout-service-prod',
          runbook_reference: 'Runbook: Checkout Service NullPointer & Auth Failure Triage'
        },
        {
          action: 'Verify rollback health and error rate normalization',
          priority: 'IMMEDIATE',
          description: 'Monitor /api/v1/checkout HTTP 500 error rate down below 0.1% within 2 minutes post-rollback.',
          runbook_reference: 'Runbook: Checkout Service NullPointer & Auth Failure Triage'
        },
        {
          action: 'Audit TenantInterceptor null-safety and integration tests',
          priority: 'SHORT_TERM',
          description: 'Add mandatory null-session contract checks and regression unit tests before re-attempting rollout.',
          runbook_reference: null
        },
        {
          action: 'Implement canary deployment gates for checkout microservice',
          priority: 'LONG_TERM',
          description: 'Configure automated Argo Rollouts with Prometheus metric analysis step to abort on 500 spikes.',
          runbook_reference: null
        }
      ],
      requires_human_escalation: false
    },
    'INC-5002': {
      incident_id: 'INC-5002',
      executive_summary: 'HikariCP connection pool saturated at 100/100 capacity, blocking all incoming client queries with timeouts.',
      suspected_root_cause: 'The users-service microservice completely exhausted the HikariCP database connection pool (100 active connections) due to unindexed slow tenant queries locking connections, triggering PostgreSQL superuser slot reservations.',
      confidence_score: 0.94,
      matched_runbooks: [
        {
          title: 'Runbook: HikariCP Connection Pool Exhaustion on Postgres Services',
          doc_type: 'RUNBOOK',
          similarity_score: 0.918
        }
      ],
      evidence: [
        {
          source: 'Metrics: active_connections = 100 / max_connections = 100',
          detail: '100% connection pool saturation with 78 threads queued in starvation.'
        },
        {
          source: 'users-service log: HikariPool-1 request timed out after 30000ms',
          detail: 'Worker threads unable to obtain connection within timeout window.'
        },
        {
          source: 'Postgres error: FATAL remaining connection slots are reserved',
          detail: 'PostgreSQL instance rejected regular client connections due to superuser ceiling.'
        }
      ],
      remediation_plan: [
        {
          action: 'Terminate long-running unindexed queries and restart hung worker pods',
          priority: 'IMMEDIATE',
          description: 'Run SELECT pg_terminate_backend(pid) for idle-in-transaction sessions and restart users-service pods to release pool handles.',
          runbook_reference: 'Runbook: HikariCP Connection Pool Exhaustion on Postgres Services'
        },
        {
          action: 'Increase pool allocation and tune connection leak detection',
          priority: 'SHORT_TERM',
          description: 'Enable leakDetectionThreshold=5000 in HikariCP config and scale PgBouncer connection limit.',
          runbook_reference: 'Runbook: HikariCP Connection Pool Exhaustion on Postgres Services'
        },
        {
          action: 'Optimize query index on tenant_accounts table',
          priority: 'LONG_TERM',
          description: 'Create partial index on tenant_accounts(status, updated_at) to prevent full sequential table scans.',
          runbook_reference: null
        }
      ],
      requires_human_escalation: true
    },
    'INC-5003': {
      incident_id: 'INC-5003',
      executive_summary: 'Stripe external payment gateway latency spike degraded response time to 8.4s, tripping proxy circuit breaker.',
      suspected_root_cause: 'External Stripe API latency degradation caused proxy socket timeouts and tripped Resilience4j circuit breaker into HALF_OPEN state, dropping 142 payment requests.',
      confidence_score: 0.88,
      matched_runbooks: [
        {
          title: 'Post-Mortem: Q3 Stripe Gateway Latency Outage',
          doc_type: 'PAST_POSTMORTEM',
          similarity_score: 0.871
        }
      ],
      evidence: [
        {
          source: 'Metrics: gateway_latency_p95_ms = 8400ms',
          detail: 'Latency spiked to 8.4 seconds exceeding the 2500ms SLA threshold.'
        },
        {
          source: 'payment-gateway-proxy log: ClientRequestTimeoutException after 5000ms',
          detail: 'Socket read timeout triggered on https://api.stripe.com/v1/charges.'
        },
        {
          source: 'Metrics: circuit_breaker_state = HALF_OPEN',
          detail: 'Circuit breaker opened to prevent thread pool starvation across internal callers.'
        }
      ],
      remediation_plan: [
        {
          action: 'Verify fallback queueing and Stripe external status page',
          priority: 'IMMEDIATE',
          description: 'Check status.stripe.com for regional gateway incidents and ensure asynchronous payment queue retry is buffering customer orders.',
          runbook_reference: 'Post-Mortem: Q3 Stripe Gateway Latency Outage'
        },
        {
          action: 'Route non-critical payment retries to secondary backup payment provider',
          priority: 'SHORT_TERM',
          description: 'Flip dynamic feature flag PAYMENT_PROVIDER_FALLBACK_ACTIVE=true to route 50% traffic through Adyen backup pipeline.',
          runbook_reference: null
        },
        {
          action: 'Refactor upstream timeout bounds to 3000ms hard ceiling with exponential backoff',
          priority: 'LONG_TERM',
          description: 'Standardize client timeouts across all third-party integrations with jittered exponential backoff.',
          runbook_reference: 'Post-Mortem: Q3 Stripe Gateway Latency Outage'
        }
      ],
      requires_human_escalation: false
    }
  };

  private readonly fallbackEvaluation: EvaluationSuiteReport = {
    total_test_cases: 3,
    total_test_case: 3,
    retrieval_recall: 1.0,
    average_faithfulness: 0.88,
    average_diagnosis_accuracy: 0.96,
    average_latency_seconds: 2.14,
    test_cases: [
      {
        incident_id: 'INC-5001',
        retrieval_success: true,
        faithfulness_score: 1.0,
        diagnosis_alignment_score: 0.98,
        latency_seconds: 1.82,
        details: {
          predicted_root_cause: 'NullPointerException in OrderController/TenantInterceptor due to missing session context in v2.4.1 release.',
          top_runbook_retrieved: 'Runbook: Checkout Service NullPointer & Auth Failure Triage'
        }
      },
      {
        incident_id: 'INC-5002',
        retrieval_success: true,
        faithfulness_score: 0.85,
        diagnosis_alignment_score: 0.95,
        latency_seconds: 2.25,
        details: {
          predicted_root_cause: 'HikariCP connection pool starvation caused by unindexed queries holding postgres slots at 100/100 max.',
          top_runbook_retrieved: 'Runbook: HikariCP Connection Pool Exhaustion on Postgres Services'
        }
      },
      {
        incident_id: 'INC-5003',
        retrieval_success: true,
        faithfulness_score: 0.80,
        diagnosis_alignment_score: 0.94,
        latency_seconds: 2.35,
        details: {
          predicted_root_cause: 'External Stripe payment gateway latency exceeding client timeout leading to HALF_OPEN circuit breaker state.',
          top_runbook_retrieved: 'Post-Mortem: Q3 Stripe Gateway Latency Outage'
        }
      }
    ]
  };

  /**
   * Health Check to probe FastAPI backend
   */
  public checkHealth(): Observable<{ status: string; app: string }> {
    return this.http.get<{ status: string; app: string }>(`${this.baseUrl}/health`).pipe(
      tap((res) => {
        this.isBackendConnected.set(true);
        this.isSimulatedMode.set(false);
        this.systemConfig.update((c) => ({
          ...c,
          status: 'HEALTHY',
          engineName: res.app || c.engineName
        }));
      }),
      catchError((err) => {
        this.isBackendConnected.set(false);
        this.isSimulatedMode.set(true);
        this.systemConfig.update((c) => ({
          ...c,
          status: 'DEGRADED'
        }));
        return of({ status: 'offline', app: 'Zero500 (Simulated SRE Sandbox)' });
      })
    );
  }

  /**
   * GET /incidents -> Returns IncidentSummary[]
   */
  public getIncidents(): Observable<IncidentSummary[]> {
    this.isIncidentsLoading.set(true);
    this.activeError.set(null);

    return this.http.get<IncidentSummary[]>(`${this.baseUrl}/incidents`).pipe(
      tap((data) => {
        this.incidents.set(data);
        this.isBackendConnected.set(true);
        this.isSimulatedMode.set(false);
        this.isIncidentsLoading.set(false);
      }),
      catchError((err) => {
        console.warn('Backend unavailable at :8000. Serving synthetic SRE incident dataset.', err);
        this.isBackendConnected.set(false);
        this.isSimulatedMode.set(true);
        this.isIncidentsLoading.set(false);

        // Fallback to synthetic incidents
        const summaries: IncidentSummary[] = this.fallbackIncidents.map((inc) => ({
          id: inc.id,
          title: inc.title,
          service: inc.service,
          severity: inc.severity,
          created_at: inc.created_at,
          status: inc.status
        }));
        this.incidents.set(summaries);
        return of(summaries);
      })
    );
  }

  /**
   * GET /incidents/{id} -> Returns IncidentDetail
   */
  public getIncidentById(id: string): Observable<IncidentDetail> {
    this.isIncidentDetailLoading.set(true);
    this.activeError.set(null);

    return this.http.get<IncidentDetail>(`${this.baseUrl}/incidents/${id}`).pipe(
      tap((detail) => {
        this.selectedIncident.set(detail);
        this.isIncidentDetailLoading.set(false);
        this.isBackendConnected.set(true);
      }),
      catchError((err) => {
        console.warn(`Failed to fetch incident ${id} from live API. Falling back to local dataset.`, err);
        this.isIncidentDetailLoading.set(false);
        const match = this.fallbackIncidents.find((i) => i.id.toLowerCase() === id.toLowerCase()) || this.fallbackIncidents[0];
        this.selectedIncident.set(match);
        return of(match);
      })
    );
  }

  /**
   * POST /incidents/{id}/investigate -> Returns InvestigationReport
   */
  public investigateIncident(id: string): Observable<InvestigationReport> {
    this.isInvestigating.set(true);
    this.activeError.set(null);

    return this.http.post<InvestigationReport>(`${this.baseUrl}/incidents/${id}/investigate`, {}).pipe(
      tap((report) => {
        this.investigationReports.update((prev) => ({
          ...prev,
          [id]: report
        }));
        this.isInvestigating.set(false);
        this.isBackendConnected.set(true);
      }),
      catchError((err) => {
        console.warn(`Investigate endpoint failed or offline for ${id}. Providing high-fidelity simulated Gemini RCA analysis.`, err);
        // Simulate real LLM latency for realistic user feedback
        return of(this.fallbackReports[id] || this.fallbackReports['INC-5001']).pipe(
          delay(1200),
          tap((mockReport) => {
            this.investigationReports.update((prev) => ({
              ...prev,
              [id]: mockReport
            }));
            this.isInvestigating.set(false);
          })
        );
      })
    );
  }

  /**
   * POST /evaluations/run -> Returns EvaluationSuiteReport
   */
  public runEvaluationSuite(): Observable<EvaluationSuiteReport> {
    this.isEvaluating.set(true);
    this.activeError.set(null);

    return this.http.post<EvaluationSuiteReport>(`${this.baseUrl}/evaluations/run`, {}).pipe(
      tap((report) => {
        this.evaluationReport.set(report);
        this.isEvaluating.set(false);
        this.isBackendConnected.set(true);
      }),
      catchError((err) => {
        console.warn('Evaluation suite endpoint failed or offline. Generating benchmark report.', err);
        return of(this.fallbackEvaluation).pipe(
          delay(1800),
          tap((mockSuite) => {
            this.evaluationReport.set(mockSuite);
            this.isEvaluating.set(false);
          })
        );
      })
    );
  }

  /**
   * Select an incident and automatically fetch details
   */
  public selectIncident(incident: IncidentSummary | string): void {
    const id = typeof incident === 'string' ? incident : incident.id;
    this.getIncidentById(id).subscribe();
  }

  /**
   * Clear error state
   */
  public clearError(): void {
    this.activeError.set(null);
  }
}
