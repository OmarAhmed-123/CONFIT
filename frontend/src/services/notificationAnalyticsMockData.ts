/**
 * CONFIT — Notification Analytics Mock Data
 * ============================================
 * Deterministic mock data generator for the analytics dashboard.
 * Produces realistic notification events, channel metrics, heatmap data,
 * conversion tracking, owner response times, and sample A/B tests.
 */

import type {
  NotificationEvent,
  HeatmapCell,
  ConversionDataPoint,
  OwnerResponseTime,
  CohortComparison,
  ABTest,
  ActivityFeedItem,
  AnalyticsChannel,
  AnalyticsRecipientType,
  NotificationEventType,
} from '@/types/notificationAnalyticsTypes';

// ─── Seed-based RNG ───

let _seed = 42;
function seededRandom(): number {
  _seed = (_seed * 16807 + 0) % 2147483647;
  return (_seed - 1) / 2147483646;
}

function randomInt(min: number, max: number): number {
  return Math.floor(seededRandom() * (max - min + 1)) + min;
}

function randomFloat(min: number, max: number, decimals = 2): number {
  return parseFloat((seededRandom() * (max - min) + min).toFixed(decimals));
}

function pick<T>(arr: T[]): T {
  return arr[Math.floor(seededRandom() * arr.length)];
}

// ─── Constants ───

const CHANNELS: AnalyticsChannel[] = ['in_app', 'email', 'push'];
const CHANNEL_WEIGHTS = { in_app: 0.45, email: 0.35, push: 0.20 };
const RECIPIENT_TYPES: AnalyticsRecipientType[] = ['customer', 'owner'];
const EVENT_TYPES: NotificationEventType[] = ['sent', 'delivered', 'read', 'clicked', 'dismissed'];
const NOTIF_TYPES = ['order_confirmed', 'order_placed', 'order_shipped', 'promotion', 'price_drop', 'styling_suggestion'];

const STORE_NAMES = [
  'CONFIT Cairo Flagship', 'CONFIT Alexandria', 'CONFIT Dubai Mall',
  'CONFIT Riyadh', 'CONFIT Istanbul', 'CONFIT Paris Showroom',
];

const STORE_IDS = STORE_NAMES.map((_, i) => `store-${i + 1}`);

// ─── Engagement Curve (hour of day → multiplier) ───
const HOUR_ENGAGEMENT: number[] = [
  0.1, 0.05, 0.03, 0.02, 0.03, 0.08, // 0–5
  0.25, 0.45, 0.65, 0.82, 0.95, 1.0,  // 6–11
  0.92, 0.88, 0.75, 0.68, 0.72, 0.78, // 12–17
  0.85, 0.90, 0.80, 0.60, 0.35, 0.18, // 18–23
];

// ─── Event Generator ───

function weightedChannelPick(): AnalyticsChannel {
  const r = seededRandom();
  if (r < CHANNEL_WEIGHTS.in_app) return 'in_app';
  if (r < CHANNEL_WEIGHTS.in_app + CHANNEL_WEIGHTS.email) return 'email';
  return 'push';
}

function generateEvents(daysBack: number): NotificationEvent[] {
  _seed = 42; // Reset for determinism
  const events: NotificationEvent[] = [];
  const now = Date.now();
  const baseCount = Math.round(daysBack * 20); // ~20 notifications per day

  for (let i = 0; i < baseCount; i++) {
    const dayOffset = randomInt(0, daysBack - 1);
    const hour = randomInt(0, 23);
    const minute = randomInt(0, 59);
    const timestamp = new Date(now - dayOffset * 86400000);
    timestamp.setHours(hour, minute, randomInt(0, 59), 0);

    const channel = weightedChannelPick();
    const recipientType = seededRandom() < 0.65 ? 'customer' : 'owner';
    const notifId = `notif-${i}-${dayOffset}`;
    const recipientId = recipientType === 'customer'
      ? `cust-${randomInt(1, 50)}`
      : `owner-${randomInt(1, 10)}`;

    // Lifecycle: sent → delivered → maybe read → maybe clicked/dismissed
    const deliveryChance = channel === 'in_app' ? 0.98 : channel === 'email' ? 0.92 : 0.85;
    const engagementMultiplier = HOUR_ENGAGEMENT[hour];
    const openChance = Math.min(0.95, (channel === 'in_app' ? 0.72 : channel === 'email' ? 0.28 : 0.55) * engagementMultiplier * 1.3);
    const clickChance = openChance * (channel === 'in_app' ? 0.35 : channel === 'email' ? 0.12 : 0.25);

    const storeIdx = randomInt(0, STORE_NAMES.length - 1);
    const payload = {
      notification_type: pick(NOTIF_TYPES),
      order_id: `order-${randomInt(1000, 9999)}`,
      store_id: STORE_IDS[storeIdx],
      store_name: STORE_NAMES[storeIdx],
    };

    // Sent
    events.push({
      id: `evt-${notifId}-sent`,
      notification_id: notifId,
      recipient_id: recipientId,
      recipient_type: recipientType,
      channel,
      event_type: 'sent',
      event_timestamp: timestamp.toISOString(),
      payload,
    });

    // Delivered
    if (seededRandom() < deliveryChance) {
      const deliveredTime = new Date(timestamp.getTime() + randomInt(200, 5000));
      events.push({
        id: `evt-${notifId}-delivered`,
        notification_id: notifId,
        recipient_id: recipientId,
        recipient_type: recipientType,
        channel,
        event_type: 'delivered',
        event_timestamp: deliveredTime.toISOString(),
        payload,
      });

      // Read
      if (seededRandom() < openChance) {
        const readTime = new Date(deliveredTime.getTime() + randomInt(10000, 3600000));
        const timeSpent = randomInt(2000, 45000);
        events.push({
          id: `evt-${notifId}-read`,
          notification_id: notifId,
          recipient_id: recipientId,
          recipient_type: recipientType,
          channel,
          event_type: 'read',
          event_timestamp: readTime.toISOString(),
          payload,
          engagement: {
            time_spent_ms: timeSpent,
            scroll_depth: randomFloat(0.1, 1.0),
          },
        });

        // Clicked or dismissed
        if (seededRandom() < clickChance) {
          events.push({
            id: `evt-${notifId}-clicked`,
            notification_id: notifId,
            recipient_id: recipientId,
            recipient_type: recipientType,
            channel,
            event_type: 'clicked',
            event_timestamp: new Date(readTime.getTime() + randomInt(500, 10000)).toISOString(),
            payload,
            engagement: {
              time_spent_ms: timeSpent,
              action_taken: pick(['view_order', 'view_product', 'accept_order', 'navigate']),
            },
          });
        } else if (seededRandom() < 0.4) {
          events.push({
            id: `evt-${notifId}-dismissed`,
            notification_id: notifId,
            recipient_id: recipientId,
            recipient_type: recipientType,
            channel,
            event_type: 'dismissed',
            event_timestamp: new Date(readTime.getTime() + randomInt(1000, 8000)).toISOString(),
            payload,
          });
        }
      }
    }
  }

  return events.sort((a, b) =>
    new Date(b.event_timestamp).getTime() - new Date(a.event_timestamp).getTime()
  );
}

// ─── Heatmap Generator ───

function generateHeatmapData(events: NotificationEvent[], recipientType?: AnalyticsRecipientType): HeatmapCell[] {
  const cells: HeatmapCell[] = [];

  for (let day = 0; day < 7; day++) {
    for (let hour = 0; hour < 24; hour++) {
      const filtered = events.filter((e) => {
        if (recipientType && e.recipient_type !== recipientType) return false;
        const d = new Date(e.event_timestamp);
        const eventDay = (d.getDay() + 6) % 7; // Monday = 0
        return eventDay === day && d.getHours() === hour;
      });

      const sent = filtered.filter((e) => e.event_type === 'sent').length;
      const read = filtered.filter((e) => e.event_type === 'read').length;
      const clicked = filtered.filter((e) => e.event_type === 'clicked').length;

      cells.push({
        day,
        hour,
        open_rate: sent > 0 ? parseFloat((read / sent).toFixed(3)) : 0,
        click_rate: sent > 0 ? parseFloat((clicked / sent).toFixed(3)) : 0,
        event_count: sent,
      });
    }
  }

  return cells;
}

// ─── Conversion Data ───

function generateConversionData(): ConversionDataPoint[] {
  _seed = 100;
  const data: ConversionDataPoint[] = [];
  const channels: AnalyticsChannel[] = ['in_app', 'email', 'push'];
  const periods = [7, 14, 30];

  for (const channel of channels) {
    for (const period of periods) {
      const count = randomInt(80, 300);
      const baseRate = channel === 'in_app' ? 0.18 : channel === 'email' ? 0.12 : 0.08;
      const periodMultiplier = period === 7 ? 0.7 : period === 14 ? 0.85 : 1.0;
      const rate = randomFloat(baseRate * periodMultiplier * 0.8, baseRate * periodMultiplier * 1.2, 3);

      data.push({
        channel,
        period_days: period,
        notification_count: count,
        repeat_purchases: Math.round(count * rate),
        conversion_rate: rate,
      });
    }
  }

  return data;
}

// ─── Owner Response Times ───

function generateOwnerResponseTimes(): OwnerResponseTime[] {
  _seed = 200;
  return STORE_NAMES.map((name, i) => ({
    store_id: STORE_IDS[i],
    store_name: name,
    avg_response_time_min: randomFloat(3, 45),
    median_response_time_min: randomFloat(2, 30),
    notification_count: randomInt(15, 120),
  }));
}

// ─── Cohort Comparison ───

function generateCohortData(): CohortComparison[] {
  _seed = 300;
  return ['Week 1', 'Week 2', 'Week 3', 'Week 4'].map((period) => {
    const notified = randomFloat(0.15, 0.35, 3);
    const nonNotified = randomFloat(0.05, 0.15, 3);
    return {
      period,
      notified_purchase_rate: notified,
      non_notified_purchase_rate: nonNotified,
      lift_percentage: parseFloat(((notified - nonNotified) / nonNotified * 100).toFixed(1)),
    };
  });
}

// ─── A/B Tests ───

function generateABTests(): ABTest[] {
  const now = new Date();
  return [
    {
      id: 'ab-001',
      name: 'Email vs Push for Order Confirmations',
      hypothesis: 'Push notifications will achieve higher open rates than email for order confirmations',
      variable: 'channel',
      status: 'completed',
      segment: 'all_customers',
      traffic_percentage: 50,
      start_date: new Date(now.getTime() - 21 * 86400000).toISOString(),
      end_date: new Date(now.getTime() - 7 * 86400000).toISOString(),
      duration_days: 14,
      variants: [
        {
          id: 'var-a',
          name: 'Variant A: Email + Toast',
          description: 'Standard email confirmation with in-app toast',
          config: { channels: ['email', 'in_app'] },
          sample_size: 234,
          metrics: { delivery_rate: 0.94, open_rate: 0.31, click_rate: 0.08, conversion_rate: 0.12 },
        },
        {
          id: 'var-b',
          name: 'Variant B: Push + Toast',
          description: 'Push notification with in-app toast',
          config: { channels: ['push', 'in_app'] },
          sample_size: 228,
          metrics: { delivery_rate: 0.87, open_rate: 0.58, click_rate: 0.19, conversion_rate: 0.15 },
        },
      ],
      winner_variant_id: 'var-b',
      confidence_level: 0.95,
      p_value: 0.003,
      is_significant: true,
      created_at: new Date(now.getTime() - 22 * 86400000).toISOString(),
      updated_at: new Date(now.getTime() - 7 * 86400000).toISOString(),
    },
    {
      id: 'ab-002',
      name: 'Immediate vs Delayed Owner Notifications',
      hypothesis: 'A 15-minute delay will not reduce owner response time but will batch similar notifications',
      variable: 'timing',
      status: 'running',
      segment: 'all_owners',
      traffic_percentage: 30,
      start_date: new Date(now.getTime() - 5 * 86400000).toISOString(),
      duration_days: 14,
      variants: [
        {
          id: 'var-c',
          name: 'Control: Immediate',
          description: 'Notifications sent immediately upon order',
          config: { timing_delay_minutes: 0 },
          sample_size: 67,
          metrics: { delivery_rate: 0.96, open_rate: 0.72, click_rate: 0.45, conversion_rate: 0.0 },
        },
        {
          id: 'var-d',
          name: 'Test: 15-min Batch',
          description: 'Notifications batched in 15-minute windows',
          config: { timing_delay_minutes: 15 },
          sample_size: 71,
          metrics: { delivery_rate: 0.97, open_rate: 0.68, click_rate: 0.42, conversion_rate: 0.0 },
        },
      ],
      confidence_level: 0.62,
      p_value: 0.18,
      is_significant: false,
      created_at: new Date(now.getTime() - 6 * 86400000).toISOString(),
      updated_at: now.toISOString(),
    },
    {
      id: 'ab-003',
      name: 'Short vs Detailed Notification Content',
      hypothesis: 'Concise notifications will have higher CTR than detailed ones',
      variable: 'content',
      status: 'draft',
      segment: 'repeat_customers',
      traffic_percentage: 25,
      start_date: '',
      duration_days: 7,
      variants: [
        {
          id: 'var-e',
          name: 'Short: Title Only',
          description: 'Order confirmed with order number only',
          config: { content_format: 'short' },
          sample_size: 0,
          metrics: { delivery_rate: 0, open_rate: 0, click_rate: 0, conversion_rate: 0 },
        },
        {
          id: 'var-f',
          name: 'Detailed: Full Summary',
          description: 'Full order details with item names and totals',
          config: { content_format: 'detailed' },
          sample_size: 0,
          metrics: { delivery_rate: 0, open_rate: 0, click_rate: 0, conversion_rate: 0 },
        },
      ],
      is_significant: false,
      created_at: now.toISOString(),
      updated_at: now.toISOString(),
    },
  ];
}

// ─── Activity Feed ───

function generateActivityFeed(events: NotificationEvent[], limit = 100): ActivityFeedItem[] {
  const NOTIF_TITLES: Record<string, string> = {
    order_confirmed: 'Order Confirmed',
    order_placed: 'New Order Placed',
    order_shipped: 'Order Shipped',
    promotion: 'Flash Sale Alert',
    price_drop: 'Price Drop Alert',
    styling_suggestion: 'Style Recommendation',
  };

  return events
    .slice(0, limit)
    .map((e) => ({
      id: e.id,
      event_type: e.event_type,
      channel: e.channel,
      recipient_type: e.recipient_type,
      recipient_id: e.recipient_id,
      notification_title: NOTIF_TITLES[e.payload.notification_type || ''] || 'Notification',
      timestamp: e.event_timestamp,
    }));
}

// ─── Public API ───

let _cachedEvents: NotificationEvent[] | null = null;

export function getAnalyticsEvents(daysBack = 30): NotificationEvent[] {
  if (!_cachedEvents) {
    _cachedEvents = generateEvents(daysBack);
  }
  return _cachedEvents;
}

export function getHeatmap(recipientType?: AnalyticsRecipientType): HeatmapCell[] {
  return generateHeatmapData(getAnalyticsEvents(), recipientType);
}

export function getConversionData(): ConversionDataPoint[] {
  return generateConversionData();
}

export function getOwnerResponseTimes(): OwnerResponseTime[] {
  return generateOwnerResponseTimes();
}

export function getCohortComparison(): CohortComparison[] {
  return generateCohortData();
}

export function getMockABTests(): ABTest[] {
  return generateABTests();
}

export function getActivityFeed(limit = 100): ActivityFeedItem[] {
  return generateActivityFeed(getAnalyticsEvents(), limit);
}

export function resetCache(): void {
  _cachedEvents = null;
}
