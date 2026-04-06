# Sales Filter System — Integration Guide

## Overview

The Sales Filter System provides centralized, bidirectional filter state management for the Sales Insights Widget and Sales Analytics Table. This system enables real-time synchronization between components while maintaining optimal performance for large datasets.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    salesFilterStore (Zustand)                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ activeFilters: { categories, dateRange, priceRange... }│   │
│  │ filterHistory: FilterSnapshot[]                         │   │
│  │ historyPointer: number                                   │   │
│  │ _rawData: SaleRecord[]                                   │   │
│  │ _computedKPIs: ComputedKPIs | null                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                      │
│           ┌───────────────┼───────────────┐                     │
│           ▼               ▼               ▼                     │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐              │
│  │   Widget    │ │   Table     │ │  External   │              │
│  │ (drill-down)│ │  (filters)  │ │   sources   │              │
│  └─────────────┘ └─────────────┘ └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Basic Integration

```tsx
import { SalesInsightsWidgetConnected } from '@/components/dashboard/SalesInsightsWidgetConnected';
import { SoldProductsTableConnected } from '@/components/dashboard/SoldProductsTableConnected';

function SalesDashboard({ salesData }) {
  return (
    <div>
      {/* Widget with drill-down */}
      <SalesInsightsWidgetConnected 
        data={salesData}
        showHistoryControls
        showFilterIndicator
      />
      
      {/* Table with filter controls */}
      <SoldProductsTableConnected 
        data={salesData}
        showFilterControls
        showFilterChips
      />
    </div>
  );
}
```

### 2. Using the Sync Hook

```tsx
import { useSalesFilterSync } from '@/hooks/useSalesFilterSync';

function CustomSalesDashboard({ rawData }) {
  const {
    filteredData,
    kpis,
    activeFilters,
    drillDownByProduct,
    drillDownByCategory,
    undo,
    redo,
    canUndo,
    canRedo,
    isTransitioning,
  } = useSalesFilterSync({
    rawData,
    enableDebounce: rawData.length > 10000,
    onFiltersChange: (filters, data) => {
      console.log('Filters changed:', filters);
    },
  });

  return (
    <div>
      <div>Total Revenue: {kpis.totalRevenue}</div>
      <button onClick={() => drillDownByProduct('Premium Dress')}>
        Filter by Premium Dress
      </button>
      <button onClick={undo} disabled={!canUndo}>Undo</button>
    </div>
  );
}
```

## Core Components

### Filter Store (`salesFilterStore.ts`)

The centralized Zustand store managing all filter state.

**State:**
- `activeFilters` — Current filter values
- `filterHistory` — Immutable snapshots for undo/redo
- `historyPointer` — Current position in history
- `_rawData` — Reference to raw sales data
- `_computedKPIs` — Memoized KPI cache

**Actions:**
- `updateFilter(type, value)` — Update a specific filter
- `updateFilters(updates)` — Batch update multiple filters
- `clearFilter(type)` — Clear a specific filter
- `clearAllFilters()` — Reset all filters
- `toggleCategory(category)` — Toggle category (additive)
- `setDateRange(start, end)` — Set date range
- `setProductName(name)` — Drill-down by product
- `setMarginRange(range)` — Drill-down by margin
- `setReturnStatuses(statuses)` — Drill-down by return status
- `undo()` / `redo()` — Navigate history

**Selectors:**
- `getFilteredData()` — Returns filtered dataset
- `getComputedKPIs()` — Returns memoized KPIs
- `hasActiveFilters()` — Boolean check
- `getActiveFilterCount()` — Number of active filters
- `getFilterChips()` — UI-friendly filter chips

### Convenience Hooks

```tsx
// Filter state and actions
const { activeFilters, updateFilter, clearAllFilters } = useSalesFilters();

// Undo/redo functionality
const { undo, redo, canUndo, canRedo } = useFilterHistory();

// Computed KPIs (memoized)
const { kpis, filteredData } = useComputedKPIs();

// Loading state
const { isLoading, setLoading, setRawData } = useSalesDataLoading();
```

## Filter Types

```typescript
interface ActiveFilters {
  categories: SaleCategory[] | null;        // ['Clothes', 'Shoes']
  dateRange: DateRangeFilter | null;        // { start: '2024-01-01', end: '2024-12-31' }
  priceRange: PriceRangeFilter | null;      // { min: 0, max: 50000 }
  customerSegments: CustomerSegment[] | null; // ['VIP', 'Wholesale']
  productTypes: string[] | null;            // ['Tops', 'Dresses']
  productName: string | null;               // Drill-down: specific product
  marginRange: 'high' | 'healthy' | 'atRisk' | null; // Drill-down: margin category
  returnStatuses: ReturnStatus[] | null;    // Drill-down: return status
}
```

## Computed KPIs

The system automatically computes these KPIs from filtered data:

```typescript
interface ComputedKPIs {
  totalRevenue: number;           // Sum of price * quantity
  revenueTrend: RevenueTrendData[]; // Daily/weekly revenue breakdown
  trendPercent: number;           // % change (first half vs second half)
  topProducts: TopProduct[];      // Top 5 products by revenue
  avgMargin: number;              // Average profit margin
  marginDistribution: MarginDistribution[]; // High/healthy/atRisk breakdown
  returnRate: ReturnRateData;     // Return rate with status
  filteredCount: number;          // Number of filtered records
  lastComputed: string;           // Timestamp of computation
}
```

## Performance Optimization

### Memoization Strategy

1. **KPI Cache** — Computed KPIs are cached in `_computedKPIs` and only recalculated when filters or data change
2. **Selector Stability** — All selectors return stable references
3. **History Depth** — Limited to 20 snapshots to prevent memory bloat

### Large Dataset Handling

```tsx
// Automatic debouncing for 10,000+ records
const { filteredData } = useSalesFilterSync({
  rawData: largeDataset,
  enableDebounce: true,
  debounceDelay: 150, // ms
});
```

### Performance Thresholds

| Dataset Size | Debounce Delay | Strategy |
|-------------|----------------|----------|
| < 1,000 | None | Real-time |
| 1,000 - 10,000 | 100ms | Light debounce |
| 10,000 - 50,000 | 150ms | Moderate debounce |
| 50,000+ | 250ms | Aggressive debounce |

## Undo/Redo System

### How It Works

1. Each filter change creates an immutable snapshot
2. Snapshots are stored in `filterHistory` (max 20)
3. `historyPointer` tracks current position
4. `undo()` moves pointer back, `redo()` moves forward

### UI Integration

```tsx
import { HistoryControls } from '@/components/dashboard/SoldProductsTableConnected';

function FilterBar() {
  return (
    <div className="flex items-center gap-2">
      <HistoryControls />
    </div>
  );
}
```

## Bidirectional Sync

### Widget → Table (Drill-Down)

When user clicks on a widget element:

```tsx
// Click on "Premium Dress" in Top Products chart
drillDownByProduct('Premium Dress');

// Click on "High Margin" segment in donut chart
drillDownByMarginRange('high');

// Click on revenue trend point
drillDownByDateSegment('2024-03-01', '2024-03-07');
```

### Table → Widget (Filter Update)

When user applies filters in the table:

```tsx
// Toggle category filter
toggleCategory('Clothes');

// Set price range
setPriceRange(5000, 20000);

// Clear all filters
clearAllFilters();
```

Both directions trigger KPI recalculation automatically.

## Animated Transitions

### Using Transition Components

```tsx
import {
  AnimatedMetricValue,
  FilterTransitionWrapper,
  StaggeredKPIGrid,
} from '@/components/dashboard/FilterTransitionComponents';

function KPICard({ value, previousValue }) {
  return (
    <FilterTransitionWrapper filterKey={value}>
      <AnimatedMetricValue
        value={value}
        previousValue={previousValue}
        formatFn={(v) => `EGP ${v.toLocaleString()}`}
        highlightColor="#D4AF37"
      />
    </FilterTransitionWrapper>
  );
}
```

### Animation Variants

- `filterTransitionVariants` — Card/container transitions
- `valueChangeVariants` — Number/value transitions
- `staggerContainerVariants` — Staggered grid animations

## Edge Cases

### Empty Results

```tsx
import { analyzeEmptyResult, getEmptyResultMessage } from '@/utils/salesFilterEdgeCases';

const context = analyzeEmptyResult(activeFilters, rawData);
const { title, description } = getEmptyResultMessage(context);

// context.suggestions contains actionable suggestions
```

### Filter Conflicts

```tsx
import { resolveFilterConflict } from '@/utils/salesFilterEdgeCases';

const resolution = resolveFilterConflict(
  currentFilters,
  'categories',
  'Clothes',
  'smart' // 'replace' | 'merge' | 'smart'
);

// resolution.action: 'replace' | 'merge' | 'add' | 'reject'
// resolution.resolvedFilters: Partial<ActiveFilters>
```

### Performance Monitoring

```tsx
import { measureFilterPerformance, isPerformanceAcceptable } from '@/utils/salesFilterEdgeCases';

const metrics = measureFilterPerformance(rawData, filters, filterFn, kpiFn);
const { acceptable, warnings } = isPerformanceAcceptable(metrics);

// metrics.filterTime, metrics.kpiComputeTime, metrics.totalTime
```

## Persistence

### LocalStorage

The store automatically persists to `localStorage` via Zustand's persist middleware.

### URL Parameters

```tsx
import { filtersToURLParams, urlParamsToFilters } from '@/utils/salesFilterEdgeCases';

// Encode to URL
const params = filtersToURLParams(activeFilters);
window.history.replaceState(null, '', `?${params}`);

// Decode from URL
const filters = urlParamsToFilters(new URLSearchParams(window.location.search));
```

## Testing

### Unit Tests

```tsx
import { useSalesFilterStore } from '@/stores';

test('should update filter and invalidate KPI cache', () => {
  const store = useSalesFilterStore.getState();
  
  store.setRawData(mockData);
  store.updateFilter('categories', ['Clothes']);
  
  expect(store.activeFilters.categories).toEqual(['Clothes']);
  expect(store._computedKPIs).toBeNull(); // Cache invalidated
});
```

### Integration Tests

```tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { SalesInsightsWidgetConnected } from '@/components/dashboard/SalesInsightsWidgetConnected';

test('drill-down from widget updates table filters', async () => {
  render(<SalesInsightsWidgetConnected data={mockData} />);
  
  // Click on product bar
  await fireEvent.click(screen.getByText('Premium Dress'));
  
  // Verify filter was applied
  const store = useSalesFilterStore.getState();
  expect(store.activeFilters.productName).toBe('Premium Dress');
});
```

## Best Practices

1. **Use Connected Components** — Prefer `SalesInsightsWidgetConnected` and `SoldProductsTableConnected` over base components
2. **Enable Debouncing** — For datasets > 10,000 records, always enable debouncing
3. **Handle Empty States** — Use `analyzeEmptyResult()` to provide helpful suggestions
4. **Show History Controls** — Give users undo/redo capability for filter exploration
5. **Animate Transitions** — Use transition components for smooth UX
6. **Monitor Performance** — Check `isPerformanceAcceptable()` in development

## File Reference

| File | Purpose |
|------|---------|
| `src/stores/salesFilterStore.ts` | Zustand store with undo/redo |
| `src/hooks/useSalesFilterSync.ts` | Bidirectional sync hook |
| `src/components/dashboard/SalesInsightsWidgetConnected.tsx` | Connected widget |
| `src/components/dashboard/SoldProductsTableConnected.tsx` | Connected table |
| `src/components/dashboard/FilterTransitionComponents.tsx` | Animation components |
| `src/utils/salesFilterEdgeCases.ts` | Edge case handlers |

## Migration from Legacy

If migrating from the old `useSalesInsightsDrillDown` hook:

```tsx
// Old
import { useSalesInsightsDrillDown } from '@/hooks/useSalesInsightsDrillDown';

// New
import { useSalesFilterSync, useWidgetDrillDown } from '@/hooks/useSalesFilterSync';

const { handleDrillDown } = useWidgetDrillDown({
  onDrillDown: (filters) => {
    // Custom handling
  },
});
```

The new system provides the same drill-down functionality with added undo/redo, persistence, and performance optimization.
