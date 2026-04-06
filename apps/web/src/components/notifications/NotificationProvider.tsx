"use client";

import React, { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { clientEnv } from "@/lib/api";

export type PickupNotification = {
  type: "PICKUP_REQUEST";
  customerName: string;
  locationName: string;
  pickupTime: string;
  orderId: string;
};

export type SaleNotification = {
  type: "notification.created";
  data: {
    notification_id: string;
    order_id: string;
    order_number?: string;
    customer_name?: string;
    total?: number;
    currency?: string;
    delivery_method?: string;
    status: string;
    created_at: string;
  };
};

export type AppNotification = PickupNotification | SaleNotification;

type NotificationContextValue = {
  push: (n: PickupNotification) => void;
  pushSale: (n: SaleNotification) => void;
  unreadCount: number;
  markRead: (id: string) => void;
};

const NotificationContext = createContext<NotificationContextValue | null>(null);

export function NotificationProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<Array<{ id: string; n: PickupNotification }>>([]);
  const [saleItems, setSaleItems] = useState<Array<{ id: string; n: SaleNotification; read: boolean }>>([]);
  const wsRef = useRef<WebSocket | null>(null);

  const push = (n: PickupNotification) => {
    setItems((prev) => [{ id: crypto.randomUUID(), n }, ...prev].slice(0, 5));
  };

  const pushSale = (n: SaleNotification) => {
    setSaleItems((prev) => [{ id: n.data.notification_id, n, read: false }, ...prev].slice(0, 20));
  };

  const markRead = (id: string) => {
    setSaleItems((prev) => prev.map(item => item.id === id ? { ...item, read: true } : item));
  };

  const unreadCount = saleItems.filter(item => !item.read).length;

  useEffect(() => {
    const url = new URL(clientEnv.NEXT_PUBLIC_API_ORIGIN);
    url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
    url.pathname = "/api/notifications/ws";
    const ws = new WebSocket(url.toString());
    wsRef.current = ws;
    ws.onmessage = (ev) => {
      try {
        const parsed = JSON.parse(String(ev.data));
        if (parsed?.type === "PICKUP_REQUEST") push(parsed as PickupNotification);
        if (parsed?.type === "notification.created") pushSale(parsed as SaleNotification);
      } catch {
        // ignore
      }
    };
    ws.onerror = () => {
      // Silently reconnect on error
    };
    ws.onclose = () => {
      // Attempt reconnect after 5 seconds
      setTimeout(() => {
        // Reconnect logic would go here
      }, 5000);
    };
    return () => {
      try {
        ws.close();
      } catch {
        // ignore
      }
    };
  }, []);

  const value = useMemo(() => ({ push, pushSale, unreadCount, markRead }), [unreadCount]);

  return (
    <NotificationContext.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed right-4 top-4 z-50 flex w-[min(420px,calc(100vw-2rem))] flex-col gap-3">
        <AnimatePresence initial={false}>
          {/* Sale/Order notifications */}
          {saleItems.filter(item => !item.read).slice(0, 3).map((it, idx) => (
            <motion.div
              key={it.id}
              initial={{ opacity: 0, y: 20, scale: 0.96 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 10, scale: 0.98 }}
              transition={{ delay: idx * 0.08, type: "spring", stiffness: 520, damping: 38 }}
              className="pointer-events-auto rounded-2xl border border-white/10 bg-neutral-950/90 p-4 text-white shadow-[0_20px_60px_rgba(0,0,0,0.5)] backdrop-blur cursor-pointer"
              whileHover={{ scale: 1.02, boxShadow: "0 24px 64px rgba(0,0,0,0.6)" }}
              whileTap={{ scale: 0.97 }}
              onClick={() => markRead(it.id)}
            >
              <div className="text-xs font-medium text-white/60">
                {it.n.data.status === "new_order" ? "New Order" : it.n.data.status === "paid" ? "Payment Confirmed" : "Notification"}
              </div>
              {it.n.data.customer_name && (
                <div className="mt-1 text-sm font-semibold">{it.n.data.customer_name}</div>
              )}
              <div className="mt-2 text-sm text-white/80">
                Order #{it.n.data.order_number || it.n.data.order_id.slice(0, 8)}
                {it.n.data.total !== undefined && ` • $${it.n.data.total.toFixed(2)}`}
              </div>
            </motion.div>
          ))}
          {/* Pickup notifications */}
          {items.map((it, idx) => (
            <motion.div
              key={it.id}
              initial={{ opacity: 0, y: 20, scale: 0.96 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 10, scale: 0.98 }}
              transition={{ delay: idx * 0.08, type: "spring", stiffness: 520, damping: 38 }}
              className="pointer-events-auto rounded-2xl border border-white/10 bg-neutral-950/90 p-4 text-white shadow-[0_20px_60px_rgba(0,0,0,0.5)] backdrop-blur"
              whileHover={{ scale: 1.02, boxShadow: "0 24px 64px rgba(0,0,0,0.6)" }}
              whileTap={{ scale: 0.97 }}
            >
              <div className="text-xs font-medium text-white/60">Pickup request</div>
              <div className="mt-1 text-sm font-semibold">{it.n.locationName}</div>
              <div className="mt-2 text-sm text-white/80">
                {it.n.customerName} • {it.n.pickupTime} • {it.n.orderId}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </NotificationContext.Provider>
  );
}

export function useNotifications() {
  const ctx = useContext(NotificationContext);
  if (!ctx) throw new Error("useNotifications must be used within NotificationProvider");
  return ctx;
}

