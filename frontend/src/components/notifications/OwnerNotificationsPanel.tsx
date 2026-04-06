/**
 * CONFIT — Owner Notifications Panel
 * =====================================
 * Displays real-time notifications for store/factory owners
 * Includes: new orders, pickup scheduled, low stock, reviews, payment issues, returns
 */

import { useMemo } from 'react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Bell,
  Wifi,
  WifiOff,
  Package,
  Truck,
  AlertTriangle,
  Star,
  CreditCard,
  RotateCcw,
  CheckCircle,
  XCircle,
  Clock,
  MapPin,
  TrendingDown,
  ExternalLink,
  Check,
  Trash2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useOwnerNotifications, type OwnerNotificationItem } from '@/hooks/useOwnerNotifications';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet';
import { PickupNotificationCard } from './PickupNotificationCard';
import { createTransition } from '@/motion';

// Notification type icons and colors
const NOTIFICATION_CONFIG: Record<string, { icon: React.ReactNode; color: string; bgColor: string }> = {
  new_order: { icon: <Package className="h-4 w-4" />, color: 'text-blue-500', bgColor: 'bg-blue-500/10 border-blue-500/20' },
  pickup_scheduled: { icon: <Truck className="h-4 w-4" />, color: 'text-purple-500', bgColor: 'bg-purple-500/10 border-purple-500/20' },
  low_stock: { icon: <AlertTriangle className="h-4 w-4" />, color: 'text-amber-500', bgColor: 'bg-amber-500/10 border-amber-500/20' },
  new_review: { icon: <Star className="h-4 w-4" />, color: 'text-yellow-500', bgColor: 'bg-yellow-500/10 border-yellow-500/20' },
  payment_issue: { icon: <CreditCard className="h-4 w-4" />, color: 'text-red-500', bgColor: 'bg-red-500/10 border-red-500/20' },
  return_requested: { icon: <RotateCcw className="h-4 w-4" />, color: 'text-orange-500', bgColor: 'bg-orange-500/10 border-orange-500/20' },
  order_cancelled: { icon: <XCircle className="h-4 w-4" />, color: 'text-red-500', bgColor: 'bg-red-500/10 border-red-500/20' },
  default: { icon: <Bell className="h-4 w-4" />, color: 'text-muted-foreground', bgColor: 'bg-muted border-border' },
};

function formatTimeAgo(dateString: string | null): string {
  if (!dateString) return 'Just now';
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

function OwnerNotificationCard({
  notification,
  onMarkRead,
  onDelete,
}: {
  notification: OwnerNotificationItem;
  onMarkRead: () => void;
  onDelete: () => void;
}) {
  const type = notification.data?.status || 'default';
  const config = NOTIFICATION_CONFIG[type] || NOTIFICATION_CONFIG.default;

  const actionLink = useMemo(() => {
    if (notification.data?.sale_id) {
      return `/dashboard?highlight=${notification.data.sale_id}`;
    }
    if (notification.data?.order_id) {
      return `/brand-dashboard/orders/${notification.data.order_id}`;
    }
    const metadata = notification.metadata as Record<string, unknown> | undefined;
    const productId = metadata?.product_id as string | undefined;
    if (productId) {
      return `/brand-dashboard/products/${productId}`;
    }
    return null;
  }, [notification.data, notification.metadata]);

  // Handle pickup notifications specially
  if (type === 'scheduled_pickup' && notification.data) {
    return (
      <PickupNotificationCard
        customerName={notification.data.customer_name}
        productName={notification.data.product_name}
        pickupLocationName={notification.data.pickup_location_name}
        pickupTime={notification.data.pickup_time}
        orderId={notification.data.order_id}
        createdAt={notification.data.created_at}
        read={notification.read_status}
        onMarkRead={onMarkRead}
      />
    );
  }

  // Format transaction time for display
  const formatTransactionTime = (time?: string) => {
    if (!time) return null;
    const date = new Date(time);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // Format price with currency
  const formatPrice = (price?: number, currency?: string) => {
    if (price === undefined) return null;
    return `${currency || '$'}${price.toLocaleString()}`;
  };

  // Get order status display
  const getOrderStatusDisplay = (status?: string) => {
    if (!status) return null;
    const statusMap: Record<string, { label: string; color: string }> = {
      confirmed: { label: 'Order Confirmed', color: 'text-blue-600' },
      shipped: { label: 'Shipped', color: 'text-purple-600' },
      ready_for_pickup: { label: 'Ready for Pickup', color: 'text-amber-600' },
      delivered: { label: 'Delivered', color: 'text-green-600' },
      cancelled: { label: 'Cancelled', color: 'text-red-600' },
      returned: { label: 'Returned', color: 'text-orange-600' },
    };
    return statusMap[status] || { label: status, color: 'text-muted-foreground' };
  };

  const statusDisplay = getOrderStatusDisplay(notification.data?.order_status);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={createTransition({ duration: 0.2 })}
      className={cn(
        'group relative rounded-xl border p-4 transition-all',
        config.bgColor,
        notification.read_status ? 'opacity-70' : 'shadow-sm'
      )}
    >
      <div className="flex gap-3">
        {/* Icon */}
        <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-background/50 flex items-center justify-center">
          <span className={config.color}>{config.icon}</span>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <h4 className={cn('text-sm font-medium', !notification.read_status && 'text-foreground')}>
              {notification.message || 'New Notification'}
            </h4>
            {!notification.read_status && (
              <span className="flex-shrink-0 w-2 h-2 rounded-full bg-accent" />
            )}
          </div>
          
          {/* Enhanced Details Section */}
          {(notification.data?.customer_name || notification.data?.product_name || notification.data?.store_name) && (
            <div className="mt-2 p-2 rounded-lg bg-background/50 space-y-1">
              {/* Customer Name */}
              {notification.data?.customer_name && (
                <p className="text-xs">
                  <span className="text-muted-foreground">Customer: </span>
                  <span className="font-medium">{notification.data.customer_name}</span>
                </p>
              )}
              
              {/* Product Name */}
              {notification.data?.product_name && (
                <p className="text-xs">
                  <span className="text-muted-foreground">Product: </span>
                  <span className="font-medium">{notification.data.product_name}</span>
                </p>
              )}
              
              {/* Store/Factory Info */}
              {notification.data?.store_name && (
                <div className="text-xs">
                  <span className="text-muted-foreground">Store: </span>
                  <span className="font-medium">{notification.data.store_name}</span>
                  {notification.data?.store_address && (
                    <span className="text-muted-foreground"> — {notification.data.store_address}</span>
                  )}
                </div>
              )}
              
              {/* Transaction Time */}
              {notification.data?.transaction_time && (
                <p className="text-xs text-muted-foreground">
                  {formatTransactionTime(notification.data.transaction_time)}
                </p>
              )}
              
              {/* Price Paid */}
              {notification.data?.price !== undefined && (
                <p className="text-xs">
                  <span className="text-muted-foreground">Price: </span>
                  <span className="font-semibold">{formatPrice(notification.data.price, notification.data?.currency)}</span>
                </p>
              )}
              
              {/* Payment Method */}
              {notification.data?.payment_method && (
                <p className="text-xs">
                  <span className="text-muted-foreground">Payment: </span>
                  <span className="font-medium">{notification.data.payment_method}</span>
                </p>
              )}
              
              {/* Order Status */}
              {statusDisplay && (
                <p className={cn('text-xs font-medium', statusDisplay.color)}>
                  {statusDisplay.label}
                </p>
              )}
            </div>
          )}

          {/* Legacy Metadata (fallback) */}
          {notification.data && !notification.data?.customer_name && !notification.data?.product_name && !notification.data?.store_name && (
            <div className="flex flex-wrap gap-2 mt-2 text-xs text-muted-foreground">
              {notification.data.customer_name && (
                <span>Customer: {notification.data.customer_name}</span>
              )}
              {notification.data.product_name && (
                <span>• {notification.data.product_name}</span>
              )}
              {notification.data.order_id && (
                <span className="font-mono">#{notification.data.order_id}</span>
              )}
            </div>
          )}

          {/* Footer */}
          <div className="flex items-center justify-between mt-3">
            <span className="text-[10px] text-muted-foreground">
              {formatTimeAgo(notification.created_at)}
            </span>
            <div className="flex items-center gap-1">
              {!notification.read_status && (
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7"
                  onClick={onMarkRead}
                  title="Mark as read"
                >
                  <Check className="h-3.5 w-3.5" />
                </Button>
              )}
              {actionLink && (
                <Link
                  href={actionLink}
                  className="inline-flex items-center justify-center h-7 w-7 rounded-md hover:bg-muted"
                  title="View details"
                >
                  <ExternalLink className="h-3.5 w-3.5" />
                </Link>
              )}
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 text-muted-foreground hover:text-destructive"
                onClick={onDelete}
                title="Delete"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

export function OwnerNotificationsPanel({ className }: { className?: string }) {
  const { items, connState, markRead, deleteNotification, markAllRead } = useOwnerNotifications();

  const unreadCount = useMemo(() => items.filter(i => !i.read_status).length, [items]);

  // Sort by created_at descending
  const sortedItems = useMemo(() => 
    [...items].sort((a, b) => (b.created_at ?? '').localeCompare(a.created_at ?? '')),
    [items]
  );

  return (
    <Sheet>
      <SheetTrigger asChild>
        <button
          className={cn('relative p-2 rounded-full hover:bg-muted transition-colors', className)}
          title="Notifications"
          aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ''}`}
        >
          <Bell className="h-5 w-5" />
          {unreadCount > 0 && (
            <span className="absolute -top-0.5 -right-0.5 h-5 w-5 rounded-full bg-accent text-accent-foreground text-[10px] font-bold flex items-center justify-center">
              {unreadCount > 9 ? '9+' : unreadCount}
            </span>
          )}
        </button>
      </SheetTrigger>

      <SheetContent side="right" className="w-full sm:max-w-md p-0 flex flex-col">
        {/* Header */}
        <SheetHeader className="p-4 border-b border-border">
          <div className="flex items-center justify-between">
            <SheetTitle className="flex items-center gap-2">
              <Bell className="h-5 w-5" />
              Owner Notifications
            </SheetTitle>
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                {connState === 'CONNECTED' ? (
                  <Wifi className="h-3.5 w-3.5 text-green-500" />
                ) : (
                  <WifiOff className="h-3.5 w-3.5 text-orange-500" />
                )}
                <span className="hidden sm:inline">{connState}</span>
              </div>
              {unreadCount > 0 && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 text-xs gap-1"
                  onClick={markAllRead}
                >
                  Mark all read
                </Button>
              )}
            </div>
          </div>
        </SheetHeader>

        {/* Notifications List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          <AnimatePresence initial={false}>
            {sortedItems.length === 0 ? (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="text-center py-12"
              >
                <Bell className="h-12 w-12 text-muted-foreground mx-auto mb-4 opacity-50" />
                <p className="text-muted-foreground">No notifications yet</p>
                <p className="text-xs text-muted-foreground mt-1">
                  You'll be notified about orders, stock alerts, and more
                </p>
              </motion.div>
            ) : (
              sortedItems.slice(0, 50).map((notification) => (
                <OwnerNotificationCard
                  key={notification.id}
                  notification={notification}
                  onMarkRead={() => markRead(notification.id)}
                  onDelete={() => deleteNotification(notification.id)}
                />
              ))
            )}
          </AnimatePresence>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-border">
          <Link href="/brand-dashboard/notifications">
            <Button variant="outline" className="w-full">
              View All Notifications
            </Button>
          </Link>
        </div>
      </SheetContent>
    </Sheet>
  );
}

export default OwnerNotificationsPanel;

