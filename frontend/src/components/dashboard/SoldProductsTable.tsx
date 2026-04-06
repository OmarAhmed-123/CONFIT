/**
 * CONFIT — Sales Analytics Table (v3)
 * =====================================
 * Production-ready, reusable data table for the Store Owner Dashboard.
 *
 * Features:
 *  - All 8 required columns with thumbnails, category badges, profit margin
 *    color-coding, return status badges, and customer tooltip
 *  - Column sorting with visual direction indicators
 *  - Client-side pagination with rows-per-page selector + direct page input
 *  - Loading skeleton matching CONFIT visual language
 *  - Empty state with clear-filters CTA
 *  - Error state with retry button
 *  - "Recently Sold" gold badge for sales within the last 24 hours
 *  - Row highlight for notification deep-links
 *  - Full ARIA labels and keyboard accessibility
 */

import { useState, useMemo, useCallback, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Package,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  AlertTriangle,
  RefreshCw,
  Sparkles,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import type { SaleRecord, SaleSortField, SortDirection } from '@/types/dashboard';
import { EASE_LUXURY } from '@/motion';

// ─── Status / Category Styling ──────────────────────────────────

const RETURN_STATUS_COLORS: Record<string, string> = {
  Completed: 'bg-green-500/10 text-green-400 border-green-500/20',
  Returned: 'bg-red-500/10 text-red-400 border-red-500/20',
  'Pending Return': 'bg-amber-500/10 text-amber-400 border-amber-500/20',
};

const CATEGORY_COLORS: Record<string, string> = {
  Clothes: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
  Shoes: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  Accessories: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  'Full Outfit': 'bg-accent/10 text-accent border-accent/20',
};

function getMarginColor(margin: number): string {
  if (margin >= 40) return 'text-green-400';
  if (margin >= 20) return 'text-amber-400';
  return 'text-red-400';
}

// ─── Column Definitions ─────────────────────────────────────────

const COLUMNS: { field: SaleSortField; label: string; sortable: boolean; minW?: string }[] = [
  { field: 'productName', label: 'Product Name', sortable: true, minW: '220px' },
  { field: 'category', label: 'Category', sortable: true, minW: '120px' },
  { field: 'price', label: 'Price', sortable: true, minW: '110px' },
  { field: 'quantity', label: 'Qty', sortable: true, minW: '60px' },
  { field: 'customerName', label: 'Customer', sortable: true, minW: '150px' },
  { field: 'saleDate', label: 'Sale Date', sortable: true, minW: '140px' },
  { field: 'profitMargin', label: 'Margin', sortable: true, minW: '90px' },
  { field: 'returnStatus', label: 'Status', sortable: true, minW: '130px' },
];

// ─── Helpers ────────────────────────────────────────────────────

function isRecentSale(saleDate: string): boolean {
  const saleDateMs = new Date(saleDate).getTime();
  const now = Date.now();
  return now - saleDateMs < 24 * 60 * 60 * 1000;
}

// ─── Component Props ────────────────────────────────────────────

export interface SoldProductsTableProps {
  /** Filtered sale records to display */
  data: SaleRecord[];
  /** Show loading skeleton */
  isLoading?: boolean;
  /** Error message to display — renders error state when truthy */
  error?: string | null;
  /** Callback to retry after error */
  onRetry?: () => void;
  /** Row ID to highlight (from notification deep-link) */
  highlightedRowId?: string | null;
  /** Set of sale IDs flagged as "recently sold" via notification system */
  recentSaleIds?: Set<string>;
  /** Callback to clear all active filters (shown in empty state) */
  onClearFilters?: () => void;
  /** Additional CSS class */
  className?: string;
}

export function SoldProductsTable({
  data,
  isLoading = false,
  error,
  onRetry,
  highlightedRowId,
  recentSaleIds,
  onClearFilters,
  className,
}: SoldProductsTableProps) {
  // ─── Sorting ────────────────────────────────────────────────────
  const [sortField, setSortField] = useState<SaleSortField>('saleDate');
  const [sortDir, setSortDir] = useState<SortDirection>('desc');

  const toggleSort = useCallback(
    (field: SaleSortField) => {
      if (sortField === field) {
        setSortDir(d => (d === 'asc' ? 'desc' : 'asc'));
      } else {
        setSortField(field);
        setSortDir('desc');
      }
    },
    [sortField]
  );

  const sorted = useMemo(() => {
    const arr = [...data];
    arr.sort((a, b) => {
      const aVal = a[sortField];
      const bVal = b[sortField];
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortDir === 'asc' ? aVal - bVal : bVal - aVal;
      }
      const aStr = String(aVal || '').toLowerCase();
      const bStr = String(bVal || '').toLowerCase();
      return sortDir === 'asc' ? aStr.localeCompare(bStr) : bStr.localeCompare(aStr);
    });
    return arr;
  }, [data, sortField, sortDir]);

  // ─── Pagination ─────────────────────────────────────────────────
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [pageInput, setPageInput] = useState('1');

  // Reset to page 1 when data or filters change
  useEffect(() => {
    setPage(1);
    setPageInput('1');
  }, [data.length, pageSize]);

  // Sync page input when page changes programmatically
  useEffect(() => {
    setPageInput(String(page));
  }, [page]);

  const totalPages = Math.max(1, Math.ceil(sorted.length / pageSize));
  const paginated = useMemo(
    () => sorted.slice((page - 1) * pageSize, page * pageSize),
    [sorted, page, pageSize]
  );

  const handlePageInputCommit = useCallback(() => {
    const parsed = parseInt(pageInput, 10);
    if (!isNaN(parsed) && parsed >= 1 && parsed <= totalPages) {
      setPage(parsed);
    } else {
      setPageInput(String(page));
    }
  }, [pageInput, totalPages, page]);

  // ─── Highlight Scroll ──────────────────────────────────────────
  const highlightRef = useRef<HTMLTableRowElement>(null);
  useEffect(() => {
    if (highlightedRowId && highlightRef.current) {
      highlightRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [highlightedRowId, paginated]);

  // ─── Formatters ─────────────────────────────────────────────────
  const formatDate = (iso: string) =>
    new Date(iso).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });

  const formatPrice = (value: number) => `EGP ${value.toLocaleString()}`;

  const SortIcon = ({ field }: { field: SaleSortField }) => {
    if (sortField !== field)
      return <ArrowUpDown className="h-3.5 w-3.5 text-muted-foreground/40" />;
    return sortDir === 'asc' ? (
      <ArrowUp className="h-3.5 w-3.5 text-accent" />
    ) : (
      <ArrowDown className="h-3.5 w-3.5 text-accent" />
    );
  };

  // ─── Error State ──────────────────────────────────────────────
  if (error) {
    return (
      <div className={cn('rounded-2xl border border-border/50 p-12 text-center', className)}>
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: EASE_LUXURY }}
        >
          <div className="h-16 w-16 rounded-2xl bg-destructive/10 flex items-center justify-center mx-auto mb-4">
            <AlertTriangle className="h-8 w-8 text-destructive/60" />
          </div>
          <h3 className="text-lg font-semibold text-foreground mb-2 font-sans">
            Unable to Load Sales Data
          </h3>
          <p className="text-sm text-muted-foreground max-w-sm mx-auto mb-6">
            {error || 'Something went wrong while loading your sales data. Please try again.'}
          </p>
          {onRetry && (
            <Button
              onClick={onRetry}
              variant="outline"
              size="sm"
              className="gap-2 border-accent/30 text-accent hover:bg-accent/10"
            >
              <RefreshCw className="h-4 w-4" />
              Try Again
            </Button>
          )}
        </motion.div>
      </div>
    );
  }

  // ─── Loading Skeleton ──────────────────────────────────────────
  if (isLoading) {
    return (
      <div className={cn('space-y-4', className)}>
        <div className="rounded-2xl border border-border/50 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm" role="table" aria-label="Sales data loading">
              <thead>
                <tr className="bg-muted/20 border-b border-border/50">
                  {COLUMNS.map(col => (
                    <th key={col.field} className="px-4 py-3.5 text-left text-muted-foreground/60 font-medium text-xs">
                      {col.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {Array.from({ length: 8 }).map((_, i) => (
                  <tr key={i} className="border-b border-border/30">
                    {COLUMNS.map((col, j) => (
                      <td key={j} className="px-4 py-3.5">
                        <motion.div
                          className="h-4 rounded-md bg-muted/30"
                          style={{ width: col.minW || '80px' }}
                          animate={{ opacity: [0.3, 0.6, 0.3] }}
                          transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut', delay: j * 0.1 }}
                        />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    );
  }

  // ─── Empty State ──────────────────────────────────────────────
  if (sorted.length === 0) {
    return (
      <div className={cn('rounded-2xl border border-border/50 p-12 text-center', className)}>
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: EASE_LUXURY }}
        >
          <div className="h-16 w-16 rounded-2xl bg-muted/20 flex items-center justify-center mx-auto mb-4">
            <Package className="h-8 w-8 text-muted-foreground/40" />
          </div>
          <h3 className="text-lg font-semibold text-foreground mb-2 font-sans">
            No sales found
          </h3>
          <p className="text-sm text-muted-foreground max-w-sm mx-auto mb-6">
            No products match your current filters. Try adjusting your filter criteria or clearing all filters.
          </p>
          {onClearFilters && (
            <Button
              onClick={onClearFilters}
              variant="outline"
              size="sm"
              className="gap-2 border-accent/30 text-accent hover:bg-accent/10"
            >
              <RefreshCw className="h-4 w-4" />
              Clear All Filters
            </Button>
          )}
        </motion.div>
      </div>
    );
  }

  // ─── Main Table ───────────────────────────────────────────────
  return (
    <div className={cn('space-y-4', className)}>
      {/* Results count */}
      <div className="flex items-center justify-between text-sm">
        <span className="text-muted-foreground">
          Showing {(page - 1) * pageSize + 1}–{Math.min(page * pageSize, sorted.length)} of{' '}
          <span className="text-foreground font-medium">{sorted.length}</span> sales
        </span>
      </div>

      {/* Table */}
      <div className="rounded-2xl border border-border/50 overflow-hidden">
        <div className="overflow-x-auto">
          <table
            className="w-full text-sm"
            role="table"
            aria-label="Sales analytics data"
          >
            <thead role="rowgroup">
              <tr className="bg-muted/20 border-b border-border/50" role="row">
                {COLUMNS.map(col => (
                  <th
                    key={col.field}
                    role="columnheader"
                    scope="col"
                    aria-sort={
                      sortField === col.field
                        ? sortDir === 'asc'
                          ? 'ascending'
                          : 'descending'
                        : 'none'
                    }
                    style={{ minWidth: col.minW }}
                    className={cn(
                      'px-4 py-3.5 text-left font-medium text-xs text-muted-foreground',
                      col.sortable && 'cursor-pointer hover:text-foreground transition-colors select-none'
                    )}
                    tabIndex={col.sortable ? 0 : undefined}
                    onClick={() => col.sortable && toggleSort(col.field)}
                    onKeyDown={(e) => {
                      if (col.sortable && (e.key === 'Enter' || e.key === ' ')) {
                        e.preventDefault();
                        toggleSort(col.field);
                      }
                    }}
                  >
                    <span className="flex items-center gap-1.5">
                      {col.label}
                      {col.sortable && <SortIcon field={col.field} />}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody role="rowgroup">
              <AnimatePresence mode="wait">
                {paginated.map((record, i) => {
                  const isHighlighted = record.id === highlightedRowId;
                  const isRecent = recentSaleIds?.has(record.id) || isRecentSale(record.saleDate);
                  return (
                    <motion.tr
                      key={record.id}
                      role="row"
                      ref={isHighlighted ? highlightRef : undefined}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: i * 0.02, duration: 0.3 }}
                      className={cn(
                        'border-b border-border/30 analytics-row-hover',
                        isHighlighted && 'bg-accent/5 ring-1 ring-accent/30'
                      )}
                    >
                      {/* Product Name + Thumbnail + Recently Sold Badge */}
                      <td className="px-4 py-3.5" role="cell">
                        <div className="flex items-center gap-3">
                          <img
                            src={record.thumbnail}
                            alt={record.productName}
                            className="h-10 w-10 rounded-lg object-cover flex-shrink-0 bg-muted/20"
                            loading="lazy"
                          />
                          <div className="min-w-0">
                            <div className="flex items-center gap-2">
                              <p className="font-medium text-foreground truncate">{record.productName}</p>
                              {isRecent && (
                                <span className="sale-new-badge inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-accent/15 text-accent text-[10px] font-semibold flex-shrink-0">
                                  <Sparkles className="h-2.5 w-2.5" />
                                  New
                                </span>
                              )}
                            </div>
                            <p className="text-xs text-muted-foreground font-mono">{record.sku}</p>
                          </div>
                        </div>
                      </td>

                      {/* Category */}
                      <td className="px-4 py-3.5" role="cell">
                        <Badge
                          variant="outline"
                          className={cn('text-xs capitalize', CATEGORY_COLORS[record.category] || '')}
                        >
                          {record.category}
                        </Badge>
                      </td>

                      {/* Price */}
                      <td className="px-4 py-3.5 font-semibold text-foreground whitespace-nowrap" role="cell">
                        {formatPrice(record.price)}
                      </td>

                      {/* Quantity */}
                      <td className="px-4 py-3.5 text-center text-foreground" role="cell">
                        {record.quantity}
                      </td>

                      {/* Customer */}
                      <td className="px-4 py-3.5" role="cell">
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <span className="text-foreground cursor-default truncate block max-w-[140px]">
                              {record.customerName}
                            </span>
                          </TooltipTrigger>
                          <TooltipContent>
                            <div className="text-xs space-y-0.5">
                              <p className="font-medium">{record.customerName}</p>
                              {record.customerEmail && <p className="text-muted-foreground">{record.customerEmail}</p>}
                              <p className="text-muted-foreground">{record.customerSegment}</p>
                            </div>
                          </TooltipContent>
                        </Tooltip>
                      </td>

                      {/* Sale Date */}
                      <td className="px-4 py-3.5 text-muted-foreground whitespace-nowrap text-xs" role="cell">
                        {formatDate(record.saleDate)}
                      </td>

                      {/* Profit Margin */}
                      <td className="px-4 py-3.5" role="cell">
                        <span className={cn('font-semibold', getMarginColor(record.profitMargin))}>
                          {record.profitMargin}%
                        </span>
                      </td>

                      {/* Return Status */}
                      <td className="px-4 py-3.5" role="cell">
                        <Badge
                          variant="outline"
                          className={cn('text-xs', RETURN_STATUS_COLORS[record.returnStatus] || '')}
                        >
                          {record.returnStatus}
                        </Badge>
                      </td>
                    </motion.tr>
                  );
                })}
              </AnimatePresence>
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination Controls */}
      <div
        className="flex flex-col sm:flex-row items-center justify-between gap-3"
        role="navigation"
        aria-label="Table pagination"
      >
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <span>Rows per page</span>
          <Select value={String(pageSize)} onValueChange={v => setPageSize(Number(v))}>
            <SelectTrigger className="h-8 w-[70px] text-xs" aria-label="Rows per page">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="10">10</SelectItem>
              <SelectItem value="25">25</SelectItem>
              <SelectItem value="50">50</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center gap-1">
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            disabled={page === 1}
            onClick={() => setPage(1)}
            aria-label="First page"
          >
            <ChevronsLeft className="h-3.5 w-3.5" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            disabled={page === 1}
            onClick={() => setPage(p => Math.max(1, p - 1))}
            aria-label="Previous page"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
          </Button>

          <span className="px-2 text-sm text-muted-foreground flex items-center gap-1.5">
            Page
            <input
              type="number"
              min={1}
              max={totalPages}
              value={pageInput}
              onChange={e => setPageInput(e.target.value)}
              onBlur={handlePageInputCommit}
              onKeyDown={e => {
                if (e.key === 'Enter') handlePageInputCommit();
              }}
              className="page-input"
              aria-label="Go to page number"
            />
            of <span className="text-foreground font-medium">{totalPages}</span>
          </span>

          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            disabled={page === totalPages}
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            aria-label="Next page"
          >
            <ChevronRight className="h-3.5 w-3.5" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            disabled={page === totalPages}
            onClick={() => setPage(totalPages)}
            aria-label="Last page"
          >
            <ChevronsRight className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>
    </div>
  );
}

export default SoldProductsTable;
