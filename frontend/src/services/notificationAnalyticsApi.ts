/**
 * CONFIT — Notification Analytics API Service
 * ============================================
 * Frontend service layer for fetching analytics data from the backend.
 * Provides typed API calls with caching and error handling.
 */

import { api } from '@/lib/api/client';
import type {
  AnalyticsKPI,
  ChannelMetrics,
  HeatmapCell,
  ConversionDataPoint,
  OwnerResponseTime,
  CohortComparison,
  DailyTrend,
  ActivityFeedItem,
  ABTest,
  AnalyticsChannel,
  AnalyticsRecipientType,
  NotificationEventType,
  DashboardPeriod,
} from '@/types/notificationAnalyticsTypes';

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

export interface AnalyticsQueryParams {
  period?: DashboardPeriod | number;
  recipient_type?: AnalyticsRecipientType;
  channel?: AnalyticsChannel;
  [key: string]: unknown;
}

export interface LogEventRequest {
  notification_id: string;
  recipient_id: string;
  recipient_type: AnalyticsRecipientType;
  channel: AnalyticsChannel;
  event_type: NotificationEventType;
  payload?: Record<string, unknown>;
  time_spent_ms?: number;
  scroll_depth?: number;
  action_taken?: string;
  ab_test_id?: string;
  variant_id?: string;
}

export interface CreateABTestRequest {
  name: string;
  hypothesis: string;
  variable: 'timing' | 'content' | 'channel' | 'frequency';
  segment: 'all_customers' | 'all_owners' | 'new_customers' | 'repeat_customers' | 'specific_stores';
  traffic_percentage: number;
  duration_days: number;
  variants: Array<{ name: string; description?: string }>;
}

// ─────────────────────────────────────────────────────────────────────────────
// Cache Configuration
// ─────────────────────────────────────────────────────────────────────────────

const CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes

interface CacheEntry<T> {
  data: T;
  timestamp: number;
  params: string;
}

const cache = new Map<string, CacheEntry<unknown>>();

function getCacheKey(endpoint: string, params?: Record<string, unknown>): string {
  const paramStr = params ? JSON.stringify(params) : '';
  return `${endpoint}:${paramStr}`;
}

function getCached<T>(key: string): T | null {
  const entry = cache.get(key) as CacheEntry<T> | undefined;
  if (!entry) return null;
  
  const age = Date.now() - entry.timestamp;
  if (age > CACHE_TTL_MS) {
    cache.delete(key);
    return null;
  }
  
  return entry.data;
}

function setCache<T>(key: string, data: T): void {
  cache.set(key, {
    data,
    timestamp: Date.now(),
    params: key,
  });
}

function invalidateCache(pattern?: string): void {
  if (!pattern) {
    cache.clear();
    return;
  }
  
  for (const key of cache.keys()) {
    if (key.startsWith(pattern)) {
      cache.delete(key);
    }
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// API Service
// ─────────────────────────────────────────────────────────────────────────────

export const notificationAnalyticsApi = {
  // ── KPIs ───────────────────────────────────────────────────────────────────

  /**
   * Get KPI summary for the executive summary section.
   */
  async getKPIs(params: AnalyticsQueryParams = {}): Promise<AnalyticsKPI> {
    const key = getCacheKey('/analytics/notifications/kpis', params);
    const cached = getCached<AnalyticsKPI>(key);
    if (cached) return cached;

    const response = await api.get<AnalyticsKPI>('/analytics/notifications/kpis', {
      period: params.period || 30,
      recipient_type: params.recipient_type,
    });

    setCache(key, response);
    return response;
  },

  // ── Channel Metrics ────────────────────────────────────────────────────────

  /**
   * Get metrics by channel for comparison charts.
   */
  async getChannelMetrics(params: AnalyticsQueryParams = {}): Promise<ChannelMetrics[]> {
    const key = getCacheKey('/analytics/notifications/channels', params);
    const cached = getCached<ChannelMetrics[]>(key);
    if (cached) return cached;

    const response = await api.get<ChannelMetrics[]>('/analytics/notifications/channels', {
      period: params.period || 30,
      recipient_type: params.recipient_type,
    });

    setCache(key, response);
    return response;
  },

  // ── Heatmap ─────────────────────────────────────────────────────────────────

  /**
   * Get engagement heatmap data (day × hour).
   */
  async getHeatmap(params: AnalyticsQueryParams = {}): Promise<HeatmapCell[]> {
    const key = getCacheKey('/analytics/notifications/heatmap', params);
    const cached = getCached<HeatmapCell[]>(key);
    if (cached) return cached;

    const response = await api.get<HeatmapCell[]>('/analytics/notifications/heatmap', {
      period: params.period || 30,
      recipient_type: params.recipient_type,
    });

    setCache(key, response);
    return response;
  },

  // ── Conversions ─────────────────────────────────────────────────────────────

  /**
   * Get conversion data by channel.
   */
  async getConversions(): Promise<ConversionDataPoint[]> {
    const key = getCacheKey('/analytics/notifications/conversions');
    const cached = getCached<ConversionDataPoint[]>(key);
    if (cached) return cached;

    const response = await api.get<ConversionDataPoint[]>('/analytics/notifications/conversions');
    setCache(key, response);
    return response;
  },

  // ── Owner Response Times ───────────────────────────────────────────────────

  /**
   * Get owner response times by store.
   */
  async getOwnerResponseTimes(params: AnalyticsQueryParams = {}): Promise<OwnerResponseTime[]> {
    const key = getCacheKey('/analytics/notifications/owner-response-times', params);
    const cached = getCached<OwnerResponseTime[]>(key);
    if (cached) return cached;

    const response = await api.get<OwnerResponseTime[]>('/analytics/notifications/owner-response-times', {
      period: params.period || 30,
    });

    setCache(key, response);
    return response;
  },

  // ── Daily Trend ─────────────────────────────────────────────────────────────

  /**
   * Get daily metrics trend.
   */
  async getDailyTrend(params: AnalyticsQueryParams = {}): Promise<DailyTrend[]> {
    const key = getCacheKey('/analytics/notifications/daily-trend', params);
    const cached = getCached<DailyTrend[]>(key);
    if (cached) return cached;

    const response = await api.get<DailyTrend[]>('/analytics/notifications/daily-trend', {
      period: params.period || 30,
      recipient_type: params.recipient_type,
    });

    setCache(key, response);
    return response;
  },

  // ── Activity Feed ───────────────────────────────────────────────────────────

  /**
   * Get recent activity feed items.
   */
  async getActivityFeed(params: {
    limit?: number;
    channel?: AnalyticsChannel;
    recipient_type?: AnalyticsRecipientType;
  } = {}): Promise<ActivityFeedItem[]> {
    // No caching for real-time feed
    const response = await api.get<ActivityFeedItem[]>('/analytics/notifications/activity', {
      limit: params.limit || 50,
      channel: params.channel,
      recipient_type: params.recipient_type,
    });

    return response;
  },

  // ── A/B Tests ───────────────────────────────────────────────────────────────

  /**
   * Get all A/B tests.
   */
  async getABTests(params: { status?: string } = {}): Promise<ABTest[]> {
    const key = getCacheKey('/analytics/notifications/ab-tests', params);
    const cached = getCached<ABTest[]>(key);
    if (cached) return cached;

    const response = await api.get<ABTest[]>('/analytics/notifications/ab-tests', {
      status: params.status,
    });

    setCache(key, response);
    return response;
  },

  /**
   * Create a new A/B test.
   */
  async createABTest(request: CreateABTestRequest): Promise<ABTest> {
    invalidateCache('/analytics/notifications/ab-tests');
    return api.post<ABTest>('/analytics/notifications/ab-tests', request);
  },

  /**
   * Start an A/B test.
   */
  async startABTest(testId: string): Promise<{ status: string; started_at: string }> {
    invalidateCache('/analytics/notifications/ab-tests');
    return api.post<{ status: string; started_at: string }>(
      `/analytics/notifications/ab-tests/${testId}/start`
    );
  },

  /**
   * Pause an A/B test.
   */
  async pauseABTest(testId: string): Promise<{ status: string }> {
    invalidateCache('/analytics/notifications/ab-tests');
    return api.post<{ status: string }>(
      `/analytics/notifications/ab-tests/${testId}/pause`
    );
  },

  /**
   * Complete an A/B test.
   */
  async completeABTest(testId: string): Promise<{ status: string; completed_at: string }> {
    invalidateCache('/analytics/notifications/ab-tests');
    return api.post<{ status: string; completed_at: string }>(
      `/analytics/notifications/ab-tests/${testId}/complete`
    );
  },

  // ── Event Logging ───────────────────────────────────────────────────────────

  /**
   * Log a notification event (non-blocking).
   */
  logEvent(request: LogEventRequest): void {
    // Fire and forget - use setTimeout to make it non-blocking
    setTimeout(() => {
      api.post('/analytics/notifications/events', request).catch((err) => {
        // Silent - analytics must never break dispatch
        console.warn('[AnalyticsAPI] Event logging failed:', err);
      });
    }, 0);
  },

  /**
   * Log a notification event (awaitable version for critical events).
   */
  async logEventAsync(request: LogEventRequest): Promise<void> {
    await api.post('/analytics/notifications/events', request);
  },

  // ── Export ──────────────────────────────────────────────────────────────────

  /**
   * Export analytics data as CSV.
   */
  async exportCSV(params: AnalyticsQueryParams = {}): Promise<Blob> {
    const baseUrl =
      process.env.NODE_ENV === 'development' ? '' : (process.env.NEXT_PUBLIC_API_BASE_URL || '');
    const url = new URL(`${baseUrl || window.location.origin}/api/analytics/notifications/export/csv`);
    
    if (params.period) url.searchParams.set('period', String(params.period));
    if (params.recipient_type) url.searchParams.set('recipient_type', params.recipient_type);

    const token = localStorage.getItem('confit_access_token');
    const response = await fetch(url.toString(), {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });

    if (!response.ok) {
      throw new Error(`Export failed: ${response.status}`);
    }

    return response.blob();
  },

  /**
   * Download CSV file.
   */
  async downloadCSV(params: AnalyticsQueryParams = {}): Promise<void> {
    const blob = await this.exportCSV(params);
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `notification_analytics_${params.period || 30}d.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  },

  // ── Cache Management ───────────────────────────────────────────────────────

  /**
   * Invalidate all cached analytics data.
   */
  invalidateAllCache(): void {
    invalidateCache();
  },

  /**
   * Invalidate cache for a specific endpoint pattern.
   */
  invalidateCacheFor(pattern: string): void {
    invalidateCache(pattern);
  },
};

export default notificationAnalyticsApi;
