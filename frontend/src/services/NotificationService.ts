/**
 * CONFIT — NotificationService
 * =============================
 * Central dispatch service for all notification logic.
 * All notification calls flow through this service — no inline
 * notification code scattered across components.
 *
 * Accepts transactionData, resolves user preferences, then dispatches
 * to the appropriate channels (toast, email, push, in-app).
 *
 * Now: checks per-type frequency and queues batch notifications.
 */

import { useNotificationStore, type AppNotification, type NotificationType, type RecipientType, type OrderStatus } from '@/stores/notificationStore';
import { checkDispatchPreferences } from '@/hooks/useNotificationPreferences';
import { useNotificationQueueStore, type BatchType } from '@/stores/notificationQueueStore';
import { useNotificationAnalyticsStore } from '@/stores/notificationAnalyticsStore';
import { apiUrl } from '@/lib/api';
import { getAuthToken } from '@/lib/auth';
import { toast as sonnerToast } from 'sonner';
import type { NotificationEvent, AnalyticsChannel, AnalyticsRecipientType } from '@/types/notificationAnalyticsTypes';

// ─── Analytics Helper (non-blocking) ───

function logAnalyticsEvent(
  notificationId: string,
  recipientId: string,
  recipientType: AnalyticsRecipientType,
  channel: AnalyticsChannel,
  eventType: 'sent' | 'delivered',
  payload?: Record<string, any>
): void {
  setTimeout(() => {
    try {
      const store = useNotificationAnalyticsStore.getState();
      const event: NotificationEvent = {
        id: `evt-${notificationId}-${eventType}-${Date.now()}`,
        notification_id: notificationId,
        recipient_id: recipientId,
        recipient_type: recipientType,
        channel,
        event_type: eventType,
        event_timestamp: new Date().toISOString(),
        payload: payload || {},
      };
      store.logEvent(event);
    } catch {
      // Silent — analytics must never break dispatch
    }
  }, 0);
}

// ─── Transaction Payload ───

export interface TransactionData {
  orderId: string;
  orderNumber: string;
  orderStatus: OrderStatus;
  transactionTime: string;
  // Customer
  customerName: string;
  customerEmail: string;
  customerPhone?: string;
  // Product(s)
  items: TransactionItem[];
  // Store / Factory
  storeName: string;
  storeAddress: string;
  storeId?: string;
  // Payment
  totalPaid: number;
  currency: string;
  paymentMethod: string;
}

export interface TransactionItem {
  productId: string;
  productName: string;
  productSku?: string;
  productCategory?: string;
  price: number;
  quantity: number;
  imageUrl?: string;
  brandName?: string;
}

// ─── Idempotency Guard ───

const _dispatchedTransactions = new Set<string>();

// ─── Channel Templates ───

function customerToastTemplate(data: TransactionData): { title: string; description: string } {
  const itemNames = data.items.map((i) => i.productName).join(', ');
  return {
    title: '✨ Order Confirmed!',
    description: `Order #${data.orderNumber} — ${itemNames}. Total: ${data.currency}${data.totalPaid.toFixed(2)}`,
  };
}

function customerInAppTemplate(data: TransactionData): Pick<AppNotification, 'title' | 'message' | 'type'> {
  const itemCount = data.items.reduce((sum, i) => sum + i.quantity, 0);
  return {
    type: 'order_confirmed',
    title: `Order #${data.orderNumber} Confirmed`,
    message: `Your order of ${itemCount} item${itemCount > 1 ? 's' : ''} from ${data.storeName} has been confirmed. Total: ${data.currency}${data.totalPaid.toFixed(2)}`,
  };
}

function customerEmailPayload(data: TransactionData) {
  return {
    to: data.customerEmail,
    template: 'order_confirmation',
    subject: `CONFIT — Order #${data.orderNumber} Confirmed`,
    data: {
      customerName: data.customerName,
      orderNumber: data.orderNumber,
      orderStatus: data.orderStatus,
      items: data.items.map((i) => ({
        name: i.productName,
        sku: i.productSku,
        category: i.productCategory,
        price: i.price,
        quantity: i.quantity,
        image: i.imageUrl,
        brand: i.brandName,
      })),
      totalPaid: data.totalPaid,
      currency: data.currency,
      paymentMethod: data.paymentMethod,
      storeName: data.storeName,
      storeAddress: data.storeAddress,
      transactionTime: data.transactionTime,
    },
  };
}

function customerPushPayload(data: TransactionData) {
  return {
    title: 'Order Confirmed ✓',
    body: `#${data.orderNumber} — ${data.currency}${data.totalPaid.toFixed(2)} from ${data.storeName}`,
    data: {
      orderId: data.orderId,
      type: 'order_confirmed',
    },
  };
}

function ownerInAppTemplate(data: TransactionData): Pick<AppNotification, 'title' | 'message' | 'type'> {
  const itemSummary = data.items.map((i) => `${i.productName} (×${i.quantity})`).join(', ');
  return {
    type: 'order_placed',
    title: `New Order #${data.orderNumber}`,
    message: `${data.customerName} ordered: ${itemSummary}. Total: ${data.currency}${data.totalPaid.toFixed(2)} via ${data.paymentMethod}`,
  };
}

function ownerEmailPayload(data: TransactionData) {
  return {
    template: 'owner_new_order',
    subject: `New Order #${data.orderNumber} — ${data.customerName}`,
    data: {
      orderNumber: data.orderNumber,
      customerName: data.customerName,
      customerEmail: data.customerEmail,
      customerPhone: data.customerPhone,
      items: data.items.map((i) => ({
        name: i.productName,
        sku: i.productSku,
        category: i.productCategory,
        price: i.price,
        quantity: i.quantity,
        brand: i.brandName,
      })),
      totalPaid: data.totalPaid,
      currency: data.currency,
      paymentMethod: data.paymentMethod,
      storeName: data.storeName,
      storeAddress: data.storeAddress,
      transactionTime: data.transactionTime,
      orderStatus: data.orderStatus,
    },
  };
}

// ─── Shared Payload Builder ───

function buildNotificationData(data: TransactionData) {
  const firstItem = data.items[0];
  return {
    customer_name: data.customerName,
    customer_contact: data.customerEmail,
    product_name: firstItem?.productName || '',
    product_id: firstItem?.productId || '',
    product_sku: firstItem?.productSku || '',
    product_category: firstItem?.productCategory || '',
    store_name: data.storeName,
    store_address: data.storeAddress,
    transaction_time: data.transactionTime,
    price_paid: data.totalPaid,
    currency: data.currency,
    payment_method: data.paymentMethod,
    order_id: data.orderId,
    order_status: data.orderStatus,
    image_url: firstItem?.imageUrl || '',
    brand_name: firstItem?.brandName || '',
  };
}

// ─── API Helpers (fire-and-forget) ───

async function sendEmailNotification(payload: ReturnType<typeof customerEmailPayload | typeof ownerEmailPayload>) {
  try {
    const token = getAuthToken();
    await fetch(apiUrl('/api/notifications/email'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(payload),
    });
  } catch (err) {
    console.warn('[NotificationService] Email dispatch failed:', err);
  }
}

async function sendPushNotification(payload: ReturnType<typeof customerPushPayload>) {
  try {
    const token = getAuthToken();
    await fetch(apiUrl('/api/notifications/push'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(payload),
    });
  } catch (err) {
    console.warn('[NotificationService] Push dispatch failed:', err);
  }
}

// ─── Queue Helper ───

function queueForBatch(notification: AppNotification, frequency: 'daily_digest' | 'weekly_summary') {
  const queueStore = useNotificationQueueStore.getState();
  queueStore.queueNotification(notification, frequency as BatchType);
  console.info(`[NotificationService] Queued notification ${notification.id} for ${frequency}`);
}

// ─── Main Service ───

export class NotificationService {
  /**
   * Dispatch all purchase notifications for both customer and owner.
   * Called synchronously after successful order placement.
   * Each channel is independent — if one fails, others still fire.
   *
   * Now respects per-type frequency and queues batch notifications.
   */
  static dispatchPurchaseNotifications(data: TransactionData, customerId: string, ownerId?: string): void {
    // ── Idempotency: prevent duplicate dispatch ──
    const txKey = `${data.orderId}-${customerId}`;
    if (_dispatchedTransactions.has(txKey)) {
      console.warn('[NotificationService] Duplicate dispatch blocked for:', txKey);
      return;
    }
    _dispatchedTransactions.add(txKey);

    const store = useNotificationStore.getState();
    const sharedData = buildNotificationData(data);
    const now = new Date().toISOString();
    const notifType = 'order_confirmed';

    // ═══ CUSTOMER NOTIFICATIONS ═══

    // 1. In-App Toast + Notification Center
    const inAppCheck = checkDispatchPreferences(customerId, 'customer', notifType, 'in_app');
    if (inAppCheck.shouldDispatch) {
      const inAppData = customerInAppTemplate(data);
      const notification: AppNotification = {
        id: `notif-customer-${data.orderId}-${Date.now()}`,
        recipient_type: 'customer',
        recipient_id: customerId,
        type: inAppData.type as NotificationType,
        title: inAppData.title,
        message: inAppData.message,
        data: sharedData,
        read: false,
        dismissed: false,
        channel: 'in_app',
        created_at: now,
      };

      if (inAppCheck.frequency === 'real_time') {
        // Fire toast
        try {
          const toastData = customerToastTemplate(data);
          sonnerToast(toastData.title, {
            description: toastData.description,
            duration: 6000,
            className: 'confit-purchase-toast',
          });
        } catch (err) {
          console.warn('[NotificationService] Toast dispatch failed:', err);
        }
        // Add to notification center
        store.addNotification(notification);
        logAnalyticsEvent(notification.id, customerId, 'customer', 'in_app', 'sent', sharedData);
      } else if (inAppCheck.frequency === 'daily_digest' || inAppCheck.frequency === 'weekly_summary') {
        queueForBatch(notification, inAppCheck.frequency);
      }
    }

    // 2. Email
    const emailCheck = checkDispatchPreferences(customerId, 'customer', notifType, 'email');
    if (emailCheck.shouldDispatch) {
      if (emailCheck.frequency === 'real_time') {
        const emailPayload = customerEmailPayload(data);
        sendEmailNotification(emailPayload);
        logAnalyticsEvent(`notif-customer-email-${data.orderId}`, customerId, 'customer', 'email', 'sent', sharedData);
      } else if (emailCheck.frequency === 'daily_digest' || emailCheck.frequency === 'weekly_summary') {
        // Queue email notification for batch delivery
        const emailNotification: AppNotification = {
          id: `notif-customer-email-${data.orderId}-${Date.now()}`,
          recipient_type: 'customer',
          recipient_id: customerId,
          type: notifType,
          title: `Order #${data.orderNumber} Confirmed`,
          message: `Email queued for ${emailCheck.frequency.replace('_', ' ')}`,
          data: sharedData,
          read: false,
          dismissed: false,
          channel: 'email',
          created_at: now,
        };
        queueForBatch(emailNotification, emailCheck.frequency);
      }
    }

    // 3. Push
    const pushCheck = checkDispatchPreferences(customerId, 'customer', notifType, 'push');
    if (pushCheck.shouldDispatch) {
      if (pushCheck.frequency === 'real_time') {
        const pushPayload = customerPushPayload(data);
        sendPushNotification(pushPayload);
        logAnalyticsEvent(`notif-customer-push-${data.orderId}`, customerId, 'customer', 'push', 'sent', sharedData);
      } else if (pushCheck.frequency === 'daily_digest' || pushCheck.frequency === 'weekly_summary') {
        const pushNotification: AppNotification = {
          id: `notif-customer-push-${data.orderId}-${Date.now()}`,
          recipient_type: 'customer',
          recipient_id: customerId,
          type: notifType,
          title: `Order #${data.orderNumber} Confirmed`,
          message: `Push queued for ${pushCheck.frequency.replace('_', ' ')}`,
          data: sharedData,
          read: false,
          dismissed: false,
          channel: 'push',
          created_at: now,
        };
        queueForBatch(pushNotification, pushCheck.frequency);
      }
    }

    // ═══ OWNER NOTIFICATIONS ═══
    const resolvedOwnerId = ownerId || data.storeId || 'store-owner';
    const ownerNotifType = 'order_placed';

    // 1. In-App Notification Center for owner
    const ownerInAppCheck = checkDispatchPreferences(resolvedOwnerId, 'store_owner', ownerNotifType, 'in_app');
    if (ownerInAppCheck.shouldDispatch) {
      const ownerData = ownerInAppTemplate(data);
      const ownerNotification: AppNotification = {
        id: `notif-owner-${data.orderId}-${Date.now()}`,
        recipient_type: 'owner',
        recipient_id: resolvedOwnerId,
        type: ownerData.type as NotificationType,
        title: ownerData.title,
        message: ownerData.message,
        data: sharedData,
        read: false,
        dismissed: false,
        channel: 'in_app',
        created_at: now,
      };

      if (ownerInAppCheck.frequency === 'real_time') {
        store.addNotification(ownerNotification);
        logAnalyticsEvent(ownerNotification.id, resolvedOwnerId, 'owner', 'in_app', 'sent', sharedData);
      } else if (ownerInAppCheck.frequency === 'daily_digest' || ownerInAppCheck.frequency === 'weekly_summary') {
        queueForBatch(ownerNotification, ownerInAppCheck.frequency);
      }
    }

    // 2. Owner Email
    const ownerEmailCheck = checkDispatchPreferences(resolvedOwnerId, 'store_owner', ownerNotifType, 'email');
    if (ownerEmailCheck.shouldDispatch) {
      if (ownerEmailCheck.frequency === 'real_time') {
        const ownerEmail = ownerEmailPayload(data);
        sendEmailNotification(ownerEmail);
      } else if (ownerEmailCheck.frequency === 'daily_digest' || ownerEmailCheck.frequency === 'weekly_summary') {
        const ownerEmailNotification: AppNotification = {
          id: `notif-owner-email-${data.orderId}-${Date.now()}`,
          recipient_type: 'owner',
          recipient_id: resolvedOwnerId,
          type: ownerNotifType as NotificationType,
          title: `New Order #${data.orderNumber}`,
          message: `Email queued for ${ownerEmailCheck.frequency.replace('_', ' ')}`,
          data: sharedData,
          read: false,
          dismissed: false,
          channel: 'email',
          created_at: now,
        };
        queueForBatch(ownerEmailNotification, ownerEmailCheck.frequency);
      }
    }
  }

  /**
   * Dispatch an order status update notification.
   * Now respects per-type frequency preferences.
   */
  static dispatchOrderStatusUpdate(
    orderId: string,
    orderNumber: string,
    newStatus: OrderStatus,
    recipientId: string,
    recipientType: RecipientType
  ): void {
    const store = useNotificationStore.getState();
    const statusLabels: Record<OrderStatus, string> = {
      confirmed: 'Order Confirmed',
      processing: 'Processing',
      shipped: 'Order Shipped',
      ready_for_pickup: 'Ready for Pickup',
      delivered: 'Order Delivered',
      cancelled: 'Order Cancelled',
    };

    const typeMap: Record<OrderStatus, NotificationType> = {
      confirmed: 'order_confirmed',
      processing: 'order_confirmed',
      shipped: 'order_shipped',
      ready_for_pickup: 'order_confirmed',
      delivered: 'order_delivered',
      cancelled: 'order_cancelled',
    };

    const notifType = typeMap[newStatus];

    // Check preferences before dispatching
    const prefRecipientType = recipientType === 'customer' ? 'customer' : 'store_owner';
    const dispatchCheck = checkDispatchPreferences(recipientId, prefRecipientType, notifType, 'in_app');

    if (!dispatchCheck.shouldDispatch) {
      console.info(`[NotificationService] Status update skipped for ${recipientId}: preferences disabled`);
      return;
    }

    const notification: AppNotification = {
      id: `notif-status-${orderId}-${newStatus}-${Date.now()}`,
      recipient_type: recipientType,
      recipient_id: recipientId,
      type: notifType,
      title: statusLabels[newStatus],
      message: `Order #${orderNumber} status updated to ${statusLabels[newStatus]}`,
      data: {
        order_id: orderId,
        order_status: newStatus,
      },
      read: false,
      dismissed: false,
      channel: 'in_app',
      created_at: new Date().toISOString(),
    };

    if (dispatchCheck.frequency === 'real_time') {
      store.addNotification(notification);
    } else if (dispatchCheck.frequency === 'daily_digest' || dispatchCheck.frequency === 'weekly_summary') {
      queueForBatch(notification, dispatchCheck.frequency);
    }
  }
}

export default NotificationService;
