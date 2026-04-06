/**
 * CONFIT — A/B Test Analytics Dashboard
 * =======================================
 * Dashboard for product team to monitor recommendation A/B test results.
 * Displays experiment metrics, significance, and recommendations.
 */

import { useMemo, useCallback, useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FlaskConical,
  Users,
  TrendingUp,
  TrendingDown,
  Minus,
  Check,
  X,
  AlertTriangle,
  BarChart3,
  Clock,
  Sparkles,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Play,
  Pause,
  Square,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import type {
  ABTestExperiment,
  ABTestReport,
  ABTestMetrics,
} from '@/types/alertRecommendationTypes';
import { DURATION_STANDARD, EASE_LUXURY, createTransition } from '@/motion';

// ─── Helper Functions ─────────────────────────────────────────────────────────

function formatPercent(value: number | undefined | null): string {
  if (value === undefined || value === null) return '—';
  return `${(value * 100).toFixed(1)}%`;
}

function formatNumber(value: number | undefined | null): string {
  if (value === undefined || value === null) return '—';
  return value.toLocaleString();
}

function formatDuration(days: number): string {
  if (days < 7) return `${days} days`;
  if (days < 30) return `${Math.floor(days / 7)} weeks`;
  return `${Math.floor(days / 30)} months`;
}

function getSignificanceColor(pValue: number | undefined): string {
  if (pValue === undefined) return 'text-muted-foreground';
  if (pValue < 0.01) return 'text-emerald-400';
  if (pValue < 0.05) return 'text-purple-400';
  return 'text-muted-foreground';
}

function getSignificanceLabel(pValue: number | undefined): string {
  if (pValue === undefined) return 'Not enough data';
  if (pValue < 0.01) return 'Highly Significant';
  if (pValue < 0.05) return 'Significant';
  return 'Not Significant';
}

// ─── Metric Comparison Component ─────────────────────────────────────────────

function MetricComparison({
  label,
  controlValue,
  treatmentValue,
  format = 'number',
  isLowerBetter = false,
}: {
  label: string;
  controlValue: number | undefined;
  treatmentValue: number | undefined;
  format?: 'number' | 'percent' | 'seconds';
  isLowerBetter?: boolean;
}) {
  const formatValue = (v: number | undefined) => {
    if (v === undefined) return '—';
    if (format === 'percent') return formatPercent(v);
    if (format === 'seconds') return `${Math.round(v)}s`;
    return formatNumber(v);
  };

  const diff = useMemo(() => {
    if (controlValue === undefined || treatmentValue === undefined) return null;
    if (controlValue === 0) return null;
    return ((treatmentValue - controlValue) / controlValue) * 100;
  }, [controlValue, treatmentValue]);

  const isPositive = diff !== null && diff > 0;
  const isNegative = diff !== null && diff < 0;
  const isGood = isLowerBetter ? isNegative : isPositive;

  return (
    <div className="flex items-center justify-between py-2 border-b border-border/30 last:border-0">
      <span className="text-sm text-muted-foreground">{label}</span>
      <div className="flex items-center gap-4">
        <span className="text-sm font-medium w-16 text-right">
          {formatValue(controlValue)}
        </span>
        <span className="text-sm font-medium w-16 text-right text-purple-400">
          {formatValue(treatmentValue)}
        </span>
        {diff !== null && (
          <div
            className={cn(
              'flex items-center gap-1 w-16 justify-end',
              isGood ? 'text-emerald-400' : 'text-gold-400'
            )}
          >
            {isPositive ? (
              <TrendingUp className="h-3 w-3" />
            ) : isNegative ? (
              <TrendingDown className="h-3 w-3" />
            ) : (
              <Minus className="h-3 w-3" />
            )}
            <span className="text-xs font-medium">
              {isPositive ? '+' : ''}
              {diff.toFixed(1)}%
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Experiment Card Component ───────────────────────────────────────────────

function ExperimentCard({
  experiment,
  report,
  onRefresh,
}: {
  experiment: ABTestExperiment;
  report?: ABTestReport;
  onRefresh?: () => void;
}) {
  const [isExpanded, setIsExpanded] = useState(false);

  const statusBadge = useMemo(() => {
    if (!experiment.is_active) {
      return (
        <Badge variant="outline" className="border-muted text-muted-foreground">
          <Square className="h-3 w-3 mr-1" />
          Completed
        </Badge>
      );
    }
    if (experiment.is_paused) {
      return (
        <Badge variant="outline" className="border-gold-500/50 text-gold-400">
          <Pause className="h-3 w-3 mr-1" />
          Paused
        </Badge>
      );
    }
    return (
      <Badge variant="outline" className="border-emerald-500/50 text-emerald-400">
        <Play className="h-3 w-3 mr-1" />
        Active
      </Badge>
    );
  }, [experiment.is_active, experiment.is_paused]);

  const significance = report?.significance;

  return (
    <Card className="bg-surface-elevated/50 border-border/30">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <FlaskConical className="h-5 w-5 text-purple-400" />
            <div>
              <CardTitle className="text-base">{experiment.name}</CardTitle>
              <p className="text-xs text-muted-foreground mt-0.5">
                {experiment.description || 'No description'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {statusBadge}
            {significance?.is_significant && (
              <Badge className="bg-emerald-500/20 text-emerald-400 border-emerald-500/30">
                <Check className="h-3 w-3 mr-1" />
                Significant
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent>
        {/* Quick Stats */}
        <div className="grid grid-cols-4 gap-4 mb-4">
          <div className="text-center">
            <p className="text-2xl font-bold text-foreground">
              {experiment.control_group_size + experiment.treatment_group_size}
            </p>
            <p className="text-xs text-muted-foreground">Total Stores</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-purple-400">
              {formatDuration(report?.duration_days || 0)}
            </p>
            <p className="text-xs text-muted-foreground">Duration</p>
          </div>
          <div className="text-center">
            <p className={cn('text-2xl font-bold', getSignificanceColor(significance?.p_value))}>
              {significance?.p_value ? significance.p_value.toFixed(3) : '—'}
            </p>
            <p className="text-xs text-muted-foreground">P-Value</p>
          </div>
          <div className="text-center">
            <p
              className={cn(
                'text-2xl font-bold',
                (significance?.relative_lift || 0) > 0 ? 'text-emerald-400' : 'text-gold-400'
              )}
            >
              {significance?.relative_lift ? `${significance.relative_lift > 0 ? '+' : ''}${significance.relative_lift}%` : '—'}
            </p>
            <p className="text-xs text-muted-foreground">Relative Lift</p>
          </div>
        </div>

        {/* Collapsible Details */}
        <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
          <CollapsibleTrigger asChild>
            <button className="flex items-center justify-center gap-2 w-full py-2 text-xs text-muted-foreground hover:text-foreground transition-colors">
              <BarChart3 className="h-3.5 w-3.5" />
              <span>Detailed Metrics</span>
              {isExpanded ? (
                <ChevronUp className="h-3.5 w-3.5" />
              ) : (
                <ChevronDown className="h-3.5 w-3.5" />
              )}
            </button>
          </CollapsibleTrigger>

          <CollapsibleContent>
            <div className="mt-4 p-4 bg-muted/20 rounded-lg">
              {/* Header Row */}
              <div className="flex items-center justify-between mb-2 text-xs font-medium text-muted-foreground">
                <span>Metric</span>
                <div className="flex items-center gap-4">
                  <span className="w-16 text-right">Control</span>
                  <span className="w-16 text-right">Treatment</span>
                  <span className="w-16 text-right">Change</span>
                </div>
              </div>

              {/* Metrics */}
              <div className="space-y-1">
                <MetricComparison
                  label="Recommendations Shown"
                  controlValue={report?.control_group.metrics.recommendations_shown}
                  treatmentValue={report?.treatment_group.metrics.recommendations_shown}
                />
                <MetricComparison
                  label="Adoption Rate"
                  controlValue={report?.control_group.metrics.recommendation_adoption_rate}
                  treatmentValue={report?.treatment_group.metrics.recommendation_adoption_rate}
                  format="percent"
                />
                <MetricComparison
                  label="Avg Time to Accept"
                  controlValue={report?.control_group.metrics.avg_time_to_accept_seconds}
                  treatmentValue={report?.treatment_group.metrics.avg_time_to_accept_seconds}
                  format="seconds"
                  isLowerBetter
                />
                <MetricComparison
                  label="Alert Actionability"
                  controlValue={report?.control_group.metrics.alert_actionability_rate}
                  treatmentValue={report?.treatment_group.metrics.alert_actionability_rate}
                  format="percent"
                />
                <MetricComparison
                  label="Manual Threshold Changes"
                  controlValue={report?.control_group.metrics.manual_threshold_changes}
                  treatmentValue={report?.treatment_group.metrics.manual_threshold_changes}
                  isLowerBetter
                />
              </div>

              {/* Recommendations */}
              {report?.recommendations && report.recommendations.length > 0 && (
                <div className="mt-4 pt-4 border-t border-border/30">
                  <h4 className="text-xs font-medium text-muted-foreground mb-2">
                    Recommendations
                  </h4>
                  <ul className="space-y-1">
                    {report.recommendations.map((rec, idx) => (
                      <li
                        key={idx}
                        className="flex items-start gap-2 text-sm text-foreground"
                      >
                        <Sparkles className="h-3.5 w-3.5 text-gold-400 mt-0.5 flex-shrink-0" />
                        <span>{rec}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </CollapsibleContent>
        </Collapsible>
      </CardContent>
    </Card>
  );
}

// ─── Main Dashboard Component ────────────────────────────────────────────────

export interface ABTestDashboardProps {
  className?: string;
}

export function ABTestDashboard({ className }: ABTestDashboardProps) {
  const [experiments, setExperiments] = useState<ABTestExperiment[]>([]);
  const [reports, setReports] = useState<Record<string, ABTestReport>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      // Fetch experiments summary
      const summaryResponse = await fetch('/api/v1/alert-recommendations/ab-test/summary');
      if (!summaryResponse.ok) throw new Error('Failed to fetch experiments');

      const summary = await summaryResponse.json();
      setExperiments(summary.experiments || []);

      // Fetch reports for each experiment
      const reportPromises = summary.experiments.map(async (exp: ABTestExperiment) => {
        const reportResponse = await fetch(
          `/api/v1/alert-recommendations/ab-test/report/${exp.id}`
        );
        if (reportResponse.ok) {
          const report = await reportResponse.json();
          return { id: exp.id, report };
        }
        return null;
      });

      const reportResults = await Promise.all(reportPromises);
      const reportMap: Record<string, ABTestReport> = {};
      reportResults.forEach((result) => {
        if (result) {
          reportMap[result.id] = result.report;
        }
      });
      setReports(reportMap);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Summary stats
  const summaryStats = useMemo(() => {
    const active = experiments.filter((e) => e.is_active && !e.is_paused);
    const significant = experiments.filter((e) => e.is_significant);
    const totalStores = experiments.reduce(
      (sum, e) => sum + e.control_group_size + e.treatment_group_size,
      0
    );

    return {
      total: experiments.length,
      active: active.length,
      significant: significant.length,
      totalStores,
    };
  }, [experiments]);

  return (
    <div className={cn('space-y-6', className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <FlaskConical className="h-6 w-6 text-purple-400" />
          <div>
            <h2 className="text-xl font-semibold">A/B Test Analytics</h2>
            <p className="text-sm text-muted-foreground">
              Monitor recommendation effectiveness experiments
            </p>
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="h-8 px-3"
          onClick={fetchData}
          disabled={isLoading}
        >
          <RefreshCw className={cn('h-3.5 w-3.5 mr-1.5', isLoading && 'animate-spin')} />
          Refresh
        </Button>
      </div>

      {/* Error State */}
      {error && (
        <div className="flex items-center gap-2 p-4 bg-destructive/10 border border-destructive/30 rounded-lg">
          <AlertTriangle className="h-4 w-4 text-destructive" />
          <span className="text-sm text-destructive">{error}</span>
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-4">
        <Card className="bg-surface-elevated/50 border-border/30">
          <CardContent className="pt-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center">
                <FlaskConical className="h-5 w-5 text-purple-400" />
              </div>
              <div>
                <p className="text-2xl font-bold">{summaryStats.total}</p>
                <p className="text-xs text-muted-foreground">Total Experiments</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-surface-elevated/50 border-border/30">
          <CardContent className="pt-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-emerald-500/20 flex items-center justify-center">
                <Play className="h-5 w-5 text-emerald-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-emerald-400">{summaryStats.active}</p>
                <p className="text-xs text-muted-foreground">Active</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-surface-elevated/50 border-border/30">
          <CardContent className="pt-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-gold-500/20 flex items-center justify-center">
                <Check className="h-5 w-5 text-gold-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gold-400">{summaryStats.significant}</p>
                <p className="text-xs text-muted-foreground">Significant</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-surface-elevated/50 border-border/30">
          <CardContent className="pt-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center">
                <Users className="h-5 w-5 text-purple-400" />
              </div>
              <div>
                <p className="text-2xl font-bold">{summaryStats.totalStores}</p>
                <p className="text-xs text-muted-foreground">Stores in Tests</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="space-y-4">
          {[1, 2].map((i) => (
            <div
              key={i}
              className="animate-pulse rounded-xl border border-border/30 bg-surface-elevated/50 p-6"
            >
              <div className="flex items-center gap-4 mb-4">
                <div className="w-10 h-10 rounded-lg bg-muted/30" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-muted/30 rounded w-1/3" />
                  <div className="h-3 bg-muted/20 rounded w-1/2" />
                </div>
              </div>
              <div className="grid grid-cols-4 gap-4">
                {[1, 2, 3, 4].map((j) => (
                  <div key={j} className="text-center">
                    <div className="h-8 bg-muted/30 rounded mx-auto w-16 mb-2" />
                    <div className="h-3 bg-muted/20 rounded mx-auto w-12" />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Experiments List */}
      {!isLoading && experiments.length > 0 && (
        <div className="space-y-4">
          <AnimatePresence mode="popLayout">
            {experiments.map((experiment) => (
              <motion.div
                key={experiment.id}
                layout
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={createTransition({ duration: 0.2 })}
              >
                <ExperimentCard
                  experiment={experiment}
                  report={reports[experiment.id]}
                  onRefresh={fetchData}
                />
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && experiments.length === 0 && (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <div className="w-16 h-16 rounded-full bg-muted/30 flex items-center justify-center mb-4">
            <FlaskConical className="h-8 w-8 text-muted-foreground" />
          </div>
          <h3 className="text-lg font-medium mb-1">No Experiments</h3>
          <p className="text-sm text-muted-foreground max-w-[320px]">
            No A/B test experiments have been created yet. Create one to start
            measuring recommendation effectiveness.
          </p>
        </div>
      )}
    </div>
  );
}

export default ABTestDashboard;
