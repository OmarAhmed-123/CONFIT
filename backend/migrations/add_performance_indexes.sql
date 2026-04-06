-- CONFIT Backend — Performance Indexes Migration
-- Add indexes for common query patterns

-- Products table
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_brand_id ON products(brand_id);
CREATE INDEX IF NOT EXISTS idx_products_store_id ON products(store_id);
CREATE INDEX IF NOT EXISTS idx_products_is_active ON products(is_active);
CREATE INDEX IF NOT EXISTS idx_products_price ON products(price);
CREATE INDEX IF NOT EXISTS idx_products_style_compatibility ON products(style_compatibility);

-- Orders table
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_placed_at ON orders(placed_at);
CREATE INDEX IF NOT EXISTS idx_orders_user_status ON orders(user_id, status);

-- Order items
CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items(product_id);

-- Wardrobe items
CREATE INDEX IF NOT EXISTS idx_wardrobe_items_category ON wardrobe_items(category);
CREATE INDEX IF NOT EXISTS idx_wardrobe_items_color ON wardrobe_items(color);
CREATE INDEX IF NOT EXISTS idx_wardrobe_items_brand ON wardrobe_items(brand);
CREATE INDEX IF NOT EXISTS idx_wardrobe_items_owner_category ON wardrobe_items(owner_user_id, category);

-- Outfits
CREATE INDEX IF NOT EXISTS idx_outfits_owner_user ON outfits(owner_user_id);
CREATE INDEX IF NOT EXISTS idx_outfits_occasion ON outfits(occasion);

-- Return requests
CREATE INDEX IF NOT EXISTS idx_return_requests_status ON return_requests(status);
CREATE INDEX IF NOT EXISTS idx_return_requests_order_id ON return_requests(order_id);

-- Digital twins
CREATE INDEX IF NOT EXISTS idx_digital_twins_user_id ON digital_twins(user_id);
CREATE INDEX IF NOT EXISTS idx_digital_twins_status ON digital_twins(status);

-- Quest completions
CREATE INDEX IF NOT EXISTS idx_quest_completions_user_id ON quest_completions(user_id);
CREATE INDEX IF NOT EXISTS idx_quest_completions_quest_id ON quest_completions(quest_id);

-- User style profiles (from models/)
CREATE INDEX IF NOT EXISTS idx_user_style_profiles_user_id ON user_style_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_body_profiles_user_id ON user_body_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_brand_affinities_user_id ON user_brand_affinities(user_id);
CREATE INDEX IF NOT EXISTS idx_user_behavior_signals_user_id ON user_behavior_signals(user_id);

-- Wardrobe analytics
CREATE INDEX IF NOT EXISTS idx_wardrobe_item_usage_item_id ON wardrobe_item_usage(item_id);
CREATE INDEX IF NOT EXISTS idx_wardrobe_sustainability_user_id ON wardrobe_sustainability_metrics(user_id);
