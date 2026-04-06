/**
 * CONFIT — Predictive Alert Card
 * ================================
 * Individual alert card for displaying predictive insights with CONFIT's
 * luxury gold/purple aesthetic. Supports drill-down interactions.
 */

import { useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  AlertTriangle,
  AlertCircle,
  TrendingUp,
  TrendingDown,
  Minus,
  DollarSign,
  Percent,
  Package,
  RotateCcw,
  ChevronRight,
  X,
  Check,
  Clock,
  BarChart3,
  Layers,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import type {
  DetectedAnomaly,
  AnomalySeverity,
  AnomalyType,
} from '@/types/predictiveInsightsTypes';
import {
  getAnomalySeverityConfig,
  getAnomalyTypeConfig,
} from '@/types/predictiveInsightsTypes';
import { usePredictiveInsightsStore } from '@/stores/predictiveInsightsStore';
import { DURATION_STANDARD, EASE_LUXURY, createTransition } from '@/motion';
import './predictive.css';

// ─── Time Formatting ────────────────────────────────────────────────────

function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

function formatCurrency(value: number): string {
  if (value >= 1000000) return `EGP ${(value / 1000000).toFixed(1)}M`;
  if (value >= 1000) return `EGP ${(value / 1000).toFixed(0)}K`;
  return `EGP ${value.toFixed(0)}`;
}

// ─── Severity Icon Component ────────────────────────────────────────────

function SeverityIcon({ severity, className }: { severity: AnomalySeverity; className?: string }) {
  const config = getAnomalySeverityConfig(severity);

  switch (config.icon) {
    case 'AlertTriangle':
      return (
        <motion.span
          className={className}
          animate={{ scale: [1, 1.1, 1] }}
          transition={{ duration: 2, repeat: Infinity }}
        >
          <AlertTriangle className="h-4 w-4" />
        </motion.span>
      );
    case 'AlertCircle':
      return <AlertCircle className={className} />;
    case 'TrendingUp':
      return <TrendingUp className={className} />;
    default:
      return <AlertCircle className={className} />;
  }
}

// ─── Metric Icon Component ──────────────────────────────────────────────

function MetricIcon({ type, className }: { type: AnomalyType; className?: string }) {
  const isPositive = getAnomalyTypeConfig(type).isPositive;

  if (type.includes('revenue')) {
    return <DollarSign className={className} />;
  }
  if (type.includes('margin')) {
    return <Percent className={className} />;
  }
  if (type.includes('velocity')) {
    return <Package className={className} />;
  }
  if (type.includes('return')) {
    return <RotateCcw className={className} />;
  }
  if (type.includes('category')) {
    return <Layers className={className} />;
  }
  if (type.includes('product')) {
    return <BarChart3 className={className} />;
  }

  return isPositive ? <TrendingUp className={className} /> : <TrendingDown className={className} />;
}

// ─── Severity Badge Component ───────────────────────────────────────────

function SeverityBadge({ severity }: { severity: AnomalySeverity }) {
  const config = getAnomalySeverityConfig(severity);

  const variantStyles = {
    critical: 'bg-gold-500/20 text-gold-400 border-gold-500/30',
    warning: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
    opportunity: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  };

  return (
    <Badge
      variant="outline"
      className={cn(
        'text-[10px] font-medium uppercase tracking-wider',
        variantStyles[severity],
        severity === 'critical' && 'severity-border-critical severity-text-critical',
        severity === 'warning' && 'severity-border-warning severity-text-warning',
        severity === 'opportunity' && 'severity-border-opportunity severity-text-opportunity'
      )}
    >
      {config.label}
    </Badge>
  );
}

// ─── Deviation Indicator Component ──────────────────────────────────────

function DeviationIndicator({
  percentDeviation,
  severity,
}: {
  percentDeviation: number;
  severity: AnomalySeverity;
}) {
  const isNegative = percentDeviation < 0;
  const absDev = Math.abs(percentDeviation).toFixed(1);

  const textClass = severity === 'critical' ? 'severity-text-critical' :
                    severity === 'warning' ? 'severity-text-warning' :
                    'severity-text-opportunity';

  return (
    <div className="flex items-center gap-1.5">
      {isNegative ? (
        <TrendingDown className={cn('h-3.5 w-3.5', textClass)} />
      ) : (
        <TrendingUp className={cn('h-3.5 w-3.5', textClass)} />
      )}
      <span className={cn('text-sm font-semibold', textClass)}>
        {isNegative ? '-' : '+'}{absDev}%
      </span>
    </div>
  );
}

// ─── Main Alert Card Component ──────────────────────────────────────────

export interface PredictiveAlertCardProps {
  alert: DetectedAnomaly;
  compact?: boolean;
  showActions?: boolean;
  onDrillDown?: (filters: DetectedAnomaly['drillDownFilters']) => void;
  onMarkRead?: () => void;
  onDismiss?: () => void;
  className?: string;
}

export function PredictiveAlertCard({
  alert,
  compact = false,
  showActions = true,
  onDrillDown,
  onMarkRead,
  onDismiss,
  className,
}: PredictiveAlertCardProps) {
  const storeActions = usePredictiveInsightsStore((s) => ({
    acknowledgeAnomaly: s.acknowledgeAnomaly,
    dismissAnomaly: s.dismissAnomaly,
  }));

  const severityConfig = getAnomalySeverityConfig(alert.severity);
  const typeConfig = getAnomalyTypeConfig(alert.type);

  const handleMarkRead = useCallback(() => {
    storeActions.acknowledgeAnomaly(alert.id);
    onMarkRead?.();
  }, [storeActions, alert.id, onMarkRead]);

  const handleDismiss = useCallback(() => {
    storeActions.dismissAnomaly(alert.id);
    onDismiss?.();
  }, [storeActions, alert.id, onDismiss]);

  const handleDrillDown = useCallback(() => {
    if (onDrillDown) {
      onDrillDown(alert.drillDownFilters);
    }
  }, [onDrillDown, alert.drillDownFilters]);

  // Determine border color based on severity
  const borderColor = useMemo(() => {
    switch (alert.severity) {
      case 'critical':
        return 'border-l-gold-500';
      case 'warning':
        return 'border-l-purple-500';
      case 'opportunity':
        return 'border-l-emerald-500';
    }
  }, [alert.severity]);

  // Determine glow color
  const glowColor = useMemo(() => {
    switch (alert.severity) {
      case 'critical':
        return 'shadow-[0_0_20px_rgba(212,175,55,0.15)]';
      case 'warning':
        return 'shadow-[0_0_20px_rgba(139,92,246,0.15)]';
      case 'opportunity':
        return 'shadow-[0_0_20px_rgba(16,185,129,0.15)]';
    }
  }, [alert.severity]);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 10, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, x: -20, scale: 0.95 }}
      transition={createTransition({ duration: 0.2 })}
      className={cn(
        'group relative rounded-xl border-l-2 transition-all cursor-pointer',
        'bg-surface-elevated/50 backdrop-blur-sm border border-border/30',
        borderColor,
        glowColor,
        alert.acknowledged ? 'opacity-60' : '',
        !compact && 'p-4',
        compact && 'p-3',
        className
      )}
      onClick={handleDrillDown}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          handleDrillDown();
        }
      }}
    >
      <div className={cn('flex gap-3', compact && 'gap-2')}>
        {/* Severity Icon */}
        <div
          className={cn(
            'flex-shrink-0 rounded-lg flex items-center justify-center',
            compact ? 'w-8 h-8' : 'w-10 h-10',
            alert.severity === 'critical' && 'severity-bg-critical',
            alert.severity === 'warning' && 'severity-bg-warning',
            alert.severity === 'opportunity' && 'severity-bg-opportunity'
          )}
        >
          <SeverityIcon
            severity={alert.severity}
            className={cn(
              alert.severity === 'critical' && 'severity-text-critical',
              alert.severity === 'warning' && 'severity-text-warning',
              alert.severity === 'opportunity' && 'severity-text-opportunity'
            )}
          />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Header */}
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <SeverityBadge severity={alert.severity} />
                {!alert.acknowledged && (
                  <span
                    className={cn(
                      'flex-shrink-0 w-2 h-2 rounded-full animate-pulse',
                      alert.severity === 'critical' ? 'gradient-gold-purple' : 'severity-dot-warning'
                    )}
                  />
                )}
              </div>
              <h4
                className={cn(
                  'text-sm font-medium mt-1 truncate',
                  !alert.acknowledged && 'text-foreground'
                )}
                title={alert.description}
              >
                {alert.description}
              </h4>
            </div>

            {/* Dismiss Button */}
            {showActions && (
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
                onClick={(e) => {
                  e.stopPropagation();
                  handleDismiss();
                }}
              >
                <X className="h-3.5 w-3.5 text-muted-foreground" />
              </Button>
            )}
          </div>

          {/* Metrics Row */}
          <div className="flex items-center gap-4 mt-2">
            {/* Deviation */}
            <DeviationIndicator
              percentDeviation={alert.percentDeviation}
              severity={alert.severity}
            />

            {/* Baseline Reference */}
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <span>vs baseline</span>
              <span className="font-medium">
                {alert.metric === 'revenue' ? formatCurrency(alert.baselineValue) :
                 alert.metric === 'profit_margin' ? `${alert.baselineValue.toFixed(1)}%` :
                 alert.metric === 'return_rate' ? `${alert.baselineValue.toFixed(1)}%` :
                 alert.baselineValue.toFixed(0)}
              </span>
            </div>
          </div>

          {/* Recommendation (non-compact) */}
          {!compact && (
            <p className="mt-2 text-xs text-muted-foreground/80 line-clamp-2">
              {alert.recommendation}
            </p>
          )}

          {/* Footer */}
          <div className={cn('flex items-center justify-between mt-3', compact && 'mt-2')}>
            <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
              <Clock className="h-3 w-3" />
              <span>{formatTimeAgo(alert.detectedAt)}</span>
              {!compact && (
                <>
                  <span>•</span>
                  <span className="flex items-center gap-1">
                    <MetricIcon type={alert.type} className="h-3 w-3" />
                    {typeConfig.label}
                  </span>
                </>
              )}
            </div>

            {/* Actions */}
            {showActions && (
              <div className="flex items-center gap-1">
                {!alert.acknowledged && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleMarkRead();
                    }}
                    title="Mark as read"
                  >
                    <Check className="h-3.5 w-3.5" />
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 px-2 text-xs gap-1 opacity-0 group-hover:opacity-100 transition-opacity"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDrillDown();
                  }}
                >
                  View
                  <ChevronRight className="h-3 w-3" />
                </Button>
              </div>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

// ─── Compact Alert Badge Component ──────────────────────────────────────

export interface PredictiveAlertBadgeProps {
  count: number;
  severity: AnomalySeverity;
  onClick?: () => void;
  className?: string;
}

export function PredictiveAlertBadge({
  count,
  severity,
  onClick,
  className,
}: PredictiveAlertBadgeProps) {
  if (count === 0) return null;

  return (
    <motion.button
      initial={{ scale: 0 }}
      animate={{ scale: 1 }}
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      onClick={onClick}
      className={cn(
        'relative flex items-center justify-center rounded-full',
        'h-5 min-w-[20px] px-1.5 text-[10px] font-bold text-white',
        severity === 'critical' ? 'gradient-gold-purple' : 
        severity === 'warning' ? 'severity-bg-warning' : 'severity-bg-opportunity',
        className
      )}
    >
      {count > 9 ? '9+' : count}
    </motion.button>
  );
}

// ─── Alert Summary Component ───────────────────────────────────────────

export interface AlertSummaryProps {
  anomalies: DetectedAnomaly[];
  onFilterBySeverity?: (severity: AnomalySeverity | 'all') => void;
  className?: string;
}

export function AlertSummary({ anomalies, onFilterBySeverity, className }: AlertSummaryProps) {
  const stats = useMemo(() => {
    const critical = anomalies.filter((a) => a.severity === 'critical' && !a.dismissed).length;
    const warning = anomalies.filter((a) => a.severity === 'warning' && !a.dismissed).length;
    const opportunity = anomalies.filter((a) => a.severity === 'opportunity' && !a.dismissed).length;
    return { critical, warning, opportunity, total: critical + warning + opportunity };
  }, [anomalies]);

  if (stats.total === 0) return null;

  return (
    <div className={cn('flex items-center gap-3 p-3 bg-muted/20 rounded-lg', className)}>
      {stats.critical > 0 && (
        <button
          onClick={() => onFilterBySeverity?.('critical')}
          className="flex items-center gap-1.5 hover:opacity-80 transition-opacity"
        >
          <span className="w-2 h-2 rounded-full severity-dot-critical" />
          <span className="text-xs font-medium severity-text-critical">
            {stats.critical} Critical
          </span>
        </button>
      )}
      {stats.warning > 0 && (
        <button
          onClick={() => onFilterBySeverity?.('warning')}
          className="flex items-center gap-1.5 hover:opacity-80 transition-opacity"
        >
          <span className="w-2 h-2 rounded-full severity-dot-warning" />
          <span className="text-xs font-medium severity-text-warning">
            {stats.warning} Warning
          </span>
        </button>
      )}
      {stats.opportunity > 0 && (
        <button
          onClick={() => onFilterBySeverity?.('opportunity')}
          className="flex items-center gap-1.5 hover:opacity-80 transition-opacity"
        >
          <span className="w-2 h-2 rounded-full severity-dot-opportunity" />
          <span className="text-xs font-medium severity-text-opportunity">
            {stats.opportunity} Opportunity
          </span>
        </button>
      )}
    </div>
  );
}

export default PredictiveAlertCard;
