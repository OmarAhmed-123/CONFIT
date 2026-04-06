-- ============================================================
-- CONFIT — Performance Indexes Migration
-- Created: 2026-03-07
-- Description: Optimized indexes for Lighthouse 95+ performance
-- ============================================================

-- ── PRODUCTS OPTIMIZATION ─────────────────────────────────────────

-- Composite index for product listing queries (category + brand + price)
CREATE INDEX IF NOT EXISTS idx_products_listing 
ON public.products(category_id, brand_id, price_cents DESC) 
WHERE deleted_at IS NULL AND is_active = true;

-- Full-text search index for products
CREATE INDEX IF NOT EXISTS idx_products_search 
ON public.products USING gin(to_tsvector('english', coalesce(name, '') || ' ' || coalesce(description, '')));

-- Covering index for product cards (reduces table lookups)
CREATE INDEX IF NOT EXISTS idx_products_card 
ON public.products(id, name, price_cents, category_id, brand_id, thumbnail_url)
WHERE deleted_at IS NULL AND is_active = true;

-- Brand relationship optimization
CREATE INDEX IF NOT EXISTS idx_products_brand_active 
ON public.products(brand_id) 
WHERE is_active = true AND deleted_at IS NULL;

-- Category relationship optimization
CREATE INDEX IF NOT EXISTS idx_products_category_active 
ON public.products(category_id) 
WHERE is_active = true AND deleted_at IS NULL;

-- Slug lookup for SEO-friendly URLs
CREATE UNIQUE INDEX IF NOT EXISTS idx_products_slug 
ON public.products(slug) 
WHERE deleted_at IS NULL;

-- ── USERS OPTIMIZATION ────────────────────────────────────────────

-- Email lookup (unique, fast auth)
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email 
ON public.users(email);

-- Active users for queries
CREATE INDEX IF NOT EXISTS idx_users_active 
ON public.users(id, created_at DESC) 
WHERE deleted_at IS NULL;

-- Style profile lookup
CREATE INDEX IF NOT EXISTS idx_users_style_profile 
ON public.users(id) 
INCLUDE (style_preferences, body_type, skin_tone);

-- ── ORDERS OPTIMIZATION ───────────────────────────────────────────

-- User orders list (most recent first)
CREATE INDEX IF NOT EXISTS idx_orders_user_recent 
ON public.orders(user_id, created_at DESC) 
WHERE deleted_at IS NULL;

-- Order status filtering
CREATE INDEX IF NOT EXISTS idx_orders_status 
ON public.orders(status, created_at DESC) 
WHERE deleted_at IS NULL;

-- Order lookup by order number
CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_number 
ON public.orders(order_number);

-- Order items optimization
CREATE INDEX IF NOT EXISTS idx_order_items_order 
ON public.order_items(order_id) 
INCLUDE (product_id, quantity, price_cents);

-- ── WARDROBE OPTIMIZATION ─────────────────────────────────────────

-- User wardrobe items
CREATE INDEX IF NOT EXISTS idx_wardrobe_user 
ON public.wardrobe_items(user_id, created_at DESC) 
WHERE deleted_at IS NULL;

-- Category filtering in wardrobe
CREATE INDEX IF NOT EXISTS idx_wardrobe_category 
ON public.wardrobe_items(user_id, category_id) 
WHERE deleted_at IS NULL;

-- ── OUTFITS OPTIMIZATION ──────────────────────────────────────────

-- User outfits list
CREATE INDEX IF NOT EXISTS idx_outfits_user_recent 
ON public.outfits(user_id, created_at DESC) 
WHERE deleted_at IS NULL;

-- Public outfits for discovery
CREATE INDEX IF NOT EXISTS idx_outfits_public 
ON public.outfits(created_at DESC) 
WHERE is_public = true AND deleted_at IS NULL;

-- ── BRANDS OPTIMIZATION ────────────────────────────────────────────

-- Active brands list
CREATE INDEX IF NOT EXISTS idx_brands_active 
ON public.brands(name, created_at) 
WHERE is_active = true;

-- Brand slug for SEO URLs
CREATE UNIQUE INDEX IF NOT EXISTS idx_brands_slug 
ON public.brands(slug);

-- ── REVIEWS OPTIMIZATION ──────────────────────────────────────────

-- Product reviews aggregation
CREATE INDEX IF NOT EXISTS idx_reviews_product 
ON public.reviews(product_id, created_at DESC) 
WHERE deleted_at IS NULL;

-- User reviews list
CREATE INDEX IF NOT EXISTS idx_reviews_user 
ON public.reviews(user_id, created_at DESC) 
WHERE deleted_at IS NULL;

-- ── SEARCH & ANALYTICS ────────────────────────────────────────────

-- Search history for personalization
CREATE INDEX IF NOT EXISTS idx_search_history_user 
ON public.search_history(user_id, created_at DESC);

-- Popular searches
CREATE INDEX IF NOT EXISTS idx_search_history_popular 
ON public.search_history(query, created_at DESC);

-- ── SESSION & AUTH ────────────────────────────────────────────────

-- Session lookup
CREATE INDEX IF NOT EXISTS idx_sessions_token 
ON public.sessions(token, expires_at);

-- User sessions
CREATE INDEX IF NOT EXISTS idx_sessions_user 
ON public.sessions(user_id, expires_at DESC) 
WHERE is_active = true;

-- ── INVENTORY ─────────────────────────────────────────────────────

-- Stock level queries
CREATE INDEX IF NOT EXISTS idx_inventory_product 
ON public.inventory(product_id, sku) 
INCLUDE (quantity, reserved_quantity);

-- Low stock alerts
CREATE INDEX IF NOT EXISTS idx_inventory_low_stock 
ON public.inventory(product_id) 
WHERE quantity < reorder_threshold;

-- ── RECOMMENDATIONS ───────────────────────────────────────────────

-- User recommendations cache
CREATE INDEX IF NOT EXISTS idx_recommendations_user 
ON public.recommendations(user_id, updated_at DESC);

-- Product recommendations
CREATE INDEX IF NOT EXISTS idx_recommendations_product 
ON public.recommendations(product_id, score DESC);

-- ── PARTIAL INDEXES FOR SOFT DELETE ───────────────────────────────

-- These indexes exclude soft-deleted rows for better performance
-- Already applied above with WHERE deleted_at IS NULL clauses

-- ── VACUUM AND ANALYZE ─────────────────────────────────────────────

-- Update statistics for query planner
ANALYZE public.products;
ANALYZE public.users;
ANALYZE public.orders;
ANALYZE public.wardrobe_items;
ANALYZE public.outfits;
ANALYZE public.brands;
ANALYZE public.reviews;

-- ── QUERY OPTIMIZATION NOTES ───────────────────────────────────────
-- 
-- 1. Use EXPLAIN ANALYZE to verify index usage
-- 2. Avoid SELECT * - use specific columns
-- 3. Use LIMIT with ORDER BY for pagination
-- 4. Consider materialized views for complex aggregations
-- 5. Use prepared statements for repeated queries
--
-- Example optimized queries:
--
-- SELECT id, name, price_cents, thumbnail_url
-- FROM products
-- WHERE category_id = $1 AND is_active = true
-- ORDER BY price_cents DESC
-- LIMIT 20 OFFSET 0;
--
-- Uses idx_products_listing for optimal performance
--
-- ───────────────────────────────────────────────────────────────────
