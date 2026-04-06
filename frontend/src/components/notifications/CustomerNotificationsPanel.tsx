/**
 * CONFIT — Customer Notifications Panel
 * ======================================
 * Displays real-time notifications for customers
 */

import { useMemo } from 'react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Bell,
  Package,
  Truck,
  CheckCircle,
  XCircle,
  CreditCard,
  Sparkles,
  Tag,
  Heart,
  Wifi,
  WifiOff,
  Check,
  CheckCheck,
  Trash2,
  ExternalLink,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useCustomerNotifications, type CustomerNotificationType, type CustomerNotification } from '@/hooks/useCustomerNotifications';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet';
import { createTransition } from '@/motion';

const NOTIFICATION_ICONS: Record<CustomerNotificationType, React.ReactNode> = {
  order_placed: <Package className="h-4 w-4" />,
  order_confirmed: <CheckCircle className="h-4 w-4" />,
  order_shipped: <Truck className="h-4 w-4" />,
  order_delivered: <Package className="h-4 w-4 text-green-500" />,
  order_cancelled: <XCircle className="h-4 w-4 text-red-500" />,
  payment_success: <CreditCard className="h-4 w-4 text-green-500" />,
  styling_suggestion: <Sparkles className="h-4 w-4 text-violet-500" />,
  price_drop: <Tag className="h-4 w-4 text-orange-500" />,
  back_in_stock: <Package className="h-4 w-4 text-blue-500" />,
  wishlist_available: <Heart className="h-4 w-4 text-pink-500" />,
  promotion: <Tag className="h-4 w-4" />,
};

const NOTIFICATION_COLORS: Record<CustomerNotificationType, string> = {
  order_placed: 'bg-blue-500/10 border-blue-500/20',
  order_confirmed: 'bg-green-500/10 border-green-500/20',
  order_shipped: 'bg-purple-500/10 border-purple-500/20',
  order_delivered: 'bg-green-500/10 border-green-500/20',
  order_cancelled: 'bg-red-500/10 border-red-500/20',
  payment_success: 'bg-green-500/10 border-green-500/20',
  styling_suggestion: 'bg-violet-500/10 border-violet-500/20',
  price_drop: 'bg-orange-500/10 border-orange-500/20',
  back_in_stock: 'bg-blue-500/10 border-blue-500/20',
  wishlist_available: 'bg-pink-500/10 border-pink-500/20',
  promotion: 'bg-muted border-border',
};

function formatTimeAgo(dateString: string): string {
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

function NotificationCard({
  notification,
  onMarkRead,
  onDelete,
}: {
  notification: CustomerNotification;
  onMarkRead: () => void;
  onDelete: () => void;
}) {
  const icon = NOTIFICATION_ICONS[notification.type] || <Bell className="h-4 w-4" />;
  const bgColor = NOTIFICATION_COLORS[notification.type] || 'bg-muted';

  const actionLink = useMemo(() => {
    if (notification.data?.order_id) {
      return `/orders/${notification.data.order_id}`;
    }
    if (notification.data?.product_id) {
      return `/product/${notification.data.product_id}`;
    }
    return null;
  }, [notification.data]);

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
        bgColor,
        notification.read ? 'opacity-70' : 'shadow-sm'
      )}
    >
      <div className="flex gap-3">
        {/* Icon */}
        <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-background/50 flex items-center justify-center">
          {icon}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <h4 className={cn('text-sm font-medium', !notification.read && 'text-foreground')}>
              {notification.title}
            </h4>
            {!notification.read && (
              <span className="flex-shrink-0 w-2 h-2 rounded-full bg-accent" />
            )}
          </div>
          <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
            {notification.message}
          </p>

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
              {notification.data?.price_paid !== undefined && (
                <p className="text-xs">
                  <span className="text-muted-foreground">Price: </span>
                  <span className="font-semibold">{formatPrice(notification.data.price_paid, notification.data?.currency)}</span>
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

          {/* Image if available */}
          {notification.data?.image_url && (
            <img
              src={notification.data.image_url}
              alt=""
              className="mt-2 h-16 w-16 rounded-lg object-cover"
            />
          )}

          {/* Footer */}
          <div className="flex items-center justify-between mt-3">
            <span className="text-[10px] text-muted-foreground">
              {formatTimeAgo(notification.created_at)}
            </span>
            <div className="flex items-center gap-1">
              {!notification.read && (
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7"
                  onClick={onMarkRead}
                  title="Mark as read"
                  aria-label="Mark as read"
                >
                  <Check className="h-3.5 w-3.5" />
                </Button>
              )}
              {actionLink && (
                <Link
                  href={actionLink}
                  className="inline-flex items-center justify-center h-7 w-7 rounded-md hover:bg-muted"
                  title="View details"
                  aria-label="View details"
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
                aria-label="Delete notification"
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

export function CustomerNotificationsPanel() {
  const {
    notifications,
    unreadCount,
    connState,
    markRead,
    markAllRead,
    deleteNotification,
  } = useCustomerNotifications();

  return (
    <Sheet>
      <SheetTrigger asChild>
        <button
          className="relative p-2 rounded-full hover:bg-muted transition-colors"
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
              Notifications
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
                  <CheckCheck className="h-3.5 w-3.5" />
                  Mark all read
                </Button>
              )}
            </div>
          </div>
        </SheetHeader>

        {/* Notifications List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          <AnimatePresence initial={false}>
            {notifications.length === 0 ? (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="text-center py-12"
              >
                <Bell className="h-12 w-12 text-muted-foreground mx-auto mb-4 opacity-50" />
                <p className="text-muted-foreground">No notifications yet</p>
                <p className="text-xs text-muted-foreground mt-1">
                  We'll notify you about orders, promotions, and more
                </p>
              </motion.div>
            ) : (
              notifications.map((notification) => (
                <NotificationCard
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
          <Link href="/notifications">
            <Button variant="outline" className="w-full">
              View All Notifications
            </Button>
          </Link>
        </div>
      </SheetContent>
    </Sheet>
  );
}

export default CustomerNotificationsPanel;
