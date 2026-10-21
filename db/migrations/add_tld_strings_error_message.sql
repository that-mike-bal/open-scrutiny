-- Align production `tld_strings` with client/backend expectations (retry reset, failed-run updates).
-- Run in Supabase SQL editor if you see:
-- "Could not find the 'error_message' column of 'tld_strings' in the schema cache"

ALTER TABLE public.tld_strings
  ADD COLUMN IF NOT EXISTS error_message TEXT;

COMMENT ON COLUMN public.tld_strings.error_message IS 'Optional top-level failure message for the evaluation run';
