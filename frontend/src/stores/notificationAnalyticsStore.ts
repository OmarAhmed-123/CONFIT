/**
 * CONFIT — Notification Analytics Store
 * =======================================
 * Zustand store for notification analytics event logging,
 * metric aggregation, and cached KPI computation.
 *
 * Features:
 * - Hybrid mode: Uses API when authenticated, falls back to local computation
 * - Non-blocking event logging with backend sync
 * - Memoized aggregation with 5-minute TTL
 * - Real-time activity feed
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type {
  NotificationEvent,
  ChannelMetrics,
  AnalyticsKPI,
  DashboardPeriod,
  AnalyticsChannel,
  AnalyticsRecipientType,
  ActivityFeedItem,
  NotificationEventType,
  HeatmapCell,
  ConversionDataPoint,
  OwnerResponseTime,
  DailyTrend,
} from '@/types/notificationAnalyticsTypes';
import { periodToDays } from '@/types/notificationAnalyticsTypes';
import { notificationAnalyticsApi } from '@/services/notificationAnalyticsApi';
import { getAuthToken } from '@/lib/auth';

// ─── Cache ───

interface CacheEntry<T> {
  data: T;
  timestamp: number;
}

const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

function isCacheValid<T>(entry: CacheEntry<T> | null): entry is CacheEntry<T> {
  if (!entry) return false;
  return Date.now() - entry.timestamp < CACHE_TTL;
}

// ─── Aggregation Helpers ───

function computeChannelMetrics(
  events: NotificationEvent[],
  channel: AnalyticsChannel
): ChannelMetrics {
  const channelEvents = events.filter((e) => e.channel === channel);
  const sent = channelEvents.filter((e) => e.event_type === 'sent').length;
  const delivered = channelEvents.filter((e) => e.event_type === 'delivered').length;
  const opened = channelEvents.filter((e) => e.event_type === 'read').length;
  const clicked = channelEvents.filter((e) => e.event_type === 'clicked').length;

  // Estimate average latency from sent→delivered
  const sentMap = new Map<string, number>();
  channelEvents
    .filter((e) => e.event_type === 'sent')
    .forEach((e) => sentMap.set(e.notification_id, new Date(e.event_timestamp).getTime()));

  let totalLatency = 0;
  let latencyCount = 0;
  channelEvents
    .filter((e) => e.event_type === 'delivered')
    .forEach((e) => {
      const sentTime = sentMap.get(e.notification_id);
      if (sentTime) {
        totalLatency += new Date(e.event_timestamp).getTime() - sentTime;
        latencyCount++;
      }
    });

  return {
    channel,
    total_sent: sent,
    total_delivered: delivered,
    total_opened: opened,
    total_clicked: clicked,
    delivery_rate: sent > 0 ? parseFloat((delivered / sent).toFixed(3)) : 0,
    open_rate: delivered > 0 ? parseFloat((opened / delivered).toFixed(3)) : 0,
    click_through_rate: opened > 0 ? parseFloat((clicked / opened).toFixed(3)) : 0,
    avg_latency_ms: latencyCount > 0 ? Math.round(totalLatency / latencyCount) : 0,
  };
}

function computeKPIs(events: NotificationEvent[], period: DashboardPeriod): AnalyticsKPI {
  const days = periodToDays(period);
  const cutoff = Date.now() - days * 86400000;
  const periodEvents = events.filter(
    (e) => new Date(e.event_timestamp).getTime() >= cutoff
  );

  // Previous period for trend
  const prevCutoff = cutoff - days * 86400000;
  const prevEvents = events.filter((e) => {
    const t = new Date(e.event_timestamp).getTime();
    return t >= prevCutoff && t < cutoff;
  });

  const channels: AnalyticsChannel[] = ['in_app', 'email', 'push'];
  const metrics = channels.map((ch) => computeChannelMetrics(periodEvents, ch));
  const prevMetrics = channels.map((ch) => computeChannelMetrics(prevEvents, ch));

  const totalSent = metrics.reduce((s, m) => s + m.total_sent, 0);
  const totalDelivered = metrics.reduce((s, m) => s + m.total_delivered, 0);
  const totalOpened = metrics.reduce((s, m) => s + m.total_opened, 0);

  const overallDeliveryRate = totalSent > 0 ? totalDelivered / totalSent : 0;
  const avgOpenRate = totalDelivered > 0 ? totalOpened / totalDelivered : 0;

  const prevTotalSent = prevMetrics.reduce((s, m) => s + m.total_sent, 0);
  const prevTotalDelivered = prevMetrics.reduce((s, m) => s + m.total_delivered, 0);
  const prevTotalOpened = prevMetrics.reduce((s, m) => s + m.total_opened, 0);
  const prevDeliveryRate = prevTotalSent > 0 ? prevTotalDelivered / prevTotalSent : 0;
  const prevOpenRate = prevTotalDelivered > 0 ? prevTotalOpened / prevTotalDelivered : 0;

  // Most used channel
  const mostUsed = metrics.reduce((best, m) =>
    m.total_sent > best.total_sent ? m : best
  , metrics[0]);

  // Top conversion channel (use click-through as proxy)
  const topConversion = metrics.reduce((best, m) =>
    m.click_through_rate > best.click_through_rate ? m : best
  , metrics[0]);

  // Unique recipients
  const recipientSet = new Set(periodEvents.map((e) => e.recipient_id));

  return {
    overall_delivery_rate: parseFloat(overallDeliveryRate.toFixed(3)),
    avg_open_rate: parseFloat(avgOpenRate.toFixed(3)),
    avg_click_rate: parseFloat((metrics.reduce((s, m) => s + m.total_clicked, 0) / totalOpened || 0).toFixed(3)),
    most_used_channel: mostUsed.channel,
    most_used_channel_count: mostUsed.total_sent,
    top_conversion_channel: topConversion.channel,
    top_conversion_rate: topConversion.click_through_rate,
    total_events: totalSent,
    period_days: days,
    delivery_rate_trend: parseFloat((overallDeliveryRate - prevDeliveryRate).toFixed(3)),
    open_rate_trend: parseFloat((avgOpenRate - prevOpenRate).toFixed(3)),
  };
}

// ─── Store ───

interface NotificationAnalyticsState {
  events: NotificationEvent[];
  initialized: boolean;
  
  // API data (when authenticated)
  apiData: {
    kpis: AnalyticsKPI | null;
    channelMetrics: ChannelMetrics[];
    heatmap: HeatmapCell[];
    conversions: ConversionDataPoint[];
    ownerResponseTimes: OwnerResponseTime[];
    dailyTrend: DailyTrend[];
    activityFeed: ActivityFeedItem[];
  } | null;
  
  // Loading states
  isLoading: boolean;
  lastFetch: number | null;
  error: string | null;

  // Actions
  initialize: () => Promise<void>;
  logEvent: (event: NotificationEvent) => void;
  refresh: (period?: DashboardPeriod) => Promise<void>;

  // Selectors (with caching)
  _kpiCache: Record<string, CacheEntry<AnalyticsKPI>>;
  _channelCache: Record<string, CacheEntry<ChannelMetrics[]>>;

  getKPIs: (period: DashboardPeriod) => AnalyticsKPI;
  getChannelMetrics: (period: DashboardPeriod) => ChannelMetrics[];
  getFilteredEvents: (period: DashboardPeriod, filters?: {
    channel?: AnalyticsChannel;
    recipient_type?: AnalyticsRecipientType;
    event_type?: NotificationEventType;
  }) => NotificationEvent[];
  getRecentActivity: (limit?: number) => ActivityFeedItem[];
  getDailyTrend: (period: DashboardPeriod, channel: AnalyticsChannel) => DailyTrend[];
  getHeatmap: (period: DashboardPeriod) => HeatmapCell[];
  getConversions: () => ConversionDataPoint[];
  getOwnerResponseTimes: () => OwnerResponseTime[];
}

export const useNotificationAnalyticsStore = create<NotificationAnalyticsState>()(
  persist(
    (set, get) => ({
      events: [],
      initialized: false,
      apiData: null,
      isLoading: false,
      lastFetch: null,
      error: null,
      _kpiCache: {},
      _channelCache: {},

      initialize: async () => {
        if (get().initialized) return;
        set({ initialized: true });
        
        // Fetch from API if authenticated
        if (getAuthToken()) {
          await get().refresh('30d');
        }
      },

      refresh: async (period: DashboardPeriod = '30d') => {
        if (!getAuthToken()) return; // Skip if not authenticated
        
        set({ isLoading: true, error: null });
        
        try {
          const days = periodToDays(period);
          
          const [kpis, channelMetrics, heatmap, conversions, ownerResponseTimes, dailyTrend, activityFeed] = 
            await Promise.all([
              notificationAnalyticsApi.getKPIs({ period: days }),
              notificationAnalyticsApi.getChannelMetrics({ period: days }),
              notificationAnalyticsApi.getHeatmap({ period: days }),
              notificationAnalyticsApi.getConversions(),
              notificationAnalyticsApi.getOwnerResponseTimes({ period: days }),
              notificationAnalyticsApi.getDailyTrend({ period: days }),
              notificationAnalyticsApi.getActivityFeed({ limit: 100 }),
            ]);
          
          set({
            apiData: {
              kpis,
              channelMetrics,
              heatmap,
              conversions,
              ownerResponseTimes,
              dailyTrend,
              activityFeed,
            },
            isLoading: false,
            lastFetch: Date.now(),
          });
        } catch (err) {
          set({ 
            error: err instanceof Error ? err.message : 'Failed to fetch analytics',
            isLoading: false 
          });
        }
      },

      logEvent: (event) => {
        // Non-blocking append to local store
        setTimeout(() => {
          set((state) => {
            if (state.events.some((e) => e.id === event.id)) return state;
            return {
              events: [event, ...state.events],
              _kpiCache: {},     // Invalidate caches
              _channelCache: {},
            };
          });
        }, 0);
        
        // Also send to API if authenticated
        if (getAuthToken()) {
          notificationAnalyticsApi.logEvent({
            notification_id: event.notification_id,
            recipient_id: event.recipient_id,
            recipient_type: event.recipient_type,
            channel: event.channel,
            event_type: event.event_type,
            payload: event.payload,
            time_spent_ms: event.engagement?.time_spent_ms,
            scroll_depth: event.engagement?.scroll_depth,
            action_taken: event.engagement?.action_taken,
          });
        }
      },

      getKPIs: (period) => {
        const state = get();
        const cached = state._kpiCache[period];
        if (isCacheValid(cached)) return cached.data;

        return computeKPIs(state.events, period);
      },

      getChannelMetrics: (period) => {
        const state = get();
        const cached = state._channelCache[period];
        if (isCacheValid(cached)) return cached.data;

        const days = periodToDays(period);
        const cutoff = Date.now() - days * 86400000;
        const periodEvents = state.events.filter(
          (e) => new Date(e.event_timestamp).getTime() >= cutoff
        );

        const channels: AnalyticsChannel[] = ['in_app', 'email', 'push'];
        return channels.map((ch) => computeChannelMetrics(periodEvents, ch));
      },

      getFilteredEvents: (period, filters) => {
        const days = periodToDays(period);
        const cutoff = Date.now() - days * 86400000;
        let result = get().events.filter(
          (e) => new Date(e.event_timestamp).getTime() >= cutoff
        );
        if (filters?.channel) result = result.filter((e) => e.channel === filters.channel);
        if (filters?.recipient_type) result = result.filter((e) => e.recipient_type === filters.recipient_type);
        if (filters?.event_type) result = result.filter((e) => e.event_type === filters.event_type);
        return result;
      },

      getRecentActivity: (limit = 100) => {
        const state = get();

        const NOTIF_TITLES: Record<string, string> = {
          order_confirmed: 'Order Confirmed',
          order_placed: 'New Order Placed',
          order_shipped: 'Order Shipped',
          promotion: 'Flash Sale Alert',
          price_drop: 'Price Drop Alert',
          styling_suggestion: 'Style Recommendation',
        };

        return state.events.slice(0, limit).map((e) => ({
          id: e.id,
          event_type: e.event_type,
          channel: e.channel,
          recipient_type: e.recipient_type,
          recipient_id: e.recipient_id,
          notification_title: NOTIF_TITLES[e.payload.notification_type || ''] || 'Notification',
          timestamp: e.event_timestamp,
        }));
      },

      getDailyTrend: (period, channel) => {
        const days = periodToDays(period);
        const result: Array<{
          date: string;
          delivery_rate: number;
          open_rate: number;
          click_rate: number;
          count: number;
        }> = [];

        for (let d = days - 1; d >= 0; d--) {
          const dayStart = new Date();
          dayStart.setDate(dayStart.getDate() - d);
          dayStart.setHours(0, 0, 0, 0);
          const dayEnd = new Date(dayStart);
          dayEnd.setDate(dayEnd.getDate() + 1);

          const dayEvents = get().events.filter((e) => {
            const t = new Date(e.event_timestamp).getTime();
            return e.channel === channel && t >= dayStart.getTime() && t < dayEnd.getTime();
          });

          const sent = dayEvents.filter((e) => e.event_type === 'sent').length;
          const delivered = dayEvents.filter((e) => e.event_type === 'delivered').length;
          const read = dayEvents.filter((e) => e.event_type === 'read').length;
          const clicked = dayEvents.filter((e) => e.event_type === 'clicked').length;

          result.push({
            date: dayStart.toISOString().split('T')[0],
            delivery_rate: sent > 0 ? parseFloat((delivered / sent).toFixed(3)) : 0,
            open_rate: delivered > 0 ? parseFloat((read / delivered).toFixed(3)) : 0,
            click_rate: read > 0 ? parseFloat((clicked / read).toFixed(3)) : 0,
            count: sent,
          });
        }

        return result;
      },

      getHeatmap: (period) => {
        const state = get();
        // Return API data if available
        if (state.apiData?.heatmap) {
          return state.apiData.heatmap;
        }
        
        // Fallback to local computation
        const days = periodToDays(period);
        const cutoff = Date.now() - days * 86400000;
        const periodEvents = state.events.filter(
          (e) => new Date(e.event_timestamp).getTime() >= cutoff
        );
        
        const heatmap: HeatmapCell[] = [];
        for (let day = 0; day < 7; day++) {
          for (let hour = 0; hour < 24; hour++) {
            const dayEvents = periodEvents.filter((e) => {
              const d = new Date(e.event_timestamp);
              return d.getDay() === day && d.getHours() === hour;
            });
            
            const sent = dayEvents.filter((e) => e.event_type === 'sent').length;
            const read = dayEvents.filter((e) => e.event_type === 'read').length;
            const clicked = dayEvents.filter((e) => e.event_type === 'clicked').length;
            
            heatmap.push({
              day,
              hour,
              open_rate: sent > 0 ? read / sent : 0,
              click_rate: sent > 0 ? clicked / sent : 0,
              event_count: sent,
            });
          }
        }
        
        return heatmap;
      },

      getConversions: () => {
        const state = get();
        // Return API data if available
        if (state.apiData?.conversions) {
          return state.apiData.conversions;
        }
        return [];
      },

      getOwnerResponseTimes: () => {
        const state = get();
        // Return API data if available
        if (state.apiData?.ownerResponseTimes) {
          return state.apiData.ownerResponseTimes;
        }
        return [];
      },
    }),
    {
      name: 'confit-notification-analytics',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        events: state.events.slice(0, 500), // Cap persisted events
        initialized: state.initialized,
      }),
    }
  )
);
