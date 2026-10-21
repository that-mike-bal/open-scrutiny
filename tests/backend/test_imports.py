"""Test that we can import core modules from the current codebase"""

import pytest

def test_app_import():
    """Test that we can import the FastAPI app from current code"""
    from crewai_service.app import app
    assert app is not None
    
def test_supabase_client_import():
    """Test that we can import the Supabase client from current code"""
    from crewai_service.utils.supabase_client import get_supabase_client
    assert get_supabase_client is not None

def test_crew_builder_import():
    """Test that we can import the CrewBuilder from current code"""
    from crewai_service.crew import CrewBuilder
    assert CrewBuilder is not None