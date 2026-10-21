"""
Evaluation Store

This module handles operations related to TLD evaluations in the database.
"""
import uuid
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from .supabase_client import get_supabase

# Table name
EVALUATIONS_TABLE = "evaluations"

def save_evaluation(
    tld: str,
    use_case: str,
    score: int,
    passed: bool,
    feedback: Dict[str, Any],
    backup_string: Optional[str] = None
) -> Dict[str, Any]:
    """
    Save a TLD evaluation to the database.
    
    Args:
        tld: The TLD string
        use_case: The use case for the TLD
        score: The evaluation score
        passed: Whether the evaluation passed
        feedback: Detailed feedback and category analysis
        backup_string: Optional backup TLD string suggestion
        
    Returns:
        The saved evaluation record
    """
    # Get Supabase client
    supabase = get_supabase()
    
    # Generate a UUID
    evaluation_id = str(uuid.uuid4())
    
    # Prepare data
    evaluation_data = {
        "id": evaluation_id,
        "tld": tld,
        "use_case": use_case,
        "score": score,
        "passed": passed,
        "feedback": feedback,
        "created_at": datetime.utcnow().isoformat()
    }
    
    # Add backup string if provided
    if backup_string:
        evaluation_data["backup_string"] = backup_string
    
    # Insert data
    result = supabase.table(EVALUATIONS_TABLE).insert(evaluation_data).execute()
    
    # Check for errors
    if len(result.data) == 0:
        raise Exception("Failed to save evaluation")
    
    return result.data[0]

def get_evaluation(evaluation_id: str) -> Optional[Dict[str, Any]]:
    """
    Get an evaluation by ID.
    
    Args:
        evaluation_id: The ID of the evaluation
        
    Returns:
        The evaluation data or None if not found
    """
    # Get Supabase client
    supabase = get_supabase()
    
    # Query the database
    result = supabase.table(EVALUATIONS_TABLE).select("*").eq("id", evaluation_id).execute()
    
    # Check if evaluation exists
    if len(result.data) == 0:
        return None
    
    return result.data[0]

def get_all_evaluations() -> List[Dict[str, Any]]:
    """
    Get all evaluations.
    
    Returns:
        List of all evaluations
    """
    # Get Supabase client
    supabase = get_supabase()
    
    # Query the database
    result = supabase.table(EVALUATIONS_TABLE).select("*").order("created_at", desc=True).execute()
    
    return result.data

def get_evaluations_for_tld(tld_string: str) -> List[Dict[str, Any]]:
    """
    Get all evaluations for a specific TLD.
    
    Args:
        tld_string: The TLD string to search for
        
    Returns:
        List of evaluations for the specified TLD
    """
    # Get Supabase client
    supabase = get_supabase()
    
    # Query the database
    result = supabase.table(EVALUATIONS_TABLE).select("*").eq("tld", tld_string).order("created_at", desc=True).execute()
    
    return result.data

def delete_evaluation(evaluation_id: str) -> bool:
    """
    Delete an evaluation.
    
    Args:
        evaluation_id: The ID of the evaluation to delete
        
    Returns:
        True if successful, False otherwise
    """
    # Get Supabase client
    supabase = get_supabase()
    
    # Delete the evaluation
    result = supabase.table(EVALUATIONS_TABLE).delete().eq("id", evaluation_id).execute()
    
    # Check if delete was successful
    return len(result.data) > 0