/**
 * CONFIT — Sales Insights Widget (Connected)
 * ===========================================
 * Connected version of SalesInsightsWidget with bidirectional
 * filter synchronization. Wraps the base widget with filter store
 * integration and animated transitions.
 *
 * Features:
 * - Automatic KPI recalculation from filter store
 * - Drill-down actions that sync to table
 * - Animated metric transitions
 * - Empty state with clear filters action
 */

import { memo, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { RefreshCw, Undo2, Redo2, Filter } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { SalesInsightsWidget, type DrillDownFilters } from './SalesInsightsWidget';
import {
  useSalesFilterStore,
  useComputedKPIs,
  useSalesFilters,
  useFilterHistory,
  type ComputedKPIs,
} from '@/stores';
import { DURATION_LUXURY, EASE_LUXURY } from '@/motion';
import type { SaleRecord, SaleCategory, ReturnStatus } from '@/types/dashboard';

// ─── Types ────────────────────────────────────────────────────────────

export interface SalesInsightsWidgetConnectedProps {
  /** Raw sales data (will be filtered by active filters) */
  data: SaleRecord[];
  /** Show loading skeleton */
  isLoading?: boolean;
  /** Error message to display */
  error?: string | null;
  /** Additional CSS class */
  className?: string;
  /** Show undo/redo controls */
  showHistoryControls?: boolean;
  /** Show active filter indicator */
  showFilterIndicator?: boolean;
  /** Custom onDrillDown handler (in addition to store sync) */
  onDrillDown?: (filters: DrillDownFilters) => void;
}

// ─── Filter Indicator Component ───────────────────────────────────────

function FilterIndicator({
  filterCount,
  onClearAll,
}: {
  filterCount: number;
  onClearAll: () => void;
}) {
  if (filterCount === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="flex items-center justify-between px-4 py-2 mb-4 rounded-lg bg-accent/10 border border-accent/20"
    >
      <div className="flex items-center gap-2 text-sm">
        <Filter className="h-4 w-4 text-accent" />
        <span className="text-accent font-medium">
          {filterCount} filter{filterCount !== 1 ? 's' : ''} active
        </span>
      </div>
      <Button
        variant="ghost"
        size="sm"
        onClick={onClearAll}
        className="h-7 text-xs text-accent hover:text-accent hover:bg-accent/10"
      >
        <RefreshCw className="h-3 w-3 mr-1" />
        Clear All
      </Button>
    </motion.div>
  );
}

// ─── History Controls Component ────────────────────────────────────────

function HistoryControls() {
  const { undo, redo, canUndo, canRedo } = useFilterHistory();

  return (
    <div className="flex items-center gap-1">
      <Button
        variant="ghost"
        size="icon"
        onClick={undo}
        disabled={!canUndo}
        className="h-8 w-8 text-muted-foreground hover:text-foreground"
        title="Undo filter change"
      >
        <Undo2 className="h-4 w-4" />
      </Button>
      <Button
        variant="ghost"
        size="icon"
        onClick={redo}
        disabled={!canRedo}
        className="h-8 w-8 text-muted-foreground hover:text-foreground"
        title="Redo filter change"
      >
        <Redo2 className="h-4 w-4" />
      </Button>
    </div>
  );
}

// ─── Animated KPI Wrapper ──────────────────────────────────────────────

interface AnimatedValueProps {
  value: number | string;
  formatFn?: (value: number) => string;
  className?: string;
}

function AnimatedValue({ value, formatFn, className }: AnimatedValueProps) {
  const displayValue = typeof value === 'number' && formatFn ? formatFn(value) : String(value);

  return (
    <motion.span
      key={String(value)}
      initial={{ opacity: 0, y: 5 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: EASE_LUXURY }}
      className={className}
    >
      {displayValue}
    </motion.span>
  );
}

// ─── Main Connected Widget ─────────────────────────────────────────────

function SalesInsightsWidgetConnectedBase({
  data,
  isLoading = false,
  error = null,
  className,
  showHistoryControls = true,
  showFilterIndicator = true,
  onDrillDown,
}: SalesInsightsWidgetConnectedProps) {
  // Set raw data in store
  const setRawData = useSalesFilterStore((s) => s.setRawData);

  // Get filtered data and KPIs
  const { filteredData, kpis } = useComputedKPIs();

  // Filter state
  const { activeFilters, clearAllFilters, hasActiveFilters, getActiveFilterCount } = useSalesFilters();

  // Update raw data when prop changes
  useMemo(() => {
    if (data && data.length > 0) {
      setRawData(data);
    }
  }, [data, setRawData]);

  // Handle drill-down from widget
  const handleDrillDown = useCallback(
    (filters: DrillDownFilters) => {
      const store = useSalesFilterStore.getState();

      // Product name drill-down
      if (filters.productName) {
        store.setProductName(filters.productName);
      }

      // Category drill-down (additive)
      if (filters.category) {
        const current = store.activeFilters.categories || [];
        store.updateFilter(
          'categories',
          current.includes(filters.category)
            ? current.filter((c) => c !== filters.category)
            : [...current, filters.category],
          'widget'
        );
      }

      // Date segment drill-down
      if (filters.dateSegment) {
        store.updateFilter('dateRange', filters.dateSegment, 'widget');
      }

      // Margin range drill-down
      if (filters.marginRange) {
        store.setMarginRange(filters.marginRange);
      }

      // Return status drill-down
      if (filters.returnStatus && filters.returnStatus.length > 0) {
        store.setReturnStatuses(filters.returnStatus);
      }

      // Call external handler
      onDrillDown?.(filters);
    },
    [onDrillDown]
  );

  // Handle clear all filters
  const handleClearAll = useCallback(() => {
    clearAllFilters();
  }, [clearAllFilters]);

  // Filter count
  const filterCount = getActiveFilterCount();
  const hasFilters = hasActiveFilters();

  return (
    <div className={cn('relative', className)}>
      {/* Filter Indicator */}
      {showFilterIndicator && (
        <AnimatePresence>
          {hasFilters && <FilterIndicator filterCount={filterCount} onClearAll={handleClearAll} />}
        </AnimatePresence>
      )}

      {/* History Controls */}
      {showHistoryControls && (
        <div className="flex justify-end mb-2">
          <HistoryControls />
        </div>
      )}

      {/* Widget with filtered data */}
      <motion.div
        key={`widget-${filterCount}`}
        initial={{ opacity: 0.95 }}
        animate={{ opacity: 1 }}
        transition={{ duration: DURATION_LUXURY, ease: EASE_LUXURY }}
      >
        <SalesInsightsWidget
          data={filteredData}
          isLoading={isLoading}
          error={error}
          onDrillDown={handleDrillDown}
        />
      </motion.div>

      {/* Empty State with Clear Filters */}
      {!isLoading && !error && filteredData.length === 0 && data.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: DURATION_LUXURY, ease: EASE_LUXURY }}
          className="col-span-full rounded-2xl border border-border/50 bg-surface-elevated/50 backdrop-blur-xl p-12 text-center"
        >
          <div className="h-16 w-16 rounded-2xl bg-muted/20 flex items-center justify-center mx-auto mb-4">
            <Filter className="h-8 w-8 text-muted-foreground/40" />
          </div>
          <h3 className="text-lg font-semibold text-foreground mb-2 font-sans">
            No sales match your filters
          </h3>
          <p className="text-sm text-muted-foreground max-w-sm mx-auto mb-6">
            Try adjusting your filter criteria or clear all filters to see all sales data.
          </p>
          {hasFilters && (
            <Button
              onClick={handleClearAll}
              variant="outline"
              size="sm"
              className="gap-2 border-accent/30 text-accent hover:bg-accent/10"
            >
              <RefreshCw className="h-4 w-4" />
              Clear All Filters
            </Button>
          )}
        </motion.div>
      )}
    </div>
  );
}

// Export memoized component
export const SalesInsightsWidgetConnected = memo(SalesInsightsWidgetConnectedBase);

// ─── Exports ───────────────────────────────────────────────────────────

export { AnimatedValue };
export default SalesInsightsWidgetConnected;
