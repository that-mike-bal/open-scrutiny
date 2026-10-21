"""
Evaluation Audit Script

Queries Supabase for all TLD evaluations and generates an audit report showing:
- Per-evaluation: status, task completion counts, workflow completion
- Per-task: status, result_status, confidence_score, result_data content, errors
- Flags evaluations with missing tasks, failures, or incomplete workflows
"""

import os
import sys
import json
from datetime import datetime

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from supabase import create_client


def load_secret(name: str) -> str:
    secret_path = os.path.join(project_root, "secrets", f"{name}.txt")
    with open(secret_path, "r") as f:
        return f.read().strip()


def fetch_all_rows(client, table_name, order_col="id"):
    """Paginate through all rows in a table (Supabase caps at 1000 per request)."""
    all_rows = []
    page_size = 1000
    offset = 0
    while True:
        result = (
            client.table(table_name)
            .select("*")
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


def get_result_data_output_length(result_data):
    """Extract the output content length from result_data JSONB."""
    if not result_data:
        return 0
    if isinstance(result_data, str):
        try:
            result_data = json.loads(result_data)
        except (json.JSONDecodeError, TypeError):
            return len(result_data)
    if isinstance(result_data, dict):
        output = result_data.get("output", "")
        if output:
            return len(str(output))
        # Fallback: check total serialized size
        return len(json.dumps(result_data))
    return 0


def main():
    url = load_secret("supabase_url")
    key = load_secret("supabase_service_key")
    client = create_client(url, key)

    # Pull all data with pagination
    print("Fetching TLD strings...")
    tld_strings = fetch_all_rows(client, "tld_strings")
    print(f"  Found {len(tld_strings)} evaluations\n")

    print("Fetching task executions...")
    all_tasks = fetch_all_rows(client, "task_executions")
    print(f"  Found {len(all_tasks)} task execution records\n")

    print("Fetching workflow executions...")
    all_workflows = fetch_all_rows(client, "workflow_executions")
    print(f"  Found {len(all_workflows)} workflow execution records\n")

    # Index tasks and workflows by tld_string_id
    tasks_by_tld = {}
    for t in all_tasks:
        tid = t.get("tld_string_id")
        if tid:
            tasks_by_tld.setdefault(tid, []).append(t)

    workflows_by_tld = {}
    for w in all_workflows:
        tid = w.get("tld_string_id")
        if tid:
            workflows_by_tld.setdefault(tid, []).append(w)

    # Expected tasks based on actual task names found in the database
    expected_tasks = {
        "technical_risk_assessment": [
            "dns_stability_review",
            "name_collision_assessment",
            "comprehensive_similarity_analysis",
            "technical_gut_check",
        ],
        "legal_risk_assessment": [
            "global_trademark_assessment",
            "patent_conflict_assessment",
            "legal_gut_check",
            "legal_risk_validation",
        ],
        "policy_safeguard_review": [
            "geographic_name_assessment",
            "safeguard_assessment",
            "gac_risk_analysis",
            "policy_gut_check",
        ],
    }
    all_expected_task_names = set()
    for tasks in expected_tasks.values():
        all_expected_task_names.update(tasks)

    expected_workflow_types = set(expected_tasks.keys())

    # Build audit report
    print("=" * 100)
    print("EVALUATION AUDIT REPORT")
    print(f"Generated: {datetime.now().isoformat()}")
    print(f"Total evaluations: {len(tld_strings)}")
    print("=" * 100)

    summary = {
        "total": len(tld_strings),
        "fully_complete": 0,
        "partial": 0,
        "failed": 0,
        "no_tasks": 0,
        "issues": [],
    }

    audit_records = []

    for tld in tld_strings:
        tld_id = tld["id"]
        tld_string = tld.get("tld_string", "UNKNOWN")
        tld_status = tld.get("overall_status") or tld.get("status") or "UNKNOWN"
        created = tld.get("created_at", "")

        tasks = tasks_by_tld.get(tld_id, [])
        workflows = workflows_by_tld.get(tld_id, [])

        # Task analysis
        task_names_present = set()
        tasks_completed = 0
        tasks_failed = 0
        tasks_pending = 0
        tasks_other = 0
        task_details = []

        for t in tasks:
            name = t.get("task_name", "unknown")
            task_names_present.add(name)
            status = (t.get("status") or "").upper()
            result_status = t.get("result_status", "N/A")
            confidence = t.get("confidence_score")
            error = t.get("error_message")
            result_data = t.get("result_data")
            result_data_len = get_result_data_output_length(result_data)
            has_result_data = result_data_len > 0
            started = t.get("started_at")
            completed = t.get("completed_at")
            exec_time = t.get("execution_time_seconds")

            if status == "COMPLETED":
                tasks_completed += 1
            elif status == "FAILED":
                tasks_failed += 1
            elif status in ("PENDING", "RUNNING"):
                tasks_pending += 1
            else:
                tasks_other += 1

            # Extract tool execution summary from result_data
            tool_exec_summary = None
            data_reliability = None
            if isinstance(result_data, dict):
                tool_exec_summary = result_data.get("tool_execution_summary")
                if isinstance(tool_exec_summary, dict):
                    overall = tool_exec_summary.get("overall", {})
                    data_reliability = overall.get("data_reliability")

            task_details.append({
                "task_name": name,
                "status": status,
                "result_status": result_status,
                "confidence_score": confidence,
                "error_message": error,
                "has_result_data": has_result_data,
                "result_data_length": result_data_len,
                "agent_name": t.get("agent_name"),
                "started_at": started,
                "completed_at": completed,
                "execution_time_seconds": exec_time,
                "retry_count": t.get("retry_count", 0),
                "data_reliability": data_reliability,
                "tool_execution_summary": tool_exec_summary,
            })

        missing_tasks = all_expected_task_names - task_names_present
        extra_tasks = task_names_present - all_expected_task_names

        # Workflow analysis
        wf_details = []
        wf_types_present = set()
        for w in workflows:
            wf_type = w.get("workflow_type", "unknown")
            wf_types_present.add(wf_type)
            wf_status = (w.get("status") or "").upper()
            wf_details.append({
                "workflow_type": wf_type,
                "status": wf_status,
                "started_at": w.get("started_at"),
                "completed_at": w.get("completed_at"),
                "total_tasks": w.get("total_tasks"),
                "completed_tasks": w.get("completed_tasks"),
                "failed_tasks": w.get("failed_tasks"),
                "overall_status": w.get("overall_status"),
                "confidence_score": w.get("confidence_score"),
            })

        missing_workflows = expected_workflow_types - wf_types_present

        # Determine evaluation health
        issues = []
        if len(tasks) == 0:
            issues.append("NO_TASK_EXECUTIONS")
        if tasks_failed > 0:
            issues.append(f"FAILED_TASKS({tasks_failed})")
        if tasks_pending > 0:
            issues.append(f"STUCK_TASKS({tasks_pending})")
        if missing_tasks:
            issues.append(f"MISSING_TASKS({','.join(sorted(missing_tasks))})")
        if missing_workflows:
            issues.append(f"MISSING_WORKFLOWS({','.join(sorted(missing_workflows))})")
        if tld_status and tld_status.upper() == "FAILED":
            issues.append("TLD_STATUS_FAILED")
        if tld_status and tld_status.upper() in ("PENDING", "RUNNING"):
            issues.append(f"TLD_STATUS_{tld_status.upper()}")

        # Check for completed tasks with no result data
        empty_tasks = [
            td["task_name"]
            for td in task_details
            if not td["has_result_data"] and td["status"] == "COMPLETED"
        ]
        if empty_tasks:
            issues.append(f"COMPLETED_NO_RESULT_DATA({','.join(empty_tasks)})")

        # Check for tasks with degraded API data reliability
        unreliable_tasks = [
            td["task_name"]
            for td in task_details
            if td.get("data_reliability") in ("PARTIAL", "NONE")
        ]
        if unreliable_tasks:
            issues.append(f"API_DATA_UNRELIABLE({','.join(unreliable_tasks)})")

        # Categorize
        if not issues and tasks_completed > 0:
            health = "CLEAN"
            summary["fully_complete"] += 1
        elif len(tasks) == 0:
            health = "NO_DATA"
            summary["no_tasks"] += 1
        elif tasks_failed > 0 or (tld_status and tld_status.upper() == "FAILED"):
            health = "FAILED"
            summary["failed"] += 1
        else:
            health = "PARTIAL"
            summary["partial"] += 1

        if issues:
            summary["issues"].append({"tld_string": tld_string, "issues": issues})

        record = {
            "tld_string": tld_string,
            "tld_id": tld_id,
            "tld_status": tld_status,
            "created_at": created,
            "health": health,
            "issues": issues,
            "task_count": len(tasks),
            "tasks_completed": tasks_completed,
            "tasks_failed": tasks_failed,
            "tasks_pending": tasks_pending,
            "missing_tasks": sorted(missing_tasks),
            "extra_tasks": sorted(extra_tasks),
            "task_details": task_details,
            "workflow_count": len(workflows),
            "missing_workflows": sorted(missing_workflows),
            "workflow_details": wf_details,
            "has_report": bool(tld.get("generated_report")),
        }
        audit_records.append(record)

        # Print per-evaluation summary
        health_icon = {"CLEAN": "OK", "PARTIAL": "!!", "FAILED": "XX", "NO_DATA": "--"}[health]
        print(f"\n[{health_icon}] .{tld_string}  [{tld_status}]  created: {created[:10] if created else 'N/A'}")
        print(f"     Tasks: {tasks_completed} completed, {tasks_failed} failed, {tasks_pending} pending  |  Workflows: {len(workflows)}  |  Report: {'yes' if record['has_report'] else 'no'}")

        if missing_tasks:
            print(f"     Missing tasks: {', '.join(sorted(missing_tasks))}")
        if missing_workflows:
            print(f"     Missing workflows: {', '.join(sorted(missing_workflows))}")

        if task_details:
            for td in sorted(task_details, key=lambda x: x["task_name"]):
                status_icon = "OK" if td["status"] == "COMPLETED" else "XX" if td["status"] == "FAILED" else ".."
                conf = f"  conf={td['confidence_score']}" if td["confidence_score"] is not None else ""
                out = f"  data={td['result_data_length']}ch" if td["has_result_data"] else "  NO_DATA"
                err = f"  ERR: {td['error_message'][:80]}" if td["error_message"] else ""
                agent = f"  [{td['agent_name']}]" if td["agent_name"] else ""
                rel = f"  api={td['data_reliability']}" if td.get("data_reliability") else ""
                print(f"     [{status_icon}] {td['task_name']:40s} {td['status']:12s} result={str(td['result_status']):15s}{conf}{out}{rel}{agent}{err}")

        if wf_details:
            for wd in wf_details:
                wf_icon = "OK" if wd["status"] == "COMPLETED" else "XX" if wd["status"] == "FAILED" else ".."
                timing = ""
                if wd["started_at"] and wd["completed_at"]:
                    try:
                        s = datetime.fromisoformat(wd["started_at"].replace("Z", "+00:00"))
                        e = datetime.fromisoformat(wd["completed_at"].replace("Z", "+00:00"))
                        timing = f"  ({(e - s).total_seconds():.0f}s)"
                    except Exception:
                        pass
                print(f"     [{wf_icon}] WF: {wd['workflow_type']:35s} {wd['status']:12s} overall={wd['overall_status'] or 'N/A'}{timing}")

        if issues:
            print(f"     Issues: {', '.join(issues)}")

    # Print summary
    print("\n" + "=" * 100)
    print("SUMMARY")
    print("=" * 100)
    print(f"Total evaluations:    {summary['total']}")
    print(f"Fully complete (CLEAN): {summary['fully_complete']}")
    print(f"Partial/incomplete:   {summary['partial']}")
    print(f"Failed:               {summary['failed']}")
    print(f"No task data:         {summary['no_tasks']}")
    print(f"Evaluations w/issues: {len(summary['issues'])}")

    # Issue type breakdown
    from collections import Counter
    issue_types = Counter()
    for item in summary["issues"]:
        for issue in item["issues"]:
            itype = issue.split("(")[0]
            issue_types[itype] += 1

    if issue_types:
        print(f"\nIssue type breakdown:")
        for itype, count in issue_types.most_common():
            print(f"  {itype}: {count}")

    # Task completion rate across all evaluations
    total_task_records = sum(e["task_count"] for e in audit_records)
    total_completed = sum(e["tasks_completed"] for e in audit_records)
    total_failed = sum(e["tasks_failed"] for e in audit_records)
    total_pending = sum(e["tasks_pending"] for e in audit_records)
    print(f"\nTask execution totals:")
    print(f"  Total task records:  {total_task_records}")
    print(f"  Completed:           {total_completed}")
    print(f"  Failed:              {total_failed}")
    print(f"  Pending/running:     {total_pending}")

    # Evaluations with reports
    with_report = sum(1 for e in audit_records if e["has_report"])
    print(f"\nReport generation:")
    print(f"  Evaluations with report: {with_report}/{summary['total']}")

    if summary["issues"]:
        print(f"\nEvaluations with issues:")
        for item in sorted(summary["issues"], key=lambda x: x["tld_string"]):
            print(f"  .{item['tld_string']}: {', '.join(item['issues'])}")

    # Export full audit to JSON
    output_path = os.path.join(project_root, "outputs", "evaluation_audit.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "summary": {
                **summary,
                "task_totals": {
                    "total": total_task_records,
                    "completed": total_completed,
                    "failed": total_failed,
                    "pending": total_pending,
                },
                "reports": {"with_report": with_report, "without_report": summary["total"] - with_report},
                "issue_breakdown": dict(issue_types.most_common()),
            },
            "evaluations": audit_records,
        }, f, indent=2, default=str)
    print(f"\nFull audit exported to: {output_path}")


if __name__ == "__main__":
    main()
