# CONFIT Database Schema ERD Explanation

## Overview

This document provides a comprehensive explanation of the CONFIT production-grade PostgreSQL schema, including entity relationships, design decisions, and optimization strategies.

---

## Schema Architecture

### Design Principles

1. **Full Normalization (3NF)**: All tables are normalized to eliminate redundancy while maintaining query performance through strategic denormalization of statistics.

2. **UUID Primary Keys**: All primary keys use UUID v4 for global uniqueness, enabling distributed systems and microservices architecture.

3. **Soft Deletes**: Critical entities support soft deletes via `deleted_at` timestamp and `is_active` flag for data recovery and audit trails.

4. **Versioning**: Key entities include a `version` column for optimistic locking and change tracking.

5. **Timestamp Tracking**: All tables have `created_at` and `updated_at` with automatic trigger updates.

---

## Module Breakdown

### 1. Core User Module

```
┌─────────────────────────────────────────────────────────────────┐
│                         users                                    │
│  ─────────────────────────────────────────────────────────────  │
│  PK: id (UUID)                                                   │
│  UK: email                                                       │
│  Columns: name, phone, avatar_url, country_code, timezone,      │
│           language, currency, settings (JSONB), deleted_at      │
└─────────────────────────────────────────────────────────────────┘
         │
         │ 1:N
         ├─────────────────┬─────────────────┬─────────────────┐
         │                 │                 │                 │
         ▼                 ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ user_roles   │  │ user_sessions│  │user_addresses│  │ user_events  │
│──────────────│  │──────────────│  │──────────────│  │──────────────│
│FK: user_id   │  │FK: user_id   │  │FK: user_id   │  │FK: user_id   │
│role (enum)   │  │refresh_token │  │address_line1 │  │event_type    │
│granted_by    │  │device_type   │  │city, country │  │entity_type   │
│expires_at    │  │expires_at    │  │is_default    │  │event_data    │
└──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
```

**Key Relationships:**
- `users` → `user_roles`: 1:N (A user can have multiple roles)
- `users` → `user_sessions`: 1:N (Multiple active sessions per user)
- `users` → `user_addresses`: 1:N (Multiple shipping/billing addresses)
- `users` → `user_events`: 1:N (Behavioral analytics, partitioned by month)

**Indexes:**
- `idx_users_email` - Fast email lookups for authentication
- `idx_users_phone` - Phone-based authentication (partial, non-null)
- `idx_users_country` - Geographic analytics
- `idx_users_active` - Active user queries (partial index)

---

### 2. User Style Profiles Module

```
┌─────────────────────────────────────────────────────────────────┐
│                   user_style_profiles                            │
│  ─────────────────────────────────────────────────────────────  │
│  PK: id (UUID)                                                   │
│  FK: user_id (UK) → users.id                                     │
│  Columns: primary_archetype, style_classic..romantic (8 dims),  │
│           preferred_colors, avoided_colors, skin_undertone,     │
│           pattern_preferences, silhouette_preferences           │
└─────────────────────────────────────────────────────────────────┘
         │
         │ 1:1
         ├─────────────────┬─────────────────┬─────────────────┐
         │                 │                 │                 │
         ▼                 ▼                 ▼                 ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐ ┌───────────────────────┐
│user_body_profiles│ │user_budget_profiles│ │user_brand_affinities│ │user_contextual_prefs│
│──────────────────│ │──────────────────│ │──────────────────│ │───────────────────────│
│FK: user_id (UK)  │ │FK: user_id (UK)  │ │FK: user_id       │ │FK: user_id (UK)       │
│height_cm         │ │per_item_min/max  │ │FK: brand_id      │ │occasion_weights       │
│body_shape        │ │monthly_max       │ │affinity_score    │ │work_environment       │
│size_tops/bottoms │ │price_sensitivity │ │affinity_source   │ │climate_zone           │
│fit_issues        │ │                  │ │                  │ │cultural_influences    │
└──────────────────┘ └──────────────────┘ └──────────────────┘ └───────────────────────┘
```

**Style Vector Dimensions (0.0-1.0 scale):**
1. `style_classic` vs `style_trendy`
2. `style_minimalist` vs `style_maximalist`
3. `style_feminine` vs `style_masculine`
4. `style_edgy` vs `style_romantic`

**Key Design Decisions:**
- 1:1 relationships for body/budget profiles (unique constraint on user_id)
- 1:N for brand affinities (user can have multiple brand preferences)
- JSONB columns for flexible preference storage without schema changes

---

### 3. Brand Module

```
┌─────────────────────────────────────────────────────────────────┐
│                          brands                                  │
│  ─────────────────────────────────────────────────────────────  │
│  PK: id (VARCHAR(64) - slug-based)                               │
│  UK: slug                                                        │
│  Columns: name, description, logo_url, website, industry,       │
│           is_verified, is_featured, product_count,              │
│           follower_count, rating_average, commission_rate       │
└─────────────────────────────────────────────────────────────────┘
         │
         │ 1:N
         ├─────────────────┬─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│  brand_managers  │ │  brand_followers │ │     stores       │
│──────────────────│ │──────────────────│ │──────────────────│
│FK: brand_id      │ │FK: brand_id      │ │FK: brand_id      │
│FK: user_id       │ │FK: user_id       │ │name, address     │
│role              │ │notification_enbl │ │location (GEO)    │
│permissions       │ │                  │ │hours, services   │
└──────────────────┘ └──────────────────┘ └──────────────────┘
```

**Key Features:**
- Slug-based brand IDs for SEO-friendly URLs
- Denormalized statistics (`product_count`, `follower_count`) for performance
- PostGIS `location` column for geospatial store queries
- Trigram index on brand name for fuzzy search

---

### 4. Product Module

```
┌─────────────────────────────────────────────────────────────────┐
│                      product_categories                          │
│  ─────────────────────────────────────────────────────────────  │
│  PK: id (UUID)                                                   │
│  FK: parent_id → product_categories.id (self-referential)       │
│  Columns: name, slug, level, path (materialized path)           │
└─────────────────────────────────────────────────────────────────┘
         │
         │ 1:N
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                        products                                  │
│  ─────────────────────────────────────────────────────────────  │
│  PK: id (UUID)                                                   │
│  FK: brand_id → brands.id                                        │
│  FK: category_id → product_categories.id                         │
│  UK: sku, slug                                                   │
│  Columns: name, description, base_price, sale_price, status,    │
│           color, material, style_tags (JSONB),                  │
│           view_count, purchase_count, rating_average            │
└─────────────────────────────────────────────────────────────────┘
         │
         │ 1:N
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    product_variants                              │
│  ─────────────────────────────────────────────────────────────  │
│  PK: id (UUID)                                                   │
│  FK: product_id → products.id                                    │
│  UK: (product_id, size, color)                                   │
│  Columns: size, color, price_adjustment, inventory_quantity,    │
│           reserved_quantity, sold_count                          │
└─────────────────────────────────────────────────────────────────┘
         │
         │ 1:N
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    inventory_items                               │
│  ─────────────────────────────────────────────────────────────  │
│  PK: id (UUID)                                                   │
│  FK: variant_id → product_variants.id                            │
│  FK: store_id → stores.id (NULL = warehouse)                     │
│  UK: (variant_id, store_id)                                      │
│  Columns: quantity, reserved_quantity, status,                   │
│           low_stock_threshold, unit_cost                         │
└─────────────────────────────────────────────────────────────────┘
```

**Category Hierarchy:**
- Uses materialized path pattern (`/parent/child/grandchild`)
- `level` column for depth tracking
- Self-referential `parent_id` for tree traversal

**Product Variant Design:**
- Each variant represents a unique size/color combination
- Inventory tracked per variant per store location
- `available_quantity` as generated column (`quantity - reserved_quantity`)

---

### 5. Orders & Payments Module

```
┌─────────────────────────────────────────────────────────────────┐
│                         orders                                   │
│  ─────────────────────────────────────────────────────────────  │
│  PK: id (VARCHAR(64))                                            │
│  UK: order_number                                                │
│  FK: user_id → users.id                                          │
│  FK: store_id → stores.id (for BOPIS)                            │
│  Columns: status (enum), shipping_address (JSONB),               │
│           billing_address (JSONB), subtotal, total, currency,   │
│           tracking_number, placed_at, delivered_at              │
└─────────────────────────────────────────────────────────────────┘
         │
         │ 1:N
         ├─────────────────┬─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│   order_items    │ │    payments      │ │return_requests   │
│──────────────────│ │──────────────────│ │──────────────────│
│FK: order_id      │ │FK: order_id      │ │FK: order_id      │
│FK: product_id    │ │FK: user_id       │ │FK: user_id       │
│FK: variant_id    │ │amount, currency  │ │reason, status    │
│quantity, total   │ │status (enum)     │ │refund_amount     │
│fulfillment_status│ │provider, token   │ │tracking_number   │
└──────────────────┘ └──────────────────┘ └──────────────────┘
         │
         │ 1:N
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    payment_events                                │
│  ─────────────────────────────────────────────────────────────  │
│  FK: payment_id → payments.id                                    │
│  Columns: event_type, old_status, new_status,                    │
│           provider_event_data (JSONB), error_code                │
└─────────────────────────────────────────────────────────────────┘
```

**Payment Security (PCI-DSS Compliance):**
- No raw card data stored; only provider tokens
- `provider_token` references Stripe/PayPal vault
- `last_four`, `card_brand` are safe display values
- `fingerprint` for fraud detection without storing PAN

**Order Status Flow:**
```
pending → confirmed → processing → shipped → delivered
    ↓         ↓           ↓          ↓
cancelled  cancelled  cancelled  returned/refunded
```

---

### 6. BNPL (Buy Now Pay Later) Module

```
┌─────────────────────────────────────────────────────────────────┐
│                    bnpl_applications                             │
│  ─────────────────────────────────────────────────────────────  │
│  PK: id (UUID)                                                   │
│  FK: user_id → users.id                                          │
│  FK: order_id → orders.id                                        │
│  Columns: provider, principal_amount, interest_amount,          │
│           term_months, monthly_payment, apr, status,            │
│           provider_application_id, credit_check_consent          │
└─────────────────────────────────────────────────────────────────┘
         │
         │ 1:N
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  bnpl_payment_schedule                           │
│  ─────────────────────────────────────────────────────────────  │
│  PK: id (UUID)                                                   │
│  FK: application_id → bnpl_applications.id                       │
│  UK: (application_id, installment_number)                        │
│  Columns: installment_number, amount_due, amount_paid,          │
│           due_date, status, late_fee                             │
└─────────────────────────────────────────────────────────────────┘
```

**Supported BNPL Providers:**
- Affirm
- Klarna
- Afterpay

---

### 7. Wardrobe & Outfits Module

```
┌─────────────────────────────────────────────────────────────────┐
│                     wardrobe_items                               │
│  ─────────────────────────────────────────────────────────────  │
│  PK: id (VARCHAR(64))                                            │
│  FK: user_id → users.id                                          │
│  FK: source_product_id → products.id                             │
│  Columns: name, category, color, size, brand,                   │
│           purchase_price, image_url, wear_count,                 │
│           last_worn_at, seasons (JSONB), tags (JSONB)            │
└─────────────────────────────────────────────────────────────────┘
         │
         │ M:N (via wardrobe_collection_items)
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  wardrobe_collections                            │
│  ─────────────────────────────────────────────────────────────  │
│  PK: id (UUID)                                                   │
│  FK: user_id → users.id                                          │
│  Columns: name, description, cover_image_url, is_public,        │
│           item_count                                             │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        outfits                                   │
│  ─────────────────────────────────────────────────────────────  │
│  PK: id (VARCHAR(64))                                            │
│  FK: user_id → users.id                                          │
│  Columns: title, item_ids (JSONB), occasion, season,            │
│           style_score, color_harmony_score, is_public,          │
│           share_slug, view_count, like_count                    │
└─────────────────────────────────────────────────────────────────┘
         │
         │ 1:N
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    outfit_history                                │
│  ─────────────────────────────────────────────────────────────  │
│  FK: outfit_id → outfits.id                                      │
│  Columns: worn_at, occasion, weather, temperature_c,            │
│           user_rating, feedback_notes                            │
└─────────────────────────────────────────────────────────────────┘
```

**Wardrobe Analytics Integration:**
- `wear_count` tracks usage frequency
- `seasons` array for seasonal rotation
- `outfit_history` captures context (weather, occasion) for ML training

---

### 8. Try-On Assets Module

```
┌─────────────────────────────────────────────────────────────────┐
│                     digital_twins                                │
│  ─────────────────────────────────────────────────────────────  │
│  PK: id (UUID)                                                   │
│  FK: user_id → users.id                                          │
│  Columns: reference_images (JSONB), twin_image_url,             │
│           body_model_url, skin_undertone, status,               │
│           quality_score, realism_score                           │
└─────────────────────────────────────────────────────────────────┘
         │
         │ 1:N
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    tryon_sessions                                │
│  ─────────────────────────────────────────────────────────────  │
│  PK: id (UUID)                                                   │
│  FK: user_id → users.id                                          │
│  FK: twin_id → digital_twins.id                                  │
│  FK: garment_product_id → products.id                            │
│  Columns: garment_image_url, result_image_url,                  │
│           quality_score, realism_score, edge_quality,            │
│           processing_time_ms, status, expires_at                 │
└─────────────────────────────────────────────────────────────────┘
         │
         │ 1:N
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                     tryon_results                                │
│  ─────────────────────────────────────────────────────────────  │
│  FK: session_id → tryon_sessions.id                              │
│  Columns: result_image_url, view_count, share_count,            │
│           is_saved, is_public, expires_at                        │
└─────────────────────────────────────────────────────────────────┘
```

**Quality Metrics:**
- `quality_score`: Overall try-on quality (0-100)
- `realism_score`: How realistic the result appears
- `edge_quality`: Seam and edge detection quality
- `color_consistency`: Color matching accuracy
- `proportion_score`: Body proportion accuracy

---

### 9. Visual Search Module

```
┌─────────────────────────────────────────────────────────────────┐
│                 visual_search_sessions                           │
│  ─────────────────────────────────────────────────────────────  │
│  PK: id (UUID)                                                   │
│  FK: user_id → users.id                                          │
│  Columns: input_image_url, detected_categories (JSONB),         │
│           detected_colors (JSONB), detected_patterns (JSONB),   │
│           status, processing_time_ms                             │
└─────────────────────────────────────────────────────────────────┘
         │
         │ 1:N
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  visual_search_results                           │
│  ─────────────────────────────────────────────────────────────  │
│  FK: session_id → visual_search_sessions.id                      │
│  FK: product_id → products.id                                    │
│  Columns: similarity_score, match_type, matched_attributes,     │
│           rank_position, clicked, clicked_at                     │
└─────────────────────────────────────────────────────────────────┘
```

**Detection Types:**
- Categories: "tops", "dresses", "pants", etc.
- Colors: Primary and secondary colors detected
- Patterns: "solid", "striped", "floral", "plaid"
- Styles: "minimalist", "bohemian", "classic"

---

### 10. Analytics & Recommendations Module

```
┌─────────────────────────────────────────────────────────────────┐
│                      user_events                                 │
│  ─────────────────────────────────────────────────────────────  │
│  PK: id (UUID)                                                   │
│  FK: user_id → users.id                                          │
│  Columns: event_type (enum), entity_type, entity_id,            │
│           event_data (JSONB), device_type, platform,            │
│           country_code, utm_source, utm_campaign                │
│  PARTITION BY RANGE (created_at)                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                recommendation_history                            │
│  ─────────────────────────────────────────────────────────────  │
│  PK: id (UUID)                                                   │
│  FK: user_id → users.id                                          │
│  Columns: recommendation_type (enum), entity_type,              │
│           entity_ids (JSONB), scores (JSONB), confidence,       │
│           context_snapshot (JSONB), user_feedback,              │
│           feedback_reason                                        │
└─────────────────────────────────────────────────────────────────┘
```

**Event Types:**
- `view`, `click`, `add_to_cart`, `remove_from_cart`
- `purchase`, `wishlist_add`, `wishlist_remove`
- `try_on`, `search`, `share`, `review`
- `return`, `refund`

**Recommendation Types:**
- `personalized`: Based on user style profile
- `trending`: Popular items platform-wide
- `similar`: Visually similar products
- `complementary`: Items that go well together
- `occasion`: Event-appropriate suggestions
- `seasonal`: Weather/season-based
- `price_drop`: Price reduction alerts

---

## Performance Optimizations

### Indexing Strategy

| Table | Index Type | Purpose |
|-------|------------|---------|
| `users` | B-tree | Email, phone lookups |
| `products` | GIN + trigram | Fuzzy name search |
| `products` | GIN | JSONB array queries (style_tags, occasion_tags) |
| `stores` | GiST | Geospatial location queries |
| `brands` | GIN + trigram | Fuzzy brand name search |
| `user_events` | B-tree | Time-series queries |
| `inventory_items` | Partial | Low stock alerts |

### Partitioning Strategy

**Tables partitioned by `created_at` (monthly):**
1. `user_events` - High-volume behavioral analytics
2. `audit_log` - Compliance audit trail

**Partition Management:**
- Automatic partition creation via cron job
- Retention policy: 24 months hot, archive to cold storage
- Partition pruning for time-range queries

### Denormalization Points

Strategic denormalization for read performance:

| Entity | Denormalized Fields | Source |
|--------|---------------------|--------|
| `brands` | `product_count`, `follower_count`, `rating_average` | Aggregated |
| `products` | `view_count`, `purchase_count`, `wishlist_count` | Aggregated |
| `product_variants` | `inventory_quantity`, `reserved_quantity` | From inventory_items |
| `orders` | `shipping_address`, `billing_address` | Snapshot from user_addresses |

---

## Security & Compliance

### Row-Level Security (RLS) Policies

```sql
-- User data isolation
CREATE POLICY "Users can read own data" ON users FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can update own data" ON users FOR UPDATE USING (auth.uid() = id);

-- Wardrobe isolation
CREATE POLICY "Users can manage own wardrobe" ON wardrobe_items FOR ALL USING (auth.uid() = user_id);

-- Payment method isolation
CREATE POLICY "Users can manage own payment methods" ON payment_methods FOR ALL USING (auth.uid() = user_id);

-- Public read access
CREATE POLICY "Anyone can read active products" ON products FOR SELECT USING (is_active = TRUE);
CREATE POLICY "Anyone can read active brands" ON brands FOR SELECT USING (is_active = TRUE);
```

### Payment Security (PCI-DSS)

1. **Tokenization**: No card numbers stored; only provider tokens
2. **Encryption**: All sensitive fields encrypted at rest
3. **Audit Trail**: `payment_events` tracks all state changes
4. **Fraud Detection**: `fraud_score`, `risk_level`, `device_fingerprint`

### Data Privacy (GDPR/CCPA)

1. **Soft Deletes**: `deleted_at` enables recovery before purge
2. **Data Export**: `user_data_export_requests` table for compliance
3. **Deletion Requests**: `user_deletion_requests` with 30-day window
4. **Consent Tracking**: `user_consent_history` for consent management

---

## Read Replica Strategy

### Architecture

```
                    ┌─────────────────┐
                    │   Application   │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │ Primary  │  │ Replica 1│  │ Replica 2│
        │ (Write)  │──│ (Read)   │──│ (Read)   │
        └──────────┘  └──────────┘  └──────────┘
              │              │              │
              └──────────────┴──────────────┘
                    Streaming Replication
```

### Read Routing Rules

| Query Type | Target | Reason |
|------------|--------|--------|
| User authentication | Primary | Consistency critical |
| Order creation | Primary | Write operation |
| Product catalog | Replica | High read volume |
| Search queries | Replica | Analytics workload |
| Wardrobe reads | Replica | User-facing latency |
| Analytics dashboards | Replica | Aggregation queries |

### Connection Pool Configuration

```python
# Primary pool (writes)
PRIMARY_POOL = {
    "min_connections": 5,
    "max_connections": 20,
    "max_idle": 10,
}

# Replica pool (reads)
REPLICA_POOL = {
    "min_connections": 10,
    "max_connections": 50,
    "max_idle": 20,
}
```

---

## Migration Strategy

### Version Control

All migrations are timestamped and idempotent:
- `20260306_production_schema.sql` - Initial production schema
- Future migrations follow `YYYYMMDD_description.sql` format

### Rollback Support

```sql
-- Each migration includes rollback section
-- Example: Drop table if exists
DROP TABLE IF EXISTS public.users CASCADE;

-- Restore from backup for critical changes
```

---

## Summary Statistics

| Metric | Value |
|--------|-------|
| Total Tables | 45 |
| Partitioned Tables | 2 |
| Enumerated Types | 11 |
| JSONB Columns | 35+ |
| Indexes | 80+ |
| Foreign Key Relationships | 60+ |
| Row-Level Security Policies | 25+ |

---

## Entity Relationship Diagram (Simplified)

```
┌─────────┐     ┌─────────────┐     ┌──────────────┐
│  users  │────▶│style_profiles│     │    brands    │
└────┬────┘     └─────────────┘     └──────┬───────┘
     │                                      │
     │         ┌──────────────┐             │
     └────────▶│ wardrobe_items│◀────────────┤
     │         └──────────────┘             │
     │                │                     │
     │                ▼                     │
     │         ┌──────────────┐             │
     │         │   outfits    │             │
     │         └──────────────┘             │
     │                                      │
     │         ┌──────────────┐             │
     └────────▶│    orders    │◀────────────┘
               └──────┬───────┘
                      │
                      ▼
               ┌──────────────┐
               │   payments   │
               └──────────────┘
                      │
                      ▼
               ┌──────────────┐
               │  tryon_sessions│
               └──────────────┘
```

---

This schema provides a solid foundation for CONFIT's global fashion commerce platform with room for future expansion and optimization.
