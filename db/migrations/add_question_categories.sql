-- Migration: Add question categorization columns to application_questions_enhanced
-- These columns enable the 3-tier answer generation system:
--   entity_field    -> direct DB lookup (no AI)
--   selection_field -> show options + tips (no AI)
--   substantive_field -> AI-generated via Gemini
--   file_upload     -> show requirements (no AI)

ALTER TABLE application_questions_enhanced
ADD COLUMN IF NOT EXISTS question_category VARCHAR(30) DEFAULT 'substantive_field'
    CHECK (question_category IN ('entity_field', 'selection_field', 'substantive_field', 'file_upload'));

ALTER TABLE application_questions_enhanced
ADD COLUMN IF NOT EXISTS applicant_field_mapping VARCHAR(100);

-- Add index for fast category-based queries
CREATE INDEX IF NOT EXISTS idx_questions_category ON application_questions_enhanced(question_category);

COMMENT ON COLUMN application_questions_enhanced.question_category IS 'Determines how this question is handled: entity_field (DB lookup), selection_field (options), substantive_field (AI), file_upload (requirements)';
COMMENT ON COLUMN application_questions_enhanced.applicant_field_mapping IS 'Maps entity_field questions to applicants table columns (e.g. legal_name, phone, email)';
