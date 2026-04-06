/**
 * CONFIT — Predictive Insights Panel
 * ====================================
 * Panel displaying predictive analytics alerts with drill-down integration.
 * Surfaces anomalies, forecasts, and opportunities in a luxury aesthetic.
 */

import { useMemo, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Bell,
  Settings,
  Sparkles,
  TrendingUp,
  TrendingDown,
  Minus,
  Filter,
  Check,
  X,
  ChevronDown,
  Clock,
  BarChart3,
  LineChart,
  AlertTriangle,
  Lightbulb,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
  SheetFooter,
} from '@/components/ui/sheet';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  PredictiveAlertCard,
  AlertSummary,
  PredictiveAlertBadge,
} from './PredictiveAlertCard';
import { usePredictiveInsightsStore } from '@/stores/predictiveInsightsStore';
import { useSalesFilterStore } from '@/stores/salesFilterStore';
import type {
  DetectedAnomaly,
  AnomalySeverity,
  RevenueForecast,
  ForecastHorizon,
  TrendDirection,
} from '@/types/predictiveInsightsTypes';
import { DURATION_LUXURY, EASE_LUXURY, createTransition } from '@/motion';
import './predictive.css';

// ─── Forecast Mini Chart Component ─────────────────────────────────────

function ForecastMiniChart({
  forecast,
  compact = true,
}: {
  forecast: RevenueForecast;
  compact?: boolean;
}) {
  const points = forecast.points.slice(0, compact ? 7 : forecast.points.length);
  const maxPredicted = Math.max(...points.map(p => p.predicted));

  const barClass = forecast.trend === 'up' ? 'forecast-bar-up' :
                  forecast.trend === 'down' ? 'forecast-bar-down' : 'forecast-bar-stable';

  return (
    <div className="flex items-end gap-0.5 h-8">
      {points.map((point, i) => {
        const height = maxPredicted > 0 ? (point.predicted / maxPredicted) * 100 : 0;

        return (
          <motion.div
            key={point.date}
            initial={{ height: 0 }}
            animate={{ height: `${Math.max(4, height)}%` }}
            transition={{ delay: i * 0.03, duration: 0.3 }}
            className={cn('w-1.5 rounded-t-sm', barClass)}
            style={{ opacity: 0.7 + (i / points.length) * 0.3 }}
          />
        );
      })}
    </div>
  );
}

// ─── Trend Indicator Component ─────────────────────────────────────────

function TrendIndicator({ direction, className }: { direction: TrendDirection; className?: string }) {
  const config = {
    up: { icon: TrendingUp, textClass: 'severity-text-opportunity', label: 'Trending Up' },
    down: { icon: TrendingDown, textClass: 'severity-text-critical', label: 'Trending Down' },
    stable: { icon: Minus, textClass: 'severity-text-warning', label: 'Stable' },
  };

  const { icon: Icon, textClass, label } = config[direction];

  return (
    <div className={cn('flex items-center gap-1.5', className)}>
      <Icon className={cn('h-4 w-4', textClass)} />
      <span className={cn('text-xs font-medium', textClass)}>
        {label}
      </span>
    </div>
  );
}

// ─── Forecast Summary Card ─────────────────────────────────────────────

function ForecastSummaryCard({
  forecasts,
  trendDirection,
}: {
  forecasts: Record<ForecastHorizon, RevenueForecast | null>;
  trendDirection: TrendDirection;
}) {
  const forecast7d = forecasts['7d'];
  const forecast30d = forecasts['30d'];

  const formatCurrency = (value: number) => {
    if (value >= 1000000) return `EGP ${(value / 1000000).toFixed(1)}M`;
    if (value >= 1000) return `EGP ${(value / 1000).toFixed(0)}K`;
    return `EGP ${value.toFixed(0)}`;
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="rounded-xl border border-border/30 bg-surface-elevated/50 backdrop-blur-sm p-4"
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg flex items-center justify-center severity-bg-warning">
            <LineChart className="h-4 w-4 severity-text-warning" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-foreground">Revenue Forecast</h4>
            <p className="text-xs text-muted-foreground">Projected trajectory</p>
          </div>
        </div>
        <TrendIndicator direction={trendDirection} />
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* 7-Day Forecast */}
        <div className="space-y-2">
          <p className="text-xs text-muted-foreground">7-Day Projection</p>
          {forecast7d ? (
            <>
              <p className="text-lg font-bold text-foreground">
                {formatCurrency(forecast7d.totalPredicted)}
              </p>
              <ForecastMiniChart forecast={forecast7d} />
            </>
          ) : (
            <p className="text-sm text-muted-foreground">Insufficient data</p>
          )}
        </div>

        {/* 30-Day Forecast */}
        <div className="space-y-2">
          <p className="text-xs text-muted-foreground">30-Day Projection</p>
          {forecast30d ? (
            <>
              <p className="text-lg font-bold text-foreground">
                {formatCurrency(forecast30d.totalPredicted)}
              </p>
              <ForecastMiniChart forecast={forecast30d} compact />
            </>
          ) : (
            <p className="text-sm text-muted-foreground">Insufficient data</p>
          )}
        </div>
      </div>

      {/* Confidence Note */}
      {forecast7d && (
        <p className="text-[10px] text-muted-foreground mt-3">
          Confidence: {(forecast7d.confidence * 100).toFixed(0)}% • Based on recent trends
        </p>
      )}
    </motion.div>
  );
}

// ─── Filter Bar Component ──────────────────────────────────────────────

interface InsightsFilterBarProps {
  activeSeverity: AnomalySeverity | 'all';
  onSeverityChange: (severity: AnomalySeverity | 'all') => void;
  onClearFilters: () => void;
}

function InsightsFilterBar({
  activeSeverity,
  onSeverityChange,
  onClearFilters,
}: InsightsFilterBarProps) {
  const hasFilters = activeSeverity !== 'all';

  return (
    <div className="flex items-center gap-2 p-3 bg-muted/30 rounded-lg">
      <Filter className="h-4 w-4 text-muted-foreground" />

      {/* Severity Filter */}
      <Select
        value={activeSeverity}
        onValueChange={(v) => onSeverityChange(v as AnomalySeverity | 'all')}
      >
        <SelectTrigger className="h-8 w-[140px] text-xs">
          <SelectValue placeholder="All Severity" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Severity</SelectItem>
          <SelectItem value="critical">Critical</SelectItem>
          <SelectItem value="warning">Warning</SelectItem>
          <SelectItem value="opportunity">Opportunity</SelectItem>
        </SelectContent>
      </Select>

      {hasFilters && (
        <Button
          variant="ghost"
          size="sm"
          className="h-8 px-2 text-xs"
          onClick={onClearFilters}
        >
          Clear
        </Button>
      )}
    </div>
  );
}

// ─── Sensitivity Selector ──────────────────────────────────────────────

function SensitivitySelector() {
  const sensitivity = usePredictiveInsightsStore((s) => s.sensitivity);
  const setSensitivity = usePredictiveInsightsStore((s) => s.setSensitivity);

  const config = {
    high: { label: 'High', desc: 'More alerts', textClass: 'severity-text-critical' },
    medium: { label: 'Medium', desc: 'Balanced', textClass: 'severity-text-warning' },
    low: { label: 'Low', desc: 'Critical only', textClass: 'severity-text-opportunity' },
  };

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-muted-foreground">Sensitivity:</span>
      <div className="flex gap-1">
        {(['high', 'medium', 'low'] as const).map((level) => (
          <button
            key={level}
            onClick={() => setSensitivity(level)}
            className={cn(
              'px-2 py-1 rounded text-xs font-medium transition-all',
              sensitivity === level
                ? cn('bg-accent/20', config[level].textClass)
                : 'text-muted-foreground hover:text-foreground'
            )}
            title={config[level].desc}
          >
            {config[level].label}
          </button>
        ))}
      </div>
    </div>
  );
}

// ─── Main Panel Component ───────────────────────────────────────────────

export interface PredictiveInsightsPanelProps {
  /** Anomalie detected by the detection engine */
  anomalies: DetectedAnomaly[];
  /** Revenue forecasts by horizon */
  forecasts: Record<ForecastHorizon, RevenueForecast | null>;
  /** Overall trend direction */
  trendDirection: TrendDirection;
  /** Whether insights are being computed */
  isComputing?: boolean;
  /** Callback when drill-down is triggered */
  onDrillDown?: (filters: DetectedAnomaly['drillDownFilters']) => void;
  /** Trigger element (defaults to bell button) */
  trigger?: React.ReactNode;
  /** Additional CSS class */
  className?: string;
}

export function PredictiveInsightsPanel({
  anomalies,
  forecasts,
  trendDirection,
  isComputing = false,
  onDrillDown,
  trigger,
  className,
}: PredictiveInsightsPanelProps) {
  const [open, setOpen] = useState(false);
  const [activeSeverity, setActiveSeverity] = useState<AnomalySeverity | 'all'>('all');

  const store = usePredictiveInsightsStore((s) => ({
    acknowledgeAnomaly: s.acknowledgeAnomaly,
    dismissAnomaly: s.dismissAnomaly,
    markAllRead: () => {
      anomalies.forEach(a => s.acknowledgeAnomaly(a.id));
    },
  }));

  // Filter anomalies
  const filteredAnomalies = useMemo(() => {
    let filtered = anomalies.filter(a => !a.dismissed);

    if (activeSeverity !== 'all') {
      filtered = filtered.filter(a => a.severity === activeSeverity);
    }

    // Sort: unacknowledged first, then by severity, then by date
    return [...filtered].sort((a, b) => {
      // Unacknowledged first
      if (a.acknowledged !== b.acknowledged) return a.acknowledged ? 1 : -1;

      // Severity order
      const severityOrder = { critical: 0, warning: 1, opportunity: 2 };
      const severityDiff = severityOrder[a.severity] - severityOrder[b.severity];
      if (severityDiff !== 0) return severityDiff;

      // Date descending
      return b.detectedAt.localeCompare(a.detectedAt);
    });
  }, [anomalies, activeSeverity]);

  // Stats
  const stats = useMemo(() => {
    const active = anomalies.filter(a => !a.dismissed);
    const unacknowledged = active.filter(a => !a.acknowledged);
    const critical = active.filter(a => a.severity === 'critical').length;
    const warning = active.filter(a => a.severity === 'warning').length;
    const opportunity = active.filter(a => a.severity === 'opportunity').length;

    return { total: active.length, unacknowledged: unacknowledged.length, critical, warning, opportunity };
  }, [anomalies]);

  // Handle drill-down
  const handleDrillDown = useCallback(
    (filters: DetectedAnomaly['drillDownFilters']) => {
      // Apply filters to sales filter store
      const salesStore = useSalesFilterStore.getState();

      if (filters.productName) {
        salesStore.setProductName(filters.productName);
      }
      if (filters.category) {
        salesStore.updateFilter('categories', [filters.category as any], 'widget');
      }
      if (filters.dateRange) {
        salesStore.updateFilter('dateRange', filters.dateRange, 'widget');
      }
      if (filters.marginRange) {
        salesStore.setMarginRange(filters.marginRange);
      }
      if (filters.returnStatuses && filters.returnStatuses.length > 0) {
        salesStore.setReturnStatuses(filters.returnStatuses as any);
      }

      // Close panel and call external handler
      setOpen(false);
      onDrillDown?.(filters);
    },
    [onDrillDown]
  );

  const handleClearFilters = () => {
    setActiveSeverity('all');
  };

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        {trigger || (
          <button
            className={cn(
              'relative p-2 rounded-full hover:bg-muted transition-colors',
              className
            )}
            title="Predictive Insights"
            aria-label={`Predictive Insights${stats.unacknowledged > 0 ? ` (${stats.unacknowledged} new)` : ''}`}
          >
            <Bell className="h-5 w-5" />
            {stats.unacknowledged > 0 && (
              <motion.span
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                className={cn(
                  'absolute -top-0.5 -right-0.5 h-5 w-5 rounded-full text-white text-[10px] font-bold flex items-center justify-center',
                  stats.critical > 0 ? 'gradient-gold-purple' : 'severity-bg-warning'
                )}
              >
                {stats.unacknowledged > 9 ? '9+' : stats.unacknowledged}
              </motion.span>
            )}
          </button>
        )}
      </SheetTrigger>

      <SheetContent side="right" className="w-full sm:max-w-md p-0 flex flex-col">
        {/* Header */}
        <SheetHeader className="p-4 border-b border-border">
          <div className="flex items-center justify-between">
            <SheetTitle className="flex items-center gap-2 text-lg">
              <Sparkles className="h-5 w-5 severity-text-critical" />
              Predictive Insights
            </SheetTitle>
            <div className="flex items-center gap-2">
              {stats.unacknowledged > 0 && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 text-xs gap-1"
                  onClick={store.markAllRead}
                >
                  <Check className="h-3.5 w-3.5" />
                  Mark all read
                </Button>
              )}
              <SensitivitySelector />
            </div>
          </div>
        </SheetHeader>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto">
          {/* Forecast Summary */}
          <div className="px-4 pt-4">
            <ForecastSummaryCard
              forecasts={forecasts}
              trendDirection={trendDirection}
            />
          </div>

          {/* Summary Stats */}
          <div className="px-4 pt-4">
            <AlertSummary
              anomalies={anomalies}
              onFilterBySeverity={(severity) => setActiveSeverity(severity)}
            />
          </div>

          {/* Filters */}
          <div className="px-4 pt-3">
            <InsightsFilterBar
              activeSeverity={activeSeverity}
              onSeverityChange={setActiveSeverity}
              onClearFilters={handleClearFilters}
            />
          </div>

          {/* Alerts List */}
          <div className="p-4 space-y-3">
            <AnimatePresence initial={false}>
              {isComputing ? (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="text-center py-12"
                >
                  <div className="w-12 h-12 rounded-full border-2 border-t-transparent loader-spin mx-auto mb-4 severity-border-warning" />
                  <p className="text-muted-foreground font-medium">Analyzing patterns...</p>
                </motion.div>
              ) : filteredAnomalies.length === 0 ? (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="text-center py-12"
                >
                  <div className="w-16 h-16 rounded-full bg-muted/50 flex items-center justify-center mx-auto mb-4">
                    {activeSeverity === 'opportunity' ? (
                      <Lightbulb className="h-8 w-8 text-muted-foreground opacity-50" />
                    ) : (
                      <Bell className="h-8 w-8 text-muted-foreground opacity-50" />
                    )}
                  </div>
                  <p className="text-muted-foreground font-medium">
                    {activeSeverity === 'all' ? 'No insights detected' : `No ${activeSeverity} insights`}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {activeSeverity === 'all'
                      ? 'Your sales performance is within normal ranges'
                      : 'Try adjusting the filter'}
                  </p>
                </motion.div>
              ) : (
                filteredAnomalies.slice(0, 50).map((anomaly) => (
                  <PredictiveAlertCard
                    key={anomaly.id}
                    alert={anomaly}
                    onDrillDown={handleDrillDown}
                    onMarkRead={() => store.acknowledgeAnomaly(anomaly.id)}
                    onDismiss={() => store.dismissAnomaly(anomaly.id)}
                  />
                ))
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* Footer */}
        <SheetFooter className="p-4 border-t border-border">
          <div className="flex items-center justify-between w-full text-xs text-muted-foreground">
            <div className="flex items-center gap-1.5">
              <Clock className="h-3 w-3" />
              <span>Updated {new Date().toLocaleTimeString()}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <BarChart3 className="h-3 w-3" />
              <span>{stats.total} insights</span>
            </div>
          </div>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}

// ─── Compact Badge Component ────────────────────────────────────────────

export interface PredictiveInsightsBadgeProps {
  anomalies: DetectedAnomaly[];
  onClick?: () => void;
  className?: string;
}

export function PredictiveInsightsBadge({
  anomalies,
  onClick,
  className,
}: PredictiveInsightsBadgeProps) {
  const stats = useMemo(() => {
    const active = anomalies.filter(a => !a.dismissed && !a.acknowledged);
    const critical = active.filter(a => a.severity === 'critical').length;
    const warning = active.filter(a => a.severity === 'warning').length;
    const opportunity = active.filter(a => a.severity === 'opportunity').length;

    return { total: active.length, critical, warning, opportunity };
  }, [anomalies]);

  if (stats.total === 0) return null;

  return (
    <motion.button
      initial={{ scale: 0 }}
      animate={{ scale: 1 }}
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      onClick={onClick}
      className={cn(
        'relative flex items-center gap-2 px-3 py-1.5 rounded-full',
        'bg-gradient-to-r from-purple-500/20 to-blue-500/20',
        'border border-purple-500/30 hover:border-purple-500/50',
        'transition-all cursor-pointer',
        className
      )}
    >
      <Sparkles className="h-3.5 w-3.5 severity-text-critical" />
      <span className="text-xs font-medium text-foreground">
        {stats.total} insight{stats.total !== 1 ? 's' : ''}
      </span>

      {/* Severity Dots */}
      <div className="flex gap-1">
        {stats.critical > 0 && (
          <span className="w-1.5 h-1.5 rounded-full severity-dot-critical" />
        )}
        {stats.warning > 0 && (
          <span className="w-1.5 h-1.5 rounded-full severity-dot-warning" />
        )}
        {stats.opportunity > 0 && (
          <span className="w-1.5 h-1.5 rounded-full severity-dot-opportunity" />
        )}
      </div>
    </motion.button>
  );
}

export default PredictiveInsightsPanel;
