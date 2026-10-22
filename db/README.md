# Database Schema

**Target:** Supabase (Postgres 15+). Deploy with `db/schema.sql`; see "Database setup" below.

---

## Overview

This database supports two major subsystems:
1. **Evaluation** — CrewAI multi-agent risk assessment (in the bundled example: TLD strings)
2. **ICANN Application Management** — Generating and managing ICANN gTLD application responses

### Architecture
- **Backend**: FastAPI (`crewai_service/app.py`) + Supabase (Postgres)
- **Frontend**: React + Vite + TypeScript, queries Supabase directly via PostgREST
- **DB Access**: Two Supabase clients — `crewai_service/utils/supabase_client.py` (SupabaseClient) and `db/supabase_client.py` (DatabaseSupabaseClient)
- **Store Layer**: `db/tld_application_store.py` (TldApplicationStore)

---

## Database setup (bring your own — Supabase recommended)

This app needs a PostgreSQL database. We recommend **[Supabase](https://supabase.com)**
(free tier) — it provides Postgres, auth, and the PostgREST API the frontend uses.
Any Postgres works, but the frontend's anon-key access and the Row Level Security
policies assume Supabase's `auth.users` / `auth.uid()`.

Deploy to a fresh project in this order:

1. **Deploy the schema (empty — no data).** Run [`db/schema.sql`](schema.sql) in the
   Supabase SQL editor (or `psql`). It creates every table — including strict
   per-user RLS on `tld_strings` — and seeds no data. This is the single
   deployable starting point; `db/create_schema.py` predates it and is kept only
   for reference.
2. **Apply incremental updates** — run the `db/migrations/*.sql` files in this
   order (they add columns/tables on top of the base schema):
   1. `create_application_entity_tables.sql`
   2. `update_applicants_table.sql`
   3. `add_applicability_and_question_sets.sql`
   4. `add_question_categories.sql`
   5. `add_generation_context.sql`
   6. `add_string_type.sql`
   7. `add_tld_strings_error_message.sql`
   8. `update_application_statuses.sql`
   9. `add_evaluation_snapshots.sql`
   10. `add_audit_logs_table.sql`
3. **Seed the example ruleset (no applicant data)** — `python scripts/categorize_questions.py`
   (and `scripts/reconcile_questions.py` if you re-import question data).
4. **Build the RAG index** — `python scripts/setup_rag_database.py`, which loads
   the sample knowledge base (`data/example_registry_knowledgebase.md`) and the
   reference datasets in `data/`.
5. **Guidebook index (optional)** — the evaluation agents' `guidebook_search`
   tool reads `guidebook_section` rows in `rag_content`. Load them from the
   public *ICANN Applicant Guidebook* PDF (not bundled; large and ICANN's) with
   `python db/populate_guidebook_embeddings.py --pdf-path <pdf> --clear-existing`.
   Without them the tool returns a clear "no sections found" message and the
   evaluation continues. Full detail: [docs/KNOWLEDGE_BASE.md](../docs/KNOWLEDGE_BASE.md).

The end-to-end boot ("a fresh clone runs an evaluation") is an acceptance check
to run after you've provisioned a backend and filled `.env` — not something the
repo can prove on its own.

---

## Active Tables (38 tables + 6 views)

### Core Evaluation Tables

#### `tld_strings` — Main evaluation records
| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `user_id` | UUID FK → auth.users | |
| `tld_string` | TEXT | Lowercase TLD string |
| `use_case` | TEXT | User-provided use case description |
| `workflow_type` | TEXT | e.g. `binary_compliance_check` |
| `overall_status` | TEXT | `PENDING`, `RUNNING`, `COMPLETED`, `FAILED` |
| `generated_report` | JSONB | AI-generated feasibility report |
| `string_type` | TEXT | `primary` or `secondary` |
| `error_message` | TEXT | Error details if evaluation failed |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |
| `completed_at` | TIMESTAMPTZ | |


#### `task_executions` — Individual CrewAI task results
| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `tld_string_id` | UUID FK → tld_strings | |
| `task_definition_id` | UUID FK → task_definitions | |
| `task_name` | TEXT | e.g. `global_trademark_assessment` |
| `status` | TEXT | `PENDING`, `COMPLETED`, `FAILED` |
| `result_status` | TEXT | `CLEAR`, `PASS`, `FAIL`, `FLAGGED`, etc. |
| `result_data` | JSONB | Rich output (see structure below) |
| `confidence_score` | NUMERIC | |
| `agent_name` | TEXT | CrewAI agent that executed |
| `workflow_id` | UUID | Links to workflow_executions |
| `workflow_type` | TEXT | |
| `error_message` | TEXT | |
| `execution_time_seconds` | INTEGER | |
| `started_at`, `completed_at`, `created_at`, `updated_at` | TIMESTAMPTZ | |

**`result_data` JSONB structure:**
```json
{
  "output": "# Formatted markdown report...",
  "raw_output": "# Same content (client compat)...",
  "full_output": "# Same content (client compat)...",
  "summary": "Task finished.",
  "workflow_context": "legal_risk_assessment",
  "evaluation_metadata": {
    "tld_string": "join",
    "use_case": "...",
    "task_index": 1,
    "total_tasks": 3
  },
  "api_call_log": [
    {"tool_name": "EnhancedTrademarkCheckerTool", "api_endpoint": "...", "status_code": 200, "response_time_ms": 533.7}
  ],
  "tool_execution_summary": {
    "EnhancedTrademarkCheckerTool": {"total_calls": 13, "failed_calls": 0, "all_data_is_real": true},
    "overall": {"total_api_calls": 14, "data_reliability": "PARTIAL"}
  },
  "trademark_audit_log": [
    {"title": "...", "url": "...", "relevant": true, "extracted_name": "JOIN", "similarity": 0.85, "filter_reason": null}
  ]
}
```

#### `workflow_executions` — Workflow-level tracking
| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `tld_string_id` | UUID FK → tld_strings | |
| `workflow_type` | TEXT | `technical_risk_assessment`, `legal_risk_assessment`, `policy_safeguard_review` |
| `status` | TEXT | |
| `started_at`, `completed_at` | TIMESTAMPTZ | |
| `created_by` | UUID | |
| `planned_tasks`, `completed_tasks`, `failed_tasks` | TEXT[] | |

#### `task_definitions` — Task metadata registry
| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `task_name` | TEXT UNIQUE | e.g. `dns_stability_assessment` |
| `task_category` | TEXT | |
| `description` | TEXT | |
| `is_binary_gate` | BOOLEAN | |
| `can_block_workflow` | BOOLEAN | |
| `task_display_name` | TEXT | |


#### `audit_logs` — Evaluation audit trail
| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `evaluation_id` | UUID | |
| `tld_string_id` | UUID FK | |
| `generated_at` | TIMESTAMPTZ | |
| `audit_data` | JSONB | Full audit payload |
| `markdown_content` | TEXT | Rendered audit report |
| `total_tasks` | INTEGER | |
| `workflow_summaries` | JSONB | |

#### `evaluation_snapshots` — Historical evaluation archive
| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `tld_string` | TEXT | |
| `snapshot_label` | TEXT | |
| `snapshot_date` | TIMESTAMPTZ | |
| `evaluation_data` | JSONB | Full evaluation data at snapshot time |


---

### ICANN Application Tables

#### `applicants` — Registry organization profiles
Reusable applicant entities with ~50 fields covering organization details, contacts, financial info, registry experience, parent companies, and legal attestations.

Key extended fields (added March 2026):
- `dba_name`, `tax_id`, `lei`, `stock_symbol`, `stock_exchange`
- Structured address: `address_line1` through `country_code`
- Parent company: `parent_company_name`, `parent_company_address` (JSONB), etc.
- Ultimate parent: `ultimate_parent_name`, `ultimate_parent_address` (JSONB), etc.
- Registry flags: `is_existing_registry_operator`, `is_rsp_or_provider`
- Legal: `has_unique_legal_issues`, `legal_issues_explanation`


#### `tld_applications` — Per-TLD application records
| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `applicant_id` | UUID FK → applicants | |
| `tld_string_id` | UUID FK → tld_strings | |
| `tld_string` | VARCHAR(63) | Denormalized |
| `application_type` | VARCHAR(50) | `standard`, `community`, `brand`, `geographic`, `idn_variant` |
| `status` | VARCHAR(50) | `Draft`, `In_Progress`, `Review`, `Submitted` |
| `completion_percentage` | DECIMAL(5,2) | |
| `internal_reference` | VARCHAR(100) UNIQUE | |
| `string_meaning`, `string_rationale`, `intended_use` | TEXT | |
| `secondary_string_id`, `secondary_tld_string` | | For variant TLDs |
| `is_reserved_name`, `has_variant_strings`, `has_voluntary_commitments` | BOOLEAN | |
| `financial_profile_type` | TEXT | |
| `application_fee_paid` | | |
| `submission_deadline`, `submitted_at` | TIMESTAMPTZ | |

#### `application_questions_enhanced` — ICANN question catalog (PRIMARY)
**This is the canonical question table.** 237 questions aligned to the 2026 ICANN Applicant Guidebook.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `question_number` | TEXT UNIQUE | e.g. `1`, `48`, `116` |
| `section_name` | TEXT | e.g. `Entity Information`, `String Evaluation` |
| `question_text` | TEXT | |
| `question_category` | TEXT | `entity_field`, `substantive_field`, `selection_field`, `file_upload` |
| `applicant_field_mapping` | TEXT | Maps to applicant table field |
| `applicability` | TEXT[] | Which app types this applies to |
| `question_set` | INTEGER | 1-23 |
| `question_set_name` | TEXT | Human-readable set name |
| `entity_scope` | TEXT | |
| `relevant_task_names` | TEXT[] | Which eval tasks inform this answer |
| `generation_hint` | TEXT | AI generation guidance |
| `character_limit`, `word_limit` | INTEGER | |
| `input_type` | TEXT | |
| `is_active` | BOOLEAN | |


**Question numbering (post-reconciliation):**
- Q1-48: Entity Information
- Q49-64: Users
- Q65-103: Payments (excluded from generation)
- Q104-115: Background Screening
- Q116-121: String Evaluation
- Q122-130: Variant Management
- Q131-157: Community
- Q158-161: Geographic
- Q162-163: Reserved Names
- Q164-171: Safeguard
- Q172-175: Registry Voluntary Commitments
- Q176-178: Registry Services
- Q179-188: Brand + Code of Conduct
- Q189-191: Profile Determination
- Q192-194: Government
- Q195-201: Registry Operator
- Q202-207: Top 25
- Q208-219: Standard Protections
- Q220-221: Operational
- Q222: Additional
- Q223-224: Bona Fide Intent
- Q225: Volume Refund
- Q226-237: Supplementary Variant

#### `application_answers_enhanced` — AI-generated answers (PRIMARY)
Used by backend answer generation (`crewai_service/answer_generation_service.py`).

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `tld_application_id` | UUID FK → tld_applications | |
| `question_id` | UUID FK → application_questions_enhanced | |
| `answer_text`, `answer_html`, `answer_markdown` | TEXT | |
| `word_count`, `character_count` | INTEGER | |
| `confidence_score`, `completeness_score`, `data_availability_score` | DECIMAL | |
| `generation_method` | VARCHAR(50) | `ai_generated`, `manual`, etc. |
| `ai_model_used` | VARCHAR(100) | |
| `review_status` | VARCHAR(50) | `draft`, `reviewed`, `approved` |
| `version` | INTEGER | |
| `source_evaluations` | JSONB | Links to task executions |
| `source_data_summary` | TEXT | |
| `updated_at` | TIMESTAMPTZ | Auto-updated via trigger |

#### `application_answers` — Frontend user edits
Used by the frontend for manual answer editing via direct Supabase upsert.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `application_id` | UUID | |
| `question_id` | UUID FK → application_questions_enhanced | FK re-pointed Apr 2026 |
| `answer_text` | TEXT | |
| `answer_files` | JSONB | |
| `status` | TEXT | |
| `ai_generated` | BOOLEAN | |
| `last_modified`, `updated_at` | TIMESTAMPTZ | `updated_at` added Apr 2026 |

**Unique constraint:** `(application_id, question_id)` — enables upsert from frontend.

**Note:** There are currently two answer tables (`application_answers` for frontend edits, `application_answers_enhanced` for AI generation). The backend API reads from both with fallback logic.

#### Application Entity Sub-tables
Created April 2026 for structured ICANN form data:
- `application_users` — Application user/contact records
- `application_billing_contacts` — Billing contact details
- `application_financial_institutions` — Financial institution references
- `application_payors` — Payment/payor information

#### `response_generation_executions` — Answer generation workflow tracking
Tracks batch answer generation runs.

---

### Legacy/Deprecated Tables (still in DB, not actively used)

| Table | Rows | Notes |
|-------|------|-------|
| `application_questions` | 216 | OLD question catalog (pre-2026 guidebook). Superseded by `application_questions_enhanced`. |
| `application_responses` | 0 | OLD answer table. Superseded by `application_answers_enhanced`. |
| `dns_stability_results` | 0 | Empty — results stored in `task_executions.result_data` JSONB |
| `gac_risk_results` | 0 | Same |
| `iana_check_results` | 0 | Same |
| `reserved_names_results` | 0 | Same |
| `blocked_names_results` | 0 | Same |
| `similarity_analysis_results` | 0 | Same |
| `trademark_assessment_results` | 0 | Same |

### RAG/Embeddings Tables
| Table | Notes |
|-------|-------|
| `rag_content` | **The live index.** Created by `scripts/setup_rag_database.py` together with the `similarity_search` function; guidebook sections are loaded by `db/populate_guidebook_embeddings.py`. See [docs/KNOWLEDGE_BASE.md](../docs/KNOWLEDGE_BASE.md). |
| `rag_embeddings` | Evaluation outputs embedded for the chat panel (`/api/rag/embed-content`). |
| `guidebook_embeddings`, `guidebook_sections`, `guidebook_search_queries`, `guidebook_search_results`, `application_question_embeddings`, `external_resource_embeddings` | Legacy, unused by the current tools. |

---

### Views

| View | Purpose |
|------|---------|
| `application_overview` | Application summary with applicant name, completion stats |
| `application_completion_status` | Per-application completion percentage |
| `application_completion_detailed` | Detailed completion with validation/approval breakdown |
| `question_readiness_assessment` | Question-level answer generation readiness |
| `tld_compliance_status` | Compliance check results per TLD |
| `tld_latest_results` | Latest task execution per TLD per task type |

---

## Evaluation Workflows

### 1. Technical Risk Assessment
4 tasks: DNS Stability, Name Collision, Similarity Analysis, Technical Risk Validation

### 2. Legal Risk Assessment
3 tasks: Global Trademark Assessment, Patent Conflict Assessment, Legal Risk Validation

### 3. Policy Safeguard Review
5 tasks: Geographic Name Assessment, Safeguard Assessment, GAC Risk Analysis, Cultural Linguistic Assessment, Policy Safeguard Validation

---

## Migrations

Active migrations are in `db/migrations/`. Applied via Supabase MCP `apply_migration`.

Legacy SQL schema files (24 files representing earlier iterations) have been archived to `archive/old_schemas/`.

---

## Key Relationships

```
tld_strings (1) ──→ (N) task_executions
tld_strings (1) ──→ (N) workflow_executions
tld_strings (1) ──→ (1) tld_applications
applicants  (1) ──→ (N) tld_applications
tld_applications (1) ──→ (N) application_answers_enhanced
tld_applications (1) ──→ (N) application_answers
application_questions_enhanced (1) ──→ (N) application_answers_enhanced (FK: question_id)
application_questions_enhanced (1) ──→ (N) application_answers (FK: question_id)
```
