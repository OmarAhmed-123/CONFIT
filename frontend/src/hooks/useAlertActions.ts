/**
 * CONFIT — Sales Alert Actions Hook
 * ===================================
 * Hook for handling one-click alert actions with routing logic.
 */

import { useCallback, useMemo } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import {
  type SalesAlert,
  type AlertAction,
  type AlertActionType,
  type SalesAlertType,
} from '@/types/salesAlertTypes';
import { useSalesAlertStore } from '@/stores/salesAlertStore';

// ─── Action Route Mapping ─────────────────────────────────────────────────────

const ACTION_ROUTES: Record<AlertActionType, (data: Record<string, unknown>) => string> = {
  view_order: (data) => `/brand-dashboard/orders/${data.order_id}`,
  view_product: (data) => `/brand-dashboard/products/${data.product_id}`,
  view_customer: (data) => `/brand-dashboard/customers/${data.customer_id}`,
  view_analytics: () => '/brand-dashboard/analytics/conversion',
  analyze_returns: (data) => `/brand-dashboard/analytics/returns?product_id=${data.product_id || ''}`,
  restock: (data) => `/brand-dashboard/inventory/restock?product_id=${data.product_id || ''}`,
  configure: () => '/brand-dashboard/settings/alerts',
  acknowledge: () => '', // No route - handled by acknowledge action
  dismiss: () => '', // No route - handled by dismiss action
};

// ─── Action Labels ────────────────────────────────────────────────────────────

const ACTION_LABELS: Record<AlertActionType, string> = {
  view_order: 'View Order',
  view_product: 'View Product',
  view_customer: 'View Customer',
  view_analytics: 'View Analytics',
  analyze_returns: 'Analyze Returns',
  restock: 'Restock',
  configure: 'Configure',
  acknowledge: 'Acknowledge',
  dismiss: 'Dismiss',
};

// ─── Main Hook ─────────────────────────────────────────────────────────────────

export function useAlertActions(storeId: string) {
  const router = useRouter();
  const pathname = usePathname();

  const store = useSalesAlertStore((s) => ({
    markRead: s.markRead,
    dismissAlert: s.dismissAlert,
    acknowledgeAlert: s.acknowledgeAlert,
    resolveAlert: s.resolveAlert,
  }));

  // Execute an alert action
  const executeAction = useCallback(
    async (alert: SalesAlert, action: AlertAction) => {
      // Mark as read when taking action
      store.markRead(alert.id);

      switch (action.type) {
        case 'dismiss':
          store.dismissAlert(alert.id);
          break;

        case 'acknowledge':
          store.acknowledgeAlert(alert.id);
          break;

        case 'view_order':
        case 'view_product':
        case 'view_customer':
        case 'view_analytics':
        case 'analyze_returns':
        case 'restock':
        case 'configure':
          if (action.target_path) {
            router.push(action.target_path);
          } else {
            // Generate route from action type and alert data
            const routeGenerator = ACTION_ROUTES[action.type];
            if (routeGenerator) {
              const route = routeGenerator(alert.data as unknown as Record<string, unknown>);
              if (route) {
                router.push(route);
              }
            }
          }
          break;

        default:
          console.warn(`Unknown action type: ${action.type}`);
      }
    },
    [router, store]
  );

  // Get primary action for an alert
  const getPrimaryAction = useCallback((alert: SalesAlert): AlertAction | undefined => {
    return alert.actions.find((a) => a.primary);
  }, []);

  // Get secondary actions for an alert
  const getSecondaryActions = useCallback((alert: SalesAlert): AlertAction[] => {
    return alert.actions.filter((a) => !a.primary && a.type !== 'dismiss');
  }, []);

  // Get dismiss action for an alert
  const getDismissAction = useCallback((alert: SalesAlert): AlertAction | undefined => {
    return alert.actions.find((a) => a.type === 'dismiss');
  }, []);

  // Check if an action should open in new tab
  const shouldOpenInNewTab = useCallback((action: AlertAction): boolean => {
    // Analytics and configure actions often benefit from new tab
    return action.type === 'view_analytics' || action.type === 'configure';
  }, []);

  // Get action URL for external navigation
  const getActionUrl = useCallback((alert: SalesAlert, action: AlertAction): string | null => {
    if (action.target_path) {
      return action.target_path;
    }

    const routeGenerator = ACTION_ROUTES[action.type];
    if (routeGenerator) {
      return routeGenerator(alert.data as unknown as Record<string, unknown>);
    }

    return null;
  }, []);

  // Bulk actions
  const executeBulkAction = useCallback(
    async (alertIds: string[], actionType: 'read' | 'dismiss' | 'acknowledge') => {
      switch (actionType) {
        case 'read':
          alertIds.forEach((id) => store.markRead(id));
          break;
        case 'dismiss':
          alertIds.forEach((id) => store.dismissAlert(id));
          break;
        case 'acknowledge':
          alertIds.forEach((id) => store.acknowledgeAlert(id));
          break;
      }
    },
    [store]
  );

  return {
    executeAction,
    getPrimaryAction,
    getSecondaryActions,
    getDismissAction,
    shouldOpenInNewTab,
    getActionUrl,
    executeBulkAction,
    ACTION_LABELS,
  };
}

// ─── Alert Type to Route Mapping ───────────────────────────────────────────────

export function getAlertTypeDefaultRoute(type: SalesAlertType, data: Record<string, unknown>): string {
  const routes: Record<SalesAlertType, string> = {
    high_value_order: `/brand-dashboard/orders/${data.order_id || ''}`,
    unusual_returns: `/brand-dashboard/analytics/returns?product_id=${data.product_id || ''}`,
    inventory_depletion: `/brand-dashboard/inventory/restock?product_id=${data.product_id || ''}`,
    conversion_anomaly: '/brand-dashboard/analytics/conversion',
    customer_segment_change: `/brand-dashboard/customers/${data.customer_id || ''}`,
  };

  return routes[type] || '/brand-dashboard';
}

// ─── Keyboard Shortcuts ───────────────────────────────────────────────────────

export function useAlertKeyboardShortcuts(storeId: string) {
  const store = useSalesAlertStore((s) => ({
    alerts: s.getUnreadAlerts(storeId),
    markRead: s.markRead,
    dismissAlert: s.dismissAlert,
  }));

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      // Only handle if there are unread alerts
      if (store.alerts.length === 0) return;

      // Alt + A: Open first unread alert
      if (event.altKey && event.key === 'a') {
        const firstAlert = store.alerts[0];
        if (firstAlert) {
          const primaryAction = firstAlert.actions.find((a) => a.primary);
          if (primaryAction?.target_path) {
            window.location.href = primaryAction.target_path;
          }
        }
      }

      // Alt + D: Dismiss first unread alert
      if (event.altKey && event.key === 'd') {
        const firstAlert = store.alerts[0];
        if (firstAlert) {
          store.dismissAlert(firstAlert.id);
        }
      }

      // Alt + R: Mark all as read
      if (event.altKey && event.key === 'r') {
        store.alerts.forEach((alert) => store.markRead(alert.id));
      }
    },
    [store]
  );

  return { handleKeyDown };
}

export default useAlertActions;
