/**
 * CONFIT — Sales Analytics Table (Connected)
 * ===========================================
 * Connected version of SoldProductsTable with bidirectional
 * filter synchronization. Wraps the base table with filter store
 * integration and animated transitions.
 *
 * Features:
 * - Automatic data filtering from store
 * - Filter controls integrated with widget
 * - Animated row transitions on filter changes
 * - Empty state with clear filters action
 */

import { memo, useCallback, useMemo, useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  RefreshCw,
  Undo2,
  Redo2,
  Filter,
  X,
  Calendar,
  DollarSign,
  Tag,
  Users,
  Package,
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
import { Slider } from '@/components/ui/slider';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { SoldProductsTable, type SoldProductsTableProps } from './SoldProductsTable';
import {
  useSalesFilterStore,
  useComputedKPIs,
  useSalesFilters,
  useFilterHistory,
  type ActiveFilters,
} from '@/stores';
import { DURATION_LUXURY, EASE_LUXURY } from '@/motion';
import type {
  SaleRecord,
  SaleCategory,
  CustomerSegment,
  ReturnStatus,
} from '@/types/dashboard';

// ─── Types ────────────────────────────────────────────────────────────

export interface SoldProductsTableConnectedProps
  extends Omit<SoldProductsTableProps, 'data' | 'onClearFilters'> {
  /** Raw sales data (will be filtered by active filters) */
  data: SaleRecord[];
  /** Show filter controls above table */
  showFilterControls?: boolean;
  /** Show undo/redo controls */
  showHistoryControls?: boolean;
  /** Show active filter chips */
  showFilterChips?: boolean;
  /** Additional CSS class */
  className?: string;
}

// ─── Filter Control Components ────────────────────────────────────────

interface FilterControlProps {
  label: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
}

function FilterControl({ label, icon, children }: FilterControlProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
        {icon}
        {label}
      </label>
      {children}
    </div>
  );
}

// ─── Category Filter ──────────────────────────────────────────────────

const CATEGORIES: SaleCategory[] = ['Clothes', 'Shoes', 'Accessories', 'Full Outfit'];

function CategoryFilter() {
  const { activeFilters, toggleCategory } = useSalesFilters();
  const selected = activeFilters.categories || [];

  return (
    <FilterControl label="Category" icon={<Tag className="h-3 w-3" />}>
      <div className="flex flex-wrap gap-1.5">
        {CATEGORIES.map((cat) => {
          const isSelected = selected.includes(cat);
          return (
            <Badge
              key={cat}
              variant={isSelected ? 'default' : 'outline'}
              className={cn(
                'cursor-pointer text-xs transition-colors',
                isSelected
                  ? 'bg-accent text-accent-foreground hover:bg-accent/90'
                  : 'hover:bg-accent/10'
              )}
              onClick={() => toggleCategory(cat)}
            >
              {cat}
            </Badge>
          );
        })}
      </div>
    </FilterControl>
  );
}

// ─── Customer Segment Filter ──────────────────────────────────────────

const SEGMENTS: CustomerSegment[] = ['New Customer', 'Returning', 'VIP', 'Wholesale'];

function CustomerSegmentFilter() {
  const { activeFilters, toggleCustomerSegment } = useSalesFilters();
  const selected = activeFilters.customerSegments || [];

  return (
    <FilterControl label="Customer Segment" icon={<Users className="h-3 w-3" />}>
      <div className="flex flex-wrap gap-1.5">
        {SEGMENTS.map((seg) => {
          const isSelected = selected.includes(seg);
          return (
            <Badge
              key={seg}
              variant={isSelected ? 'default' : 'outline'}
              className={cn(
                'cursor-pointer text-xs transition-colors',
                isSelected
                  ? 'bg-accent text-accent-foreground hover:bg-accent/90'
                  : 'hover:bg-accent/10'
              )}
              onClick={() => toggleCustomerSegment(seg as CustomerSegment)}
            >
              {seg}
            </Badge>
          );
        })}
      </div>
    </FilterControl>
  );
}

// ─── Price Range Filter ───────────────────────────────────────────────

function PriceRangeFilter() {
  const { activeFilters, setPriceRange } = useSalesFilters();
  const [localRange, setLocalRange] = useState<[number, number]>([
    activeFilters.priceRange?.min ?? 0,
    activeFilters.priceRange?.max ?? 50000,
  ]);

  // Sync with store
  useEffect(() => {
    if (activeFilters.priceRange) {
      setLocalRange([activeFilters.priceRange.min, activeFilters.priceRange.max]);
    }
  }, [activeFilters.priceRange]);

  const handleCommit = useCallback(
    (value: [number, number]) => {
      setPriceRange(value[0], value[1]);
    },
    [setPriceRange]
  );

  return (
    <FilterControl label="Price Range" icon={<DollarSign className="h-3 w-3" />}>
      <div className="w-48 space-y-2">
        <Slider
          value={localRange}
          min={0}
          max={50000}
          step={100}
          onValueChange={(v) => setLocalRange(v as [number, number])}
          onValueCommit={(v) => handleCommit(v as [number, number])}
          className="w-full"
        />
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>EGP {localRange[0].toLocaleString()}</span>
          <span>EGP {localRange[1].toLocaleString()}</span>
        </div>
      </div>
    </FilterControl>
  );
}

// ─── Filter Chips Component ────────────────────────────────────────────

function FilterChips() {
  const { getFilterChips, clearFilter, clearAllFilters } = useSalesFilters();
  const chips = getFilterChips();

  if (chips.length === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: -5 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -5 }}
      className="flex flex-wrap items-center gap-2 mb-4"
    >
      <span className="text-xs text-muted-foreground">Active filters:</span>
      {chips.map((chip) => (
        <Badge
          key={chip.key}
          variant="secondary"
          className="gap-1 pr-1 text-xs bg-accent/10 text-accent border-accent/20"
        >
          {chip.label}
          <button
            onClick={() => clearFilter(chip.type)}
            className="ml-1 rounded-full hover:bg-accent/20 p-0.5"
            aria-label={`Remove ${chip.label} filter`}
          >
            <X className="h-3 w-3" />
          </button>
        </Badge>
      ))}
      <Button
        variant="ghost"
        size="sm"
        onClick={clearAllFilters}
        className="h-6 text-xs text-muted-foreground hover:text-foreground"
      >
        Clear all
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

// ─── Filter Controls Bar ───────────────────────────────────────────────

function FilterControlsBar() {
  return (
    <div className="flex items-center gap-4 mb-4 p-4 rounded-lg border border-border/50 bg-surface-elevated/50">
      <CategoryFilter />
      <CustomerSegmentFilter />
      <PriceRangeFilter />

      <div className="ml-auto">
        <HistoryControls />
      </div>
    </div>
  );
}

// ─── Main Connected Table ──────────────────────────────────────────────

function SoldProductsTableConnectedBase({
  data,
  isLoading = false,
  error = null,
  onRetry,
  highlightedRowId,
  recentSaleIds,
  showFilterControls = true,
  showHistoryControls = true,
  showFilterChips = true,
  className,
}: SoldProductsTableConnectedProps) {
  // Set raw data in store
  const setRawData = useSalesFilterStore((s) => s.setRawData);

  // Get filtered data
  const { filteredData } = useComputedKPIs();

  // Filter state
  const { clearAllFilters, hasActiveFilters } = useSalesFilters();

  // Update raw data when prop changes
  useMemo(() => {
    if (data && data.length > 0) {
      setRawData(data);
    }
  }, [data, setRawData]);

  // Handle clear all filters
  const handleClearFilters = useCallback(() => {
    clearAllFilters();
  }, [clearAllFilters]);

  // Animation key based on filter state
  const hasFilters = hasActiveFilters();

  return (
    <div className={cn('relative', className)}>
      {/* Filter Controls */}
      {showFilterControls && <FilterControlsBar />}

      {/* Filter Chips */}
      {showFilterChips && (
        <AnimatePresence>
          {hasFilters && <FilterChips />}
        </AnimatePresence>
      )}

      {/* Table with filtered data */}
      <motion.div
        key={`table-${hasFilters ? 'filtered' : 'all'}`}
        initial={{ opacity: 0.95 }}
        animate={{ opacity: 1 }}
        transition={{ duration: DURATION_LUXURY, ease: EASE_LUXURY }}
      >
        <SoldProductsTable
          data={filteredData}
          isLoading={isLoading}
          error={error}
          onRetry={onRetry}
          highlightedRowId={highlightedRowId}
          recentSaleIds={recentSaleIds}
          onClearFilters={hasFilters ? handleClearFilters : undefined}
        />
      </motion.div>
    </div>
  );
}

// Export memoized component
export const SoldProductsTableConnected = memo(SoldProductsTableConnectedBase);

// ─── Exports ───────────────────────────────────────────────────────────

export {
  CategoryFilter,
  CustomerSegmentFilter,
  PriceRangeFilter,
  FilterChips,
  HistoryControls,
};

export default SoldProductsTableConnected;
