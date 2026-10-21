-- Add new application statuses needed by async generation workflow
-- Run this in the Supabase SQL Editor

ALTER TABLE tld_applications
  DROP CONSTRAINT IF EXISTS tld_applications_status_check;

ALTER TABLE tld_applications
  ADD CONSTRAINT tld_applications_status_check
  CHECK (status IN (
    'Draft',
    'Generating',
    'In_Progress',
    'Ready_For_Review',
    'Completed',
    'Failed',
    'Submitted',
    'Under_Evaluation'
  ));
