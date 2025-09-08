-- Migration: Add Categories Table and Update Products Table
-- Date: 2025-09-08
-- Description: Creates a categories table and adds category_id foreign key to products table

-- Create categories table
CREATE TABLE IF NOT EXISTS categories (
    id UUID NOT NULL DEFAULT uuid_generate_v4() PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now()
);

-- Add constraints for categories table
ALTER TABLE categories ADD CONSTRAINT chk_categories_code_format 
    CHECK (code ~ '^[A-Z0-9_-]+$');

-- Add category_id column to products table
ALTER TABLE products ADD COLUMN IF NOT EXISTS category_id UUID;

-- Add foreign key constraint
ALTER TABLE products ADD CONSTRAINT fk_products_category_id 
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL;

-- Create index for better performance
CREATE INDEX IF NOT EXISTS idx_products_category_id ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_categories_code ON categories(code);

-- Insert some default categories based on the existing product data
INSERT INTO categories (code, description) VALUES 
    ('BATCH', 'Batch tracked products'),
    ('MEDICAL', 'Medical supplies and equipment'),
    ('MEDICATION', 'Medications and pharmaceuticals'),
    ('EMERGENCY', 'Emergency supplies and rations'),
    ('GENERAL', 'General products and supplies')
ON CONFLICT (code) DO NOTHING;

-- Update existing products with appropriate categories based on their names
UPDATE products SET category_id = (
    SELECT id FROM categories WHERE code = 'BATCH'
) WHERE LOWER(name) LIKE '%batch%';

UPDATE products SET category_id = (
    SELECT id FROM categories WHERE code = 'MEDICAL'
) WHERE LOWER(name) LIKE '%pen%' OR LOWER(name) LIKE '%glove%' OR LOWER(name) LIKE '%gauze%';

UPDATE products SET category_id = (
    SELECT id FROM categories WHERE code = 'MEDICATION'
) WHERE LOWER(name) LIKE '%tablet%' OR LOWER(name) LIKE '%cream%' OR LOWER(name) LIKE '%vitamin%';

UPDATE products SET category_id = (
    SELECT id FROM categories WHERE code = 'EMERGENCY'
) WHERE LOWER(name) LIKE '%ration%';

-- Set remaining products to GENERAL category
UPDATE products SET category_id = (
    SELECT id FROM categories WHERE code = 'GENERAL'
) WHERE category_id IS NULL;

-- Add comment to the new column
COMMENT ON COLUMN products.category_id IS 'Foreign key reference to categories table';
COMMENT ON TABLE categories IS 'Product categories for better organization and filtering';
