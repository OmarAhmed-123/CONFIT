# CONFIT Sales Alert System

## Overview

The Sales Alert System is an intelligent, real-time notification engine for store owners that monitors business metrics and delivers contextually rich, actionable alerts. It prevents notification fatigue through intelligent throttling, deduplication, and user-configurable preferences.

## Alert Types

### 1. High-Value Order (`high_value_order`)

**Trigger:** Single order value exceeds AOV × configurable multiplier (default 1.5x)

**Severity:** Warning

**Use Case:** Alert store owners to VIP customers and high-value transactions that may require special attention.

**Data Payload:**
```typescript
{
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
```

**Actions:**
- View Order (primary)
- View Customer
- Dismiss

---

### 2. Unusual Returns Pattern (`unusual_returns`)

**Trigger:** 
- 5+ returns within 1 hour window, OR
- Return rate increases 50%+ vs baseline

**Severity:** Warning

**Use Case:** Detect potential product quality issues, sizing problems, or fraud patterns.

**Data Payload:**
```typescript
{
  product_id: string;
  product_name: string;
  product_sku: string;
  return_count: number;
  return_rate_percent: number;
  baseline_return_rate_percent: number;
  time_window_hours: number;
  affected_orders: string[];
}
```

**Actions:**
- View Product (primary)
- Analyze Returns
- Dismiss

---

### 3. Inventory Depletion (`inventory_depletion`)

**Trigger:** Stock drops below configured threshold (default 10 units)

**Severity:** Critical (if ≤5 units or ≤3 days to stockout), Warning otherwise

**Use Case:** Prevent stockouts and enable proactive restocking.

**Data Payload:**
```typescript
{
  product_id: string;
  product_name: string;
  product_sku: string;
  current_stock: number;
  reorder_point: number;
  threshold_configured: number;
  days_until_stockout: number | null;
  product_image?: string;
}
```

**Actions:**
- Restock (primary)
- View Product
- Dismiss

---

### 4. Conversion Rate Anomaly (`conversion_anomaly`)

**Trigger:** 
- Conversion rate drops ≥15% from 7-day baseline, OR
- Conversion rate rises ≥20% from baseline

**Severity:** Critical (drop), Info (rise)

**Use Case:** Identify significant changes in store performance requiring investigation.

**Data Payload:**
```typescript
{
  current_rate: number;
  baseline_rate: number;
  delta_percent: number;
  direction: 'drop' | 'rise';
  time_window: '1h' | '24h' | '7d';
  sessions_analyzed: number;
  conversions_analyzed: number;
}
```

**Actions:**
- View Analytics (primary)
- Dismiss

---

### 5. Customer Segment Change (`customer_segment_change`)

**Trigger:**
- VIP customer inactive for 30+ days
- Returning customer inactive for 60+ days

**Severity:** Critical (VIP churn), Warning (other segment changes)

**Use Case:** Identify at-risk VIP customers and enable proactive re-engagement.

**Data Payload:**
```typescript
{
  customer_id: string;
  customer_name: string;
  previous_segment: 'vip' | 'returning' | 'new' | 'inactive';
  current_segment: 'vip' | 'returning' | 'new' | 'inactive';
  last_purchase_date: string | null;
  days_since_last_purchase: number;
  total_lifetime_value: number;
  total_orders: number;
}
```

**Actions:**
- View Profile (primary)
- Adjust Settings
- Dismiss

---

## Severity Levels

| Severity | Color | Icon | Behavior |
|----------|-------|------|----------|
| **Critical** | Red/Gold | AlertTriangle (pulsing) | Real-time delivery, always shown |
| **Warning** | Amber/Gold | AlertCircle | Batched by default, high priority |
| **Info** | Blue/Gold | Info | Batched delivery, lower priority |

## Alert Status Lifecycle

```
ACTIVE → ACKNOWLEDGED → RESOLVED
   ↓
DISMISSED
```

- **Active:** New alert, unread
- **Acknowledged:** Owner has seen and acknowledged
- **Resolved:** Issue has been addressed
- **Dismissed:** Owner has dismissed the alert

---

## Configuration

### Threshold Configuration

```typescript
{
  high_value_aov_multiplier: 1.5,        // AOV multiplier for high-value orders
  inventory_threshold_units: 10,         // Stock level threshold
  inventory_threshold_percent: 20.0,     // Alternative % threshold
  conversion_drop_threshold_percent: 15.0,
  conversion_rise_threshold_percent: 20.0,
  conversion_baseline_days: 7,           // Rolling baseline period
  returns_spike_count: 5,                // Returns count threshold
  returns_spike_window_hours: 1,         // Time window for spike detection
  returns_rate_increase_percent: 50.0,   // Rate increase threshold
  vip_inactive_days: 30,                 // VIP inactivity threshold
  returning_to_inactive_days: 60         // Returning customer threshold
}
```

### Frequency Configuration

```typescript
{
  mode: 'throttled',           // 'real_time' | 'batched' | 'throttled'
  max_alerts_per_hour: 10,     // Hourly limit per store
  batch_interval_minutes: 30,  // Batch delivery interval
  dedup_window_minutes: 60,    // Deduplication window
  critical_mode: 'real_time',  // Severity-specific delivery
  warning_mode: 'batched',
  info_mode: 'batched'
}
```

### Per-Type Preferences

```typescript
{
  [alertType]: {
    enabled: boolean;
    frequency: 'real_time' | 'batched_15m' | 'batched_30m' | 'batched_1h' | 'disabled';
    channels: ('in_app' | 'email' | 'push')[];
  }
}
```

---

## Deduplication & Throttling

### Deduplication

Prevents duplicate alerts for the same event within a configurable window (default 60 minutes).

**Dedup Key Format:** `{alert_type}::{store_id}::{entity_id}`

Example: `inventory_depletion::store-123::product-456`

### Throttling

Limits alerts per store per hour (default 10) to prevent notification fatigue.

- Critical alerts bypass throttling by default
- Excess alerts are batched and delivered in summary
- Hourly limit resets at the top of each hour

---

## API Endpoints

### Alerts

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/sales-alerts` | List alerts with filters |
| `GET` | `/api/sales-alerts/unread-count` | Get unread counts by severity |
| `GET` | `/api/sales-alerts/summary` | Get alert statistics |
| `GET` | `/api/sales-alerts/{id}` | Get single alert |
| `POST` | `/api/sales-alerts/{id}/read` | Mark as read |
| `POST` | `/api/sales-alerts/read-all` | Mark all as read |
| `POST` | `/api/sales-alerts/{id}/acknowledge` | Acknowledge alert |
| `POST` | `/api/sales-alerts/{id}/resolve` | Resolve alert |
| `POST` | `/api/sales-alerts/{id}/dismiss` | Dismiss alert |
| `DELETE` | `/api/sales-alerts/{id}` | Delete alert |

### Preferences

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/sales-alerts/preferences` | Get store preferences |
| `PUT` | `/api/sales-alerts/preferences` | Update preferences |
| `POST` | `/api/sales-alerts/preferences/reset` | Reset to defaults |

### Export

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/sales-alerts/export/csv` | Export alerts to CSV |

---

## Frontend Components

### Components

- `SalesAlertCard` - Individual alert display with severity styling
- `SalesAlertToast` - Toast notification for new alerts
- `SalesAlertsPanel` - Panel with bell badge and alert list
- `SalesAlertBadge` - Standalone bell badge component
- `AlertPreferencesPanel` - Settings panel for preferences

### Hooks

- `useAlertActions` - Handle one-click actions with routing
- `useAlertKeyboardShortcuts` - Keyboard shortcuts for alert management

### Store

- `useSalesAlertStore` - Zustand store with persistence

### Pages

- `AlertHistoryPage` - Full history with search, filter, export

---

## Database Schema

### Tables

#### `sales_alerts`
Main alerts table with 30-day retention.

#### `sales_alert_preferences`
Per-store configuration.

#### `sales_alert_logs`
Immutable audit trail (30-day retention).

---

## WebSocket Integration

Sales alerts integrate with the existing WebSocket infrastructure at `/api/notifications/ws`.

**Message Format:**
```json
{
  "type": "sales_alert",
  "data": {
    "id": "alert-xxx",
    "type": "high_value_order",
    "severity": "warning",
    "title": "High-Value Order Detected: $2,500.00",
    "rich_preview": "Customer: John Doe | Order: #12345 | 3 items",
    "data": { ... },
    "actions": [ ... ]
  }
}
```

---

## Best Practices

1. **Configure thresholds** based on your store's typical performance
2. **Use batched delivery** for non-critical alerts to reduce noise
3. **Review alert history** weekly to identify patterns
4. **Adjust AOV multiplier** seasonally for high-value order detection
5. **Set VIP inactivity threshold** based on typical purchase frequency

---

## Troubleshooting

### Not receiving alerts?
1. Check preferences are enabled for the alert type
2. Verify WebSocket connection status (green indicator)
3. Check hourly throttling limit hasn't been reached

### Too many alerts?
1. Increase thresholds in preferences
2. Switch to batched delivery mode
3. Reduce max alerts per hour

### Missing critical alerts?
1. Ensure critical mode is set to "real_time"
2. Check that alert type is enabled
3. Verify deduplication window isn't too long
