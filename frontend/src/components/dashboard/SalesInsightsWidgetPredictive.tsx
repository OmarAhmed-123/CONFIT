/**
 * CONFIT — Sales Insights Widget with Predictive Analytics
 * ==========================================================
 * Enhanced version of SalesInsightsWidgetConnected with integrated
 * predictive analytics, anomaly detection, and forecasting.
 *
 * Features:
 * - All features of SalesInsightsWidgetConnected
 * - Real-time anomaly detection with statistical methods
 * - Revenue forecasting (7/14/30 day horizons)
 * - Predictive alerts panel with drill-down
 * - Sensitivity configuration
 * - Performance optimized with debouncing
 */

import { memo, useCallback, useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, Bell, Settings, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  SalesInsightsWidgetConnected,
  type SalesInsightsWidgetConnectedProps,
} from './SalesInsightsWidgetConnected';
import {
  PredictiveInsightsPanel,
  PredictiveInsightsBadge,
} from '@/components/predictive/PredictiveInsightsPanel';
import { usePredictiveInsights } from '@/hooks/usePredictiveInsights';
import { useSalesFilterStore } from '@/stores';
import type { DrillDownFilters } from './SalesInsightsWidget';
import type { AnomalyDrillDownFilters } from '@/types/predictiveInsightsTypes';
import { DURATION_LUXURY, EASE_LUXURY } from '@/motion';
import '@/components/predictive/predictive.css';

// ─── Types ──────────────────────────────────────────────────────────────

export interface SalesInsightsWidgetPredictiveProps extends SalesInsightsWidgetConnectedProps {
  /** Enable predictive analytics */
  enablePredictive?: boolean;
  /** Show predictive insights badge */
  showPredictiveBadge?: boolean;
  /** Show predictive insights panel trigger */
  showPredictiveTrigger?: boolean;
  /** Predictive sensitivity level */
  predictiveSensitivity?: 'high' | 'medium' | 'low';
  /** Callback when predictive drill-down is triggered */
  onPredictiveDrillDown?: (filters: AnomalyDrillDownFilters) => void;
}

// ─── Trend Indicator Mini Component ────────────────────────────────────

function TrendMiniIndicator({ direction }: { direction: 'up' | 'down' | 'stable' }) {
  const config = {
    up: { icon: TrendingUp, bgClass: 'trend-bg-up', textClass: 'severity-text-opportunity' },
    down: { icon: TrendingDown, bgClass: 'trend-bg-down', textClass: 'severity-text-critical' },
    stable: { icon: Minus, bgClass: 'trend-bg-stable', textClass: 'severity-text-warning' },
  };

  const { icon: Icon, bgClass, textClass } = config[direction];

  return (
    <div className={cn('flex items-center justify-center w-6 h-6 rounded-full', bgClass)}>
      <Icon className={cn('h-3.5 w-3.5', textClass)} />
    </div>
  );
}

// ─── Predictive Header Component ────────────────────────────────────────

interface PredictiveHeaderProps {
  criticalCount: number;
  warningCount: number;
  opportunityCount: number;
  trendDirection: 'up' | 'down' | 'stable';
  onOpenPanel: () => void;
}

function PredictiveHeader({
  criticalCount,
  warningCount,
  opportunityCount,
  trendDirection,
  onOpenPanel,
}: PredictiveHeaderProps) {
  const totalInsights = criticalCount + warningCount + opportunityCount;

  if (totalInsights === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="flex items-center justify-between px-4 py-2 mb-4 rounded-lg bg-gradient-to-r from-purple-500/10 to-blue-500/10 border border-purple-500/20"
    >
      <div className="flex items-center gap-3">
        <Sparkles className="h-4 w-4 severity-text-critical" />
        <span className="text-sm font-medium text-foreground">
          {totalInsights} insight{totalInsights !== 1 ? 's' : ''} detected
        </span>

        {/* Severity Dots */}
        <div className="flex items-center gap-1.5">
          {criticalCount > 0 && (
            <div className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full animate-pulse severity-dot-critical" />
              <span className="text-xs text-muted-foreground">{criticalCount}</span>
            </div>
          )}
          {warningCount > 0 && (
            <div className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full severity-dot-warning" />
              <span className="text-xs text-muted-foreground">{warningCount}</span>
            </div>
          )}
          {opportunityCount > 0 && (
            <div className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full severity-dot-opportunity" />
              <span className="text-xs text-muted-foreground">{opportunityCount}</span>
            </div>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2">
        <TrendMiniIndicator direction={trendDirection} />
        <Button
          variant="ghost"
          size="sm"
          onClick={onOpenPanel}
          className="h-7 px-2 text-xs gap-1 text-purple-400 hover:text-purple-300 hover:bg-purple-500/10"
        >
          View Insights
        </Button>
      </div>
    </motion.div>
  );
}

// ─── Main Predictive Widget Component ────────────────────────────────────

function SalesInsightsWidgetPredictiveBase({
  data,
  isLoading = false,
  error = null,
  className,
  showHistoryControls = true,
  showFilterIndicator = true,
  onDrillDown,
  enablePredictive = true,
  showPredictiveBadge = true,
  showPredictiveTrigger = true,
  predictiveSensitivity = 'medium',
  onPredictiveDrillDown,
}: SalesInsightsWidgetPredictiveProps) {
  const [isPanelOpen, setIsPanelOpen] = useState(false);

  // Get filtered data from store for predictive analysis
  const filteredData = useSalesFilterStore((s) => s.getFilteredData());

  // Predictive insights hook
  const predictive = usePredictiveInsights({
    data: filteredData,
    enabled: enablePredictive && !isLoading && filteredData.length >= 10,
    sensitivity: predictiveSensitivity,
    debounceMs: 150,
    onDrillDown: onPredictiveDrillDown,
  });

  // Handle drill-down from widget (pass through + predictive sync)
  const handleDrillDown = useCallback(
    (filters: DrillDownFilters) => {
      onDrillDown?.(filters);
    },
    [onDrillDown]
  );

  // Handle predictive drill-down
  const handlePredictiveDrillDown = useCallback(
    (filters: AnomalyDrillDownFilters) => {
      onPredictiveDrillDown?.(filters);
    },
    [onPredictiveDrillDown]
  );

  // Open predictive panel
  const handleOpenPanel = useCallback(() => {
    setIsPanelOpen(true);
  }, []);

  return (
    <div className={cn('relative', className)}>
      {/* Predictive Insights Header */}
      {enablePredictive && showPredictiveBadge && (
        <AnimatePresence>
          {(predictive.criticalCount > 0 || predictive.warningCount > 0) && (
            <PredictiveHeader
              criticalCount={predictive.criticalCount}
              warningCount={predictive.warningCount}
              opportunityCount={predictive.opportunityCount}
              trendDirection={predictive.trendDirection}
              onOpenPanel={handleOpenPanel}
            />
          )}
        </AnimatePresence>
      )}

      {/* Original Connected Widget */}
      <SalesInsightsWidgetConnected
        data={data}
        isLoading={isLoading}
        error={error}
        showHistoryControls={showHistoryControls}
        showFilterIndicator={showFilterIndicator}
        onDrillDown={handleDrillDown}
      />

      {/* Predictive Insights Panel */}
      {enablePredictive && showPredictiveTrigger && (
        <PredictiveInsightsPanel
          anomalies={predictive.anomalies}
          forecasts={predictive.forecasts}
          trendDirection={predictive.trendDirection}
          isComputing={predictive.isComputing}
          onDrillDown={handlePredictiveDrillDown}
          trigger={
            <Button
              variant="ghost"
              size="icon"
              className="relative"
              title="Predictive Insights"
            >
              <Bell className="h-5 w-5" />
              {predictive.unacknowledgedCount > 0 && (
                <motion.span
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  className={cn(
                    'absolute -top-0.5 -right-0.5 h-5 w-5 rounded-full text-white text-[10px] font-bold flex items-center justify-center',
                    predictive.criticalCount > 0 ? 'gradient-gold-purple' : 'severity-bg-warning'
                  )}
                >
                  {predictive.unacknowledgedCount > 9 ? '9+' : predictive.unacknowledgedCount}
                </motion.span>
              )}
            </Button>
          }
        />
      )}
    </div>
  );
}

// Export memoized component
export const SalesInsightsWidgetPredictive = memo(SalesInsightsWidgetPredictiveBase);

// ─── Hook Export for Direct Use ────────────────────────────────────────

export { usePredictiveInsights } from '@/hooks/usePredictiveInsights';

// ─── Type Exports ───────────────────────────────────────────────────────

export type { AnomalyDrillDownFilters } from '@/types/predictiveInsightsTypes';

export default SalesInsightsWidgetPredictive;
