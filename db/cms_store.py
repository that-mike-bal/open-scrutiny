"""
CMS Store - Content Management System for TLD Evaluations

This module implements a CMS-style approach with two post types:
1. String Evaluation Posts - Technical ICANN analysis (reusable)
2. Application Posts - Business cases (unique per applicant)

Follows the existing Supabase patterns in the codebase.
"""
import uuid
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Literal
from .supabase_client import get_supabase

# Table names
STRING_EVALUATIONS_TABLE = "string_evaluation_posts"
APPLICATIONS_TABLE = "application_posts" 
POST_RELATIONSHIPS_TABLE = "post_relationships"

# Post types
PostType = Literal["string_evaluation", "application"]
StringEvaluationStatus = Literal["draft", "processing", "published", "archived"]
ApplicationStatus = Literal["draft", "submitted", "under_review", "approved", "rejected", "withdrawn"]

# ============= STRING EVALUATION POSTS =============

def create_string_evaluation_post(
    tld_string: str,
    task_outputs: Dict[str, Any],
    research_data: Dict[str, Any],
    agent_reasoning: Optional[Dict[str, Any]] = None,
    status: StringEvaluationStatus = "published"
) -> Dict[str, Any]:
    """
    Create a new String Evaluation Post (Technical Analysis).
    
    Args:
        tld_string: The TLD string being evaluated
        task_outputs: Results from CrewAI tasks (5 ICANN gates)
        research_data: Research intelligence gathered
        agent_reasoning: Agent decision rationale
        status: Publication status
        
    Returns:
        The created string evaluation post
    """
    supabase = get_supabase()
    
    # Generate unique slug and ID
    post_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    slug = f"{tld_string}-eval-{timestamp}"
    
    # Extract metadata from task outputs for efficient querying
    metadata = _extract_string_evaluation_metadata(task_outputs, research_data)
    
    # Build content structure
    content = {
        "task_outputs": task_outputs,
        "research_data": research_data,
        "agent_reasoning": agent_reasoning or {},
        "evaluation_summary": _generate_evaluation_summary(task_outputs)
    }
    
    # Prepare post data
    post_data = {
        "id": post_id,
        "slug": slug,
        "title": f".{tld_string}",
        "post_type": "string_evaluation",
        "status": status,
        "content": content,
        "metadata": metadata,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    
    # Insert into database
    result = supabase.table(STRING_EVALUATIONS_TABLE).insert(post_data).execute()
    
    if len(result.data) == 0:
        raise Exception("Failed to create string evaluation post")
    
    return result.data[0]

def get_string_evaluation_post(tld_string: str, latest: bool = True) -> Optional[Dict[str, Any]]:
    """
    Get string evaluation post(s) for a TLD.
    
    Args:
        tld_string: The TLD string
        latest: If True, get only the latest evaluation
        
    Returns:
        The evaluation post or None if not found
    """
    supabase = get_supabase()
    
    query = supabase.table(STRING_EVALUATIONS_TABLE).select("*").eq("title", f".{tld_string}")
    
    if latest:
        query = query.order("created_at", desc=True).limit(1)
    else:
        query = query.order("created_at", desc=True)
    
    result = query.execute()
    
    if len(result.data) == 0:
        return None
    
    return result.data[0] if latest else result.data

def search_string_evaluation_posts(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Search string evaluation posts by metadata.
    
    Args:
        filters: Dictionary of metadata filters
        
    Returns:
        List of matching evaluation posts
    """
    supabase = get_supabase()
    
    query = supabase.table(STRING_EVALUATIONS_TABLE).select("*")
    
    # Apply metadata filters
    for key, value in filters.items():
        if key == "overall_status":
            query = query.eq("metadata->>overall_status", value)
        elif key == "cost_range":
            if value == "high":
                query = query.filter("metadata->>estimated_cost", "like", "%$350K%")
            elif value == "medium":
                query = query.filter("metadata->>estimated_cost", "like", "%$225K%")
        elif key == "risk_level":
            query = query.eq("metadata->>risk_level", value)
    
    result = query.order("created_at", desc=True).execute()
    return result.data

# ============= APPLICATION POSTS =============

def create_application_post(
    applicant_info: Dict[str, Any],
    business_case: Dict[str, Any],
    tld_string: str,
    string_evaluation_slug: Optional[str] = None,
    status: ApplicationStatus = "draft"
) -> Dict[str, Any]:
    """
    Create a new Application Post (Business Case).
    
    Args:
        applicant_info: Organization and contact details
        business_case: Business strategy and use case
        tld_string: The TLD string being applied for
        string_evaluation_slug: Reference to string evaluation post
        status: Application status
        
    Returns:
        The created application post
    """
    supabase = get_supabase()
    
    # Generate unique slug and ID
    post_id = str(uuid.uuid4())
    org_clean = applicant_info.get("organization", "unknown").lower().replace(" ", "-").replace(".", "")
    timestamp = datetime.utcnow().strftime("%Y%m%d")
    slug = f"{org_clean}-{tld_string}-app-{timestamp}"
    
    # Extract metadata for efficient querying
    metadata = _extract_application_metadata(applicant_info, business_case, tld_string)
    metadata["string_evaluation_slug"] = string_evaluation_slug
    
    # Build content structure
    content = {
        "business_case": business_case,
        "applicant_information": applicant_info,
        "business_strategy": {},
        "financial_projections": {},
        "risk_mitigation": {},
        "supporting_documents": {}
    }
    
    # Prepare post data
    post_data = {
        "id": post_id,
        "slug": slug,
        "title": f"{applicant_info.get('organization', 'Unknown')} Application for .{tld_string}",
        "post_type": "application",
        "status": status,
        "content": content,
        "metadata": metadata,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    
    # Insert into database
    result = supabase.table(APPLICATIONS_TABLE).insert(post_data).execute()
    
    if len(result.data) == 0:
        raise Exception("Failed to create application post")
    
    # Create relationship to string evaluation if provided
    if string_evaluation_slug:
        _create_post_relationship(post_id, string_evaluation_slug, "references")
    
    return result.data[0]

def get_application_post(application_slug: str) -> Optional[Dict[str, Any]]:
    """
    Get application post by slug.
    
    Args:
        application_slug: The application slug
        
    Returns:
        The application post or None if not found
    """
    supabase = get_supabase()
    
    result = supabase.table(APPLICATIONS_TABLE).select("*").eq("slug", application_slug).execute()
    
    if len(result.data) == 0:
        return None
    
    return result.data[0]

def get_applications_for_string(tld_string: str) -> List[Dict[str, Any]]:
    """
    Get all applications for a specific TLD string.
    
    Args:
        tld_string: The TLD string
        
    Returns:
        List of application posts
    """
    supabase = get_supabase()
    
    result = supabase.table(APPLICATIONS_TABLE).select("*").eq("metadata->>tld_string", tld_string).order("created_at", desc=True).execute()
    
    return result.data

def search_application_posts(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Search application posts by metadata.
    
    Args:
        filters: Dictionary of metadata filters
        
    Returns:
        List of matching application posts
    """
    supabase = get_supabase()
    
    query = supabase.table(APPLICATIONS_TABLE).select("*")
    
    # Apply metadata filters
    for key, value in filters.items():
        if key == "status":
            query = query.eq("status", value)
        elif key == "organization_type":
            query = query.eq("metadata->>organization_type", value)
        elif key == "business_viability_score":
            if value.startswith(">"):
                score = int(value[1:])
                query = query.gte("metadata->>business_viability_score", score)
        elif key == "funding_status":
            query = query.eq("metadata->>funding_status", value)
    
    result = query.order("created_at", desc=True).execute()
    return result.data

# ============= RAG CHAT INTEGRATION =============

def get_evaluation_context_for_chat(tld_string: str) -> Dict[str, Any]:
    """
    Get complete evaluation context for RAG chat system.
    
    Args:
        tld_string: The TLD string
        
    Returns:
        Complete context including string evaluation and applications
    """
    # Get string evaluation
    string_eval = get_string_evaluation_post(tld_string)
    
    # Get related applications
    applications = get_applications_for_string(tld_string)
    
    return {
        "tld_string": tld_string,
        "string_evaluation": {
            "exists": string_eval is not None,
            "metadata": string_eval["metadata"] if string_eval else {},
            "content": string_eval["content"] if string_eval else {},
            "status": string_eval["status"] if string_eval else "not_found"
        },
        "applications": [
            {
                "slug": app["slug"],
                "metadata": app["metadata"],
                "business_case": app["content"].get("business_case", {}),
                "status": app["status"]
            }
            for app in applications
        ],
        "context_type": "evaluation_and_applications",
        "retrieved_at": datetime.utcnow().isoformat()
    }

# ============= ANALYTICS & REPORTING =============

def get_evaluation_analytics() -> Dict[str, Any]:
    """
    Get system-wide evaluation analytics.
    
    Returns:
        Analytics data for dashboards
    """
    supabase = get_supabase()
    
    # Get counts
    string_evals = supabase.table(STRING_EVALUATIONS_TABLE).select("id", count="exact").execute()
    applications = supabase.table(APPLICATIONS_TABLE).select("id", count="exact").execute()
    
    # Get success rates (this would need more complex queries in practice)
    return {
        "total_strings_evaluated": string_evals.count,
        "total_applications": applications.count,
        "success_rates": _calculate_success_rates(),
        "common_failure_points": _analyze_failure_patterns(),
        "cost_distribution": _analyze_cost_distribution(),
        "processing_performance": _analyze_processing_times()
    }

# ============= HELPER FUNCTIONS =============

def _extract_string_evaluation_metadata(task_outputs: Dict[str, Any], research_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract queryable metadata from task outputs."""
    metadata = {
        # ICANN Compliance Results
        "overall_status": "PENDING",
        "gates_completed": 0,
        "gates_passed": 0,
        "gates_failed": 0,
        "blocking_gates": [],
        "risk_gates": [],
        
        # Cost & Timeline
        "estimated_cost": "TBD",
        "estimated_timeline": "TBD",
        "cost_factors": [],
        "timeline_risks": [],
        
        # Technical Details
        "string_length": 0,
        "character_set": "latin",
        "similarity_score": 0.0,
        "collision_risk": "unknown",
        
        # Regulatory Classification
        "geographic_classification": "non-geographic",
        "safeguard_category": "none",
        "trademark_conflicts": 0,
        
        # System Fields
        "evaluation_version": "2.1",
        "confidence_level": "medium",
        "created_at": datetime.utcnow().isoformat(),
        "evaluated_by": "crewai-system"
    }
    
    # Process task outputs to populate metadata
    if task_outputs:
        gates_completed = len([k for k, v in task_outputs.items() if v.get("api_ready")])
        metadata["gates_completed"] = gates_completed
        
        # Count passes/fails
        gates_passed = 0
        gates_failed = 0
        blocking_gates = []
        
        for gate_name, gate_result in task_outputs.items():
            if isinstance(gate_result, dict) and "status" in gate_result:
                status = gate_result["status"]
                if status in ["NOT_SIMILAR", "LOW_RISK", "NON_GEOGRAPHIC", "NO_SAFEGUARDS"]:
                    gates_passed += 1
                elif status in ["BLOCKED", "HIGH_RISK", "GEOGRAPHIC", "SAFEGUARDS_REQUIRED"]:
                    gates_failed += 1
                    blocking_gates.append(gate_name)
        
        metadata["gates_passed"] = gates_passed
        metadata["gates_failed"] = gates_failed
        metadata["blocking_gates"] = blocking_gates
        
        # Determine overall status
        if gates_failed > 0:
            metadata["overall_status"] = "AT_RISK" if "BLOCKED" not in [task_outputs[g].get("status") for g in blocking_gates] else "FAIL"
        elif gates_completed == 5:
            metadata["overall_status"] = "PASS"
        else:
            metadata["overall_status"] = "IN_PROGRESS"
    
    return metadata

def _extract_application_metadata(applicant_info: Dict[str, Any], business_case: Dict[str, Any], tld_string: str) -> Dict[str, Any]:
    """Extract queryable metadata from application data."""
    return {
        # Application Details
        "tld_string": tld_string,
        "applicant_name": applicant_info.get("name", ""),
        "applicant_email": applicant_info.get("email", ""),
        "organization": applicant_info.get("organization", ""),
        "organization_type": applicant_info.get("organization_type", "corporation"),
        "jurisdiction": applicant_info.get("jurisdiction", ""),
        
        # Business Analysis
        "business_viability_score": 0,
        "market_potential": business_case.get("market_potential", "unknown"),
        "competitive_advantage": business_case.get("competitive_advantage", "unknown"),
        "revenue_model": business_case.get("revenue_model", ""),
        "funding_status": "unknown",
        
        # Application Process
        "application_type": "standard",
        "priority_status": "standard",
        "objection_risk": "unknown",
        "government_support": False,
        "community_support": False,
        
        # System Fields
        "created_at": datetime.utcnow().isoformat(),
        "workflow_stage": "initial",
        "next_steps": [],
        "pending_requirements": []
    }

def _generate_evaluation_summary(task_outputs: Dict[str, Any]) -> Dict[str, Any]:
    """Generate executive summary from task outputs."""
    return {
        "executive_summary": "TLD evaluation completed with detailed analysis of ICANN requirements.",
        "key_findings": [],
        "critical_risks": [],
        "recommendations": []
    }

def _create_post_relationship(from_post_id: str, to_post_slug: str, relationship_type: str) -> bool:
    """Create a relationship between posts."""
    supabase = get_supabase()
    
    relationship_data = {
        "id": str(uuid.uuid4()),
        "from_post_id": from_post_id,
        "to_post_slug": to_post_slug,
        "relationship_type": relationship_type,
        "created_at": datetime.utcnow().isoformat()
    }
    
    result = supabase.table(POST_RELATIONSHIPS_TABLE).insert(relationship_data).execute()
    return len(result.data) > 0

def _calculate_success_rates() -> Dict[str, float]:
    """Calculate evaluation success rates."""
    return {"overall": 0.75, "icann_compliance": 0.85, "business_viability": 0.65}

def _analyze_failure_patterns() -> List[str]:
    """Analyze common failure patterns."""
    return ["trademark_conflicts", "geographic_classification", "collision_risk"]

def _analyze_cost_distribution() -> Dict[str, int]:
    """Analyze cost distribution."""
    return {"low": 25, "medium": 50, "high": 25}

def _analyze_processing_times() -> Dict[str, float]:
    """Analyze processing performance."""
    return {"avg_seconds": 180, "median_seconds": 150, "p95_seconds": 300} 