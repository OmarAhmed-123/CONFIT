/**
 * CONFIT — Customer Notifications Hook
 * =====================================
 * Real-time notifications for customers (order updates, styling suggestions, etc.)
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { apiUrl, getBackendUrl } from '@/lib/api';
import { getAuthToken } from '@/lib/auth';

export type CustomerNotificationType =
  | 'order_placed'
  | 'order_confirmed'
  | 'order_shipped'
  | 'order_delivered'
  | 'order_cancelled'
  | 'payment_success'
  | 'styling_suggestion'
  | 'price_drop'
  | 'back_in_stock'
  | 'wishlist_available'
  | 'promotion';

export type CustomerNotification = {
  id: string;
  type: CustomerNotificationType;
  title: string;
  message: string;
  read: boolean;
  created_at: string;
  data?: {
    // Order details
    order_id?: string;
    order_number?: string;
    order_status?: 'confirmed' | 'shipped' | 'ready_for_pickup' | 'delivered' | 'cancelled';
    // Product details
    product_id?: string;
    product_name?: string;
    product_sku?: string;
    product_category?: string;
    image_url?: string;
    // Price
    price_paid?: number;
    currency?: string;
    // Store/Factory info (for BOPIS and purchase tracking)
    store_name?: string;
    store_address?: string;
    store_city?: string;
    store_phone?: string;
    // Transaction details
    transaction_time?: string;
    payment_method?: string;
    // Customer info (for confirmation)
    customer_name?: string;
    customer_email?: string;
    // Tracking
    tracking_url?: string;
    tracking_number?: string;
    // Promotional
    discount_code?: string;
    discount_percent?: number;
    sale_name?: string;
    // Brand info
    brand_name?: string;
  };
};

type ApiNotificationRow = {
  id: string;
  type?: string;
  title?: string;
  message?: string;
  read_status?: boolean;
  created_at?: string;
  metadata?: Record<string, unknown>;
};

function toWsUrl(httpBase: string, path: string): string {
  const base = httpBase || window.location.origin;
  const u = new URL(base);
  u.protocol = u.protocol === 'https:' ? 'wss:' : 'ws:';
  u.pathname = path.startsWith('/') ? path : `/${path}`;
  u.search = '';
  u.hash = '';
  return u.toString();
}

export function useCustomerNotifications() {
  const [notifications, setNotifications] = useState<CustomerNotification[]>([]);
  const [connState, setConnState] = useState<'CONNECTED' | 'RECONNECTING' | 'OFFLINE'>('OFFLINE');
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptRef = useRef(0);
  const unmountedRef = useRef(false);

  const token = useMemo(() => getAuthToken(), []);

  const loadInitial = useCallback(async () => {
    const t = getAuthToken();
    if (!t) return;

    try {
      const res = await fetch(apiUrl('/api/notifications/customer'), {
        headers: { Authorization: `Bearer ${t}` },
      });

      if (!res.ok) return;

      const body = await res.json();
      const items = Array.isArray(body?.items) ? body.items : [];

      const parsed: CustomerNotification[] = items.map((raw: ApiNotificationRow) => ({
        id: raw.id,
        type: (raw.type as CustomerNotificationType) || 'promotion',
        title: raw.title || 'Notification',
        message: raw.message || '',
        read: Boolean(raw.read_status),
        created_at: raw.created_at || new Date().toISOString(),
        data: raw.metadata as CustomerNotification['data'],
      }));

      setNotifications(parsed.sort((a, b) => b.created_at.localeCompare(a.created_at)));
    } catch {
      // Silently fail on load
    }
  }, []);

  const markRead = useCallback(async (notificationId: string) => {
    const t = getAuthToken();
    if (!t) return;

    try {
      await fetch(apiUrl(`/api/notifications/${encodeURIComponent(notificationId)}/read`), {
        method: 'POST',
        headers: { Authorization: `Bearer ${t}` },
      });
    } catch {
      // Ignore
    }

    setNotifications((prev) =>
      prev.map((n) => (n.id === notificationId ? { ...n, read: true } : n))
    );
  }, []);

  const markAllRead = useCallback(async () => {
    const t = getAuthToken();
    if (!t) return;

    try {
      await fetch(apiUrl('/api/notifications/read-all'), {
        method: 'POST',
        headers: { Authorization: `Bearer ${t}` },
      });
    } catch {
      // Ignore
    }

    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  }, []);

  const deleteNotification = useCallback(async (notificationId: string) => {
    const t = getAuthToken();
    if (!t) return;

    try {
      await fetch(apiUrl(`/api/notifications/${encodeURIComponent(notificationId)}`), {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${t}` },
      });
    } catch {
      // Ignore
    }

    setNotifications((prev) => prev.filter((n) => n.id !== notificationId));
  }, []);

  useEffect(() => {
    loadInitial();
  }, [loadInitial]);

  useEffect(() => {
    const t = getAuthToken();
    if (!t) return;

    unmountedRef.current = false;
    reconnectAttemptRef.current = 0;

    const connect = () => {
      if (unmountedRef.current) return;
      setConnState((prev) => (prev === 'CONNECTED' ? 'CONNECTED' : 'RECONNECTING'));

      const wsUrl = `${toWsUrl(getBackendUrl(), '/api/notifications/customer/ws')}?token=${encodeURIComponent(t)}`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        if (unmountedRef.current) return;
        reconnectAttemptRef.current = 0;
        setConnState('CONNECTED');
      };

      ws.onclose = () => {
        if (unmountedRef.current) return;
        setConnState('RECONNECTING');
        reconnectAttemptRef.current += 1;
        const delay = Math.min(5000, 800 * 2 ** (reconnectAttemptRef.current - 1));
        setTimeout(() => connect(), delay);
      };

      ws.onerror = () => {
        try {
          ws.close();
        } catch {
          // Ignore
        }
      };

      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          const type = msg?.type;

          if (type === 'notification.created' || type === 'notification') {
            const data = msg?.data || msg;
            const notification: CustomerNotification = {
              id: data.id || data.notification_id || `notif-${Date.now()}`,
              type: data.type || 'promotion',
              title: data.title || 'New Update',
              message: data.message || '',
              read: false,
              created_at: data.created_at || new Date().toISOString(),
              data: data.data || data.metadata,
            };

            setNotifications((prev) => {
              const exists = prev.some((n) => n.id === notification.id);
              if (exists) return prev;
              return [notification, ...prev].sort((a, b) =>
                b.created_at.localeCompare(a.created_at)
              );
            });

            // Send ACK
            try {
              ws.send(
                JSON.stringify({
                  type: 'notification.ack',
                  notification_id: notification.id,
                })
              );
            } catch {
              // Ignore
            }
          }
        } catch {
          // Ignore parse errors
        }
      };
    };

    connect();

    return () => {
      unmountedRef.current = true;
      try {
        wsRef.current?.close();
      } catch {
        // Ignore
      }
    };
  }, [token]);

  const unreadCount = useMemo(
    () => notifications.filter((n) => !n.read).length,
    [notifications]
  );

  return {
    notifications,
    unreadCount,
    connState,
    markRead,
    markAllRead,
    deleteNotification,
    reload: loadInitial,
  };
}

export default useCustomerNotifications;
