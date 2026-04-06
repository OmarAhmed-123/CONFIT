/**
 * CONFIT — Sales Alert Types
 * ============================
 * TypeScript types for the intelligent Real-Time Sales Alert System.
 * Defines alert types, severity levels, thresholds, and preferences.
 */

// ─── Alert Types ───

export type SalesAlertType =
  | 'high_value_order'
  | 'unusual_returns'
  | 'inventory_depletion'
  | 'conversion_anomaly'
  | 'customer_segment_change';

export type AlertSeverity = 'critical' | 'warning' | 'info';

export type AlertStatus = 'active' | 'acknowledged' | 'resolved' | 'dismissed';

// ─── Alert Data Payloads ───

export interface HighValueOrderData {
  order_id: string;
  order_number: string;
  customer_name: string;
  customer_id: string;
  total_value: number;
  currency: string;
  aov_threshold: number;
  aov_multiplier: number;
  items: Array<{
    product_name: string;
    product_id: string;
    quantity: number;
    price: number;
  }>;
}

export interface UnusualReturnsData {
  product_id: string;
  product_name: string;
  product_sku: string;
  return_count: number;
  return_rate_percent: number;
  baseline_return_rate_percent: number;
  time_window_hours: number;
  affected_orders: string[];
}

export interface InventoryDepletionData {
  product_id: string;
  product_name: string;
  product_sku: string;
  current_stock: number;
  reorder_point: number;
  threshold_configured: number;
  days_until_stockout: number | null;
  product_image?: string;
}

export interface ConversionAnomalyData {
  current_rate: number;
  baseline_rate: number;
  delta_percent: number;
  direction: 'drop' | 'rise';
  time_window: '1h' | '24h' | '7d';
  sessions_analyzed: number;
  conversions_analyzed: number;
}

export interface CustomerSegmentChangeData {
  customer_id: string;
  customer_name: string;
  previous_segment: 'vip' | 'returning' | 'new' | 'inactive';
  current_segment: 'vip' | 'returning' | 'new' | 'inactive';
  last_purchase_date: string | null;
  days_since_last_purchase: number;
  total_lifetime_value: number;
  total_orders: number;
}

export type AlertData =
  | HighValueOrderData
  | UnusualReturnsData
  | InventoryDepletionData
  | ConversionAnomalyData
  | CustomerSegmentChangeData;

// ─── Alert Actions ───

export type AlertActionType =
  | 'view_order'
  | 'view_product'
  | 'view_customer'
  | 'view_analytics'
  | 'analyze_returns'
  | 'restock'
  | 'configure'
  | 'acknowledge'
  | 'dismiss';

export interface AlertAction {
  type: AlertActionType;
  label: string;
  primary?: boolean;
  target_path?: string;
  target_params?: Record<string, string>;
}

// ─── Main Alert Interface ───

export interface SalesAlert {
  id: string;
  type: SalesAlertType;
  severity: AlertSeverity;
  status: AlertStatus;
  title: string;
  message: string;
  rich_preview: string;
  data: AlertData;
  actions: AlertAction[];
  store_id: string;
  store_name: string;
  created_at: string;
  acknowledged_at?: string;
  resolved_at?: string;
  read: boolean;
  dismissed: boolean;
  // Throttling metadata
  dedup_key: string;
  first_triggered_at: string;
  trigger_count: number;
  last_triggered_at: string;
}

// ─── Alert Preferences ───

export interface AlertThresholdConfig {
  // High Value Orders
  high_value_aov_multiplier: number; // e.g., 1.5 = 150% of AOV
  // Inventory Depletion
  inventory_threshold_units: number; // e.g., 10 units
  inventory_threshold_percent: number; // e.g., 20% of stock
  // Conversion Anomaly
  conversion_drop_threshold_percent: number; // e.g., 15%
  conversion_rise_threshold_percent: number; // e.g., 20%
  conversion_baseline_days: number; // Rolling average window
  // Returns Pattern
  returns_spike_count: number; // e.g., 5 returns
  returns_spike_window_hours: number; // e.g., 1 hour
  returns_rate_increase_percent: number; // e.g., 50%
  // Customer Segment
  vip_inactive_days: number; // e.g., 30 days
  returning_to_inactive_days: number; // e.g., 60 days
}

export interface AlertFrequencyConfig {
  mode: 'real_time' | 'batched' | 'throttled';
  max_alerts_per_hour: number;
  batch_interval_minutes: number;
  dedup_window_minutes: number;
  // Per-severity overrides
  critical_mode: 'real_time' | 'batched';
  warning_mode: 'real_time' | 'batched';
  info_mode: 'real_time' | 'batched';
}

export interface AlertTypePreference {
  enabled: boolean;
  frequency: 'real_time' | 'batched_15m' | 'batched_30m' | 'batched_1h' | 'disabled';
  channels: ('in_app' | 'email' | 'push')[];
}

export interface SalesAlertPreferences {
  store_id: string;
  updated_at: string;
  thresholds: AlertThresholdConfig;
  frequency: AlertFrequencyConfig;
  type_preferences: Record<SalesAlertType, AlertTypePreference>;
}

// ─── Default Configurations ───

export const DEFAULT_THRESHOLD_CONFIG: AlertThresholdConfig = {
  high_value_aov_multiplier: 1.5,
  inventory_threshold_units: 10,
  inventory_threshold_percent: 20,
  conversion_drop_threshold_percent: 15,
  conversion_rise_threshold_percent: 20,
  conversion_baseline_days: 7,
  returns_spike_count: 5,
  returns_spike_window_hours: 1,
  returns_rate_increase_percent: 50,
  vip_inactive_days: 30,
  returning_to_inactive_days: 60,
};

export const DEFAULT_FREQUENCY_CONFIG: AlertFrequencyConfig = {
  mode: 'throttled',
  max_alerts_per_hour: 10,
  batch_interval_minutes: 30,
  dedup_window_minutes: 60,
  critical_mode: 'real_time',
  warning_mode: 'batched',
  info_mode: 'batched',
};

export const DEFAULT_TYPE_PREFERENCES: Record<SalesAlertType, AlertTypePreference> = {
  high_value_order: {
    enabled: true,
    frequency: 'real_time',
    channels: ['in_app', 'push'],
  },
  unusual_returns: {
    enabled: true,
    frequency: 'batched_30m',
    channels: ['in_app', 'email'],
  },
  inventory_depletion: {
    enabled: true,
    frequency: 'real_time',
    channels: ['in_app', 'email', 'push'],
  },
  conversion_anomaly: {
    enabled: true,
    frequency: 'batched_30m',
    channels: ['in_app'],
  },
  customer_segment_change: {
    enabled: true,
    frequency: 'batched_1h',
    channels: ['in_app', 'email'],
  },
};

// ─── Alert History & Filtering ───

export interface AlertHistoryFilter {
  types?: SalesAlertType[];
  severities?: AlertSeverity[];
  statuses?: AlertStatus[];
  date_from?: string;
  date_to?: string;
  read?: boolean;
  search?: string;
}

export interface AlertHistorySort {
  field: 'created_at' | 'severity' | 'type';
  direction: 'asc' | 'desc';
}

// ─── Severity Helpers ───

export function getSeverityConfig(severity: AlertSeverity) {
  const configs = {
    critical: {
      color: 'text-red-400',
      bgColor: 'bg-red-500/10 border-red-500/30',
      borderColor: 'border-l-red-500',
      glowColor: 'shadow-red-500/20',
      icon: 'AlertTriangle',
      pulseAnimation: true,
      autoDismiss: false,
      badgeVariant: 'destructive' as const,
    },
    warning: {
      color: 'text-amber-400',
      bgColor: 'bg-amber-500/10 border-amber-500/30',
      borderColor: 'border-l-amber-500',
      glowColor: 'shadow-amber-500/20',
      icon: 'AlertCircle',
      pulseAnimation: false,
      autoDismiss: false,
      badgeVariant: 'warning' as const,
    },
    info: {
      color: 'text-blue-400',
      bgColor: 'bg-blue-500/10 border-blue-500/30',
      borderColor: 'border-l-blue-500',
      glowColor: 'shadow-blue-500/20',
      icon: 'Info',
      pulseAnimation: false,
      autoDismiss: true,
      autoDismissDelay: 5000,
      badgeVariant: 'info' as const,
    },
  };
  return configs[severity];
}

export function getAlertTypeConfig(type: SalesAlertType) {
  const configs: Record<SalesAlertType, { icon: string; label: string; description: string }> = {
    high_value_order: {
      icon: 'DollarSign',
      label: 'High-Value Order',
      description: 'Triggered when an order exceeds your AOV threshold',
    },
    unusual_returns: {
      icon: 'RotateCcw',
      label: 'Unusual Return Pattern',
      description: 'Triggered when a product shows a spike in returns',
    },
    inventory_depletion: {
      icon: 'Package',
      label: 'Inventory Depletion',
      description: 'Triggered when stock drops below threshold',
    },
    conversion_anomaly: {
      icon: 'TrendingUp',
      label: 'Conversion Anomaly',
      description: 'Triggered when conversion rate deviates from baseline',
    },
    customer_segment_change: {
      icon: 'Users',
      label: 'Customer Segment Change',
      description: 'Triggered when VIP or returning customers become inactive',
    },
  };
  return configs[type];
}

// ─── Alert Title Generators ───

export function generateAlertTitle(type: SalesAlertType, data: AlertData): string {
  switch (type) {
    case 'high_value_order': {
      const d = data as HighValueOrderData;
      return `High-Value Order Detected: ${d.currency}${d.total_value.toLocaleString()}`;
    }
    case 'unusual_returns': {
      const d = data as UnusualReturnsData;
      return `Unusual Return Pattern: ${d.product_name}`;
    }
    case 'inventory_depletion': {
      const d = data as InventoryDepletionData;
      return `Low Stock Alert: ${d.product_name}`;
    }
    case 'conversion_anomaly': {
      const d = data as ConversionAnomalyData;
      return `Conversion ${d.direction === 'drop' ? 'Drop' : 'Spike'}: ${Math.abs(d.delta_percent).toFixed(1)}%`;
    }
    case 'customer_segment_change': {
      const d = data as CustomerSegmentChangeData;
      return d.previous_segment === 'vip' ? `VIP Customer Inactive: ${d.customer_name}` : `Customer Status Change: ${d.customer_name}`;
    }
  }
}

export function generateRichPreview(type: SalesAlertType, data: AlertData): string {
  switch (type) {
    case 'high_value_order': {
      const d = data as HighValueOrderData;
      return `Customer: ${d.customer_name} | Order: #${d.order_number} | ${d.items.length} items`;
    }
    case 'unusual_returns': {
      const d = data as UnusualReturnsData;
      return `SKU: ${d.product_sku} | ${d.return_count} returns in ${d.time_window_hours}h | Rate: ${d.return_rate_percent.toFixed(1)}%`;
    }
    case 'inventory_depletion': {
      const d = data as InventoryDepletionData;
      return `Stock: ${d.current_stock} units | Threshold: ${d.threshold_configured} units${d.days_until_stockout ? ` | ~${d.days_until_stockout} days to stockout` : ''}`;
    }
    case 'conversion_anomaly': {
      const d = data as ConversionAnomalyData;
      return `Current: ${d.current_rate.toFixed(2)}% | Baseline: ${d.baseline_rate.toFixed(2)}% | Sessions: ${d.sessions_analyzed.toLocaleString()}`;
    }
    case 'customer_segment_change': {
      const d = data as CustomerSegmentChangeData;
      return `Segment: ${d.previous_segment} → ${d.current_segment} | Last purchase: ${d.last_purchase_date ? new Date(d.last_purchase_date).toLocaleDateString() : 'Never'} | LTV: $${d.total_lifetime_value.toLocaleString()}`;
    }
  }
}

export function generateAlertActions(type: SalesAlertType, data: AlertData): AlertAction[] {
  const baseActions: AlertAction[] = [];

  switch (type) {
    case 'high_value_order': {
      const d = data as HighValueOrderData;
      baseActions.push({
        type: 'view_order',
        label: 'View Order',
        primary: true,
        target_path: `/brand-dashboard/orders/${d.order_id}`,
      });
      baseActions.push({
        type: 'view_customer',
        label: 'View Customer',
        target_path: `/brand-dashboard/customers/${d.customer_id}`,
      });
      break;
    }
    case 'unusual_returns': {
      const d = data as UnusualReturnsData;
      baseActions.push({
        type: 'view_product',
        label: 'View Product',
        primary: true,
        target_path: `/brand-dashboard/products/${d.product_id}`,
      });
      baseActions.push({
        type: 'analyze_returns',
        label: 'Analyze Returns',
        target_path: `/brand-dashboard/analytics/returns?product_id=${d.product_id}`,
      });
      break;
    }
    case 'inventory_depletion': {
      const d = data as InventoryDepletionData;
      baseActions.push({
        type: 'restock',
        label: 'Restock',
        primary: true,
        target_path: `/brand-dashboard/inventory/restock?product_id=${d.product_id}`,
      });
      baseActions.push({
        type: 'view_product',
        label: 'View Product',
        target_path: `/brand-dashboard/products/${d.product_id}`,
      });
      break;
    }
    case 'conversion_anomaly': {
      const d = data as ConversionAnomalyData;
      baseActions.push({
        type: 'view_analytics',
        label: 'View Analytics',
        primary: true,
        target_path: `/brand-dashboard/analytics/conversion`,
      });
      break;
    }
    case 'customer_segment_change': {
      const d = data as CustomerSegmentChangeData;
      baseActions.push({
        type: 'view_customer',
        label: 'View Profile',
        primary: true,
        target_path: `/brand-dashboard/customers/${d.customer_id}`,
      });
      baseActions.push({
        type: 'configure',
        label: 'Adjust Settings',
        target_path: `/brand-dashboard/settings/alerts`,
      });
      break;
    }
  }

  baseActions.push({
    type: 'dismiss',
    label: 'Dismiss',
  });

  return baseActions;
}
