/**
 * CONFIT — Dashboard Filter Hook
 * ================================
 * Centralized filter state for the Store Owner Dashboard.
 * Returns filtered data, active filter chips, and filter mutation helpers.
 */

import { useState, useMemo, useCallback } from 'react';
import type {
  SaleRecord,
  SaleCategory,
  DashboardFilters,
  FilterChip,
  DateRangePreset,
  ReturnStatus,
} from '@/types/dashboard';
import { INITIAL_DASHBOARD_FILTERS, CATEGORY_PRODUCT_TYPES } from '@/types/dashboard';
import {
  startOfDay,
  startOfWeek,
  startOfMonth,
  endOfDay,
  isWithinInterval,
  parseISO,
} from 'date-fns';

export function useDashboardFilters(allData: SaleRecord[]) {
  const [filters, setFilters] = useState<DashboardFilters>(INITIAL_DASHBOARD_FILTERS);

  // ─── Filter Mutations ─────────────────────────────────────────

  const setCategories = useCallback((cats: SaleCategory[]) => {
    setFilters(prev => ({ ...prev, categories: cats, productType: 'all' }));
  }, []);

  const toggleCategory = useCallback((cat: SaleCategory) => {
    setFilters(prev => {
      const next = prev.categories.includes(cat)
        ? prev.categories.filter(c => c !== cat)
        : [...prev.categories, cat];
      return { ...prev, categories: next, productType: 'all' };
    });
  }, []);

  const setDateRange = useCallback((range: DateRangePreset) => {
    setFilters(prev => ({ ...prev, dateRange: range }));
  }, []);

  const setCustomDates = useCallback((from: string, to: string) => {
    setFilters(prev => ({
      ...prev,
      dateRange: 'custom' as DateRangePreset,
      customDateFrom: from,
      customDateTo: to,
    }));
  }, []);

  const setProductType = useCallback((type: string) => {
    setFilters(prev => ({ ...prev, productType: type }));
  }, []);

  const setPriceRange = useCallback((min: number, max: number) => {
    setFilters(prev => ({ ...prev, priceMin: min, priceMax: max }));
  }, []);

  const setCustomerSegment = useCallback((seg: string) => {
    setFilters(prev => ({ ...prev, customerSegment: seg }));
  }, []);

  // ─── Drill-Down Filter Mutations ───────────────────────────────

  const setProductName = useCallback((name: string | undefined) => {
    setFilters(prev => ({ ...prev, productName: name }));
  }, []);

  const setMarginRange = useCallback((range: 'high' | 'healthy' | 'atRisk' | undefined) => {
    setFilters(prev => ({ ...prev, marginRange: range }));
  }, []);

  const setReturnStatuses = useCallback((statuses: ReturnStatus[] | undefined) => {
    setFilters(prev => ({ ...prev, returnStatuses: statuses }));
  }, []);

  const clearAll = useCallback(() => {
    setFilters(INITIAL_DASHBOARD_FILTERS);
  }, []);

  // ─── Available Product Types (dependent on selected categories) ─

  const availableProductTypes = useMemo(() => {
    if (filters.categories.length === 0) {
      return Object.values(CATEGORY_PRODUCT_TYPES).flat();
    }
    return filters.categories.flatMap(cat => CATEGORY_PRODUCT_TYPES[cat] || []);
  }, [filters.categories]);

  // ─── Active Filter Chips ──────────────────────────────────────

  const activeChips = useMemo<FilterChip[]>(() => {
    const chips: FilterChip[] = [];

    filters.categories.forEach(cat => {
      chips.push({
        key: `cat-${cat}`,
        label: cat,
        onRemove: () => toggleCategory(cat),
      });
    });

    if (filters.dateRange !== 'this_month') {
      const labels: Record<string, string> = {
        today: 'Today',
        this_week: 'This Week',
        custom: filters.customDateFrom && filters.customDateTo
          ? `${filters.customDateFrom} – ${filters.customDateTo}`
          : 'Custom Range',
      };
      chips.push({
        key: 'date',
        label: labels[filters.dateRange] || filters.dateRange,
        onRemove: () => setDateRange('this_month'),
      });
    }

    if (filters.productType !== 'all') {
      chips.push({
        key: 'type',
        label: filters.productType,
        onRemove: () => setProductType('all'),
      });
    }

    if (filters.priceMin > 0 || filters.priceMax < 50000) {
      chips.push({
        key: 'price',
        label: `EGP ${filters.priceMin.toLocaleString()} – ${filters.priceMax.toLocaleString()}`,
        onRemove: () => setPriceRange(0, 50000),
      });
    }

    if (filters.customerSegment !== 'all') {
      chips.push({
        key: 'segment',
        label: filters.customerSegment,
        onRemove: () => setCustomerSegment('all'),
      });
    }

    // Drill-down filter chips
    if (filters.productName) {
      chips.push({
        key: 'product',
        label: filters.productName,
        onRemove: () => setProductName(undefined),
      });
    }

    if (filters.marginRange) {
      const marginLabels: Record<string, string> = {
        high: 'High Margin (>30%)',
        healthy: 'Healthy Margin (15-30%)',
        atRisk: 'At-Risk Margin (<15%)',
      };
      chips.push({
        key: 'margin',
        label: marginLabels[filters.marginRange] || filters.marginRange,
        onRemove: () => setMarginRange(undefined),
      });
    }

    if (filters.returnStatuses && filters.returnStatuses.length > 0) {
      const statusLabel = filters.returnStatuses.length === 1
        ? filters.returnStatuses[0]
        : `${filters.returnStatuses.length} statuses`;
      chips.push({
        key: 'returnStatus',
        label: `Return: ${statusLabel}`,
        onRemove: () => setReturnStatuses(undefined),
      });
    }

    return chips;
  }, [filters, toggleCategory, setDateRange, setProductType, setPriceRange, setCustomerSegment, setProductName, setMarginRange, setReturnStatuses]);

  // ─── Filtered Data ────────────────────────────────────────────

  const filteredData = useMemo(() => {
    let result = [...allData];

    // Category filter
    if (filters.categories.length > 0) {
      result = result.filter(r => filters.categories.includes(r.category));
    }

    // Product type filter
    if (filters.productType !== 'all') {
      result = result.filter(r => r.productType === filters.productType);
    }

    // Price range filter
    result = result.filter(r => r.price >= filters.priceMin && r.price <= filters.priceMax);

    // Customer segment filter
    if (filters.customerSegment !== 'all') {
      result = result.filter(r => r.customerSegment === filters.customerSegment);
    }

    // Date range filter
    const now = new Date();
    let dateStart: Date | null = null;
    let dateEnd: Date = endOfDay(now);

    switch (filters.dateRange) {
      case 'today':
        dateStart = startOfDay(now);
        break;
      case 'this_week':
        dateStart = startOfWeek(now, { weekStartsOn: 0 });
        break;
      case 'this_month':
        dateStart = startOfMonth(now);
        break;
      case 'custom':
        if (filters.customDateFrom) dateStart = parseISO(filters.customDateFrom);
        if (filters.customDateTo) dateEnd = endOfDay(parseISO(filters.customDateTo));
        break;
    }

    if (dateStart) {
      result = result.filter(r => {
        const d = parseISO(r.saleDate);
        return isWithinInterval(d, { start: dateStart!, end: dateEnd });
      });
    }

    // ─── Drill-Down Filters ─────────────────────────────────────

    // Product name filter (drill-down from Top Products)
    if (filters.productName) {
      result = result.filter(r => r.productName === filters.productName);
    }

    // Margin range filter (drill-down from Margin Distribution)
    if (filters.marginRange) {
      const marginThresholds: Record<string, (m: number) => boolean> = {
        high: (m) => m >= 30,
        healthy: (m) => m >= 15 && m < 30,
        atRisk: (m) => m < 15,
      };
      result = result.filter(r => marginThresholds[filters.marginRange!](r.profitMargin));
    }

    // Return status filter (drill-down from Return Rate)
    if (filters.returnStatuses && filters.returnStatuses.length > 0) {
      result = result.filter(r => filters.returnStatuses!.includes(r.returnStatus));
    }

    return result;
  }, [allData, filters]);

  return {
    filters,
    filteredData,
    activeChips,
    availableProductTypes,
    setCategories,
    toggleCategory,
    setDateRange,
    setCustomDates,
    setProductType,
    setPriceRange,
    setCustomerSegment,
    setProductName,
    setMarginRange,
    setReturnStatuses,
    clearAll,
  };
}
