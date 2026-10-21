"""
Evaluation Snapshot Script

Archives all current TLD string evaluation data into the evaluation_snapshots table
before a rerun. Each string gets one row with all its evaluation data packed into JSONB.

Usage:
    python scripts/snapshot_evaluations.py "pre-rerun-2026-04-02"
    python scripts/snapshot_evaluations.py                        # auto-labels with date
"""

import os
import sys
import json
from datetime import datetime, timezone

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from supabase import create_client


def load_secret(name: str) -> str:
    """Load a secret from the secrets directory or environment."""
    env_val = os.getenv(name.upper())
    if env_val and env_val.strip():
        return env_val.strip()
    secret_path = os.path.join(project_root, "secrets", f"{name}.txt")
    with open(secret_path, "r") as f:
        return f.read().strip()


def fetch_all_rows(client, table_name, select="*", order_col="id"):
    """Paginate through all rows in a table (Supabase caps at 1000 per request)."""
    all_rows = []
    page_size = 1000
    offset = 0
    while True:
        result = (
            client.table(table_name)
            .select(select)
            .order(order_col, desc=False)
            .range(offset, offset + page_size - 1)
            .execute()
        )
        rows = result.data or []
        all_rows.extend(rows)
        if len(rows) < page_size:
            break
        offset += page_size
    return all_rows


def index_by_field(rows, field):
    """Group a list of dicts by a given field value."""
    index = {}
    for row in rows:
        key = row.get(field)
        if key:
            index.setdefault(key, []).append(row)
    return index


def strip_large_fields(obj):
    """Remove excessively large raw_output fields to keep snapshot size reasonable."""
    if isinstance(obj, dict):
        return {
            k: (v[:2000] + "...[truncated]" if k == "raw_output" and isinstance(v, str) and len(v) > 2000 else strip_large_fields(v))
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [strip_large_fields(item) for item in obj]
    return obj


# All specialized result tables keyed by task_execution_id.
# Each is fetched once, indexed by task_execution_id, and attached to the
# relevant task execution entry in the snapshot blob.
RESULT_TABLES = [
    "iana_check_results",
    "blocked_names_results",
    "reserved_names_results",
    "string_analysis_results",
    "dns_stability_results",
    "similarity_analysis_results",
    "trademark_assessment_results",
    "gac_risk_results",
    "validation_results",
]


def fetch_result_tables(client):
    """Fetch all specialized result tables. Returns dict of table_name -> {task_execution_id: [rows]}."""
    result_indexes = {}
    for table in RESULT_TABLES:
        try:
            rows = fetch_all_rows(client, table)
            result_indexes[table] = index_by_field(rows, "task_execution_id")
            print(f"  {table}: {len(rows)} rows")
        except Exception as e:
            print(f"  {table}: not found or error ({e}), skipping")
            result_indexes[table] = {}
    return result_indexes


def get_task_result_details(task_id, result_indexes):
    """Collect all specialized result rows that belong to a given task_execution_id."""
    details = {}
    for table, index in result_indexes.items():
        rows = index.get(task_id, [])
        if rows:
            details[table] = rows
    return details


def build_evaluation_blob(tld_record, workflows, tasks, risk_assessments, result_indexes):
    """Pack all evaluation data for one string into a single dict."""
    blob = {
        "string_metadata": {
            "id": tld_record.get("id"),
            "use_case": tld_record.get("use_case"),
            "overall_status": tld_record.get("overall_status"),
            "status": tld_record.get("status"),
            "created_at": tld_record.get("created_at"),
            "updated_at": tld_record.get("updated_at"),
        },
        "generated_report": tld_record.get("generated_report"),
        "workflow_executions": [
            strip_large_fields({
                "id": w.get("id"),
                "workflow_type": w.get("workflow_type"),
                "status": w.get("status"),
                "overall_status": w.get("overall_status"),
                "confidence_score": w.get("confidence_score"),
                "final_recommendation": w.get("final_recommendation"),
                "total_tasks": w.get("total_tasks"),
                "completed_tasks": w.get("completed_tasks"),
                "failed_tasks": w.get("failed_tasks"),
                "execution_time_minutes": w.get("execution_time_minutes"),
                "started_at": w.get("started_at"),
                "completed_at": w.get("completed_at"),
                "raw_output": w.get("raw_output"),
            })
            for w in workflows
        ],
        "task_executions": [
            strip_large_fields({
                "id": t.get("id"),
                "task_name": t.get("task_name"),
                "task_display_name": t.get("task_display_name"),
                "status": t.get("status"),
                "result_status": t.get("result_status"),
                "result_data": t.get("result_data"),
                "confidence_score": t.get("confidence_score"),
                "user_friendly_summary": t.get("user_friendly_summary"),
                "agent_name": t.get("agent_name"),
                "tools_used": t.get("tools_used"),
                "error_message": t.get("error_message"),
                "started_at": t.get("started_at"),
                "completed_at": t.get("completed_at"),
                "raw_output": t.get("raw_output"),
                # Specialized result table data attached per-task
                "result_details": get_task_result_details(t.get("id"), result_indexes),
            })
            for t in tasks
        ],
        "risk_assessments": [
            {
                "id": r.get("id"),
                "overall_risk_level": r.get("overall_risk_level"),
                "risk_category": r.get("risk_category"),
                "risk_score": r.get("risk_score"),
                "investment_recommendation": r.get("investment_recommendation"),
                "action_required": r.get("action_required"),
                "technical_compliance": r.get("technical_compliance"),
                "name_collision": r.get("name_collision"),
                "string_similarity": r.get("string_similarity"),
                "safeguard_policy": r.get("safeguard_policy"),
                "geopolitical": r.get("geopolitical"),
                "legal_trademark": r.get("legal_trademark"),
                "cultural_linguistic": r.get("cultural_linguistic"),
                "high_risk_flags": r.get("high_risk_flags"),
                "top_3_risks": r.get("top_3_risks"),
                "critical_concerns": r.get("critical_concerns"),
                "risk_explanation": r.get("risk_explanation"),
                "strategic_guidance": r.get("strategic_guidance"),
                "mitigation_recommendations": r.get("mitigation_recommendations"),
                "data_confidence": r.get("data_confidence"),
                "assessment_date": r.get("assessment_date"),
            }
            for r in risk_assessments
        ],
    }
    return blob


def main():
    # Determine snapshot label
    if len(sys.argv) > 1:
        label = sys.argv[1]
    else:
        label = f"snapshot-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"

    print(f"Snapshot label: {label}")
    print()

    # Connect
    url = load_secret("supabase_url")
    key = load_secret("supabase_service_key")
    client = create_client(url, key)

    # Fetch all evaluation data
    print("Fetching tld_strings...")
    tld_strings = fetch_all_rows(client, "tld_strings")
    print(f"  {len(tld_strings)} strings")

    print("Fetching workflow_executions...")
    workflows = fetch_all_rows(client, "workflow_executions")
    print(f"  {len(workflows)} workflows")

    print("Fetching task_executions...")
    tasks = fetch_all_rows(client, "task_executions")
    print(f"  {len(tasks)} tasks")

    print("Fetching risk_assessments...")
    try:
        risk_assessments = fetch_all_rows(client, "risk_assessments")
        print(f"  {len(risk_assessments)} risk assessments")
    except Exception as e:
        print(f"  Warning: could not fetch risk_assessments ({e}), continuing without them")
        risk_assessments = []

    print("\nFetching specialized result tables...")
    result_indexes = fetch_result_tables(client)

    print()

    # Index by tld_string_id
    workflows_by_tld = index_by_field(workflows, "tld_string_id")
    tasks_by_tld = index_by_field(tasks, "tld_string_id")
    # risk_assessments uses string_id as the FK
    risks_by_tld = index_by_field(risk_assessments, "string_id")

    # Build and insert snapshots
    inserted = 0
    skipped = 0
    errors = 0

    for tld in tld_strings:
        tld_id = tld["id"]
        tld_string = tld.get("tld_string", "UNKNOWN")

        tld_workflows = workflows_by_tld.get(tld_id, [])
        tld_tasks = tasks_by_tld.get(tld_id, [])
        tld_risks = risks_by_tld.get(tld_id, [])

        # Skip strings with no evaluation data at all
        if not tld_workflows and not tld_tasks and not tld_risks:
            skipped += 1
            continue

        blob = build_evaluation_blob(tld, tld_workflows, tld_tasks, tld_risks, result_indexes)

        try:
            client.table("evaluation_snapshots").upsert(
                {
                    "tld_string": tld_string,
                    "snapshot_label": label,
                    "evaluation_data": blob,
                },
                on_conflict="tld_string,snapshot_label",
            ).execute()
            inserted += 1
        except Exception as e:
            print(f"  ERROR inserting snapshot for '{tld_string}': {e}")
            errors += 1

    print(f"Done!")
    print(f"  Inserted/updated: {inserted}")
    print(f"  Skipped (no eval data): {skipped}")
    if errors:
        print(f"  Errors: {errors}")
    print(f"  Label: {label}")


if __name__ == "__main__":
    main()
