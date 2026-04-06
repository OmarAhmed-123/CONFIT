/**
 * CONFIT Frontend — Security Scanning Service
 * =============================================
 * Client-side API for PentAGI security scanning integration.
 */

import { api } from '@/lib/api/client';

// ── Types ───────────────────────────────────────────────────────────

export type ScanType = 'api' | 'web' | 'auth' | 'full';
export type ScanStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
export type Severity = 'critical' | 'high' | 'medium' | 'low' | 'info';

export interface ScanRequest {
  target: string;
  scan_type: ScanType;
  description?: string;
}

export interface ScanStartResponse {
  scan_id: string;
  pentagi_flow_id: string | null;
  status: ScanStatus;
  target: string;
  scan_type: ScanType;
  message: string;
  created_at: string;
}

export interface ScanStatusResponse {
  scan_id: string;
  pentagi_flow_id: string | null;
  status: ScanStatus;
  target: string;
  scan_type: ScanType;
  tasks_count: number;
  tasks: Array<{ id: string; name: string; status: string }>;
  created_at: string;
  updated_at: string | null;
}

export interface SecurityFinding {
  severity: Severity;
  vulnerability: string;
  description: string;
  remediation: string;
  timestamp: string | null;
}

export interface FindingSummary {
  total: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
  info: number;
}

export interface ScanReportResponse {
  scan_id: string;
  pentagi_flow_id: string | null;
  status: ScanStatus;
  target: string;
  scan_type: ScanType;
  findings: SecurityFinding[];
  summary: FindingSummary;
  raw_ai_output: string;
  created_at: string;
  updated_at: string | null;
}

export interface ScanListItem {
  scan_id: string;
  pentagi_flow_id: string | null;
  status: ScanStatus;
  target: string;
  scan_type: ScanType;
  findings_count: number;
  created_at: string;
  updated_at: string | null;
}

export interface DiscoveredRoute {
  path: string;
  method: string;
  tags: string[];
  summary: string;
  url: string;
}

export interface DiscoveryResponse {
  api_routes: DiscoveredRoute[];
  web_routes: DiscoveredRoute[];
  services: Array<Record<string, any>>;
  summary: {
    total_routes: number;
    total_web_routes: number;
    total_services: number;
    route_groups: Record<string, number>;
    methods: Record<string, number>;
  };
}

export interface HealthResponse {
  pentagi_reachable: boolean;
  pentagi_url: string;
  message: string;
}

// ── API Endpoints ───────────────────────────────────────────────────

const SECURITY_ENDPOINTS = {
  SCAN: '/security/scan',
  STATUS: (id: string) => `/security/status/${id}`,
  REPORT: (id: string) => `/security/report/${id}`,
  SCANS: '/security/scans',
  DISCOVER: '/security/targets/discover',
  HEALTH: '/security/health',
} as const;

// ── Service Functions ───────────────────────────────────────────────

/**
 * Start a new security scan.
 */
export async function startScan(request: ScanRequest): Promise<ScanStartResponse> {
  return api.post<ScanStartResponse>(SECURITY_ENDPOINTS.SCAN, request);
}

/**
 * Get the status of a running scan.
 */
export async function getScanStatus(scanId: string): Promise<ScanStatusResponse> {
  return api.get<ScanStatusResponse>(SECURITY_ENDPOINTS.STATUS(scanId));
}

/**
 * Get the full report for a completed scan.
 */
export async function getScanReport(scanId: string): Promise<ScanReportResponse> {
  return api.get<ScanReportResponse>(SECURITY_ENDPOINTS.REPORT(scanId));
}

/**
 * List all scans.
 */
export async function listScans(status?: ScanStatus): Promise<ScanListItem[]> {
  const params = status ? `?status=${status}` : '';
  return api.get<ScanListItem[]>(`${SECURITY_ENDPOINTS.SCANS}${params}`);
}

/**
 * Auto-discover scan targets.
 */
export async function discoverTargets(): Promise<DiscoveryResponse> {
  return api.get<DiscoveryResponse>(SECURITY_ENDPOINTS.DISCOVER);
}

/**
 * Check PentAGI health.
 */
export async function checkHealth(): Promise<HealthResponse> {
  return api.get<HealthResponse>(SECURITY_ENDPOINTS.HEALTH);
}

// ── Utility ─────────────────────────────────────────────────────────

export const SEVERITY_CONFIG: Record<Severity, { color: string; bg: string; label: string }> = {
  critical: { color: '#ff1744', bg: 'rgba(255, 23, 68, 0.15)', label: 'CRITICAL' },
  high: { color: '#ff9100', bg: 'rgba(255, 145, 0, 0.15)', label: 'HIGH' },
  medium: { color: '#ffd600', bg: 'rgba(255, 214, 0, 0.15)', label: 'MEDIUM' },
  low: { color: '#00b0ff', bg: 'rgba(0, 176, 255, 0.15)', label: 'LOW' },
  info: { color: '#90a4ae', bg: 'rgba(144, 164, 174, 0.15)', label: 'INFO' },
};

export const SCAN_TYPE_LABELS: Record<ScanType, string> = {
  api: 'API Security',
  web: 'Web Application',
  auth: 'Authentication',
  full: 'Full Penetration Test',
};

export const STATUS_LABELS: Record<ScanStatus, { label: string; color: string }> = {
  pending: { label: 'Pending', color: '#90a4ae' },
  running: { label: 'Running', color: '#00b0ff' },
  completed: { label: 'Completed', color: '#00e676' },
  failed: { label: 'Failed', color: '#ff1744' },
  cancelled: { label: 'Cancelled', color: '#78909c' },
};

export const securityService = {
  startScan,
  getScanStatus,
  getScanReport,
  listScans,
  discoverTargets,
  checkHealth,
};
