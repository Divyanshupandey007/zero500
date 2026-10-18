export interface SystemMetadata {
  engineName: string;      // e.g. "RootLens Engine" or "Zero500 Autonomous RCA"
  activeModel: string;     // Dynamic model label (e.g. "gemini-3.1-flash-lite")
  vectorStore: string;     // Vector database (e.g. "Neon pgvector")
  backendVersion: string;  // API version
  status: 'HEALTHY' | 'DEGRADED';
  apiUrl: string;
}

export const DEFAULT_SYSTEM_CONFIG: SystemMetadata = {
  engineName: 'RootLens Engine',
  activeModel: 'Autonomous SRE Agent',
  vectorStore: 'Neon pgvector',
  backendVersion: 'v0.2.0',
  status: 'HEALTHY',
  apiUrl: 'http://localhost:8000/api/v1'
};
