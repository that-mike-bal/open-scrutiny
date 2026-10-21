-- Migration: Add missing entity columns to applicants table
-- Aligned with 2026 ICANN Applicant Guidebook Q1-48

ALTER TABLE applicants
ADD COLUMN IF NOT EXISTS dba_name VARCHAR(255),                    -- Q2
ADD COLUMN IF NOT EXISTS tax_id VARCHAR(100),                       -- Q5
ADD COLUMN IF NOT EXISTS tax_id_issuing_authority VARCHAR(255),     -- Q6
ADD COLUMN IF NOT EXISTS lei VARCHAR(20),                           -- Q7 (Legal Entity Identifier)
ADD COLUMN IF NOT EXISTS is_existing_registry_operator BOOLEAN,     -- Q11
ADD COLUMN IF NOT EXISTS registry_relationship_explanation TEXT,     -- Q12
ADD COLUMN IF NOT EXISTS is_rsp_or_provider BOOLEAN,                -- Q13
ADD COLUMN IF NOT EXISTS rsp_affiliate_explanation TEXT,             -- Q14
ADD COLUMN IF NOT EXISTS stock_symbol VARCHAR(20),                  -- Q15
ADD COLUMN IF NOT EXISTS stock_exchange VARCHAR(100),               -- Q16

-- Primary Business Address (structured, not a single text blob)
ADD COLUMN IF NOT EXISTS address_line1 VARCHAR(255),                -- Q20
ADD COLUMN IF NOT EXISTS address_line2 VARCHAR(255),                -- Q21
ADD COLUMN IF NOT EXISTS city VARCHAR(100),                         -- Q22
ADD COLUMN IF NOT EXISTS state_province VARCHAR(100),               -- Q23
ADD COLUMN IF NOT EXISTS postal_code VARCHAR(20),                   -- Q24
ADD COLUMN IF NOT EXISTS country_code VARCHAR(10),                  -- Q25

-- Direct Parent Company (Q26-35)
ADD COLUMN IF NOT EXISTS parent_company_name VARCHAR(255),          -- Q26
ADD COLUMN IF NOT EXISTS parent_company_dba VARCHAR(255),           -- Q27
ADD COLUMN IF NOT EXISTS parent_company_entity_type VARCHAR(100),   -- Q28
ADD COLUMN IF NOT EXISTS parent_company_jurisdiction VARCHAR(100),  -- Q29
ADD COLUMN IF NOT EXISTS parent_company_address JSONB,              -- Q30-35 (structured)

-- Ultimate Parent Company (Q36-45)
ADD COLUMN IF NOT EXISTS ultimate_parent_name VARCHAR(255),         -- Q36
ADD COLUMN IF NOT EXISTS ultimate_parent_dba VARCHAR(255),          -- Q37
ADD COLUMN IF NOT EXISTS ultimate_parent_entity_type VARCHAR(100),  -- Q38
ADD COLUMN IF NOT EXISTS ultimate_parent_jurisdiction VARCHAR(100), -- Q39
ADD COLUMN IF NOT EXISTS ultimate_parent_address JSONB,             -- Q40-45 (structured)

-- Legal attestations
ADD COLUMN IF NOT EXISTS has_unique_legal_issues BOOLEAN,           -- Q47
ADD COLUMN IF NOT EXISTS legal_issues_explanation TEXT;              -- Q48

-- Comments
COMMENT ON COLUMN applicants.lei IS 'Legal Entity Identifier (ISO 17442) - Q7';
COMMENT ON COLUMN applicants.parent_company_address IS 'Structured address JSONB: {line1, line2, city, state, postal_code, country}';
COMMENT ON COLUMN applicants.ultimate_parent_address IS 'Structured address JSONB: {line1, line2, city, state, postal_code, country}';
