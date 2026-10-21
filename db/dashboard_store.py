"""
Dashboard Store

This module handles database operations optimized for dashboard display.
It provides efficient queries for dashboard cards and summary data.
"""
from typing import Dict, Any, List, Optional
from .supabase_client import get_supabase

# Table names
APPLICATIONS_TABLE = "applications"
EVALUATIONS_TABLE = "evaluations"
APPLICATION_PROGRESS_VIEW = "application_progress"

def get_dashboard_applications() -> List[Dict[str, Any]]:
    """
    Get applications optimized for dashboard display.
    
    Returns:
        List of applications with dashboard-specific fields
    """
    supabase = get_supabase()
    
    # Get applications with related data in a single query
    result = supabase.table(APPLICATIONS_TABLE).select("""
        id,
        tld_string,
        use_case,
        applicant_name,
        applicant_email,
        organization,
        status,
        created_at,
        updated_at,
        evaluation_id
    """).order("created_at", desc=True).execute()
    
    # Transform data to match frontend expectations
    dashboard_apps = []
    for app in result.data:
        # Ensure we get the organization name properly
        organization = app.get("organization", "")
        applicant_name = app.get("applicant_name", "")
        org_name = organization if organization else (applicant_name if applicant_name else "Unknown Organization")
        
        dashboard_app = {
            "id": app["id"],
            "title": f".{app['tld_string']}",
            "slug": app["tld_string"],
            "_source": "dashboard_store",  # Debug marker
            "tldString": app["tld_string"],
            "useCase": app["use_case"],
            "status": app["status"],
            "createdAt": app["created_at"],
            "updatedAt": app["updated_at"],
            
            # Organization info
            "organizationName": org_name,
            "contactName": app.get("applicant_name"),
            "contactEmail": app.get("applicant_email"),
            
            # Legacy compatibility
            "applicantName": app.get("applicant_name"),
            "applicantEmail": app.get("applicant_email"),
            "organization": app.get("organization"),
            
            # Evaluation data
            "evaluationId": app.get("evaluation_id"),
            "score": None,  # Will be populated from evaluations table if needed
            "passed": None,  # Will be populated from evaluations table if needed
            
            # Default values for new schema fields
            "versionCount": 1,
            "organizationType": None,
            "jurisdiction": None,
            "currentVersionId": None,
            "createdBy": None,
            "sharedWith": [],
            "workflowId": None,
            "overallStatus": None,
            "icannCompliant": None,
            "icannComplianceStatus": None,
            "icannFailureReason": None,
            "strengthScore": None,
            "strengthPassed": None,
            "strengthRecommendation": None,
            "recommendationLevel": None,
            "keyStrengths": [],
            "keyWeaknesses": [],
            "totalFlags": 0,
            "criticalFlags": 0,
            "openFlags": 0,
            "lastEditedAt": None,
            "submittedAt": None,
            "approvedAt": None
        }
        dashboard_apps.append(dashboard_app)
    
    return dashboard_apps

def get_dashboard_stats() -> Dict[str, Any]:
    """
    Get summary statistics for the dashboard.
    
    Returns:
        Dictionary with dashboard statistics
    """
    supabase = get_supabase()
    
    # Get total applications count
    apps_result = supabase.table(APPLICATIONS_TABLE).select("id", count="exact").execute()
    total_apps = apps_result.count
    
    # Get applications by status
    status_result = supabase.table(APPLICATIONS_TABLE).select("status").execute()
    status_counts = {}
    for app in status_result.data:
        status = app["status"]
        status_counts[status] = status_counts.get(status, 0) + 1
    
    # Get evaluation statistics from evaluations table if it exists, otherwise use application data
    try:
        eval_result = supabase.table(EVALUATIONS_TABLE).select("passed").execute()
        passed_count = sum(1 for eval in eval_result.data if eval.get("passed"))
        evaluated_count = len(eval_result.data)
    except:
        # Fallback: count applications with evaluation_id as evaluated
        eval_result = supabase.table(APPLICATIONS_TABLE).select("evaluation_id").not_.is_("evaluation_id", "null").execute()
        evaluated_count = len(eval_result.data)
        passed_count = 0  # We don't have evaluation results without the evaluations table
    
    return {
        "totalApplications": total_apps,
        "statusCounts": status_counts,
        "evaluatedApplications": evaluated_count,
        "passedEvaluations": passed_count,
        "pendingEvaluations": total_apps - evaluated_count,
        "successRate": (passed_count / evaluated_count * 100) if evaluated_count > 0 else 0
    }

def get_recent_activity(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get recent application activity for dashboard.
    
    Args:
        limit: Maximum number of recent activities to return
        
    Returns:
        List of recent activities
    """
    supabase = get_supabase()
    
    # Get recent applications and updates
    result = supabase.table(APPLICATIONS_TABLE).select("""
        id,
        tld_string,
        status,
        created_at,
        updated_at,
        applicant_name,
        organization
    """).order("updated_at", desc=True).limit(limit).execute()
    
    activities = []
    for app in result.data:
        activities.append({
            "id": app["id"],
            "type": "application_update",
            "tldString": app["tld_string"],
            "status": app["status"],
            "timestamp": app["updated_at"],
            "description": f"Application for .{app['tld_string']} updated to {app['status']}",
            "applicantName": app.get("applicant_name") or app.get("organization")
        })
    
    return activities

def search_applications(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Search applications by TLD string, use case, or applicant name.
    
    Args:
        query: Search query string
        limit: Maximum number of results to return
        
    Returns:
        List of matching applications
    """
    supabase = get_supabase()
    
    # Search across multiple fields
    result = supabase.table(APPLICATIONS_TABLE).select("""
        id,
        tld_string,
        use_case,
        applicant_name,
        organization,
        status,
        created_at,
        score,
        passed
    """).or_(
        f"tld_string.ilike.%{query}%,"
        f"use_case.ilike.%{query}%,"
        f"applicant_name.ilike.%{query}%,"
        f"organization.ilike.%{query}%"
    ).limit(limit).execute()
    
    return result.data

def get_application_summary(application_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a summary of an application for dashboard preview.
    
    Args:
        application_id: The application ID
        
    Returns:
        Application summary or None if not found
    """
    supabase = get_supabase()
    
    result = supabase.table(APPLICATIONS_TABLE).select("""
        id,
        tld_string,
        use_case,
        applicant_name,
        applicant_email,
        organization,
        status,
        created_at,
        updated_at,
        score,
        passed,
        summary
    """).eq("id", application_id).execute()
    
    if not result.data:
        return None
    
    app = result.data[0]
    return {
        "id": app["id"],
        "tldString": app["tld_string"],
        "useCase": app["use_case"][:200] + "..." if len(app["use_case"]) > 200 else app["use_case"],
        "applicantName": app.get("applicant_name"),
        "organization": app.get("organization"),
        "status": app["status"],
        "createdAt": app["created_at"],
        "score": app.get("score"),
        "passed": app.get("passed"),
        "summary": app.get("summary")
    } 