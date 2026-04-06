/**
 * CONFIT — Notification Store
 * ============================
 * Centralized Zustand store for both customer and owner notifications.
 * Enforces recipient isolation at the data layer — customer notifications
 * never leak to owners and vice versa.
 *
 * Enhanced with: soft-delete (dismissed), channel tracking, date grouping.
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

// ─── Types ───

export type RecipientType = 'customer' | 'owner';

export type OrderStatus =
  | 'confirmed'
  | 'processing'
  | 'shipped'
  | 'ready_for_pickup'
  | 'delivered'
  | 'cancelled';

export type NotificationType =
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

export type NotificationChannel = 'in_app' | 'email' | 'push' | 'toast';

export interface NotificationData {
  // Customer fields
  customer_name?: string;
  customer_contact?: string;
  customer_email?: string;
  customer_phone?: string;
  // Product fields
  product_name?: string;
  product_id?: string;
  product_sku?: string;
  product_category?: string;
  product_type?: string;
  product_image?: string;
  // Store fields
  store_name?: string;
  store_address?: string;
  store_city?: string;
  store_phone?: string;
  // Transaction fields
  transaction_time?: string;
  price_paid?: number;
  price?: number;
  currency?: string;
  payment_method?: string;
  // Order fields
  order_id?: string;
  order_status?: OrderStatus;
  // Sale fields (for dashboard deep-linking)
  sale_id?: string;
  // Other
  image_url?: string;
  brand_name?: string;
}

export interface AppNotification {
  id: string;
  recipient_type: RecipientType;
  recipient_id: string;
  type: NotificationType;
  channel: NotificationChannel;
  title: string;
  message: string;
  data: NotificationData;
  read: boolean;
  dismissed: boolean; // soft-delete
  created_at: string;
}

// ─── Date Grouping ───

export interface GroupedNotifications {
  today: AppNotification[];
  yesterday: AppNotification[];
  earlier: AppNotification[];
}

function isToday(dateStr: string): boolean {
  const d = new Date(dateStr);
  const now = new Date();
  return d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate();
}

function isYesterday(dateStr: string): boolean {
  const d = new Date(dateStr);
  const yesterday = new Date();
  yesterday.setDate(yesterday.getDate() - 1);
  return d.getFullYear() === yesterday.getFullYear() &&
    d.getMonth() === yesterday.getMonth() &&
    d.getDate() === yesterday.getDate();
}

// ─── Filter Types ───

export type NotificationFilter = 'all' | 'unread' | 'orders' | 'promotions';

const ORDER_TYPES: NotificationType[] = [
  'order_placed', 'order_confirmed', 'order_shipped',
  'order_delivered', 'order_cancelled', 'payment_success',
];

const PROMO_TYPES: NotificationType[] = [
  'styling_suggestion', 'price_drop', 'back_in_stock',
  'wishlist_available', 'promotion',
];

// ─── Store State ───

interface NotificationState {
  notifications: AppNotification[];

  // Actions
  addNotification: (n: AppNotification) => void;
  addNotifications: (ns: AppNotification[]) => void;
  markRead: (id: string) => void;
  markAllRead: (recipientType: RecipientType, recipientId: string) => void;
  dismissNotification: (id: string) => void;
  restoreNotification: (id: string) => void;
  deleteNotification: (id: string) => void;
  clearAll: (recipientType: RecipientType, recipientId: string) => void;

  // Selectors
  getForRecipient: (type: RecipientType, id: string) => AppNotification[];
  getFilteredNotifications: (type: RecipientType, id: string, filter: NotificationFilter) => AppNotification[];
  getGroupedByDate: (type: RecipientType, id: string, filter?: NotificationFilter) => GroupedNotifications;
  getUnreadCount: (type: RecipientType, id: string) => number;
}

export const useNotificationStore = create<NotificationState>()(
  persist(
    (set, get) => ({
      notifications: [],

      addNotification: (n) =>
        set((state) => {
          // Deduplication by ID
          if (state.notifications.some((x) => x.id === n.id)) return state;
          return { notifications: [n, ...state.notifications] };
        }),

      addNotifications: (ns) =>
        set((state) => {
          const existingIds = new Set(state.notifications.map((x) => x.id));
          const newOnes = ns.filter((x) => !existingIds.has(x.id));
          if (newOnes.length === 0) return state;
          return { notifications: [...newOnes, ...state.notifications] };
        }),

      markRead: (id) =>
        set((state) => ({
          notifications: state.notifications.map((n) =>
            n.id === id ? { ...n, read: true } : n
          ),
        })),

      markAllRead: (recipientType, recipientId) =>
        set((state) => ({
          notifications: state.notifications.map((n) =>
            n.recipient_type === recipientType && n.recipient_id === recipientId
              ? { ...n, read: true }
              : n
          ),
        })),

      dismissNotification: (id) =>
        set((state) => ({
          notifications: state.notifications.map((n) =>
            n.id === id ? { ...n, dismissed: true } : n
          ),
        })),

      restoreNotification: (id) =>
        set((state) => ({
          notifications: state.notifications.map((n) =>
            n.id === id ? { ...n, dismissed: false } : n
          ),
        })),

      deleteNotification: (id) =>
        set((state) => ({
          notifications: state.notifications.filter((n) => n.id !== id),
        })),

      clearAll: (recipientType, recipientId) =>
        set((state) => ({
          notifications: state.notifications.filter(
            (n) => !(n.recipient_type === recipientType && n.recipient_id === recipientId)
          ),
        })),

      // Recipient-isolated selectors (excludes dismissed)
      getForRecipient: (type, id) =>
        get().notifications.filter(
          (n) => n.recipient_type === type && n.recipient_id === id && !n.dismissed
        ),

      getFilteredNotifications: (type, id, filter) => {
        const base = get().notifications.filter(
          (n) => n.recipient_type === type && n.recipient_id === id && !n.dismissed
        );
        switch (filter) {
          case 'unread':
            return base.filter((n) => !n.read);
          case 'orders':
            return base.filter((n) => ORDER_TYPES.includes(n.type));
          case 'promotions':
            return base.filter((n) => PROMO_TYPES.includes(n.type));
          default:
            return base;
        }
      },

      getGroupedByDate: (type, id, filter = 'all') => {
        const filtered = get().getFilteredNotifications(type, id, filter);
        const groups: GroupedNotifications = { today: [], yesterday: [], earlier: [] };

        for (const n of filtered) {
          if (isToday(n.created_at)) {
            groups.today.push(n);
          } else if (isYesterday(n.created_at)) {
            groups.yesterday.push(n);
          } else {
            groups.earlier.push(n);
          }
        }

        return groups;
      },

      getUnreadCount: (type, id) =>
        get().notifications.filter(
          (n) => n.recipient_type === type && n.recipient_id === id && !n.read && !n.dismissed
        ).length,
    }),
    {
      name: 'confit-notifications',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ notifications: state.notifications }),
    }
  )
);
