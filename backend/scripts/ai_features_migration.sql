-- CONFIT AI Features — Supplemental Migration
-- Run AFTER 0008_ai_features_tables.py
-- Adds: image_embedding column on products, wardrobe_items.image_url,
--        try_on_sessions.category, and helper functions

-- 1. Add image_embedding column to products (pgvector vector(512) for CLIP)
ALTER TABLE products ADD COLUMN IF NOT EXISTS image_embedding vector(512);

-- 2. Create ivfflat index for product image embeddings
CREATE INDEX IF NOT EXISTS ix_products_image_embedding
ON products USING ivfflat (image_embedding vector_cosine_ops)
WITH (lists = 100)
WHERE image_embedding IS NOT NULL;

-- 3. Add image_url column to wardrobe_items if missing
ALTER TABLE wardrobe_items ADD COLUMN IF NOT EXISTS image_url TEXT;

-- 4. Add category column to try_on_sessions if missing
ALTER TABLE try_on_sessions ADD COLUMN IF NOT EXISTS category VARCHAR(50) DEFAULT 'upper_body';

-- 5. Helper function: compute cosine similarity
CREATE OR REPLACE FUNCTION cosine_similarity(a vector, b vector) RETURNS float AS $$
  SELECT 1 - (a <=> b);
$$ LANGUAGE SQL IMMUTABLE STRICT;

-- 6. Helper function: find similar wardrobe items
CREATE OR REPLACE FUNCTION find_similar_wardrobe_items(
  p_user_id UUID,
  p_embedding vector,
  p_threshold float DEFAULT 0.9,
  p_limit int DEFAULT 5
) RETURNS TABLE (
  id UUID,
  name VARCHAR,
  category VARCHAR,
  similarity float
) AS $$
  SELECT
    wi.id,
    wi.name,
    wi.category,
    cosine_similarity(wi.embedding, p_embedding) AS similarity
  FROM wardrobe_items wi
  WHERE wi.user_id = p_user_id
    AND wi.embedding IS NOT NULL
    AND cosine_similarity(wi.embedding, p_embedding) > p_threshold
  ORDER BY wi.embedding <=> p_embedding
  LIMIT p_limit;
$$ LANGUAGE SQL STABLE;
