import { Injectable, inject, signal, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { catchError, map, tap } from 'rxjs/operators';
import {
  IncidentSummary,
  IncidentDetail,
  InvestigationReport,
  EvaluationSuiteReport,
} from '../models/incident.model';
import { SystemMetadata, DEFAULT_SYSTEM_CONFIG } from '../core/config/system.config';

export interface RunbookCreate {
  title: string;
  service: string;
  doc_type: 'RUNBOOK' | 'PAST_POSTMORTEM';
  content: string;
}

@Injectable({
  providedIn: 'root',
})
export class IncidentService {
  private readonly http = inject(HttpClient);

  // System Configuration & Metadata (Decoupled & Dynamic)
  public readonly systemConfig = signal<SystemMetadata>(DEFAULT_SYSTEM_CONFIG);

  public get baseUrl(): string {
    return this.systemConfig().apiUrl;
  }

  // Local cache for ingested incidents to guarantee instant read-after-write
  public readonly localIncidentDetails = new Map<string, IncidentDetail>();

  // State Signals
  public readonly incidents = signal<IncidentSummary[]>([]);
  public readonly selectedIncident = signal<IncidentDetail | null>(null);
  public readonly investigationReports = signal<Record<string, InvestigationReport | null>>({});
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
    return this.investigationReports()[selected.id] ?? null;
  });

  /**
   * Demo incident dataset, loaded from the shared JSON fixture at assets/demo-incidents.json.
   *
   * This is only ever a read-only fallback for the incident list when the backend is
   * unreachable. It is never used to fabricate AI investigation reports or benchmark
   * scorecards, and it is generated from backend/app/data/synthetic.py so there is one
   * source of truth for demo incident data instead of two hand-duplicated copies.
   */
  private demoIncidentsCache: IncidentDetail[] | null = null;

  private loadDemoIncidents(): Observable<IncidentDetail[]> {
    if (this.demoIncidentsCache) {
      return of(this.demoIncidentsCache);
    }
    return this.http.get<IncidentDetail[]>('assets/demo-incidents.json').pipe(
      tap((demo) => {
        this.demoIncidentsCache = demo;
      }),
      catchError(() => of([])),
    );
  }

  /**
   * Health Check to probe FastAPI backend
   */
  public checkHealth(): Observable<{ status: string; app: string }> {
    return this.http.get<{ status: string; app: string }>(`${this.baseUrl}/health`).pipe(
      tap((res) => {
        this.isBackendConnected.set(true);
        this.isSimulatedMode.set(false);
        this.activeError.set(null);
        this.systemConfig.update((c) => ({
          ...c,
          status: 'HEALTHY',
          engineName: res.app || c.engineName,
        }));
      }),
      catchError((err) => {
        console.warn('Backend health check failed — API unreachable.', err);
        this.isBackendConnected.set(false);
        this.isSimulatedMode.set(true);
        this.activeError.set(
          'Backend unreachable — the API did not respond to the health check. Retry when it wakes up.',
        );
        this.systemConfig.update((c) => ({
          ...c,
          status: 'DEGRADED',
        }));
        return of({ status: 'offline', app: 'Zero500' });
      }),
    );
  }

  /**
   * POST /incidents/ingest -> Live Webhook Ingestion
   */
  public ingestIncident(incident: IncidentDetail): Observable<IncidentSummary> {
    this.localIncidentDetails.set(incident.id, incident);

    const summary: IncidentSummary = {
      id: incident.id,
      title: incident.title,
      service: incident.service,
      severity: incident.severity,
      created_at: incident.created_at || new Date().toISOString(),
      status: incident.status || 'INVESTIGATING',
    };

    // Prepend to incidents list signal immediately so sidebar reflects the new incident
    this.incidents.update((list) => [summary, ...list.filter((i) => i.id !== summary.id)]);

    return this.http
      .post<IncidentSummary>(`${this.systemConfig().apiUrl}/incidents/ingest`, incident)
      .pipe(
        tap((res) => {
          this.isBackendConnected.set(true);
          this.isSimulatedMode.set(false);
          this.activeError.set(null);
          this.incidents.update((list) => [res, ...list.filter((i) => i.id !== res.id)]);
        }),
        catchError((err) => {
          console.warn('Backend /incidents/ingest unreachable. Retaining incident locally.', err);
          this.isBackendConnected.set(false);
          this.isSimulatedMode.set(true);
          this.activeError.set(
            'Backend unreachable — the incident was saved locally and will sync when the API recovers.',
          );
          return of(summary);
        }),
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
        const localSummaries = Array.from(this.localIncidentDetails.values()).map((inc) => ({
          id: inc.id,
          title: inc.title,
          service: inc.service,
          severity: inc.severity,
          created_at: inc.created_at,
          status: inc.status,
        }));
        const combined = [
          ...localSummaries.filter((l) => !data.some((d) => d.id === l.id)),
          ...data,
        ];
        this.incidents.set(combined);
        this.isBackendConnected.set(true);
        this.isSimulatedMode.set(false);
        this.activeError.set(null);
        this.isIncidentsLoading.set(false);
      }),
      catchError((err) => {
        console.warn(
          'Backend unavailable at :8000. Demo incidents only — no fabricated AI output.',
          err,
        );
        this.isBackendConnected.set(false);
        this.isSimulatedMode.set(true);
        this.activeError.set(
          'Backend unreachable — incident history and AI investigation are unavailable until the API recovers.',
        );
        this.isIncidentsLoading.set(false);

        // Fallback to the shared demo-incidents fixture + any locally ingested incidents
        return this.loadDemoIncidents().pipe(
          tap((demo) => {
            const localSummaries = Array.from(this.localIncidentDetails.values()).map((inc) => ({
              id: inc.id,
              title: inc.title,
              service: inc.service,
              severity: inc.severity,
              created_at: inc.created_at,
              status: inc.status,
            }));
            const demoSummaries = demo.map((inc) => ({
              id: inc.id,
              title: inc.title,
              service: inc.service,
              severity: inc.severity,
              created_at: inc.created_at,
              status: inc.status,
            }));
            const combined = [
              ...localSummaries.filter((l) => !demoSummaries.some((f) => f.id === l.id)),
              ...demoSummaries,
            ];
            this.incidents.set(combined);
          }),
        );
      }),
    );
  }

  /**
   * GET /incidents/{id} -> Returns IncidentDetail
   */
  public getIncidentById(id: string): Observable<IncidentDetail | null> {
    this.isIncidentDetailLoading.set(true);
    this.activeError.set(null);

    const localMatch = this.localIncidentDetails.get(id);

    return this.http.get<IncidentDetail>(`${this.baseUrl}/incidents/${id}`).pipe(
      tap((detail) => {
        this.selectedIncident.set(detail);
        this.localIncidentDetails.set(detail.id, detail);
        this.isIncidentDetailLoading.set(false);
        this.isBackendConnected.set(true);
        this.isSimulatedMode.set(false);
        this.activeError.set(null);
      }),
      catchError((err) => {
        console.warn(`Failed to fetch incident ${id} from live API.`, err);
        this.isIncidentDetailLoading.set(false);
        this.isBackendConnected.set(false);
        this.isSimulatedMode.set(true);
        this.activeError.set(
          `Backend unreachable — details for ${id} are unavailable until the API recovers.`,
        );

        // Serve the matching demo incident from the shared fixture, never a substituted one
        return this.loadDemoIncidents().pipe(
          map((demo) => demo.find((i) => i.id.toLowerCase() === id.toLowerCase()) || null),
          tap((match) => this.selectedIncident.set(match ?? null)),
        );
      }),
    );
  }

  /**
   * POST /incidents/{id}/investigate -> Returns InvestigationReport
   *
   * On backend failure no report is fabricated: the caller sees an honest error state
   * (activeError + awaiting-rca UI) and can retry manually via "Run Autonomous RCA".
   */
  public investigateIncident(id: string): Observable<InvestigationReport | null> {
    this.isInvestigating.set(true);
    this.activeError.set(null);

    return this.http
      .post<InvestigationReport>(`${this.baseUrl}/incidents/${id}/investigate`, {})
      .pipe(
        tap((report) => {
          this.investigationReports.update((prev) => ({
            ...prev,
            [id]: report,
          }));
          this.isInvestigating.set(false);
          this.isBackendConnected.set(true);
          this.isSimulatedMode.set(false);
          this.activeError.set(null);
        }),
        catchError((err) => {
          console.warn(
            `Investigation unavailable for ${id} — backend offline. No simulated report will be shown.`,
            err,
          );
          this.isInvestigating.set(false);
          this.isBackendConnected.set(false);
          this.isSimulatedMode.set(true);
          this.activeError.set(
            `Backend unreachable — AI investigation for ${id} is unavailable. Retry when the API recovers.`,
          );
          return of(null);
        }),
      );
  }

  /**
   * POST /evaluations/run -> Returns EvaluationSuiteReport
   *
   * On backend failure no benchmark numbers are fabricated: the scorecard stays empty
   * and the user can re-run the suite manually once the API recovers.
   */
  public runEvaluationSuite(): Observable<EvaluationSuiteReport | null> {
    this.isEvaluating.set(true);
    this.activeError.set(null);

    return this.http.post<EvaluationSuiteReport>(`${this.baseUrl}/evaluations/run`, {}).pipe(
      tap((report) => {
        this.evaluationReport.set(report);
        this.isEvaluating.set(false);
        this.isBackendConnected.set(true);
        this.isSimulatedMode.set(false);
        this.activeError.set(null);
      }),
      catchError((err) => {
        console.warn('Evaluation suite unavailable — backend offline.', err);
        this.isEvaluating.set(false);
        this.isBackendConnected.set(false);
        this.isSimulatedMode.set(true);
        this.activeError.set(
          'Backend unreachable — benchmark suite is unavailable until the API recovers.',
        );
        return of(null);
      }),
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
   * POST /runbooks -> Index new Runbook / SOP into database
   */
  public createRunbook(
    payload: RunbookCreate,
  ): Observable<{ id: number; title: string; status: string }> {
    return this.http.post<{ id: number; title: string; status: string }>(
      `${this.systemConfig().apiUrl}/runbooks`,
      payload,
    );
  }

  /**
   * Clear error state
   */
  public clearError(): void {
    this.activeError.set(null);
  }
}
