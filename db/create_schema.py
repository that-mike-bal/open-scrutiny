#!/usr/bin/env python3
"""
Script to create the comprehensive database schema for the TLD evaluation platform.
This supports the new multi-stage workflow with use case discovery and portfolio strategy.
"""

schema_sql = """-- =====================================================
-- TLD Evaluation Platform - Comprehensive Database Schema
-- =====================================================
-- 
-- This schema supports the new multi-stage workflow:
-- 1. Use Case Discovery (StrategicIdeationAgent)
-- 2. Parallel Business Case Analysis (Business Case Agents)
-- 3. Portfolio Strategy Synthesis (PortfolioStrategyAgent)
--
-- Version: 2.0
-- Created: 2024
-- =====================================================

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- MAIN EVALUATION TRACKING TABLES
-- =====================================================

-- Main table to track each overall evaluation request
CREATE TABLE tld_evaluations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id),
    tld_string TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING', -- PENDING, RUNNING, COMPLETED, FAILED
    workflow_type TEXT NOT NULL DEFAULT 'use_case_driven', -- use_case_driven, business_case_only, icann_compliance
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    execution_time_minutes INTEGER,
    
    -- Store the final top-level recommendation here
    final_recommendation JSONB,
    
    -- Store the initial discovery results here
    discovery_results JSONB,
    
    -- Store workflow metadata
    workflow_metadata JSONB DEFAULT '{}',
    
    -- Error tracking
    error_message TEXT,
    error_stage TEXT,
    
    -- Indexing for performance
    CONSTRAINT valid_status CHECK (status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED')),
    CONSTRAINT valid_workflow_type CHECK (workflow_type IN ('use_case_driven', 'business_case_only', 'icann_compliance'))
);

-- Child table to store the detailed analysis for EACH use case
CREATE TABLE use_case_analyses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tld_evaluation_id UUID NOT NULL REFERENCES tld_evaluations(id) ON DELETE CASCADE,
    use_case TEXT NOT NULL,
    use_case_rank INTEGER, -- Rank from discovery phase (1 = highest priority)
    status TEXT NOT NULL DEFAULT 'PENDING', -- PENDING, RUNNING, COMPLETED, FAILED
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    completed_at TIMESTAMP WITH TIME ZONE,
    execution_time_minutes INTEGER,
    
    -- Store the full report from business case analysis here
    full_report JSONB,
    
    -- Store key metrics for easy querying and comparison
    overall_business_score INTEGER CHECK (overall_business_score >= 0 AND overall_business_score <= 100),
    market_potential_score INTEGER CHECK (market_potential_score >= 0 AND market_potential_score <= 100),
    financial_viability_score INTEGER CHECK (financial_viability_score >= 0 AND financial_viability_score <= 100),
    competitive_position_score INTEGER CHECK (competitive_position_score >= 0 AND competitive_position_score <= 100),
    risk_score INTEGER CHECK (risk_score >= 0 AND risk_score <= 100),
    
    -- Business recommendation category
    final_recommendation_category TEXT, -- HIGHLY_RECOMMENDED, RECOMMENDED, PROCEED_WITH_CAUTION, NOT_RECOMMENDED
    confidence_level TEXT DEFAULT 'MEDIUM', -- LOW, MEDIUM, HIGH
    
    -- Financial projections (extracted for easy querying)
    estimated_revenue_y1_usd DECIMAL(15,2),
    estimated_revenue_y5_usd DECIMAL(15,2),
    break_even_registrations INTEGER,
    break_even_timeframe_months INTEGER,
    roi_projection_percent DECIMAL(5,2),
    estimated_investment_usd DECIMAL(15,2),
    
    -- Market metrics
    estimated_market_size_usd DECIMAL(15,2),
    projected_registrations_y1 INTEGER,
    projected_registrations_y5 INTEGER,
    market_growth_rate_percent DECIMAL(5,2),
    
    -- Risk assessment
    overall_risk_level TEXT DEFAULT 'UNKNOWN', -- LOW, MEDIUM, HIGH, CRITICAL, UNKNOWN
    regulatory_risk_score INTEGER CHECK (regulatory_risk_score >= 0 AND regulatory_risk_score <= 100),
    market_risk_score INTEGER CHECK (market_risk_score >= 0 AND market_risk_score <= 100),
    operational_risk_score INTEGER CHECK (operational_risk_score >= 0 AND operational_risk_score <= 100),
    
    -- Error tracking
    error_message TEXT,
    
    CONSTRAINT valid_status CHECK (status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED')),
    CONSTRAINT valid_recommendation CHECK (final_recommendation_category IN ('HIGHLY_RECOMMENDED', 'RECOMMENDED', 'PROCEED_WITH_CAUTION', 'NOT_RECOMMENDED')),
    CONSTRAINT valid_confidence CHECK (confidence_level IN ('LOW', 'MEDIUM', 'HIGH')),
    CONSTRAINT valid_risk_level CHECK (overall_risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL', 'UNKNOWN'))
);

-- =====================================================
-- PORTFOLIO STRATEGY & SYNTHESIS TABLES
-- =====================================================

-- Store portfolio strategy synthesis results
CREATE TABLE portfolio_strategies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tld_evaluation_id UUID NOT NULL REFERENCES tld_evaluations(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    
    -- Strategic recommendations
    primary_strategy_type TEXT, -- Single Use Case Focus, Dual Strategy, Portfolio Approach
    recommended_use_cases TEXT[], -- Array of recommended use case names
    strategic_rationale TEXT,
    
    -- Implementation strategy
    implementation_phases JSONB, -- Structured phase-by-phase implementation plan
    
    -- Portfolio analysis results
    portfolio_analysis_summary JSONB,
    individual_use_case_rankings JSONB, -- Ranked list with scores and rationale
    
    -- Synthesis metadata
    total_use_cases_analyzed INTEGER,
    confidence_level TEXT DEFAULT 'MEDIUM',
    recommendation_strength TEXT DEFAULT 'MODERATE', -- WEAK, MODERATE, STRONG
    
    -- Full synthesis report
    full_synthesis_report JSONB,
    
    CONSTRAINT valid_confidence CHECK (confidence_level IN ('LOW', 'MEDIUM', 'HIGH')),
    CONSTRAINT valid_strength CHECK (recommendation_strength IN ('WEAK', 'MODERATE', 'STRONG'))
);

-- =====================================================
-- DETAILED BUSINESS ANALYSIS TABLES
-- =====================================================

-- Store detailed business metrics for advanced analytics
CREATE TABLE business_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    use_case_analysis_id UUID NOT NULL REFERENCES use_case_analyses(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    
    -- Market metrics
    market_opportunity_score INTEGER CHECK (market_opportunity_score >= 0 AND market_opportunity_score <= 100),
    estimated_market_size_usd DECIMAL(15,2),
    market_growth_rate_percent DECIMAL(5,2),
    target_market_segments TEXT[],
    
    -- Competitive metrics
    competitive_position_score INTEGER CHECK (competitive_position_score >= 0 AND competitive_position_score <= 100),
    direct_competitors_count INTEGER DEFAULT 0,
    competitive_advantage_score INTEGER CHECK (competitive_advantage_score >= 0 AND competitive_advantage_score <= 100),
    market_differentiation_score INTEGER CHECK (market_differentiation_score >= 0 AND market_differentiation_score <= 100),
    
    -- Financial metrics
    financial_viability_score INTEGER CHECK (financial_viability_score >= 0 AND financial_viability_score <= 100),
    estimated_total_investment_usd DECIMAL(15,2),
    estimated_annual_operating_cost_usd DECIMAL(15,2),
    estimated_time_to_market_months INTEGER,
    
    -- Risk metrics (detailed)
    risk_adjusted_score INTEGER CHECK (risk_adjusted_score >= 0 AND risk_adjusted_score <= 100),
    primary_risks_identified TEXT[],
    risk_mitigation_strategies TEXT[],
    
    -- Additional structured data
    key_success_factors TEXT[],
    critical_assumptions TEXT[],
    data_quality_score INTEGER CHECK (data_quality_score >= 0 AND data_quality_score <= 100)
);

-- Store qualitative business insights
CREATE TABLE business_insights (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    use_case_analysis_id UUID NOT NULL REFERENCES use_case_analyses(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    
    -- Market intelligence insights
    relevant_trends TEXT[],
    market_drivers TEXT[],
    target_market_analysis TEXT,
    demand_indicators TEXT[],
    
    -- Competitive landscape
    competitive_positioning TEXT,
    key_competitors TEXT[],
    competitive_advantages TEXT[],
    market_gaps_identified TEXT[],
    
    -- Adoption assessment
    adoption_drivers TEXT[],
    adoption_barriers TEXT[],
    adoption_timeline_assessment TEXT,
    early_adopter_segments TEXT[],
    
    -- Strategic recommendations
    go_to_market_strategy TEXT,
    pricing_strategy_recommendations TEXT[],
    partnership_opportunities TEXT[],
    marketing_strategy_recommendations TEXT[],
    
    -- Supporting data
    data_sources_consulted TEXT[],
    key_research_findings TEXT[],
    benchmark_comparisons TEXT[],
    expert_opinions TEXT[],
    
    -- Investment considerations
    funding_requirements TEXT,
    investment_risks TEXT[],
    return_expectations TEXT,
    exit_strategy_considerations TEXT[]
);

-- =====================================================
-- WORKFLOW EXECUTION TRACKING
-- =====================================================

-- Track individual workflow stages and their execution
CREATE TABLE workflow_stages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tld_evaluation_id UUID NOT NULL REFERENCES tld_evaluations(id) ON DELETE CASCADE,
    stage_name TEXT NOT NULL, -- use_case_discovery, business_case_analysis, portfolio_synthesis
    stage_order INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    execution_time_seconds INTEGER,
    
    -- Agent information
    agent_type TEXT, -- StrategicIdeationAgent, BusinessCaseAgents, PortfolioStrategyAgent
    agent_version TEXT DEFAULT '1.0',
    
    -- Stage-specific data
    stage_input JSONB,
    stage_output JSONB,
    stage_metadata JSONB DEFAULT '{}',
    
    -- Error tracking
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    CONSTRAINT valid_stage_status CHECK (status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'SKIPPED')),
    CONSTRAINT valid_stage_name CHECK (stage_name IN ('use_case_discovery', 'business_case_analysis', 'portfolio_synthesis'))
);

-- =====================================================
-- INDEXES FOR PERFORMANCE
-- =====================================================

-- Primary lookup indexes
CREATE INDEX idx_tld_evaluations_user_id ON tld_evaluations(user_id);
CREATE INDEX idx_tld_evaluations_tld_string ON tld_evaluations(tld_string);
CREATE INDEX idx_tld_evaluations_status ON tld_evaluations(status);
CREATE INDEX idx_tld_evaluations_created_at ON tld_evaluations(created_at);

-- Use case analysis indexes
CREATE INDEX idx_use_case_analyses_tld_evaluation_id ON use_case_analyses(tld_evaluation_id);
CREATE INDEX idx_use_case_analyses_use_case ON use_case_analyses(use_case);
CREATE INDEX idx_use_case_analyses_recommendation ON use_case_analyses(final_recommendation_category);
CREATE INDEX idx_use_case_analyses_scores ON use_case_analyses(overall_business_score, market_potential_score, financial_viability_score);

-- Portfolio strategy indexes
CREATE INDEX idx_portfolio_strategies_tld_evaluation_id ON portfolio_strategies(tld_evaluation_id);
CREATE INDEX idx_portfolio_strategies_strategy_type ON portfolio_strategies(primary_strategy_type);

-- Workflow tracking indexes
CREATE INDEX idx_workflow_stages_tld_evaluation_id ON workflow_stages(tld_evaluation_id);
CREATE INDEX idx_workflow_stages_stage_name ON workflow_stages(stage_name);
CREATE INDEX idx_workflow_stages_status ON workflow_stages(status);

-- Business metrics indexes
CREATE INDEX idx_business_metrics_use_case_analysis_id ON business_metrics(use_case_analysis_id);
CREATE INDEX idx_business_insights_use_case_analysis_id ON business_insights(use_case_analysis_id);

-- =====================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- =====================================================

-- Enable RLS on all user-facing tables
ALTER TABLE tld_evaluations ENABLE ROW LEVEL SECURITY;
ALTER TABLE use_case_analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE portfolio_strategies ENABLE ROW LEVEL SECURITY;
ALTER TABLE business_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE business_insights ENABLE ROW LEVEL SECURITY;
ALTER TABLE workflow_stages ENABLE ROW LEVEL SECURITY;

-- RLS Policies for tld_evaluations
CREATE POLICY "Users can view their own evaluations" ON tld_evaluations
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own evaluations" ON tld_evaluations
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own evaluations" ON tld_evaluations
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own evaluations" ON tld_evaluations
    FOR DELETE USING (auth.uid() = user_id);

-- RLS Policies for use_case_analyses (inherit from parent tld_evaluations)
CREATE POLICY "Users can view their own use case analyses" ON use_case_analyses
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM tld_evaluations 
            WHERE tld_evaluations.id = use_case_analyses.tld_evaluation_id 
            AND tld_evaluations.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can insert their own use case analyses" ON use_case_analyses
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM tld_evaluations 
            WHERE tld_evaluations.id = use_case_analyses.tld_evaluation_id 
            AND tld_evaluations.user_id = auth.uid()
        )
    );

-- =====================================================
-- UTILITY FUNCTIONS
-- =====================================================

-- Function to calculate overall business score
CREATE OR REPLACE FUNCTION calculate_overall_business_score(
    market_score INTEGER,
    financial_score INTEGER,
    competitive_score INTEGER,
    risk_score INTEGER
) RETURNS INTEGER AS $$
BEGIN
    -- Weighted average: Market 30%, Financial 25%, Competitive 25%, Risk 20%
    RETURN ROUND(
        (market_score * 0.30 + 
         financial_score * 0.25 + 
         competitive_score * 0.25 + 
         risk_score * 0.20)::NUMERIC
    );
END;
$$ LANGUAGE plpgsql;

-- Function to get evaluation summary statistics
CREATE OR REPLACE FUNCTION get_evaluation_summary(evaluation_id UUID)
RETURNS TABLE(
    tld_string TEXT,
    total_use_cases INTEGER,
    completed_use_cases INTEGER,
    avg_business_score DECIMAL,
    top_recommendation TEXT,
    evaluation_status TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        te.tld_string,
        COUNT(uca.id)::INTEGER as total_use_cases,
        COUNT(CASE WHEN uca.status = 'COMPLETED' THEN 1 END)::INTEGER as completed_use_cases,
        AVG(uca.overall_business_score) as avg_business_score,
        (SELECT uca2.use_case FROM use_case_analyses uca2 
         WHERE uca2.tld_evaluation_id = evaluation_id 
         ORDER BY uca2.overall_business_score DESC NULLS LAST 
         LIMIT 1) as top_recommendation,
        te.status as evaluation_status
    FROM tld_evaluations te
    LEFT JOIN use_case_analyses uca ON te.id = uca.tld_evaluation_id
    WHERE te.id = evaluation_id
    GROUP BY te.id, te.tld_string, te.status;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- VIEWS FOR COMMON QUERIES
-- =====================================================

-- View for evaluation dashboard
CREATE VIEW evaluation_dashboard AS
SELECT 
    te.id,
    te.tld_string,
    te.status,
    te.created_at,
    te.execution_time_minutes,
    COUNT(uca.id) as total_use_cases,
    COUNT(CASE WHEN uca.status = 'COMPLETED' THEN 1 END) as completed_use_cases,
    AVG(uca.overall_business_score) as avg_business_score,
    MAX(uca.overall_business_score) as max_business_score,
    ps.primary_strategy_type,
    ps.confidence_level as strategy_confidence
FROM tld_evaluations te
LEFT JOIN use_case_analyses uca ON te.id = uca.tld_evaluation_id
LEFT JOIN portfolio_strategies ps ON te.id = ps.tld_evaluation_id
GROUP BY te.id, te.tld_string, te.status, te.created_at, te.execution_time_minutes, 
         ps.primary_strategy_type, ps.confidence_level;

-- View for use case comparison
CREATE VIEW use_case_comparison AS
SELECT 
    te.tld_string,
    uca.use_case,
    uca.use_case_rank,
    uca.overall_business_score,
    uca.market_potential_score,
    uca.financial_viability_score,
    uca.competitive_position_score,
    uca.risk_score,
    uca.final_recommendation_category,
    uca.estimated_revenue_y5_usd,
    uca.roi_projection_percent,
    uca.break_even_timeframe_months,
    uca.overall_risk_level
FROM use_case_analyses uca
JOIN tld_evaluations te ON uca.tld_evaluation_id = te.id
WHERE uca.status = 'COMPLETED'
ORDER BY te.tld_string, uca.overall_business_score DESC;

-- =====================================================
-- SCHEMA VERSION TRACKING
-- =====================================================

CREATE TABLE schema_versions (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    description TEXT
);

INSERT INTO schema_versions (version, description) 
VALUES ('2.0', 'Multi-stage TLD evaluation workflow with use case discovery and portfolio strategy');
"""

if __name__ == "__main__":
    # Write the schema to schema.sql file
    with open("schema.sql", "w") as f:
        f.write(schema_sql)
    
    print("✅ Database schema created successfully in db/schema.sql")
    print("\n📋 Schema Summary:")
    print("- Main evaluation tracking: tld_evaluations")
    print("- Use case analysis: use_case_analyses") 
    print("- Portfolio strategy: portfolio_strategies")
    print("- Business metrics: business_metrics")
    print("- Business insights: business_insights")
    print("- Workflow tracking: workflow_stages")
    print("- Performance indexes and RLS policies included")
    print("- Utility functions and views for common queries") 