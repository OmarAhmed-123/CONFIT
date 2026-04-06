/**
 * CONFIT — Sales Filter Edge Case Handlers
 * ==========================================
 * Utilities for handling edge cases in the bidirectional
 * filter synchronization system.
 *
 * Handles:
 * - Empty filter results
 * - Filter conflicts (widget drill-down vs existing filters)
 * - Large dataset performance optimization
 * - Filter validation and normalization
 */

import type { ActiveFilters, ComputedKPIs } from '@/stores/salesFilterStore';
import type { SaleRecord, SaleCategory, CustomerSegment, ReturnStatus } from '@/types/dashboard';

// ─── Types ────────────────────────────────────────────────────────────

export interface FilterConflictResolution {
  action: 'replace' | 'merge' | 'add' | 'reject';
  reason: string;
  resolvedFilters: Partial<ActiveFilters>;
}

export interface EmptyResultContext {
  hasFilters: boolean;
  filterCombination: string;
  suggestions: string[];
}

export interface PerformanceMetrics {
  filterTime: number;
  recordCount: number;
  filteredCount: number;
  kpiComputeTime: number;
  totalTime: number;
}

// ─── Empty Result Handling ────────────────────────────────────────────

/**
 * Analyze empty filter results and provide context
 */
export function analyzeEmptyResult(
  filters: ActiveFilters,
  rawData: SaleRecord[]
): EmptyResultContext {
  const activeFilterTypes = Object.entries(filters)
    .filter(([_, value]) => {
      if (value === null) return false;
      if (Array.isArray(value)) return value.length > 0;
      return true;
    })
    .map(([key]) => key);

  const hasFilters = activeFilterTypes.length > 0;

  // Build filter combination description
  const filterDescriptions: string[] = [];

  if (filters.categories?.length) {
    filterDescriptions.push(`categories: ${filters.categories.join(', ')}`);
  }
  if (filters.dateRange) {
    filterDescriptions.push(`date range: ${filters.dateRange.start} to ${filters.dateRange.end}`);
  }
  if (filters.priceRange) {
    filterDescriptions.push(`price: EGP ${filters.priceRange.min.toLocaleString()} - ${filters.priceRange.max.toLocaleString()}`);
  }
  if (filters.customerSegments?.length) {
    filterDescriptions.push(`segments: ${filters.customerSegments.join(', ')}`);
  }
  if (filters.productTypes?.length) {
    filterDescriptions.push(`product types: ${filters.productTypes.join(', ')}`);
  }
  if (filters.productName) {
    filterDescriptions.push(`product: "${filters.productName}"`);
  }
  if (filters.marginRange) {
    const labels: Record<string, string> = {
      high: 'high margin (>30%)',
      healthy: 'healthy margin (15-30%)',
      atRisk: 'at-risk margin (<15%)',
    };
    filterDescriptions.push(labels[filters.marginRange]);
  }
  if (filters.returnStatuses?.length) {
    filterDescriptions.push(`status: ${filters.returnStatuses.join(', ')}`);
  }

  // Generate suggestions
  const suggestions: string[] = [];

  if (activeFilterTypes.length > 2) {
    suggestions.push('Try removing some filters to broaden your search');
  }

  if (filters.dateRange) {
    const daysDiff = Math.ceil(
      (new Date(filters.dateRange.end).getTime() - new Date(filters.dateRange.start).getTime()) /
        (1000 * 60 * 60 * 24)
    );
    if (daysDiff < 7) {
      suggestions.push('Expand your date range to include more sales');
    }
  }

  if (filters.priceRange && filters.priceRange.min > 10000) {
    suggestions.push('Lower the minimum price to include more products');
  }

  if (filters.productName) {
    suggestions.push('Check if the product name is spelled correctly');
    suggestions.push('Try searching for a partial product name instead');
  }

  if (filters.categories?.length === 1) {
    suggestions.push(`Try including other categories besides ${filters.categories[0]}`);
  }

  return {
    hasFilters,
    filterCombination: filterDescriptions.join(' AND '),
    suggestions,
  };
}

/**
 * Generate empty result message for UI
 */
export function getEmptyResultMessage(context: EmptyResultContext): {
  title: string;
  description: string;
} {
  if (!context.hasFilters) {
    return {
      title: 'No sales data available',
      description: 'There are no sales records in the system. Check back later or contact support.',
    };
  }

  return {
    title: 'No sales match your filters',
    description: `No sales found for ${context.filterCombination}. ${context.suggestions[0] || 'Try adjusting your filter criteria.'}`,
  };
}

// ─── Filter Conflict Resolution ───────────────────────────────────────

/**
 * Resolve conflicts when widget drill-down conflicts with existing filters
 */
export function resolveFilterConflict(
  currentFilters: ActiveFilters,
  drillDownType: keyof ActiveFilters,
  drillDownValue: unknown,
  strategy: 'replace' | 'merge' | 'smart' = 'smart'
): FilterConflictResolution {
  // Smart strategy: merge for additive filters, replace for singular filters
  const additiveFilters: (keyof ActiveFilters)[] = ['categories', 'customerSegments', 'productTypes', 'returnStatuses'];
  const singularFilters: (keyof ActiveFilters)[] = ['dateRange', 'priceRange', 'productName', 'marginRange'];

  if (strategy === 'replace') {
    return {
      action: 'replace',
      reason: 'Replacing all existing filters with drill-down selection',
      resolvedFilters: { [drillDownType]: drillDownValue as any },
    };
  }

  if (strategy === 'merge') {
    if (additiveFilters.includes(drillDownType)) {
      const current = currentFilters[drillDownType] as Array<unknown> | null;
      const newValue = Array.isArray(drillDownValue) ? drillDownValue : [drillDownValue];
      const merged = [...(current || []), ...newValue];
      const unique = [...new Set(merged)];

      return {
        action: 'merge',
        reason: `Adding ${drillDownType} to existing filters`,
        resolvedFilters: { [drillDownType]: unique as any },
      };
    }

    return {
      action: 'replace',
      reason: `Replacing ${drillDownType} filter with drill-down selection`,
      resolvedFilters: { [drillDownType]: drillDownValue as any },
    };
  }

  // Smart strategy
  if (additiveFilters.includes(drillDownType)) {
    const current = currentFilters[drillDownType] as Array<unknown> | null;
    if (!current || current.length === 0) {
      return {
        action: 'add',
        reason: `No existing ${drillDownType} filter, adding new filter`,
        resolvedFilters: { [drillDownType]: Array.isArray(drillDownValue) ? drillDownValue : [drillDownValue] as any },
      };
    }

    const newValue = Array.isArray(drillDownValue) ? drillDownValue[0] : drillDownValue;
    const exists = current.includes(newValue);

    if (exists) {
      // Toggle off
      const filtered = current.filter((v) => v !== newValue);
      return {
        action: 'merge',
        reason: `Toggling off ${drillDownType} filter: ${newValue}`,
        resolvedFilters: { [drillDownType]: filtered.length > 0 ? filtered : null as any },
      };
    }

    // Add to existing
    return {
      action: 'merge',
      reason: `Adding ${drillDownType} to existing filters`,
      resolvedFilters: { [drillDownType]: [...current, newValue] as any },
    };
  }

  if (singularFilters.includes(drillDownType)) {
    const current = currentFilters[drillDownType];
    const isSame = JSON.stringify(current) === JSON.stringify(drillDownValue);

    if (isSame) {
      return {
        action: 'reject',
        reason: `${drillDownType} filter already set to this value`,
        resolvedFilters: {},
      };
    }

    return {
      action: 'replace',
      reason: `Replacing ${drillDownType} filter with drill-down selection`,
      resolvedFilters: { [drillDownType]: drillDownValue as any },
    };
  }

  return {
    action: 'replace',
    reason: 'Default replacement strategy applied',
    resolvedFilters: { [drillDownType]: drillDownValue as any },
  };
}

// ─── Large Dataset Performance ────────────────────────────────────────

const PERFORMANCE_THRESHOLDS = {
  small: 1000,
  medium: 10000,
  large: 50000,
  veryLarge: 100000,
};

/**
 * Determine if debouncing is needed based on dataset size
 */
export function shouldDebounceFilters(recordCount: number): {
  needed: boolean;
  delay: number;
  reason: string;
} {
  if (recordCount <= PERFORMANCE_THRESHOLDS.small) {
    return {
      needed: false,
      delay: 0,
      reason: 'Small dataset, real-time filtering is acceptable',
    };
  }

  if (recordCount <= PERFORMANCE_THRESHOLDS.medium) {
    return {
      needed: true,
      delay: 100,
      reason: 'Medium dataset, light debouncing recommended',
    };
  }

  if (recordCount <= PERFORMANCE_THRESHOLDS.large) {
    return {
      needed: true,
      delay: 150,
      reason: 'Large dataset, moderate debouncing recommended',
    };
  }

  return {
    needed: true,
    delay: 250,
    reason: 'Very large dataset, aggressive debouncing required',
  };
}

/**
 * Measure filter performance
 */
export function measureFilterPerformance(
  rawData: SaleRecord[],
  filters: ActiveFilters,
  filterFn: (data: SaleRecord[], filters: ActiveFilters) => SaleRecord[],
  kpiFn: (data: SaleRecord[]) => ComputedKPIs
): PerformanceMetrics {
  const startTime = performance.now();

  // Filter
  const filterStart = performance.now();
  const filteredData = filterFn(rawData, filters);
  const filterEnd = performance.now();

  // KPI computation
  const kpiStart = performance.now();
  kpiFn(filteredData);
  const kpiEnd = performance.now();

  const endTime = performance.now();

  return {
    filterTime: filterEnd - filterStart,
    recordCount: rawData.length,
    filteredCount: filteredData.length,
    kpiComputeTime: kpiEnd - kpiStart,
    totalTime: endTime - startTime,
  };
}

/**
 * Check if performance is within acceptable bounds
 */
export function isPerformanceAcceptable(metrics: PerformanceMetrics): {
  acceptable: boolean;
  warnings: string[];
} {
  const warnings: string[] = [];
  const FILTER_TIME_THRESHOLD = 200; // 200ms
  const KPI_TIME_THRESHOLD = 100; // 100ms
  const TOTAL_TIME_THRESHOLD = 300; // 300ms

  if (metrics.filterTime > FILTER_TIME_THRESHOLD) {
    warnings.push(
      `Filter time (${metrics.filterTime.toFixed(0)}ms) exceeds threshold (${FILTER_TIME_THRESHOLD}ms)`
    );
  }

  if (metrics.kpiComputeTime > KPI_TIME_THRESHOLD) {
    warnings.push(
      `KPI computation time (${metrics.kpiComputeTime.toFixed(0)}ms) exceeds threshold (${KPI_TIME_THRESHOLD}ms)`
    );
  }

  if (metrics.totalTime > TOTAL_TIME_THRESHOLD) {
    warnings.push(
      `Total time (${metrics.totalTime.toFixed(0)}ms) exceeds threshold (${TOTAL_TIME_THRESHOLD}ms)`
    );
  }

  return {
    acceptable: warnings.length === 0,
    warnings,
  };
}

// ─── Filter Validation ────────────────────────────────────────────────

/**
 * Validate filter values
 */
export function validateFilters(filters: ActiveFilters): {
  valid: boolean;
  errors: string[];
  normalized: Partial<ActiveFilters>;
} {
  const errors: string[] = [];
  const normalized: Partial<ActiveFilters> = {};

  // Validate categories
  if (filters.categories?.length) {
    const validCategories: SaleCategory[] = ['Clothes', 'Shoes', 'Accessories', 'Full Outfit'];
    const invalid = filters.categories.filter((c) => !validCategories.includes(c));
    if (invalid.length > 0) {
      errors.push(`Invalid categories: ${invalid.join(', ')}`);
    }
    normalized.categories = filters.categories.filter((c) => validCategories.includes(c));
  }

  // Validate date range
  if (filters.dateRange) {
    const start = new Date(filters.dateRange.start);
    const end = new Date(filters.dateRange.end);

    if (isNaN(start.getTime())) {
      errors.push('Invalid start date');
    } else if (isNaN(end.getTime())) {
      errors.push('Invalid end date');
    } else if (start > end) {
      errors.push('Start date must be before end date');
    } else {
      normalized.dateRange = filters.dateRange;
    }
  }

  // Validate price range
  if (filters.priceRange) {
    if (filters.priceRange.min < 0) {
      errors.push('Minimum price cannot be negative');
    } else if (filters.priceRange.max < filters.priceRange.min) {
      errors.push('Maximum price must be greater than minimum price');
    } else {
      normalized.priceRange = filters.priceRange;
    }
  }

  // Validate customer segments
  if (filters.customerSegments?.length) {
    const validSegments: CustomerSegment[] = ['New Customer', 'Returning', 'VIP', 'Wholesale'];
    const invalid = filters.customerSegments.filter((s) => !validSegments.includes(s));
    if (invalid.length > 0) {
      errors.push(`Invalid customer segments: ${invalid.join(', ')}`);
    }
    normalized.customerSegments = filters.customerSegments.filter((s) =>
      validSegments.includes(s)
    );
  }

  // Validate margin range
  if (filters.marginRange) {
    const validRanges = ['high', 'healthy', 'atRisk'];
    if (!validRanges.includes(filters.marginRange)) {
      errors.push(`Invalid margin range: ${filters.marginRange}`);
    } else {
      normalized.marginRange = filters.marginRange;
    }
  }

  // Validate return statuses
  if (filters.returnStatuses?.length) {
    const validStatuses: ReturnStatus[] = ['Completed', 'Returned', 'Pending Return'];
    const invalid = filters.returnStatuses.filter((s) => !validStatuses.includes(s));
    if (invalid.length > 0) {
      errors.push(`Invalid return statuses: ${invalid.join(', ')}`);
    }
    normalized.returnStatuses = filters.returnStatuses.filter((s) =>
      validStatuses.includes(s)
    );
  }

  // Copy valid simple filters
  if (filters.productName) {
    normalized.productName = filters.productName;
  }
  if (filters.productTypes?.length) {
    normalized.productTypes = filters.productTypes;
  }

  return {
    valid: errors.length === 0,
    errors,
    normalized,
  };
}

// ─── Filter State Persistence ──────────────────────────────────────────

const STORAGE_KEY = 'confit-sales-filters';

/**
 * Persist filter state to localStorage
 */
export function persistFilters(filters: ActiveFilters): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(filters));
  } catch (error) {
    console.warn('Failed to persist filters:', error);
  }
}

/**
 * Load persisted filter state from localStorage
 */
export function loadPersistedFilters(): ActiveFilters | null {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      const { valid, normalized } = validateFilters(parsed);
      if (valid) {
        return normalized as ActiveFilters;
      }
    }
  } catch (error) {
    console.warn('Failed to load persisted filters:', error);
  }
  return null;
}

/**
 * Clear persisted filter state
 */
export function clearPersistedFilters(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch (error) {
    console.warn('Failed to clear persisted filters:', error);
  }
}

// ─── URL Parameter Sync ────────────────────────────────────────────────

/**
 * Encode filters to URL parameters
 */
export function filtersToURLParams(filters: ActiveFilters): URLSearchParams {
  const params = new URLSearchParams();

  if (filters.categories?.length) {
    params.set('categories', filters.categories.join(','));
  }
  if (filters.dateRange) {
    params.set('dateStart', filters.dateRange.start);
    params.set('dateEnd', filters.dateRange.end);
  }
  if (filters.priceRange) {
    params.set('priceMin', String(filters.priceRange.min));
    params.set('priceMax', String(filters.priceRange.max));
  }
  if (filters.customerSegments?.length) {
    params.set('segments', filters.customerSegments.join(','));
  }
  if (filters.productTypes?.length) {
    params.set('productTypes', filters.productTypes.join(','));
  }
  if (filters.productName) {
    params.set('product', filters.productName);
  }
  if (filters.marginRange) {
    params.set('margin', filters.marginRange);
  }
  if (filters.returnStatuses?.length) {
    params.set('status', filters.returnStatuses.join(','));
  }

  return params;
}

/**
 * Decode filters from URL parameters
 */
export function urlParamsToFilters(params: URLSearchParams): Partial<ActiveFilters> {
  const filters: Partial<ActiveFilters> = {};

  const categories = params.get('categories');
  if (categories) {
    filters.categories = categories.split(',') as SaleCategory[];
  }

  const dateStart = params.get('dateStart');
  const dateEnd = params.get('dateEnd');
  if (dateStart && dateEnd) {
    filters.dateRange = { start: dateStart, end: dateEnd };
  }

  const priceMin = params.get('priceMin');
  const priceMax = params.get('priceMax');
  if (priceMin && priceMax) {
    filters.priceRange = { min: Number(priceMin), max: Number(priceMax) };
  }

  const segments = params.get('segments');
  if (segments) {
    filters.customerSegments = segments.split(',') as CustomerSegment[];
  }

  const productTypes = params.get('productTypes');
  if (productTypes) {
    filters.productTypes = productTypes.split(',');
  }

  const product = params.get('product');
  if (product) {
    filters.productName = product;
  }

  const margin = params.get('margin');
  if (margin && ['high', 'healthy', 'atRisk'].includes(margin)) {
    filters.marginRange = margin as 'high' | 'healthy' | 'atRisk';
  }

  const status = params.get('status');
  if (status) {
    filters.returnStatuses = status.split(',') as ReturnStatus[];
  }

  return filters;
}

export default {
  analyzeEmptyResult,
  getEmptyResultMessage,
  resolveFilterConflict,
  shouldDebounceFilters,
  measureFilterPerformance,
  isPerformanceAcceptable,
  validateFilters,
  persistFilters,
  loadPersistedFilters,
  clearPersistedFilters,
  filtersToURLParams,
  urlParamsToFilters,
};
