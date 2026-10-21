"""
Narrative Audit Log Generator
==============================

Generates human-readable, task-by-task audit logs that prove what each
evaluation task did, including: models used, searches performed, results
found, validation applied, and final verdicts.

Designed to create transparency and auditability for TLD evaluations.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# Task metadata for generating meaningful narratives
TASK_METADATA = {
    # Technical Risk Assessment tasks
    # These use LOCAL analysis tools — no external API calls expected
    "dns_stability_review": {
        "display_name": "DNS Stability Review",
        "workflow": "technical_risk_assessment",
        "purpose": "technical DNS compliance and stability validation",
        "agent": "String Technical Analysis Specialist",
        "tools": ["string_analyzer"],
        "expects_api_calls": False,
        "checks": [
            "character length (3-63 characters)",
            "IDN/punycode compliance",
            "reserved name conflicts",
            "DNS label validity"
        ]
    },
    "comprehensive_similarity_analysis": {
        "display_name": "Comprehensive Similarity Analysis",
        "workflow": "technical_risk_assessment",
        "purpose": "string similarity analysis against existing TLDs",
        "agent": "String Technical Analysis Specialist",
        "tools": ["similarity_analyzer"],
        "expects_api_calls": False,
        "checks": [
            "Levenshtein distance calculation",
            "phonetic similarity (Soundex/Metaphone)",
            "visual similarity assessment",
            "existing TLD collision detection"
        ]
    },
    "name_collision_assessment": {
        "display_name": "Name Collision Assessment",
        "workflow": "technical_risk_assessment",
        "purpose": "DNS name collision risk evaluation using ICANN magnitude data",
        "agent": "Collision Risk Analyst",
        "tools": ["magnitude_collision_checker"],
        "expects_api_calls": False,
        "checks": [
            "ICANN magnitude collision score",
            "historical collision patterns",
            "internal namespace conflicts",
            "enterprise infrastructure risks"
        ]
    },
    "technical_gut_check": {
        "display_name": "Technical Validation",
        "workflow": "technical_risk_assessment",
        "purpose": "sanity check of technical analysis for logic and consistency",
        "agent": "Evaluation Validator",
        "tools": [],
        "expects_api_calls": False,
        "checks": [
            "output consistency verification",
            "logic validation",
            "completeness check"
        ]
    },

    # Legal Risk Assessment tasks
    "deep_research_legal_assessment": {
        "display_name": "Deep Research Legal Assessment",
        "workflow": "legal_risk_assessment",
        "purpose": "comprehensive legal risk research via Gemini Deep Research — trademarks, patents, and IP conflicts with cited sources",
        "agent": "Global Legal & IP Risk Analyst",
        "tools": ["deep_research_legal_analyzer"],
        "expects_api_calls": True,
        "checks": [
            "USPTO/EUIPO/WIPO trademark search via deep research",
            "patent conflict analysis via deep research",
            "UDRP and domain litigation check",
            "legal risk classification with cited sources"
        ]
    },
    # Legacy task names — kept for backward compat with existing eval results
    "global_trademark_assessment": {
        "display_name": "Global Trademark Assessment",
        "workflow": "legal_risk_assessment",
        "purpose": "trademark conflict analysis across USPTO, EUIPO, and WIPO databases",
        "agent": "Global Trademark Risk Analyst",
        "tools": ["enhanced_trademark_analyzer"],
        "expects_api_calls": True,
        "checks": [
            "USPTO trademark database search",
            "EUIPO trademark registry lookup",
            "WIPO global trademark scan",
            "trademark conflict classification by risk level"
        ]
    },
    "patent_conflict_assessment": {
        "display_name": "Patent Conflict Assessment",
        "workflow": "legal_risk_assessment",
        "purpose": "USPTO patent conflict analysis for intellectual property risks",
        "agent": "Global Trademark Risk Analyst",
        "tools": ["patent_analyzer"],
        "expects_api_calls": True,
        "checks": [
            "USPTO patent database search",
            "technology class identification",
            "patent holder conflict detection"
        ]
    },
    "legal_risk_validation": {
        "display_name": "Legal Risk Validation",
        "workflow": "legal_risk_assessment",
        "purpose": "synthesis and validation of legal risk findings",
        "agent": "Global Trademark Risk Analyst",
        "tools": [],
        "expects_api_calls": False,
        "checks": [
            "trademark analysis accuracy verification",
            "jurisdiction coverage validation",
            "risk classification consistency"
        ]
    },
    "legal_gut_check": {
        "display_name": "Legal Validation",
        "workflow": "legal_risk_assessment",
        "purpose": "sanity check of legal analysis for logic and consistency",
        "agent": "Evaluation Validator",
        "tools": [],
        "expects_api_calls": False,
        "checks": [
            "output consistency verification",
            "logic validation",
            "completeness check"
        ]
    },

    # Policy Safeguard Review tasks
    "geographic_name_assessment": {
        "display_name": "Geographic Name Assessment",
        "workflow": "policy_safeguard_review",
        "purpose": "determination of geographic location representation requiring government approval",
        "agent": "GAC Safeguard Risk Analyst",
        "tools": ["gac_precedent_analyzer", "guidebook_search"],
        "expects_api_calls": False,
        "checks": [
            "country/territory name matching",
            "city/region identification",
            "ISO 3166 code conflicts",
            "government approval requirements"
        ]
    },
    "safeguard_assessment": {
        "display_name": "Safeguard Assessment",
        "workflow": "policy_safeguard_review",
        "purpose": "evaluation against ICANN's 6 mandatory safeguard questions (Q175-Q180)",
        "agent": "GAC Safeguard Risk Analyst",
        "tools": ["guidebook_search"],
        "expects_api_calls": False,
        "checks": [
            "Q175: consumer protection requirements",
            "Q176: sensitive industry safeguards",
            "Q177: regulated industry compliance",
            "Q178: consumer trust measures",
            "Q179: malicious conduct prevention",
            "Q180: WHOIS verification requirements"
        ]
    },
    "cultural_linguistic_assessment": {
        "display_name": "Cultural & Linguistic Assessment",
        "workflow": "policy_safeguard_review",
        "purpose": "multi-language conflict detection and cultural sensitivity analysis",
        "agent": "GAC Safeguard Risk Analyst",
        "tools": ["brave_web_search"],
        "expects_api_calls": True,
        "checks": [
            "multi-language meaning analysis",
            "cultural sensitivity evaluation",
            "religious/political implications",
            "regional conflict potential"
        ]
    },
    "gac_risk_analysis": {
        "display_name": "GAC Risk Analysis",
        "workflow": "policy_safeguard_review",
        "purpose": "government function assessment and official capacity conflict detection",
        "agent": "GAC Safeguard Risk Analyst",
        "tools": ["gac_precedent_analyzer"],
        "expects_api_calls": False,
        "checks": [
            "government operation associations",
            "public authority conflicts",
            "historical GAC objection patterns",
            "diplomatic sensitivity assessment"
        ]
    },
    "policy_gut_check": {
        "display_name": "Policy Validation",
        "workflow": "policy_safeguard_review",
        "purpose": "sanity check of policy analysis for logic and consistency",
        "agent": "Evaluation Validator",
        "tools": [],
        "expects_api_calls": False,
        "checks": [
            "output consistency verification",
            "logic validation",
            "completeness check"
        ]
    }
}


@dataclass
class TaskAuditEntry:
    """Represents a single task's audit entry."""
    task_name: str
    display_name: str
    workflow: str
    agent: str
    purpose: str
    tools_used: List[str]
    api_calls_made: int
    api_calls_successful: int
    api_sources: List[str]
    data_reliability: str
    key_findings: List[str]
    result_status: str
    execution_time_seconds: Optional[float]
    narrative: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    expects_api_calls: bool = False
    checks_performed: List[str] = None
    actions_performed: List[str] = None

    def __post_init__(self):
        if self.checks_performed is None:
            self.checks_performed = []
        if self.actions_performed is None:
            self.actions_performed = []


def generate_task_narrative(
    task_name: str,
    task_data: Dict[str, Any],
    tld_string: str
) -> TaskAuditEntry:
    """
    Generate a human-readable narrative for a single task execution.

    Args:
        task_name: The task identifier (e.g., 'global_trademark_assessment')
        task_data: The task execution data from Supabase
        tld_string: The TLD string being evaluated

    Returns:
        TaskAuditEntry with complete narrative
    """
    metadata = TASK_METADATA.get(task_name, {
        "display_name": task_name.replace("_", " ").title(),
        "workflow": "unknown",
        "purpose": "evaluation task",
        "agent": "Unknown Agent",
        "tools": [],
        "checks": []
    })

    result_data = task_data.get("result_data", {})
    api_call_log = result_data.get("api_call_log", [])
    tool_summary = result_data.get("tool_execution_summary", {})
    overall_stats = tool_summary.get("overall", {})

    # Extract API sources from call log
    api_sources = set()
    for call in api_call_log:
        endpoint = call.get("api_endpoint", "")
        if "brave" in endpoint.lower():
            api_sources.add("Brave Search API")
        elif "firecrawl" in endpoint.lower():
            api_sources.add("Firecrawl Scraping API")
        elif "uspto" in endpoint.lower():
            api_sources.add("USPTO API")
        elif "serper" in endpoint.lower():
            api_sources.add("Google Serper API")
        elif endpoint:
            api_sources.add(endpoint.split("/")[2] if "/" in endpoint else "API")

    # Extract key findings from output
    key_findings = _extract_key_findings(task_name, result_data)

    expects_api = metadata.get("expects_api_calls", False)

    # Build narrative
    narrative_parts = []

    # Opening statement
    narrative_parts.append(
        f"Evaluated '{tld_string}' for {metadata['purpose']} using the {metadata['agent']}."
    )

    # Tools and API calls
    tools_used = metadata.get("tools", [])
    if tools_used:
        narrative_parts.append(
            f"Utilized {', '.join(tools_used)} tool(s)."
        )

    total_calls = overall_stats.get("total_api_calls", len(api_call_log))
    successful_calls = overall_stats.get("total_successful", 0)
    data_reliability = overall_stats.get("data_reliability", "UNKNOWN")

    if not expects_api and total_calls == 0:
        narrative_parts.append("Local analysis (no external API calls needed).")
    elif total_calls > 0:
        narrative_parts.append(
            f"Made {total_calls} API call(s) with {successful_calls} successful."
        )

        if api_sources:
            narrative_parts.append(
                f"Data sources queried: {', '.join(sorted(api_sources))}."
            )

    # Deep research stats
    if task_name == "deep_research_legal_assessment":
        search_summary = result_data.get("search_summary", {})
        if search_summary.get("deep_research_used"):
            duration = result_data.get("research_duration_seconds", 0)
            source_count = result_data.get("source_count", 0)
            narrative_parts.append(
                f"Gemini Deep Research completed in {duration}s with {source_count} cited source(s)."
            )

    # Validation stats for trademark task (legacy)
    if task_name == "global_trademark_assessment":
        validation_stats = result_data.get("validation_stats", {})
        if validation_stats:
            brave_raw = validation_stats.get("brave_raw", 0)
            brave_valid = validation_stats.get("brave_validated", 0)
            if brave_raw > 0:
                narrative_parts.append(
                    f"Brave Search returned {brave_raw} initial results; {brave_valid} passed validation filters."
                )

            enriched = validation_stats.get("enriched", 0)
            if enriched > 0:
                narrative_parts.append(
                    f"Enriched {enriched} trademark record(s) with detailed data from USPTO.report."
                )

    # Search degradation disclosure
    search_summary = result_data.get("search_summary", {})
    if search_summary.get("model_knowledge_only"):
        bypass_reason = search_summary.get("search_bypass_reason", "")
        narrative_parts.append(
            "Note: No external searches were executed for this task. "
            "Assessment is based on model knowledge only."
            + (f" ({bypass_reason})" if bypass_reason else "")
        )
    elif search_summary.get("brave_degraded"):
        bypass_reason = search_summary.get("search_bypass_reason", "API quota limitations")
        narrative_parts.append(
            f"Note: Brave Search API was degraded ({bypass_reason}). "
            "Results may be based on partial external data supplemented by model knowledge."
        )

    # Key findings
    if key_findings:
        narrative_parts.append("Key findings: " + "; ".join(key_findings[:3]) + ".")

    # Result status
    result_status = task_data.get("result_status", "UNKNOWN")
    narrative_parts.append(f"Task completed with status: {result_status}.")

    # Build actions performed
    actions_performed = _build_actions_performed(task_name, metadata, result_data)

    return TaskAuditEntry(
        task_name=task_name,
        display_name=metadata["display_name"],
        workflow=metadata["workflow"],
        agent=metadata["agent"],
        purpose=metadata["purpose"],
        tools_used=tools_used,
        api_calls_made=total_calls,
        api_calls_successful=successful_calls,
        api_sources=list(api_sources),
        data_reliability=data_reliability,
        key_findings=key_findings,
        result_status=result_status,
        execution_time_seconds=task_data.get("execution_time_seconds"),
        narrative=" ".join(narrative_parts),
        started_at=task_data.get("started_at"),
        completed_at=task_data.get("completed_at"),
        expects_api_calls=expects_api,
        checks_performed=metadata.get("checks", []),
        actions_performed=actions_performed,
    )


def _extract_key_findings(task_name: str, result_data: Dict[str, Any]) -> List[str]:
    """Extract key findings from task result data."""
    findings = []
    full_output = result_data.get("full_output", "") or result_data.get("output", "") or ""

    # Task-specific extraction
    if task_name == "deep_research_legal_assessment":
        # Deep research combines trademark + patent analysis
        search_summary = result_data.get("search_summary", {})
        if search_summary.get("deep_research_used"):
            findings.append("Gemini Deep Research completed with cited web sources")
        elif search_summary.get("model_knowledge_only"):
            findings.append(
                "Deep research unavailable — assessment based on model knowledge only"
            )
        # Look for risk level in output
        if "CRITICAL" in full_output.upper():
            findings.append("Critical legal risk detected")
        elif "HIGH" in full_output.upper()[:500]:
            findings.append("High legal risk detected")
        elif "MEDIUM" in full_output.upper()[:500]:
            findings.append("Medium legal risk detected")
        elif "LOW" in full_output.upper()[:500]:
            findings.append("Low legal risk detected")
        # Source count
        source_count = result_data.get("source_count", 0)
        if source_count:
            findings.append(f"{source_count} source(s) cited in research")

    elif task_name == "global_trademark_assessment":
        # Check for search bypass/degradation
        search_summary = result_data.get("search_summary", {})
        if search_summary.get("model_knowledge_only"):
            findings.append(
                "No external trademark searches executed — assessment based on model knowledge only"
            )
        elif search_summary.get("brave_degraded"):
            findings.append("Brave Search API degraded — partial external data used")

        # Look for trademark conflict counts
        if "conflicts" in str(result_data).lower():
            conflicts = result_data.get("conflicts", [])
            if isinstance(conflicts, list) and conflicts:
                findings.append(f"{len(conflicts)} potential trademark conflict(s) identified")

        # Look for risk level
        if "HIGH" in full_output.upper():
            findings.append("High trademark risk detected")
        elif "MEDIUM" in full_output.upper():
            findings.append("Medium trademark risk detected")
        elif "LOW" in full_output.upper():
            findings.append("Low trademark risk detected")

    elif task_name == "name_collision_assessment":
        # Look for collision score
        if "magnitude" in full_output.lower() or "collision" in full_output.lower():
            import re
            score_match = re.search(r"score[:\s]+(\d+\.?\d*)", full_output.lower())
            if score_match:
                findings.append(f"Collision magnitude score: {score_match.group(1)}")

    elif task_name == "dns_stability_review":
        if "compliant" in full_output.lower():
            findings.append("DNS compliance validated")
        if "reserved" in full_output.lower():
            findings.append("Reserved name check performed")

    elif task_name == "comprehensive_similarity_analysis":
        # Look for similar TLDs
        import re
        similar_match = re.search(r"(\d+)\s*(similar|matches)", full_output.lower())
        if similar_match:
            findings.append(f"{similar_match.group(1)} similar TLD(s) identified")

    elif task_name == "geographic_name_assessment":
        if "geographic" in full_output.lower():
            if "not a geographic" in full_output.lower() or "non-geographic" in full_output.lower():
                findings.append("Not classified as geographic name")
            else:
                findings.append("Geographic name analysis performed")

    elif task_name == "safeguard_assessment":
        # Look for Q175-Q180 references
        for q_num in range(175, 181):
            if f"Q{q_num}" in full_output or f"q{q_num}" in full_output.lower():
                findings.append(f"Evaluated against ICANN safeguard Q{q_num}")

    elif task_name == "patent_conflict_assessment":
        if "patent" in full_output.lower():
            if "no patent" in full_output.lower() or "no conflicts" in full_output.lower():
                findings.append("No patent conflicts identified")
            elif "conflict" in full_output.lower():
                findings.append("Patent conflict analysis performed")
        # Look for risk level
        if "HIGH" in full_output.upper():
            findings.append("High patent risk detected")
        elif "MEDIUM" in full_output.upper():
            findings.append("Medium patent risk detected")
        elif "LOW" in full_output.upper():
            findings.append("Low patent risk detected")

    elif task_name == "gac_risk_analysis":
        if "government" in full_output.lower():
            findings.append("Government function assessment completed")
        if "precedent" in full_output.lower():
            findings.append("Historical GAC precedents reviewed")

    return findings


def _build_actions_performed(
    task_name: str,
    metadata: Dict[str, Any],
    result_data: Dict[str, Any]
) -> List[str]:
    """Build a list of human-readable actions this task performed."""
    actions = []

    tools = metadata.get("tools", [])
    if tools:
        actions.append(f"Ran {', '.join(tools)}")

    checks = metadata.get("checks", [])
    for check in checks:
        actions.append(check)

    search_summary = result_data.get("search_summary", {})
    if search_summary.get("deep_research_used"):
        actions.append("Conducted Gemini Deep Research with autonomous web search")
    elif search_summary.get("model_knowledge_only"):
        actions.append("Used model knowledge (external search bypassed)")
    elif search_summary.get("brave_degraded"):
        actions.append("External search partially available (degraded mode)")

    validation_stats = result_data.get("validation_stats", {})
    if validation_stats:
        brave_raw = validation_stats.get("brave_raw", 0)
        if brave_raw > 0:
            actions.append(f"Processed {brave_raw} search results")
        enriched = validation_stats.get("enriched", 0)
        if enriched > 0:
            actions.append(f"Enriched {enriched} records with detailed data")

    return actions


def _find_task_result_data(
    task_executions: List[Dict[str, Any]], task_name: str
) -> Dict[str, Any]:
    """Find the result_data dict for a given task name."""
    for td in task_executions:
        if td.get("task_name") == task_name:
            return td.get("result_data") or {}
    return {}


def _run_integrity_checks(
    audit_entries: List[TaskAuditEntry],
    task_executions: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Run integrity checks on the evaluation to detect tasks that didn't
    actually perform their intended work. Returns a list of issues found.

    Each issue is a dict with:
      - severity: "CRITICAL" | "WARNING" | "INFO"
      - task_name: which task (or "evaluation" for global issues)
      - issue: short description
      - detail: longer explanation
    """
    issues: List[Dict[str, Any]] = []

    # Statuses that indicate a task completed its work (even if findings vary)
    SUCCESS_STATUSES = {
        "SUCCESS", "COMPLETED", "CLEAR", "PASS",
        "LOW_RISK", "MEDIUM_RISK", "HIGH_RISK",
    }

    # 1. Check for tasks that should have made external API calls but didn't
    for entry in audit_entries:
        metadata = TASK_METADATA.get(entry.task_name, {})
        expects_api = metadata.get("expects_api_calls", False)

        task_workflow = metadata.get("workflow", entry.workflow)

        # Only flag tasks explicitly marked as needing external API calls
        if expects_api and entry.api_calls_made == 0:
            # Check if the search was intentionally bypassed (graceful degradation)
            task_result_data = _find_task_result_data(task_executions, entry.task_name)
            search_summary = task_result_data.get("search_summary", {})
            task_output = (
                task_result_data.get("full_output", "")
                or task_result_data.get("output", "")
                or ""
            ).lower()

            intentional_bypass = (
                search_summary.get("model_knowledge_only")
                or search_summary.get("brave_degraded")
                or "intentionally bypassed" in task_output
            )

            if intentional_bypass:
                bypass_reason = (
                    search_summary.get("search_bypass_reason")
                    or "External searches intentionally bypassed"
                )
                issues.append({
                    "severity": "INFO",
                    "task_name": entry.task_name,
                    "workflow": task_workflow,
                    "issue": "External searches bypassed",
                    "detail": (
                        f"{entry.display_name} used model knowledge instead of external APIs. "
                        f"Reason: {bypass_reason}."
                    )
                })
            else:
                issues.append({
                    "severity": "CRITICAL",
                    "task_name": entry.task_name,
                    "workflow": task_workflow,
                    "issue": "No API calls made",
                    "detail": (
                        f"{entry.display_name} is expected to call external APIs "
                        f"but made 0 API calls. The evaluation data for this task is not "
                        f"backed by external research."
                    )
                })

        # 2. Tasks with all API calls failed
        if entry.api_calls_made > 0 and entry.api_calls_successful == 0:
            issues.append({
                "severity": "CRITICAL",
                "task_name": entry.task_name,
                "workflow": task_workflow,
                "issue": "All API calls failed",
                "detail": (
                    f"{entry.display_name} made {entry.api_calls_made} API call(s) "
                    f"but none succeeded. Results are not backed by real data."
                )
            })

        # 3. Tasks with PARTIAL reliability (some failures)
        if entry.data_reliability == "PARTIAL":
            issues.append({
                "severity": "WARNING",
                "task_name": entry.task_name,
                "workflow": task_workflow,
                "issue": "Partial data reliability",
                "detail": (
                    f"{entry.display_name} had {entry.api_calls_made - entry.api_calls_successful} "
                    f"failed API call(s) out of {entry.api_calls_made}. Some data may be incomplete."
                )
            })

        # 4. Tasks that "completed" but have no key findings and were expected to produce them
        # Only for tasks that use external APIs — local analysis tasks may not
        # produce structured findings that the extractor can parse
        if (entry.result_status.upper() in SUCCESS_STATUSES
                and not entry.key_findings
                and expects_api
                and "gut_check" not in entry.task_name
                and "validation" not in entry.task_name):
            issues.append({
                "severity": "INFO",
                "task_name": entry.task_name,
                "workflow": task_workflow,
                "issue": "No key findings extracted",
                "detail": (
                    f"{entry.display_name} completed but produced no structured findings. "
                    f"Review the task output for details."
                )
            })

        # 5. Tasks with non-success status (FAIL, BLOCKED, UNKNOWN, etc.)
        if entry.result_status.upper() not in SUCCESS_STATUSES:
            issues.append({
                "severity": "CRITICAL",
                "task_name": entry.task_name,
                "workflow": task_workflow,
                "issue": f"Task status: {entry.result_status}",
                "detail": (
                    f"{entry.display_name} did not complete successfully "
                    f"(status: {entry.result_status})."
                )
            })

    # 5b. Check for tasks that reported success but admit failure in output
    # (e.g. "I am unable to perform", "cannot provide", "not available")
    INABILITY_PHRASES = [
        "unable to perform",
        "cannot provide",
        "could not perform",
        "i cannot",
        "i am unable",
        "not available in my",
        "does not have the capability",
        "tool is not available",
        "tools are not available",
    ]
    for task_data in task_executions:
        task_name = task_data.get("task_name", "unknown_task")
        result_data = task_data.get("result_data", {}) or {}
        full_output = (
            result_data.get("full_output", "")
            or result_data.get("output", "")
            or ""
        ).lower()

        if not full_output:
            continue

        result_status = task_data.get("result_status", "UNKNOWN")
        if result_status.upper() not in SUCCESS_STATUSES:
            continue  # Already flagged in check #5

        for phrase in INABILITY_PHRASES:
            if phrase in full_output:
                metadata = TASK_METADATA.get(task_name, {})
                task_workflow = metadata.get("workflow", "unknown")
                display_name = metadata.get(
                    "display_name",
                    task_name.replace("_", " ").title()
                )

                # Downgrade to WARNING if search was intentionally bypassed
                search_summary = result_data.get("search_summary", {})
                intentional_bypass = (
                    search_summary.get("model_knowledge_only")
                    or search_summary.get("brave_degraded")
                    or "intentionally bypassed" in full_output
                )

                if intentional_bypass:
                    issues.append({
                        "severity": "INFO",
                        "task_name": task_name,
                        "workflow": task_workflow,
                        "issue": "Task used model knowledge due to search bypass",
                        "detail": (
                            f"{display_name} used model knowledge instead of external searches. "
                            f"Results should be independently verified."
                        )
                    })
                else:
                    issues.append({
                        "severity": "CRITICAL",
                        "task_name": task_name,
                        "workflow": task_workflow,
                        "issue": "Task reported success but did not perform its work",
                        "detail": (
                            f"{display_name} returned status {result_status} but its "
                            f"output indicates it was unable to complete the intended "
                            f"analysis (found: \"{phrase}\")."
                        )
                    })
                break  # One flag per task is enough

    # 6. Check for missing expected tasks (only those that call external APIs)
    executed_task_names = {e.task_name for e in audit_entries}
    expected_api_tasks = {
        name for name, meta in TASK_METADATA.items()
        if meta.get("expects_api_calls")
    }
    missing_tasks = expected_api_tasks - executed_task_names
    for missing in sorted(missing_tasks):
        meta = TASK_METADATA[missing]
        issues.append({
            "severity": "WARNING",
            "task_name": missing,
            "workflow": meta["workflow"],
            "issue": "Task not executed",
            "detail": (
                f"{meta['display_name']} ({meta['workflow']}) was expected but "
                f"has no execution record."
            )
        })

    return issues


def _compute_audit_health(issues: List[Dict[str, Any]]) -> str:
    """
    Compute overall audit health from integrity issues.
    Returns: "PASS" | "WARNING" | "FAIL"
    INFO-level issues do not affect health status.
    """
    critical_count = sum(1 for i in issues if i["severity"] == "CRITICAL")
    warning_count = sum(1 for i in issues if i["severity"] == "WARNING")

    if critical_count > 0:
        return "FAIL"
    elif warning_count > 0:
        return "WARNING"
    return "PASS"


def generate_evaluation_audit_log(
    tld_string: str,
    task_executions: List[Dict[str, Any]],
    include_raw_data: bool = False
) -> Dict[str, Any]:
    """
    Generate a complete audit log for an evaluation.

    Args:
        tld_string: The TLD string evaluated
        task_executions: List of task execution records from Supabase
        include_raw_data: Whether to include raw API call logs

    Returns:
        Complete audit log dictionary with narratives and summary
    """
    audit_entries = []
    workflow_summaries = {}

    # Process each task execution
    for task_data in task_executions:
        task_name = task_data.get("task_name", "unknown_task")
        entry = generate_task_narrative(task_name, task_data, tld_string)
        audit_entries.append(entry)

        # Aggregate by workflow
        workflow = entry.workflow
        if workflow not in workflow_summaries:
            workflow_summaries[workflow] = {
                "tasks_completed": 0,
                "total_api_calls": 0,
                "successful_api_calls": 0,
                "expected_api_tasks": 0,
                "local_only_tasks": 0,
                "data_sources": set(),
                "overall_reliability": "UNKNOWN",
                "status": "completed",
                "total_execution_time_seconds": 0,
            }

        summary = workflow_summaries[workflow]
        summary["tasks_completed"] += 1
        summary["total_api_calls"] += entry.api_calls_made
        summary["successful_api_calls"] += entry.api_calls_successful
        summary["data_sources"].update(entry.api_sources)
        if entry.expects_api_calls:
            summary["expected_api_tasks"] += 1
        else:
            summary["local_only_tasks"] += 1
        if entry.execution_time_seconds:
            summary["total_execution_time_seconds"] += entry.execution_time_seconds

    # Calculate overall reliability per workflow
    for workflow, summary in workflow_summaries.items():
        total = summary["total_api_calls"]
        successful = summary["successful_api_calls"]

        # If no tasks in this workflow expect API calls, reliability is N/A
        if summary["expected_api_tasks"] == 0:
            summary["overall_reliability"] = "N/A"
        elif total == 0:
            summary["overall_reliability"] = "NONE"
        elif successful == total:
            summary["overall_reliability"] = "FULL"
        elif successful == 0:
            summary["overall_reliability"] = "NONE"
        else:
            summary["overall_reliability"] = "PARTIAL"

        # Convert set to list for JSON serialization
        summary["data_sources"] = list(summary["data_sources"])

    # Run integrity checks
    integrity_issues = _run_integrity_checks(audit_entries, task_executions)
    audit_health = _compute_audit_health(integrity_issues)

    # Compute workflow-level status from integrity issues
    workflow_issues: Dict[str, List[Dict[str, Any]]] = {}
    for issue in integrity_issues:
        wf = issue.get("workflow", "unknown")
        if wf not in workflow_issues:
            workflow_issues[wf] = []
        workflow_issues[wf].append(issue)

    for workflow, summary in workflow_summaries.items():
        wf_issues = workflow_issues.get(workflow, [])
        has_critical = any(i["severity"] == "CRITICAL" for i in wf_issues)
        has_warning = any(i["severity"] == "WARNING" for i in wf_issues)
        if has_critical:
            summary["status"] = "failed"
        elif has_warning:
            summary["status"] = "completed_with_notes"
        else:
            summary["status"] = "completed"

    # Build the complete audit log
    audit_log = {
        "generated_at": datetime.utcnow().isoformat(),
        "tld_string": tld_string,
        "total_tasks": len(audit_entries),
        "audit_health": audit_health,
        "integrity_issues": integrity_issues,
        "workflow_summaries": workflow_summaries,
        "task_narratives": [
            {
                "task_name": e.task_name,
                "display_name": e.display_name,
                "workflow": e.workflow,
                "agent": e.agent,
                "api_calls": e.api_calls_made,
                "data_reliability": e.data_reliability,
                "key_findings": e.key_findings,
                "result_status": e.result_status,
                "narrative": e.narrative,
                "started_at": e.started_at,
                "completed_at": e.completed_at,
                "execution_time_seconds": e.execution_time_seconds,
                "expects_api_calls": e.expects_api_calls,
                "checks_performed": e.checks_performed,
                "actions_performed": e.actions_performed,
            }
            for e in audit_entries
        ]
    }

    if include_raw_data:
        audit_log["raw_task_data"] = task_executions

    return audit_log


def format_audit_log_markdown(audit_log: Dict[str, Any]) -> str:
    """
    Format the audit log as a human-readable Markdown document.

    Args:
        audit_log: The audit log dictionary from generate_evaluation_audit_log

    Returns:
        Formatted Markdown string
    """
    lines = []

    # Header
    lines.append(f"# Evaluation Audit Log: .{audit_log['tld_string']}")
    lines.append(f"*Generated: {audit_log['generated_at']}*")
    lines.append("")

    # Workflow Completion Summary
    audit_health = audit_log.get("audit_health", "UNKNOWN")
    integrity_issues = audit_log.get("integrity_issues", [])
    critical_issues = [i for i in integrity_issues if i["severity"] == "CRITICAL"]
    warning_issues = [i for i in integrity_issues if i["severity"] == "WARNING"]
    info_issues = [i for i in integrity_issues if i["severity"] == "INFO"]

    lines.append("## Workflow Completion Summary")
    lines.append("")

    if audit_health == "FAIL":
        lines.append(f"**{len(critical_issues)} issue(s) detected** that may affect evaluation quality.")
        lines.append("")
    elif audit_health == "WARNING":
        lines.append(f"All tasks completed. {len(warning_issues)} note(s) for review.")
        lines.append("")
    else:
        lines.append("All tasks completed successfully.")
        lines.append("")

    # Executive Summary
    lines.append(f"- **TLD String:** .{audit_log['tld_string']}")
    lines.append(f"- **Total Tasks:** {audit_log['total_tasks']}")
    lines.append("")

    # Workflow summaries
    for workflow, summary in audit_log.get("workflow_summaries", {}).items():
        workflow_display = workflow.replace("_", " ").title()
        status = summary.get("status", "completed")
        status_label = {"completed": "Completed", "completed_with_notes": "Completed*", "failed": "Failed"}.get(status, status)
        duration = summary.get("total_execution_time_seconds", 0)
        duration_str = f" ({int(duration)}s)" if duration else ""

        parts = [f"**{workflow_display}:** {status_label}{duration_str}"]
        parts.append(f"{summary['tasks_completed']} tasks")

        if summary.get("expected_api_tasks", 0) > 0:
            parts.append(f"{summary['successful_api_calls']}/{summary['total_api_calls']} API calls")
        else:
            parts.append("local analysis only")

        if summary.get("data_sources"):
            parts.append(f"Sources: {', '.join(summary['data_sources'])}")

        lines.append(f"- {', '.join(parts)}")
    lines.append("")

    # Notes section (only for non-INFO issues, or if there are critical/warning)
    if critical_issues or warning_issues:
        lines.append("### Notes")
        lines.append("")
        for issue in critical_issues:
            task_display = TASK_METADATA.get(issue["task_name"], {}).get(
                "display_name", issue["task_name"].replace("_", " ").title()
            )
            lines.append(f"- **{task_display}:** {issue['detail']}")
        for issue in warning_issues:
            task_display = TASK_METADATA.get(issue["task_name"], {}).get(
                "display_name", issue["task_name"].replace("_", " ").title()
            )
            lines.append(f"- {task_display}: {issue['detail']}")
        lines.append("")

    # Task-by-task narratives
    lines.append("## Task-by-Task Audit")
    lines.append("")

    current_workflow = None
    for task in audit_log.get("task_narratives", []):
        # Workflow header
        if task["workflow"] != current_workflow:
            current_workflow = task["workflow"]
            workflow_display = current_workflow.replace("_", " ").title()
            lines.append(f"### {workflow_display}")
            lines.append("")

        # Task entry
        lines.append(f"#### {task['display_name']}")
        lines.append(f"**Agent:** {task['agent']} | **Status:** {task['result_status']}")

        # Only show API calls for tasks that expect them
        if task.get("expects_api_calls"):
            lines.append(f"**API Calls:** {task['api_calls']} | "
                        f"**Data:** {task['data_reliability']}")
        else:
            lines.append("**Analysis:** Local (no external calls needed)")

        # Timestamps
        if task.get("started_at") or task.get("completed_at"):
            time_parts = []
            if task.get("started_at"):
                time_parts.append(f"Started: {task['started_at']}")
            if task.get("completed_at"):
                time_parts.append(f"Completed: {task['completed_at']}")
            if task.get("execution_time_seconds"):
                time_parts.append(f"Duration: {int(task['execution_time_seconds'])}s")
            lines.append(f"*{' | '.join(time_parts)}*")

        lines.append("")
        lines.append(f"> {task['narrative']}")
        lines.append("")

        if task.get("key_findings"):
            lines.append("**Findings:**")
            for finding in task["key_findings"]:
                lines.append(f"- {finding}")
            lines.append("")

        lines.append("---")
        lines.append("")

    # Footer
    lines.append("---")
    lines.append("*Audit log auto-generated from task execution data.*")

    return "\n".join(lines)


async def save_audit_log_to_supabase(
    supabase_client,
    evaluation_id: str,
    tld_string_id: str,
    audit_log: Dict[str, Any],
    markdown_content: str
) -> Optional[str]:
    """
    Save the audit log to Supabase audit_logs table.

    Args:
        supabase_client: Initialized Supabase client
        evaluation_id: The evaluation/workflow execution ID
        tld_string_id: The TLD string ID
        audit_log: The structured audit log dictionary
        markdown_content: The formatted Markdown content

    Returns:
        The audit log ID if saved successfully, None otherwise
    """
    import uuid

    try:
        record = {
            "id": str(uuid.uuid4()),
            "evaluation_id": evaluation_id,
            "tld_string_id": tld_string_id,
            "generated_at": audit_log["generated_at"],
            "audit_data": audit_log,
            "markdown_content": markdown_content,
            "total_tasks": audit_log["total_tasks"],
            "workflow_summaries": audit_log.get("workflow_summaries", {})
        }

        response = supabase_client.table("audit_logs").insert(record).execute()

        if response.data:
            logger.info(f"✅ Saved audit log {record['id']} for evaluation {evaluation_id}")
            return record["id"]
        else:
            logger.error(f"Failed to save audit log: {response}")
            return None

    except Exception as e:
        logger.error(f"Error saving audit log: {e}")
        return None


# Convenience function for generating audit from evaluation ID
async def generate_audit_for_evaluation(
    supabase_client,
    tld_string_id: str,
    save_to_db: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Generate and optionally save an audit log for a TLD string evaluation.

    Args:
        supabase_client: Initialized Supabase client
        tld_string_id: The TLD string ID to generate audit for
        save_to_db: Whether to save the audit log to Supabase

    Returns:
        The complete audit log dictionary
    """
    try:
        # Fetch task executions for this TLD string
        response = supabase_client.table("task_executions").select(
            "task_name, result_data, result_status, execution_time_seconds, agent_name, workflow_id, started_at, completed_at"
        ).eq("tld_string_id", tld_string_id).execute()

        if not response.data:
            logger.warning(f"No task executions found for TLD string ID: {tld_string_id}")
            return None

        # Get TLD string value
        tld_response = supabase_client.table("tld_strings").select("tld_string").eq("id", tld_string_id).execute()
        tld_string = tld_response.data[0]["tld_string"] if tld_response.data else "unknown"

        # Generate audit log
        audit_log = generate_evaluation_audit_log(tld_string, response.data)
        markdown_content = format_audit_log_markdown(audit_log)

        # Save if requested
        if save_to_db:
            # Use first workflow_id as evaluation_id
            evaluation_id = response.data[0].get("workflow_id", str(uuid.uuid4()))
            await save_audit_log_to_supabase(
                supabase_client,
                evaluation_id,
                tld_string_id,
                audit_log,
                markdown_content
            )

        return {
            "audit_log": audit_log,
            "markdown": markdown_content
        }

    except Exception as e:
        logger.error(f"Error generating audit for evaluation: {e}")
        return None
