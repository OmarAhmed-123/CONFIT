/**
 * CONFIT — Alert History Page
 * =============================
 * Dedicated page for viewing and managing alert history.
 * Features search, filtering, sorting, and CSV export.
 */

import { useState, useMemo, useCallback } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  History,
  Search,
  Filter,
  Download,
  Trash2,
  Check,
  X,
  ChevronLeft,
  ChevronRight,
  Calendar,
  AlertTriangle,
  AlertCircle,
  Info,
  Clock,
  ArrowUpDown,
  ExternalLink,
  FileDown,
  MoreHorizontal,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { Calendar as CalendarComponent } from '@/components/ui/calendar';
import { SalesAlertCard } from '@/components/alerts/SalesAlertCard';
import { useSalesAlertStore } from '@/stores/salesAlertStore';
import {
  type SalesAlert,
  type SalesAlertType,
  type AlertSeverity,
  type AlertStatus,
  type AlertHistoryFilter,
  type AlertHistorySort,
  getSeverityConfig,
  getAlertTypeConfig,
} from '@/types/salesAlertTypes';
import { createTransition } from '@/motion';

// ─── Constants ────────────────────────────────────────────────────────────────

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

const TYPE_OPTIONS: { value: SalesAlertType | 'all'; label: string }[] = [
  { value: 'all', label: 'All Types' },
  { value: 'high_value_order', label: 'High-Value Orders' },
  { value: 'unusual_returns', label: 'Return Patterns' },
  { value: 'inventory_depletion', label: 'Inventory' },
  { value: 'conversion_anomaly', label: 'Conversion' },
  { value: 'customer_segment_change', label: 'Customers' },
];

const SEVERITY_OPTIONS: { value: AlertSeverity | 'all'; label: string }[] = [
  { value: 'all', label: 'All Severity' },
  { value: 'critical', label: 'Critical' },
  { value: 'warning', label: 'Warning' },
  { value: 'info', label: 'Info' },
];

const STATUS_OPTIONS: { value: AlertStatus | 'all'; label: string }[] = [
  { value: 'all', label: 'All Status' },
  { value: 'active', label: 'Active' },
  { value: 'acknowledged', label: 'Acknowledged' },
  { value: 'resolved', label: 'Resolved' },
  { value: 'dismissed', label: 'Dismissed' },
];

// ─── Export to CSV ────────────────────────────────────────────────────────────

function exportAlertsToCSV(alerts: SalesAlert[], filename: string = 'alerts-export.csv'): void {
  const headers = [
    'ID',
    'Type',
    'Severity',
    'Status',
    'Title',
    'Rich Preview',
    'Store ID',
    'Store Name',
    'Created At',
    'Read',
    'Dismissed',
  ];

  const rows = alerts.map((alert) => [
    alert.id,
    alert.type,
    alert.severity,
    alert.status,
    `"${alert.title.replace(/"/g, '""')}"`,
    `"${alert.rich_preview.replace(/"/g, '""')}"`,
    alert.store_id,
    alert.store_name,
    alert.created_at,
    alert.read ? 'Yes' : 'No',
    alert.dismissed ? 'Yes' : 'No',
  ]);

  const csv = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

// ─── Filter Panel Component ───────────────────────────────────────────────────

interface FilterPanelProps {
  filters: AlertHistoryFilter;
  onFilterChange: (filters: AlertHistoryFilter) => void;
  onClearFilters: () => void;
}

function FilterPanel({ filters, onFilterChange, onClearFilters }: FilterPanelProps) {
  const hasActiveFilters = useMemo(() => {
    return (
      (filters.types && filters.types.length > 0) ||
      (filters.severities && filters.severities.length > 0) ||
      (filters.statuses && filters.statuses.length > 0) ||
      filters.date_from ||
      filters.date_to ||
      filters.read !== undefined ||
      filters.search
    );
  }, [filters]);

  return (
    <div className="flex flex-wrap items-center gap-3 p-4 bg-muted/20 rounded-xl">
      {/* Search */}
      <div className="relative flex-1 min-w-[200px]">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search alerts..."
          value={filters.search || ''}
          onChange={(e) => onFilterChange({ ...filters, search: e.target.value || undefined })}
          className="pl-9 h-9"
        />
      </div>

      {/* Type Filter */}
      <Select
        value={filters.types?.[0] || 'all'}
        onValueChange={(v) =>
          onFilterChange({
            ...filters,
            types: v === 'all' ? undefined : [v as SalesAlertType],
          })
        }
      >
        <SelectTrigger className="w-[150px] h-9">
          <SelectValue placeholder="Type" />
        </SelectTrigger>
        <SelectContent>
          {TYPE_OPTIONS.map((opt) => (
            <SelectItem key={opt.value} value={opt.value}>
              {opt.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* Severity Filter */}
      <Select
        value={filters.severities?.[0] || 'all'}
        onValueChange={(v) =>
          onFilterChange({
            ...filters,
            severities: v === 'all' ? undefined : [v as AlertSeverity],
          })
        }
      >
        <SelectTrigger className="w-[130px] h-9">
          <SelectValue placeholder="Severity" />
        </SelectTrigger>
        <SelectContent>
          {SEVERITY_OPTIONS.map((opt) => (
            <SelectItem key={opt.value} value={opt.value}>
              {opt.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* Status Filter */}
      <Select
        value={filters.statuses?.[0] || 'all'}
        onValueChange={(v) =>
          onFilterChange({
            ...filters,
            statuses: v === 'all' ? undefined : [v as AlertStatus],
          })
        }
      >
        <SelectTrigger className="w-[130px] h-9">
          <SelectValue placeholder="Status" />
        </SelectTrigger>
        <SelectContent>
          {STATUS_OPTIONS.map((opt) => (
            <SelectItem key={opt.value} value={opt.value}>
              {opt.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* Date Range */}
      <Popover>
        <PopoverTrigger asChild>
          <Button variant="outline" size="sm" className="h-9 gap-1">
            <Calendar className="h-4 w-4" />
            Date Range
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-auto p-0" align="end">
          <div className="p-3 space-y-3">
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">From</label>
              <Input
                type="date"
                value={filters.date_from || ''}
                onChange={(e) =>
                  onFilterChange({ ...filters, date_from: e.target.value || undefined })
                }
                className="h-8"
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">To</label>
              <Input
                type="date"
                value={filters.date_to || ''}
                onChange={(e) =>
                  onFilterChange({ ...filters, date_to: e.target.value || undefined })
                }
                className="h-8"
              />
            </div>
          </div>
        </PopoverContent>
      </Popover>

      {/* Read/Unread */}
      <Select
        value={filters.read === undefined ? 'all' : filters.read ? 'read' : 'unread'}
        onValueChange={(v) =>
          onFilterChange({
            ...filters,
            read: v === 'all' ? undefined : v === 'read',
          })
        }
      >
        <SelectTrigger className="w-[110px] h-9">
          <SelectValue placeholder="Read Status" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All</SelectItem>
          <SelectItem value="unread">Unread</SelectItem>
          <SelectItem value="read">Read</SelectItem>
        </SelectContent>
      </Select>

      {/* Clear Filters */}
      {hasActiveFilters && (
        <Button variant="ghost" size="sm" className="h-9" onClick={onClearFilters}>
          <X className="h-4 w-4 mr-1" />
          Clear
        </Button>
      )}
    </div>
  );
}

// ─── Pagination Component ─────────────────────────────────────────────────────

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  pageSize: number;
  totalItems: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (size: number) => void;
}

function Pagination({
  currentPage,
  totalPages,
  pageSize,
  totalItems,
  onPageChange,
  onPageSizeChange,
}: PaginationProps) {
  const startItem = (currentPage - 1) * pageSize + 1;
  const endItem = Math.min(currentPage * pageSize, totalItems);

  return (
    <div className="flex items-center justify-between px-4 py-3 border-t border-border">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <span>
          Showing {startItem}-{endItem} of {totalItems}
        </span>
        <Select value={String(pageSize)} onValueChange={(v) => onPageSizeChange(parseInt(v))}>
          <SelectTrigger className="w-[70px] h-8">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {PAGE_SIZE_OPTIONS.map((size) => (
              <SelectItem key={size} value={String(size)}>
                {size}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <span>per page</span>
      </div>

      <div className="flex items-center gap-1">
        <Button
          variant="outline"
          size="icon"
          className="h-8 w-8"
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage <= 1}
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>

        {/* Page Numbers */}
        <div className="flex items-center gap-1">
          {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
            let pageNum: number;
            if (totalPages <= 5) {
              pageNum = i + 1;
            } else if (currentPage <= 3) {
              pageNum = i + 1;
            } else if (currentPage >= totalPages - 2) {
              pageNum = totalPages - 4 + i;
            } else {
              pageNum = currentPage - 2 + i;
            }

            return (
              <Button
                key={pageNum}
                variant={currentPage === pageNum ? 'default' : 'outline'}
                size="icon"
                className={cn(
                  'h-8 w-8',
                  currentPage === pageNum &&
                    'bg-gradient-to-r from-purple-600 to-blue-600'
                )}
                onClick={() => onPageChange(pageNum)}
              >
                {pageNum}
              </Button>
            );
          })}
        </div>

        <Button
          variant="outline"
          size="icon"
          className="h-8 w-8"
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage >= totalPages}
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

// ─── Main Alert History Page ──────────────────────────────────────────────────

interface AlertHistoryPageProps {
  storeId?: string;
}

export function AlertHistoryPage({ storeId = 'default-store' }: AlertHistoryPageProps) {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [filters, setFilters] = useState<AlertHistoryFilter>({});
  const [sort, setSort] = useState<AlertHistorySort>({
    field: 'created_at',
    direction: 'desc',
  });
  const [selectedAlerts, setSelectedAlerts] = useState<Set<string>>(new Set());

  const store = useSalesAlertStore((s) => ({
    alerts: s.getFilteredHistory(storeId, filters, sort),
    markAllRead: s.markAllRead,
    clearAlerts: () => s.clearAlerts(storeId),
  }));

  // Paginated alerts
  const paginatedAlerts = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    const end = start + pageSize;
    return store.alerts.slice(start, end);
  }, [store.alerts, currentPage, pageSize]);

  const totalPages = Math.ceil(store.alerts.length / pageSize);

  // Handlers
  const handleFilterChange = useCallback((newFilters: AlertHistoryFilter) => {
    setFilters(newFilters);
    setCurrentPage(1);
    setSelectedAlerts(new Set());
  }, []);

  const handleClearFilters = useCallback(() => {
    setFilters({});
    setCurrentPage(1);
    setSelectedAlerts(new Set());
  }, []);

  const handleSortChange = useCallback((field: AlertHistorySort['field']) => {
    setSort((prev) => ({
      field,
      direction: prev.field === field && prev.direction === 'desc' ? 'asc' : 'desc',
    }));
  }, []);

  const handlePageSizeChange = useCallback((size: number) => {
    setPageSize(size);
    setCurrentPage(1);
  }, []);

  const handleExport = useCallback(() => {
    const alertsToExport = selectedAlerts.size > 0
      ? store.alerts.filter((a) => selectedAlerts.has(a.id))
      : store.alerts;
    
    const timestamp = new Date().toISOString().split('T')[0];
    exportAlertsToCSV(alertsToExport, `confit-alerts-${timestamp}.csv`);
  }, [store.alerts, selectedAlerts]);

  const handleSelectAll = useCallback(() => {
    if (selectedAlerts.size === paginatedAlerts.length) {
      setSelectedAlerts(new Set());
    } else {
      setSelectedAlerts(new Set(paginatedAlerts.map((a) => a.id)));
    }
  }, [paginatedAlerts, selectedAlerts.size]);

  const handleSelectAlert = useCallback((alertId: string) => {
    setSelectedAlerts((prev) => {
      const next = new Set(prev);
      if (next.has(alertId)) {
        next.delete(alertId);
      } else {
        next.add(alertId);
      }
      return next;
    });
  }, []);

  const handleBulkMarkRead = useCallback(() => {
    store.markAllRead();
    setSelectedAlerts(new Set());
  }, [store]);

  const handleBulkDismiss = useCallback(() => {
    // Would call bulk dismiss API
    setSelectedAlerts(new Set());
  }, []);

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold flex items-center gap-3">
            <History className="h-6 w-6 text-purple-400" />
            Alert History
          </h1>
          <p className="text-muted-foreground mt-1">
            View and manage all sales alerts from the past 30 days
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link href="/brand-dashboard/settings/alerts">
            <Button variant="outline" size="sm">
              Alert Settings
            </Button>
          </Link>
          <Button
            variant="outline"
            size="sm"
            onClick={handleExport}
            className="gap-1"
          >
            <FileDown className="h-4 w-4" />
            Export CSV
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[
          {
            label: 'Total Alerts',
            value: store.alerts.length,
            icon: <History className="h-4 w-4" />,
            color: 'text-purple-400',
            bg: 'bg-purple-500/10',
          },
          {
            label: 'Critical',
            value: store.alerts.filter((a) => a.severity === 'critical').length,
            icon: <AlertTriangle className="h-4 w-4" />,
            color: 'text-red-400',
            bg: 'bg-red-500/10',
          },
          {
            label: 'Warning',
            value: store.alerts.filter((a) => a.severity === 'warning').length,
            icon: <AlertCircle className="h-4 w-4" />,
            color: 'text-amber-400',
            bg: 'bg-amber-500/10',
          },
          {
            label: 'Unread',
            value: store.alerts.filter((a) => !a.read).length,
            icon: <Clock className="h-4 w-4" />,
            color: 'text-blue-400',
            bg: 'bg-blue-500/10',
          },
        ].map((stat) => (
          <Card key={stat.label} className="bg-muted/20 border-border/50">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className={cn('w-10 h-10 rounded-lg flex items-center justify-center', stat.bg)}>
                  <span className={stat.color}>{stat.icon}</span>
                </div>
                <div>
                  <p className="text-2xl font-semibold">{stat.value}</p>
                  <p className="text-xs text-muted-foreground">{stat.label}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Filters */}
      <FilterPanel
        filters={filters}
        onFilterChange={handleFilterChange}
        onClearFilters={handleClearFilters}
      />

      {/* Bulk Actions */}
      {selectedAlerts.size > 0 && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-3 p-3 bg-purple-500/10 border border-purple-500/30 rounded-lg"
        >
          <span className="text-sm font-medium text-purple-400">
            {selectedAlerts.size} selected
          </span>
          <div className="flex items-center gap-2">
            <Button size="sm" variant="outline" onClick={handleBulkMarkRead}>
              <Check className="h-4 w-4 mr-1" />
              Mark Read
            </Button>
            <Button size="sm" variant="outline" onClick={handleBulkDismiss}>
              <X className="h-4 w-4 mr-1" />
              Dismiss
            </Button>
            <Button size="sm" variant="outline" onClick={() => setSelectedAlerts(new Set())}>
              Clear Selection
            </Button>
          </div>
        </motion.div>
      )}

      {/* Table/List Header */}
      <div className="flex items-center gap-4 px-4 py-2 bg-muted/30 rounded-t-lg border border-border/50 border-b-0">
        <input
          type="checkbox"
          checked={selectedAlerts.size === paginatedAlerts.length && paginatedAlerts.length > 0}
          onChange={handleSelectAll}
          className="rounded border-border"
          title="Select all alerts on this page"
          aria-label="Select all alerts on this page"
        />
        <div className="flex-1 grid grid-cols-12 gap-4 text-xs font-medium text-muted-foreground">
          <div
            className="col-span-4 cursor-pointer hover:text-foreground flex items-center gap-1"
            onClick={() => handleSortChange('type')}
          >
            Alert
            <ArrowUpDown className="h-3 w-3" />
          </div>
          <div
            className="col-span-2 cursor-pointer hover:text-foreground flex items-center gap-1"
            onClick={() => handleSortChange('severity')}
          >
            Severity
            <ArrowUpDown className="h-3 w-3" />
          </div>
          <div className="col-span-2">Status</div>
          <div
            className="col-span-3 cursor-pointer hover:text-foreground flex items-center gap-1"
            onClick={() => handleSortChange('created_at')}
          >
            Time
            <ArrowUpDown className="h-3 w-3" />
          </div>
          <div className="col-span-1">Actions</div>
        </div>
      </div>

      {/* Alert List */}
      <div className="border border-border/50 rounded-b-lg divide-y divide-border/50">
        <AnimatePresence initial={false}>
          {paginatedAlerts.length === 0 ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-center py-12"
            >
              <History className="h-12 w-12 text-muted-foreground mx-auto mb-4 opacity-50" />
              <p className="text-muted-foreground">No alerts match your filters</p>
              <Button
                variant="link"
                size="sm"
                onClick={handleClearFilters}
                className="mt-2"
              >
                Clear filters
              </Button>
            </motion.div>
          ) : (
            paginatedAlerts.map((alert) => (
              <motion.div
                key={alert.id}
                layout
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className={cn(
                  'flex items-center gap-4 px-4 py-3 hover:bg-muted/20 transition-colors',
                  selectedAlerts.has(alert.id) && 'bg-purple-500/5'
                )}
              >
                <input
                  type="checkbox"
                  checked={selectedAlerts.has(alert.id)}
                  onChange={() => handleSelectAlert(alert.id)}
                  className="rounded border-border"
                  title={`Select alert ${alert.id}`}
                  aria-label={`Select alert ${alert.id}`}
                />
                <div className="flex-1 grid grid-cols-12 gap-4 items-center">
                  <div className="col-span-4">
                    <SalesAlertCard alert={alert} compact showActions={false} />
                  </div>
                  <div className="col-span-2">
                    <Badge
                      variant="outline"
                      className={cn(
                        'text-xs',
                        alert.severity === 'critical' && 'bg-red-500/20 text-red-400 border-red-500/30',
                        alert.severity === 'warning' && 'bg-amber-500/20 text-amber-400 border-amber-500/30',
                        alert.severity === 'info' && 'bg-blue-500/20 text-blue-400 border-blue-500/30'
                      )}
                    >
                      {alert.severity}
                    </Badge>
                  </div>
                  <div className="col-span-2">
                    <Badge variant="outline" className="text-xs">
                      {alert.status}
                    </Badge>
                  </div>
                  <div className="col-span-3 text-xs text-muted-foreground">
                    {new Date(alert.created_at).toLocaleString()}
                  </div>
                  <div className="col-span-1">
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon" className="h-8 w-8">
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        {alert.actions
                          .filter((a) => a.type !== 'dismiss')
                          .map((action, idx) => (
                            <DropdownMenuItem
                              key={idx}
                              onClick={() => {
                                if (action.target_path) {
                                  router.push(action.target_path);
                                }
                              }}
                            >
                              <ExternalLink className="h-4 w-4 mr-2" />
                              {action.label}
                            </DropdownMenuItem>
                          ))}
                        <DropdownMenuSeparator />
                        <DropdownMenuItem onClick={() => handleSelectAlert(alert.id)}>
                          <X className="h-4 w-4 mr-2" />
                          Dismiss
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </div>
              </motion.div>
            ))
          )}
        </AnimatePresence>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <Pagination
          currentPage={currentPage}
          totalPages={totalPages}
          pageSize={pageSize}
          totalItems={store.alerts.length}
          onPageChange={setCurrentPage}
          onPageSizeChange={handlePageSizeChange}
        />
      )}
    </div>
  );
}

export default AlertHistoryPage;
