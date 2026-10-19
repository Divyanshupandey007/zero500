export interface SystemMetadata {
  engineName: string;      // e.g. "RootLens Engine" or "Zero500 Autonomous RCA"
  activeModel: string;     // Dynamic model label (e.g. "gemini-3.1-flash-lite")
  vectorStore: string;     // Vector database (e.g. "Neon pgvector")
  backendVersion: string;  // API version
  status: 'HEALTHY' | 'DEGRADED';
  apiUrl: string;
}

const isLocalHost=typeof window!=='undefined' && (window.location.hostname==='localhost' || window.location.hostname==='127.0.0.1');

export const DEFAULT_SYSTEM_CONFIG: SystemMetadata = {
  engineName: 'RootLens Engine',
  activeModel: 'Autonomous SRE Agent',
  vectorStore: 'Neon pgvector',
  backendVersion: 'v0.3.0',
  status: 'HEALTHY',
  apiUrl: isLocalHost
    ? 'http://localhost:8000/api/v1'
    : 'https://zero500-o8jk.onrender.com/api/v1'
};
