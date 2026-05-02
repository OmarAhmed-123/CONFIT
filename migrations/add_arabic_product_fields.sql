-- CONFIT Database Migration: Add Arabic Product Fields
-- =======================================================
-- Migration: 0009_add_arabic_product_fields
-- Purpose: Add Arabic localization columns to products table

-- Add new columns for Arabic localization
ALTER TABLE products
    ADD COLUMN IF NOT EXISTS name_ar VARCHAR(255) NULL,
    ADD COLUMN IF NOT EXISTS description_ar TEXT NULL,
    ADD COLUMN IF NOT EXISTS category_ar VARCHAR(100) NULL,
    ADD COLUMN IF NOT EXISTS subcategory_ar VARCHAR(100) NULL,
    ADD COLUMN IF NOT EXISTS color_ar VARCHAR(50) NULL,
    ADD COLUMN IF NOT EXISTS tags_ar JSONB NULL;

-- Add comments for documentation
COMMENT ON COLUMN products.name_ar IS 'Arabic product name for localization';
COMMENT ON COLUMN products.description_ar IS 'Arabic product description for localization';
COMMENT ON COLUMN products.category_ar IS 'Arabic category name for localization';
COMMENT ON COLUMN products.subcategory_ar IS 'Arabic subcategory name for localization';
COMMENT ON COLUMN products.color_ar IS 'Arabic color name for localization';
COMMENT ON COLUMN products.tags_ar IS 'Arabic tags for search and filtering';

-- Create index for Arabic name search
CREATE INDEX IF NOT EXISTS idx_products_name_ar ON products(name_ar) WHERE name_ar IS NOT NULL;

-- Create index for Arabic category search
CREATE INDEX IF NOT EXISTS idx_products_category_ar ON products(category_ar) WHERE category_ar IS NOT NULL;

-- Migration complete
