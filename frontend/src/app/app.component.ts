import {
  Component,
  OnInit,
  inject,
  signal,
  computed,
  HostListener
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { IncidentService } from './services/incident.service';
import {
  Severity,
  LogLevel,
  ActionPriority,
  MatchedRunbook,
  LogEntry,
  IncidentDetail
} from './models/incident.model';
import { SystemMetadata } from './core/config/system.config';

export interface CausalNode {
  index: number;
  stage: 'TRIGGER' | 'PROPAGATION' | 'IMPACT';
  title: string;
  source: string;
  timeOffset: string;
  icon: string;
  detail: string;
  badge: string;
  rawLogSnippet?: string;
}

export interface MetricVisual {
  key: string;
  displayKey: string;
  value: string;
  rawKey: string;
  rawValue: any;
  sparklinePath: string;
  sparklineArea: string;
  saturationPct: number;
  isAlert: boolean;
  unit: string;
}

export interface LogDensityTick {
  positionPct: number;
  level: LogLevel;
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent implements OnInit {
  public readonly incidentService = inject(IncidentService);

  public readonly systemConfig = computed<SystemMetadata>(() => this.incidentService.systemConfig());

  public readonly searchQuery = signal<string>('');
  public readonly severityFilter = signal<string>('ALL');
  public readonly logFilter = signal<string>('ALL');
  public readonly logSearch = signal<string>('');

  public readonly isEvalModalOpen = signal<boolean>(false);
  public readonly isInvestigationModalOpen = signal<boolean>(false);
  public readonly isSubmitting = signal<boolean>(false);
  public readonly toastMessage = signal<string | null>(null);

  // New Investigation Form Signals
  public readonly investigationTitle = signal<string>('');
  public readonly investigationService = signal<string>('');
  public readonly investigationSeverity = signal<Severity>('CRITICAL');
  public readonly investigationRawLogs = signal<string>('');

  public readonly isDeepAnalysisOpen = signal<boolean>(false);
  public readonly activeRunbook = signal<MatchedRunbook | null>(null);
  public readonly selectedCausalNode = signal<CausalNode | null>(null);
  public readonly expandedTestCases = signal<Record<string, boolean>>({});
  public readonly activeWorkbenchTab = signal<'PLAYBOOK' | 'LOGS' | 'RUNBOOKS'>('PLAYBOOK');
  public readonly completedSteps = signal<Record<string, boolean>>({});
  public readonly copiedText = signal<string | null>(null);
  public readonly copiedIncidentId = signal<string | null>(null);

  public readonly severities: ('ALL' | Severity)[] = ['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'];

  public readonly runbookContents: Record<string, { summary: string; triageSteps: string[]; commands: string[]; docType: string }> = {
    'Runbook: Checkout Service NullPointer & Auth Failure Triage': {
      docType: 'RUNBOOK',
      summary: 'Standard Operating Procedure for handling NullPointerExceptions in checkout pipeline post-deployment.',
      triageSteps: [
        'Inspect if incoming HTTP session context contains required X-Tenant-ID headers.',
        'Check TenantInterceptor.preHandle() trace to verify session object instantiation.',
        'If error rate exceeds 5% immediately after a deployment rollout, trigger automated rollback.'
      ],
      commands: [
        'helm rollback checkout-service-prod',
        'kubectl logs -l app=checkout-service --tail=100 -n production | grep -E "NullPointer|TenantInterceptor"',
        'kubectl rollout status deployment/checkout-service -n production'
      ]
    },
    'Post-Mortem: Q3 Deployment Interceptor Context Drop': {
      docType: 'PAST_POSTMORTEM',
      summary: 'Historical post-mortem from Q3 incident where asynchronous filter ordering bypassed SecurityContextHolder.',
      triageSteps: [
        'Validate FilterChain registration order in SecurityConfig.java.',
        'Ensure session propagation across async thread pool executors.',
        'Verify Prometheus alert alert_checkout_error_rate_spike.'
      ],
      commands: [
        'git log -n 5 -p src/main/java/com/zero500/interceptor/TenantInterceptor.java',
        'curl -s -o /dev/null -w "%{http_code}" https://api.zero500.internal/health'
      ]
    },
    'Runbook: HikariCP Connection Pool Exhaustion on Postgres Services': {
      docType: 'RUNBOOK',
      summary: 'Mitigation procedure for HikariCP database pool saturation and PostgreSQL connection starvation.',
      triageSteps: [
        'Identify long-running or unindexed queries blocking Postgres connection worker slots.',
        'Terminate idle-in-transaction worker sessions holding locks > 30 seconds.',
        'Scale up PgBouncer connection ceiling or gracefully cycle microservice pods.'
      ],
      commands: [
        "psql -d neondb -c \"SELECT pid, query, state, age(clock_timestamp(), query_start) FROM pg_stat_activity WHERE state != 'idle';\"",
        "psql -d neondb -c \"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle in transaction' AND age(clock_timestamp(), state_change) > interval '30 seconds';\"",
        'kubectl rollout restart deployment/users-service -n production'
      ]
    },
    'Post-Mortem: Q3 Stripe Gateway Latency Outage': {
      docType: 'PAST_POSTMORTEM',
      summary: 'Analysis of downstream third-party payment gateway latency spike and circuit breaker configuration.',
      triageSteps: [
        'Confirm upstream provider operational status at status.stripe.com.',
        'Verify circuit breaker threshold state transition from CLOSED to HALF_OPEN.',
        'Temporarily route payment retry queue to secondary backup gateway provider.'
      ],
      commands: [
        'curl -s https://status.stripe.com/current',
        'kubectl exec -it deploy/payment-gateway-proxy -- curl -s localhost:8080/actuator/circuitbreakers'
      ]
    }
  };

  public getRunbookDetail(title: string): { summary: string; triageSteps: string[]; commands: string[]; docType: string } {
    if (this.runbookContents[title]) {
      return this.runbookContents[title];
    }
    const service = this.incidentService.selectedIncident()?.service || 'service';
    return {
      docType: 'RUNBOOK',
      summary: `Standard Operating Procedure for handling telemetry alerts, upstream saturation, and failover in ${service}.`,
      triageSteps: [
        `Inspect ingress proxy routing tables and upstream health checks for ${service}.`,
        `Verify container pod metrics, cgroup limits, and restart exit codes via kubectl.`,
        `If error rate persists above SLA threshold, initiate graceful traffic shed or rollback.`
      ],
      commands: [
        `kubectl logs -l app=${service} --tail=100 -n production | grep -E "ERROR|FATAL"`,
        `kubectl top pods -l app=${service} -n production --containers`,
        `kubectl rollout status deployment/${service} -n production`
      ]
    };
  }

  public readonly filteredIncidents = computed(() => {
    const list = this.incidentService.incidents();
    const query = this.searchQuery().toLowerCase().trim();
    const filter = this.severityFilter();

    return list.filter((inc) => {
      const matchesSearch =
        !query ||
        inc.id.toLowerCase().includes(query) ||
        inc.title.toLowerCase().includes(query) ||
        inc.service.toLowerCase().includes(query);

      const matchesSeverity = filter === 'ALL' || inc.severity === filter;
      return matchesSearch && matchesSeverity;
    });
  });

  public readonly filteredLogs = computed(() => {
    const selected = this.incidentService.selectedIncident();
    if (!selected || !selected.logs) return [];

    const level = this.logFilter();
    const search = this.logSearch().toLowerCase().trim();

    return selected.logs.filter((log) => {
      const matchesLevel = level === 'ALL' || log.level === level;
      const matchesSearch =
        !search ||
        log.message.toLowerCase().includes(search) ||
        log.service.toLowerCase().includes(search) ||
        log.level.toLowerCase().includes(search);

      return matchesLevel && matchesSearch;
    });
  });

  public readonly logDensityTicks = computed<LogDensityTick[]>(() => {
    const selected = this.incidentService.selectedIncident();
    if (!selected || !selected.logs || selected.logs.length === 0) return [];

    const count = selected.logs.length;
    return selected.logs.map((log, idx) => ({
      positionPct: Math.round(((idx + 0.5) / count) * 100),
      level: log.level
    }));
  });

  public readonly currentMetrics = computed<MetricVisual[]>(() => {
    const selected = this.incidentService.selectedIncident();
    if (!selected || !selected.metrics_snapshot) return [];

    return Object.entries(selected.metrics_snapshot).map(([key, value]) => {
      const displayKey = this.formatMetricKey(key);
      const strVal = this.formatMetricValue(value);
      const numVal = typeof value === 'number' ? value : parseFloat(value) || 0;

      let saturationPct = 40;
      let isAlert = false;
      let unit = '';

      if (key.includes('error') || key.includes('pct') || key.includes('percentage')) {
        unit = '%';
        saturationPct = Math.min(100, Math.round(numVal));
        isAlert = numVal > 5;
      } else if (key.includes('ms') || key.includes('latency')) {
        unit = 'ms';
        saturationPct = Math.min(100, Math.round((numVal / 2500) * 100));
        isAlert = numVal > 1500;
      } else if (key.includes('active') || key.includes('connections')) {
        saturationPct = Math.min(100, Math.round(numVal));
        isAlert = numVal >= 90;
      } else if (key.includes('restart')) {
        saturationPct = numVal > 0 ? 100 : 0;
        isAlert = numVal > 0;
      } else {
        saturationPct = Math.min(100, Math.round(numVal));
        isAlert = saturationPct > 80;
      }

      const { path, areaPath } = this.generateSparkline(key, isAlert);

      return {
        key,
        displayKey,
        value: strVal,
        rawKey: key,
        rawValue: value,
        sparklinePath: path,
        sparklineArea: areaPath,
        saturationPct,
        isAlert,
        unit
      };
    });
  });

  public readonly causalFlowNodes = computed<CausalNode[]>(() => {
    const report = this.incidentService.currentReport();
    const incident = this.incidentService.selectedIncident();
    if (!report || !incident) return [];

    const evidence = report.evidence || [];

    return evidence.map((ev, idx) => {
      let stage: 'TRIGGER' | 'PROPAGATION' | 'IMPACT' = 'PROPAGATION';
      let icon = '⚡';
      let badge = 'Cascade';

      if (idx === 0) {
        stage = 'TRIGGER';
        icon = '●';
        badge = 'Root Trigger';
      } else if (idx === evidence.length - 1) {
        stage = 'IMPACT';
        icon = '▲';
        badge = 'Blast Radius';
      } else {
        stage = 'PROPAGATION';
        icon = '◆';
        badge = 'Propagation';
      }

      return {
        index: idx + 1,
        stage,
        title: this.deriveNodeTitle(ev.source, ev.detail),
        source: ev.source,
        timeOffset: `T+${idx * 1.5}m`,
        icon,
        detail: ev.detail,
        badge,
        rawLogSnippet: this.findMatchingLogSnippet(ev.source, incident.logs) || ev.detail
      };
    });
  });

  public readonly confidencePercentage = computed(() => {
    const report = this.incidentService.currentReport();
    return report ? Math.round(report.confidence_score * 100) : 0;
  });

  public readonly remediationProgress = computed(() => {
    const report = this.incidentService.currentReport();
    if (!report || !report.remediation_plan) {
      return { total: 0, completed: 0, percent: 0, isAllDone: false };
    }

    const total = report.remediation_plan.length;
    const completed = report.remediation_plan.filter((s) => this.isStepCompleted(s.action)).length;
    const percent = total > 0 ? Math.round((completed / total) * 100) : 0;

    return { total, completed, percent, isAllDone: total > 0 && completed === total };
  });

  public readonly primaryCulprit = computed(() => {
    const report = this.incidentService.currentReport();
    const incident = this.incidentService.selectedIncident();
    if (!report || !incident) return null;

    if (incident.id === 'INC-5001') {
      return 'checkout-service ➔ TenantInterceptor.preHandle() [NullPointerException]';
    } else if (incident.id === 'INC-5002') {
      return 'users-service ➔ HikariCP Connection Pool Exhaustion (100/100 slots)';
    } else if (incident.id === 'INC-5003') {
      return 'payment-gateway-proxy ➔ Stripe API Client Timeout (8400ms)';
    }

    if (report.suspected_root_cause) {
      const summary = report.suspected_root_cause.length > 70
        ? report.suspected_root_cause.slice(0, 70) + '...'
        : report.suspected_root_cause;
      return `${incident.service} ➔ ${summary}`;
    }

    return `${incident.service} ➔ Root Anomaly Identified`;
  });

  ngOnInit(): void {
    this.incidentService.checkHealth().subscribe();
    this.loadIncidents();
  }

  public loadIncidents(): void {
    this.incidentService.getIncidents().subscribe({
      next: (list) => {
        if (list && list.length > 0 && !this.incidentService.selectedIncident()) {
          this.selectIncident(list[0].id);
        }
      }
    });
  }

  public selectIncident(id: string): void {
    this.incidentService.selectIncident(id);
    this.selectedCausalNode.set(null);
    this.activeRunbook.set(null);

    const existingReports = this.incidentService.investigationReports();
    if (!existingReports[id] && id === 'INC-5001') {
      this.investigateIncident(id);
    }
  }

  public investigateCurrentIncident(): void {
    const selected = this.incidentService.selectedIncident();
    if (selected) {
      this.investigateIncident(selected.id);
    }
  }

  public investigateIncident(id: string): void {
    this.incidentService.investigateIncident(id).subscribe({
      next: () => {
        setTimeout(() => {
          const reportEl = document.getElementById('ai-investigation-report');
          if (reportEl) {
            reportEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
          }
        }, 120);
      }
    });
  }

  public toggleDeepAnalysis(): void {
    this.isDeepAnalysisOpen.update((v) => !v);
  }

  public setWorkbenchTab(tab: 'PLAYBOOK' | 'LOGS' | 'RUNBOOKS'): void {
    this.activeWorkbenchTab.set(tab);
  }

  public openRunbookDrawer(runbook: MatchedRunbook): void {
    this.activeRunbook.set(runbook);
  }

  public closeRunbookDrawer(): void {
    this.activeRunbook.set(null);
  }

  public selectCausalNode(node: CausalNode): void {
    if (this.selectedCausalNode()?.index === node.index) {
      this.selectedCausalNode.set(null);
    } else {
      this.selectedCausalNode.set(node);
    }
  }

  public openEvaluationModal(): void {
    this.isEvalModalOpen.set(true);
    if (!this.incidentService.evaluationReport()) {
      this.runEvaluationSuite();
    }
  }

  public closeEvaluationModal(): void {
    this.isEvalModalOpen.set(false);
  }

  public runEvaluationSuite(): void {
    this.incidentService.runEvaluationSuite().subscribe();
  }

  public toggleTestCaseExpand(incidentId: string): void {
    this.expandedTestCases.update((prev) => ({
      ...prev,
      [incidentId]: !prev[incidentId]
    }));
  }

  public isTestCaseExpanded(incidentId: string): boolean {
    return !!this.expandedTestCases()[incidentId];
  }

  public toggleRemediationStep(action: string): void {
    this.completedSteps.update((prev) => ({
      ...prev,
      [action]: !prev[action]
    }));
  }

  public isStepCompleted(action: string): boolean {
    return !!this.completedSteps()[action];
  }

  public copyToClipboard(text: string, label: string = 'Copied'): void {
    navigator.clipboard.writeText(text).then(() => {
      this.copiedText.set(label);
      setTimeout(() => {
        if (this.copiedText() === label) {
          this.copiedText.set(null);
        }
      }, 1800);
    });
  }

  public copyCommand(cmd: string, event?: Event): void {
    if (event) event.stopPropagation();
    this.copyToClipboard(cmd, 'Command Copied');
  }

  public copyIncidentId(id: string, event: Event): void {
    event.stopPropagation();
    navigator.clipboard.writeText(id).then(() => {
      this.copiedIncidentId.set(id);
      setTimeout(() => {
        if (this.copiedIncidentId() === id) {
          this.copiedIncidentId.set(null);
        }
      }, 1500);
    });
  }

  public openInvestigationModal(): void {
    this.isInvestigationModalOpen.set(true);
  }

  public closeInvestigationModal(): void {
    this.isInvestigationModalOpen.set(false);
  }

  public clearInvestigationForm(): void {
    this.investigationTitle.set('');
    this.investigationService.set('');
    this.investigationRawLogs.set('');
    this.investigationSeverity.set('CRITICAL');
  }


  public submitInvestigation(): void {
    const title = this.investigationTitle().trim() || 'Spike in 502 Bad Gateway errors on auth proxy';
    const service = this.investigationService().trim() || 'auth-proxy';
    const severity = this.investigationSeverity();
    const rawLogs = this.investigationRawLogs().trim();

    this.isSubmitting.set(true);

    const generatedId = `INC-${Math.floor(1000 + Math.random() * 9000)}`;
    const now = Date.now();

    // 1. Parse submitted text into LogEntry records (auto-detect timestamps or use current UTC, auto-detect level ERROR/WARN/INFO)
    const lines = rawLogs
      ? rawLogs.split('\n').map((l) => l.trim()).filter((l) => l.length > 0)
      : [`[ERROR] ${service}: Uncaught runtime exception causing service degradation`];

    const logs: LogEntry[] = lines.map((line, idx) => {
      let level: LogLevel = 'INFO';
      const upper = line.toUpperCase();
      if (upper.includes('FATAL') || upper.includes('CRITICAL')) {
        level = 'FATAL';
      } else if (
        upper.includes('ERROR') ||
        upper.includes('EXCEPTION') ||
        upper.includes('FAILED') ||
        upper.includes('500') ||
        upper.includes('502') ||
        upper.includes('504')
      ) {
        level = 'ERROR';
      } else if (upper.includes('WARN')) {
        level = 'WARN';
      }

      // Check for timestamp at start of line
      const timestampMatch = line.match(/^(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)/);
      const timestamp = timestampMatch
        ? new Date(timestampMatch[1]).toISOString()
        : new Date(now - (lines.length - idx) * 15 * 1000).toISOString();

      let cleanMessage = line;
      if (timestampMatch) {
        cleanMessage = cleanMessage.substring(timestampMatch[0].length).trim();
      }
      cleanMessage = cleanMessage.replace(/^\[?(?:INFO|WARN|WARNING|ERROR|FATAL|DEBUG|CRITICAL)\]?\s*[:-]?\s*/i, '');
      cleanMessage = cleanMessage.replace(new RegExp(`^${service}\\s*[:-]?\s*`, 'i'), '');

      return {
        timestamp,
        level,
        service,
        message: cleanMessage || line
      };
    });

    const incident: IncidentDetail = {
      id: generatedId,
      title,
      service,
      severity,
      status: 'INVESTIGATING',
      created_at: new Date(now).toISOString(),
      description: `Autonomous investigation initiated for ${service}: ${title}`,
      metrics_snapshot: {
        error_rate_percentage: severity === 'CRITICAL' ? 36.4 : severity === 'HIGH' ? 18.2 : 6.1,
        latency_p99_ms: severity === 'CRITICAL' ? 3200 : severity === 'HIGH' ? 1650 : 540,
        pod_restart_count: severity === 'CRITICAL' ? 4 : 0,
        active_threads: 310
      },
      logs
    };

    // 2. Post to incidentService.ingestIncident()
    // 3. Prepend the new incident to active list, select it immediately, trigger the investigation, and close modal.
    this.incidentService.ingestIncident(incident).subscribe({
      next: (summary) => {
        this.isSubmitting.set(false);
        this.closeInvestigationModal();
        this.selectIncident(summary.id);
        this.investigateIncident(summary.id);
        this.showToast(`Incident ${summary.id} registered for autonomous root-cause analysis`);
      },
      error: () => {
        this.isSubmitting.set(false);
        this.closeInvestigationModal();
        this.selectIncident(incident.id);
        this.investigateIncident(incident.id);
        this.showToast(`Incident ${incident.id} registered for autonomous root-cause analysis`);
      }
    });
  }

  public showToast(msg: string, duration: number = 3500): void {
    this.toastMessage.set(msg);
    setTimeout(() => {
      if (this.toastMessage() === msg) {
        this.toastMessage.set(null);
      }
    }, duration);
  }

  @HostListener('document:keydown.escape')
  public handleEscape(): void {
    if (this.isInvestigationModalOpen()) {
      this.closeInvestigationModal();
    } else if (this.activeRunbook()) {
      this.closeRunbookDrawer();
    } else if (this.isEvalModalOpen()) {
      this.closeEvaluationModal();
    } else if (this.selectedCausalNode()) {
      this.selectedCausalNode.set(null);
    }
  }

  private generateSparkline(key: string, isAlert: boolean): { path: string; areaPath: string } {
    if (isAlert || key.includes('error') || key.includes('timeout') || key.includes('active')) {
      return {
        path: 'M 0,22 Q 25,22 40,20 T 65,18 T 80,14 L 100,2',
        areaPath: 'M 0,22 Q 25,22 40,20 T 65,18 T 80,14 L 100,2 L 100,26 L 0,26 Z'
      };
    } else if (key.includes('latency')) {
      return {
        path: 'M 0,20 Q 30,21 55,17 T 80,12 L 100,4',
        areaPath: 'M 0,20 Q 30,21 55,17 T 80,12 L 100,4 L 100,26 L 0,26 Z'
      };
    }
    return {
      path: 'M 0,16 Q 25,12 50,16 T 75,14 L 100,16',
      areaPath: 'M 0,16 Q 25,12 50,16 T 75,14 L 100,16 L 100,26 L 0,26 Z'
    };
  }

  private deriveNodeTitle(source: string, detail?: string): string {
    const textToAnalyze = (detail && detail.trim().length > 0 ? detail.trim() : source) || '';

    // Check if source is a generic log label (e.g. "payment-gw log [ERROR]" or "service log [WARN]")
    const isGenericLogSource = !source || /log\s*\[(?:ERROR|WARN|FATAL|INFO|DEBUG|CRITICAL)\]/i.test(source);

    // 1. Check for Exception class name in detail or source (e.g. ConnectionPoolTimeoutException, SocketTimeoutError)
    const exceptionMatch = textToAnalyze.match(/\b([A-Z][a-zA-Z0-9]*(?:Exception|Error|Timeout|Fault|Failure|Starvation|Exhaustion|OOMKilled))\b/);
    if (exceptionMatch && exceptionMatch[1]) {
      return exceptionMatch[1];
    }

    // 2. If it's a generic log source, extract the first 4 to 6 words of the log message / detail
    if (detail && isGenericLogSource) {
      const cleaned = detail
        .replace(/^\[?\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?\]?\s*/i, '')
        .replace(/^\[?(?:ERROR|FATAL|WARN|INFO|DEBUG|CRITICAL)\]?[:\s]*/i, '')
        .replace(/^\[[\w.-]+\][:\s]*/i, '')
        .replace(/^[\w.-]+:\s*/i, '')
        .trim();

      const words = cleaned.split(/\s+/).filter((w) => w.length > 0);
      if (words.length > 0) {
        const wordCount = Math.min(words.length, 6);
        const titleCandidate = words.slice(0, wordCount).join(' ');
        return titleCandidate.length > 40 ? titleCandidate.substring(0, 40) + '...' : titleCandidate;
      }
    }

    // 3. Fallback for structured / baseline sources (e.g. "checkout-service log: OrderController.process line 84")
    const clean = source
      .replace(/Metrics:\s*/i, '')
      .replace(/^[\w-]+(?:\s*log)?:\s*/i, '')
      .trim();

    return clean.length > 36 ? clean.substring(0, 36) + '...' : clean;
  }

  private findMatchingLogSnippet(source: string, logs: LogEntry[]): string | undefined {
    if (!logs) return undefined;
    const lower = source.toLowerCase();
    const matched = logs.find(
      (l) => lower.includes(l.message.substring(0, 20).toLowerCase()) || l.message.toLowerCase().includes(lower.substring(0, 20))
    );
    return matched ? `[${matched.level}] ${matched.service}: ${matched.message}` : source;
  }

  public formatMetricKey(key: string): string {
    return key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  }

  public formatMetricValue(value: any): string {
    return typeof value === 'number' ? value.toLocaleString() : String(value);
  }

  public formatSimilarity(score: number): string {
    return `${Math.round(score * 100)}%`;
  }

  public formatPercentage(score: number): string {
    return `${Math.round(score * 100)}%`;
  }

  public formatTimestamp(timestamp: string): string {
    if (!timestamp) return '';
    try {
      const d = new Date(timestamp);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return timestamp;
    }
  }

  public formatRelativeTime(dateStr: string): string {
    if (!dateStr) return '';
    try {
      const diffMs = Date.now() - new Date(dateStr).getTime();
      const diffMins = Math.floor(diffMs / 60000);
      if (diffMins < 1) return 'Just now';
      if (diffMins < 60) return `${diffMins}m ago`;
      const diffHours = Math.floor(diffMins / 60);
      if (diffHours < 24) return `${diffHours}h ago`;
      return `${Math.floor(diffHours / 24)}d ago`;
    } catch {
      return dateStr;
    }
  }

  public getSeverityBadgeClass(severity: Severity): string {
    const map: Record<Severity, string> = {
      CRITICAL: 'badge-critical',
      HIGH: 'badge-high',
      MEDIUM: 'badge-medium',
      LOW: 'badge-low'
    };
    return map[severity] || 'badge-default';
  }

  public getLogLevelBadgeClass(level: LogLevel): string {
    const map: Record<LogLevel, string> = {
      ERROR: 'log-badge-error',
      FATAL: 'log-badge-error',
      WARN: 'log-badge-warn',
      INFO: 'log-badge-info'
    };
    return map[level] || 'log-badge-default';
  }

  public getPriorityBadgeClass(priority: ActionPriority): string {
    const map: Record<ActionPriority, string> = {
      IMMEDIATE: 'priority-immediate',
      SHORT_TERM: 'priority-short',
      LONG_TERM: 'priority-long'
    };
    return map[priority] || '';
  }

  public extractCommand(description: string): string | null {
    const match = description.match(/'([^']+)'/);
    return match ? match[1] : null;
  }
}
