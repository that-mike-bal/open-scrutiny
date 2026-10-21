"""
Database Package

This package contains modules for interacting with the Supabase database.
It provides functions for storing and retrieving TLD applications and evaluations.

New CMS-style architecture supports two post types:
- String Evaluation Posts (technical ICANN analysis)  
- Application Posts (business cases)
"""

from .supabase_client import supabase, get_supabase
from .evaluation_store import save_evaluation, get_evaluation, get_evaluations_for_tld, get_all_evaluations
from .tld_application_store import TldApplicationStore

# CMS-style data management
from .cms_store import (
    # String Evaluation Posts
    create_string_evaluation_post,
    get_string_evaluation_post,
    search_string_evaluation_posts,
    
    # Application Posts
    create_application_post,
    get_application_post,
    get_applications_for_string,
    search_application_posts,
    
    # RAG Chat Integration
    get_evaluation_context_for_chat
)