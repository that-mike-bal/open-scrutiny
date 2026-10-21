-- Migration: Add primary/secondary string classification
-- ICANN allows applicants to submit a secondary (alternate) string with each gTLD application.
-- This adds string_type to tld_strings and links a secondary string at the application level.

-- 1. Add string_type to tld_strings (defaults all existing rows to 'primary')
ALTER TABLE tld_strings
  ADD COLUMN IF NOT EXISTS string_type VARCHAR(20) DEFAULT 'primary'
    CHECK (string_type IN ('primary', 'secondary'));

-- 2. Add secondary string reference to tld_applications
ALTER TABLE tld_applications
  ADD COLUMN IF NOT EXISTS secondary_string_id UUID REFERENCES tld_strings(id),
  ADD COLUMN IF NOT EXISTS secondary_tld_string VARCHAR(63);

-- 3. Index for filtering by string_type
CREATE INDEX IF NOT EXISTS idx_tld_strings_string_type ON tld_strings(string_type);
