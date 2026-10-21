-- Migration: create_application_entity_tables.sql
-- Purpose: Add relational entity tables for repeatable application entities
--          and boolean flags for routing question state.

-- =========================================================================
-- 1. Application Users (Set 2, Q49-64)
-- =========================================================================
CREATE TABLE IF NOT EXISTS application_users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id UUID NOT NULL REFERENCES tld_applications(id) ON DELETE CASCADE,
  user_role VARCHAR(50) NOT NULL,  -- 'primary_contact', 'technical_contact', 'admin_contact', etc.
  sort_order INTEGER DEFAULT 0,

  -- Identity (Q49-52 equivalent)
  first_name VARCHAR(255),
  last_name VARCHAR(255),
  title VARCHAR(255),
  organization VARCHAR(255),

  -- Address (Q53-58 equivalent)
  address_line1 VARCHAR(255),
  address_line2 VARCHAR(255),
  city VARCHAR(255),
  state_province VARCHAR(255),
  postal_code VARCHAR(50),
  country_code VARCHAR(10),

  -- Contact (Q59-64 equivalent)
  phone_country_code VARCHAR(10),
  phone_number VARCHAR(50),
  phone_extension VARCHAR(20),
  fax_number VARCHAR(50),
  email VARCHAR(255),

  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_app_users_application ON application_users(application_id);

-- =========================================================================
-- 2. Application Payors (Set 3a, Q65-76 equivalent)
-- =========================================================================
CREATE TABLE IF NOT EXISTS application_payors (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id UUID NOT NULL REFERENCES tld_applications(id) ON DELETE CASCADE,
  payor_role VARCHAR(50) DEFAULT 'primary',
  sort_order INTEGER DEFAULT 0,

  -- Identity
  payor_name VARCHAR(255),
  payor_organization VARCHAR(255),

  -- Address
  address_line1 VARCHAR(255),
  address_line2 VARCHAR(255),
  city VARCHAR(255),
  state_province VARCHAR(255),
  postal_code VARCHAR(50),
  country_code VARCHAR(10),

  -- Contact
  phone_country_code VARCHAR(10),
  phone_number VARCHAR(50),
  email VARCHAR(255),

  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_app_payors_application ON application_payors(application_id);

-- =========================================================================
-- 3. Financial Institutions (Set 3b, Q75-90 equivalent)
-- =========================================================================
CREATE TABLE IF NOT EXISTS application_financial_institutions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id UUID NOT NULL REFERENCES tld_applications(id) ON DELETE CASCADE,
  institution_role VARCHAR(50) DEFAULT 'primary',
  sort_order INTEGER DEFAULT 0,

  institution_name VARCHAR(255),
  branch_name VARCHAR(255),
  swift_bic VARCHAR(20),
  account_name VARCHAR(255),
  account_number_last4 VARCHAR(4),  -- Never store full account numbers

  -- Address
  address_line1 VARCHAR(255),
  address_line2 VARCHAR(255),
  city VARCHAR(255),
  state_province VARCHAR(255),
  postal_code VARCHAR(50),
  country_code VARCHAR(10),

  -- Contact
  contact_name VARCHAR(255),
  phone_number VARCHAR(50),
  email VARCHAR(255),

  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_app_fi_application ON application_financial_institutions(application_id);

-- =========================================================================
-- 4. Billing Contacts (Set 3c, Q91-103 equivalent)
-- =========================================================================
CREATE TABLE IF NOT EXISTS application_billing_contacts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id UUID NOT NULL REFERENCES tld_applications(id) ON DELETE CASCADE,
  contact_role VARCHAR(50) DEFAULT 'primary',
  sort_order INTEGER DEFAULT 0,

  first_name VARCHAR(255),
  last_name VARCHAR(255),
  title VARCHAR(255),
  organization VARCHAR(255),

  address_line1 VARCHAR(255),
  address_line2 VARCHAR(255),
  city VARCHAR(255),
  state_province VARCHAR(255),
  postal_code VARCHAR(50),
  country_code VARCHAR(10),

  phone_country_code VARCHAR(10),
  phone_number VARCHAR(50),
  email VARCHAR(255),

  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_app_bc_application ON application_billing_contacts(application_id);

-- =========================================================================
-- 5. Application Flags on tld_applications
-- =========================================================================
ALTER TABLE tld_applications
  ADD COLUMN IF NOT EXISTS is_reserved_name BOOLEAN DEFAULT false,
  ADD COLUMN IF NOT EXISTS has_variant_strings BOOLEAN DEFAULT false,
  ADD COLUMN IF NOT EXISTS has_voluntary_commitments BOOLEAN DEFAULT false,
  ADD COLUMN IF NOT EXISTS financial_profile_type VARCHAR(50);
  -- financial_profile_type: 'government' | 'registry_operator' | 'top25' | 'standard'
