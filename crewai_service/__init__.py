"""
CrewAI Service for TLD Evaluation

A modern, clean implementation of TLD evaluation workflows using CrewAI.
Built with YAML-driven configuration and dynamic crew building.
"""

__version__ = "2.0.0"
__author__ = "CrewAI TLD Evaluation Team"

# Main exports
from .crew import CrewBuilder, build_crew_for_workflow
from .utils.supabase_client import SupabaseClient, get_supabase_client

__all__ = [
    # Core architecture
    "CrewBuilder",
    "build_crew_for_workflow",
    
    # Database utilities
    "SupabaseClient",
    "get_supabase_client"
] 