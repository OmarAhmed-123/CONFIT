/**
 * CONFIT — Recommendations Panel
 * ==================================
 * Panel displaying predictive alert recommendations within alert preferences.
 * Integrates with the existing AlertPreferencesPanel component.
 */

import { useMemo, useCallback, useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Sparkles,
  RefreshCw,
  Filter,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  CheckCircle2,
  Info,
  X,
  Settings2,
  BarChart3,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuCheckboxItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { RecommendationCard } from './RecommendationCard';
import { useAlertRecommendationStore } from '@/stores/alertRecommendationStore';
import type {
  AlertRecommendation,
  RecommendationType,
  RecommendationStatus,
  ConfidenceLevel,
} from '@/types/alertRecommendationTypes';
import {
  getRecommendationTypeLabel,
} from '@/types/alertRecommendationTypes';
import { DURATION_STANDARD, EASE_LUXURY, createTransition } from '@/motion';

// ─── Panel Props ───────────────────────────────────────────────────────────────

export interface RecommendationsPanelProps {
  storeId: string;
  onRecommendationApplied?: (recommendation: AlertRecommendation) => void;
  className?: string;
  collapsible?: boolean;
  defaultExpanded?: boolean;
  showFilters?: boolean;
  maxVisible?: number;
}

// ─── Empty State Component ────────────────────────────────────────────────────

function EmptyState({ onRefresh }: { onRefresh?: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-8 text-center">
      <div className="w-12 h-12 rounded-full bg-muted/30 flex items-center justify-center mb-4">
        <Sparkles className="h-6 w-6 text-muted-foreground" />
      </div>
      <h4 className="text-sm font-medium text-foreground mb-1">
        No Recommendations Available
      </h4>
      <p className="text-xs text-muted-foreground max-w-[280px]">
        Recommendations are generated based on your store's historical data.
        Check back after more orders are processed.
      </p>
      {onRefresh && (
        <Button
          variant="outline"
          size="sm"
          className="mt-4 h-8 px-3 text-xs"
          onClick={onRefresh}
        >
          <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
          Refresh Analysis
        </Button>
      )}
    </div>
  );
}

// ─── Loading State Component ──────────────────────────────────────────────────

function LoadingState() {
  return (
    <div className="space-y-4">
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className="animate-pulse rounded-xl border border-border/30 bg-surface-elevated/50 p-4"
        >
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-lg bg-muted/30" />
            <div className="flex-1 space-y-2">
              <div className="h-4 bg-muted/30 rounded w-1/3" />
              <div className="h-3 bg-muted/20 rounded w-2/3" />
              <div className="h-3 bg-muted/20 rounded w-1/2" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Summary Stats Component ──────────────────────────────────────────────────

function SummaryStats({
  recommendations,
}: {
  recommendations: AlertRecommendation[];
}) {
  const stats = useMemo(() => {
    const pending = recommendations.filter((r) => r.status === 'pending' || r.status === 'shown');
    const highImpact = pending.filter((r) => r.impact_estimate === 'high' || r.impact_estimate === 'critical');
    const highConfidence = pending.filter((r) => r.confidence === 'high');

    return {
      total: pending.length,
      highImpact: highImpact.length,
      highConfidence: highConfidence.length,
    };
  }, [recommendations]);

  if (stats.total === 0) return null;

  return (
    <div className="flex items-center gap-4 p-3 bg-muted/20 rounded-lg mb-4">
      <div className="flex items-center gap-2">
        <Sparkles className="h-4 w-4 text-gold-400" />
        <span className="text-sm font-medium">
          {stats.total} {stats.total === 1 ? 'Recommendation' : 'Recommendations'}
        </span>
      </div>
      {stats.highImpact > 0 && (
        <div className="flex items-center gap-1.5">
          <AlertTriangle className="h-3.5 w-3.5 text-gold-400" />
          <span className="text-xs text-muted-foreground">
            {stats.highImpact} high impact
          </span>
        </div>
      )}
      {stats.highConfidence > 0 && (
        <div className="flex items-center gap-1.5">
          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
          <span className="text-xs text-muted-foreground">
            {stats.highConfidence} high confidence
          </span>
        </div>
      )}
    </div>
  );
}

// ─── Filter Bar Component ──────────────────────────────────────────────────────

function FilterBar({
  filters,
  onFilterChange,
  onReset,
}: {
  filters: {
    types: RecommendationType[];
    status: RecommendationStatus[];
    confidence: ConfidenceLevel | 'all';
  };
  onFilterChange: (key: string, value: unknown) => void;
  onReset: () => void;
}) {
  const hasActiveFilters = filters.types.length > 0 || filters.status.length > 0 || filters.confidence !== 'all';

  return (
    <div className="flex items-center gap-2 mb-4">
      {/* Type Filter */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" size="sm" className="h-8 px-3 text-xs">
            <Filter className="h-3.5 w-3.5 mr-1.5" />
            Type
            {filters.types.length > 0 && (
              <Badge variant="secondary" className="ml-1.5 h-4 px-1.5 text-[10px]">
                {filters.types.length}
              </Badge>
            )}
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-48">
          {(['return_spike', 'high_value_aov', 'conversion_anomaly', 'inventory_depletion', 'seasonal_adjustment', 'vip_inactivity'] as RecommendationType[]).map(
            (type) => (
              <DropdownMenuCheckboxItem
                key={type}
                checked={filters.types.includes(type)}
                onCheckedChange={(checked) => {
                  const newTypes = checked
                    ? [...filters.types, type]
                    : filters.types.filter((t) => t !== type);
                  onFilterChange('types', newTypes);
                }}
              >
                {getRecommendationTypeLabel(type)}
              </DropdownMenuCheckboxItem>
            )
          )}
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Confidence Filter */}
      <Select
        value={filters.confidence}
        onValueChange={(value) => onFilterChange('confidence', value)}
      >
        <SelectTrigger className="h-8 w-[130px] text-xs">
          <SelectValue placeholder="Confidence" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Confidence</SelectItem>
          <SelectItem value="high">High</SelectItem>
          <SelectItem value="medium">Medium</SelectItem>
          <SelectItem value="low">Low</SelectItem>
        </SelectContent>
      </Select>

      {/* Reset */}
      {hasActiveFilters && (
        <Button
          variant="ghost"
          size="sm"
          className="h-8 px-2 text-xs text-muted-foreground"
          onClick={onReset}
        >
          <X className="h-3.5 w-3.5 mr-1" />
          Clear
        </Button>
      )}
    </div>
  );
}

// ─── Main Panel Component ─────────────────────────────────────────────────────

export function RecommendationsPanel({
  storeId,
  onRecommendationApplied,
  className,
  collapsible = true,
  defaultExpanded = true,
  showFilters = true,
  maxVisible,
}: RecommendationsPanelProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const [applyingId, setApplyingId] = useState<string | null>(null);

  const {
    getFilteredRecommendations,
    isLoading,
    isGenerating,
    error,
    filters,
    setFilters,
    resetFilters,
    setRecommendations,
    updateRecommendation,
    setLoading,
    setGenerating,
    setError,
    isStale,
  } = useAlertRecommendationStore();

  const recommendations = getFilteredRecommendations(storeId);
  const visibleRecommendations = maxVisible
    ? recommendations.slice(0, maxVisible)
    : recommendations;

  // Fetch recommendations on mount or when stale
  useEffect(() => {
    if (storeId && isStale(storeId)) {
      fetchRecommendations();
    }
  }, [storeId]);

  const fetchRecommendations = useCallback(async () => {
    if (!storeId) return;

    setLoading(true, storeId);
    setError(null);

    try {
      const response = await fetch(
        `/api/v1/alert-recommendations/generate`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            store_id: storeId,
            data_window_days: 60,
            force_refresh: false,
          }),
        }
      );

      if (!response.ok) {
        throw new Error('Failed to fetch recommendations');
      }

      const data = await response.json();
      setRecommendations(storeId, data.recommendations);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  }, [storeId, setRecommendations, setLoading, setError]);

  const handleRefresh = useCallback(async () => {
    if (!storeId) return;

    setGenerating(true);
    setError(null);

    try {
      const response = await fetch(
        `/api/v1/alert-recommendations/generate`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            store_id: storeId,
            data_window_days: 60,
            force_refresh: true,
          }),
        }
      );

      if (!response.ok) {
        throw new Error('Failed to refresh recommendations');
      }

      const data = await response.json();
      setRecommendations(storeId, data.recommendations);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setGenerating(false);
    }
  }, [storeId, setRecommendations, setGenerating, setError]);

  const handleApply = useCallback(
    async (recommendation: AlertRecommendation, customThresholds?: Record<string, number>) => {
      setApplyingId(recommendation.id);

      try {
        const response = await fetch(`/api/v1/alert-recommendations/apply`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            recommendation_id: recommendation.id,
            store_id: storeId,
            custom_thresholds: customThresholds,
          }),
        });

        if (!response.ok) {
          throw new Error('Failed to apply recommendation');
        }

        // Update local state
        updateRecommendation(storeId, recommendation.id, {
          status: 'applied',
          applied_at: new Date().toISOString(),
        });

        onRecommendationApplied?.(recommendation);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to apply');
      } finally {
        setApplyingId(null);
      }
    },
    [storeId, updateRecommendation, onRecommendationApplied, setError]
  );

  const handleDismiss = useCallback(
    async (recommendation: AlertRecommendation) => {
      try {
        const response = await fetch(`/api/v1/alert-recommendations/dismiss`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            recommendation_id: recommendation.id,
            store_id: storeId,
          }),
        });

        if (!response.ok) {
          throw new Error('Failed to dismiss recommendation');
        }

        updateRecommendation(storeId, recommendation.id, {
          status: 'dismissed',
          dismissed_at: new Date().toISOString(),
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to dismiss');
      }
    },
    [storeId, updateRecommendation, setError]
  );

  const handleFilterChange = useCallback(
    (key: string, value: unknown) => {
      setFilters({ [key]: value });
    },
    [setFilters]
  );

  const content = (
    <>
      {/* Error State */}
      {error && (
        <div className="flex items-center gap-2 p-3 bg-destructive/10 border border-destructive/30 rounded-lg mb-4">
          <AlertTriangle className="h-4 w-4 text-destructive" />
          <span className="text-sm text-destructive">{error}</span>
          <Button
            variant="ghost"
            size="sm"
            className="ml-auto h-6 px-2 text-xs"
            onClick={() => setError(null)}
          >
            <X className="h-3 w-3" />
          </Button>
        </div>
      )}

      {/* Loading State */}
      {isLoading && <LoadingState />}

      {/* Content */}
      {!isLoading && (
        <>
          {/* Summary Stats */}
          <SummaryStats recommendations={recommendations} />

          {/* Filter Bar */}
          {showFilters && recommendations.length > 1 && (
            <FilterBar
              filters={filters}
              onFilterChange={handleFilterChange}
              onReset={resetFilters}
            />
          )}

          {/* Recommendations List */}
          {recommendations.length > 0 ? (
            <div className="space-y-3">
              <AnimatePresence mode="popLayout">
                {visibleRecommendations.map((rec) => (
                  <RecommendationCard
                    key={rec.id}
                    recommendation={rec}
                    onApply={handleApply}
                    onDismiss={handleDismiss}
                    isApplying={applyingId === rec.id}
                    showBacktest={true}
                  />
                ))}
              </AnimatePresence>

              {/* Show More Button */}
              {maxVisible && recommendations.length > maxVisible && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="w-full h-8 text-xs text-muted-foreground"
                  onClick={() => {}} // Would expand to show all
                >
                  Show {recommendations.length - maxVisible} more
                  <ChevronDown className="h-3.5 w-3.5 ml-1" />
                </Button>
              )}
            </div>
          ) : (
            <EmptyState onRefresh={handleRefresh} />
          )}
        </>
      )}
    </>
  );

  // Non-collapsible version
  if (!collapsible) {
    return (
      <div className={cn('relative', className)}>
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-gold-400" />
            <h3 className="text-lg font-semibold">Smart Recommendations</h3>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="h-8 px-3 text-xs"
            onClick={handleRefresh}
            disabled={isGenerating}
          >
            <RefreshCw
              className={cn('h-3.5 w-3.5 mr-1.5', isGenerating && 'animate-spin')}
            />
            Refresh
          </Button>
        </div>

        {content}
      </div>
    );
  }

  // Collapsible version
  return (
    <Collapsible open={isExpanded} onOpenChange={setIsExpanded} className={className}>
      <div className="flex items-center justify-between">
        <CollapsibleTrigger asChild>
          <button className="flex items-center gap-2 py-2 hover:opacity-80 transition-opacity">
            <Sparkles className="h-5 w-5 text-gold-400" />
            <h3 className="text-lg font-semibold">Smart Recommendations</h3>
            {recommendations.filter((r) => r.status === 'pending').length > 0 && (
              <Badge
                variant="outline"
                className="border-gold-500/50 text-gold-400"
              >
                {recommendations.filter((r) => r.status === 'pending').length} new
              </Badge>
            )}
            {isExpanded ? (
              <ChevronUp className="h-4 w-4 text-muted-foreground" />
            ) : (
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            )}
          </button>
        </CollapsibleTrigger>

        <Button
          variant="ghost"
          size="sm"
          className="h-8 px-2 text-xs"
          onClick={handleRefresh}
          disabled={isGenerating}
        >
          <RefreshCw
            className={cn('h-3.5 w-3.5', isGenerating && 'animate-spin')}
          />
        </Button>
      </div>

      <CollapsibleContent className="mt-4">
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={createTransition({ duration: 0.2 })}
        >
          {content}
        </motion.div>
      </CollapsibleContent>
    </Collapsible>
  );
}

export default RecommendationsPanel;
