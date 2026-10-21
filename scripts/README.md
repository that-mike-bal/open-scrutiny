# Scripts

Run from the repo root with your `.env` populated (`set -a; . ./.env; set +a` or a loader of your choice). All credentials come from the environment.

## Setup and seeding (run once after deploying `db/schema.sql`)

| Script | Purpose |
|---|---|
| `reconcile_questions.py` | Remaps the example question numbering to the final guidebook numbering. Idempotent. Run **before** `categorize_questions.py` when re-importing question data. |
| `categorize_questions.py` | Seeds the example ruleset's question categories, sets, and field mappings. `CUSTOMIZE:` for your own item schema. |
| `setup_rag_database.py` | Builds the RAG index from the sample knowledge base and the datasets in `data/`. |
| `setup_audit_table.py` | Creates the audit-log table if your schema predates it. |

## Operating

| Script | Purpose |
|---|---|
| `audit_evaluations.py` | Generates audit logs for completed evaluations. |
| `snapshot_evaluations.py` | Snapshots evaluation results into `evaluation_snapshots` before a reset or migration. |
| `verify_question_categories.py` | Sanity-checks the seeded question categories. |
| `match_tld_magnitude.py` | Refreshes the example's DNS-magnitude lookup from a newer ICANN export. |
| `validate-binary-compliance.js` | Validates the client-side gate datasets in `client/public/data/`. |
| `utilities/run_mcp_server.py` | Runs the optional MCP server (`crewai_service/mcp_server.py`) for development. |
