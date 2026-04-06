/**
 * CONFIT — Sales Filter Sync Hook
 * ==================================
 * Bidirectional synchronization hook for Sales Insights Widget
 * and Sales Analytics Table. Enables real-time filter updates
 * and KPI recalculation across both components.
 *
 * Features:
 * - Automatic KPI recalculation on filter changes
 * - Drill-down support from widget to table
 * - Debounced updates for large datasets
 * - Animated transition triggers
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  useSalesFilterStore,
  useComputedKPIs,
  useSalesFilters,
  useFilterHistory,
  type ActiveFilters,
} from '@/stores';
import type { SaleRecord, SaleCategory, ReturnStatus } from '@/types/dashboard';

// ─── Types ────────────────────────────────────────────────────────────

export interface DrillDownAction {
  type: 'productName' | 'category' | 'dateSegment' | 'marginRange' | 'returnStatus';
  value: unknown;
}

export interface UseSalesFilterSyncOptions {
  /** Raw sales data to filter */
  rawData: SaleRecord[];
  /** Enable debouncing for large datasets */
  enableDebounce?: boolean;
  /** Debounce delay in ms (default: 150ms) */
  debounceDelay?: number;
  /** Callback when filters change */
  onFiltersChange?: (filters: ActiveFilters, filteredData: SaleRecord[]) => void;
  /** Callback when KPIs are recalculated */
  onKPIsRecalculated?: (kpis: ReturnType<typeof useComputedKPIs>['kpis']) => void;
}

export interface UseSalesFilterSyncReturn {
  // Filtered data
  filteredData: SaleRecord[];

  // Computed KPIs
  kpis: ReturnType<typeof useComputedKPIs>['kpis'];

  // Filter state and actions
  activeFilters: ActiveFilters;
  hasActiveFilters: boolean;
  activeFilterCount: number;
  filterChips: Array<{ key: string; label: string; type: keyof ActiveFilters }>;

  // Update actions
  updateFilter: <K extends keyof ActiveFilters>(
    filterType: K,
    value: ActiveFilters[K]
  ) => void;
  updateFilters: (updates: Partial<ActiveFilters>) => void;
  clearFilter: (filterType: keyof ActiveFilters) => void;
  clearAllFilters: () => void;

  // Drill-down actions (from widget)
  drillDownByProduct: (productName: string) => void;
  drillDownByCategory: (category: SaleCategory) => void;
  drillDownByDateSegment: (start: string, end: string) => void;
  drillDownByMarginRange: (range: 'high' | 'healthy' | 'atRisk') => void;
  drillDownByReturnStatus: (statuses: ReturnStatus[]) => void;

  // Undo/Redo
  undo: () => void;
  redo: () => void;
  canUndo: boolean;
  canRedo: boolean;

  // Loading state
  isLoading: boolean;
  setLoading: (loading: boolean) => void;

  // Animation triggers
  isTransitioning: boolean;
  transitionKey: number;
}

// ─── Debounce Hook ────────────────────────────────────────────────────

function useDebouncedValue<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debouncedValue;
}

// ─── Main Hook ─────────────────────────────────────────────────────────

export function useSalesFilterSync(
  options: UseSalesFilterSyncOptions
): UseSalesFilterSyncReturn {
  const {
    rawData,
    enableDebounce = false,
    debounceDelay = 150,
    onFiltersChange,
    onKPIsRecalculated,
  } = options;

  // Store actions
  const setRawData = useSalesFilterStore((s) => s.setRawData);
  const setLoading = useSalesFilterStore((s) => s.setLoading);
  const isLoading = useSalesFilterStore((s) => s.isLoading);

  // Filter state
  const {
    activeFilters,
    updateFilter,
    updateFilters,
    clearFilter,
    clearAllFilters,
    hasActiveFilters,
    getActiveFilterCount,
    getFilterChips,
  } = useSalesFilters();

  // Computed KPIs
  const { kpis, filteredData } = useComputedKPIs();

  // History
  const { undo, redo, canUndo, canRedo } = useFilterHistory();

  // Animation state
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [transitionKey, setTransitionKey] = useState(0);

  // Track previous filter count for animation trigger
  const prevFilterCountRef = useRef(0);

  // Set raw data when provided
  useEffect(() => {
    if (rawData && rawData.length > 0) {
      setRawData(rawData);
    }
  }, [rawData, setRawData]);

  // Debounced filters for large datasets
  const debouncedFilters = enableDebounce
    ? useDebouncedValue(activeFilters, debounceDelay)
    : activeFilters;

  // Notify on filter changes
  useEffect(() => {
    if (onFiltersChange && filteredData) {
      onFiltersChange(debouncedFilters, filteredData);
    }
  }, [debouncedFilters, filteredData, onFiltersChange]);

  // Notify on KPI recalculation
  useEffect(() => {
    if (onKPIsRecalculated && kpis) {
      onKPIsRecalculated(kpis);
    }
  }, [kpis, onKPIsRecalculated]);

  // Trigger transition animation on filter changes
  useEffect(() => {
    const currentCount = getActiveFilterCount();
    if (currentCount !== prevFilterCountRef.current) {
      setIsTransitioning(true);
      setTransitionKey((k) => k + 1);

      // Reset transition after animation completes
      const timer = setTimeout(() => setIsTransitioning(false), 300);
      prevFilterCountRef.current = currentCount;

      return () => clearTimeout(timer);
    }
  }, [activeFilters, getActiveFilterCount]);

  // ─── Drill-Down Actions ──────────────────────────────────────────────

  const drillDownByProduct = useCallback(
    (productName: string) => {
      updateFilter('productName', productName, 'widget');
    },
    [updateFilter]
  );

  const drillDownByCategory = useCallback(
    (category: SaleCategory) => {
      // Toggle category (additive)
      const current = activeFilters.categories || [];
      const exists = current.includes(category);
      updateFilter(
        'categories',
        exists ? current.filter((c) => c !== category) : [...current, category],
        'widget'
      );
    },
    [activeFilters.categories, updateFilter]
  );

  const drillDownByDateSegment = useCallback(
    (start: string, end: string) => {
      updateFilter('dateRange', { start, end }, 'widget');
    },
    [updateFilter]
  );

  const drillDownByMarginRange = useCallback(
    (range: 'high' | 'healthy' | 'atRisk') => {
      updateFilter('marginRange', range, 'widget');
    },
    [updateFilter]
  );

  const drillDownByReturnStatus = useCallback(
    (statuses: ReturnStatus[]) => {
      updateFilter('returnStatuses', statuses, 'widget');
    },
    [updateFilter]
  );

  // Filter chips
  const filterChips = useMemo(() => getFilterChips(), [getFilterChips]);
  const activeFilterCount = useMemo(() => getActiveFilterCount(), [getActiveFilterCount]);

  return {
    // Data
    filteredData,
    kpis,

    // Filter state
    activeFilters,
    hasActiveFilters: hasActiveFilters(),
    activeFilterCount,
    filterChips,

    // Update actions
    updateFilter,
    updateFilters,
    clearFilter,
    clearAllFilters,

    // Drill-down
    drillDownByProduct,
    drillDownByCategory,
    drillDownByDateSegment,
    drillDownByMarginRange,
    drillDownByReturnStatus,

    // History
    undo,
    redo,
    canUndo: canUndo(),
    canRedo: canRedo(),

    // Loading
    isLoading,
    setLoading,

    // Animation
    isTransitioning,
    transitionKey,
  };
}

// ─── Widget Integration Hook ──────────────────────────────────────────

export interface UseWidgetDrillDownOptions {
  onDrillDown?: (filters: {
    productName?: string;
    category?: SaleCategory;
    dateSegment?: { start: string; end: string };
    marginRange?: 'high' | 'healthy' | 'atRisk';
    returnStatus?: ReturnStatus[];
  }) => void;
}

export function useWidgetDrillDown(options: UseWidgetDrillDownOptions = {}) {
  const { onDrillDown } = options;

  const setProductName = useSalesFilterStore((s) => s.setProductName);
  const setMarginRange = useSalesFilterStore((s) => s.setMarginRange);
  const setReturnStatuses = useSalesFilterStore((s) => s.setReturnStatuses);
  const updateFilter = useSalesFilterStore((s) => s.updateFilter);

  const handleDrillDown = useCallback(
    (filters: {
      productName?: string;
      category?: SaleCategory;
      dateSegment?: { start: string; end: string };
      marginRange?: 'high' | 'healthy' | 'atRisk';
      returnStatus?: ReturnStatus[];
    }) => {
      // Apply filters to store
      if (filters.productName) {
        setProductName(filters.productName);
      }

      if (filters.category) {
        updateFilter('categories', [filters.category], 'widget');
      }

      if (filters.dateSegment) {
        updateFilter('dateRange', filters.dateSegment, 'widget');
      }

      if (filters.marginRange) {
        setMarginRange(filters.marginRange);
      }

      if (filters.returnStatus) {
        setReturnStatuses(filters.returnStatus);
      }

      // Call external callback
      onDrillDown?.(filters);
    },
    [setProductName, setMarginRange, setReturnStatuses, updateFilter, onDrillDown]
  );

  return { handleDrillDown };
}

// ─── Table Integration Hook ───────────────────────────────────────────

export interface UseTableFilterOptions {
  /** Enable real-time sync with widget */
  enableSync?: boolean;
}

export function useTableFilter(options: UseTableFilterOptions = {}) {
  const { enableSync = true } = options;

  const activeFilters = useSalesFilterStore((s) => s.activeFilters);
  const toggleCategory = useSalesFilterStore((s) => s.toggleCategory);
  const toggleCustomerSegment = useSalesFilterStore((s) => s.toggleCustomerSegment);
  const updateFilter = useSalesFilterStore((s) => s.updateFilter);
  const clearFilter = useSalesFilterStore((s) => s.clearFilter);
  const clearAllFilters = useSalesFilterStore((s) => s.clearAllFilters);

  // Table-specific filter handlers
  const handleCategoryToggle = useCallback(
    (category: SaleCategory) => {
      toggleCategory(category);
    },
    [toggleCategory]
  );

  const handleCustomerSegmentToggle = useCallback(
    (segment: string) => {
      toggleCustomerSegment(segment as any);
    },
    [toggleCustomerSegment]
  );

  const handleDateRangeChange = useCallback(
    (start: string, end: string) => {
      updateFilter('dateRange', { start, end }, 'table');
    },
    [updateFilter]
  );

  const handlePriceRangeChange = useCallback(
    (min: number, max: number) => {
      updateFilter('priceRange', { min, max }, 'table');
    },
    [updateFilter]
  );

  const handleProductTypeChange = useCallback(
    (types: string[]) => {
      updateFilter('productTypes', types.length > 0 ? types : null, 'table');
    },
    [updateFilter]
  );

  const handleClearFilter = useCallback(
    (filterType: keyof ActiveFilters) => {
      clearFilter(filterType);
    },
    [clearFilter]
  );

  const handleClearAll = useCallback(() => {
    clearAllFilters();
  }, [clearAllFilters]);

  return {
    activeFilters,
    handleCategoryToggle,
    handleCustomerSegmentToggle,
    handleDateRangeChange,
    handlePriceRangeChange,
    handleProductTypeChange,
    handleClearFilter,
    handleClearAll,
  };
}

export default useSalesFilterSync;
