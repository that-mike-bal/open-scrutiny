-- ============================================================================
-- RuleEval -- Deployable database schema (empty; no data)
-- ============================================================================
-- Bring-your-own-database: this app needs a PostgreSQL database. We recommend
-- Supabase (free tier). Deploy this file to a fresh project (Supabase SQL editor
-- or psql), then apply the incremental updates in db/migrations/ in the order
-- listed in db/README.md. This file creates tables only -- it seeds no data.
--
-- Assembled from the project's own schema definitions. If your Postgres/Supabase
-- lacks it, `CREATE EXTENSION IF NOT EXISTS "uuid-ossp";` is included below.
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";



-- ============================================================================
-- Evaluation schema (tld_strings, task/workflow executions, check results)
-- ============================================================================
-- =====================================================
-- ENHANCED CREWAI SCHEMA DEPLOYMENT
-- Fresh deployment - drops existing tables and recreates
-- =====================================================

-- Drop existing tables in correct order (respecting foreign key constraints)
DROP VIEW IF EXISTS binary_gate_summary CASCADE;
DROP VIEW IF EXISTS tld_latest_task_results CASCADE;
DROP VIEW IF EXISTS tld_evaluation_status CASCADE;

DROP TABLE IF EXISTS tool_executions CASCADE;
DROP TABLE IF EXISTS agent_executions CASCADE;
DROP TABLE IF EXISTS validation_results CASCADE;
DROP TABLE IF EXISTS string_analysis_results CASCADE;
DROP TABLE IF EXISTS reserved_names_results CASCADE;
DROP TABLE IF EXISTS blocked_names_results CASCADE;
DROP TABLE IF EXISTS iana_check_results CASCADE;
DROP TABLE IF EXISTS task_executions CASCADE;
DROP TABLE IF EXISTS workflow_executions CASCADE;
DROP TABLE IF EXISTS task_definitions CASCADE;
DROP TABLE IF EXISTS tld_strings CASCADE;

-- Ensure UUID extension is available
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- CORE TABLES
-- =====================================================

-- Main TLD strings table
CREATE TABLE tld_strings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID, -- References auth.users(id), nullable for anonymous usage
    tld_string TEXT NOT NULL UNIQUE,
    use_case TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- Task definitions (predefined task types)
CREATE TABLE task_definitions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_name TEXT NOT NULL UNIQUE, -- Database-friendly name (e.g., 'iana_database_check')
    task_display_name TEXT NOT NULL, -- User-friendly name (e.g., 'IANA Database Verification')
    task_category TEXT NOT NULL, -- 'binary_compliance', 'analysis', 'validation'
    description TEXT,
    is_binary_gate BOOLEAN DEFAULT FALSE, -- True for pass/fail gates
    can_block_workflow BOOLEAN DEFAULT FALSE, -- True if failure blocks entire workflow
    expected_tools TEXT[], -- Array of tool names this task typically uses
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- Track complete workflow executions
CREATE TABLE workflow_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tld_string_id UUID NOT NULL REFERENCES tld_strings(id) ON DELETE CASCADE,
    
    -- Workflow metadata
    workflow_type TEXT NOT NULL, -- 'binary_compliance_check', 'comprehensive_evaluation', etc.
    crew_execution_id TEXT, -- CrewAI internal execution ID
    
    -- Execution tracking
    status TEXT NOT NULL DEFAULT 'PENDING', -- 'PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED'
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    execution_time_minutes INTEGER,
    
    -- Task summary
    total_tasks INTEGER DEFAULT 0,
    completed_tasks INTEGER DEFAULT 0,
    failed_tasks INTEGER DEFAULT 0,
    
    -- Overall results
    overall_status TEXT, -- 'PASS', 'BLOCKED', 'REVIEW_REQUIRED'
    confidence_score DECIMAL(3,2), -- Overall confidence 0.00 to 1.00
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    
    CONSTRAINT valid_workflow_status CHECK (status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED')),
    CONSTRAINT valid_overall_status CHECK (overall_status IN ('PASS', 'BLOCKED', 'REVIEW_REQUIRED', 'CLEAR', 'LOW_RISK', 'MEDIUM_RISK', 'HIGH_RISK'))
);

-- Track individual task executions for each workflow
CREATE TABLE task_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tld_string_id UUID NOT NULL REFERENCES tld_strings(id) ON DELETE CASCADE,
    workflow_execution_id UUID NOT NULL REFERENCES workflow_executions(id) ON DELETE CASCADE,
    task_definition_id UUID REFERENCES task_definitions(id), -- Can be null for dynamic tasks
    
    -- Task identification
    task_name TEXT NOT NULL, -- Database-friendly name (e.g., 'iana_database_check')
    task_display_name TEXT, -- User-friendly name (e.g., 'IANA Database Verification')
    
    -- Execution metadata
    status TEXT NOT NULL DEFAULT 'PENDING', -- 'PENDING', 'RUNNING', 'COMPLETED', 'FAILED'
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    execution_time_seconds INTEGER,
    
    -- Task results
    result_status TEXT, -- 'PASS', 'FAIL', 'BLOCKED', 'REVIEW_REQUIRED', etc.
    result_data JSONB, -- Structured output from the task
    confidence_score DECIMAL(5,2), -- 0.00 to 100.00 (percentage)
    
    -- Agent and tool information
    agent_name TEXT,
    agent_version TEXT,
    tools_used TEXT[], -- Array of tool names used
    tool_call_count INTEGER DEFAULT 0,
    
    -- CrewAI specific data
    crew_task_id TEXT, -- CrewAI internal task ID
    raw_output TEXT, -- Raw output from this specific task
    user_friendly_summary TEXT, -- Processed summary for UI display
    
    -- Workflow context
    workflow_context JSONB, -- Additional context data
    
    -- Error handling
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    
    CONSTRAINT valid_status CHECK (status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED')),
    CONSTRAINT valid_result_status CHECK (result_status IN ('PASS', 'FAIL', 'BLOCKED', 'REVIEW_REQUIRED', 'CLEAR', 'LOW_RISK', 'MEDIUM_RISK', 'HIGH_RISK', 'VERIFIED', 'REQUIRES_EXCEPTION'))
);

-- =====================================================
-- SPECIFIC TASK RESULT TABLES
-- =====================================================

-- IANA Database Check Results
CREATE TABLE iana_check_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_execution_id UUID NOT NULL REFERENCES task_executions(id) ON DELETE CASCADE,
    tld_string TEXT NOT NULL,
    is_delegated BOOLEAN NOT NULL,
    iana_data_source TEXT, -- 'live_api', 'cached_data', 'fallback'
    data_timestamp TIMESTAMP WITH TIME ZONE,
    delegation_details JSONB, -- If delegated, store details
    iana_list_checked TEXT[], -- List of IANA sources checked
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- Blocked Names Check Results
CREATE TABLE blocked_names_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_execution_id UUID NOT NULL REFERENCES task_executions(id) ON DELETE CASCADE,
    tld_string TEXT NOT NULL,
    is_blocked BOOLEAN NOT NULL,
    blocked_category TEXT, -- 'special_use', 'country_code', 'icann_entity', etc.
    blocking_reason TEXT,
    icann_list_version TEXT,
    policy_references TEXT[], -- Array of policy references
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- Reserved Names Check Results
CREATE TABLE reserved_names_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_execution_id UUID NOT NULL REFERENCES task_executions(id) ON DELETE CASCADE,
    tld_string TEXT NOT NULL,
    is_reserved BOOLEAN NOT NULL,
    reserved_category TEXT, -- 'igo', 'rcrc', 'ioc', 'geographic'
    reserving_organization TEXT,
    reservation_details JSONB,
    exception_required BOOLEAN DEFAULT FALSE,
    exception_process TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- String Analysis Results
CREATE TABLE string_analysis_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_execution_id UUID NOT NULL REFERENCES task_executions(id) ON DELETE CASCADE,
    tld_string TEXT NOT NULL,
    character_count INTEGER,
    is_ascii BOOLEAN,
    contains_special_chars BOOLEAN,
    technical_compliance_score DECIMAL(3,2),
    identified_issues TEXT[],
    recommendations TEXT[],
    next_steps TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- Data Validation Results (for fact-checking tasks)
CREATE TABLE validation_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_execution_id UUID NOT NULL REFERENCES task_executions(id) ON DELETE CASCADE,
    tld_string TEXT NOT NULL,
    validation_status TEXT NOT NULL, -- 'CONFIRMED', 'CONTRADICTION_DETECTED', 'PARTIAL_VALIDATION'
    discrepancies_found INTEGER DEFAULT 0,
    corrected_findings JSONB, -- Array of corrections made
    data_sources_checked TEXT[],
    validation_confidence DECIMAL(3,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    
    CONSTRAINT valid_validation_status CHECK (validation_status IN ('CONFIRMED', 'CONTRADICTION_DETECTED', 'PARTIAL_VALIDATION'))
);

-- =====================================================
-- AGENT AND TOOL TRACKING
-- =====================================================

-- Track agent performance and usage
CREATE TABLE agent_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_execution_id UUID NOT NULL REFERENCES task_executions(id) ON DELETE CASCADE,
    agent_name TEXT NOT NULL,
    agent_role TEXT, -- 'String Technical Analysis Specialist', 'ICANN Compliance Gatekeeper', etc.
    execution_time_seconds INTEGER,
    token_usage INTEGER,
    tool_calls_made INTEGER DEFAULT 0,
    success_rate DECIMAL(3,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- Track tool usage and performance
CREATE TABLE tool_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_execution_id UUID NOT NULL REFERENCES task_executions(id) ON DELETE CASCADE,
    tool_name TEXT NOT NULL,
    tool_input JSONB,
    tool_output JSONB,
    execution_time_ms INTEGER,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- =====================================================
-- INDEXES FOR PERFORMANCE
-- =====================================================

-- TLD strings indexes
CREATE INDEX idx_tld_strings_user_id ON tld_strings(user_id);
CREATE INDEX idx_tld_strings_tld_string ON tld_strings(tld_string);
CREATE INDEX idx_tld_strings_created_at ON tld_strings(created_at);

-- Workflow executions indexes
CREATE INDEX idx_workflow_executions_tld_string_id ON workflow_executions(tld_string_id);
CREATE INDEX idx_workflow_executions_status ON workflow_executions(status);
CREATE INDEX idx_workflow_executions_workflow_type ON workflow_executions(workflow_type);
CREATE INDEX idx_workflow_executions_overall_status ON workflow_executions(overall_status);
CREATE INDEX idx_workflow_executions_created_at ON workflow_executions(created_at);

-- Task executions indexes
CREATE INDEX idx_task_executions_tld_string_id ON task_executions(tld_string_id);
CREATE INDEX idx_task_executions_workflow_execution_id ON task_executions(workflow_execution_id);
CREATE INDEX idx_task_executions_task_definition_id ON task_executions(task_definition_id);
CREATE INDEX idx_task_executions_status ON task_executions(status);
CREATE INDEX idx_task_executions_result_status ON task_executions(result_status);
CREATE INDEX idx_task_executions_task_name ON task_executions(task_name);

-- Task definitions indexes
CREATE INDEX idx_task_definitions_category ON task_definitions(task_category);
CREATE INDEX idx_task_definitions_binary_gate ON task_definitions(is_binary_gate);

-- Result table indexes
CREATE INDEX idx_iana_results_task_execution_id ON iana_check_results(task_execution_id);
CREATE INDEX idx_blocked_results_task_execution_id ON blocked_names_results(task_execution_id);
CREATE INDEX idx_reserved_results_task_execution_id ON reserved_names_results(task_execution_id);
CREATE INDEX idx_string_analysis_results_task_execution_id ON string_analysis_results(task_execution_id);
CREATE INDEX idx_validation_results_task_execution_id ON validation_results(task_execution_id);

-- Agent and tool tracking indexes
CREATE INDEX idx_agent_executions_task_execution_id ON agent_executions(task_execution_id);
CREATE INDEX idx_tool_executions_task_execution_id ON tool_executions(task_execution_id);
CREATE INDEX idx_tool_executions_tool_name ON tool_executions(tool_name);

-- =====================================================
-- VIEWS FOR EASY QUERYING
-- =====================================================

-- Get complete evaluation status for a TLD string
CREATE VIEW tld_evaluation_status AS
SELECT 
    ts.id as tld_string_id,
    ts.tld_string,
    ts.use_case,
    we.id as workflow_execution_id,
    we.workflow_type,
    we.status as workflow_status,
    we.overall_status,
    we.confidence_score,
    we.started_at,
    we.completed_at,
    we.execution_time_minutes,
    we.total_tasks,
    we.completed_tasks,
    we.failed_tasks,
    CASE 
        WHEN we.completed_tasks = we.total_tasks AND we.failed_tasks = 0 THEN TRUE
        ELSE FALSE
    END as all_tasks_completed,
    ts.created_at as tld_created_at,
    ts.updated_at as tld_updated_at
FROM tld_strings ts
LEFT JOIN workflow_executions we ON ts.id = we.tld_string_id
ORDER BY ts.created_at DESC;

-- Get latest task execution results for each TLD
CREATE VIEW tld_latest_task_results AS
SELECT DISTINCT ON (ts.id, te.task_name)
    ts.id as tld_string_id,
    ts.tld_string,
    te.task_name,
    te.task_display_name,
    te.status,
    te.result_status,
    te.confidence_score,
    te.agent_name,
    te.user_friendly_summary,
    te.completed_at,
    td.is_binary_gate,
    td.can_block_workflow
FROM tld_strings ts
JOIN task_executions te ON ts.id = te.tld_string_id
LEFT JOIN task_definitions td ON te.task_definition_id = td.id
ORDER BY ts.id, te.task_name, te.created_at DESC;

-- Get binary gate status summary
CREATE VIEW binary_gate_summary AS
SELECT 
    ts.id as tld_string_id,
    ts.tld_string,
    COUNT(te.id) as total_binary_gates,
    COUNT(CASE WHEN te.result_status = 'PASS' THEN 1 END) as passed_gates,
    COUNT(CASE WHEN te.result_status = 'BLOCKED' THEN 1 END) as blocked_gates,
    COUNT(CASE WHEN te.result_status = 'FAIL' THEN 1 END) as failed_gates,
    CASE 
        WHEN COUNT(CASE WHEN te.result_status = 'BLOCKED' THEN 1 END) > 0 THEN 'BLOCKED'
        WHEN COUNT(CASE WHEN te.result_status = 'FAIL' THEN 1 END) > 0 THEN 'FAILED'
        WHEN COUNT(te.id) = COUNT(CASE WHEN te.result_status = 'PASS' THEN 1 END) THEN 'PASSED'
        ELSE 'PENDING'
    END as overall_binary_status
FROM tld_strings ts
LEFT JOIN task_executions te ON ts.id = te.tld_string_id
LEFT JOIN task_definitions td ON te.task_definition_id = td.id
WHERE td.is_binary_gate = TRUE OR te.task_name IN ('iana_database_check', 'blocked_names_check', 'reserved_names_check')
GROUP BY ts.id, ts.tld_string;

-- =====================================================
-- INITIAL DATA SETUP
-- =====================================================

-- Insert standard task definitions
INSERT INTO task_definitions (task_name, task_display_name, task_category, description, is_binary_gate, can_block_workflow) VALUES
('string_analysis', 'String Technical Analysis', 'technical_analysis', 'Comprehensive analysis of TLD string technical characteristics', FALSE, FALSE),
('iana_database_check', 'IANA Database Verification', 'binary_compliance', 'Check if TLD is already delegated in IANA root zone', TRUE, TRUE),
('blocked_names_check', 'Blocked Names Verification', 'binary_compliance', 'Check against ICANN blocked names list', TRUE, TRUE),
('reserved_names_check', 'Reserved Names Verification', 'binary_compliance', 'Check against ICANN reserved names list', TRUE, FALSE),
('findings_validation', 'Data Validation & Fact-Check', 'validation', 'Cross-reference and validate all findings', FALSE, FALSE);

-- =====================================================
-- ROW LEVEL SECURITY (RLS)
-- =====================================================

-- Enable RLS on all tables
ALTER TABLE tld_strings ENABLE ROW LEVEL SECURITY;
ALTER TABLE workflow_executions ENABLE ROW LEVEL SECURITY;
ALTER TABLE task_executions ENABLE ROW LEVEL SECURITY;

-- Policies for authenticated users
CREATE POLICY "Users can view their own TLD strings" ON tld_strings
    FOR SELECT USING (auth.uid() = user_id OR user_id IS NULL);

CREATE POLICY "Users can insert their own TLD strings" ON tld_strings
    FOR INSERT WITH CHECK (auth.uid() = user_id OR user_id IS NULL);

CREATE POLICY "Users can update their own TLD strings" ON tld_strings
    FOR UPDATE USING (auth.uid() = user_id OR user_id IS NULL);

CREATE POLICY "Users can view workflow executions for their TLD strings" ON workflow_executions
    FOR SELECT USING (
        tld_string_id IN (
            SELECT id FROM tld_strings WHERE user_id = auth.uid() OR user_id IS NULL
        )
    );

CREATE POLICY "Users can view task executions for their TLD strings" ON task_executions
    FOR SELECT USING (
        tld_string_id IN (
            SELECT id FROM tld_strings WHERE user_id = auth.uid() OR user_id IS NULL
        )
    );

-- Allow anonymous access for demo purposes (can be removed in production)
CREATE POLICY "Allow anonymous access to TLD strings" ON tld_strings
    FOR ALL USING (user_id IS NULL);

CREATE POLICY "Allow anonymous access to workflow executions" ON workflow_executions
    FOR ALL USING (
        tld_string_id IN (
            SELECT id FROM tld_strings WHERE user_id IS NULL
        )
    );

CREATE POLICY "Allow anonymous access to task executions" ON task_executions
    FOR ALL USING (
        tld_string_id IN (
            SELECT id FROM tld_strings WHERE user_id IS NULL
        )
    );

-- =====================================================
-- DEPLOYMENT COMPLETE
-- =====================================================

-- Show final status
SELECT 'Enhanced CrewAI Schema Deployment Complete!' as status; 

-- ============================================================================
-- Application entity schema (applicants, applications, responses)
-- ============================================================================
-- =====================================================
-- ICANN APPLICATION DATABASE SCHEMA V1
-- Simple schema focused on core application drafting needs
-- =====================================================

-- Example Registry applicant information (reusable across all applications)
CREATE TABLE applicants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Organization Details
    legal_name VARCHAR(255) NOT NULL DEFAULT 'Example Registry LLC',
    business_name VARCHAR(255) DEFAULT 'Example Registry',
    entity_type VARCHAR(100) NOT NULL DEFAULT 'Limited Liability Company',
    jurisdiction VARCHAR(100) NOT NULL DEFAULT 'Delaware, United States',
    incorporation_date DATE,
    
    -- Contact Information
    business_address TEXT NOT NULL,
    mailing_address TEXT,
    phone VARCHAR(50),
    email VARCHAR(255) NOT NULL,
    website VARCHAR(255),
    
    -- Financial Information
    annual_revenue DECIMAL(15,2),
    total_assets DECIMAL(15,2),
    funding_sources TEXT,
    financial_statement_url TEXT,
    
    -- Key Personnel (stored as JSONB for flexibility)
    key_personnel JSONB DEFAULT '[]'::jsonb,
    
    -- Registry Experience
    registry_experience_description TEXT,
    current_tlds TEXT[], -- Array of currently operated TLDs
    affiliated_organizations TEXT[],
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- Individual TLD applications (one per string)
CREATE TABLE tld_applications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    applicant_id UUID NOT NULL REFERENCES applicants(id),
    tld_string_id UUID NOT NULL REFERENCES tld_strings(id), -- Link to existing string evaluation
    
    -- Application Identifiers
    internal_reference VARCHAR(100) NOT NULL UNIQUE,
    icann_application_id VARCHAR(50), -- Will be assigned by ICANN later
    
    -- TLD Details
    tld_string VARCHAR(63) NOT NULL, -- Denormalized for convenience
    string_meaning TEXT,
    string_rationale TEXT,
    intended_use TEXT,
    
    -- Application Type (determines which questions are shown)
    application_type VARCHAR(50) DEFAULT 'standard' CHECK (application_type IN ('standard', 'community', 'brand', 'geographic', 'idn_variant')),
    
    -- Application Status
    status VARCHAR(50) DEFAULT 'Draft' CHECK (status IN ('Draft', 'In_Progress', 'Ready_For_Review', 'Submitted', 'Under_Evaluation')),
    completion_percentage DECIMAL(5,2) DEFAULT 0.00,
    
    -- Submission Info
    submission_deadline DATE,
    submitted_at TIMESTAMP WITH TIME ZONE,
    application_fee_paid BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    
    UNIQUE(applicant_id, tld_string_id)
);

-- ICANN Master Questions (the ~200 questions from ICANN)
CREATE TABLE application_questions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Question Identification
    question_number VARCHAR(20) NOT NULL UNIQUE, -- e.g., "18a", "19.1", "20.b.i"
    section_number INTEGER NOT NULL,
    section_name VARCHAR(100) NOT NULL, -- e.g., "Registry Services", "Technical Capability"
    sub_section VARCHAR(100),
    
    -- Question Content
    question_text TEXT NOT NULL,
    question_description TEXT, -- Additional context/instructions
    character_limit INTEGER,
    
    -- Question Properties  
    requires_document_upload BOOLEAN DEFAULT FALSE,
    acceptable_file_types TEXT[], -- ['PDF', 'DOC', 'XLS']
    is_public BOOLEAN DEFAULT FALSE, -- Will this be made public by ICANN?
    
    -- Conditional Logic (simple)
    is_conditional BOOLEAN DEFAULT FALSE,
    condition_description TEXT, -- Human readable condition
    
    -- Metadata
    question_version VARCHAR(20) DEFAULT '2012', -- ICANN version
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- Application Responses (AI-generated + human-edited answers)
CREATE TABLE application_responses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tld_application_id UUID NOT NULL REFERENCES tld_applications(id) ON DELETE CASCADE,
    application_question_id UUID NOT NULL REFERENCES application_questions(id),
    
    -- Response Content (rich text with formatting)
    response_text TEXT, -- Main response content
    response_html TEXT, -- Formatted version for display
    response_markdown TEXT, -- Markdown version for editing
    
    -- Response Metadata
    word_count INTEGER,
    character_count INTEGER,
    is_complete BOOLEAN DEFAULT FALSE,
    confidence_score DECIMAL(3,2), -- AI confidence in response quality
    
    -- Source Information (links back to string evaluation data)
    source_evaluations JSONB DEFAULT '[]'::jsonb, -- Array of task_execution_ids that informed this response
    source_description TEXT, -- Human readable description of sources used
    
    -- Generation Information
    generation_method VARCHAR(50) DEFAULT 'ai_generated' CHECK (generation_method IN ('ai_generated', 'human_written', 'hybrid')),
    ai_model_used VARCHAR(100), -- e.g., "gpt-4", "claude-3"
    generated_at TIMESTAMP WITH TIME ZONE,
    
    -- Review Status
    review_status VARCHAR(50) DEFAULT 'draft' CHECK (review_status IN ('draft', 'ai_reviewed', 'human_reviewed', 'approved', 'needs_revision')),
    review_notes TEXT,
    reviewed_by VARCHAR(255),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    
    -- Version Control
    version INTEGER DEFAULT 1,
    previous_version_id UUID REFERENCES application_responses(id),
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    
    UNIQUE(tld_application_id, application_question_id, version)
);

-- Response Generation History (track AI workflow executions)
CREATE TABLE response_generation_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tld_application_id UUID NOT NULL REFERENCES tld_applications(id),
    application_response_id UUID REFERENCES application_responses(id),
    
    -- Workflow Information
    workflow_type VARCHAR(100) NOT NULL, -- e.g., "application_response_generation", "response_enhancement"
    workflow_execution_id UUID, -- Links to existing workflow_executions table if needed
    
    -- Generation Details
    questions_targeted INTEGER[], -- Array of question IDs this workflow addressed
    input_data JSONB, -- Source evaluation data used
    prompt_template TEXT, -- AI prompt used
    
    -- Results
    status VARCHAR(50) DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED')),
    responses_generated INTEGER DEFAULT 0,
    responses_approved INTEGER DEFAULT 0,
    
    -- Performance Metrics
    total_execution_time_seconds INTEGER,
    average_response_length INTEGER,
    average_confidence_score DECIMAL(3,2),
    
    -- Error Handling
    error_message TEXT,
    
    -- Metadata
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- =====================================================
-- INDEXES FOR PERFORMANCE
-- =====================================================

CREATE INDEX idx_tld_applications_tld_string_id ON tld_applications(tld_string_id);
CREATE INDEX idx_tld_applications_status ON tld_applications(status);
CREATE INDEX idx_application_responses_tld_application_id ON application_responses(tld_application_id);
CREATE INDEX idx_application_responses_question_id ON application_responses(application_question_id);
CREATE INDEX idx_application_responses_review_status ON application_responses(review_status);
CREATE INDEX idx_application_questions_section ON application_questions(section_name);
CREATE INDEX idx_response_generation_executions_status ON response_generation_executions(status);

-- =====================================================
-- INITIAL DATA SETUP
-- =====================================================

-- Note: Example Registry applicant data will be populated via your own seed script
-- This provides comprehensive real-world data from the Example Registry knowledgebase

-- Sample application questions (will need to be populated with actual ICANN questions)
INSERT INTO application_questions (question_number, section_number, section_name, question_text, character_limit) VALUES
('18a', 18, 'Registry Services', 'Describe your registry services and technical capabilities.', 5000),
('19.1', 19, 'Technical Capability', 'Provide details of your technical infrastructure and architecture.', 7500),
('20.1', 20, 'Operational Capability', 'Describe your operational procedures and capabilities.', 6000),
('21.1', 21, 'Financial Capability', 'Provide financial projections and demonstrate financial capability.', 8000);

-- =====================================================
-- VIEWS FOR EASY QUERYING
-- =====================================================

-- Complete application overview
CREATE VIEW application_overview AS
SELECT 
    ta.id,
    ta.internal_reference,
    ta.tld_string,
    ta.status,
    ta.completion_percentage,
    a.legal_name as applicant_name,
    ts.status as string_evaluation_status,
    COUNT(ar.id) as total_responses,
    COUNT(CASE WHEN ar.is_complete = true THEN 1 END) as completed_responses,
    COUNT(CASE WHEN ar.review_status = 'approved' THEN 1 END) as approved_responses
FROM tld_applications ta
JOIN applicants a ON ta.applicant_id = a.id
JOIN tld_strings ts ON ta.tld_string_id = ts.id
LEFT JOIN application_responses ar ON ta.id = ar.tld_application_id
GROUP BY ta.id, ta.internal_reference, ta.tld_string, ta.status, ta.completion_percentage, a.legal_name, ts.status;

-- Response completion status by application
CREATE VIEW application_completion_status AS
SELECT 
    ta.id as application_id,
    ta.tld_string,
    ta.status,
    COUNT(aq.id) as total_questions,
    COUNT(ar.id) as answered_questions,
    COUNT(CASE WHEN ar.is_complete = true THEN 1 END) as complete_answers,
    ROUND((COUNT(ar.id)::DECIMAL / COUNT(aq.id)) * 100, 2) as completion_percentage
FROM tld_applications ta
CROSS JOIN application_questions aq
LEFT JOIN application_responses ar ON ta.id = ar.tld_application_id AND aq.id = ar.application_question_id
GROUP BY ta.id, ta.tld_string, ta.status; 

-- ============================================================================
-- Enhanced questions & answers schema
-- ============================================================================
-- =====================================================
-- ENHANCED APPLICATION QUESTIONS & ANSWERS SCHEMA
-- Comprehensive 1:1 mapping with parsed data points
-- =====================================================

-- Enhanced Application Questions table with parsed metadata
CREATE TABLE application_questions_enhanced (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Question Identification
    question_number VARCHAR(20) NOT NULL UNIQUE, -- e.g., "7", "8", "18a", "19.1", "20.b.i"
    section_name VARCHAR(100) NOT NULL, -- e.g., "Applicant Entity", "Registry Services"
    sub_section VARCHAR(100), -- e.g., "Primary Business Address", "Direct Parent Company"
    
    -- Question Content
    question_text TEXT NOT NULL,
    notes_instructions TEXT, -- From **Notes/Instructions:** section
    
    -- Parsed Input Requirements
    input_type VARCHAR(50) NOT NULL, -- 'text', 'textarea', 'upload', 'dropdown', 'radio', 'checkbox', 'url', 'email', 'phone'
    character_limit INTEGER,
    word_limit INTEGER,
    file_upload_max_pages INTEGER,
    acceptable_file_types TEXT[], -- ['PDF', 'DOC', 'XLS']
    
    -- Validation Requirements (parsed from Input Field Requirements)
    validation_rules JSONB DEFAULT '{}', -- Structured validation rules
    /*
    Example validation_rules:
    {
        "required": true,
        "format": "email|url|phone",
        "min_length": 10,
        "max_length": 255,
        "pattern": "^[a-zA-Z0-9]+$",
        "no_po_box": true,
        "valid_url": true,
        "alphanumeric_only": true,
        "latin_characters_only": true
    }
    */
    
    -- Criteria (parsed from **Criteria:** section)
    criteria_codes TEXT[], -- ['CR-1', 'CR-2', 'CR-3']
    criteria_descriptions TEXT[], -- Human readable criteria descriptions
    
    -- Question Properties
    is_public BOOLEAN DEFAULT FALSE, -- From **Public Posting:** Yes/No
    is_required BOOLEAN DEFAULT TRUE,
    is_conditional BOOLEAN DEFAULT FALSE,
    condition_description TEXT, -- Human readable condition logic
    dependent_question_numbers TEXT[], -- Questions this depends on
    
    -- Data Type Classification (for AI response generation)
    expected_data_type VARCHAR(50), -- 'organization_info', 'contact_details', 'financial_data', 'technical_specs', 'legal_documents'
    response_format VARCHAR(50), -- 'narrative', 'structured_data', 'document_upload', 'selection'
    
    -- Metadata
    question_version VARCHAR(20) DEFAULT '2012', -- ICANN version
    is_active BOOLEAN DEFAULT TRUE,
    parsing_confidence DECIMAL(3,2) DEFAULT 1.0, -- Confidence in parsed data quality
    parsed_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- Enhanced Application Answers table with comprehensive metadata
CREATE TABLE application_answers_enhanced (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Foreign Keys
    tld_application_id UUID NOT NULL REFERENCES tld_applications(id) ON DELETE CASCADE,
    question_id UUID NOT NULL REFERENCES application_questions_enhanced(id),
    
    -- Answer Content (multiple formats for flexibility)
    answer_text TEXT, -- Main response content
    answer_html TEXT, -- HTML formatted version
    answer_markdown TEXT, -- Markdown version for editing
    answer_structured JSONB, -- Structured data for complex answers
    
    -- File Uploads (if applicable)
    uploaded_files JSONB DEFAULT '[]', -- Array of file metadata
    /*
    Example uploaded_files:
    [
        {
            "filename": "articles_of_incorporation.pdf",
            "file_size_bytes": 1048576,
            "file_type": "PDF",
            "uploaded_at": "2024-01-15T10:30:00Z",
            "file_url": "https://storage.example.com/files/...",
            "file_hash": "sha256:abc123..."
        }
    ]
    */
    
    -- Answer Quality Metrics
    word_count INTEGER,
    character_count INTEGER,
    completeness_score DECIMAL(3,2), -- 0.0 to 1.0
    confidence_score DECIMAL(3,2), -- AI confidence in answer quality
    validation_status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'valid', 'invalid', 'needs_review'
    validation_errors JSONB DEFAULT '[]', -- Array of validation error messages
    
    -- Source Information (links back to evaluation data)
    source_evaluations JSONB DEFAULT '[]', -- Array of task_execution_ids that informed this answer
    source_data_summary TEXT, -- Human readable description of data sources used
    data_availability_score DECIMAL(3,2), -- How much needed data was available (0.0 to 1.0)
    
    -- Generation Information
    generation_method VARCHAR(50) DEFAULT 'ai_generated', -- 'ai_generated', 'human_written', 'hybrid', 'template_filled'
    ai_model_used VARCHAR(100), -- e.g., "gpt-4", "claude-3", "gemini-pro"
    generation_prompt TEXT, -- Prompt used for AI generation
    generation_temperature DECIMAL(3,2), -- AI temperature setting used
    generated_at TIMESTAMP WITH TIME ZONE,
    
    -- Review and Approval Workflow
    review_status VARCHAR(50) DEFAULT 'draft', -- 'draft', 'ai_reviewed', 'human_reviewed', 'approved', 'needs_revision', 'rejected'
    review_notes TEXT,
    review_score DECIMAL(3,2), -- Reviewer's quality score (0.0 to 1.0)
    reviewed_by VARCHAR(255),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    
    -- Error Handling for Missing Data
    missing_data_fields TEXT[], -- Array of data fields that were missing
    error_handling_strategy VARCHAR(50), -- 'skip', 'placeholder', 'request_manual', 'use_default'
    fallback_data_used JSONB, -- Any fallback/default data that was used
    
    -- Version Control
    version INTEGER DEFAULT 1,
    previous_version_id UUID REFERENCES application_answers_enhanced(id),
    change_reason TEXT, -- Why this version was created
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    
    -- Constraints
    UNIQUE(tld_application_id, question_id, version),
    CONSTRAINT valid_review_status CHECK (review_status IN ('draft', 'ai_reviewed', 'human_reviewed', 'approved', 'needs_revision', 'rejected')),
    CONSTRAINT valid_generation_method CHECK (generation_method IN ('ai_generated', 'human_written', 'hybrid', 'template_filled'))
);

-- Question-Answer Relationship Tracking
CREATE TABLE question_answer_dependencies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- The main question/answer
    primary_question_id UUID NOT NULL REFERENCES application_questions_enhanced(id),
    primary_answer_id UUID REFERENCES application_answers_enhanced(id),
    
    -- The dependent question/answer
    dependent_question_id UUID NOT NULL REFERENCES application_questions_enhanced(id),
    dependent_answer_id UUID REFERENCES application_answers_enhanced(id),
    
    -- Dependency metadata
    dependency_type VARCHAR(50) NOT NULL, -- 'conditional', 'data_source', 'validation', 'cross_reference'
    dependency_rule TEXT, -- Human readable dependency rule
    is_blocking BOOLEAN DEFAULT FALSE, -- Does this dependency block completion?
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- Answer Generation Error Tracking
CREATE TABLE answer_generation_errors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    tld_application_id UUID NOT NULL REFERENCES tld_applications(id),
    question_id UUID NOT NULL REFERENCES application_questions_enhanced(id),
    attempted_answer_id UUID REFERENCES application_answers_enhanced(id),
    
    -- Error Information
    error_type VARCHAR(100) NOT NULL, -- 'missing_data', 'validation_failed', 'ai_generation_failed', 'file_upload_failed'
    error_message TEXT NOT NULL,
    error_details JSONB, -- Structured error information
    
    -- Context
    missing_data_fields TEXT[], -- What data was missing
    available_data_summary JSONB, -- Summary of data that was available
    generation_attempt_count INTEGER DEFAULT 1,
    
    -- Resolution
    resolution_status VARCHAR(50) DEFAULT 'unresolved', -- 'unresolved', 'resolved', 'manually_handled', 'skipped'
    resolution_notes TEXT,
    resolved_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- =====================================================
-- INDEXES FOR PERFORMANCE
-- =====================================================

-- Questions
CREATE INDEX idx_questions_enhanced_number ON application_questions_enhanced(question_number);
CREATE INDEX idx_questions_enhanced_section ON application_questions_enhanced(section_name);
CREATE INDEX idx_questions_enhanced_input_type ON application_questions_enhanced(input_type);
CREATE INDEX idx_questions_enhanced_public ON application_questions_enhanced(is_public);

-- Answers
CREATE INDEX idx_answers_enhanced_application_id ON application_answers_enhanced(tld_application_id);
CREATE INDEX idx_answers_enhanced_question_id ON application_answers_enhanced(question_id);
CREATE INDEX idx_answers_enhanced_review_status ON application_answers_enhanced(review_status);
CREATE INDEX idx_answers_enhanced_generation_method ON application_answers_enhanced(generation_method);
CREATE INDEX idx_answers_enhanced_validation_status ON application_answers_enhanced(validation_status);

-- Dependencies
CREATE INDEX idx_dependencies_primary_question ON question_answer_dependencies(primary_question_id);
CREATE INDEX idx_dependencies_dependent_question ON question_answer_dependencies(dependent_question_id);

-- Errors
CREATE INDEX idx_generation_errors_application ON answer_generation_errors(tld_application_id);
CREATE INDEX idx_generation_errors_question ON answer_generation_errors(question_id);
CREATE INDEX idx_generation_errors_type ON answer_generation_errors(error_type);
CREATE INDEX idx_generation_errors_status ON answer_generation_errors(resolution_status);

-- =====================================================
-- VIEWS FOR EASY QUERYING
-- =====================================================

-- Application completion status with detailed breakdown
CREATE VIEW application_completion_detailed AS
SELECT 
    ta.id as application_id,
    ta.tld_string,
    ta.status as application_status,
    
    -- Question counts
    COUNT(q.id) as total_questions,
    COUNT(a.id) as answered_questions,
    COUNT(CASE WHEN a.validation_status = 'valid' THEN 1 END) as valid_answers,
    COUNT(CASE WHEN a.review_status = 'approved' THEN 1 END) as approved_answers,
    
    -- Completion percentages
    ROUND((COUNT(a.id)::DECIMAL / NULLIF(COUNT(q.id), 0)) * 100, 2) as answer_completion_percentage,
    ROUND((COUNT(CASE WHEN a.validation_status = 'valid' THEN 1 END)::DECIMAL / NULLIF(COUNT(q.id), 0)) * 100, 2) as validation_completion_percentage,
    ROUND((COUNT(CASE WHEN a.review_status = 'approved' THEN 1 END)::DECIMAL / NULLIF(COUNT(q.id), 0)) * 100, 2) as approval_completion_percentage,
    
    -- Quality metrics
    ROUND(AVG(a.completeness_score), 2) as avg_completeness_score,
    ROUND(AVG(a.confidence_score), 2) as avg_confidence_score,
    ROUND(AVG(a.data_availability_score), 2) as avg_data_availability,
    
    -- Error tracking
    COUNT(e.id) as total_errors,
    COUNT(CASE WHEN e.resolution_status = 'unresolved' THEN 1 END) as unresolved_errors
    
FROM tld_applications ta
CROSS JOIN application_questions_enhanced q
LEFT JOIN application_answers_enhanced a ON ta.id = a.tld_application_id AND q.id = a.question_id AND a.version = (
    SELECT MAX(version) FROM application_answers_enhanced a2 
    WHERE a2.tld_application_id = ta.id AND a2.question_id = q.id
)
LEFT JOIN answer_generation_errors e ON ta.id = e.tld_application_id AND q.id = e.question_id
GROUP BY ta.id, ta.tld_string, ta.status;

-- Question readiness assessment (what can be answered with available data)
CREATE VIEW question_readiness_assessment AS
SELECT 
    q.id as question_id,
    q.question_number,
    q.section_name,
    q.sub_section,
    q.question_text,
    q.expected_data_type,
    
    -- Count applications that have tried to answer this question
    COUNT(a.id) as answer_attempts,
    COUNT(CASE WHEN a.validation_status = 'valid' THEN 1 END) as successful_answers,
    COUNT(CASE WHEN e.error_type = 'missing_data' THEN 1 END) as missing_data_errors,
    
    -- Calculate success rate
    ROUND(
        (COUNT(CASE WHEN a.validation_status = 'valid' THEN 1 END)::DECIMAL / NULLIF(COUNT(a.id), 0)) * 100, 
        2
    ) as success_rate_percentage,
    
    -- Average data availability for this question
    ROUND(AVG(a.data_availability_score), 2) as avg_data_availability,
    
    -- Most common missing data fields
    (
        SELECT array_agg(DISTINCT unnest_field)
        FROM (
            SELECT unnest(missing_data_fields) as unnest_field
            FROM application_answers_enhanced 
            WHERE question_id = q.id AND missing_data_fields IS NOT NULL
        ) t
        LIMIT 10
    ) as common_missing_fields
    
FROM application_questions_enhanced q
LEFT JOIN application_answers_enhanced a ON q.id = a.question_id
LEFT JOIN answer_generation_errors e ON q.id = e.question_id
GROUP BY q.id, q.question_number, q.section_name, q.sub_section, q.question_text, q.expected_data_type
ORDER BY q.question_number::INTEGER;

-- Error summary by data type
CREATE VIEW error_summary_by_data_type AS
SELECT 
    q.expected_data_type,
    COUNT(e.id) as total_errors,
    COUNT(CASE WHEN e.error_type = 'missing_data' THEN 1 END) as missing_data_errors,
    COUNT(CASE WHEN e.error_type = 'validation_failed' THEN 1 END) as validation_errors,
    COUNT(CASE WHEN e.error_type = 'ai_generation_failed' THEN 1 END) as generation_errors,
    COUNT(CASE WHEN e.resolution_status = 'unresolved' THEN 1 END) as unresolved_errors,
    
    -- Most common missing data fields for this data type
    (
        SELECT array_agg(DISTINCT unnest_field)
        FROM (
            SELECT unnest(missing_data_fields) as unnest_field
            FROM answer_generation_errors 
            WHERE question_id IN (SELECT id FROM application_questions_enhanced WHERE expected_data_type = q.expected_data_type)
            AND missing_data_fields IS NOT NULL
        ) t
        LIMIT 10
    ) as common_missing_fields
    
FROM application_questions_enhanced q
LEFT JOIN answer_generation_errors e ON q.id = e.question_id
GROUP BY q.expected_data_type
ORDER BY total_errors DESC;

-- ============================================================================
-- Strict per-user Row Level Security on tld_strings (overrides the permissive
-- defaults above). The frontend uses the PUBLIC anon key, so RLS is the only
-- tenant boundary -- scope every row to its owner and drop anonymous fallbacks.
-- ============================================================================
ALTER TABLE tld_strings ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow anonymous access to TLD strings" ON tld_strings;
DROP POLICY IF EXISTS "Users can view their own TLD strings" ON tld_strings;
DROP POLICY IF EXISTS "Users can insert their own TLD strings" ON tld_strings;
DROP POLICY IF EXISTS "Users can update their own TLD strings" ON tld_strings;

CREATE POLICY "tld_strings owner select" ON tld_strings
    FOR SELECT TO authenticated USING (auth.uid() = user_id);
CREATE POLICY "tld_strings owner insert" ON tld_strings
    FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);
CREATE POLICY "tld_strings owner update" ON tld_strings
    FOR UPDATE TO authenticated USING (auth.uid() = user_id);
CREATE POLICY "tld_strings owner delete" ON tld_strings
    FOR DELETE TO authenticated USING (auth.uid() = user_id);

-- Drop the anonymous fallbacks on the child tables so they inherit per-user scoping.
DROP POLICY IF EXISTS "Allow anonymous access to workflow executions" ON workflow_executions;
DROP POLICY IF EXISTS "Allow anonymous access to task executions" ON task_executions;
