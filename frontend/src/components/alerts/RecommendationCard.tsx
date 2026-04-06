/**
 * CONFIT — Recommendation Card
 * ==============================
 * Individual recommendation card with CONFIT's luxury gold/purple aesthetic.
 * Displays threshold recommendations with backtesting validation.
 */

import { useMemo, useCallback, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Check,
  X,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Settings2,
  Sparkles,
  BarChart3,
  Clock,
  Zap,
  Package,
  RotateCcw,
  Users,
  Calendar,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Slider } from '@/components/ui/slider';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import type {
  AlertRecommendation,
  ThresholdRecommendation,
} from '@/types/alertRecommendationTypes';
import {
  getRecommendationTypeLabel,
  getConfidenceColor,
  getImpactColor,
  formatThresholdValue,
  isRecommendationActionable,
} from '@/types/alertRecommendationTypes';
import { DURATION_STANDARD, EASE_LUXURY, createTransition } from '@/motion';

// ─── Icons by Recommendation Type ─────────────────────────────────────────────

function getTypeIcon(type: string) {
  switch (type) {
    case 'return_spike':
      return RotateCcw;
    case 'high_value_aov':
      return TrendingUp;
    case 'conversion_anomaly':
      return BarChart3;
    case 'inventory_depletion':
      return Package;
    case 'seasonal_adjustment':
      return Calendar;
    case 'vip_inactivity':
      return Users;
    default:
      return Sparkles;
  }
}

// ─── Confidence Indicator Component ───────────────────────────────────────────

function ConfidenceIndicator({
  confidence,
  score,
}: {
  confidence: string;
  score: number;
}) {
  const colorClass = getConfidenceColor(confidence as 'low' | 'medium' | 'high');

  return (
    <div className="flex items-center gap-2">
      <div className="flex gap-0.5">
        {[1, 2, 3].map((level) => (
          <div
            key={level}
            className={cn(
              'w-1.5 h-4 rounded-sm',
              level <= (confidence === 'high' ? 3 : confidence === 'medium' ? 2 : 1)
                ? colorClass.replace('text-', 'bg-')
                : 'bg-muted/30'
            )}
          />
        ))}
      </div>
      <span className={cn('text-xs font-medium', colorClass)}>
        {Math.round(score * 100)}% confidence
      </span>
    </div>
  );
}

// ─── Threshold Comparison Component ───────────────────────────────────────────

function ThresholdComparison({
  threshold,
  isEditing,
  customValue,
  onCustomValueChange,
}: {
  threshold: ThresholdRecommendation;
  isEditing: boolean;
  customValue: number;
  onCustomValueChange: (value: number) => void;
}) {
  const isIncrease = Number(threshold.recommended_value) > Number(threshold.current_value);
  const percentChange = Math.abs(
    ((Number(threshold.recommended_value) - Number(threshold.current_value)) /
      Number(threshold.current_value)) *
      100
  ).toFixed(0);

  return (
    <div className="flex items-center justify-between py-2 border-b border-border/30 last:border-0">
      <div className="flex-1">
        <p className="text-xs text-muted-foreground">{threshold.parameter_name.replace(/_/g, ' ')}</p>
        <div className="flex items-center gap-3 mt-1">
          <span className="text-sm text-muted-foreground">
            Current: <span className="font-medium text-foreground">{formatThresholdValue(threshold.current_value, threshold.unit)}</span>
          </span>
          <div className="flex items-center gap-1">
            {isIncrease ? (
              <TrendingUp className="h-3 w-3 text-emerald-400" />
            ) : (
              <TrendingDown className="h-3 w-3 text-gold-400" />
            )}
            <span className={cn('text-xs font-medium', isIncrease ? 'text-emerald-400' : 'text-gold-400')}>
              {percentChange}%
            </span>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2">
        {isEditing ? (
          <div className="flex items-center gap-2 min-w-[120px]">
            <Slider
              value={[customValue]}
              onValueChange={(vals) => onCustomValueChange(vals[0])}
              min={Math.min(Number(threshold.current_value), Number(threshold.recommended_value)) * 0.5}
              max={Math.max(Number(threshold.current_value), Number(threshold.recommended_value)) * 1.5}
              step={1}
              className="w-20"
            />
            <span className="text-sm font-medium text-gold-400 min-w-[40px]">
              {formatThresholdValue(customValue, threshold.unit)}
            </span>
          </div>
        ) : (
          <span className="text-sm font-semibold text-gold-400">
            {formatThresholdValue(threshold.recommended_value, threshold.unit)}
          </span>
        )}
      </div>
    </div>
  );
}

// ─── Backtest Summary Component ───────────────────────────────────────────────

function BacktestSummaryDisplay({
  summary,
  isExpanded,
}: {
  summary: AlertRecommendation['backtest_summary'];
  isExpanded: boolean;
}) {
  if (!summary) return null;

  return (
    <AnimatePresence>
      {isExpanded && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          transition={{ duration: 0.2 }}
          className="overflow-hidden"
        >
          <div className="grid grid-cols-2 gap-3 p-3 bg-muted/20 rounded-lg mt-3">
            <div className="flex items-center gap-2">
              <Check className="h-4 w-4 text-emerald-400" />
              <span className="text-xs text-muted-foreground">Precision</span>
              <span className="text-sm font-medium text-emerald-400">
                {(summary.precision * 100).toFixed(0)}%
              </span>
            </div>
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-gold-400" />
              <span className="text-xs text-muted-foreground">False Positives</span>
              <span className="text-sm font-medium text-gold-400">
                {(summary.false_positive_rate * 100).toFixed(1)}%
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-purple-400" />
              <span className="text-xs text-muted-foreground">Moments Caught</span>
              <span className="text-sm font-medium text-purple-400">
                {summary.significant_moments_caught}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">Data Points</span>
              <span className="text-sm font-medium">
                {summary.data_points_analyzed}
              </span>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

// ─── Main Recommendation Card Component ───────────────────────────────────────

export interface RecommendationCardProps {
  recommendation: AlertRecommendation;
  onApply?: (recommendation: AlertRecommendation, customThresholds?: Record<string, number>) => void;
  onDismiss?: (recommendation: AlertRecommendation) => void;
  onCustomize?: (recommendation: AlertRecommendation) => void;
  onViewDetails?: (recommendation: AlertRecommendation) => void;
  isApplying?: boolean;
  showBacktest?: boolean;
  compact?: boolean;
  className?: string;
}

export function RecommendationCard({
  recommendation,
  onApply,
  onDismiss,
  onCustomize,
  onViewDetails,
  isApplying = false,
  showBacktest = true,
  compact = false,
  className,
}: RecommendationCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [customThresholds, setCustomThresholds] = useState<Record<string, number>>({});

  const isActionable = isRecommendationActionable(recommendation);
  const TypeIcon = getTypeIcon(recommendation.type);

  // Initialize custom thresholds from recommended values
  const initialCustomThreshold = useCallback((threshold: ThresholdRecommendation) => {
    return customThresholds[threshold.parameter_name] ?? Number(threshold.recommended_value);
  }, [customThresholds]);

  const handleApply = useCallback(() => {
    if (onApply) {
      onApply(recommendation, isEditing ? customThresholds : undefined);
    }
  }, [onApply, recommendation, isEditing, customThresholds]);

  const handleDismiss = useCallback(() => {
    if (onDismiss) {
      onDismiss(recommendation);
    }
  }, [onDismiss, recommendation]);

  const handleCustomValueChange = useCallback((paramName: string, value: number) => {
    setCustomThresholds((prev) => ({
      ...prev,
      [paramName]: value,
    }));
  }, []);

  // Border color based on impact
  const borderColor = useMemo(() => {
    switch (recommendation.impact_estimate) {
      case 'critical':
        return 'border-l-gold-500';
      case 'high':
        return 'border-l-purple-500';
      case 'medium':
        return 'border-l-purple-400';
      default:
        return 'border-l-muted';
    }
  }, [recommendation.impact_estimate]);

  // Glow effect
  const glowColor = useMemo(() => {
    switch (recommendation.impact_estimate) {
      case 'critical':
        return 'shadow-[0_0_20px_rgba(212,175,55,0.15)]';
      case 'high':
        return 'shadow-[0_0_20px_rgba(139,92,246,0.15)]';
      default:
        return '';
    }
  }, [recommendation.impact_estimate]);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, x: -20, scale: 0.95 }}
      transition={createTransition({ duration: 0.25 })}
      className={cn(
        'group relative rounded-xl border-l-2 transition-all',
        'bg-surface-elevated/50 backdrop-blur-sm border border-border/30',
        borderColor,
        glowColor,
        recommendation.status === 'applied' && 'opacity-60',
        recommendation.status === 'dismissed' && 'opacity-40',
        !compact && 'p-4',
        compact && 'p-3',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 flex-1">
          {/* Type Icon */}
          <div
            className={cn(
              'flex-shrink-0 rounded-lg flex items-center justify-center',
              compact ? 'w-8 h-8' : 'w-10 h-10',
              recommendation.impact_estimate === 'critical' && 'bg-gold-500/20',
              recommendation.impact_estimate === 'high' && 'bg-purple-500/20',
              recommendation.impact_estimate === 'medium' && 'bg-purple-400/20',
              recommendation.impact_estimate === 'low' && 'bg-muted/30'
            )}
          >
            <TypeIcon
              className={cn(
                compact ? 'h-4 w-4' : 'h-5 w-5',
                getImpactColor(recommendation.impact_estimate)
              )}
            />
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            {/* Title Row */}
            <div className="flex items-center gap-2 flex-wrap">
              <h4 className="text-sm font-medium truncate">
                {recommendation.title}
              </h4>
              {recommendation.impact_estimate === 'critical' && (
                <Badge variant="outline" className="text-[10px] border-gold-500/50 text-gold-400">
                  High Impact
                </Badge>
              )}
            </div>

            {/* Description */}
            {!compact && (
              <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                {recommendation.explanation.summary}
              </p>
            )}

            {/* Confidence & Impact Row */}
            <div className="flex items-center gap-4 mt-2">
              <ConfidenceIndicator
                confidence={recommendation.confidence}
                score={recommendation.confidence_score}
              />
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <Clock className="h-3 w-3" />
                <span>{recommendation.data_window_days} days analyzed</span>
              </div>
            </div>
          </div>
        </div>

        {/* Status Badge */}
        {recommendation.status === 'applied' && (
          <Badge variant="outline" className="border-emerald-500/50 text-emerald-400">
            <Check className="h-3 w-3 mr-1" />
            Applied
          </Badge>
        )}
        {recommendation.status === 'dismissed' && (
          <Badge variant="outline" className="border-muted text-muted-foreground">
            <X className="h-3 w-3 mr-1" />
            Dismissed
          </Badge>
        )}
      </div>

      {/* Thresholds Section */}
      {recommendation.thresholds.length > 0 && (
        <div className="mt-4 p-3 bg-muted/10 rounded-lg">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Threshold Adjustments
            </span>
            {isActionable && (
              <Button
                variant="ghost"
                size="sm"
                className="h-6 px-2 text-xs"
                onClick={() => setIsEditing(!isEditing)}
              >
                <Settings2 className="h-3 w-3 mr-1" />
                {isEditing ? 'Cancel' : 'Customize'}
              </Button>
            )}
          </div>

          {recommendation.thresholds.map((threshold, idx) => (
            <ThresholdComparison
              key={`${threshold.parameter_name}-${idx}`}
              threshold={threshold}
              isEditing={isEditing}
              customValue={initialCustomThreshold(threshold)}
              onCustomValueChange={(val) =>
                handleCustomValueChange(threshold.parameter_name, val)
              }
            />
          ))}
        </div>
      )}

      {/* Backtest Section */}
      {showBacktest && recommendation.backtest_summary && (
        <Collapsible open={isExpanded} onOpenChange={setIsExpanded} className="mt-3">
          <CollapsibleTrigger asChild>
            <button className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground transition-colors w-full justify-center py-1">
              <BarChart3 className="h-3 w-3" />
              <span>Backtest Results</span>
              {isExpanded ? (
                <ChevronUp className="h-3 w-3" />
              ) : (
                <ChevronDown className="h-3 w-3" />
              )}
            </button>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <BacktestSummaryDisplay
              summary={recommendation.backtest_summary}
              isExpanded={isExpanded}
            />
          </CollapsibleContent>
        </Collapsible>
      )}

      {/* Action Buttons */}
      {isActionable && (
        <div className="flex items-center justify-end gap-2 mt-4 pt-3 border-t border-border/30">
          <Button
            variant="ghost"
            size="sm"
            className="h-8 px-3 text-xs text-muted-foreground hover:text-foreground"
            onClick={handleDismiss}
            disabled={isApplying}
          >
            <X className="h-3.5 w-3.5 mr-1" />
            Dismiss
          </Button>
          <Button
            variant="default"
            size="sm"
            className={cn(
              'h-8 px-4 text-xs',
              'bg-gradient-to-r from-gold-500 to-purple-500 hover:from-gold-400 hover:to-purple-400',
              'text-white font-medium'
            )}
            onClick={handleApply}
            disabled={isApplying}
          >
            {isApplying ? (
              <RefreshCw className="h-3.5 w-3.5 mr-1 animate-spin" />
            ) : (
              <Check className="h-3.5 w-3.5 mr-1" />
            )}
            {isApplying ? 'Applying...' : 'Apply Recommendation'}
          </Button>
        </div>
      )}
    </motion.div>
  );
}

export default RecommendationCard;
