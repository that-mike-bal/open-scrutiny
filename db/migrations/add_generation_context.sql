-- Migration: Add generation context columns to application_questions_enhanced
-- These columns improve answer generation by:
--   relevant_task_names  -> filters evaluation tasks to only those relevant per question
--   generation_hint      -> per-question LLM guidance for focused, accurate answers

ALTER TABLE application_questions_enhanced
ADD COLUMN IF NOT EXISTS relevant_task_names TEXT[];

ALTER TABLE application_questions_enhanced
ADD COLUMN IF NOT EXISTS generation_hint TEXT;

COMMENT ON COLUMN application_questions_enhanced.relevant_task_names IS 'Array of evaluation task names relevant to this question (e.g., global_trademark_assessment). Used to filter context sent to LLM.';
COMMENT ON COLUMN application_questions_enhanced.generation_hint IS 'Per-question guidance appended to the LLM prompt (e.g., "Focus on DNS technical compliance")';
