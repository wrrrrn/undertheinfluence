-- Initialize PostgreSQL extensions for UnderTheInfluence

-- Enable pg_trgm for trigram-based text search (useful for LIKE queries)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Enable unaccent for accent-insensitive text search
CREATE EXTENSION IF NOT EXISTS unaccent;
