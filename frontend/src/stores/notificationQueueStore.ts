/**
 * CONFIT — Notification Queue Store
 * ===================================
 * Holds notifications queued for batch delivery (daily digest / weekly summary).
 * The NotificationService writes here instead of dispatching immediately
 * when the user's frequency preference is daily_digest or weekly_summary.
 *
 * A background scheduler (or manual flush) processes the queue.
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type { AppNotification } from '@/stores/notificationStore';

// ─── Types ───

export type BatchType = 'daily_digest' | 'weekly_summary';

export interface QueuedNotification {
  notification: AppNotification;
  batch_type: BatchType;
  queued_at: string;
}

interface NotificationQueueState {
  queue: QueuedNotification[];

  /** Add a notification to the batch queue */
  queueNotification: (notification: AppNotification, batchType: BatchType) => void;

  /** Get all queued notifications for a recipient and batch type */
  getQueuedNotifications: (recipientId: string, batchType: BatchType) => QueuedNotification[];

  /** Get all queued notifications for a recipient (any batch type) */
  getAllQueued: (recipientId: string) => QueuedNotification[];

  /** Remove all queued notifications for a recipient and batch type after delivery */
  flushQueue: (recipientId: string, batchType: BatchType) => void;

  /** Remove a single queued notification */
  removeFromQueue: (notificationId: string) => void;

  /** Get queue count for a specific recipient */
  getQueueCount: (recipientId: string) => number;
}

export const useNotificationQueueStore = create<NotificationQueueState>()(
  persist(
    (set, get) => ({
      queue: [],

      queueNotification: (notification, batchType) =>
        set((state) => {
          // Deduplicate
          if (state.queue.some((q) => q.notification.id === notification.id)) {
            return state;
          }
          return {
            queue: [
              ...state.queue,
              {
                notification,
                batch_type: batchType,
                queued_at: new Date().toISOString(),
              },
            ],
          };
        }),

      getQueuedNotifications: (recipientId, batchType) =>
        get().queue.filter(
          (q) =>
            q.notification.recipient_id === recipientId &&
            q.batch_type === batchType
        ),

      getAllQueued: (recipientId) =>
        get().queue.filter((q) => q.notification.recipient_id === recipientId),

      flushQueue: (recipientId, batchType) =>
        set((state) => ({
          queue: state.queue.filter(
            (q) =>
              !(
                q.notification.recipient_id === recipientId &&
                q.batch_type === batchType
              )
          ),
        })),

      removeFromQueue: (notificationId) =>
        set((state) => ({
          queue: state.queue.filter(
            (q) => q.notification.id !== notificationId
          ),
        })),

      getQueueCount: (recipientId) =>
        get().queue.filter((q) => q.notification.recipient_id === recipientId)
          .length,
    }),
    {
      name: 'confit-notification-queue',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ queue: state.queue }),
    }
  )
);
