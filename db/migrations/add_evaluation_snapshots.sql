-- Migration: Create evaluation_snapshots table
-- Standalone archive table for preserving string evaluation data before reruns.
-- Not connected to the application schema — purely for historical comparison.

CREATE TABLE IF NOT EXISTS evaluation_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tld_string TEXT NOT NULL,
    snapshot_label TEXT NOT NULL,              -- e.g. 'pre-rerun-2026-04-02'
    snapshot_date TIMESTAMP WITH TIME ZONE DEFAULT now(),

    -- All evaluation data packed into one JSONB blob per string:
    --   workflow_executions: [{status, overall_status, confidence_score, final_recommendation, ...}]
    --   task_executions:     [{task_name, status, result_status, result_data, confidence_score, user_friendly_summary, ...}]
    --   risk_assessment:     {overall_risk_level, risk_score, risk_category, top_3_risks, high_risk_flags, ...}
    --   generated_report:    <the tld_strings.generated_report JSONB if present>
    --   string_metadata:     {use_case, created_at, updated_at}
    evaluation_data JSONB NOT NULL,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Indexes for lookup
CREATE INDEX IF NOT EXISTS idx_eval_snapshots_tld_string ON evaluation_snapshots(tld_string);
CREATE INDEX IF NOT EXISTS idx_eval_snapshots_label ON evaluation_snapshots(snapshot_label);
CREATE INDEX IF NOT EXISTS idx_eval_snapshots_date ON evaluation_snapshots(snapshot_date);

-- Unique: one snapshot per string per label
CREATE UNIQUE INDEX IF NOT EXISTS idx_eval_snapshots_string_label
    ON evaluation_snapshots(tld_string, snapshot_label);

-- RLS
ALTER TABLE evaluation_snapshots ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Enable read access for all users" ON evaluation_snapshots
    FOR SELECT USING (true);

CREATE POLICY "Enable insert for all users" ON evaluation_snapshots
    FOR INSERT WITH CHECK (true);

-- Permissions
GRANT ALL ON evaluation_snapshots TO authenticated;
GRANT ALL ON evaluation_snapshots TO service_role;

COMMENT ON TABLE evaluation_snapshots IS 'Standalone archive of string evaluation data, used for comparing runs across reprocessing cycles';
COMMENT ON COLUMN evaluation_snapshots.snapshot_label IS 'Human-friendly tag identifying the batch, e.g. pre-rerun-2026-04-02';
COMMENT ON COLUMN evaluation_snapshots.evaluation_data IS 'JSONB blob containing workflow_executions, task_executions, risk_assessment, generated_report, string_metadata';
