#!/usr/bin/env python3
"""
Setup script to create the audit_logs table in Supabase.

Run this script once to create the table, or run the SQL manually
via the Supabase dashboard.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.tld_application_store import TldApplicationStore


def create_audit_logs_table():
    """Create the audit_logs table using Supabase."""
    store = TldApplicationStore()

    # Try to check if table exists
    try:
        result = store.supabase.table('audit_logs').select('id').limit(1).execute()
        print("✅ audit_logs table already exists!")
        return True
    except Exception as e:
        error_str = str(e)
        if 'does not exist' in error_str.lower() or 'PGRST205' in error_str:
            print("Table does not exist. Creating...")
        else:
            print(f"Error checking table: {e}")
            return False

    # The SQL to create the table
    # Note: Supabase doesn't support raw SQL via the client
    # This needs to be run via the Supabase dashboard SQL Editor

    sql = """
-- Create the audit_logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    evaluation_id UUID,
    tld_string_id UUID NOT NULL REFERENCES tld_strings(id) ON DELETE CASCADE,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    audit_data JSONB NOT NULL,
    markdown_content TEXT NOT NULL,
    total_tasks INTEGER NOT NULL DEFAULT 0,
    workflow_summaries JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_audit_logs_tld_string_id ON audit_logs(tld_string_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_evaluation_id ON audit_logs(evaluation_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_generated_at ON audit_logs(generated_at DESC);
"""

    print("\n" + "=" * 60)
    print("MANUAL STEP REQUIRED")
    print("=" * 60)
    print("""
The Supabase Python client doesn't support raw SQL execution.
Please run the following SQL in your Supabase dashboard:

1. Go to: https://supabase.com/dashboard
2. Select your project
3. Click "SQL Editor" in the left sidebar
4. Paste this SQL and click "Run":
""")
    print("-" * 60)
    print(sql)
    print("-" * 60)
    print("\nAfter running the SQL, run this script again to verify.")

    return False


def test_audit_generation():
    """Test audit log generation with existing data."""
    from crewai_service.utils.audit_log_generator import (
        generate_evaluation_audit_log,
        format_audit_log_markdown
    )

    store = TldApplicationStore()

    # Get a TLD with task executions
    result = store.supabase.table('tld_strings').select('id, tld_string').limit(1).execute()
    if not result.data:
        print("No TLD strings found to test with.")
        return

    tld = result.data[0]
    print(f"\n📋 Testing audit generation for: {tld['tld_string']}")

    # Fetch task executions
    tasks = store.supabase.table('task_executions').select(
        'task_name, result_data, result_status, execution_time_seconds'
    ).eq('tld_string_id', tld['id']).execute()

    if not tasks.data:
        print("No task executions found.")
        return

    # Generate audit
    audit_log = generate_evaluation_audit_log(tld['tld_string'], tasks.data)
    markdown = format_audit_log_markdown(audit_log)

    print(f"✅ Generated audit log with {audit_log['total_tasks']} tasks")
    print(f"   Workflows: {list(audit_log.get('workflow_summaries', {}).keys())}")

    # Try to save if table exists
    try:
        import uuid
        record = {
            "id": str(uuid.uuid4()),
            "tld_string_id": tld['id'],
            "generated_at": audit_log["generated_at"],
            "audit_data": audit_log,
            "markdown_content": markdown,
            "total_tasks": audit_log["total_tasks"],
            "workflow_summaries": audit_log.get("workflow_summaries", {})
        }

        save_response = store.supabase.table("audit_logs").insert(record).execute()
        if save_response.data:
            print(f"✅ Saved audit log to database: {record['id']}")
        else:
            print("⚠️  Could not save to database")
    except Exception as e:
        print(f"⚠️  Database save failed (table may not exist): {e}")


if __name__ == "__main__":
    print("🔧 Audit Logs Setup Script")
    print("=" * 60)

    if create_audit_logs_table():
        print("\n✅ Table is ready!")
        test_audit_generation()
    else:
        print("\n❌ Please create the table manually and run again.")
