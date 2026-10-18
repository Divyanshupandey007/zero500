export type Severity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type LogLevel = 'INFO' | 'WARN' | 'ERROR' | 'FATAL';
export type ActionPriority = 'IMMEDIATE' | 'SHORT_TERM' | 'LONG_TERM';

export interface LogEntry {
  timestamp: string;
  level: LogLevel;
  service: string;
  message: string;
  metadata?: Record<string, any>;
}

export interface IncidentSummary {
  id: string;
  title: string;
  service: string;
  severity: Severity;
  created_at: string;
  status: string;
}

export interface IncidentDetail extends IncidentSummary {
  description: string;
  logs: LogEntry[];
  metrics_snapshot: Record<string, any>;
}

export interface EvidenceItem {
  source: string;
  detail: string;
}

export interface RemediationStep {
  action: string;
  priority: ActionPriority;
  description: string;
  runbook_reference?: string | null;
}

export interface MatchedRunbook {
  title: string;
  doc_type: string;
  similarity_score: number;
}

export interface InvestigationReport {
  incident_id: string;
  executive_summary: string;
  suspected_root_cause: string;
  confidence_score: number;
  matched_runbooks: MatchedRunbook[];
  evidence: EvidenceItem[];
  remediation_plan: RemediationStep[];
  requires_human_escalation: boolean;
}

export interface TestCaseResult {
  incident_id: string;
  retrieval_success: boolean;
  faithfulness_score: number;
  diagnosis_alignment_score: number;
  latency_seconds: number;
  details: Record<string, string>;
}

export interface EvaluationSuiteReport {
  total_test_cases?: number;
  total_test_case?: number;
  retrieval_recall: number;
  average_faithfulness: number;
  average_diagnosis_accuracy: number;
  average_latency_seconds: number;
  test_cases: TestCaseResult[];
}
