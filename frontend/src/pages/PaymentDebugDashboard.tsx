/**
 * Payment Debug Dashboard
 * =======================
 * Comprehensive debugging dashboard for Paymob and PayPal integrations.
 * Only accessible in development/staging environments.
 */

import { useState, useEffect, useCallback } from 'react';
import {
  AlertCircle,
  CheckCircle,
  XCircle,
  RefreshCw,
  Clock,
  Key,
  Globe,
  Shield,
  Zap,
  AlertTriangle,
  Play,
  RotateCcw,
  ChevronDown,
  ChevronUp,
  Copy,
  ExternalLink,
  Trash2,
  Bug,
  Activity,
  Settings,
  Info,
  Heart,
  Bell,
  BellRing,
  Calendar,
  TrendingUp,
  Pause,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { MainLayout } from '@/components/layout/MainLayout';
import { getPublicApiBaseUrl, isDev } from '@/lib/env';

// Types
interface PaymentLog {
  trace_id: string;
  provider: string;
  timestamp: string;
  request: {
    method: string;
    url: string;
    headers: Record<string, string>;
    payload?: unknown;
  };
  response: {
    status_code: number | null;
    body?: unknown;
  };
  latency_ms: number;
  success: boolean;
  error?: string;
}

interface ClientError {
  id: string;
  error_type: string;
  message: string;
  url: string;
  timestamp: string;
  stack?: string;
  component_stack?: string;
  metadata?: Record<string, unknown>;
}

interface EnvCheckResult {
  variable: string;
  present: boolean;
  valid_format: boolean;
  value_preview?: string;
  error?: string;
}

interface APIKeyValidation {
  provider: string;
  key_type: string;
  status: 'valid' | 'invalid' | 'missing' | 'error';
  message?: string;
  last_checked: string;
}

interface TestScenarioResult {
  step: string;
  status: 'pass' | 'fail' | 'skip' | 'pending';
  message?: string;
  latency_ms?: number;
  details?: Record<string, unknown>;
}

interface PerfMetric {
  count: number;
  avg_ms?: number;
  min_ms?: number;
  max_ms?: number;
  recent: Array<{ id: string; value_ms: number; timestamp: string }>;
}

interface CorsSslIssue {
  id: string;
  issue_type: string;
  url: string;
  message: string;
  timestamp: string;
}

// Health Check Types
interface HealthCheckResult {
  provider: string;
  check_name: string;
  status: 'pass' | 'fail' | 'warn' | 'skip';
  latency_ms: number;
  message: string;
  timestamp: string;
  details?: Record<string, unknown>;
}

interface ProviderHealth {
  overall: 'healthy' | 'degraded' | 'down' | 'unknown';
  checks: Record<string, string>;
  last_checked: string | null;
  latency_ms: number;
  details?: Record<string, unknown>;
}

interface HealthSnapshot {
  paymob: ProviderHealth;
  paypal: ProviderHealth;
  scheduler_running: boolean;
  last_run?: string;
  duration_ms?: number;
}

interface HealthHistoryEntry {
  id: string;
  provider: string;
  check_name: string;
  status: string;
  latency_ms: number;
  message: string;
  timestamp: string;
  details?: Record<string, unknown>;
}

interface AlertItem {
  id: string;
  provider: string;
  check_name: string;
  status: string;
  message: string;
  timestamp: string;
  acknowledged: boolean;
  acknowledged_at?: string;
  acknowledged_by?: string;
  details?: Record<string, unknown>;
}

interface SchedulerStatus {
  running: boolean;
  interval_minutes: number;
  environment: string;
  enabled: boolean;
}

const getApiUrl = () => getPublicApiBaseUrl();

const isDevOrStaging = () => {
  return isDev || ['staging', 'test'].includes(process.env.NEXT_PUBLIC_APP_ENV || '');
};

// Status badge component
function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { icon: typeof CheckCircle; className: string }> = {
    valid: { icon: CheckCircle, className: 'text-green-500 bg-green-50 dark:bg-green-950' },
    invalid: { icon: XCircle, className: 'text-red-500 bg-red-50 dark:bg-red-950' },
    missing: { icon: AlertCircle, className: 'text-yellow-500 bg-yellow-50 dark:bg-yellow-950' },
    error: { icon: AlertTriangle, className: 'text-orange-500 bg-orange-50 dark:bg-orange-950' },
    pass: { icon: CheckCircle, className: 'text-green-500 bg-green-50 dark:bg-green-950' },
    fail: { icon: XCircle, className: 'text-red-500 bg-red-50 dark:bg-red-950' },
    skip: { icon: AlertCircle, className: 'text-gray-500 bg-gray-50 dark:bg-gray-950' },
    pending: { icon: Clock, className: 'text-blue-500 bg-blue-50 dark:bg-blue-950' },
  };
  
  const { icon: Icon, className } = config[status] || config.error;
  
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${className}`}>
      <Icon className="h-3 w-3" />
      {status}
    </span>
  );
}

// Provider badge
function ProviderBadge({ provider }: { provider: string }) {
  const colors: Record<string, string> = {
    paymob: 'bg-purple-100 text-purple-700 dark:bg-purple-950 dark:text-purple-300',
    paypal: 'bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300',
    stripe: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300',
  };
  
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${colors[provider] || 'bg-gray-100 text-gray-700'}`}>
      {provider.toUpperCase()}
    </span>
  );
}

// Collapsible section
function CollapsibleSection({
  title,
  icon: Icon,
  children,
  defaultOpen = true,
  badge,
}: {
  title: string;
  icon: typeof Key;
  children: React.ReactNode;
  defaultOpen?: boolean;
  badge?: React.ReactNode;
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  
  return (
    <div className="border rounded-lg bg-card">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-4 hover:bg-muted/50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Icon className="h-5 w-5 text-muted-foreground" />
          <span className="font-medium">{title}</span>
          {badge}
        </div>
        {isOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
      </button>
      {isOpen && <div className="p-4 pt-0 border-t">{children}</div>}
    </div>
  );
}

// JSON viewer
function JsonViewer({ data, maxHeight = 200 }: { data: unknown; maxHeight?: number }) {
  const [copied, setCopied] = useState(false);
  
  const jsonString = JSON.stringify(data, null, 2);
  
  const handleCopy = async () => {
    await navigator.clipboard.writeText(jsonString);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  
  return (
    <div className="relative">
      <button
        onClick={handleCopy}
        className="absolute top-2 right-2 p-1 rounded hover:bg-muted text-muted-foreground"
      >
        {copied ? <CheckCircle className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4" />}
      </button>
      <pre
        className="bg-muted p-3 rounded text-xs overflow-auto font-mono"
        style={{ maxHeight }}
      >
        {jsonString}
      </pre>
    </div>
  );
}

export default function PaymentDebugDashboard() {
  // State
  const [logs, setLogs] = useState<PaymentLog[]>([]);
  const [clientErrors, setClientErrors] = useState<ClientError[]>([]);
  const [envCheck, setEnvCheck] = useState<Record<string, unknown> | null>(null);
  const [apiValidations, setApiValidations] = useState<APIKeyValidation[]>([]);
  const [perfMetrics, setPerfMetrics] = useState<Record<string, PerfMetric>>({});
  const [corsSslIssues, setCorsSslIssues] = useState<CorsSslIssue[]>([]);
  const [testResults, setTestResults] = useState<Record<string, { results: TestScenarioResult[]; passed: boolean } | null>>({});
  const [replayCandidates, setReplayCandidates] = useState<Array<{ trace_id: string; provider: string; error?: string }>>([]);
  
  // Health monitoring state
  const [healthSnapshot, setHealthSnapshot] = useState<HealthSnapshot | null>(null);
  const [healthHistory, setHealthHistory] = useState<HealthHistoryEntry[]>([]);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [schedulerStatus, setSchedulerStatus] = useState<SchedulerStatus | null>(null);
  const [unacknowledgedCount, setUnacknowledgedCount] = useState(0);
  
  const [loading, setLoading] = useState<Record<string, boolean>>({});
  const [activeTab, setActiveTab] = useState<'overview' | 'logs' | 'errors' | 'replay' | 'tests' | 'health' | 'alerts'>('overview');
  const [selectedLog, setSelectedLog] = useState<PaymentLog | null>(null);
  const [replayModifications, setReplayModifications] = useState<Record<string, unknown>>({});
  
  // Check environment access
  if (!isDevOrStaging()) {
    return (
      <MainLayout>
        <div className="container py-16 flex flex-col items-center justify-center min-h-[50vh]">
          <Shield className="h-16 w-16 text-muted-foreground/50 mb-4" />
          <h2 className="text-xl font-semibold mb-2">Access Denied</h2>
          <p className="text-muted-foreground text-center max-w-md">
            The debug dashboard is only accessible in development or staging environments.
          </p>
        </div>
      </MainLayout>
    );
  }
  
  // Fetch functions
  const fetchLogs = useCallback(async () => {
    setLoading((l) => ({ ...l, logs: true }));
    try {
      const res = await fetch(`${getApiUrl()}/debug/logs?limit=50`);
      const data = await res.json();
      setLogs(data.logs || []);
    } catch (e) {
      console.error('Failed to fetch logs:', e);
    } finally {
      setLoading((l) => ({ ...l, logs: false }));
    }
  }, []);
  
  const fetchClientErrors = useCallback(async () => {
    try {
      const res = await fetch(`${getApiUrl()}/debug/client-errors?limit=50`);
      const data = await res.json();
      setClientErrors(data.errors || []);
    } catch (e) {
      console.error('Failed to fetch client errors:', e);
    }
  }, []);
  
  const fetchEnvCheck = useCallback(async () => {
    setLoading((l) => ({ ...l, env: true }));
    try {
      const res = await fetch(`${getApiUrl()}/debug/env-check`);
      const data = await res.json();
      setEnvCheck(data);
    } catch (e) {
      console.error('Failed to fetch env check:', e);
    } finally {
      setLoading((l) => ({ ...l, env: false }));
    }
  }, []);
  
  const fetchApiValidations = useCallback(async () => {
    setLoading((l) => ({ ...l, apiKeys: true }));
    try {
      const res = await fetch(`${getApiUrl()}/debug/api-keys/validate`);
      const data = await res.json();
      setApiValidations(data.validations || []);
    } catch (e) {
      console.error('Failed to fetch API validations:', e);
    } finally {
      setLoading((l) => ({ ...l, apiKeys: false }));
    }
  }, []);
  
  const fetchPerfMetrics = useCallback(async () => {
    try {
      const res = await fetch(`${getApiUrl()}/debug/perf-metrics`);
      const data = await res.json();
      setPerfMetrics(data);
    } catch (e) {
      console.error('Failed to fetch perf metrics:', e);
    }
  }, []);
  
  const fetchCorsSslIssues = useCallback(async () => {
    try {
      const res = await fetch(`${getApiUrl()}/debug/cors-ssl-issues`);
      const data = await res.json();
      setCorsSslIssues(data.issues || []);
    } catch (e) {
      console.error('Failed to fetch CORS/SSL issues:', e);
    }
  }, []);
  
  const fetchReplayCandidates = useCallback(async () => {
    try {
      const res = await fetch(`${getApiUrl()}/debug/replay/candidates`);
      const data = await res.json();
      setReplayCandidates(data.candidates || []);
    } catch (e) {
      console.error('Failed to fetch replay candidates:', e);
    }
  }, []);
  
  const runTestScenario = useCallback(async (provider: 'paymob' | 'paypal') => {
    setLoading((l) => ({ ...l, [`test_${provider}`]: true }));
    try {
      const res = await fetch(`${getApiUrl()}/debug/test-scenarios/${provider}`, { method: 'POST' });
      const data = await res.json();
      setTestResults((r) => ({ ...r, [provider]: data }));
    } catch (e) {
      console.error('Failed to run test scenario:', e);
    } finally {
      setLoading((l) => ({ ...l, [`test_${provider}`]: false }));
    }
  }, []);
  
  const replayRequest = useCallback(async (traceId: string) => {
    setLoading((l) => ({ ...l, replay: true }));
    try {
      const res = await fetch(`${getApiUrl()}/debug/replay`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          trace_id: traceId,
          modifications: replayModifications,
        }),
      });
      const data = await res.json();
      // Refresh logs to show new entry
      fetchLogs();
      return data;
    } catch (e) {
      console.error('Failed to replay request:', e);
    } finally {
      setLoading((l) => ({ ...l, replay: false }));
    }
  }, [replayModifications, fetchLogs]);
  
  const clearLogs = useCallback(async () => {
    await fetch(`${getApiUrl()}/debug/logs`, { method: 'DELETE' });
    setLogs([]);
  }, []);
  
  const clearClientErrors = useCallback(async () => {
    await fetch(`${getApiUrl()}/debug/client-errors`, { method: 'DELETE' });
    setClientErrors([]);
  }, []);
  
  // Health monitoring fetch functions
  const fetchHealthSnapshot = useCallback(async () => {
    try {
      const res = await fetch(`${getApiUrl()}/debug/health`);
      const data = await res.json();
      setHealthSnapshot(data);
    } catch (e) {
      console.error('Failed to fetch health snapshot:', e);
    }
  }, []);
  
  const fetchHealthHistory = useCallback(async (limit = 50) => {
    setLoading((l) => ({ ...l, healthHistory: true }));
    try {
      const res = await fetch(`${getApiUrl()}/debug/health/history?limit=${limit}`);
      const data = await res.json();
      setHealthHistory(data.entries || []);
    } catch (e) {
      console.error('Failed to fetch health history:', e);
    } finally {
      setLoading((l) => ({ ...l, healthHistory: false }));
    }
  }, []);
  
  const fetchAlerts = useCallback(async () => {
    try {
      const res = await fetch(`${getApiUrl()}/debug/alerts`);
      const data = await res.json();
      setAlerts(data.alerts || []);
      setUnacknowledgedCount(data.unacknowledged || 0);
    } catch (e) {
      console.error('Failed to fetch alerts:', e);
    }
  }, []);
  
  const fetchSchedulerStatus = useCallback(async () => {
    try {
      const res = await fetch(`${getApiUrl()}/debug/scheduler/status`);
      const data = await res.json();
      setSchedulerStatus(data);
    } catch (e) {
      console.error('Failed to fetch scheduler status:', e);
    }
  }, []);
  
  const triggerHealthCheck = useCallback(async () => {
    setLoading((l) => ({ ...l, healthTrigger: true }));
    try {
      const res = await fetch(`${getApiUrl()}/debug/health/trigger`, { method: 'POST' });
      const data = await res.json();
      setHealthSnapshot(data);
    } catch (e) {
      console.error('Failed to trigger health check:', e);
    } finally {
      setLoading((l) => ({ ...l, healthTrigger: false }));
    }
  }, []);
  
  const acknowledgeAlert = useCallback(async (alertId: string) => {
    try {
      await fetch(`${getApiUrl()}/debug/alerts/${alertId}/acknowledge`, { method: 'POST' });
      fetchAlerts();
    } catch (e) {
      console.error('Failed to acknowledge alert:', e);
    }
  }, [fetchAlerts]);
  
  const acknowledgeAllAlerts = useCallback(async () => {
    try {
      await fetch(`${getApiUrl()}/debug/alerts/acknowledge-all`, { method: 'POST' });
      fetchAlerts();
    } catch (e) {
      console.error('Failed to acknowledge all alerts:', e);
    }
  }, [fetchAlerts]);
  
  const toggleScheduler = useCallback(async (action: 'start' | 'stop') => {
    try {
      await fetch(`${getApiUrl()}/debug/scheduler/${action}`, { method: 'POST' });
      fetchSchedulerStatus();
    } catch (e) {
      console.error(`Failed to ${action} scheduler:`, e);
    }
  }, [fetchSchedulerStatus]);
  
  // Initial fetch
  useEffect(() => {
    fetchLogs();
    fetchClientErrors();
    fetchEnvCheck();
    fetchApiValidations();
    fetchPerfMetrics();
    fetchCorsSslIssues();
    fetchReplayCandidates();
    fetchHealthSnapshot();
    fetchAlerts();
    fetchSchedulerStatus();
  }, [fetchLogs, fetchClientErrors, fetchEnvCheck, fetchApiValidations, fetchPerfMetrics, fetchCorsSslIssues, fetchReplayCandidates, fetchHealthSnapshot, fetchAlerts, fetchSchedulerStatus]);
  
  // Auto-refresh logs
  useEffect(() => {
    const interval = setInterval(fetchLogs, 30000);
    return () => clearInterval(interval);
  }, [fetchLogs]);
  
  // Auto-refresh health snapshot and alerts
  useEffect(() => {
    const interval = setInterval(() => {
      fetchHealthSnapshot();
      fetchAlerts();
    }, 60000); // Every minute
    return () => clearInterval(interval);
  }, [fetchHealthSnapshot, fetchAlerts]);
  
  // Calculate stats
  const stats = {
    totalLogs: logs.length,
    successCount: logs.filter((l) => l.success).length,
    failCount: logs.filter((l) => !l.success).length,
    avgLatency: logs.length > 0 ? logs.reduce((a, l) => a + l.latency_ms, 0) / logs.length : 0,
    clientErrorCount: clientErrors.length,
    corsSslIssueCount: corsSslIssues.length,
  };
  
  return (
    <MainLayout>
      <div className="container py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-display font-semibold flex items-center gap-2">
              <Bug className="h-6 w-6" />
              Payment Debug Dashboard
            </h1>
            <p className="text-muted-foreground text-sm mt-1">
              Real-time visibility into Paymob and PayPal integrations
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => {
              fetchLogs();
              fetchClientErrors();
              fetchEnvCheck();
              fetchApiValidations();
              fetchPerfMetrics();
              fetchCorsSslIssues();
              fetchReplayCandidates();
            }}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh All
            </Button>
          </div>
        </div>
        
        {/* Quick Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-card border rounded-lg p-4">
            <div className="flex items-center gap-2 text-muted-foreground text-sm mb-1">
              <Activity className="h-4 w-4" />
              Total Requests
            </div>
            <div className="text-2xl font-semibold">{stats.totalLogs}</div>
          </div>
          <div className="bg-card border rounded-lg p-4">
            <div className="flex items-center gap-2 text-muted-foreground text-sm mb-1">
              <CheckCircle className="h-4 w-4 text-green-500" />
              Success Rate
            </div>
            <div className="text-2xl font-semibold">
              {stats.totalLogs > 0 ? ((stats.successCount / stats.totalLogs) * 100).toFixed(1) : 0}%
            </div>
          </div>
          <div className="bg-card border rounded-lg p-4">
            <div className="flex items-center gap-2 text-muted-foreground text-sm mb-1">
              <Clock className="h-4 w-4" />
              Avg Latency
            </div>
            <div className="text-2xl font-semibold">{stats.avgLatency.toFixed(0)}ms</div>
          </div>
          <div className="bg-card border rounded-lg p-4">
            <div className="flex items-center gap-2 text-muted-foreground text-sm mb-1">
              <AlertCircle className="h-4 w-4 text-red-500" />
              Issues
            </div>
            <div className="text-2xl font-semibold">{stats.failCount + stats.clientErrorCount + stats.corsSslIssueCount}</div>
          </div>
        </div>
        
        {/* Tabs */}
        <div className="flex gap-2 mb-6 border-b overflow-x-auto">
          {[
            { id: 'overview', label: 'Overview', icon: Globe },
            { id: 'health', label: 'Health', icon: Heart, badge: healthSnapshot && (healthSnapshot.paymob.overall === 'down' || healthSnapshot.paypal.overall === 'down') ? '!' : null },
            { id: 'alerts', label: 'Alerts', icon: Bell, badge: unacknowledgedCount > 0 ? unacknowledgedCount.toString() : null },
            { id: 'logs', label: 'Transaction Logs', icon: Activity },
            { id: 'errors', label: 'Client Errors', icon: AlertCircle },
            { id: 'replay', label: 'Request Replay', icon: RotateCcw },
            { id: 'tests', label: 'Test Scenarios', icon: Play },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as typeof activeTab)}
              className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                activeTab === tab.id
                  ? 'border-accent text-accent'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
            >
              <tab.icon className="h-4 w-4" />
              {tab.label}
              {tab.badge && (
                <span className={`px-1.5 py-0.5 rounded-full text-xs ${
                  tab.badge === '!' ? 'bg-red-100 text-red-700' : 'bg-orange-100 text-orange-700'
                }`}>
                  {tab.badge}
                </span>
              )}
            </button>
          ))}
        </div>
        
        {/* Tab Content */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* API Key Validation Panel */}
            <CollapsibleSection title="API Key Validation" icon={Key} badge={
              apiValidations.length > 0 && (
                <span className="ml-2">
                  {apiValidations.every((v) => v.status === 'valid') ? (
                    <CheckCircle className="h-4 w-4 text-green-500" />
                  ) : (
                    <AlertCircle className="h-4 w-4 text-yellow-500" />
                  )}
                </span>
              )
            }>
              <div className="flex justify-between items-center mb-4">
                <span className="text-sm text-muted-foreground">Live validation of payment provider credentials</span>
                <Button variant="outline" size="sm" onClick={fetchApiValidations} disabled={loading.apiKeys}>
                  {loading.apiKeys ? <RefreshCw className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
                </Button>
              </div>
              <div className="grid gap-3">
                {apiValidations.map((v, i) => (
                  <div key={i} className="flex items-center justify-between p-3 bg-muted/50 rounded">
                    <div>
                      <div className="font-medium">{v.provider.toUpperCase()} - {v.key_type}</div>
                      {v.message && <div className="text-xs text-muted-foreground">{v.message}</div>}
                    </div>
                    <StatusBadge status={v.status} />
                  </div>
                ))}
                {apiValidations.length === 0 && (
                  <div className="text-muted-foreground text-sm">Click refresh to validate API keys</div>
                )}
              </div>
            </CollapsibleSection>
            
            {/* Environment Status */}
            <CollapsibleSection title="Environment Variables" icon={Settings}>
              {envCheck ? (
                <div className="space-y-4">
                  <div className="flex items-center gap-4 text-sm">
                    <span className="px-2 py-1 bg-muted rounded font-mono">{envCheck.environment}</span>
                    <span className={envCheck.debug_mode ? 'text-green-500' : 'text-yellow-500'}>
                      Debug: {envCheck.debug_mode ? 'ON' : 'OFF'}
                    </span>
                  </div>
                  
                  {envCheck.issues && (envCheck.issues as string[]).length > 0 && (
                    <div className="bg-yellow-50 dark:bg-yellow-950 border border-yellow-200 rounded p-3">
                      <div className="font-medium text-yellow-800 dark:text-yellow-200 mb-2">Issues Found</div>
                      <ul className="text-sm space-y-1">
                        {(envCheck.issues as string[]).map((issue, i) => (
                          <li key={i} className="text-yellow-700 dark:text-yellow-300">• {issue}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  
                  {envCheck.providers && (
                    <div className="grid md:grid-cols-3 gap-4">
                      {Object.entries(envCheck.providers as Record<string, { configured: boolean; variables: EnvCheckResult[] }>).map(([provider, data]) => (
                        <div key={provider} className="border rounded p-3">
                          <div className="flex items-center justify-between mb-2">
                            <span className="font-medium capitalize">{provider}</span>
                            {data.configured ? (
                              <CheckCircle className="h-4 w-4 text-green-500" />
                            ) : (
                              <XCircle className="h-4 w-4 text-red-500" />
                            )}
                          </div>
                          <div className="space-y-1">
                            {data.variables.map((v) => (
                              <div key={v.variable} className="flex items-center justify-between text-xs">
                                <span className="font-mono text-muted-foreground">{v.variable}</span>
                                {v.present ? (
                                  v.valid_format ? (
                                    <CheckCircle className="h-3 w-3 text-green-500" />
                                  ) : (
                                    <AlertTriangle className="h-3 w-3 text-yellow-500" />
                                  )
                                ) : (
                                  <XCircle className="h-3 w-3 text-red-500" />
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-muted-foreground">Loading...</div>
              )}
            </CollapsibleSection>
            
            {/* Performance Metrics */}
            <CollapsibleSection title="Rendering Performance" icon={Zap}>
              <div className="grid md:grid-cols-3 gap-4">
                {Object.entries(perfMetrics).map(([type, data]) => (
                  <div key={type} className="border rounded p-3">
                    <div className="font-medium capitalize mb-2">{type.replace('_', ' ')}</div>
                    {data.count > 0 ? (
                      <>
                        <div className="grid grid-cols-3 gap-2 text-xs mb-2">
                          <div>
                            <div className="text-muted-foreground">Avg</div>
                            <div className="font-mono">{data.avg_ms?.toFixed(0)}ms</div>
                          </div>
                          <div>
                            <div className="text-muted-foreground">Min</div>
                            <div className="font-mono">{data.min_ms?.toFixed(0)}ms</div>
                          </div>
                          <div>
                            <div className="text-muted-foreground">Max</div>
                            <div className="font-mono">{data.max_ms?.toFixed(0)}ms</div>
                          </div>
                        </div>
                        <div className="text-xs text-muted-foreground">{data.count} samples</div>
                      </>
                    ) : (
                      <div className="text-xs text-muted-foreground">No data yet</div>
                    )}
                  </div>
                ))}
              </div>
            </CollapsibleSection>
            
            {/* CORS/SSL Issues */}
            <CollapsibleSection title="CORS & SSL Issues" icon={Shield} defaultOpen={corsSslIssues.length > 0}>
              {corsSslIssues.length > 0 ? (
                <div className="space-y-2">
                  {corsSslIssues.map((issue) => (
                    <div key={issue.id} className="flex items-center justify-between p-3 bg-red-50 dark:bg-red-950 border border-red-200 rounded">
                      <div>
                        <div className="font-medium">{issue.issue_type.toUpperCase()}</div>
                        <div className="text-sm text-muted-foreground">{issue.url}</div>
                        <div className="text-xs">{issue.message}</div>
                      </div>
                      <span className="text-xs text-muted-foreground">{new Date(issue.timestamp).toLocaleTimeString()}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-muted-foreground text-sm flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-green-500" />
                  No CORS or SSL issues detected
                </div>
              )}
            </CollapsibleSection>
          </div>
        )}
        
        {activeTab === 'health' && (
          <div className="space-y-6">
            {/* Health Status Header */}
            <div className="flex items-center justify-between">
              <h2 className="font-medium">Provider Health Status</h2>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={triggerHealthCheck}
                  disabled={loading.healthTrigger}
                >
                  {loading.healthTrigger ? (
                    <RefreshCw className="h-4 w-4 animate-spin" />
                  ) : (
                    <Play className="h-4 w-4" />
                  )}
                  <span className="ml-2">Run Check</span>
                </Button>
                <Button variant="outline" size="sm" onClick={fetchHealthSnapshot}>
                  <RefreshCw className="h-4 w-4" />
                </Button>
              </div>
            </div>
            
            {/* Scheduler Status */}
            {schedulerStatus && (
              <div className="bg-muted/50 border rounded-lg p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {schedulerStatus.running ? (
                    <div className="flex items-center gap-2 text-green-600">
                      <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
                      Scheduler Running
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 text-yellow-600">
                      <Pause className="h-4 w-4" />
                      Scheduler Paused
                    </div>
                  )}
                  <span className="text-sm text-muted-foreground">
                    Interval: {schedulerStatus.interval_minutes} min
                  </span>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => toggleScheduler(schedulerStatus.running ? 'stop' : 'start')}
                >
                  {schedulerStatus.running ? 'Stop' : 'Start'}
                </Button>
              </div>
            )}
            
            {/* Provider Health Cards */}
            <div className="grid md:grid-cols-2 gap-6">
              {/* Paymob Health */}
              <div className={`border rounded-lg p-4 ${
                healthSnapshot?.paymob.overall === 'healthy' ? 'border-green-200 bg-green-50/50 dark:bg-green-950/50' :
                healthSnapshot?.paymob.overall === 'degraded' ? 'border-yellow-200 bg-yellow-50/50 dark:bg-yellow-950/50' :
                healthSnapshot?.paymob.overall === 'down' ? 'border-red-200 bg-red-50/50 dark:bg-red-950/50' : ''
              }`}>
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <ProviderBadge provider="paymob" />
                    <span className="font-medium">Paymob</span>
                  </div>
                  <StatusBadge status={healthSnapshot?.paymob.overall || 'unknown'} />
                </div>
                
                {healthSnapshot?.paymob.last_checked && (
                  <div className="text-xs text-muted-foreground mb-3">
                    Last checked: {new Date(healthSnapshot.paymob.last_checked).toLocaleString()}
                  </div>
                )}
                
                <div className="space-y-2">
                  {healthSnapshot?.paymob.checks && Object.entries(healthSnapshot.paymob.checks).map(([check, status]) => (
                    <div key={check} className="flex items-center justify-between p-2 bg-background/50 rounded">
                      <span className="text-sm capitalize">{check.replace(/_/g, ' ')}</span>
                      <StatusBadge status={status} />
                    </div>
                  ))}
                  {(!healthSnapshot?.paymob.checks || Object.keys(healthSnapshot.paymob.checks).length === 0) && (
                    <div className="text-sm text-muted-foreground">No checks run yet</div>
                  )}
                </div>
              </div>
              
              {/* PayPal Health */}
              <div className={`border rounded-lg p-4 ${
                healthSnapshot?.paypal.overall === 'healthy' ? 'border-green-200 bg-green-50/50 dark:bg-green-950/50' :
                healthSnapshot?.paypal.overall === 'degraded' ? 'border-yellow-200 bg-yellow-50/50 dark:bg-yellow-950/50' :
                healthSnapshot?.paypal.overall === 'down' ? 'border-red-200 bg-red-50/50 dark:bg-red-950/50' : ''
              }`}>
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <ProviderBadge provider="paypal" />
                    <span className="font-medium">PayPal</span>
                  </div>
                  <StatusBadge status={healthSnapshot?.paypal.overall || 'unknown'} />
                </div>
                
                {healthSnapshot?.paypal.last_checked && (
                  <div className="text-xs text-muted-foreground mb-3">
                    Last checked: {new Date(healthSnapshot.paypal.last_checked).toLocaleString()}
                  </div>
                )}
                
                <div className="space-y-2">
                  {healthSnapshot?.paypal.checks && Object.entries(healthSnapshot.paypal.checks).map(([check, status]) => (
                    <div key={check} className="flex items-center justify-between p-2 bg-background/50 rounded">
                      <span className="text-sm capitalize">{check.replace(/_/g, ' ')}</span>
                      <StatusBadge status={status} />
                    </div>
                  ))}
                  {(!healthSnapshot?.paypal.checks || Object.keys(healthSnapshot.paypal.checks).length === 0) && (
                    <div className="text-sm text-muted-foreground">No checks run yet</div>
                  )}
                </div>
              </div>
            </div>
            
            {/* Health History */}
            <CollapsibleSection title="Health Check History" icon={TrendingUp} defaultOpen={false}>
              <div className="flex justify-between items-center mb-4">
                <span className="text-sm text-muted-foreground">Recent health check results</span>
                <Button variant="outline" size="sm" onClick={() => fetchHealthHistory(100)} disabled={loading.healthHistory}>
                  <RefreshCw className={`h-4 w-4 ${loading.healthHistory ? 'animate-spin' : ''}`} />
                </Button>
              </div>
              
              {healthHistory.length > 0 ? (
                <div className="max-h-64 overflow-y-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-muted sticky top-0">
                      <tr>
                        <th className="text-left p-2">Time</th>
                        <th className="text-left p-2">Provider</th>
                        <th className="text-left p-2">Check</th>
                        <th className="text-left p-2">Status</th>
                        <th className="text-left p-2">Latency</th>
                      </tr>
                    </thead>
                    <tbody>
                      {healthHistory.slice(0, 50).map((entry) => (
                        <tr key={entry.id} className="border-t">
                          <td className="p-2 text-xs text-muted-foreground">
                            {new Date(entry.timestamp).toLocaleTimeString()}
                          </td>
                          <td className="p-2"><ProviderBadge provider={entry.provider} /></td>
                          <td className="p-2 text-xs capitalize">{entry.check_name.replace(/_/g, ' ')}</td>
                          <td className="p-2"><StatusBadge status={entry.status} /></td>
                          <td className="p-2 text-xs font-mono">{entry.latency_ms.toFixed(0)}ms</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-muted-foreground text-sm">No health history yet</div>
              )}
            </CollapsibleSection>
          </div>
        )}
        
        {activeTab === 'alerts' && (
          <div className="space-y-6">
            {/* Alerts Header */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <h2 className="font-medium">Active Alerts</h2>
                {unacknowledgedCount > 0 && (
                  <span className="px-2 py-1 rounded-full text-xs bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300">
                    {unacknowledgedCount} unacknowledged
                  </span>
                )}
              </div>
              <div className="flex gap-2">
                {unacknowledgedCount > 0 && (
                  <Button variant="outline" size="sm" onClick={acknowledgeAllAlerts}>
                    <CheckCircle className="h-4 w-4 mr-2" />
                    Acknowledge All
                  </Button>
                )}
                <Button variant="outline" size="sm" onClick={fetchAlerts}>
                  <RefreshCw className="h-4 w-4" />
                </Button>
              </div>
            </div>
            
            {/* Alerts List */}
            {alerts.length > 0 ? (
              <div className="space-y-3">
                {alerts.map((alert) => (
                  <div
                    key={alert.id}
                    className={`border rounded-lg p-4 ${
                      alert.acknowledged
                        ? 'bg-muted/30 border-muted'
                        : alert.status === 'fail'
                        ? 'bg-red-50 dark:bg-red-950/50 border-red-200'
                        : 'bg-yellow-50 dark:bg-yellow-950/50 border-yellow-200'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-start gap-3">
                        {alert.acknowledged ? (
                          <CheckCircle className="h-5 w-5 text-muted-foreground mt-0.5" />
                        ) : alert.status === 'fail' ? (
                          <BellRing className="h-5 w-5 text-red-500 mt-0.5" />
                        ) : (
                          <AlertTriangle className="h-5 w-5 text-yellow-500 mt-0.5" />
                        )}
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <ProviderBadge provider={alert.provider} />
                            <StatusBadge status={alert.status} />
                            <span className="text-sm font-medium capitalize">
                              {alert.check_name.replace(/_/g, ' ')}
                            </span>
                          </div>
                          <p className="text-sm">{alert.message}</p>
                          <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                            <span className="flex items-center gap-1">
                              <Calendar className="h-3 w-3" />
                              {new Date(alert.timestamp).toLocaleString()}
                            </span>
                            {alert.acknowledged && alert.acknowledged_at && (
                              <span className="flex items-center gap-1">
                                <CheckCircle className="h-3 w-3" />
                                Acknowledged {new Date(alert.acknowledged_at).toLocaleString()}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                      {!alert.acknowledged && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => acknowledgeAlert(alert.id)}
                        >
                          Acknowledge
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="border rounded-lg p-8 text-center">
                <Bell className="h-12 w-12 text-muted-foreground/50 mx-auto mb-3" />
                <h3 className="font-medium mb-1">No Alerts</h3>
                <p className="text-sm text-muted-foreground">
                  All systems healthy. Alerts will appear here when issues are detected.
                </p>
              </div>
            )}
            
            {/* Alert Settings Info */}
            <div className="bg-blue-50 dark:bg-blue-950 border border-blue-200 rounded-lg p-4">
              <div className="flex items-start gap-2">
                <Info className="h-5 w-5 text-blue-500 mt-0.5" />
                <div className="text-sm">
                  <div className="font-medium text-blue-800 dark:text-blue-200">About Alerts</div>
                  <ul className="mt-1 text-blue-700 dark:text-blue-300 space-y-1">
                    <li>Alerts are triggered on state changes (pass → fail/warn)</li>
                    <li>Configure Slack webhooks via <code className="text-xs bg-blue-100 dark:bg-blue-900 px-1 rounded">SLACK_WEBHOOK_URL</code></li>
                    <li>Configure email alerts via <code className="text-xs bg-blue-100 dark:bg-blue-900 px-1 rounded">SMTP_*</code> environment variables</li>
                    <li>Set API key expiry dates via <code className="text-xs bg-blue-100 dark:bg-blue-900 px-1 rounded">PAYMOB_KEY_EXPIRES_AT</code> and <code className="text-xs bg-blue-100 dark:bg-blue-900 px-1 rounded">PAYPAL_KEY_EXPIRES_AT</code></li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        )}
        
        {activeTab === 'logs' && (
          <div className="grid lg:grid-cols-3 gap-6">
            {/* Log List */}
            <div className="lg:col-span-2">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-medium">Recent Transactions</h2>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={fetchLogs} disabled={loading.logs}>
                    <RefreshCw className={`h-4 w-4 ${loading.logs ? 'animate-spin' : ''}`} />
                  </Button>
                  <Button variant="outline" size="sm" onClick={clearLogs}>
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              
              <div className="border rounded-lg overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-muted">
                    <tr>
                      <th className="text-left p-3">Provider</th>
                      <th className="text-left p-3">Method</th>
                      <th className="text-left p-3">Status</th>
                      <th className="text-left p-3">Latency</th>
                      <th className="text-left p-3">Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {logs.map((log) => (
                      <tr
                        key={log.trace_id}
                        onClick={() => setSelectedLog(log)}
                        className={`border-t cursor-pointer hover:bg-muted/50 ${
                          selectedLog?.trace_id === log.trace_id ? 'bg-muted' : ''
                        }`}
                      >
                        <td className="p-3"><ProviderBadge provider={log.provider} /></td>
                        <td className="p-3 font-mono text-xs">{log.request.method}</td>
                        <td className="p-3">
                          {log.success ? (
                            <span className="text-green-500">{log.response.status_code}</span>
                          ) : (
                            <span className="text-red-500">{log.response.status_code || 'ERR'}</span>
                          )}
                        </td>
                        <td className="p-3 font-mono text-xs">{log.latency_ms.toFixed(0)}ms</td>
                        <td className="p-3 text-xs text-muted-foreground">
                          {new Date(log.timestamp).toLocaleTimeString()}
                        </td>
                      </tr>
                    ))}
                    {logs.length === 0 && (
                      <tr>
                        <td colSpan={5} className="p-8 text-center text-muted-foreground">
                          No logs yet
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
            
            {/* Log Detail */}
            <div>
              <h2 className="font-medium mb-4">Log Detail</h2>
              {selectedLog ? (
                <div className="border rounded-lg p-4 space-y-4">
                  <div className="flex items-center justify-between">
                    <ProviderBadge provider={selectedLog.provider} />
                    <StatusBadge status={selectedLog.success ? 'pass' : 'fail'} />
                  </div>
                  
                  <div className="text-xs font-mono text-muted-foreground">{selectedLog.trace_id}</div>
                  
                  <div>
                    <div className="text-xs font-medium mb-1">Request</div>
                    <JsonViewer data={selectedLog.request} />
                  </div>
                  
                  <div>
                    <div className="text-xs font-medium mb-1">Response</div>
                    <JsonViewer data={selectedLog.response} />
                  </div>
                  
                  {selectedLog.error && (
                    <div className="bg-red-50 dark:bg-red-950 border border-red-200 rounded p-2 text-xs text-red-700 dark:text-red-300">
                      {selectedLog.error}
                    </div>
                  )}
                  
                  {!selectedLog.success && (
                    <Button
                      variant="outline"
                      size="sm"
                      className="w-full"
                      onClick={() => {
                        setActiveTab('replay');
                        setReplayModifications({});
                      }}
                    >
                      <RotateCcw className="h-4 w-4 mr-2" />
                      Replay Request
                    </Button>
                  )}
                </div>
              ) : (
                <div className="border rounded-lg p-8 text-center text-muted-foreground text-sm">
                  Select a log entry to view details
                </div>
              )}
            </div>
          </div>
        )}
        
        {activeTab === 'errors' && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-medium">Client-Side Errors</h2>
              <Button variant="outline" size="sm" onClick={clearClientErrors}>
                <Trash2 className="h-4 w-4 mr-2" />
                Clear
              </Button>
            </div>
            
            {clientErrors.length > 0 ? (
              <div className="space-y-3">
                {clientErrors.map((error) => (
                  <div key={error.id} className="border rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <StatusBadge status="fail" />
                        <span className="font-medium">{error.error_type}</span>
                      </div>
                      <span className="text-xs text-muted-foreground">{new Date(error.timestamp).toLocaleString()}</span>
                    </div>
                    <div className="text-sm mb-2">{error.message}</div>
                    <div className="text-xs text-muted-foreground font-mono truncate">{error.url}</div>
                    
                    {error.stack && (
                      <details className="mt-3">
                        <summary className="cursor-pointer text-xs text-muted-foreground">View Stack</summary>
                        <pre className="mt-2 p-2 bg-muted rounded text-xs overflow-auto max-h-32">
                          {error.stack}
                        </pre>
                      </details>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="border rounded-lg p-8 text-center text-muted-foreground">
                <CheckCircle className="h-8 w-8 mx-auto mb-2 text-green-500" />
                No client errors reported
              </div>
            )}
          </div>
        )}
        
        {activeTab === 'replay' && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-medium">Request Replay Tool</h2>
              <Button variant="outline" size="sm" onClick={fetchReplayCandidates}>
                <RefreshCw className="h-4 w-4" />
              </Button>
            </div>
            
            <div className="grid lg:grid-cols-2 gap-6">
              {/* Candidates */}
              <div>
                <h3 className="text-sm font-medium mb-3">Failed Requests</h3>
                <div className="space-y-2">
                  {replayCandidates.map((c) => (
                    <div
                      key={c.trace_id}
                      className="border rounded p-3 cursor-pointer hover:bg-muted/50"
                      onClick={async () => {
                        const result = await replayRequest(c.trace_id);
                        if (result) {
                          alert(`Replay complete: ${result.new_status}`);
                        }
                      }}
                    >
                      <div className="flex items-center justify-between">
                        <ProviderBadge provider={c.provider} />
                        <Button variant="outline" size="sm" disabled={loading.replay}>
                          {loading.replay ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                        </Button>
                      </div>
                      <div className="text-xs font-mono text-muted-foreground mt-1">{c.trace_id}</div>
                      {c.error && <div className="text-xs text-red-500 mt-1">{c.error}</div>}
                    </div>
                  ))}
                  {replayCandidates.length === 0 && (
                    <div className="text-muted-foreground text-sm">No failed requests to replay</div>
                  )}
                </div>
              </div>
              
              {/* Modifications */}
              <div>
                <h3 className="text-sm font-medium mb-3">Modifications (JSON)</h3>
                <textarea
                  className="w-full h-64 p-3 font-mono text-xs border rounded-lg bg-muted"
                  placeholder={`{
  "headers": { "X-Custom": "value" },
  "payload": { "amount": 1000 }
}`}
                  value={JSON.stringify(replayModifications, null, 2)}
                  onChange={(e) => {
                    try {
                      setReplayModifications(JSON.parse(e.target.value));
                    } catch {
                      // Invalid JSON, ignore
                    }
                  }}
                />
                <p className="text-xs text-muted-foreground mt-2">
                  Modify headers or payload before replaying a request
                </p>
              </div>
            </div>
          </div>
        )}
        
        {activeTab === 'tests' && (
          <div>
            <h2 className="font-medium mb-4">Automated Test Scenarios</h2>
            
            <div className="grid md:grid-cols-2 gap-6">
              {/* Paymob Test */}
              <div className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <ProviderBadge provider="paymob" />
                    <span className="font-medium">Flow Test</span>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => runTestScenario('paymob')}
                    disabled={loading.test_paymob}
                  >
                    {loading.test_paymob ? (
                      <RefreshCw className="h-4 w-4 animate-spin" />
                    ) : (
                      <Play className="h-4 w-4" />
                    )}
                  </Button>
                </div>
                
                {testResults.paymob ? (
                  <div className="space-y-2">
                    {testResults.paymob.results.map((r, i) => (
                      <div key={i} className="flex items-center justify-between p-2 bg-muted/50 rounded">
                        <div>
                          <div className="text-sm font-medium">{r.step}</div>
                          {r.message && <div className="text-xs text-muted-foreground">{r.message}</div>}
                        </div>
                        <div className="flex items-center gap-2">
                          {r.latency_ms && <span className="text-xs font-mono">{r.latency_ms.toFixed(0)}ms</span>}
                          <StatusBadge status={r.status} />
                        </div>
                      </div>
                    ))}
                    <div className={`mt-3 p-2 rounded ${testResults.paymob.passed ? 'bg-green-50 dark:bg-green-950' : 'bg-red-50 dark:bg-red-950'}`}>
                      <span className={testResults.paymob.passed ? 'text-green-700 dark:text-green-300' : 'text-red-700 dark:text-red-300'}>
                        {testResults.paymob.passed ? '✓ All steps passed' : '✗ Some steps failed'}
                      </span>
                    </div>
                  </div>
                ) : (
                  <div className="text-muted-foreground text-sm">Click play to run test</div>
                )}
              </div>
              
              {/* PayPal Test */}
              <div className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <ProviderBadge provider="paypal" />
                    <span className="font-medium">Flow Test</span>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => runTestScenario('paypal')}
                    disabled={loading.test_paypal}
                  >
                    {loading.test_paypal ? (
                      <RefreshCw className="h-4 w-4 animate-spin" />
                    ) : (
                      <Play className="h-4 w-4" />
                    )}
                  </Button>
                </div>
                
                {testResults.paypal ? (
                  <div className="space-y-2">
                    {testResults.paypal.results.map((r, i) => (
                      <div key={i} className="flex items-center justify-between p-2 bg-muted/50 rounded">
                        <div>
                          <div className="text-sm font-medium">{r.step}</div>
                          {r.message && <div className="text-xs text-muted-foreground">{r.message}</div>}
                        </div>
                        <div className="flex items-center gap-2">
                          {r.latency_ms && <span className="text-xs font-mono">{r.latency_ms.toFixed(0)}ms</span>}
                          <StatusBadge status={r.status} />
                        </div>
                      </div>
                    ))}
                    <div className={`mt-3 p-2 rounded ${testResults.paypal.passed ? 'bg-green-50 dark:bg-green-950' : 'bg-red-50 dark:bg-red-950'}`}>
                      <span className={testResults.paypal.passed ? 'text-green-700 dark:text-green-300' : 'text-red-700 dark:text-red-300'}>
                        {testResults.paypal.passed ? '✓ All steps passed' : '✗ Some steps failed'}
                      </span>
                    </div>
                  </div>
                ) : (
                  <div className="text-muted-foreground text-sm">Click play to run test</div>
                )}
              </div>
            </div>
            
            {/* Test Info */}
            <div className="mt-6 bg-blue-50 dark:bg-blue-950 border border-blue-200 rounded-lg p-4">
              <div className="flex items-start gap-2">
                <Info className="h-5 w-5 text-blue-500 mt-0.5" />
                <div className="text-sm">
                  <div className="font-medium text-blue-800 dark:text-blue-200">About Test Scenarios</div>
                  <ul className="mt-1 text-blue-700 dark:text-blue-300 space-y-1">
                    <li><strong>Paymob:</strong> Auth token → Order registration → Payment key generation</li>
                    <li><strong>PayPal:</strong> OAuth token → Order creation</li>
                    <li>Tests use minimal amounts and will not charge real money</li>
                    <li>Check the Transaction Logs tab for detailed request/response data</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </MainLayout>
  );
}
