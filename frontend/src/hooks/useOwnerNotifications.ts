import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { apiUrl, getBackendUrl } from '@/lib/api';
import { getAuthToken } from '@/lib/auth';

export type PickupScheduledNotification = {
  notification_id: string;
  customer_name: string;
  product_name: string;
  pickup_location_name: string;
  pickup_time: string;
  order_id: string;
  created_at: string;
  status: 'scheduled_pickup';
  // Additional fields for enhanced notifications
  sale_id?: string;
  store_name?: string;
  store_address?: string;
  transaction_time?: string;
  price?: number;
  currency?: string;
  payment_method?: string;
  order_status?: 'confirmed' | 'shipped' | 'ready_for_pickup' | 'delivered' | 'cancelled' | 'returned';
};

type ApiNotificationRow = {
  id: unknown;
  message?: unknown;
  metadata?: unknown;
  read_status?: unknown;
  created_at?: unknown;
};

function asRecord(v: unknown): Record<string, unknown> {
  return v && typeof v === 'object' ? (v as Record<string, unknown>) : {};
}

export type OwnerNotificationItem = {
  id: string;
  message: string;
  metadata: unknown;
  read_status: boolean;
  created_at: string | null;
  data?: PickupScheduledNotification;
};

// Full notification data for store/factory owners
export type OwnerNotificationData = {
  // Customer info
  customer_name: string;
  customer_email?: string;
  customer_phone?: string;
  // Product details
  product_name: string;
  product_sku?: string;
  product_category?: string;
  product_type?: string;
  product_image?: string;
  // Store/Factory info
  store_name: string;
  store_address?: string;
  store_city?: string;
  store_phone?: string;
  // Transaction details
  transaction_time: string;
  price: number;
  currency?: string;
  payment_method?: string;
  // Order info
  order_id: string;
  order_status?: 'confirmed' | 'shipped' | 'ready_for_pickup' | 'delivered' | 'cancelled' | 'returned';
  // Sale info (for dashboard deep-linking)
  sale_id?: string;
  // Brand info
  brand_name?: string;
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

export function useOwnerNotifications() {
  const [items, setItems] = useState<OwnerNotificationItem[]>([]);
  const [connState, setConnState] = useState<'CONNECTED' | 'RECONNECTING' | 'OFFLINE'>('OFFLINE');
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptRef = useRef(0);
  const unmountedRef = useRef(false);
  const [storeIds, setStoreIds] = useState<string[]>([]);

  const pendingRef = useRef<OwnerNotificationItem[]>([]);
  const flushTimerRef = useRef<number | null>(null);

  const token = useMemo(() => getAuthToken(), []);

  const flush = useCallback(() => {
    flushTimerRef.current = null;
    const pending = pendingRef.current;
    pendingRef.current = [];
    if (!pending.length) return;
    setItems((prev) => {
      const seen = new Set(prev.map((p) => p.id));
      const next = [...pending.filter((p) => !seen.has(p.id)), ...prev];
      return next;
    });
  }, []);

  const enqueue = useCallback(
    (n: OwnerNotificationItem) => {
      pendingRef.current.push(n);
      if (flushTimerRef.current != null) return;
      // Debounce bursts: single state update per tick.
      flushTimerRef.current = window.setTimeout(flush, 50);
    },
    [flush]
  );

  const loadInitial = useCallback(async () => {
    const t = getAuthToken();
    if (!t) return;
    const res = await fetch(apiUrl('/api/notifications'), {
      headers: { Authorization: `Bearer ${t}` },
    });
    if (!res.ok) return;
    const body: unknown = await res.json().catch(() => null);
    if (!body || typeof body !== 'object') return;
    const itemsRaw = (body as { items?: unknown }).items;
    if (!Array.isArray(itemsRaw)) return;
    const initial: OwnerNotificationItem[] = itemsRaw.map((raw) => {
      const r = (raw ?? {}) as ApiNotificationRow;
      const id = String(r.id ?? '');
      const metadata = asRecord(r.metadata);
      const status = typeof metadata.status === 'string' ? metadata.status : undefined;
      const createdAt = typeof r.created_at === 'string' ? r.created_at : null;
      const pickupData: PickupScheduledNotification | undefined =
        status === 'scheduled_pickup'
          ? {
              notification_id: id,
              customer_name: String(metadata.customer_name ?? 'Customer'),
              product_name: String(metadata.product_name ?? ''),
              pickup_location_name: String(metadata.pickup_location_name ?? ''),
              pickup_time: String(metadata.pickup_time ?? ''),
              order_id: String(metadata.order_id ?? ''),
              created_at: createdAt ?? new Date().toISOString(),
              status: 'scheduled_pickup',
            }
          : undefined;
      return {
        id,
        message: typeof r.message === 'string' ? r.message : '',
        metadata: r.metadata ?? {},
        read_status: Boolean(r.read_status),
        created_at: createdAt,
        data: pickupData,
      };
    });
    setItems((prev) => {
      const initialIds = new Set(initial.map((p) => p.id));
      const merged = [...initial, ...prev.filter((p) => !initialIds.has(p.id))];
      // stable order: most recent first
      return merged.sort((a, b) => (b.created_at ?? '').localeCompare(a.created_at ?? ''));
    });
  }, []);

  const markRead = useCallback(async (notificationId: string) => {
    const t = getAuthToken();
    if (!t) return;
    await fetch(apiUrl(`/api/notifications/${encodeURIComponent(notificationId)}/read`), {
      method: 'POST',
      headers: { Authorization: `Bearer ${t}` },
    }).catch(() => null);
    setItems((prev) => prev.map((p) => (p.id === notificationId ? { ...p, read_status: true } : p)));
  }, []);

  const markAllRead = useCallback(async () => {
    const t = getAuthToken();
    if (!t) return;
    await fetch(apiUrl('/api/notifications/read-all'), {
      method: 'POST',
      headers: { Authorization: `Bearer ${t}` },
    }).catch(() => null);
    setItems((prev) => prev.map((p) => ({ ...p, read_status: true })));
  }, []);

  const deleteNotification = useCallback(async (notificationId: string) => {
    const t = getAuthToken();
    if (!t) return;
    await fetch(apiUrl(`/api/notifications/${encodeURIComponent(notificationId)}`), {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${t}` },
    }).catch(() => null);
    setItems((prev) => prev.filter((p) => p.id !== notificationId));
  }, []);

  useEffect(() => {
    loadInitial();
  }, [loadInitial]);

  useEffect(() => {
    const t = getAuthToken();
    if (!t) return;

    let cancelled = false;

    const loadStores = async () => {
      try {
        const res = await fetch(apiUrl('/api/stores'));
        const data = await res.json().catch(() => null);
        if (Array.isArray(data)) {
          setStoreIds(data.map((s: any) => String(s.id)).filter(Boolean));
        }
      } catch {
        // ignore
      }
    };

    loadStores();
    return () => {
      cancelled = true;
    };
  }, [token]);

  useEffect(() => {
    const t = getAuthToken();
    if (!t) return;
    if (!storeIds.length) return;

    unmountedRef.current = false;
    reconnectAttemptRef.current = 0;

    const connect = () => {
      if (unmountedRef.current) return;
      setConnState((prev) => (prev === 'CONNECTED' ? 'CONNECTED' : 'RECONNECTING'));

      const wsUrl = `${toWsUrl(getBackendUrl(), '/api/notifications/ws')}?token=${encodeURIComponent(t)}`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = async () => {
        if (unmountedRef.current) return;
        reconnectAttemptRef.current = 0;
        setConnState('CONNECTED');

        // Subscribe to all stores this dashboard should receive.
        ws.send(
          JSON.stringify({
            type: 'subscribe',
            store_ids: storeIds,
          }),
        );

        // Sync missed notifications after reconnect.
        await loadInitial();
      };

      ws.onclose = () => {
        if (unmountedRef.current) return;
        setConnState('RECONNECTING');
        reconnectAttemptRef.current += 1;
        const delay = Math.min(5000, 800 * 2 ** (reconnectAttemptRef.current - 1));
        window.setTimeout(() => connect(), delay);
      };

      ws.onerror = () => {
        // Let onclose drive the reconnect state.
        try {
          ws.close();
        } catch {
          // ignore
        }
      };

      ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
          const type = msg?.type;
          const data = (msg?.data ?? msg) as any;

          // Backward compatibility: older server used type 'notification'.
          const isNotification =
            type === 'notification.created' || type === 'notification';
          if (!isNotification) return;

          const n = data as PickupScheduledNotification | undefined;
          if (!n?.notification_id) return;

          enqueue({
            id: String(n.notification_id),
            message: '',
            metadata: { status: n.status, ...n },
            read_status: false,
            created_at: n.created_at ?? null,
            data: n,
          });

          // ACK immediately so the server can stop retrying.
          try {
            ws.send(
              JSON.stringify({
                type: 'notification.ack',
                notification_id: n.notification_id,
              }),
            );
          } catch {
            // ignore
          }
      } catch {
        // ignore
      }
      };
    };

    connect();

    return () => {
      unmountedRef.current = true;
      try {
        wsRef.current?.close();
      } catch {
        // ignore
      }
      if (flushTimerRef.current != null) {
        window.clearTimeout(flushTimerRef.current);
        flushTimerRef.current = null;
      }
    };
  }, [enqueue, loadInitial, storeIds, token]);

  return { items, connState, markRead, markAllRead, deleteNotification, reload: loadInitial };
}

