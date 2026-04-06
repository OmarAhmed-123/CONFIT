/**
 * CONFIT — Sales Alerts Panel
 * =============================
 * Panel displaying sales alerts integrated with the notification bell.
 * Shows alerts with severity indicators, rich previews, and actions.
 */

import { useMemo, useState } from 'react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Bell,
  Settings,
  History,
  Filter,
  Check,
  Trash2,
  AlertTriangle,
  Package,
  TrendingUp,
  Users,
  DollarSign,
  RotateCcw,
  ChevronDown,
  X,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
  SheetFooter,
} from '@/components/ui/sheet';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { SalesAlertCard } from './SalesAlertCard';
import { useSalesAlertStore } from '@/stores/salesAlertStore';
import {
  type SalesAlert,
  type SalesAlertType,
  type AlertSeverity,
  getSeverityConfig,
  getAlertTypeConfig,
} from '@/types/salesAlertTypes';
import { createTransition } from '@/motion';

// ─── Filter Bar Component ─────────────────────────────────────────────────────

interface AlertFilterBarProps {
  activeType: SalesAlertType | 'all';
  activeSeverity: AlertSeverity | 'all';
  onTypeChange: (type: SalesAlertType | 'all') => void;
  onSeverityChange: (severity: AlertSeverity | 'all') => void;
  onClearFilters: () => void;
}

function AlertFilterBar({
  activeType,
  activeSeverity,
  onTypeChange,
  onSeverityChange,
  onClearFilters,
}: AlertFilterBarProps) {
  const hasFilters = activeType !== 'all' || activeSeverity !== 'all';

  return (
    <div className="flex items-center gap-2 p-3 bg-muted/30 rounded-lg">
      <Filter className="h-4 w-4 text-muted-foreground" />

      {/* Type Filter */}
      <Select value={activeType} onValueChange={(v) => onTypeChange(v as SalesAlertType | 'all')}>
        <SelectTrigger className="h-8 w-[140px] text-xs">
          <SelectValue placeholder="All Types" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Types</SelectItem>
          <SelectItem value="high_value_order">High-Value Orders</SelectItem>
          <SelectItem value="unusual_returns">Return Patterns</SelectItem>
          <SelectItem value="inventory_depletion">Inventory</SelectItem>
          <SelectItem value="conversion_anomaly">Conversion</SelectItem>
          <SelectItem value="customer_segment_change">Customers</SelectItem>
        </SelectContent>
      </Select>

      {/* Severity Filter */}
      <Select value={activeSeverity} onValueChange={(v) => onSeverityChange(v as AlertSeverity | 'all')}>
        <SelectTrigger className="h-8 w-[120px] text-xs">
          <SelectValue placeholder="All Severity" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Severity</SelectItem>
          <SelectItem value="critical">Critical</SelectItem>
          <SelectItem value="warning">Warning</SelectItem>
          <SelectItem value="info">Info</SelectItem>
        </SelectContent>
      </Select>

      {hasFilters && (
        <Button
          variant="ghost"
          size="sm"
          className="h-8 px-2 text-xs"
          onClick={onClearFilters}
        >
          Clear
        </Button>
      )}
    </div>
  );
}

// ─── Alert Summary Stats ──────────────────────────────────────────────────────

interface AlertSummaryProps {
  alerts: SalesAlert[];
}

function AlertSummary({ alerts }: AlertSummaryProps) {
  const stats = useMemo(() => {
    const critical = alerts.filter((a) => a.severity === 'critical' && !a.read).length;
    const warning = alerts.filter((a) => a.severity === 'warning' && !a.read).length;
    const info = alerts.filter((a) => a.severity === 'info' && !a.read).length;
    return { critical, warning, info, total: critical + warning + info };
  }, [alerts]);

  if (stats.total === 0) return null;

  return (
    <div className="flex items-center gap-3 p-3 bg-muted/20 rounded-lg">
      {stats.critical > 0 && (
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-red-500" />
          <span className="text-xs font-medium text-red-400">{stats.critical} Critical</span>
        </div>
      )}
      {stats.warning > 0 && (
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-amber-500" />
          <span className="text-xs font-medium text-amber-400">{stats.warning} Warning</span>
        </div>
      )}
      {stats.info > 0 && (
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-blue-500" />
          <span className="text-xs font-medium text-blue-400">{stats.info} Info</span>
        </div>
      )}
    </div>
  );
}

// ─── Main Panel Component ─────────────────────────────────────────────────────

interface SalesAlertsPanelProps {
  storeId: string;
  className?: string;
  trigger?: React.ReactNode;
}

export function SalesAlertsPanel({ storeId, className, trigger }: SalesAlertsPanelProps) {
  const [open, setOpen] = useState(false);
  const [activeType, setActiveType] = useState<SalesAlertType | 'all'>('all');
  const [activeSeverity, setActiveSeverity] = useState<AlertSeverity | 'all'>('all');

  const store = useSalesAlertStore((s) => ({
    alerts: s.getAlertsForStore(storeId),
    unreadCount: s.getUnreadAlerts(storeId).length,
    markAllRead: () => s.markAllRead(),
  }));

  // Filter alerts
  const filteredAlerts = useMemo(() => {
    let filtered = store.alerts;

    if (activeType !== 'all') {
      filtered = filtered.filter((a) => a.type === activeType);
    }

    if (activeSeverity !== 'all') {
      filtered = filtered.filter((a) => a.severity === activeSeverity);
    }

    // Sort: unread first, then by severity, then by date
    return [...filtered].sort((a, b) => {
      // Unread first
      if (a.read !== b.read) return a.read ? 1 : -1;

      // Severity order
      const severityOrder = { critical: 0, warning: 1, info: 2 };
      const severityDiff = severityOrder[a.severity] - severityOrder[b.severity];
      if (severityDiff !== 0) return severityDiff;

      // Date descending
      return b.created_at.localeCompare(a.created_at);
    });
  }, [store.alerts, activeType, activeSeverity]);

  const handleClearFilters = () => {
    setActiveType('all');
    setActiveSeverity('all');
  };

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        {trigger || (
          <button
            className={cn('relative p-2 rounded-full hover:bg-muted transition-colors', className)}
            title="Sales Alerts"
            aria-label={`Sales Alerts${store.unreadCount > 0 ? ` (${store.unreadCount} unread)` : ''}`}
          >
            <Bell className="h-5 w-5" />
            {store.unreadCount > 0 && (
              <motion.span
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                className="absolute -top-0.5 -right-0.5 h-5 w-5 rounded-full bg-gradient-to-r from-purple-500 to-blue-500 text-white text-[10px] font-bold flex items-center justify-center"
              >
                {store.unreadCount > 9 ? '9+' : store.unreadCount}
              </motion.span>
            )}
          </button>
        )}
      </SheetTrigger>

      <SheetContent side="right" className="w-full sm:max-w-md p-0 flex flex-col">
        {/* Header */}
        <SheetHeader className="p-4 border-b border-border">
          <div className="flex items-center justify-between">
            <SheetTitle className="flex items-center gap-2 text-lg">
              <Bell className="h-5 w-5" />
              Sales Alerts
            </SheetTitle>
            <div className="flex items-center gap-2">
              {store.unreadCount > 0 && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 text-xs gap-1"
                  onClick={store.markAllRead}
                >
                  <Check className="h-3.5 w-3.5" />
                  Mark all read
                </Button>
              )}
              <Link href="/brand-dashboard/settings/alerts">
                <Button variant="ghost" size="icon" className="h-8 w-8" title="Alert Settings">
                  <Settings className="h-4 w-4" />
                </Button>
              </Link>
            </div>
          </div>
        </SheetHeader>

        {/* Summary Stats */}
        <div className="px-4 pt-4">
          <AlertSummary alerts={store.alerts} />
        </div>

        {/* Filters */}
        <div className="px-4 pt-3">
          <AlertFilterBar
            activeType={activeType}
            activeSeverity={activeSeverity}
            onTypeChange={setActiveType}
            onSeverityChange={setActiveSeverity}
            onClearFilters={handleClearFilters}
          />
        </div>

        {/* Alerts List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          <AnimatePresence initial={false}>
            {filteredAlerts.length === 0 ? (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="text-center py-12"
              >
                <div className="w-16 h-16 rounded-full bg-muted/50 flex items-center justify-center mx-auto mb-4">
                  <Bell className="h-8 w-8 text-muted-foreground opacity-50" />
                </div>
                <p className="text-muted-foreground font-medium">No alerts</p>
                <p className="text-xs text-muted-foreground mt-1">
                  You'll be notified about important business events
                </p>
              </motion.div>
            ) : (
              filteredAlerts.slice(0, 50).map((alert) => (
                <SalesAlertCard
                  key={alert.id}
                  alert={alert}
                  onMarkRead={() => setOpen(false)}
                />
              ))
            )}
          </AnimatePresence>
        </div>

        {/* Footer */}
        <SheetFooter className="p-4 border-t border-border">
          <div className="flex items-center gap-2 w-full">
            <Link href="/brand-dashboard/alerts/history" className="flex-1">
              <Button variant="outline" className="w-full">
                <History className="h-4 w-4 mr-2" />
                View History
              </Button>
            </Link>
            <Link href="/brand-dashboard/settings/alerts">
              <Button variant="outline" size="icon">
                <Settings className="h-4 w-4" />
              </Button>
            </Link>
          </div>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}

// ─── Compact Bell Badge Component ─────────────────────────────────────────────

interface SalesAlertBadgeProps {
  storeId: string;
  className?: string;
  onClick?: () => void;
}

export function SalesAlertBadge({ storeId, className, onClick }: SalesAlertBadgeProps) {
  const unreadCount = useSalesAlertStore((s) => s.getUnreadAlerts(storeId).length);
  const criticalCount = useSalesAlertStore((s) => 
    s.getAlertsForStore(storeId).filter((a) => a.severity === 'critical' && !a.read).length
  );

  return (
    <button
      className={cn(
        'relative p-2 rounded-full hover:bg-muted transition-colors',
        className
      )}
      onClick={onClick}
      title="Sales Alerts"
      aria-label={`Sales Alerts${unreadCount > 0 ? ` (${unreadCount} unread)` : ''}`}
    >
      <Bell className="h-5 w-5" />
      {unreadCount > 0 && (
        <motion.span
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          className={cn(
            'absolute -top-0.5 -right-0.5 h-5 w-5 rounded-full text-white text-[10px] font-bold flex items-center justify-center',
            criticalCount > 0
              ? 'bg-gradient-to-r from-red-500 to-amber-500'
              : 'bg-gradient-to-r from-purple-500 to-blue-500'
          )}
        >
          {unreadCount > 9 ? '9+' : unreadCount}
        </motion.span>
      )}
    </button>
  );
}

export default SalesAlertsPanel;
