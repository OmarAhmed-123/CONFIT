/**
 * CONFIT — Security Dashboard
 * ============================
 * AI-powered penetration testing dashboard integrated with PentAGI.
 * Premium dark-themed design with live scan monitoring.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  startScan,
  getScanStatus,
  getScanReport,
  listScans,
  checkHealth,
  SEVERITY_CONFIG,
  SCAN_TYPE_LABELS,
  STATUS_LABELS,
  type ScanType,
  type ScanStatus as ScanStatusType,
  type ScanListItem,
  type ScanReportResponse,
  type SecurityFinding,
  type HealthResponse,
} from '@/services/securityService';
import { getPublicApiBaseUrl } from '@/lib/env';

// ── Styles ───────────────────────────────────────────────────────────

const styles = {
  page: {
    minHeight: '100vh',
    background: 'linear-gradient(135deg, #0a0e1a 0%, #111827 50%, #0f172a 100%)',
    color: '#e2e8f0',
    fontFamily: "'Inter', 'Segoe UI', system-ui, sans-serif",
    padding: '2rem',
  } as React.CSSProperties,

  container: {
    maxWidth: '1400px',
    margin: '0 auto',
  } as React.CSSProperties,

  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: '2rem',
    flexWrap: 'wrap' as const,
    gap: '1rem',
  } as React.CSSProperties,

  title: {
    fontSize: '2rem',
    fontWeight: 700,
    background: 'linear-gradient(135deg, #60a5fa, #a78bfa, #f472b6)',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
    margin: 0,
  } as React.CSSProperties,

  subtitle: {
    fontSize: '0.9rem',
    color: '#94a3b8',
    margin: '0.25rem 0 0',
  } as React.CSSProperties,

  healthBadge: (healthy: boolean) => ({
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.5rem',
    padding: '0.5rem 1rem',
    borderRadius: '2rem',
    fontSize: '0.8rem',
    fontWeight: 600,
    background: healthy ? 'rgba(0, 230, 118, 0.1)' : 'rgba(255, 23, 68, 0.1)',
    border: `1px solid ${healthy ? 'rgba(0, 230, 118, 0.3)' : 'rgba(255, 23, 68, 0.3)'}`,
    color: healthy ? '#00e676' : '#ff1744',
  }) as React.CSSProperties,

  grid: {
    display: 'grid',
    gridTemplateColumns: '380px 1fr',
    gap: '1.5rem',
    alignItems: 'start',
  } as React.CSSProperties,

  card: {
    background: 'rgba(30, 41, 59, 0.6)',
    backdropFilter: 'blur(16px)',
    border: '1px solid rgba(148, 163, 184, 0.1)',
    borderRadius: '1rem',
    padding: '1.5rem',
    transition: 'border-color 0.3s',
  } as React.CSSProperties,

  cardTitle: {
    fontSize: '1.1rem',
    fontWeight: 600,
    color: '#f1f5f9',
    marginBottom: '1rem',
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
  } as React.CSSProperties,

  formGroup: {
    marginBottom: '1rem',
  } as React.CSSProperties,

  label: {
    display: 'block',
    fontSize: '0.8rem',
    fontWeight: 500,
    color: '#94a3b8',
    marginBottom: '0.4rem',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.05em',
  } as React.CSSProperties,

  input: {
    width: '100%',
    padding: '0.75rem 1rem',
    background: 'rgba(15, 23, 42, 0.8)',
    border: '1px solid rgba(148, 163, 184, 0.2)',
    borderRadius: '0.5rem',
    color: '#e2e8f0',
    fontSize: '0.9rem',
    outline: 'none',
    transition: 'border-color 0.2s',
    boxSizing: 'border-box' as const,
  } as React.CSSProperties,

  select: {
    width: '100%',
    padding: '0.75rem 1rem',
    background: 'rgba(15, 23, 42, 0.8)',
    border: '1px solid rgba(148, 163, 184, 0.2)',
    borderRadius: '0.5rem',
    color: '#e2e8f0',
    fontSize: '0.9rem',
    outline: 'none',
    boxSizing: 'border-box' as const,
    cursor: 'pointer',
  } as React.CSSProperties,

  textarea: {
    width: '100%',
    padding: '0.75rem 1rem',
    background: 'rgba(15, 23, 42, 0.8)',
    border: '1px solid rgba(148, 163, 184, 0.2)',
    borderRadius: '0.5rem',
    color: '#e2e8f0',
    fontSize: '0.9rem',
    outline: 'none',
    resize: 'vertical' as const,
    minHeight: '4rem',
    fontFamily: 'inherit',
    boxSizing: 'border-box' as const,
  } as React.CSSProperties,

  button: {
    width: '100%',
    padding: '0.85rem 1.5rem',
    background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
    border: 'none',
    borderRadius: '0.5rem',
    color: '#fff',
    fontSize: '0.95rem',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.3s',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '0.5rem',
  } as React.CSSProperties,

  buttonDisabled: {
    opacity: 0.5,
    cursor: 'not-allowed',
  } as React.CSSProperties,

  scanItem: {
    padding: '1rem',
    background: 'rgba(15, 23, 42, 0.5)',
    borderRadius: '0.75rem',
    border: '1px solid rgba(148, 163, 184, 0.08)',
    marginBottom: '0.75rem',
    cursor: 'pointer',
    transition: 'all 0.2s',
  } as React.CSSProperties,

  scanItemHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '0.4rem',
  } as React.CSSProperties,

  statusBadge: (status: ScanStatusType) => ({
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.3rem',
    padding: '0.2rem 0.6rem',
    borderRadius: '1rem',
    fontSize: '0.7rem',
    fontWeight: 600,
    background: `${STATUS_LABELS[status]?.color || '#78909c'}22`,
    color: STATUS_LABELS[status]?.color || '#78909c',
    border: `1px solid ${STATUS_LABELS[status]?.color || '#78909c'}44`,
  }) as React.CSSProperties,

  severityBadge: (severity: string) => {
    const config = SEVERITY_CONFIG[severity as keyof typeof SEVERITY_CONFIG] || SEVERITY_CONFIG.info;
    return {
      display: 'inline-flex',
      padding: '0.15rem 0.5rem',
      borderRadius: '0.25rem',
      fontSize: '0.65rem',
      fontWeight: 700,
      background: config.bg,
      color: config.color,
      letterSpacing: '0.05em',
    } as React.CSSProperties;
  },

  summaryGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(5, 1fr)',
    gap: '0.5rem',
    marginBottom: '1.5rem',
  } as React.CSSProperties,

  summaryItem: (color: string) => ({
    textAlign: 'center' as const,
    padding: '0.75rem 0.5rem',
    background: `${color}11`,
    borderRadius: '0.5rem',
    border: `1px solid ${color}33`,
  }) as React.CSSProperties,

  summaryCount: (color: string) => ({
    fontSize: '1.5rem',
    fontWeight: 700,
    color,
    lineHeight: 1,
  }) as React.CSSProperties,

  summaryLabel: {
    fontSize: '0.65rem',
    color: '#94a3b8',
    marginTop: '0.25rem',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.05em',
  } as React.CSSProperties,

  findingRow: {
    display: 'grid',
    gridTemplateColumns: '80px 1fr',
    gap: '1rem',
    padding: '0.85rem 1rem',
    borderBottom: '1px solid rgba(148, 163, 184, 0.08)',
    alignItems: 'start',
  } as React.CSSProperties,

  rawOutput: {
    background: 'rgba(15, 23, 42, 0.8)',
    borderRadius: '0.5rem',
    padding: '1rem',
    fontSize: '0.8rem',
    fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
    color: '#94a3b8',
    maxHeight: '300px',
    overflow: 'auto',
    whiteSpace: 'pre-wrap' as const,
    wordBreak: 'break-word' as const,
    border: '1px solid rgba(148, 163, 184, 0.1)',
  } as React.CSSProperties,

  emptyState: {
    textAlign: 'center' as const,
    padding: '3rem 1rem',
    color: '#64748b',
  } as React.CSSProperties,

  spinner: {
    display: 'inline-block',
    width: '1rem',
    height: '1rem',
    border: '2px solid rgba(255,255,255,0.3)',
    borderTop: '2px solid #fff',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  } as React.CSSProperties,
};

// ── Component ────────────────────────────────────────────────────────

const SecurityDashboard: React.FC = () => {
  // State
  const [targetMode, setTargetMode] = useState<'auto' | 'internal_api' | 'internal_web' | 'custom'>('auto');
  const [customTarget, setCustomTarget] = useState(() => getPublicApiBaseUrl());
  const [scanType, setScanType] = useState<ScanType>('full');
  const [description, setDescription] = useState('');
  const [isScanning, setIsScanning] = useState(false);
  const [scans, setScans] = useState<ScanListItem[]>([]);
  const [selectedScanId, setSelectedScanId] = useState<string | null>(null);
  const [report, setReport] = useState<ScanReportResponse | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const target: string =
    targetMode === 'auto'
      ? 'auto'
      : targetMode === 'internal_api'
        ? 'http://api:8000'
        : targetMode === 'internal_web'
          ? 'https://nginx'
          : customTarget;

  // ── Load Data ──────────────────────────────────────────────────────

  const loadScans = useCallback(async () => {
    try {
      const data = await listScans();
      setScans(data);
    } catch {
      console.warn('Failed to load scans');
    }
  }, []);

  const loadHealth = useCallback(async () => {
    try {
      const h = await checkHealth();
      setHealth(h);
    } catch {
      setHealth({ pentagi_reachable: false, pentagi_url: '', message: 'Unable to reach security service' });
    }
  }, []);

  useEffect(() => {
    const init = async () => {
      setLoading(true);
      await Promise.all([loadScans(), loadHealth()]);
      setLoading(false);
    };
    init();
    // Poll every 10s
    const interval = setInterval(loadScans, 10000);
    return () => clearInterval(interval);
  }, [loadScans, loadHealth]);

  // Live status polling for the selected scan
  useEffect(() => {
    if (!selectedScanId) return;

    let cancelled = false;
    const interval = setInterval(async () => {
      try {
        const status = await getScanStatus(selectedScanId);
        if (cancelled) return;

        setScans((prev) =>
          prev.map((s) => (s.scan_id === selectedScanId ? { ...s, status: status.status } : s)),
        );

        if (status.status === 'completed' && !report) {
          const r = await getScanReport(selectedScanId);
          if (cancelled) return;
          setReport(r);
          await loadScans();
        }
      } catch {
        // ignore polling errors; user can retry by re-selecting
      }
    }, 5000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [selectedScanId, report, loadScans]);

  // ── Start Scan ─────────────────────────────────────────────────────

  const handleStartScan = async () => {
    setError(null);
    setIsScanning(true);

    try {
      const result = await startScan({
        target,
        scan_type: scanType,
        description: description || undefined,
      });
      setSelectedScanId(result.scan_id);
      await loadScans();
    } catch (err: any) {
      setError(err?.message || 'Failed to start scan');
    } finally {
      setIsScanning(false);
    }
  };

  // ── Select Scan ────────────────────────────────────────────────────

  const handleSelectScan = async (scanId: string) => {
    setSelectedScanId(scanId);
    setReport(null);

    try {
      const r = await getScanReport(scanId);
      setReport(r);
    } catch (err) {
      console.warn('Failed to load report:', err);
    }
  };

  // ── Render ─────────────────────────────────────────────────────────

  return (
    <div style={styles.page}>
      {/* Spin keyframe */}
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>

      <div style={styles.container}>
        {/* Header */}
        <div style={styles.header}>
          <div>
            <h1 style={styles.title}>🛡️ Security Dashboard</h1>
            <p style={styles.subtitle}>AI-Powered Penetration Testing • PentAGI Integration</p>
          </div>
          <div style={styles.healthBadge(health?.pentagi_reachable ?? false)}>
            <span style={{ fontSize: '0.6rem' }}>{health?.pentagi_reachable ? '●' : '○'}</span>
            {health?.pentagi_reachable ? 'PentAGI Online' : 'PentAGI Offline'}
          </div>
        </div>

        {/* Main Grid */}
        <div style={styles.grid}>
          {/* Left Column — Scan Controls */}
          <div>
            {/* New Scan Form */}
            <div style={styles.card}>
              <div style={styles.cardTitle}>
                <span>🔍</span> New Scan
              </div>

              <div style={styles.formGroup}>
                <label style={styles.label}>Target URL</label>
                <select
                  style={styles.select}
                  value={targetMode}
                  onChange={(e) => setTargetMode(e.target.value as any)}
                >
                  <option value="auto">Auto-discover entire app</option>
                  <option value="internal_api">Internal API (http://api:8000)</option>
                  <option value="internal_web">Internal Web (https://nginx)</option>
                  <option value="custom">Custom</option>
                </select>
                {targetMode === 'custom' && (
                  <input
                    style={{ ...styles.input, marginTop: '0.75rem' }}
                    type="text"
                    value={customTarget}
                    onChange={(e) => setCustomTarget(e.target.value)}
                    placeholder="https://confit.app"
                  />
                )}
              </div>

              <div style={styles.formGroup}>
                <label style={styles.label}>Scan Type</label>
                <select
                  style={styles.select}
                  value={scanType}
                  onChange={(e) => setScanType(e.target.value as ScanType)}
                >
                  {Object.entries(SCAN_TYPE_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>{label}</option>
                  ))}
                </select>
              </div>

              <div style={styles.formGroup}>
                <label style={styles.label}>Description (optional)</label>
                <textarea
                  style={styles.textarea}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Additional context for the AI agent..."
                />
              </div>

              <button
                style={{
                  ...styles.button,
                  ...(isScanning ? styles.buttonDisabled : {}),
                }}
                onClick={handleStartScan}
                disabled={isScanning || !target}
              >
                {isScanning ? (
                  <>
                    <span style={styles.spinner} />
                    Starting Scan...
                  </>
                ) : (
                  '⚡ Launch Scan'
                )}
              </button>

              {error && (
                <div style={{
                  marginTop: '0.75rem',
                  padding: '0.75rem',
                  background: 'rgba(255, 23, 68, 0.1)',
                  border: '1px solid rgba(255, 23, 68, 0.3)',
                  borderRadius: '0.5rem',
                  color: '#ff1744',
                  fontSize: '0.8rem',
                }}>
                  {error}
                </div>
              )}
            </div>

            {/* Scan History */}
            <div style={{ ...styles.card, marginTop: '1rem' }}>
              <div style={styles.cardTitle}>
                <span>📋</span> Scan History
              </div>

              {loading ? (
                <div style={styles.emptyState}>
                  <span style={styles.spinner} />
                  <p style={{ marginTop: '0.5rem' }}>Loading...</p>
                </div>
              ) : scans.length === 0 ? (
                <div style={styles.emptyState}>
                  <p style={{ fontSize: '2rem', margin: 0 }}>🔒</p>
                  <p>No scans yet. Start your first security scan above.</p>
                </div>
              ) : (
                <div style={{ maxHeight: '400px', overflow: 'auto' }}>
                  {scans.map((scan) => (
                    <div
                      key={scan.scan_id}
                      style={{
                        ...styles.scanItem,
                        borderColor: selectedScanId === scan.scan_id
                          ? 'rgba(99, 102, 241, 0.5)'
                          : 'rgba(148, 163, 184, 0.08)',
                      }}
                      onClick={() => handleSelectScan(scan.scan_id)}
                    >
                      <div style={styles.scanItemHeader}>
                        <span style={{ fontSize: '0.8rem', fontWeight: 500, color: '#cbd5e1' }}>
                          {SCAN_TYPE_LABELS[scan.scan_type as ScanType] || scan.scan_type}
                        </span>
                        <span style={styles.statusBadge(scan.status)}>
                          {scan.status === 'running' && <span style={styles.spinner} />}
                          {STATUS_LABELS[scan.status]?.label || scan.status}
                        </span>
                      </div>
                      <div style={{ fontSize: '0.75rem', color: '#64748b', wordBreak: 'break-all' }}>
                        {scan.target}
                      </div>
                      <div style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        marginTop: '0.3rem',
                        fontSize: '0.7rem',
                        color: '#475569',
                      }}>
                        <span>{new Date(scan.created_at).toLocaleString()}</span>
                        {scan.findings_count > 0 && (
                          <span style={{ color: '#f59e0b' }}>
                            {scan.findings_count} findings
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Right Column — Report View */}
          <div>
            {report ? (
              <>
                {/* Summary Cards */}
                <div style={styles.card}>
                  <div style={styles.cardTitle}>
                    <span>📊</span> Findings Summary
                    <span style={{
                      ...styles.statusBadge(report.status),
                      marginLeft: 'auto',
                    }}>
                      {STATUS_LABELS[report.status]?.label || report.status}
                    </span>
                  </div>

                  <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '1rem' }}>
                    <strong>Target:</strong> {report.target} &nbsp;|&nbsp;
                    <strong>Type:</strong> {SCAN_TYPE_LABELS[report.scan_type as ScanType]}
                  </div>

                  <div style={styles.summaryGrid}>
                    {(['critical', 'high', 'medium', 'low', 'info'] as const).map((sev) => (
                      <div key={sev} style={styles.summaryItem(SEVERITY_CONFIG[sev].color)}>
                        <div style={styles.summaryCount(SEVERITY_CONFIG[sev].color)}>
                          {report.summary[sev]}
                        </div>
                        <div style={styles.summaryLabel}>{sev}</div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Findings Table */}
                <div style={{ ...styles.card, marginTop: '1rem' }}>
                  <div style={styles.cardTitle}>
                    <span>🐛</span> Vulnerabilities ({report.findings.length})
                  </div>

                  {report.findings.length === 0 ? (
                    <div style={styles.emptyState}>
                      <p style={{ fontSize: '2rem', margin: 0 }}>✅</p>
                      <p>No vulnerabilities found (yet). Scan may still be in progress.</p>
                    </div>
                  ) : (
                    <div style={{ maxHeight: '500px', overflow: 'auto' }}>
                      {report.findings.map((finding: SecurityFinding, idx: number) => (
                        <div key={idx} style={styles.findingRow}>
                          <div>
                            <span style={styles.severityBadge(finding.severity)}>
                              {SEVERITY_CONFIG[finding.severity]?.label || finding.severity}
                            </span>
                          </div>
                          <div>
                            <div style={{
                              fontWeight: 600,
                              fontSize: '0.85rem',
                              color: '#e2e8f0',
                              marginBottom: '0.25rem',
                            }}>
                              {finding.vulnerability}
                            </div>
                            <div style={{ fontSize: '0.8rem', color: '#94a3b8', lineHeight: 1.5 }}>
                              {finding.description.substring(0, 300)}
                              {finding.description.length > 300 && '...'}
                            </div>
                            {finding.remediation && (
                              <div style={{
                                marginTop: '0.4rem',
                                fontSize: '0.75rem',
                                color: '#22d3ee',
                              }}>
                                💡 {finding.remediation}
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Raw AI Output */}
                {report.raw_ai_output && (
                  <div style={{ ...styles.card, marginTop: '1rem' }}>
                    <div style={styles.cardTitle}>
                      <span>🤖</span> Raw AI Output
                    </div>
                    <div style={styles.rawOutput}>
                      {report.raw_ai_output}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div style={styles.card}>
                <div style={styles.emptyState}>
                  <p style={{ fontSize: '3rem', margin: 0 }}>🛡️</p>
                  <h3 style={{ color: '#cbd5e1', margin: '1rem 0 0.5rem' }}>
                    Select a Scan or Start a New One
                  </h3>
                  <p style={{ maxWidth: '400px', margin: '0 auto', lineHeight: 1.6 }}>
                    Launch an AI-powered penetration test against your application.
                    PentAGI will autonomously discover and test for OWASP Top 10 vulnerabilities.
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default SecurityDashboard;
