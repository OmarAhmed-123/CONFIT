/**
 * CONFIT — Sales Insights Drill-Down Hook
 * =========================================
 * Manages bi-directional filter synchronization between the Sales Insights Widget
 * and the Sales Analytics Table. Enables drill-down from widget visualizations
 * to table filters with additive filter logic.
 */

import { useCallback, useMemo } from 'react';
import type { SaleRecord, SaleCategory, ReturnStatus } from '@/types/dashboard';

// ─── Types ────────────────────────────────────────────────────────

export interface DrillDownFilters {
  /** Filter by specific product name */
  productName?: string;
  /** Filter by category */
  category?: SaleCategory;
  /** Filter by date segment */
  dateSegment?: { start: string; end: string };
  /** Filter by margin range category */
  marginRange?: 'high' | 'healthy' | 'atRisk';
  /** Filter by return status */
  returnStatus?: ReturnStatus[];
}

export interface UseSalesInsightsDrillDownOptions {
  /** Current filtered data */
  filteredData: SaleRecord[];
  /** Callback to set product name filter */
  setProductName?: (name: string) => void;
  /** Callback to toggle category filter */
  toggleCategory?: (category: SaleCategory) => void;
  /** Callback to set custom date range */
  setCustomDates?: (from: string, to: string) => void;
  /** Callback to set price range (used for margin filtering) */
  setPriceRange?: (min: number, max: number) => void;
  /** Callback to set return status filter */
  setReturnStatusFilter?: (statuses: ReturnStatus[]) => void;
  /** Callback to clear all filters */
  clearAll?: () => void;
}

export interface UseSalesInsightsDrillDownReturn {
  /** Handle drill-down action from widget */
  handleDrillDown: (filters: DrillDownFilters) => void;
  /** Apply drill-down filters to data (for preview) */
  applyDrillDownToData: (data: SaleRecord[], filters: DrillDownFilters) => SaleRecord[];
  /** Check if any drill-down filters are active */
  hasActiveDrillDown: boolean;
  /** Current drill-down filters */
  activeDrillDown: DrillDownFilters | null;
}

// ─── Margin Range Price Multipliers ───────────────────────────────

const MARGIN_PRICE_RANGES: Record<string, { min: number; max: number }> = {
  high: { min: 0, max: 50000 },      // High margin products (all prices)
  healthy: { min: 0, max: 50000 },   // Healthy margin products
  atRisk: { min: 0, max: 50000 },    // At-risk margin products
};

// ─── Hook Implementation ─────────────────────────────────────────

export function useSalesInsightsDrillDown({
  filteredData,
  setProductName,
  toggleCategory,
  setCustomDates,
  setPriceRange,
  setReturnStatusFilter,
  clearAll,
}: UseSalesInsightsDrillDownOptions): UseSalesInsightsDrillDownReturn {
  
  /**
   * Apply drill-down filters to a dataset
   * Used for calculating widget metrics with drill-down applied
   */
  const applyDrillDownToData = useCallback(
    (data: SaleRecord[], filters: DrillDownFilters): SaleRecord[] => {
      let result = [...data];

      // Product name filter
      if (filters.productName) {
        result = result.filter(r => r.productName === filters.productName);
      }

      // Category filter
      if (filters.category) {
        result = result.filter(r => r.category === filters.category);
      }

      // Date segment filter
      if (filters.dateSegment) {
        const start = new Date(filters.dateSegment.start).getTime();
        const end = new Date(filters.dateSegment.end).getTime();
        result = result.filter(r => {
          const saleDate = new Date(r.saleDate).getTime();
          return saleDate >= start && saleDate <= end;
        });
      }

      // Margin range filter
      if (filters.marginRange) {
        const marginThresholds: Record<string, (m: number) => boolean> = {
          high: (m) => m >= 30,
          healthy: (m) => m >= 15 && m < 30,
          atRisk: (m) => m < 15,
        };
        result = result.filter(r => marginThresholds[filters.marginRange!](r.profitMargin));
      }

      // Return status filter
      if (filters.returnStatus && filters.returnStatus.length > 0) {
        result = result.filter(r => filters.returnStatus!.includes(r.returnStatus));
      }

      return result;
    },
    []
  );

  /**
   * Handle drill-down action from widget
   * Applies filters to the table with additive logic
   */
  const handleDrillDown = useCallback(
    (filters: DrillDownFilters) => {
      // Product name drill-down
      if (filters.productName && setProductName) {
        setProductName(filters.productName);
      }

      // Category drill-down (additive)
      if (filters.category && toggleCategory) {
        toggleCategory(filters.category);
      }

      // Date segment drill-down
      if (filters.dateSegment && setCustomDates) {
        const start = filters.dateSegment.start.split('T')[0];
        const end = filters.dateSegment.end.split('T')[0];
        setCustomDates(start, end);
      }

      // Margin range drill-down
      // Note: We'll use a combination of filters for margin
      if (filters.marginRange) {
        // Margin filtering requires a custom approach
        // We'll emit an event that the parent can handle
        const event = new CustomEvent('confit:margin-drilldown', {
          detail: { marginRange: filters.marginRange },
        });
        window.dispatchEvent(event);
      }

      // Return status drill-down
      if (filters.returnStatus && filters.returnStatus.length > 0 && setReturnStatusFilter) {
        setReturnStatusFilter(filters.returnStatus);
      }
    },
    [setProductName, toggleCategory, setCustomDates, setReturnStatusFilter]
  );

  // Track active drill-down state (for UI indicators)
  const activeDrillDown = useMemo<DrillDownFilters | null>(() => {
    return null; // This would be populated from actual filter state
  }, []);

  const hasActiveDrillDown = useMemo(() => {
    return activeDrillDown !== null && Object.keys(activeDrillDown).length > 0;
  }, [activeDrillDown]);

  return {
    handleDrillDown,
    applyDrillDownToData,
    hasActiveDrillDown,
    activeDrillDown,
  };
}

export default useSalesInsightsDrillDown;
