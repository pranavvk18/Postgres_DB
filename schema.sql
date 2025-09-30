-- Enable trigram extension (needed for prefix, substring, fuzzy)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 1. Prefix + Substring + Fuzzy Search (trigram index on "name")
CREATE INDEX IF NOT EXISTS idx_medicines_name_trgm
ON medicines USING GIN (name gin_trgm_ops);

-- 2. Full-Text Search
-- Add a tsvector column if not already present
ALTER TABLE medicines 
ADD COLUMN IF NOT EXISTS search_tsv tsvector;

-- Fill the tsvector column with data from name + short_composition
UPDATE medicines
SET search_tsv = to_tsvector(
    'english', 
    coalesce(name, '') || ' ' || coalesce(short_composition, '')
);

-- Create GIN index on tsvector
CREATE INDEX IF NOT EXISTS idx_medicines_tsv
ON medicines USING GIN (search_tsv);
