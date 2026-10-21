# Policy Assessment Migration

This document describes the database schema updates for enhanced policy assessment capabilities in the TLD Evaluation Platform.

## Overview

The policy assessment migration adds comprehensive support for evaluating TLD strings against ICANN policy requirements, geographic naming conventions, and safeguard obligations. This enhancement supports the new CrewAI workflows for policy analysis.

## New Tables

### 1. Geographic Names Assessments (`geographic_names_assessments`)

Evaluates if a TLD represents geographic locations requiring government approval.

**Key Fields:**
- `is_geographic_name` - Boolean flag for geographic classification
- `geographic_type` - Type of geographic entity (country, territory, capital, city, etc.)
- `specific_matches` - JSONB array of specific geographic matches found
- `major_language_variants` - Analysis of how the string appears in different languages
- `cultural_name_variations` - Cultural and historical name variations
- `transliteration_matches` - Matches found through transliteration analysis
- `documentation_required` - Whether government documentation is needed
- `relevant_authorities` - Government authorities that may need to approve
- `gac_objection_risk` - Risk level for GAC objections (low/medium/high)
- `recommendation` - Final recommendation (proceed/conditional/expert_review)

**Usage:**
```python
from db.policy_assessment_store import save_geographic_names_assessment

assessment_data = {
    "is_geographic_name": True,
    "geographic_type": "country",
    "specific_matches": {"iso_3166": ["US"], "common_names": ["United States"]},
    "gac_objection_risk": "high",
    "recommendation": "expert_review"
}

result = save_geographic_names_assessment(task_execution_id, tld_string, assessment_data)
```

### 2. Safeguard Assessments (`safeguard_assessments`)

Analyzes TLD strings against ICANN's mandatory safeguard questions (Q175-Q180).

**Key Fields:**
- `q175_consumer_trust` through `q180_government_function` - Boolean responses to ICANN questions
- `q175_reasoning` through `q180_reasoning` - Detailed reasoning for each answer
- `safeguards_1_3_required` - Whether Safeguards 1.3 (verification) are required
- `safeguards_1_8_required` - Whether Safeguards 1.8 (restrictions) are required  
- `safeguards_1_9_required` - Whether Safeguards 1.9 (licensing) are required
- `safeguards_special_required` - Whether special safeguards are needed
- `alternative_meanings` - JSONB analysis of alternative meanings in different languages
- `cultural_sensitivities` - Cultural sensitivity analysis
- `safeguard_risk_level` - Overall safeguard risk (none/standard/high/special)

**ICANN Questions Covered:**
- **Q175**: Does the applied-for gTLD string closely resemble a term that would enhance consumer trust?
- **Q176**: Could the applied-for gTLD string be used to mislead or harm consumers?
- **Q177**: Does the applied-for gTLD string require licensing or authorization?
- **Q178**: Does the applied-for gTLD string require government oversight?
- **Q179**: Could the applied-for gTLD string be used for harassment?
- **Q180**: Does the applied-for gTLD string represent a government function?

### 3. Enhanced GAC Risk Results

Adds new columns to the existing `gac_risk_results` table for enhanced policy analysis:

**New Fields:**
- `pattern_match_risk` - Risk from pattern matching analysis
- `multi_government_risk` - Risk from multi-government concerns
- `religious_sensitivities` - JSONB analysis of religious concerns
- `ethnic_cultural_concerns` - JSONB analysis of ethnic/cultural issues
- `political_terminology` - JSONB analysis of political terms
- `historical_conflicts` - JSONB analysis of historical conflict associations
- `diplomatic_strategy` - Recommended diplomatic engagement approach
- `key_stakeholders` - JSONB list of key stakeholders to engage
- `expert_consultation_required` - Whether expert consultation is needed

## Migration Files

### 1. `add_policy_assessment_tables.sql`
Main migration script that:
- Creates the new tables with proper constraints
- Adds indexes for performance
- Sets up Row Level Security (RLS) policies
- Creates utility functions
- Updates task definitions

### 2. `apply_policy_assessment_migration.py`
Python script to apply the migration:
```bash
cd db
python apply_policy_assessment_migration.py
```

### 3. `policy_assessment_store.py`
Data access layer providing:
- Save/retrieve functions for each table
- Comprehensive policy assessment queries
- Dashboard statistics
- Search and filtering capabilities

## Key Features

### 1. Comprehensive Policy Assessment Function

```sql
SELECT * FROM get_policy_assessment_summary('example');
```

Returns a unified view of all policy risks for a TLD string.

### 2. Dashboard Statistics

```python
from db.policy_assessment_store import get_policy_assessment_dashboard_data
stats = get_policy_assessment_dashboard_data()
```

### 3. Advanced Search and Filtering

```python
from db.policy_assessment_store import search_policy_assessments

filters = {
    "assessment_type": "geographic",
    "is_geographic": True,
    "gac_risk": "high"
}
results = search_policy_assessments(filters)
```

## Integration with CrewAI Workflows

The new tables support enhanced CrewAI workflows:

1. **Geographic Name Assessment Task** - Populates `geographic_names_assessments`
2. **Safeguard Assessment Task** - Populates `safeguard_assessments`  
3. **GAC Risk Analysis Task** - Updates `gac_risk_results` with enhanced fields

## Security

- Row Level Security (RLS) enabled on all new tables
- Policies allow users to access their own data and anonymous data
- Proper foreign key constraints to `task_executions`

## Performance

- Comprehensive indexing on key lookup fields
- JSONB indexes for complex queries
- Optimized queries for dashboard views

## Migration Verification

After running the migration, verify success:

```sql
-- Check new tables exist
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('geographic_names_assessments', 'safeguard_assessments');

-- Check new columns added
SELECT column_name FROM information_schema.columns 
WHERE table_schema = 'public' 
AND table_name = 'gac_risk_results'
AND column_name IN ('pattern_match_risk', 'multi_government_risk', 'expert_consultation_required');

-- Test utility function
SELECT get_policy_assessment_summary('test');
```

## Usage Examples

### Complete Assessment Workflow

```python
from db.policy_assessment_store import (
    save_geographic_names_assessment,
    save_safeguard_assessment,
    update_gac_risk_assessment,
    get_comprehensive_policy_assessment
)

# Save geographic assessment
geo_data = {
    "is_geographic_name": True,
    "geographic_type": "country",
    "gac_objection_risk": "high"
}
save_geographic_names_assessment(task_id, tld, geo_data)

# Save safeguard assessment  
safeguard_data = {
    "q175_consumer_trust": True,
    "q175_reasoning": "String enhances consumer trust in financial services",
    "safeguards_1_3_required": True,
    "safeguard_risk_level": "standard"
}
save_safeguard_assessment(task_id, tld, safeguard_data)

# Update GAC assessment with enhanced data
gac_data = {
    "pattern_match_risk": "medium",
    "expert_consultation_required": True
}
update_gac_risk_assessment(task_id, gac_data)

# Get comprehensive summary
summary = get_comprehensive_policy_assessment(tld)
```

## Next Steps

1. **Apply Migration**: Run `apply_policy_assessment_migration.py`
2. **Update CrewAI Tasks**: Modify task implementations to save data to new tables
3. **Update Frontend**: Add new policy assessment views to the dashboard
4. **Testing**: Verify end-to-end workflow with sample TLD strings

## Support

For questions or issues with the migration:
1. Check the migration logs for any errors
2. Verify environment variables are set correctly
3. Ensure Supabase connection is working
4. Review the RLS policies if access issues occur 