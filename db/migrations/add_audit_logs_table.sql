-- Add audit_logs table for storing evaluation audit narratives
-- This table stores human-readable audit logs that prove what each evaluation task did

CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    evaluation_id UUID,  -- Reference to workflow_executions.id
    tld_string_id UUID NOT NULL REFERENCES tld_strings(id) ON DELETE CASCADE,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Structured audit data (JSON)
    audit_data JSONB NOT NULL,

    -- Human-readable markdown content
    markdown_content TEXT NOT NULL,

    -- Summary stats for quick filtering
    total_tasks INTEGER NOT NULL DEFAULT 0,
    workflow_summaries JSONB,  -- Per-workflow stats

    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_audit_logs_tld_string_id ON audit_logs(tld_string_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_evaluation_id ON audit_logs(evaluation_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_generated_at ON audit_logs(generated_at DESC);

-- Update trigger for updated_at
CREATE OR REPLACE FUNCTION update_audit_logs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_audit_logs_updated_at ON audit_logs;
CREATE TRIGGER trigger_audit_logs_updated_at
    BEFORE UPDATE ON audit_logs
    FOR EACH ROW
    EXECUTE FUNCTION update_audit_logs_updated_at();

-- RLS policies (if RLS is enabled)
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- Allow authenticated users to read audit logs
CREATE POLICY "Allow authenticated read" ON audit_logs
    FOR SELECT
    TO authenticated
    USING (true);

-- Allow service role to manage audit logs
CREATE POLICY "Allow service role full access" ON audit_logs
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

COMMENT ON TABLE audit_logs IS 'Human-readable audit logs for TLD evaluations proving what each task did';
COMMENT ON COLUMN audit_logs.audit_data IS 'Structured JSON containing task narratives, API call stats, and findings';
COMMENT ON COLUMN audit_logs.markdown_content IS 'Formatted Markdown document for human consumption';
COMMENT ON COLUMN audit_logs.workflow_summaries IS 'Per-workflow summary stats for quick dashboard display';
