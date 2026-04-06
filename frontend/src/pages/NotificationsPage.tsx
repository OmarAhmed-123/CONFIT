/**
 * CONFIT — Notifications Page
 * ============================
 * Full-page notification center accessible at /notifications.
 * Uses the same NotificationCenter logic rendered within MainLayout.
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
  Inbox,
  ArrowLeft,
  Settings,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuth } from '@/context/AuthContext';
import { MainLayout } from '@/components/layout/MainLayout';
import { Button } from '@/components/ui/button';
import {
  useNotificationStore,
  type NotificationType,
  type NotificationFilter,
  type AppNotification,
} from '@/stores/notificationStore';
import { createTransition } from '@/motion';

// Icon / accent maps (shared with NotificationCenter)
const NOTIFICATION_ICONS: Record<NotificationType, React.ReactNode> = {
  order_placed: <Package className="h-5 w-5" />,
  order_confirmed: <CheckCircle className="h-5 w-5" />,
  order_shipped: <Truck className="h-5 w-5" />,
  order_delivered: <Package className="h-5 w-5 text-green-500" />,
  order_cancelled: <XCircle className="h-5 w-5 text-red-500" />,
  payment_success: <CreditCard className="h-5 w-5 text-green-500" />,
  styling_suggestion: <Sparkles className="h-5 w-5 text-violet-500" />,
  price_drop: <Tag className="h-5 w-5 text-orange-500" />,
  back_in_stock: <Package className="h-5 w-5 text-blue-500" />,
  wishlist_available: <Heart className="h-5 w-5 text-pink-500" />,
  promotion: <Tag className="h-5 w-5" />,
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

const FILTER_TABS: { value: NotificationFilter; label: string; icon: React.ReactNode }[] = [
  { value: 'all', label: 'All', icon: <Inbox className="h-4 w-4" /> },
  { value: 'unread', label: 'Unread', icon: <Bell className="h-4 w-4" /> },
  { value: 'orders', label: 'Orders', icon: <Package className="h-4 w-4" /> },
  { value: 'promotions', label: 'Promotions', icon: <Tag className="h-4 w-4" /> },
];

function NotificationCard({
  notification,
  onMarkRead,
  onDismiss,
}: {
  notification: AppNotification;
  onMarkRead: () => void;
  onDismiss: () => void;
}) {
  const router = useRouter();
  const icon = NOTIFICATION_ICONS[notification.type] || <Bell className="h-5 w-5" />;
  const accent = NOTIFICATION_ACCENT[notification.type] || 'border-l-amber-500';

  const handleClick = () => {
    if (!notification.read) onMarkRead();
    if (notification.data?.order_id) router.push('/orders');
    else if (notification.data?.product_id) router.push(`/product/${notification.data.product_id}`);
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
        'group relative rounded-xl border-l-[3px] border border-border bg-card p-5 transition-all cursor-pointer hover:shadow-md',
        accent,
        !notification.read && 'bg-accent/[0.03] shadow-sm',
        notification.read && 'opacity-65'
      )}
    >
      <div className="flex gap-4">
        <div className={cn(
          'flex-shrink-0 w-11 h-11 rounded-xl flex items-center justify-center',
          !notification.read ? 'bg-accent/10' : 'bg-muted/50'
        )}>
          {icon}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h4 className={cn(
                'text-sm',
                !notification.read ? 'font-semibold' : 'font-medium text-muted-foreground'
              )}>
                {notification.title}
              </h4>
              <p className="text-sm text-muted-foreground mt-1">{notification.message}</p>
            </div>
            {!notification.read && (
              <span className="flex-shrink-0 w-2.5 h-2.5 rounded-full bg-accent mt-1 animate-pulse" />
            )}
          </div>

          {(notification.data?.store_name || notification.data?.price_paid !== undefined) && (
            <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
              {notification.data.store_name && <span>📍 {notification.data.store_name}</span>}
              {notification.data.price_paid !== undefined && (
                <span className="font-medium text-foreground">
                  {notification.data.currency || '$'}{notification.data.price_paid.toFixed(2)}
                </span>
              )}
              {notification.data.payment_method && (
                <span>via {notification.data.payment_method}</span>
              )}
            </div>
          )}

          <div className="flex items-center justify-between mt-3">
            <span className="text-xs text-muted-foreground">{formatTimeAgo(notification.created_at)}</span>
            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              {!notification.read && (
                <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={(e) => { e.stopPropagation(); onMarkRead(); }}>
                  <Check className="h-3 w-3 mr-1" /> Read
                </Button>
              )}
              <Button
                variant="ghost"
                size="sm"
                className="h-7 text-xs text-muted-foreground hover:text-destructive"
                onClick={(e) => { e.stopPropagation(); onDismiss(); }}
              >
                <Trash2 className="h-3 w-3 mr-1" /> Dismiss
              </Button>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

export default function NotificationsPage() {
  const { user } = useAuth();
  const router = useRouter();
  const [activeFilter, setActiveFilter] = useState<NotificationFilter>('all');
  const store = useNotificationStore();
  const userId = user?.id || '';

  const unreadCount = useMemo(() => store.getUnreadCount('customer', userId), [store, userId]);
  const grouped = useMemo(
    () => store.getGroupedByDate('customer', userId, activeFilter),
    [store, userId, activeFilter]
  );

  const hasNotifications = grouped.today.length > 0 || grouped.yesterday.length > 0 || grouped.earlier.length > 0;

  return (
    <MainLayout>
      <div className="container py-8 max-w-3xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon" onClick={() => router.back()}>
              <ArrowLeft className="h-5 w-5" />
            </Button>
            <div>
              <h1 className="text-2xl font-display font-semibold">Notifications</h1>
              {unreadCount > 0 && (
                <p className="text-sm text-muted-foreground">{unreadCount} unread</p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            {unreadCount > 0 && (
              <Button variant="ghost" size="sm" className="gap-1" onClick={() => store.markAllRead('customer', userId)}>
                <CheckCheck className="h-4 w-4" /> Mark all read
              </Button>
            )}
            <Button variant="outline" size="sm" className="gap-1" asChild>
              <Link href="/notification-preferences">
                <Settings className="h-4 w-4" /> Preferences
              </Link>
            </Button>
          </div>
        </div>

        {/* Filter Tabs */}
        <div className="flex gap-2 mb-6">
          {FILTER_TABS.map((tab) => (
            <button
              key={tab.value}
              onClick={() => setActiveFilter(tab.value)}
              className={cn(
                'flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all',
                activeFilter === tab.value
                  ? 'bg-accent/15 text-accent'
                  : 'text-muted-foreground hover:bg-muted/50'
              )}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>

        {/* Notifications */}
        <div className="space-y-6">
          <AnimatePresence initial={false}>
            {!hasNotifications ? (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="text-center py-24"
              >
                <div className="w-24 h-24 rounded-2xl bg-gradient-to-br from-accent/10 to-accent/5 flex items-center justify-center mx-auto mb-6">
                  <Bell className="h-10 w-10 text-accent/40" />
                </div>
                <h2 className="font-display text-xl font-semibold mb-2">Nothing here yet</h2>
                <p className="text-muted-foreground max-w-xs mx-auto">
                  Your style journey awaits — we'll notify you about orders, trends, and exclusive drops from CONFIT.
                </p>
                <Button variant="hero" className="mt-6" asChild>
                  <Link href="/discover">Start Shopping</Link>
                </Button>
              </motion.div>
            ) : (
              <>
                {grouped.today.length > 0 && (
                  <div>
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">Today</h3>
                    <div className="space-y-3">
                      {grouped.today.map((n) => (
                        <NotificationCard key={n.id} notification={n} onMarkRead={() => store.markRead(n.id)} onDismiss={() => store.dismissNotification(n.id)} />
                      ))}
                    </div>
                  </div>
                )}
                {grouped.yesterday.length > 0 && (
                  <div>
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">Yesterday</h3>
                    <div className="space-y-3">
                      {grouped.yesterday.map((n) => (
                        <NotificationCard key={n.id} notification={n} onMarkRead={() => store.markRead(n.id)} onDismiss={() => store.dismissNotification(n.id)} />
                      ))}
                    </div>
                  </div>
                )}
                {grouped.earlier.length > 0 && (
                  <div>
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">Earlier</h3>
                    <div className="space-y-3">
                      {grouped.earlier.map((n) => (
                        <NotificationCard key={n.id} notification={n} onMarkRead={() => store.markRead(n.id)} onDismiss={() => store.dismissNotification(n.id)} />
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </AnimatePresence>
        </div>
      </div>
    </MainLayout>
  );
}
