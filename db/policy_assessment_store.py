"""
Policy Assessment Store

This module handles database operations for policy assessment tables:
- Geographic names assessments
- Safeguard assessments  
- Enhanced GAC risk assessments
"""
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from .supabase_client import get_supabase

# Table names
GEOGRAPHIC_NAMES_TABLE = "geographic_names_assessments"
SAFEGUARD_ASSESSMENTS_TABLE = "safeguard_assessments"
GAC_RISK_RESULTS_TABLE = "gac_risk_results"

# =====================================================
# GEOGRAPHIC NAMES ASSESSMENT
# =====================================================

def save_geographic_names_assessment(
    task_execution_id: str,
    tld_string: str,
    assessment_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Save geographic names assessment results.
    
    Args:
        task_execution_id: The task execution ID
        tld_string: The TLD string
        assessment_data: Assessment results
        
    Returns:
        The created assessment record
    """
    supabase = get_supabase()
    
    # Generate a UUID
    assessment_id = str(uuid.uuid4())
    
    # Prepare data with defaults
    assessment_record = {
        "id": assessment_id,
        "task_execution_id": task_execution_id,
        "tld_string": tld_string,
        "is_geographic_name": assessment_data.get("is_geographic_name", False),
        "geographic_type": assessment_data.get("geographic_type", "none"),
        "specific_matches": assessment_data.get("specific_matches", {}),
        "major_language_variants": assessment_data.get("major_language_variants", {}),
        "cultural_name_variations": assessment_data.get("cultural_name_variations", {}),
        "transliteration_matches": assessment_data.get("transliteration_matches", {}),
        "documentation_required": assessment_data.get("documentation_required", False),
        "relevant_authorities": assessment_data.get("relevant_authorities", {}),
        "special_requirements": assessment_data.get("special_requirements"),
        "approval_complexity": assessment_data.get("approval_complexity", "low"),
        "gac_objection_risk": assessment_data.get("gac_objection_risk", "low"),
        "multi_government_concerns": assessment_data.get("multi_government_concerns"),
        "recommendation": assessment_data.get("recommendation", "proceed"),
        "confidence_score": assessment_data.get("confidence_score", 0.75),
        "conservative_assessment_flag": assessment_data.get("conservative_assessment_flag", False),
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    
    # Insert data
    result = supabase.table(GEOGRAPHIC_NAMES_TABLE).insert(assessment_record).execute()
    
    if len(result.data) == 0:
        raise Exception("Failed to save geographic names assessment")
    
    return result.data[0]

def get_geographic_names_assessment(task_execution_id: str) -> Optional[Dict[str, Any]]:
    """
    Get geographic names assessment by task execution ID.
    
    Args:
        task_execution_id: The task execution ID
        
    Returns:
        The assessment data or None if not found
    """
    supabase = get_supabase()
    
    result = supabase.table(GEOGRAPHIC_NAMES_TABLE).select("*").eq("task_execution_id", task_execution_id).execute()
    
    if len(result.data) == 0:
        return None
    
    return result.data[0]

def get_geographic_assessments_for_tld(tld_string: str) -> List[Dict[str, Any]]:
    """
    Get all geographic assessments for a TLD string.
    
    Args:
        tld_string: The TLD string
        
    Returns:
        List of assessment records
    """
    supabase = get_supabase()
    
    result = supabase.table(GEOGRAPHIC_NAMES_TABLE).select("*").eq("tld_string", tld_string).order("created_at", desc=True).execute()
    
    return result.data

# =====================================================
# SAFEGUARD ASSESSMENT
# =====================================================

def save_safeguard_assessment(
    task_execution_id: str,
    tld_string: str,
    assessment_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Save safeguard assessment results.
    
    Args:
        task_execution_id: The task execution ID
        tld_string: The TLD string
        assessment_data: Assessment results
        
    Returns:
        The created assessment record
    """
    supabase = get_supabase()
    
    # Generate a UUID
    assessment_id = str(uuid.uuid4())
    
    # Prepare data with defaults
    assessment_record = {
        "id": assessment_id,
        "task_execution_id": task_execution_id,
        "tld_string": tld_string,
        
        # ICANN Questions 175-180
        "q175_consumer_trust": assessment_data.get("q175_consumer_trust", False),
        "q175_reasoning": assessment_data.get("q175_reasoning"),
        "q176_consumer_risk": assessment_data.get("q176_consumer_risk", False),
        "q176_reasoning": assessment_data.get("q176_reasoning"),
        "q177_licensing_required": assessment_data.get("q177_licensing_required", False),
        "q177_reasoning": assessment_data.get("q177_reasoning"),
        "q178_government_oversight": assessment_data.get("q178_government_oversight", False),
        "q178_reasoning": assessment_data.get("q178_reasoning"),
        "q179_harassment_potential": assessment_data.get("q179_harassment_potential", False),
        "q179_reasoning": assessment_data.get("q179_reasoning"),
        "q180_government_function": assessment_data.get("q180_government_function", False),
        "q180_reasoning": assessment_data.get("q180_reasoning"),
        
        # Safeguard requirements
        "safeguards_1_3_required": assessment_data.get("safeguards_1_3_required", False),
        "safeguards_1_8_required": assessment_data.get("safeguards_1_8_required", False),
        "safeguards_1_9_required": assessment_data.get("safeguards_1_9_required", False),
        "safeguards_special_required": assessment_data.get("safeguards_special_required", False),
        
        # Multi-language analysis
        "alternative_meanings": assessment_data.get("alternative_meanings", {}),
        "cultural_sensitivities": assessment_data.get("cultural_sensitivities", {}),
        "informal_usage_concerns": assessment_data.get("informal_usage_concerns", {}),
        
        # Registry Agreement impact
        "contractual_safeguards": assessment_data.get("contractual_safeguards"),
        "operational_requirements": assessment_data.get("operational_requirements"),
        "implementation_complexity": assessment_data.get("implementation_complexity", "low"),
        
        # Overall assessment
        "safeguard_risk_level": assessment_data.get("safeguard_risk_level", "none"),
        "conservative_assessment_flag": assessment_data.get("conservative_assessment_flag", False),
        "recommendation": assessment_data.get("recommendation", "proceed"),
        
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    
    # Insert data
    result = supabase.table(SAFEGUARD_ASSESSMENTS_TABLE).insert(assessment_record).execute()
    
    if len(result.data) == 0:
        raise Exception("Failed to save safeguard assessment")
    
    return result.data[0]

def get_safeguard_assessment(task_execution_id: str) -> Optional[Dict[str, Any]]:
    """
    Get safeguard assessment by task execution ID.
    
    Args:
        task_execution_id: The task execution ID
        
    Returns:
        The assessment data or None if not found
    """
    supabase = get_supabase()
    
    result = supabase.table(SAFEGUARD_ASSESSMENTS_TABLE).select("*").eq("task_execution_id", task_execution_id).execute()
    
    if len(result.data) == 0:
        return None
    
    return result.data[0]

def get_safeguard_assessments_for_tld(tld_string: str) -> List[Dict[str, Any]]:
    """
    Get all safeguard assessments for a TLD string.
    
    Args:
        tld_string: The TLD string
        
    Returns:
        List of assessment records
    """
    supabase = get_supabase()
    
    result = supabase.table(SAFEGUARD_ASSESSMENTS_TABLE).select("*").eq("tld_string", tld_string).order("created_at", desc=True).execute()
    
    return result.data

# =====================================================
# ENHANCED GAC RISK ASSESSMENT
# =====================================================

def update_gac_risk_assessment(
    task_execution_id: str,
    enhanced_data: Dict[str, Any]
) -> bool:
    """
    Update existing GAC risk assessment with enhanced policy data.
    
    Args:
        task_execution_id: The task execution ID
        enhanced_data: Enhanced assessment data
        
    Returns:
        True if successful, False otherwise
    """
    supabase = get_supabase()
    
    # Prepare update data
    update_data = {}
    
    # Add enhanced fields if provided
    if "pattern_match_risk" in enhanced_data:
        update_data["pattern_match_risk"] = enhanced_data["pattern_match_risk"]
    if "multi_government_risk" in enhanced_data:
        update_data["multi_government_risk"] = enhanced_data["multi_government_risk"]
    if "religious_sensitivities" in enhanced_data:
        update_data["religious_sensitivities"] = enhanced_data["religious_sensitivities"]
    if "ethnic_cultural_concerns" in enhanced_data:
        update_data["ethnic_cultural_concerns"] = enhanced_data["ethnic_cultural_concerns"]
    if "political_terminology" in enhanced_data:
        update_data["political_terminology"] = enhanced_data["political_terminology"]
    if "historical_conflicts" in enhanced_data:
        update_data["historical_conflicts"] = enhanced_data["historical_conflicts"]
    if "diplomatic_strategy" in enhanced_data:
        update_data["diplomatic_strategy"] = enhanced_data["diplomatic_strategy"]
    if "key_stakeholders" in enhanced_data:
        update_data["key_stakeholders"] = enhanced_data["key_stakeholders"]
    if "expert_consultation_required" in enhanced_data:
        update_data["expert_consultation_required"] = enhanced_data["expert_consultation_required"]
    
    if not update_data:
        return False
    
    # Update the record
    result = supabase.table(GAC_RISK_RESULTS_TABLE).update(update_data).eq("task_execution_id", task_execution_id).execute()
    
    return len(result.data) > 0

def get_enhanced_gac_risk_assessment(task_execution_id: str) -> Optional[Dict[str, Any]]:
    """
    Get enhanced GAC risk assessment by task execution ID.
    
    Args:
        task_execution_id: The task execution ID
        
    Returns:
        The assessment data or None if not found
    """
    supabase = get_supabase()
    
    result = supabase.table(GAC_RISK_RESULTS_TABLE).select("*").eq("task_execution_id", task_execution_id).execute()
    
    if len(result.data) == 0:
        return None
    
    return result.data[0]

# =====================================================
# COMPREHENSIVE POLICY ASSESSMENT
# =====================================================

def get_comprehensive_policy_assessment(tld_string: str) -> Dict[str, Any]:
    """
    Get comprehensive policy assessment for a TLD string.
    
    Args:
        tld_string: The TLD string
        
    Returns:
        Comprehensive assessment data
    """
    supabase = get_supabase()
    
    try:
        # Use the utility function
        result = supabase.rpc('get_policy_assessment_summary', {'tld_string_input': tld_string}).execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]
        else:
            return {
                "tld_string": tld_string,
                "is_geographic": False,
                "geographic_risk": "low",
                "safeguard_risk": "none",
                "gac_risk": "UNKNOWN",
                "overall_policy_risk": "UNKNOWN",
                "requires_expert_review": False,
                "key_concerns": []
            }
    except Exception as e:
        print(f"Error getting comprehensive policy assessment: {e}")
        return {
            "tld_string": tld_string,
            "error": str(e),
            "overall_policy_risk": "ERROR",
            "requires_expert_review": True,
            "key_concerns": ["Error retrieving assessment data"]
        }

def get_policy_assessment_dashboard_data() -> Dict[str, Any]:
    """
    Get dashboard data for policy assessments.
    
    Returns:
        Dashboard statistics and data
    """
    supabase = get_supabase()
    
    try:
        # Get geographic assessments stats
        geo_result = supabase.table(GEOGRAPHIC_NAMES_TABLE).select("is_geographic_name, gac_objection_risk").execute()
        
        # Get safeguard assessments stats
        safeguard_result = supabase.table(SAFEGUARD_ASSESSMENTS_TABLE).select("safeguard_risk_level").execute()
        
        # Get GAC risk stats
        gac_result = supabase.table(GAC_RISK_RESULTS_TABLE).select("overall_risk_level, expert_consultation_required").execute()
        
        # Calculate statistics
        total_geographic = len(geo_result.data)
        geographic_names = sum(1 for item in geo_result.data if item.get("is_geographic_name"))
        high_geo_risk = sum(1 for item in geo_result.data if item.get("gac_objection_risk") == "high")
        
        total_safeguard = len(safeguard_result.data)
        special_safeguards = sum(1 for item in safeguard_result.data if item.get("safeguard_risk_level") == "special")
        
        total_gac = len(gac_result.data)
        expert_consultation = sum(1 for item in gac_result.data if item.get("expert_consultation_required"))
        high_gac_risk = sum(1 for item in gac_result.data if item.get("overall_risk_level") == "HIGH_RISK")
        
        return {
            "geographic_assessments": {
                "total": total_geographic,
                "geographic_names": geographic_names,
                "high_risk": high_geo_risk,
                "percentage_geographic": (geographic_names / total_geographic * 100) if total_geographic > 0 else 0
            },
            "safeguard_assessments": {
                "total": total_safeguard,
                "special_safeguards": special_safeguards,
                "percentage_special": (special_safeguards / total_safeguard * 100) if total_safeguard > 0 else 0
            },
            "gac_assessments": {
                "total": total_gac,
                "expert_consultation_required": expert_consultation,
                "high_risk": high_gac_risk,
                "percentage_expert": (expert_consultation / total_gac * 100) if total_gac > 0 else 0
            },
            "overall": {
                "total_assessments": max(total_geographic, total_safeguard, total_gac),
                "high_risk_count": high_geo_risk + special_safeguards + high_gac_risk,
                "expert_review_required": expert_consultation
            }
        }
        
    except Exception as e:
        print(f"Error getting policy assessment dashboard data: {e}")
        return {
            "error": str(e),
            "geographic_assessments": {"total": 0, "geographic_names": 0, "high_risk": 0},
            "safeguard_assessments": {"total": 0, "special_safeguards": 0},
            "gac_assessments": {"total": 0, "expert_consultation_required": 0, "high_risk": 0},
            "overall": {"total_assessments": 0, "high_risk_count": 0, "expert_review_required": 0}
        }

# =====================================================
# SEARCH AND FILTERING
# =====================================================

def search_policy_assessments(
    search_filters: Dict[str, Any],
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Search policy assessments with filters.
    
    Args:
        search_filters: Dictionary of filter criteria
        limit: Maximum number of results
        
    Returns:
        List of matching assessments
    """
    supabase = get_supabase()
    
    try:
        # Build query based on filters
        if search_filters.get("assessment_type") == "geographic":
            query = supabase.table(GEOGRAPHIC_NAMES_TABLE).select("*")
            
            if search_filters.get("is_geographic"):
                query = query.eq("is_geographic_name", True)
            if search_filters.get("geographic_type"):
                query = query.eq("geographic_type", search_filters["geographic_type"])
            if search_filters.get("gac_risk"):
                query = query.eq("gac_objection_risk", search_filters["gac_risk"])
                
        elif search_filters.get("assessment_type") == "safeguard":
            query = supabase.table(SAFEGUARD_ASSESSMENTS_TABLE).select("*")
            
            if search_filters.get("safeguard_risk"):
                query = query.eq("safeguard_risk_level", search_filters["safeguard_risk"])
            if search_filters.get("special_safeguards"):
                query = query.eq("safeguards_special_required", True)
                
        else:
            # Default to geographic assessments
            query = supabase.table(GEOGRAPHIC_NAMES_TABLE).select("*")
        
        result = query.order("created_at", desc=True).limit(limit).execute()
        return result.data
        
    except Exception as e:
        print(f"Error searching policy assessments: {e}")
        return [] 