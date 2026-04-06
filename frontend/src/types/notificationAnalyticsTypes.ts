/**
 * CONFIT — Notification Analytics Types
 * =======================================
 * TypeScript types for the notification analytics & monitoring dashboard.
 * Covers event logging, channel metrics, heatmap data, conversion tracking,
 * A/B testing, and dashboard configuration.
 */

// ─── Dashboard Period ───

export type DashboardPeriod = '7d' | '14d' | '30d';

export function periodToDays(period: DashboardPeriod): number {
  switch (period) {
    case '7d': return 7;
    case '14d': return 14;
    case '30d': return 30;
  }
}

// ─── Notification Event Lifecycle ───

export type NotificationEventType =
  | 'sent'
  | 'delivered'
  | 'read'
  | 'clicked'
  | 'dismissed';

export type AnalyticsChannel = 'in_app' | 'email' | 'push' | 'toast';
export type AnalyticsRecipientType = 'customer' | 'owner';

export interface NotificationEvent {
  id: string;
  notification_id: string;
  recipient_id: string;
  recipient_type: AnalyticsRecipientType;
  channel: AnalyticsChannel;
  event_type: NotificationEventType;
  event_timestamp: string;
  payload: {
    notification_type?: string;
    order_id?: string;
    store_id?: string;
    store_name?: string;
    content_variant?: string;
  };
  // Engagement metadata
  engagement?: {
    time_spent_ms?: number;
    scroll_depth?: number;
    action_taken?: string;
  };
}

// ─── Channel Metrics ───

export interface ChannelMetrics {
  channel: AnalyticsChannel;
  total_sent: number;
  total_delivered: number;
  total_opened: number;
  total_clicked: number;
  delivery_rate: number;    // delivered / sent
  open_rate: number;        // opened / delivered
  click_through_rate: number; // clicked / opened
  avg_latency_ms: number;
}

// ─── Time Series ───

export interface DailyChannelMetrics {
  date: string;
  in_app: ChannelMetrics;
  email: ChannelMetrics;
  push: ChannelMetrics;
}

// ─── Heatmap ───

export interface HeatmapCell {
  day: number;      // 0 = Monday … 6 = Sunday
  hour: number;     // 0–23
  open_rate: number;
  click_rate: number;
  event_count: number;
}

export type HeatmapData = HeatmapCell[];

// ─── Conversion / Business Impact ───

export interface ConversionDataPoint {
  channel: AnalyticsChannel;
  period_days: number;
  notification_count: number;
  repeat_purchases: number;
  conversion_rate: number;
}

export interface OwnerResponseTime {
  store_id: string;
  store_name: string;
  avg_response_time_min: number;
  median_response_time_min: number;
  notification_count: number;
}

export interface CohortComparison {
  period: string;
  notified_purchase_rate: number;
  non_notified_purchase_rate: number;
  lift_percentage: number;
}

// ─── KPI Summary ───

export interface AnalyticsKPI {
  overall_delivery_rate: number;
  avg_open_rate: number;
  avg_click_rate: number;
  most_used_channel: AnalyticsChannel;
  most_used_channel_count: number;
  top_conversion_channel: AnalyticsChannel;
  top_conversion_rate: number;
  total_events: number;
  period_days: number;
  // Trends vs previous period
  delivery_rate_trend: number;  // positive = improving
  open_rate_trend: number;
}

// ─── A/B Testing ───

export type ABTestStatus = 'draft' | 'running' | 'paused' | 'completed' | 'archived';

export type ABTestVariable = 'timing' | 'content' | 'channel' | 'frequency';

export type ABTestSegment =
  | 'all_customers'
  | 'all_owners'
  | 'new_customers'
  | 'repeat_customers'
  | 'specific_stores';

export interface ABTestVariant {
  id: string;
  name: string;
  description: string;
  config: {
    channels?: AnalyticsChannel[];
    timing_delay_minutes?: number;
    content_format?: 'short' | 'detailed';
    frequency?: string;
  };
  // Results
  sample_size: number;
  metrics: {
    delivery_rate: number;
    open_rate: number;
    click_rate: number;
    conversion_rate: number;
  };
}

export interface ABTest {
  id: string;
  name: string;
  hypothesis: string;
  variable: ABTestVariable;
  status: ABTestStatus;
  segment: ABTestSegment;
  traffic_percentage: number;
  start_date: string;
  end_date?: string;
  duration_days: number;
  variants: ABTestVariant[];
  // Statistical results
  winner_variant_id?: string;
  confidence_level?: number;
  p_value?: number;
  is_significant: boolean;
  created_at: string;
  updated_at: string;
}

// ─── Activity Feed ───

export interface ActivityFeedItem {
  id: string;
  event_type: NotificationEventType;
  channel: AnalyticsChannel;
  recipient_type: AnalyticsRecipientType;
  recipient_id: string;
  notification_title: string;
  timestamp: string;
}

export interface ActivityFeedFilters {
  channels: AnalyticsChannel[];
  recipient_types: AnalyticsRecipientType[];
}

// ─── Daily Trend ───

export interface DailyTrend {
  date: string;
  delivery_rate: number;
  open_rate: number;
  click_rate: number;
  count: number;
}
