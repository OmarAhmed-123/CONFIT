/**
 * CONFIT — Sales Filter Store
 * =============================
 * Centralized, performant filter state management for bidirectional
 * synchronization between Sales Insights Widget and Sales Analytics Table.
 *
 * Features:
 * - Single source of truth for all active filters
 * - Undo/redo capability with immutable history snapshots
 * - Memoized KPI selectors for derived state
 * - localStorage persistence for filter state survival
 * - Debounced updates for large dataset performance
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type {
  SaleRecord,
  SaleCategory,
  CustomerSegment,
  ReturnStatus,
} from '@/types/dashboard';

// ─── Filter Types ─────────────────────────────────────────────────────

export interface DateRangeFilter {
  start: string; // ISO 8601
  end: string;   // ISO 8601
}

export interface PriceRangeFilter {
  min: number;
  max: number;
}

export interface ActiveFilters {
  /** Filter by product categories */
  categories: SaleCategory[] | null;
  /** Filter by date range */
  dateRange: DateRangeFilter | null;
  /** Filter by price range */
  priceRange: PriceRangeFilter | null;
  /** Filter by customer segments */
  customerSegments: CustomerSegment[] | null;
  /** Filter by product types */
  productTypes: string[] | null;
  /** Filter by specific product name (drill-down) */
  productName: string | null;
  /** Filter by margin range category */
  marginRange: 'high' | 'healthy' | 'atRisk' | null;
  /** Filter by return status */
  returnStatuses: ReturnStatus[] | null;
}

export interface FilterSnapshot {
  filters: ActiveFilters;
  timestamp: string;
  source: 'widget' | 'table' | 'external';
}

// ─── KPI Types ────────────────────────────────────────────────────────

export interface RevenueTrendData {
  date: string;
  revenue: number;
}

export interface TopProduct {
  name: string;
  revenue: number;
  quantity: number;
  avgMargin: number;
}

export interface MarginDistribution {
  name: string;
  value: number;
  count: number;
  color: string;
  range: string;
}

export interface ReturnRateData {
  returnRate: number;
  returnedCount: number;
  pendingCount: number;
  totalSales: number;
  status: 'Low' | 'Moderate' | 'High';
}

export interface ComputedKPIs {
  totalRevenue: number;
  revenueTrend: RevenueTrendData[];
  trendPercent: number;
  topProducts: TopProduct[];
  avgMargin: number;
  marginDistribution: MarginDistribution[];
  returnRate: ReturnRateData;
  filteredCount: number;
  lastComputed: string;
}

// ─── Default Filters ──────────────────────────────────────────────────

export const DEFAULT_ACTIVE_FILTERS: ActiveFilters = {
  categories: null,
  dateRange: null,
  priceRange: null,
  customerSegments: null,
  productTypes: null,
  productName: null,
  marginRange: null,
  returnStatuses: null,
};

// ─── History Configuration ────────────────────────────────────────────

const MAX_HISTORY_DEPTH = 20;

// ─── Store State Interface ────────────────────────────────────────────

interface SalesFilterState {
  // Current active filters
  activeFilters: ActiveFilters;

  // Filter history for undo/redo
  filterHistory: FilterSnapshot[];
  historyPointer: number;

  // Raw sales data reference (set externally)
  _rawData: SaleRecord[];

  // Computed KPIs (memoized via selector)
  _computedKPIs: ComputedKPIs | null;

  // Loading state
  isLoading: boolean;

  // ─── Filter Actions ───

  /** Update a specific filter type */
  updateFilter: <K extends keyof ActiveFilters>(
    filterType: K,
    value: ActiveFilters[K],
    source?: 'widget' | 'table' | 'external'
  ) => void;

  /** Apply multiple filters at once */
  updateFilters: (
    updates: Partial<ActiveFilters>,
    source?: 'widget' | 'table' | 'external'
  ) => void;

  /** Clear a specific filter */
  clearFilter: (filterType: keyof ActiveFilters) => void;

  /** Clear all filters */
  clearAllFilters: () => void;

  /** Toggle a category filter (additive) */
  toggleCategory: (category: SaleCategory) => void;

  /** Toggle a customer segment filter (additive) */
  toggleCustomerSegment: (segment: CustomerSegment) => void;

  /** Set date range filter */
  setDateRange: (start: string, end: string) => void;

  /** Set price range filter */
  setPriceRange: (min: number, max: number) => void;

  /** Set product name filter (drill-down) */
  setProductName: (name: string | null) => void;

  /** Set margin range filter (drill-down) */
  setMarginRange: (range: 'high' | 'healthy' | 'atRisk' | null) => void;

  /** Set return status filter (drill-down) */
  setReturnStatuses: (statuses: ReturnStatus[] | null) => void;

  // ─── History Actions ───

  /** Undo to previous filter state */
  undo: () => void;

  /** Redo to next filter state */
  redo: () => void;

  /** Check if undo is available */
  canUndo: () => boolean;

  /** Check if redo is available */
  canRedo: () => boolean;

  /** Clear filter history */
  clearHistory: () => void;

  // ─── Data Actions ───

  /** Set raw sales data (triggers KPI recomputation) */
  setRawData: (data: SaleRecord[]) => void;

  /** Set loading state */
  setLoading: (loading: boolean) => void;

  // ─── Computed Selectors ───

  /** Get filtered data based on active filters */
  getFilteredData: () => SaleRecord[];

  /** Get computed KPIs */
  getComputedKPIs: () => ComputedKPIs;

  /** Check if any filters are active */
  hasActiveFilters: () => boolean;

  /** Get count of active filters */
  getActiveFilterCount: () => number;

  /** Get filter chips for UI display */
  getFilterChips: () => Array<{ key: string; label: string; type: keyof ActiveFilters }>;
}

// ─── Filter Application Functions ─────────────────────────────────────

function applyFiltersToData(
  data: SaleRecord[],
  filters: ActiveFilters
): SaleRecord[] {
  let result = [...data];

  // Category filter
  if (filters.categories && filters.categories.length > 0) {
    result = result.filter((r) =>
      filters.categories!.includes(r.category)
    );
  }

  // Date range filter
  if (filters.dateRange) {
    const startTime = new Date(filters.dateRange.start).getTime();
    const endTime = new Date(filters.dateRange.end).getTime();
    result = result.filter((r) => {
      const saleDate = new Date(r.saleDate).getTime();
      return saleDate >= startTime && saleDate <= endTime;
    });
  }

  // Price range filter
  if (filters.priceRange) {
    result = result.filter(
      (r) =>
        r.price >= filters.priceRange!.min &&
        r.price <= filters.priceRange!.max
    );
  }

  // Customer segment filter
  if (filters.customerSegments && filters.customerSegments.length > 0) {
    result = result.filter((r) =>
      filters.customerSegments!.includes(r.customerSegment)
    );
  }

  // Product types filter
  if (filters.productTypes && filters.productTypes.length > 0) {
    result = result.filter((r) =>
      filters.productTypes!.includes(r.productType)
    );
  }

  // Product name filter (drill-down)
  if (filters.productName) {
    result = result.filter((r) => r.productName === filters.productName);
  }

  // Margin range filter (drill-down)
  if (filters.marginRange) {
    const marginThresholds: Record<string, (m: number) => boolean> = {
      high: (m) => m >= 30,
      healthy: (m) => m >= 15 && m < 30,
      atRisk: (m) => m < 15,
    };
    result = result.filter((r) =>
      marginThresholds[filters.marginRange!](r.profitMargin)
    );
  }

  // Return status filter (drill-down)
  if (filters.returnStatuses && filters.returnStatuses.length > 0) {
    result = result.filter((r) =>
      filters.returnStatuses!.includes(r.returnStatus)
    );
  }

  return result;
}

// ─── KPI Computation Functions ────────────────────────────────────────

const MARGIN_COLORS = {
  high: '#22C55E',
  healthy: '#FBBF24',
  atRisk: '#F87171',
};

function computeKPIs(filteredData: SaleRecord[]): ComputedKPIs {
  const totalRevenue = filteredData.reduce(
    (sum, r) => sum + r.price * r.quantity,
    0
  );

  // Revenue trend calculation
  const revenueTrend = computeRevenueTrend(filteredData);
  const trendPercent = computeTrendPercent(revenueTrend);

  // Top products
  const topProducts = computeTopProducts(filteredData);

  // Margin distribution
  const { avgMargin, marginDistribution } = computeMarginDistribution(filteredData);

  // Return rate
  const returnRate = computeReturnRate(filteredData);

  return {
    totalRevenue,
    revenueTrend,
    trendPercent,
    topProducts,
    avgMargin,
    marginDistribution,
    returnRate,
    filteredCount: filteredData.length,
    lastComputed: new Date().toISOString(),
  };
}

function computeRevenueTrend(data: SaleRecord[]): RevenueTrendData[] {
  if (data.length === 0) return [];

  // Group by date
  const revenueByDate = new Map<string, number>();

  data.forEach((r) => {
    const dateKey = r.saleDate.split('T')[0];
    const current = revenueByDate.get(dateKey) || 0;
    revenueByDate.set(dateKey, current + r.price * r.quantity);
  });

  // Sort by date and return
  return Array.from(revenueByDate.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, revenue]) => ({ date, revenue }));
}

function computeTrendPercent(trend: RevenueTrendData[]): number {
  if (trend.length < 2) return 0;

  const midPoint = Math.floor(trend.length / 2);
  const firstHalf = trend.slice(0, midPoint).reduce((s, d) => s + d.revenue, 0);
  const secondHalf = trend.slice(midPoint).reduce((s, d) => s + d.revenue, 0);

  return firstHalf > 0 ? ((secondHalf - firstHalf) / firstHalf) * 100 : 0;
}

function computeTopProducts(data: SaleRecord[]): TopProduct[] {
  const productStats = new Map<
    string,
    { revenue: number; quantity: number; margin: number; count: number }
  >();

  data.forEach((r) => {
    const existing = productStats.get(r.productName) || {
      revenue: 0,
      quantity: 0,
      margin: 0,
      count: 0,
    };
    productStats.set(r.productName, {
      revenue: existing.revenue + r.price * r.quantity,
      quantity: existing.quantity + r.quantity,
      margin: existing.margin + r.profitMargin,
      count: existing.count + 1,
    });
  });

  return Array.from(productStats.entries())
    .map(([name, stats]) => ({
      name,
      revenue: stats.revenue,
      quantity: stats.quantity,
      avgMargin: Math.round(stats.margin / stats.count),
    }))
    .sort((a, b) => b.revenue - a.revenue)
    .slice(0, 5);
}

function computeMarginDistribution(data: SaleRecord[]): {
  avgMargin: number;
  marginDistribution: MarginDistribution[];
} {
  const categories = {
    high: { name: 'High', value: 0, count: 0, color: MARGIN_COLORS.high, range: '>30%' },
    healthy: { name: 'Healthy', value: 0, count: 0, color: MARGIN_COLORS.healthy, range: '15-30%' },
    atRisk: { name: 'At Risk', value: 0, count: 0, color: MARGIN_COLORS.atRisk, range: '<15%' },
  };

  let totalMargin = 0;
  const totalSales = data.length;

  data.forEach((r) => {
    const category = getMarginCategory(r.profitMargin);
    categories[category].value += r.price * r.quantity;
    categories[category].count += 1;
    totalMargin += r.profitMargin;
  });

  const marginDistribution = Object.values(categories)
    .filter((c) => c.count > 0)
    .map((c) => ({
      name: c.name,
      value: c.value,
      count: c.count,
      color: c.color,
      range: c.range,
    }));

  const avgMargin = totalSales > 0 ? Math.round(totalMargin / totalSales) : 0;

  return { avgMargin, marginDistribution };
}

function computeReturnRate(data: SaleRecord[]): ReturnRateData {
  const totalSales = data.length;
  const returned = data.filter((d) => d.returnStatus === 'Returned').length;
  const pending = data.filter((d) => d.returnStatus === 'Pending Return').length;
  const returnRate = totalSales > 0 ? ((returned + pending) / totalSales) * 100 : 0;

  let status: 'Low' | 'Moderate' | 'High';
  if (returnRate < 5) status = 'Low';
  else if (returnRate < 15) status = 'Moderate';
  else status = 'High';

  return { returnRate, returnedCount: returned, pendingCount: pending, totalSales, status };
}

function getMarginCategory(margin: number): 'high' | 'healthy' | 'atRisk' {
  if (margin >= 30) return 'high';
  if (margin >= 15) return 'healthy';
  return 'atRisk';
}

// ─── Store Implementation ─────────────────────────────────────────────

export const useSalesFilterStore = create<SalesFilterState>()(
  persist(
    (set, get) => ({
      // Initial state
      activeFilters: { ...DEFAULT_ACTIVE_FILTERS },
      filterHistory: [],
      historyPointer: -1,
      _rawData: [],
      _computedKPIs: null,
      isLoading: false,

      // ─── Filter Actions ───

      updateFilter: (filterType, value, source = 'external') => {
        const currentFilters = get().activeFilters;

        // Create snapshot for history
        const snapshot: FilterSnapshot = {
          filters: { ...currentFilters },
          timestamp: new Date().toISOString(),
          source,
        };

        set((state) => {
          // Add to history, trim to max depth
          const newHistory = [
            ...state.filterHistory.slice(
              Math.max(0, state.filterHistory.length - MAX_HISTORY_DEPTH + 1)
            ),
            snapshot,
          ];

          // Update pointer to end
          const newPointer = newHistory.length - 1;

          return {
            activeFilters: { ...state.activeFilters, [filterType]: value },
            filterHistory: newHistory,
            historyPointer: newPointer,
            _computedKPIs: null, // Invalidate cache
          };
        });
      },

      updateFilters: (updates, source = 'external') => {
        const currentFilters = get().activeFilters;

        const snapshot: FilterSnapshot = {
          filters: { ...currentFilters },
          timestamp: new Date().toISOString(),
          source,
        };

        set((state) => {
          const newHistory = [
            ...state.filterHistory.slice(
              Math.max(0, state.filterHistory.length - MAX_HISTORY_DEPTH + 1)
            ),
            snapshot,
          ];
          const newPointer = newHistory.length - 1;

          return {
            activeFilters: { ...state.activeFilters, ...updates },
            filterHistory: newHistory,
            historyPointer: newPointer,
            _computedKPIs: null,
          };
        });
      },

      clearFilter: (filterType) => {
        set((state) => ({
          activeFilters: { ...state.activeFilters, [filterType]: null },
          _computedKPIs: null,
        }));
      },

      clearAllFilters: () => {
        const currentFilters = get().activeFilters;

        const snapshot: FilterSnapshot = {
          filters: { ...currentFilters },
          timestamp: new Date().toISOString(),
          source: 'external',
        };

        set((state) => {
          const newHistory = [
            ...state.filterHistory.slice(
              Math.max(0, state.filterHistory.length - MAX_HISTORY_DEPTH + 1)
            ),
            snapshot,
          ];

          return {
            activeFilters: { ...DEFAULT_ACTIVE_FILTERS },
            filterHistory: newHistory,
            historyPointer: newHistory.length - 1,
            _computedKPIs: null,
          };
        });
      },

      toggleCategory: (category) => {
        const current = get().activeFilters.categories || [];
        const exists = current.includes(category);

        set((state) => ({
          activeFilters: {
            ...state.activeFilters,
            categories: exists
              ? current.filter((c) => c !== category)
              : [...current, category],
          },
          _computedKPIs: null,
        }));
      },

      toggleCustomerSegment: (segment) => {
        const current = get().activeFilters.customerSegments || [];
        const exists = current.includes(segment);

        set((state) => ({
          activeFilters: {
            ...state.activeFilters,
            customerSegments: exists
              ? current.filter((s) => s !== segment)
              : [...current, segment],
          },
          _computedKPIs: null,
        }));
      },

      setDateRange: (start, end) => {
        get().updateFilter('dateRange', { start, end }, 'external');
      },

      setPriceRange: (min, max) => {
        get().updateFilter('priceRange', { min, max }, 'external');
      },

      setProductName: (name) => {
        get().updateFilter('productName', name, 'widget');
      },

      setMarginRange: (range) => {
        get().updateFilter('marginRange', range, 'widget');
      },

      setReturnStatuses: (statuses) => {
        get().updateFilter('returnStatuses', statuses, 'widget');
      },

      // ─── History Actions ───

      undo: () => {
        const { filterHistory, historyPointer } = get();

        if (historyPointer > 0) {
          const prevSnapshot = filterHistory[historyPointer - 1];
          set({
            activeFilters: { ...prevSnapshot.filters },
            historyPointer: historyPointer - 1,
            _computedKPIs: null,
          });
        }
      },

      redo: () => {
        const { filterHistory, historyPointer } = get();

        if (historyPointer < filterHistory.length - 1) {
          const nextSnapshot = filterHistory[historyPointer + 1];
          set({
            activeFilters: { ...nextSnapshot.filters },
            historyPointer: historyPointer + 1,
            _computedKPIs: null,
          });
        }
      },

      canUndo: () => get().historyPointer > 0,

      canRedo: () => get().historyPointer < get().filterHistory.length - 1,

      clearHistory: () => {
        set({ filterHistory: [], historyPointer: -1 });
      },

      // ─── Data Actions ───

      setRawData: (data) => {
        set({ _rawData: data, _computedKPIs: null });
      },

      setLoading: (loading) => {
        set({ isLoading: loading });
      },

      // ─── Computed Selectors ───

      getFilteredData: () => {
        const { _rawData, activeFilters } = get();
        return applyFiltersToData(_rawData, activeFilters);
      },

      getComputedKPIs: () => {
        const { _rawData, activeFilters, _computedKPIs } = get();

        // Return cached if available
        if (_computedKPIs) {
          return _computedKPIs;
        }

        // Compute and cache
        const filteredData = applyFiltersToData(_rawData, activeFilters);
        const kpis = computeKPIs(filteredData);

        // Update cache
        set({ _computedKPIs: kpis });

        return kpis;
      },

      hasActiveFilters: () => {
        const { activeFilters } = get();
        return Object.values(activeFilters).some((v) => {
          if (v === null) return false;
          if (Array.isArray(v)) return v.length > 0;
          return true;
        });
      },

      getActiveFilterCount: () => {
        const { activeFilters } = get();
        let count = 0;

        Object.entries(activeFilters).forEach(([key, value]) => {
          if (value === null) return;
          if (Array.isArray(value) && value.length === 0) return;
          count++;
        });

        return count;
      },

      getFilterChips: () => {
        const { activeFilters } = get();
        const chips: Array<{ key: string; label: string; type: keyof ActiveFilters }> = [];

        if (activeFilters.categories && activeFilters.categories.length > 0) {
          activeFilters.categories.forEach((cat) => {
            chips.push({
              key: `category-${cat}`,
              label: cat,
              type: 'categories',
            });
          });
        }

        if (activeFilters.dateRange) {
          const start = new Date(activeFilters.dateRange.start).toLocaleDateString();
          const end = new Date(activeFilters.dateRange.end).toLocaleDateString();
          chips.push({
            key: 'dateRange',
            label: `${start} - ${end}`,
            type: 'dateRange',
          });
        }

        if (activeFilters.priceRange) {
          chips.push({
            key: 'priceRange',
            label: `EGP ${activeFilters.priceRange.min.toLocaleString()} - ${activeFilters.priceRange.max.toLocaleString()}`,
            type: 'priceRange',
          });
        }

        if (activeFilters.customerSegments && activeFilters.customerSegments.length > 0) {
          activeFilters.customerSegments.forEach((seg) => {
            chips.push({
              key: `segment-${seg}`,
              label: seg,
              type: 'customerSegments',
            });
          });
        }

        if (activeFilters.productTypes && activeFilters.productTypes.length > 0) {
          activeFilters.productTypes.forEach((pt) => {
            chips.push({
              key: `productType-${pt}`,
              label: pt,
              type: 'productTypes',
            });
          });
        }

        if (activeFilters.productName) {
          chips.push({
            key: 'productName',
            label: activeFilters.productName,
            type: 'productName',
          });
        }

        if (activeFilters.marginRange) {
          const labels: Record<string, string> = {
            high: 'High Margin (>30%)',
            healthy: 'Healthy Margin (15-30%)',
            atRisk: 'At Risk Margin (<15%)',
          };
          chips.push({
            key: 'marginRange',
            label: labels[activeFilters.marginRange],
            type: 'marginRange',
          });
        }

        if (activeFilters.returnStatuses && activeFilters.returnStatuses.length > 0) {
          activeFilters.returnStatuses.forEach((status) => {
            chips.push({
              key: `returnStatus-${status}`,
              label: status,
              type: 'returnStatuses',
            });
          });
        }

        return chips;
      },
    }),
    {
      name: 'confit-sales-filters',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        activeFilters: state.activeFilters,
        filterHistory: state.filterHistory.slice(-10), // Persist last 10
        historyPointer: state.historyPointer,
      }),
    }
  )
);

// ─── Convenience Hooks ────────────────────────────────────────────────

/**
 * Hook for accessing filter state and actions
 */
export function useSalesFilters() {
  const activeFilters = useSalesFilterStore((s) => s.activeFilters);
  const updateFilter = useSalesFilterStore((s) => s.updateFilter);
  const updateFilters = useSalesFilterStore((s) => s.updateFilters);
  const clearFilter = useSalesFilterStore((s) => s.clearFilter);
  const clearAllFilters = useSalesFilterStore((s) => s.clearAllFilters);
  const toggleCategory = useSalesFilterStore((s) => s.toggleCategory);
  const toggleCustomerSegment = useSalesFilterStore((s) => s.toggleCustomerSegment);
  const setDateRange = useSalesFilterStore((s) => s.setDateRange);
  const setPriceRange = useSalesFilterStore((s) => s.setPriceRange);
  const setProductName = useSalesFilterStore((s) => s.setProductName);
  const setMarginRange = useSalesFilterStore((s) => s.setMarginRange);
  const setReturnStatuses = useSalesFilterStore((s) => s.setReturnStatuses);
  const hasActiveFilters = useSalesFilterStore((s) => s.hasActiveFilters);
  const getActiveFilterCount = useSalesFilterStore((s) => s.getActiveFilterCount);
  const getFilterChips = useSalesFilterStore((s) => s.getFilterChips);

  return {
    activeFilters,
    updateFilter,
    updateFilters,
    clearFilter,
    clearAllFilters,
    toggleCategory,
    toggleCustomerSegment,
    setDateRange,
    setPriceRange,
    setProductName,
    setMarginRange,
    setReturnStatuses,
    hasActiveFilters,
    getActiveFilterCount,
    getFilterChips,
  };
}

/**
 * Hook for undo/redo functionality
 */
export function useFilterHistory() {
  const undo = useSalesFilterStore((s) => s.undo);
  const redo = useSalesFilterStore((s) => s.redo);
  const canUndo = useSalesFilterStore((s) => s.canUndo);
  const canRedo = useSalesFilterStore((s) => s.canRedo);
  const clearHistory = useSalesFilterStore((s) => s.clearHistory);
  const filterHistory = useSalesFilterStore((s) => s.filterHistory);
  const historyPointer = useSalesFilterStore((s) => s.historyPointer);

  return {
    undo,
    redo,
    canUndo,
    canRedo,
    clearHistory,
    filterHistory,
    historyPointer,
  };
}

/**
 * Hook for computed KPIs with memoization
 */
export function useComputedKPIs() {
  const rawData = useSalesFilterStore((s) => s._rawData);
  const activeFilters = useSalesFilterStore((s) => s.activeFilters);
  const getComputedKPIs = useSalesFilterStore((s) => s.getComputedKPIs);
  const getFilteredData = useSalesFilterStore((s) => s.getFilteredData);

  // Get memoized KPIs
  const kpis = getComputedKPIs();
  const filteredData = getFilteredData();

  return {
    kpis,
    filteredData,
    rawData,
    activeFilters,
  };
}

/**
 * Hook for loading state management
 */
export function useSalesDataLoading() {
  const isLoading = useSalesFilterStore((s) => s.isLoading);
  const setLoading = useSalesFilterStore((s) => s.setLoading);
  const setRawData = useSalesFilterStore((s) => s.setRawData);

  return { isLoading, setLoading, setRawData };
}

export default useSalesFilterStore;
