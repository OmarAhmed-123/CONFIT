/**
 * CONFIT — Dashboard Filter Bar
 * ===============================
 * Persistent filter bar with multi-select category, date range, product type,
 * price range slider, customer segment, and removable active filter chips.
 * On mobile: collapses into a slide-up sheet.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Filter,
  X,
  Calendar,
  ChevronDown,
  SlidersHorizontal,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet';
import { Slider } from '@/components/ui/slider';
import { Input } from '@/components/ui/input';
import type {
  SaleCategory,
  DashboardFilters,
  FilterChip,
  DateRangePreset,
} from '@/types/dashboard';
import { createTransition } from '@/motion';

// Available categories
const ALL_CATEGORIES: SaleCategory[] = ['Clothes', 'Shoes', 'Accessories', 'Full Outfit'];
const DATE_PRESETS: { value: DateRangePreset; label: string }[] = [
  { value: 'today', label: 'Today' },
  { value: 'this_week', label: 'This Week' },
  { value: 'this_month', label: 'This Month' },
  { value: 'custom', label: 'Custom Range' },
];
const SEGMENTS = ['all', 'New Customer', 'Returning', 'VIP', 'Wholesale'];

interface DashboardFilterBarProps {
  filters: DashboardFilters;
  activeChips: FilterChip[];
  availableProductTypes: string[];
  onToggleCategory: (cat: SaleCategory) => void;
  onSetDateRange: (range: DateRangePreset) => void;
  onSetCustomDates: (from: string, to: string) => void;
  onSetProductType: (type: string) => void;
  onSetPriceRange: (min: number, max: number) => void;
  onSetCustomerSegment: (seg: string) => void;
  onClearAll: () => void;
}

export function DashboardFilterBar({
  filters,
  activeChips,
  availableProductTypes,
  onToggleCategory,
  onSetDateRange,
  onSetCustomDates,
  onSetProductType,
  onSetPriceRange,
  onSetCustomerSegment,
  onClearAll,
}: DashboardFilterBarProps) {
  const [mobileOpen, setMobileOpen] = useState(false);

  // ─── Debounced Price Range ─────────────────────────────────────
  const [localPrice, setLocalPrice] = useState<[number, number]>([filters.priceMin, filters.priceMax]);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Sync local state when filters reset externally (e.g. Clear All)
  useEffect(() => {
    setLocalPrice([filters.priceMin, filters.priceMax]);
  }, [filters.priceMin, filters.priceMax]);

  const handlePriceSliderChange = useCallback(([min, max]: number[]) => {
    setLocalPrice([min, max]);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => onSetPriceRange(min, max), 250);
  }, [onSetPriceRange]);

  const handlePriceMinInput = useCallback((val: number) => {
    setLocalPrice(prev => [val, prev[1]]);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => onSetPriceRange(val, localPrice[1]), 250);
  }, [onSetPriceRange, localPrice]);

  const handlePriceMaxInput = useCallback((val: number) => {
    setLocalPrice(prev => [prev[0], val]);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => onSetPriceRange(localPrice[0], val), 250);
  }, [onSetPriceRange, localPrice]);

  const filterContent = (
    <div className="space-y-5">
      {/* Row 1: Category + Date Range */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Category Multi-Select */}
        <div>
          <label className="text-xs text-muted-foreground mb-1.5 block font-medium">
            Product Category
          </label>
          <Popover>
            <PopoverTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                className="w-full justify-between h-9 text-xs font-normal"
              >
                {filters.categories.length === 0
                  ? 'All Categories'
                  : `${filters.categories.length} selected`}
                <ChevronDown className="h-3.5 w-3.5 ml-1 text-muted-foreground" />
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-52 p-3" align="start">
              <div className="space-y-2">
                {ALL_CATEGORIES.map(cat => (
                  <label
                    key={cat}
                    className="flex items-center gap-2 cursor-pointer text-sm hover:text-accent transition-colors"
                  >
                    <Checkbox
                      checked={filters.categories.includes(cat)}
                      onCheckedChange={() => onToggleCategory(cat)}
                      className="h-4 w-4"
                    />
                    {cat}
                  </label>
                ))}
              </div>
            </PopoverContent>
          </Popover>
        </div>

        {/* Date Range */}
        <div>
          <label className="text-xs text-muted-foreground mb-1.5 block font-medium">
            Date Range
          </label>
          <Select
            value={filters.dateRange}
            onValueChange={v => onSetDateRange(v as DateRangePreset)}
          >
            <SelectTrigger className="h-9 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {DATE_PRESETS.map(p => (
                <SelectItem key={p.value} value={p.value}>
                  {p.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Product Type */}
        <div>
          <label className="text-xs text-muted-foreground mb-1.5 block font-medium">
            Product Type
          </label>
          <Select value={filters.productType} onValueChange={onSetProductType}>
            <SelectTrigger className="h-9 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              {availableProductTypes.map(t => (
                <SelectItem key={t} value={t}>{t}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Customer Segment */}
        <div>
          <label className="text-xs text-muted-foreground mb-1.5 block font-medium">
            Customer Segment
          </label>
          <Select value={filters.customerSegment} onValueChange={onSetCustomerSegment}>
            <SelectTrigger className="h-9 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {SEGMENTS.map(s => (
                <SelectItem key={s} value={s}>
                  {s === 'all' ? 'All Segments' : s}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Row 2: Price Range + Custom Dates */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Price Range */}
        <div>
          <label className="text-xs text-muted-foreground mb-1.5 block font-medium">
            Price Range (EGP)
          </label>
          <div className="flex items-center gap-3">
            <Input
              type="number"
              value={localPrice[0]}
              onChange={e => handlePriceMinInput(Number(e.target.value) || 0)}
              className="h-8 w-24 text-xs"
              placeholder="Min"
            />
            <div className="flex-1 px-2">
              <Slider
                value={localPrice}
                min={0}
                max={50000}
                step={100}
                onValueChange={handlePriceSliderChange}
                className="w-full"
              />
            </div>
            <Input
              type="number"
              value={localPrice[1]}
              onChange={e => handlePriceMaxInput(Number(e.target.value) || 50000)}
              className="h-8 w-24 text-xs"
              placeholder="Max"
            />
          </div>
        </div>

        {/* Custom Date Inputs */}
        {filters.dateRange === 'custom' && (
          <div>
            <label className="text-xs text-muted-foreground mb-1.5 block font-medium">
              Custom Date Range
            </label>
            <div className="flex items-center gap-2">
              <div className="relative flex-1">
                <Calendar className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                <Input
                  type="date"
                  value={filters.customDateFrom || ''}
                  onChange={e => onSetCustomDates(e.target.value, filters.customDateTo || '')}
                  className="h-8 text-xs pl-8"
                />
              </div>
              <span className="text-xs text-muted-foreground">to</span>
              <div className="relative flex-1">
                <Calendar className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                <Input
                  type="date"
                  value={filters.customDateTo || ''}
                  onChange={e => onSetCustomDates(filters.customDateFrom || '', e.target.value)}
                  className="h-8 text-xs pl-8"
                />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Clear All */}
      {activeChips.length > 0 && (
        <div className="flex justify-end">
          <Button variant="ghost" size="sm" onClick={onClearAll} className="text-xs gap-1.5 text-muted-foreground hover:text-accent">
            <X className="h-3 w-3" />
            Clear All Filters
          </Button>
        </div>
      )}
    </div>
  );

  return (
    <div className="space-y-3">
      {/* Desktop Filter Bar */}
      <div className="hidden md:block">
        <div className="glass-card rounded-2xl p-5 border border-border/50">
          <div className="flex items-center gap-2 mb-4">
            <Filter className="h-4 w-4 text-accent" />
            <span className="text-sm font-medium text-foreground">Filters</span>
            {activeChips.length > 0 && (
              <span className="h-5 w-5 rounded-full bg-accent text-accent-foreground text-[10px] font-bold flex items-center justify-center">
                {activeChips.length}
              </span>
            )}
          </div>
          {filterContent}
        </div>
      </div>

      {/* Mobile Filter Button + Sheet */}
      <div className="md:hidden">
        <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
          <SheetTrigger asChild>
            <Button variant="outline" size="sm" className="w-full gap-2">
              <SlidersHorizontal className="h-4 w-4" />
              Filters
              {activeChips.length > 0 && (
                <span className="h-5 w-5 rounded-full bg-accent text-accent-foreground text-[10px] font-bold flex items-center justify-center">
                  {activeChips.length}
                </span>
              )}
            </Button>
          </SheetTrigger>
          <SheetContent side="bottom" className="h-[85vh] rounded-t-2xl">
            <SheetHeader>
              <SheetTitle className="flex items-center gap-2">
                <Filter className="h-4 w-4 text-accent" />
                Filters
              </SheetTitle>
            </SheetHeader>
            <div className="mt-4 overflow-y-auto max-h-[calc(85vh-80px)] pb-8">
              {filterContent}
            </div>
          </SheetContent>
        </Sheet>
      </div>

      {/* Active Filter Chips */}
      <AnimatePresence>
        {activeChips.length > 0 && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={createTransition({ duration: 0.2 })}
            className="flex flex-wrap gap-2"
          >
            {activeChips.map(chip => (
              <motion.div
                key={chip.key}
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.8, opacity: 0 }}
              >
                <Badge
                  variant="outline"
                  className="gap-1.5 pr-1.5 text-xs bg-accent/5 border-accent/20 text-accent hover:bg-accent/10 cursor-pointer"
                  onClick={chip.onRemove}
                >
                  {chip.label}
                  <X className="h-3 w-3" />
                </Badge>
              </motion.div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default DashboardFilterBar;
