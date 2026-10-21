-- Migration: Add applicability, question_set, question_set_name, entity_scope columns
-- to application_questions_enhanced for 2026 guidebook alignment.
--
-- Applicability: controls which application types see each question
-- Question Set: ICANN question set number (1-22) and name
-- Entity Scope: what entity the question is about (applying_entity, primary_user, etc.)

-- 1. Applicability: which application types/profiles must answer this question
ALTER TABLE application_questions_enhanced
ADD COLUMN IF NOT EXISTS applicability TEXT[] DEFAULT '{ALL}';

-- 2. ICANN Question Set number (1-22)
ALTER TABLE application_questions_enhanced
ADD COLUMN IF NOT EXISTS question_set INTEGER;

-- 3. ICANN Question Set name
ALTER TABLE application_questions_enhanced
ADD COLUMN IF NOT EXISTS question_set_name VARCHAR(100);

-- 4. Entity scope: what entity the question is about
ALTER TABLE application_questions_enhanced
ADD COLUMN IF NOT EXISTS entity_scope VARCHAR(50);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_questions_applicability ON application_questions_enhanced USING GIN(applicability);
CREATE INDEX IF NOT EXISTS idx_questions_set ON application_questions_enhanced(question_set);

-- Comments
COMMENT ON COLUMN application_questions_enhanced.applicability IS
  'Which app types must answer: ALL, community, geographic, reserved, brand, code_of_conduct, variant, rvc, government_profile, registry_operator_profile, top25_profile, standard_profile, conditional';
COMMENT ON COLUMN application_questions_enhanced.question_set IS 'ICANN Question Set number (1-22)';
COMMENT ON COLUMN application_questions_enhanced.question_set_name IS 'ICANN Question Set name (e.g., "Applying Entity Information")';
COMMENT ON COLUMN application_questions_enhanced.entity_scope IS 'What entity the question is about (applying_entity, primary_user, payor, financial_institution, etc.)';
