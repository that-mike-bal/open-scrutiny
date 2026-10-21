"""
API Call Logger — ContextVar-based logging for tool-level API calls.

Accumulates structured records during tool execution so the pipeline
can persist them into result_data JSONB without touching CrewAI internals.

Also provides a trademark_audit_log for per-result filtering diagnostics.
"""

import logging
import time
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Each workflow run gets its own list via copy-on-write semantics.
_api_call_log: ContextVar[List[Dict[str, Any]]] = ContextVar(
    "api_call_log", default=[]
)

# Trademark-specific audit: per-result filtering detail
_trademark_audit_log: ContextVar[List[Dict[str, Any]]] = ContextVar(
    "trademark_audit_log", default=[]
)


def log_api_call(
    tool_name: str,
    endpoint: str,
    method: str,
    status_code: Optional[int],
    response_time_ms: float,
    success: bool,
    error: Optional[str] = None,
) -> None:
    """Append a single API-call record to the current context's log."""
    record = {
        "tool_name": tool_name,
        "api_endpoint": endpoint,
        "http_method": method,
        "status_code": status_code,
        "response_time_ms": round(response_time_ms, 1),
        "success": success,
        "error": error,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    try:
        log = _api_call_log.get()
    except LookupError:
        log = []
        _api_call_log.set(log)
    log.append(record)


def get_api_call_log() -> List[Dict[str, Any]]:
    """Return the accumulated API-call records for the current context."""
    try:
        return list(_api_call_log.get())
    except LookupError:
        return []


def clear_api_call_log() -> None:
    """Reset the log for a new workflow run."""
    _api_call_log.set([])
    _trademark_audit_log.set([])


def log_trademark_audit(record: Dict[str, Any]) -> None:
    """Append a trademark audit record to the current context's log."""
    try:
        log = _trademark_audit_log.get()
    except LookupError:
        log = []
        _trademark_audit_log.set(log)
    log.append(record)


def get_trademark_audit_log() -> List[Dict[str, Any]]:
    """Return the accumulated trademark audit records for the current context."""
    try:
        return list(_trademark_audit_log.get())
    except LookupError:
        return []


def compute_tool_execution_summary(
    api_calls: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Aggregate per-tool stats and an overall data_reliability verdict.

    Returns a dict like:
      {
        "TrademarkCheckerTool": {
          "total_calls": 3, "successful_calls": 3, "failed_calls": 0,
          "all_data_is_real": True
        },
        "overall": {
          "total_api_calls": 4, "total_successful": 3, "total_failed": 1,
          "data_reliability": "PARTIAL"
        }
      }
    """
    per_tool: Dict[str, Dict[str, Any]] = {}
    total_ok = 0
    total_fail = 0

    for call in api_calls:
        name = call.get("tool_name", "unknown")
        bucket = per_tool.setdefault(
            name,
            {"total_calls": 0, "successful_calls": 0, "failed_calls": 0},
        )
        bucket["total_calls"] += 1
        if call.get("success"):
            bucket["successful_calls"] += 1
            total_ok += 1
        else:
            bucket["failed_calls"] += 1
            total_fail += 1

    # Derive per-tool boolean
    for bucket in per_tool.values():
        bucket["all_data_is_real"] = bucket["failed_calls"] == 0

    total = total_ok + total_fail
    if total == 0:
        reliability = "NONE"
    elif total_fail == 0:
        reliability = "FULL"
    elif total_ok == 0:
        reliability = "NONE"
    else:
        reliability = "PARTIAL"

    per_tool["overall"] = {
        "total_api_calls": total,
        "total_successful": total_ok,
        "total_failed": total_fail,
        "data_reliability": reliability,
    }
    return per_tool


# ---------------------------------------------------------------------------
# Per-task API call attribution
# ---------------------------------------------------------------------------

# Maps the tool_name string passed to logged_get()/logged_post() → the
# short name used in TASK_METADATA["tools"] lists.
TOOL_CLASS_TO_SHORT_NAME: Dict[str, str] = {
    "DeepResearchLegalTool": "deep_research_legal_analyzer",
    "EnhancedTrademarkCheckerTool": "enhanced_trademark_analyzer",
    "PatentCheckerTool": "patent_analyzer",
    "BraveWebSearchTool": "brave_web_search",
    "BraveWebSearchTool/FirecrawlFallback": "brave_web_search",
    "TrademarkCheckerTool": "enhanced_trademark_analyzer",  # legacy
}


def partition_api_calls_by_task(
    api_calls: List[Dict[str, Any]],
    task_names: List[str],
    task_metadata: Dict[str, Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    """Partition a workflow-level API call log into per-task call lists.

    Uses the ``tool_name`` field in each log entry to match calls to tasks
    via the *task_metadata* ``tools`` list.  For shared tools (e.g.
    ``brave_web_search`` used by two tasks), calls are split using
    timestamp-gap clustering since CrewAI executes tasks sequentially.

    Args:
        api_calls: Full workflow API call log (from ``get_api_call_log()``).
        task_names: Ordered list of task names as they executed.
        task_metadata: ``TASK_METADATA`` dict mapping task_name → {tools, …}.

    Returns:
        Dict mapping each task_name → its subset of API call entries.
    """
    # Initialise empty buckets for every task
    result: Dict[str, List[Dict[str, Any]]] = {name: [] for name in task_names}

    if not api_calls:
        return result

    # Build reverse map: tool_short_name → [task_names] (in execution order)
    tool_to_tasks: Dict[str, List[str]] = {}
    for task_name in task_names:
        meta = task_metadata.get(task_name, {})
        for tool_short in meta.get("tools", []):
            tool_to_tasks.setdefault(tool_short, []).append(task_name)

    # Group API calls by their tool short name
    calls_by_tool: Dict[str, List[Dict[str, Any]]] = {}
    for call in api_calls:
        tool_class = call.get("tool_name", "unknown")
        short_name = TOOL_CLASS_TO_SHORT_NAME.get(tool_class)
        if short_name and short_name in tool_to_tasks:
            calls_by_tool.setdefault(short_name, []).append(call)
        else:
            logger.debug(
                "API call from unrecognised tool %r — not attributed to any task",
                tool_class,
            )

    # Assign calls from exclusive tools (used by exactly one task)
    for short_name, owning_tasks in tool_to_tasks.items():
        if len(owning_tasks) == 1:
            result[owning_tasks[0]].extend(calls_by_tool.pop(short_name, []))

    # Assign calls from shared tools via timestamp-gap clustering
    for short_name, owning_tasks in tool_to_tasks.items():
        if len(owning_tasks) <= 1:
            continue
        calls = calls_by_tool.pop(short_name, [])
        if not calls:
            continue

        calls.sort(key=lambda c: c.get("timestamp", ""))
        clusters = _cluster_calls_by_time_gap(calls, len(owning_tasks))
        for i, cluster in enumerate(clusters):
            if i < len(owning_tasks):
                result[owning_tasks[i]].extend(cluster)

    return result


def _cluster_calls_by_time_gap(
    calls: List[Dict[str, Any]],
    num_clusters: int,
) -> List[List[Dict[str, Any]]]:
    """Split sorted API calls into *num_clusters* groups at the largest gaps.

    Finds the ``num_clusters - 1`` largest time gaps between consecutive
    entries and uses them as cluster boundaries.  Falls back to assigning
    all calls to a single cluster if timestamps cannot be parsed.
    """
    if num_clusters <= 1 or len(calls) <= 1:
        return [calls]

    # Parse timestamps
    timestamps: List[Optional[datetime]] = []
    for call in calls:
        ts_str = call.get("timestamp", "")
        try:
            timestamps.append(datetime.fromisoformat(ts_str.replace("Z", "+00:00")))
        except (ValueError, TypeError):
            timestamps.append(None)

    # Compute gaps
    gaps: List[tuple] = []  # (gap_seconds, split_index)
    for i in range(1, len(calls)):
        if timestamps[i] and timestamps[i - 1]:
            gap = (timestamps[i] - timestamps[i - 1]).total_seconds()
            gaps.append((gap, i))
        else:
            gaps.append((0.0, i))

    if not gaps:
        return [calls]

    # Pick the largest (num_clusters - 1) gaps as split points
    gaps.sort(key=lambda g: g[0], reverse=True)
    split_indices = sorted(g[1] for g in gaps[: num_clusters - 1])

    clusters: List[List[Dict[str, Any]]] = []
    prev = 0
    for idx in split_indices:
        clusters.append(calls[prev:idx])
        prev = idx
    clusters.append(calls[prev:])

    return clusters
