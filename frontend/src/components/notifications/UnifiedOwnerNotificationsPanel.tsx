/**
 * CONFIT — Unified Owner Notifications Panel
 * ============================================
 * Combined panel for regular notifications and sales alerts.
 * Features tabbed interface to switch between notification types.
 */

import { useMemo, useState } from 'react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Bell,
  BellRing,
  Wifi,
  WifiOff,
  Settings,
  History,
  AlertTriangle,
  Package,
  TrendingUp,
  Users,
  DollarSign,
  RotateCcw,
  Check,
  ExternalLink,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useOwnerNotifications } from '@/hooks/useOwnerNotifications';
import { useSalesAlertStore } from '@/stores/salesAlertStore';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger, SheetFooter } from '@/components/ui/sheet';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { OwnerNotificationCard } from './OwnerNotificationCard';
import { PickupNotificationCard } from './PickupNotificationCard';
import { SalesAlertCard, SalesAlertToast } from '@/components/alerts';
import { createTransition } from '@/motion';
import { type AlertSeverity } from '@/types/salesAlertTypes';

// ─── Tab Configuration ────────────────────────────────────────────────────────

const TAB_CONFIG = {
  all: { label: 'All', icon: Bell },
  alerts: { label: 'Alerts', icon: AlertTriangle },
  orders: { label: 'Orders', icon: Package },
};

// ─── Severity Summary Component ───────────────────────────────────────────────

function AlertSeveritySummary({ storeId }: { storeId: string }) {
  const alerts = useSalesAlertStore((s) => s.getAlertsForStore(storeId));

  const counts = useMemo(() => {
    const unread = alerts.filter((a) => !a.read);
    return {
      critical: unread.filter((a) => a.severity === 'critical').length,
      warning: unread.filter((a) => a.severity === 'warning').length,
      info: unread.filter((a) => a.severity === 'info').length,
    };
  }, [alerts]);

  if (counts.critical + counts.warning + counts.info === 0) return null;

  return (
    <div className="flex items-center gap-3 px-4 py-2 bg-muted/20 rounded-lg mx-4 mt-2">
      {counts.critical > 0 && (
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
          <span className="text-xs font-medium text-red-400">{counts.critical} Critical</span>
        </div>
      )}
      {counts.warning > 0 && (
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-amber-500" />
          <span className="text-xs font-medium text-amber-400">{counts.warning} Warning</span>
        </div>
      )}
      {counts.info > 0 && (
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-blue-500" />
          <span className="text-xs font-medium text-blue-400">{counts.info} Info</span>
        </div>
      )}
    </div>
  );
}

// ─── Combined Notification Item Type ──────────────────────────────────────────

type CombinedItemType = 'notification' | 'alert';

interface CombinedItem {
  id: string;
  type: CombinedItemType;
  createdAt: string;
  read: boolean;
  severity?: AlertSeverity;
  // For regular notifications
  notification?: ReturnType<typeof useOwnerNotifications>['items'][0];
  // For alerts
  alert?: ReturnType<typeof useSalesAlertStore['getState']>['alerts'][0];
}

// ─── Main Unified Panel Component ─────────────────────────────────────────────

interface UnifiedOwnerNotificationsPanelProps {
  storeId?: string;
  className?: string;
}

export function UnifiedOwnerNotificationsPanel({
  storeId = 'default-store',
  className,
}: UnifiedOwnerNotificationsPanelProps) {
  const [activeTab, setActiveTab] = useState('all');

  // Regular notifications
  const { items: notifications, connState, markRead, deleteNotification, markAllRead: markAllNotificationsRead } = useOwnerNotifications();

  // Sales alerts
  const alertStore = useSalesAlertStore((s) => ({
    alerts: s.getAlertsForStore(storeId),
    unreadAlerts: s.getUnreadAlerts(storeId),
    markAllRead: s.markAllRead,
  }));

  // Combined unread count
  const totalUnreadCount = useMemo(() => {
    const notificationUnread = notifications.filter((n) => !n.read_status).length;
    const alertUnread = alertStore.unreadAlerts.length;
    return notificationUnread + alertUnread;
  }, [notifications, alertStore.unreadAlerts]);

  // Combined and sorted items
  const combinedItems = useMemo(() => {
    const combined: CombinedItem[] = [
      ...notifications.map((n) => ({
        id: `notif-${n.id}`,
        type: 'notification' as const,
        createdAt: n.created_at || new Date().toISOString(),
        read: n.read_status,
        notification: n,
      })),
      ...alertStore.alerts.map((a) => ({
        id: `alert-${a.id}`,
        type: 'alert' as const,
        createdAt: a.created_at,
        read: a.read,
        severity: a.severity,
        alert: a,
      })),
    ];

    // Sort by createdAt descending
    return combined.sort((a, b) => b.createdAt.localeCompare(a.createdAt));
  }, [notifications, alertStore.alerts]);

  // Filtered items based on tab
  const filteredItems = useMemo(() => {
    if (activeTab === 'all') return combinedItems;
    if (activeTab === 'alerts') return combinedItems.filter((i) => i.type === 'alert');
    if (activeTab === 'orders') return combinedItems.filter((i) => i.type === 'notification');
    return combinedItems;
  }, [combinedItems, activeTab]);

  // Mark all as read handler
  const handleMarkAllRead = () => {
    markAllNotificationsRead();
    alertStore.markAllRead();
  };

  // Render individual item
  const renderItem = (item: CombinedItem) => {
    if (item.type === 'notification' && item.notification) {
      const n = item.notification;
      const type = n.data?.status || 'default';

      // Handle pickup notifications specially
      if (type === 'scheduled_pickup' && n.data) {
        return (
          <PickupNotificationCard
            key={item.id}
            customerName={n.data.customer_name}
            productName={n.data.product_name}
            pickupLocationName={n.data.pickup_location_name}
            pickupTime={n.data.pickup_time}
            orderId={n.data.order_id}
            createdAt={n.data.created_at}
            read={n.read_status}
            onMarkRead={() => markRead(n.id)}
          />
        );
      }

      return (
        <OwnerNotificationCard
          key={item.id}
          notification={n}
          onMarkRead={() => markRead(n.id)}
          onDelete={() => deleteNotification(n.id)}
        />
      );
    }

    if (item.type === 'alert' && item.alert) {
      return (
        <SalesAlertCard
          key={item.id}
          alert={item.alert}
          onMarkRead={() => alertStore.markAllRead()}
        />
      );
    }

    return null;
  };

  return (
    <Sheet>
      <SheetTrigger asChild>
        <button
          className={cn('relative p-2 rounded-full hover:bg-muted transition-colors', className)}
          title="Notifications & Alerts"
          aria-label={`Notifications${totalUnreadCount > 0 ? ` (${totalUnreadCount} unread)` : ''}`}
        >
          {totalUnreadCount > 0 ? (
            <BellRing className="h-5 w-5" />
          ) : (
            <Bell className="h-5 w-5" />
          )}
          {totalUnreadCount > 0 && (
            <motion.span
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              className="absolute -top-0.5 -right-0.5 h-5 w-5 rounded-full bg-gradient-to-r from-purple-500 to-blue-500 text-white text-[10px] font-bold flex items-center justify-center"
            >
              {totalUnreadCount > 9 ? '9+' : totalUnreadCount}
            </motion.span>
          )}
        </button>
      </SheetTrigger>

      <SheetContent side="right" className="w-full sm:max-w-md p-0 flex flex-col">
        {/* Header */}
        <SheetHeader className="p-4 border-b border-border">
          <div className="flex items-center justify-between">
            <SheetTitle className="flex items-center gap-2 text-lg">
              <Bell className="h-5 w-5" />
              Notifications
            </SheetTitle>
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                {connState === 'CONNECTED' ? (
                  <Wifi className="h-3.5 w-3.5 text-green-500" />
                ) : (
                  <WifiOff className="h-3.5 w-3.5 text-orange-500" />
                )}
              </div>
              {totalUnreadCount > 0 && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 text-xs gap-1"
                  onClick={handleMarkAllRead}
                >
                  <Check className="h-3.5 w-3.5" />
                  Mark all read
                </Button>
              )}
              <Link href="/brand-dashboard/settings/alerts">
                <Button variant="ghost" size="icon" className="h-8 w-8" title="Settings">
                  <Settings className="h-4 w-4" />
                </Button>
              </Link>
            </div>
          </div>
        </SheetHeader>

        {/* Alert Severity Summary */}
        <AlertSeveritySummary storeId={storeId} />

        {/* Tabs */}
        <div className="px-4 pt-3">
          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
            <TabsList className="w-full grid grid-cols-3 h-9">
              <TabsTrigger value="all" className="text-xs gap-1">
                <Bell className="h-3.5 w-3.5" />
                All
                {totalUnreadCount > 0 && (
                  <Badge variant="secondary" className="ml-1 h-4 px-1.5 text-[10px]">
                    {totalUnreadCount}
                  </Badge>
                )}
              </TabsTrigger>
              <TabsTrigger value="alerts" className="text-xs gap-1">
                <AlertTriangle className="h-3.5 w-3.5" />
                Alerts
                {alertStore.unreadAlerts.length > 0 && (
                  <Badge variant="secondary" className="ml-1 h-4 px-1.5 text-[10px]">
                    {alertStore.unreadAlerts.length}
                  </Badge>
                )}
              </TabsTrigger>
              <TabsTrigger value="orders" className="text-xs gap-1">
                <Package className="h-3.5 w-3.5" />
                Orders
                {notifications.filter((n) => !n.read_status).length > 0 && (
                  <Badge variant="secondary" className="ml-1 h-4 px-1.5 text-[10px]">
                    {notifications.filter((n) => !n.read_status).length}
                  </Badge>
                )}
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </div>

        {/* Items List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          <AnimatePresence initial={false}>
            {filteredItems.length === 0 ? (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="text-center py-12"
              >
                <div className="w-16 h-16 rounded-full bg-muted/50 flex items-center justify-center mx-auto mb-4">
                  <Bell className="h-8 w-8 text-muted-foreground opacity-50" />
                </div>
                <p className="text-muted-foreground font-medium">
                  {activeTab === 'alerts'
                    ? 'No alerts'
                    : activeTab === 'orders'
                    ? 'No order notifications'
                    : 'No notifications'}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  {activeTab === 'alerts'
                    ? "You'll be alerted about important business events"
                    : "You'll be notified about orders, stock alerts, and more"}
                </p>
              </motion.div>
            ) : (
              filteredItems.slice(0, 50).map((item) => renderItem(item))
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

export default UnifiedOwnerNotificationsPanel;
