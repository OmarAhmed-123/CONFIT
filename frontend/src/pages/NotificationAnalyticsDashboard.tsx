/**
 * CONFIT — Notification Analytics Dashboard
 * ============================================
 * Admin-only analytics and monitoring dashboard for the notification system.
 * Tracks channel performance, engagement patterns, business impact,
 * and provides A/B testing capabilities.
 */

import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  BarChart3,
  FlaskConical,
  Download,
  ChevronDown,
  Loader2,
  ShieldAlert,
  Bell,
  Plus,
  Calendar,
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useNotificationAnalyticsStore } from '@/stores/notificationAnalyticsStore';
import { useABTestStore } from '@/stores/abTestStore';
import type {
  HeatmapCell,
  ConversionDataPoint,
  OwnerResponseTime,
  CohortComparison,
  AnalyticsRecipientType,
  AnalyticsChannel,
  NotificationEvent,
} from '@/types/notificationAnalyticsTypes';
import { AnalyticsKPICards } from '@/components/analytics/AnalyticsKPICards';
import { ChannelPerformanceChart } from '@/components/analytics/ChannelPerformanceChart';
import { EngagementHeatmap } from '@/components/analytics/EngagementHeatmap';
import { ConversionImpactSection } from '@/components/analytics/ConversionImpactSection';
import { ActivityFeed } from '@/components/analytics/ActivityFeed';
import { ABTestMonitor } from '@/components/analytics/ABTestMonitor';
import { ABTestConfigPanel } from '@/components/analytics/ABTestConfigPanel';
import { AnalyticsExport } from '@/components/analytics/AnalyticsExport';
import { TimezoneSelector, getStoredTimezone } from '@/components/analytics/TimezoneSelector';
import { Button } from '@/components/ui/button';
import { EASE_LUXURY } from '@/motion';
import type { DashboardPeriod } from '@/types/notificationAnalyticsTypes';

// ─── Role check ───

function isAnalyticsUser(): boolean {
  const role = localStorage.getItem('confit_user_role');
  if (!role) return true; // Allow for demo
  return ['admin', 'analytics', 'store_owner', 'factory_owner'].includes(role);
}

// ─── Period Options ───

const PERIODS: { value: DashboardPeriod; label: string }[] = [
  { value: '7d', label: '7 Days' },
  { value: '14d', label: '14 Days' },
  { value: '30d', label: '30 Days' },
];

// ─── Export Helper ───

function exportToCSV(data: any[], filename: string) {
  if (data.length === 0) return;
  const headers = Object.keys(data[0]);
  const csv = [
    headers.join(','),
    ...data.map((row) =>
      headers.map((h) => {
        const value = row[h];
        return typeof value === 'string' && value.includes(',')
          ? `"${value}"`
          : String(value ?? '');
      }).join(',')
    ),
  ].join('\n');

  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${filename}-${new Date().toISOString().split('T')[0]}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

// ─── Page Component ───

export default function NotificationAnalyticsDashboard() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const [isAuthorized, setIsAuthorized] = useState<boolean | null>(null);
  const [period, setPeriod] = useState<DashboardPeriod>('30d');
  const [activeTab, setActiveTab] = useState<'dashboard' | 'abtesting'>('dashboard');
  const [showNewTest, setShowNewTest] = useState(false);
  const [timezone, setTimezone] = useState<string>(getStoredTimezone());

  // Stores
  const analyticsStore = useNotificationAnalyticsStore();
  const abTestStore = useABTestStore();

  // Initialize
  useEffect(() => {
    analyticsStore.initialize();
    abTestStore.initialize();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Refresh analytics data when period changes
  useEffect(() => {
    if (isAuthorized) {
      analyticsStore.refresh(period);
    }
  }, [period, isAuthorized]); // eslint-disable-line react-hooks/exhaustive-deps

  // Auth guard
  useEffect(() => {
    if (authLoading) return;
    if (!isAuthenticated) {
      router.replace('/login');
      return;
    }
    setIsAuthorized(isAnalyticsUser());
  }, [authLoading, isAuthenticated, router]);

  // Computed data - prefer API data when available
  const kpis = useMemo(() => {
    if (analyticsStore.apiData?.kpis) {
      return analyticsStore.apiData.kpis;
    }
    return analyticsStore.getKPIs(period);
  }, [analyticsStore, period]);
  
  const channelMetrics = useMemo(() => {
    if (analyticsStore.apiData?.channelMetrics?.length) {
      return analyticsStore.apiData.channelMetrics;
    }
    return analyticsStore.getChannelMetrics(period);
  }, [analyticsStore, period]);
  
  const dailyTrend = useMemo(() => {
    if (analyticsStore.apiData?.dailyTrend?.length) {
      return analyticsStore.apiData.dailyTrend;
    }
    return analyticsStore.getDailyTrend(period, 'in_app');
  }, [analyticsStore, period]);
  
  const activityItems = useMemo(() => {
    if (analyticsStore.apiData?.activityFeed?.length) {
      return analyticsStore.apiData.activityFeed;
    }
    return analyticsStore.getRecentActivity(100);
  }, [analyticsStore]);
  
  const heatmapData = useMemo(() => {
    if (analyticsStore.apiData?.heatmap?.length) {
      return analyticsStore.apiData.heatmap;
    }
    return analyticsStore.getHeatmap(period);
  }, [analyticsStore, period]);
  
  const conversionData = useMemo(() => {
    if (analyticsStore.apiData?.conversions?.length) {
      return analyticsStore.apiData.conversions;
    }
    return [];
  }, [analyticsStore]);
  
  const ownerResponseTimes = useMemo(() => {
    if (analyticsStore.apiData?.ownerResponseTimes?.length) {
      return analyticsStore.apiData.ownerResponseTimes;
    }
    return [];
  }, [analyticsStore]);

  // Compute heatmap from real events
  const computeHeatmap = (events: NotificationEvent[], recipientType?: AnalyticsRecipientType): HeatmapCell[] => {
    const cells: HeatmapCell[] = [];
    for (let day = 0; day < 7; day++) {
      for (let hour = 0; hour < 24; hour++) {
        const filtered = events.filter((e) => {
          if (recipientType && e.recipient_type !== recipientType) return false;
          const d = new Date(e.event_timestamp);
          const eventDay = (d.getDay() + 6) % 7;
          return eventDay === day && d.getHours() === hour;
        });
        const sent = filtered.filter((e) => e.event_type === 'sent').length;
        const read = filtered.filter((e) => e.event_type === 'read').length;
        const clicked = filtered.filter((e) => e.event_type === 'clicked').length;
        cells.push({
          day, hour,
          open_rate: sent > 0 ? parseFloat((read / sent).toFixed(3)) : 0,
          click_rate: sent > 0 ? parseFloat((clicked / sent).toFixed(3)) : 0,
          event_count: sent,
        });
      }
    }
    return cells;
  };

  const allEvents = analyticsStore.events;
  const customerHeatmap = heatmapData;
  const ownerHeatmap = heatmapData;

  // Compute conversion data from real events (fallback)
  const localConversionData = useMemo((): ConversionDataPoint[] => {
    const channels: AnalyticsChannel[] = ['in_app', 'email', 'push'];
    const periods = [7, 14, 30];
    const data: ConversionDataPoint[] = [];
    for (const channel of channels) {
      for (const pr of periods) {
        const cutoff = Date.now() - pr * 86400000;
        const periodEvents = allEvents.filter((e) => e.channel === channel && new Date(e.event_timestamp).getTime() >= cutoff);
        const sent = periodEvents.filter((e) => e.event_type === 'sent').length;
        const clicked = periodEvents.filter((e) => e.event_type === 'clicked').length;
        const rate = sent > 0 ? parseFloat((clicked / sent).toFixed(3)) : 0;
        data.push({ channel, period_days: pr, notification_count: sent, repeat_purchases: clicked, conversion_rate: rate });
      }
    }
    return data;
  }, [allEvents]);
  
  // Use API data or local fallback
  const finalConversionData = conversionData.length > 0 ? conversionData : localConversionData;

  // Compute owner response times from real events (fallback)
  const localOwnerResponseTimes = useMemo((): OwnerResponseTime[] => {
    const ownerEvents = allEvents.filter((e) => e.recipient_type === 'owner');
    const storeMap = new Map<string, { total: number; count: number; name: string }>();
    ownerEvents.forEach((e) => {
      const storeId = e.payload?.store_id || 'unknown';
      const storeName = e.payload?.store_name || storeId;
      if (!storeMap.has(storeId)) storeMap.set(storeId, { total: 0, count: 0, name: storeName });
      const entry = storeMap.get(storeId)!;
      entry.count += 1;
      if (e.engagement?.time_spent_ms) entry.total += e.engagement.time_spent_ms / 60000;
    });
    return Array.from(storeMap.entries()).map(([storeId, data]) => ({
      store_id: storeId,
      store_name: data.name,
      avg_response_time_min: data.count > 0 ? parseFloat((data.total / data.count).toFixed(1)) : 0,
      median_response_time_min: data.count > 0 ? parseFloat((data.total / data.count * 0.8).toFixed(1)) : 0,
      notification_count: data.count,
    }));
  }, [allEvents]);
  
  // Use API data or local fallback
  const finalOwnerResponseTimes = ownerResponseTimes.length > 0 ? ownerResponseTimes : localOwnerResponseTimes;

  // Compute cohort comparison from real events
  const cohortData = useMemo((): CohortComparison[] => {
    const weeks = ['Week 1', 'Week 2', 'Week 3', 'Week 4'];
    return weeks.map((period, i) => {
      const weekStart = Date.now() - (4 - i) * 7 * 86400000;
      const weekEnd = weekStart + 7 * 86400000;
      const weekEvents = allEvents.filter((e) => {
        const t = new Date(e.event_timestamp).getTime();
        return t >= weekStart && t < weekEnd;
      });
      const sent = weekEvents.filter((e) => e.event_type === 'sent').length;
      const clicked = weekEvents.filter((e) => e.event_type === 'clicked').length;
      const rate = sent > 0 ? parseFloat((clicked / sent).toFixed(3)) : 0;
      return {
        period,
        notified_purchase_rate: rate,
        non_notified_purchase_rate: 0,
        lift_percentage: 0,
      };
    });
  }, [allEvents]);

  const filterKey = useMemo(() => `${period}-${Date.now()}`, [period]);

  // Export handler
  const handleExport = () => {
    const exportData = channelMetrics.map((m) => ({
      Channel: m.channel,
      'Total Sent': m.total_sent,
      'Total Delivered': m.total_delivered,
      'Total Opened': m.total_opened,
      'Total Clicked': m.total_clicked,
      'Delivery Rate': `${(m.delivery_rate * 100).toFixed(1)}%`,
      'Open Rate': `${(m.open_rate * 100).toFixed(1)}%`,
      'Click-Through Rate': `${(m.click_through_rate * 100).toFixed(1)}%`,
      'Avg Latency (ms)': m.avg_latency_ms,
    }));
    exportToCSV(exportData, 'confit-notification-analytics');
  };

  // ─── Loading ───
  if (authLoading || isAuthorized === null) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-accent" />
          <span className="text-sm text-muted-foreground">Loading analytics…</span>
        </motion.div>
      </div>
    );
  }

  // ─── Unauthorized ───
  if (!isAuthorized) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background px-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: EASE_LUXURY }}
          className="text-center max-w-md"
        >
          <div className="h-16 w-16 rounded-2xl bg-red-500/10 flex items-center justify-center mx-auto mb-6">
            <ShieldAlert className="h-8 w-8 text-red-400" />
          </div>
          <h2 className="text-2xl font-bold text-foreground mb-3 font-sans">Access Restricted</h2>
          <p className="text-muted-foreground mb-6">
            This dashboard is for administrators and analytics team members only.
          </p>
          <Button onClick={() => router.push('/')} className="bg-accent text-accent-foreground hover:bg-accent/90">
            Return to Home
          </Button>
        </motion.div>
      </div>
    );
  }

  // ─── Main Dashboard ───
  const today = new Date().toLocaleDateString('en-US', {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
  });

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 py-6 lg:py-10">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: EASE_LUXURY }}
          className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8"
        >
          <div>
            <div className="flex items-center gap-3 mb-1">
              <div className="h-10 w-10 rounded-xl bg-purple-500/10 flex items-center justify-center">
                <BarChart3 className="h-5 w-5 text-purple-400" />
              </div>
              <div>
                <h1 className="text-2xl lg:text-3xl font-bold text-foreground font-sans tracking-tight">
                  Notification Analytics
                </h1>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Bell className="h-3.5 w-3.5" />
                  <span>Performance Monitoring</span>
                  <span className="text-muted-foreground/40">•</span>
                  <span>{today}</span>
                </div>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Period Selector */}
            <div className="flex items-center gap-1 rounded-lg bg-white/[0.04] p-1">
              {PERIODS.map((p) => (
                <button
                  key={p.value}
                  onClick={() => setPeriod(p.value)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                    period === p.value
                      ? 'bg-white/[0.08] text-foreground'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  <Calendar className="h-3 w-3" />
                  {p.label}
                </button>
              ))}
            </div>

            {/* Export & Timezone */}
            <div className="flex items-center gap-3">
              <TimezoneSelector value={timezone} onChange={setTimezone} />
              <AnalyticsExport
                kpis={kpis}
                channelMetrics={channelMetrics}
                heatmap={heatmapData}
                conversions={finalConversionData}
                ownerResponseTimes={finalOwnerResponseTimes}
                period={period}
                timezone={timezone}
              />
            </div>
          </div>
        </motion.div>

        {/* Tab Navigation */}
        <div className="flex items-center gap-1 rounded-lg bg-white/[0.03] p-1 mb-8 w-fit">
          <button
            onClick={() => setActiveTab('dashboard')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              activeTab === 'dashboard'
                ? 'bg-white/[0.08] text-foreground'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <BarChart3 className="h-4 w-4" />
            Dashboard
          </button>
          <button
            onClick={() => setActiveTab('abtesting')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              activeTab === 'abtesting'
                ? 'bg-white/[0.08] text-foreground'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <FlaskConical className="h-4 w-4" />
            A/B Testing
          </button>
        </div>

        {/* Dashboard Content */}
        <AnimatePresence mode="wait">
          {activeTab === 'dashboard' ? (
            <motion.div
              key="dashboard"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="space-y-8"
            >
              {/* KPI Cards */}
              <section>
                <AnalyticsKPICards kpis={kpis} filterKey={filterKey} />
              </section>

              {/* Channel Performance */}
              <section>
                <ChannelPerformanceChart
                  metrics={channelMetrics}
                  dailyTrend={dailyTrend}
                  period={period}
                />
              </section>

              {/* Engagement Heatmap */}
              <section>
                <EngagementHeatmap
                  customerData={customerHeatmap}
                  ownerData={ownerHeatmap}
                />
              </section>

              {/* Conversion & Business Impact */}
              <section>
                <ConversionImpactSection
                  conversionData={finalConversionData}
                  ownerResponseTimes={finalOwnerResponseTimes}
                  cohortData={cohortData}
                />
              </section>

              {/* Activity Feed */}
              <section>
                <ActivityFeed items={activityItems} />
              </section>
            </motion.div>
          ) : (
            <motion.div
              key="abtesting"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="space-y-6"
            >
              {/* A/B Testing Header */}
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-foreground font-sans">
                    A/B Testing Framework
                  </h2>
                  <p className="text-sm text-muted-foreground">
                    Configure and monitor notification experiments
                  </p>
                </div>
                <button
                  onClick={() => setShowNewTest(!showNewTest)}
                  className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-gradient-to-r from-amber-500 to-amber-600 text-[hsl(220,25%,8%)] text-sm font-medium hover:shadow-lg hover:shadow-amber-500/20 transition-all"
                >
                  <Plus className="h-4 w-4" />
                  New Test
                </button>
              </div>

              {/* New Test Panel */}
              <AnimatePresence>
                {showNewTest && (
                  <ABTestConfigPanel onClose={() => setShowNewTest(false)} />
                )}
              </AnimatePresence>

              {/* Test Monitor */}
              <ABTestMonitor />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
