"""
Supabase Client for Database Operations

This module provides a centralized Supabase client specifically for database
operations, migrations, and schema management.
"""
import os
import logging
from typing import Optional, Dict, Any, List
from supabase import create_client, Client

logger = logging.getLogger(__name__)

def _load_secret(secret_name: str, env_var_name: Optional[str] = None) -> Optional[str]:
    """Load a secret from environment or the /secrets directory."""
    # Prefer environment variable if provided
    if env_var_name:
        env_val = os.getenv(env_var_name)
        if env_val and env_val.strip():
            return env_val.strip()

    # Try standard uppercased env var as well
    env_val = os.getenv(secret_name.upper())
    if env_val and env_val.strip():
        return env_val.strip()

    # Fallback to secrets directory
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    secret_path = os.path.join(project_root, "secrets", f"{secret_name}.txt")

    if not os.path.exists(secret_path):
        logger.warning(f"Secret file not found: {secret_path}")
        return None

    try:
        with open(secret_path, 'r') as f:
            return f.read().strip()
    except Exception as e:
        logger.error(f"Failed to read secret {secret_name}: {e}")
        return None

class DatabaseSupabaseClient:
    """
    Supabase client optimized for database operations.
    Focused on CRUD operations, migrations, and schema management.
    """
    
    def __init__(self):
        """Initialize the database client."""
        self.url = _load_secret("supabase_url", "SUPABASE_URL")
        # Prefer service role key for server-side operations (bypasses RLS)
        self.key = _load_secret("supabase_service_key", "SUPABASE_SERVICE_KEY") or _load_secret("supabase_key", "SUPABASE_ANON_KEY")
        
        if not self.url or not self.key:
            logger.warning("Supabase credentials not found - database operations will be disabled")
            self.enabled = False
            self.client = None
        else:
            try:
                self.client: Client = create_client(self.url, self.key)
                self.enabled = True
                logger.info("Database Supabase client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize database Supabase client: {e}")
                self.enabled = False
                self.client = None
    
    def table(self, table_name: str):
        """
        Access table operations.
        
        Args:
            table_name (str): Name of the table to access
            
        Returns:
            Table operations interface or None if disabled
        """
        if not self.enabled or not self.client:
            logger.warning(f"Database client not enabled - table '{table_name}' operations will fail")
            return None
        return self.client.table(table_name)
    
    def is_enabled(self) -> bool:
        """Check if the client is enabled and ready for operations."""
        return self.enabled and self.client is not None
    
    def rpc(self, function_name: str, params: Optional[Dict[str, Any]] = None):
        """
        Call a remote procedure (function) in the database.
        
        Args:
            function_name (str): Name of the function to call
            params (dict): Parameters to pass to the function
            
        Returns:
            RPC call result or None if disabled
        """
        if not self.enabled or not self.client:
            logger.warning(f"Database client not enabled - RPC '{function_name}' will fail")
            return None
        return self.client.rpc(function_name, params or {})
    
    def execute_query(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Execute a raw SQL query.
        
        Args:
            query (str): SQL query to execute
            
        Returns:
            Query result or None if failed
        """
        if not self.enabled:
            logger.warning("Database client not enabled - query execution skipped")
            return None
        
        try:
            result = self.client.rpc('execute_sql', {'query': query})
            return result.execute()
        except Exception as e:
            logger.error(f"Failed to execute query: {e}")
            return None
    
    def get_table_info(self, table_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a table structure.
        
        Args:
            table_name (str): Name of the table
            
        Returns:
            Table information or None if failed
        """
        if not self.enabled:
            logger.warning("Database client not enabled - table info unavailable")
            return None
        
        try:
            # Get table schema information
            result = self.client.rpc('get_table_info', {'table_name': table_name})
            return result.execute()
        except Exception as e:
            logger.error(f"Failed to get table info for {table_name}: {e}")
            return None

# Global instance
_db_client = None

def get_supabase() -> DatabaseSupabaseClient:
    """
    Get the database Supabase client instance.
    
    Returns:
        DatabaseSupabaseClient: The database client or raises an error if not initialized
    """
    global _db_client
    if _db_client is None:
        logger.info("Initializing DatabaseSupabaseClient from get_supabase()")
        _db_client = DatabaseSupabaseClient()
        logger.info(f"DB client created: enabled={getattr(_db_client, 'enabled', None)} url_set={bool(getattr(_db_client,'url',None))} key_set={bool(getattr(_db_client,'key',None))}")
    
    if not _db_client.is_enabled():
        # Add diagnostics to help identify why initialization failed
        try:
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            secrets_dir = os.path.join(project_root, "secrets")
            present = []
            for name in ("supabase_service_key.txt", "supabase_key.txt", "supabase_url.txt"):
                path = os.path.join(secrets_dir, name)
                if os.path.exists(path) and os.path.getsize(path) > 0:
                    present.append(name)
            logger.error(f"Supabase client disabled. Secrets present: {present}; SUPABASE_URL env set={bool(os.getenv('SUPABASE_URL'))}; SUPABASE_SERVICE_KEY env set={bool(os.getenv('SUPABASE_SERVICE_KEY'))}")
        except Exception:
            pass
        raise ValueError("Database Supabase client not initialized. Check your secrets in /secrets directory.")
    
    return _db_client

# Legacy compatibility - lazy-loaded
def _get_legacy_supabase():
    """Legacy compatibility function."""
    try:
        return get_supabase()
    except ValueError:
        logger.warning("Legacy supabase access failed - client not initialized")
        return None

# Create a property-like access for legacy compatibility
class LegacySupabaseProxy:
    """Proxy object for legacy supabase access."""
    
    def __getattr__(self, name):
        client = _get_legacy_supabase()
        if client is None:
            raise ValueError("Supabase client not initialized")
        return getattr(client, name)

supabase = LegacySupabaseProxy()