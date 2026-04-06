# CONFIT Analytics Events Documentation

This document lists all standard analytics events tracked by the CONFIT platform.

## Event Naming Convention

All event names use `snake_case` format for consistency.

## Event Properties

Each event has a standard set of properties plus event-specific properties documented below.

### Standard Properties

| Property | Type | Description |
|----------|------|-------------|
| `user_id` | UUID | User who triggered the event (nullable for anonymous) |
| `session_id` | String | Session identifier for funnel tracking |
| `store_id` | UUID | Store ID if store-related |
| `product_id` | UUID | Product ID if product-related |
| `timestamp` | DateTime | UTC timestamp of the event |
| `device` | String | Device type: `ios`, `android`, `web` |
| `country` | String | Country code: `EG`, `SA`, etc. |
| `properties` | JSONB | Event-specific properties |

---

## User Lifecycle Events

### `user_signup`

Triggered when a new user registers.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `signup_method` | String | Yes | `email`, `google`, `facebook`, `apple` |
| `referral_code` | String | No | Referral code if applicable |
| `campaign_id` | String | No | Marketing campaign ID |

```json
{
  "event_name": "user_signup",
  "properties": {
    "signup_method": "google",
    "referral_code": "FRIEND2024"
  }
}
```

### `user_login`

Triggered on user authentication.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `login_method` | String | Yes | `email`, `google`, `facebook`, `apple` |
| `is_first_login` | Boolean | No | True if first login after signup |

---

## Product Engagement Events

### `product_viewed`

Triggered when a user views a product detail page.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `sku` | String | Yes | Product SKU |
| `category` | String | No | Product category |
| `price_egp` | Number | No | Product price |
| `from_outfit` | Boolean | No | True if viewed from an outfit |
| `outfit_id` | String | No | Outfit ID if from outfit |

```json
{
  "event_name": "product_viewed",
  "product_id": "uuid-here",
  "properties": {
    "sku": "SKU-12345",
    "category": "tops",
    "price_egp": 599.00,
    "from_outfit": true,
    "outfit_id": "outfit-uuid"
  }
}
```

### `product_added_to_cart`

Triggered when a product is added to shopping cart.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `sku` | String | Yes | Product SKU |
| `quantity` | Number | Yes | Quantity added |
| `price_egp` | Number | Yes | Unit price |
| `from_try_on` | Boolean | No | True if added after try-on |
| `session_id` | String | No | Try-on session ID if applicable |

---

## Try-On Flow Events

### `try_on_started`

Triggered when a virtual try-on session begins.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `garment_category` | String | Yes | `tops`, `bottoms`, `dresses`, etc. |
| `garment_id` | String | Yes | Product/garment ID |
| `source` | String | No | `product_page`, `outfit`, `muse` |

### `try_on_completed`

Triggered when a try-on renders successfully.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `quality_score` | Number | No | Render quality score (0-1) |
| `processing_time_ms` | Number | No | Processing duration |
| `garment_category` | String | Yes | Category of garment |
| `garment_id` | String | Yes | Product/garment ID |

```json
{
  "event_name": "try_on_completed",
  "product_id": "uuid-here",
  "session_id": "session-uuid",
  "properties": {
    "quality_score": 0.92,
    "processing_time_ms": 3500,
    "garment_category": "tops",
    "garment_id": "product-uuid"
  }
}
```

### `try_on_added_to_bag`

Triggered when user adds product to bag directly from try-on result.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `sku` | String | Yes | Product SKU |
| `session_id` | String | Yes | Try-on session ID |
| `quality_score` | Number | No | Render quality score |

---

## Muse AI Events

### `muse_query_sent`

Triggered when user sends a query to Muse AI stylist.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `query_type` | String | Yes | `text`, `voice`, `image` |
| `occasion` | String | No | Mentioned occasion |
| `budget_range` | String | No | Mentioned budget |

### `muse_outfit_generated`

Triggered when Muse generates an outfit recommendation.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `item_count` | Number | Yes | Number of items in outfit |
| `total_price_egp` | Number | No | Total outfit price |
| `saved` | Boolean | No | True if user saved outfit |

---

## Outfit Action Events

### `outfit_saved`

Triggered when user saves an outfit to their collection.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `outfit_id` | String | Yes | Outfit identifier |
| `item_count` | Number | Yes | Number of items |
| `brand_id` | String | No | Primary brand if applicable |
| `from_muse` | Boolean | No | True if generated by Muse |

### `outfit_shared`

Triggered when user shares an outfit.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `outfit_id` | String | Yes | Outfit identifier |
| `platform` | String | Yes | `instagram`, `whatsapp`, `copy_link`, etc. |

---

## Checkout & Payment Events

### `checkout_started`

Triggered when user initiates checkout.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `cart_value_egp` | Number | Yes | Total cart value |
| `item_count` | Number | Yes | Number of items |
| `has_try_on_items` | Boolean | No | True if cart has try-on items |

### `payment_succeeded`

Triggered on successful payment.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `order_id` | String | Yes | Order identifier |
| `payment_method` | String | Yes | `card`, `paymob`, `paypal`, `cod` |
| `total_egp` | Number | Yes | Total amount paid |
| `discount_egp` | Number | No | Discount applied |

### `payment_failed`

Triggered on failed payment attempt.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `order_id` | String | Yes | Order identifier |
| `payment_method` | String | Yes | Payment method attempted |
| `error_code` | String | No | Error code from provider |
| `error_reason` | String | No | Human-readable error |

---

## Order Events

### `order_placed`

Triggered when an order is successfully placed.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `order_id` | String | Yes | Order identifier |
| `total_egp` | Number | Yes | Order total |
| `delivery_method` | String | Yes | `shipping`, `bopis` |
| `store_id` | String | No | Store ID for BOPIS |
| `from_outfit` | Boolean | No | True if ordered from outfit |
| `from_try_on` | Boolean | No | True if ordered after try-on |
| `brand_id` | String | No | Brand ID if single-brand order |

```json
{
  "event_name": "order_placed",
  "user_id": "user-uuid",
  "store_id": "store-uuid",
  "properties": {
    "order_id": "ORD-12345",
    "total_egp": 1250.00,
    "delivery_method": "bopis",
    "from_try_on": true,
    "session_id": "tryon-session-uuid"
  }
}
```

### `order_delivered`

Triggered when order is delivered/picked up.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `order_id` | String | Yes | Order identifier |
| `delivery_method` | String | Yes | `shipping`, `bopis` |
| `pickup_time_minutes` | Number | No | Time from order to pickup (BOPIS) |

### `order_returned`

Triggered when an order is returned.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `order_id` | String | Yes | Order identifier |
| `return_reason` | String | Yes | Reason for return |
| `return_reason_code` | String | No | Categorized reason code |
| `refund_amount_egp` | Number | Yes | Refund amount |

---

## Quality Control Events

### `midway_rejection`

Triggered when a product is rejected during quality control (factory/brand dashboard).

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `sku` | String | Yes | Product SKU |
| `stage` | String | Yes | `fabric`, `stitch`, `final` |
| `reason_code` | String | Yes | Rejection reason code |
| `brand_id` | String | Yes | Brand ID |
| `batch_id` | String | No | Production batch ID |

```json
{
  "event_name": "midway_rejection",
  "properties": {
    "sku": "SKU-12345",
    "stage": "stitch",
    "reason_code": "stitch_loose_seam",
    "brand_id": "brand-luxelayers",
    "batch_id": "BATCH-2024-001"
  }
}
```

---

## Coupon Events

### `coupon_applied`

Triggered when a coupon is applied to cart.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `coupon_code` | String | Yes | Coupon code |
| `discount_egp` | Number | Yes | Discount amount |
| `coupon_type` | String | No | `percentage`, `fixed`, `donor` |
| `donor_id` | String | No | Donor ID if donor coupon |

### `coupon_redeemed`

Triggered when coupon is redeemed at checkout.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `coupon_code` | String | Yes | Coupon code |
| `discount_egp` | Number | Yes | Actual discount applied |
| `order_id` | String | Yes | Order ID |

---

## Store Visit Events

### `store_visited`

Triggered when user visits a physical store (BOPIS check-in or app location ping).

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `visit_type` | String | Yes | `bopis_checkin`, `app_ping` |
| `order_id` | String | No | Order ID for BOPIS pickup |
| `hour` | Number | No | Hour of day (0-23) |
| `day_of_week` | Number | No | Day of week (0=Monday) |

```json
{
  "event_name": "store_visited",
  "user_id": "user-uuid",
  "store_id": "store-uuid",
  "properties": {
    "visit_type": "bopis_checkin",
    "order_id": "ORD-12345",
    "hour": 14,
    "day_of_week": 4
  }
}
```

---

## Donor System Events

### `donor_coupon_created`

Triggered when a donor creates a coupon for a beneficiary.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `donor_id` | String | Yes | Donor user ID |
| `beneficiary_id` | String | Yes | Beneficiary ID |
| `amount_egp` | Number | Yes | Coupon value |
| `campaign_id` | String | No | Campaign ID |

### `donor_coupon_redeemed`

Triggered when a donor-funded coupon is redeemed.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `donor_id` | String | Yes | Donor user ID |
| `beneficiary_id` | String | Yes | Beneficiary ID |
| `amount_egp` | Number | Yes | Amount redeemed |
| `store_id` | String | Yes | Store where redeemed |
| `order_id` | String | Yes | Order ID |

---

## Feedback Events

### `nps_response`

Triggered when user responds to NPS survey.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `score` | Number | Yes | NPS score (0-10) |
| `feedback` | String | No | Optional feedback text |

### `csat_response`

Triggered when user responds to CSAT survey.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `score` | Number | Yes | CSAT score (1-5) |
| `touchpoint` | String | Yes | `try_on`, `checkout`, `delivery`, `support` |

---

## Fraud & Security Events

### `fraud_flagged`

Triggered when suspicious activity is detected.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `flag_type` | String | Yes | Type of fraud flag |
| `severity` | String | Yes | `low`, `medium`, `high` |
| `order_id` | String | No | Associated order if applicable |
| `details` | Object | No | Additional details |

---

## Redis Real-Time Counters

The following Redis keys are used for real-time dashboards:

| Key Pattern | Description | TTL |
|-------------|-------------|-----|
| `analytics:events:{date}` | Global event counts by type | 36h |
| `analytics:store:{store_id}:{date}` | Store-specific event counts | 36h |
| `analytics:store:{store_id}:visits:today` | Store visits today | 36h |
| `analytics:dau:{date}` | Daily active users set | 36h |
| `analytics:brand:{brand_id}:{date}` | Brand-specific event counts | 36h |
| `analytics:heatmap:{store_id}:{date}` | Hour×day visitor heatmap | 7 days |

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ANALYTICS_FORWARD_ENABLED` | Enable Mixpanel forwarding | `false` |
| `MIXPANEL_TOKEN` | Mixpanel project token | - |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |

---

## PII Minimization

When forwarding events to external services (Mixpanel, PostHog):

- `user_id` is hashed using SHA-256 before sending
- `email`, `phone`, `name`, `address` are never forwarded
- Only non-PII properties are included

---

## Timestamps

- All timestamps are stored in UTC
- Display timestamps in `Africa/Cairo` timezone (UTC+2)
- Use `timestamp AT TIME ZONE 'Africa/Cairo'` in SQL queries for display

---

## Nightly Aggregation

The nightly aggregation worker runs at 2am Cairo time (midnight UTC) and:

1. Aggregates raw events into `daily_store_summary`
2. Aggregates raw events into `daily_brand_summary`
3. Aggregates raw events into `daily_user_summary`
4. Archives events older than 180 days to cold storage (S3)

---

## API Endpoints

### Store Analytics
- `GET /api/v1/analytics/stores/{store_id}/dashboard` - Store dashboard
- `GET /api/v1/analytics/stores/{store_id}/heatmap` - Visitor heatmap

### Brand Analytics
- `GET /api/v1/analytics/brands/{brand_id}/dashboard` - Brand dashboard
- `GET /api/v1/analytics/brands/{brand_id}/rejections` - Quality control
- `GET /api/v1/analytics/brands/{brand_id}/regional-sales` - Regional breakdown

### User Analytics
- `GET /api/v1/analytics/me/summary` - Personal summary
- `GET /api/v1/analytics/me/activity` - Activity timeline
- `GET /api/v1/analytics/me/wardrobe-stats` - Sustainability metrics

### Admin Analytics
- `GET /api/v1/analytics/admin/overview` - Platform overview
- `GET /api/v1/analytics/admin/metrics` - Event metrics
- `GET /api/v1/analytics/admin/revenue` - Revenue analytics
- `GET /api/v1/analytics/admin/funnel` - Conversion funnel
- `GET /api/v1/analytics/admin/geographic` - Geographic distribution
