/**
 * CONFIT — Notification Center
 * ==============================
 * Full-featured notification panel with date grouping, filtering,
 * read/unread management, and luxury styling consistent with CONFIT brand.
 *
 * Replaces the basic CustomerNotificationsPanel with a comprehensive center.
 */

import { useState, useMemo, useCallback } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
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
  Check,
  CheckCheck,
  Trash2,
  ExternalLink,
  Filter,
  Inbox,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuth } from '@/context/AuthContext';
import {
  useNotificationStore,
  type NotificationType,
  type NotificationFilter,
  type AppNotification,
} from '@/stores/notificationStore';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet';
import { createTransition } from '@/motion';

// ─── Icon Map ───

const NOTIFICATION_ICONS: Record<NotificationType, React.ReactNode> = {
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

const NOTIFICATION_ACCENT: Record<NotificationType, string> = {
  order_placed: 'border-l-blue-500',
  order_confirmed: 'border-l-green-500',
  order_shipped: 'border-l-purple-500',
  order_delivered: 'border-l-green-500',
  order_cancelled: 'border-l-red-500',
  payment_success: 'border-l-green-500',
  styling_suggestion: 'border-l-violet-500',
  price_drop: 'border-l-orange-500',
  back_in_stock: 'border-l-blue-500',
  wishlist_available: 'border-l-pink-500',
  promotion: 'border-l-amber-500',
};

// ─── Helpers ───

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

// ─── Filter Tabs ───

const FILTER_TABS: { value: NotificationFilter; label: string; icon: React.ReactNode }[] = [
  { value: 'all', label: 'All', icon: <Inbox className="h-3.5 w-3.5" /> },
  { value: 'unread', label: 'Unread', icon: <Bell className="h-3.5 w-3.5" /> },
  { value: 'orders', label: 'Orders', icon: <Package className="h-3.5 w-3.5" /> },
  { value: 'promotions', label: 'Promos', icon: <Tag className="h-3.5 w-3.5" /> },
];

// ─── Notification Item ───

function NotificationItem({
  notification,
  onMarkRead,
  onDismiss,
}: {
  notification: AppNotification;
  onMarkRead: () => void;
  onDismiss: () => void;
}) {
  const router = useRouter();
  const icon = NOTIFICATION_ICONS[notification.type] || <Bell className="h-4 w-4" />;
  const accentClass = NOTIFICATION_ACCENT[notification.type] || 'border-l-amber-500';

  const handleClick = useCallback(() => {
    if (!notification.read) onMarkRead();
    if (notification.data?.order_id) {
      router.push('/orders');
    } else if (notification.data?.product_id) {
      router.push(`/product/${notification.data.product_id}`);
    }
  }, [notification, onMarkRead, router]);

  const formatPrice = (price?: number, currency?: string) => {
    if (price === undefined) return null;
    return `${currency || '$'}${price.toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -20, height: 0 }}
      transition={createTransition({ duration: 0.2 })}
      onClick={handleClick}
      className={cn(
        'group relative rounded-xl border-l-[3px] border border-border bg-card/50 p-3.5 transition-all cursor-pointer hover:bg-card',
        accentClass,
        !notification.read && 'bg-accent/[0.03] shadow-sm',
        notification.read && 'opacity-65'
      )}
    >
      <div className="flex gap-3">
        {/* Icon */}
        <div className={cn(
          'flex-shrink-0 w-9 h-9 rounded-lg flex items-center justify-center',
          !notification.read ? 'bg-accent/10' : 'bg-muted/50'
        )}>
          {icon}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <h4 className={cn(
              'text-sm leading-tight',
              !notification.read ? 'font-semibold text-foreground' : 'font-medium text-muted-foreground'
            )}>
              {notification.title}
            </h4>
            {!notification.read && (
              <span className="flex-shrink-0 w-2 h-2 rounded-full bg-accent mt-1.5 animate-pulse" />
            )}
          </div>

          <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">
            {notification.message}
          </p>

          {/* Quick details */}
          {(notification.data?.store_name || notification.data?.price_paid !== undefined) && (
            <div className="flex items-center gap-3 mt-1.5 text-[11px] text-muted-foreground">
              {notification.data.store_name && (
                <span>{notification.data.store_name}</span>
              )}
              {notification.data.price_paid !== undefined && (
                <span className="font-medium text-foreground/80">
                  {formatPrice(notification.data.price_paid, notification.data.currency)}
                </span>
              )}
            </div>
          )}

          {/* Footer */}
          <div className="flex items-center justify-between mt-2">
            <span className="text-[10px] text-muted-foreground">
              {formatTimeAgo(notification.created_at)}
            </span>
            <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
              {!notification.read && (
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6"
                  onClick={(e) => { e.stopPropagation(); onMarkRead(); }}
                  title="Mark as read"
                >
                  <Check className="h-3 w-3" />
                </Button>
              )}
              {notification.data?.order_id && (
                <Link
                  href="/orders"
                  className="inline-flex items-center justify-center h-6 w-6 rounded-md hover:bg-muted"
                  onClick={(e) => e.stopPropagation()}
                  title="View order"
                >
                  <ExternalLink className="h-3 w-3" />
                </Link>
              )}
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 text-muted-foreground hover:text-destructive"
                onClick={(e) => { e.stopPropagation(); onDismiss(); }}
                title="Dismiss"
              >
                <Trash2 className="h-3 w-3" />
              </Button>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

// ─── Section Header ───

function DateSection({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground mb-2 px-1">
        {label}
      </h3>
      <div className="space-y-2">
        {children}
      </div>
    </div>
  );
}

// ─── Main NotificationCenter ───

export function NotificationCenter() {
  const { user } = useAuth();
  const [activeFilter, setActiveFilter] = useState<NotificationFilter>('all');
  const store = useNotificationStore();

  const userId = user?.id || '';

  const unreadCount = useMemo(
    () => store.getUnreadCount('customer', userId),
    [store, userId]
  );

  const grouped = useMemo(
    () => store.getGroupedByDate('customer', userId, activeFilter),
    [store, userId, activeFilter]
  );

  const hasNotifications = grouped.today.length > 0 || grouped.yesterday.length > 0 || grouped.earlier.length > 0;

  const handleMarkAllRead = useCallback(() => {
    store.markAllRead('customer', userId);
  }, [store, userId]);

  return (
    <Sheet>
      <SheetTrigger asChild>
        <button
          className="relative p-2 rounded-full hover:bg-muted transition-colors"
          title="Notifications"
          aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ''}`}
          id="notification-bell"
        >
          <Bell className="h-5 w-5" />
          <AnimatePresence>
            {unreadCount > 0 && (
              <motion.span
                key="badge"
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0 }}
                className="absolute -top-0.5 -right-0.5 h-5 w-5 rounded-full bg-accent text-accent-foreground text-[10px] font-bold flex items-center justify-center gold-glow"
              >
                {unreadCount > 9 ? '9+' : unreadCount}
              </motion.span>
            )}
          </AnimatePresence>
        </button>
      </SheetTrigger>

      <SheetContent side="right" className="w-full sm:max-w-md p-0 flex flex-col bg-background/95 backdrop-blur-xl">
        {/* Header */}
        <SheetHeader className="p-4 pb-3 border-b border-border/50">
          <div className="flex items-center justify-between">
            <SheetTitle className="flex items-center gap-2 text-base">
              <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-amber-500/20 to-yellow-500/10 flex items-center justify-center">
                <Bell className="h-4 w-4 text-accent" />
              </div>
              Notifications
              {unreadCount > 0 && (
                <span className="text-xs font-normal text-muted-foreground">
                  ({unreadCount} new)
                </span>
              )}
            </SheetTitle>
            {unreadCount > 0 && (
              <Button
                variant="ghost"
                size="sm"
                className="h-7 text-xs gap-1 text-accent hover:text-accent"
                onClick={handleMarkAllRead}
              >
                <CheckCheck className="h-3.5 w-3.5" />
                Mark all read
              </Button>
            )}
          </div>

          {/* Filter Tabs */}
          <div className="flex gap-1 mt-3">
            {FILTER_TABS.map((tab) => (
              <button
                key={tab.value}
                onClick={() => setActiveFilter(tab.value)}
                className={cn(
                  'flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all',
                  activeFilter === tab.value
                    ? 'bg-accent/15 text-accent'
                    : 'text-muted-foreground hover:bg-muted/50 hover:text-foreground'
                )}
              >
                {tab.icon}
                {tab.label}
              </button>
            ))}
          </div>
        </SheetHeader>

        {/* Notifications List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          <AnimatePresence initial={false}>
            {!hasNotifications ? (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="text-center py-16"
              >
                <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-accent/10 to-accent/5 flex items-center justify-center mx-auto mb-5">
                  <Bell className="h-8 w-8 text-accent/40" />
                </div>
                <p className="font-display font-semibold text-lg mb-2">Nothing here yet</p>
                <p className="text-sm text-muted-foreground max-w-[240px] mx-auto leading-relaxed">
                  Your style journey awaits — we'll notify you about orders, trends, and exclusive drops.
                </p>
              </motion.div>
            ) : (
              <>
                {grouped.today.length > 0 && (
                  <DateSection label="Today">
                    {grouped.today.map((n) => (
                      <NotificationItem
                        key={n.id}
                        notification={n}
                        onMarkRead={() => store.markRead(n.id)}
                        onDismiss={() => store.dismissNotification(n.id)}
                      />
                    ))}
                  </DateSection>
                )}

                {grouped.yesterday.length > 0 && (
                  <DateSection label="Yesterday">
                    {grouped.yesterday.map((n) => (
                      <NotificationItem
                        key={n.id}
                        notification={n}
                        onMarkRead={() => store.markRead(n.id)}
                        onDismiss={() => store.dismissNotification(n.id)}
                      />
                    ))}
                  </DateSection>
                )}

                {grouped.earlier.length > 0 && (
                  <DateSection label="Earlier">
                    {grouped.earlier.map((n) => (
                      <NotificationItem
                        key={n.id}
                        notification={n}
                        onMarkRead={() => store.markRead(n.id)}
                        onDismiss={() => store.dismissNotification(n.id)}
                      />
                    ))}
                  </DateSection>
                )}
              </>
            )}
          </AnimatePresence>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-border/50">
          <Link href="/notifications">
            <Button variant="outline" className="w-full text-sm">
              View All Notifications
            </Button>
          </Link>
        </div>
      </SheetContent>
    </Sheet>
  );
}

export default NotificationCenter;
