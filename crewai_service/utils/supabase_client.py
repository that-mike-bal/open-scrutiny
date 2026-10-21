"""
Supabase Client Utility

Handles storing and retrieving workflow results in Supabase database using the official SDK.
"""

import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

# Import official Supabase SDK
from supabase import create_client, Client
from crewai_service.utils.config import load_secret

logger = logging.getLogger(__name__)


class SupabaseClient:
    """Client for interacting with Supabase database using official SDK."""
    
    def __init__(self):
        """
        Initialize Supabase client from environment variables.
        For server-side operations, try to use service_role key first to bypass RLS.
        """
        self.url = load_secret("supabase_url", "SUPABASE_URL")
        
        # Try service_role key first for server operations (bypasses RLS)
        self.key = load_secret("supabase_service_key", "SUPABASE_SERVICE_KEY")
        if not self.key:
            # Fallback to anon key (will be subject to RLS policies)
            self.key = load_secret("supabase_key")
            if self.key:
                logger.warning("Using anon key - operations may be blocked by RLS policies. Consider using service_role key for server operations.")
        
        if not self.url or not self.key:
            logger.warning("SUPABASE_URL / SUPABASE_SERVICE_KEY not set - database operations will be disabled")
            self.enabled = False
            self.client = None
        else:
            try:
                # Create official Supabase client
                self.client: Client = create_client(self.url, self.key)
                self.enabled = True
                logger.info("Supabase client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}")
                self.enabled = False
                self.client = None
    
    def table(self, table_name: str):
        """
        Direct access to table method for easier usage.
        This prevents confusion between supabase.table() and supabase.client.table() patterns.
        """
        if not self.enabled or not self.client:
            logger.warning("Supabase client not enabled - table operations will fail")
            return None
        return self.client.table(table_name)
    
    def store_tld_string(self, tld_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Store TLD string data using Supabase SDK"""
        if not self.enabled:
            logger.debug("Supabase client disabled - skipping storage")
            return None
        
        try:
            result = self.client.table('tld_strings').insert(tld_data).execute()
            if result.data:
                logger.info(f"✅ Successfully stored TLD string: {tld_data['tld_string']}")
                return result.data[0]
            else:
                logger.error(f"❌ Failed to store TLD string: {result}")
                return None
        except Exception as e:
            logger.error(f"❌ Error storing TLD string: {e}")
            return None
    
    def update_tld_string(self, tld_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update TLD string data using Supabase SDK"""
        if not self.enabled:
            logger.debug("Supabase client disabled - skipping update")
            return None
        
        try:
            result = self.client.table('tld_strings').update(update_data).eq('id', tld_id).execute()
            if result.data:
                logger.info(f"✅ Successfully updated TLD string: {tld_id}")
                return result.data[0]
            else:
                logger.error(f"❌ Failed to update TLD string: {result}")
                return None
        except Exception as e:
            logger.error(f"❌ Error updating TLD string: {e}")
            return None
    
    def store_workflow_execution(self, workflow_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Store workflow execution data using Supabase SDK"""
        if not self.enabled:
            logger.debug("Supabase client disabled - skipping storage")
            return None
        
        try:
            result = self.client.table('workflow_executions').insert(workflow_data).execute()
            if result.data:
                logger.info(f"✅ Successfully stored workflow execution: {workflow_data['id']}")
                return result.data[0]
            else:
                logger.error(f"❌ Failed to store workflow execution: {result}")
                return None
        except Exception as e:
            logger.error(f"❌ Error storing workflow execution: {e}")
            return None
    
    def update_workflow_execution(self, workflow_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update workflow execution data using Supabase SDK"""
        if not self.enabled:
            logger.debug("Supabase client disabled - skipping update")
            return None
        
        try:
            result = self.client.table('workflow_executions').update(update_data).eq('id', workflow_id).execute()
            if result.data:
                logger.info(f"✅ Successfully updated workflow execution: {workflow_id}")
                return result.data[0]
            else:
                logger.error(f"❌ Failed to update workflow execution: {result}")
                return None
        except Exception as e:
            logger.error(f"❌ Error updating workflow execution: {e}")
            return None
    
    def store_task_execution(self, task_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Store task execution data using Supabase SDK with upsert to handle duplicates"""
        if not self.enabled:
            logger.debug("Supabase client disabled - skipping storage")
            return None
        
        try:
            # Use upsert to handle the unique constraint on (tld_string_id, task_definition_id)
            # This will update existing records or insert new ones
            result = self.client.table('task_executions').upsert(
                task_data,
                on_conflict='tld_string_id,task_definition_id'
            ).execute()
            
            if result.data:
                logger.info(f"✅ Successfully stored/updated task execution: {task_data['task_name']}")
                return result.data[0]
            else:
                logger.error(f"❌ Failed to store task execution: {result}")
                return None
        except Exception as e:
            logger.error(f"❌ Error storing task execution: {e}")
            return None
    
    def get_tld_string_by_name(self, tld_string: str) -> Optional[Dict[str, Any]]:
        """Get TLD string by name using Supabase SDK"""
        if not self.enabled:
            logger.debug("Supabase client disabled - returning None")
            return None
        
        try:
            result = self.client.table('tld_strings').select('*').eq('tld_string', tld_string).execute()
            if result.data:
                logger.info(f"✅ Found existing TLD string: {tld_string}")
                return result.data[0]
            else:
                logger.info(f"🔍 TLD string not found: {tld_string}")
                return None
        except Exception as e:
            logger.error(f"❌ Error getting TLD string: {e}")
            return None

    def get_task_executions_by_tld_id(self, tld_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get all task executions for a TLD string ID using Supabase SDK"""
        if not self.enabled:
            logger.debug("Supabase client disabled - returning None")
            return None
        
        try:
            result = self.client.table('task_executions').select('*').eq('tld_string_id', tld_id).order('created_at', desc=False).execute()
            if result.data:
                logger.info(f"✅ Found {len(result.data)} task executions for TLD ID: {tld_id}")
                return result.data
            else:
                logger.info(f"🔍 No task executions found for TLD ID: {tld_id}")
                return []
        except Exception as e:
            logger.error(f"❌ Error getting task executions for TLD ID {tld_id}: {e}")
            return None

    def get_all_tld_strings(self) -> Optional[List[Dict[str, Any]]]:
        """Get all TLD strings using Supabase SDK"""
        if not self.enabled:
            logger.debug("Supabase client disabled - returning None")
            return None
        
        try:
            result = self.client.table('tld_strings').select('*').order('created_at', desc=True).execute()
            if result.data:
                logger.info(f"✅ Found {len(result.data)} TLD strings")
                return result.data
            else:
                logger.info("🔍 No TLD strings found")
                return []
        except Exception as e:
            logger.error(f"❌ Error getting all TLD strings: {e}")
            return None

    def get_all_task_executions(self) -> Optional[List[Dict[str, Any]]]:
        """Get all task executions using Supabase SDK"""
        if not self.enabled:
            logger.debug("Supabase client disabled - returning None")
            return None
        
        try:
            result = self.client.table('task_executions').select('*').order('created_at', desc=False).execute()
            if result.data:
                logger.info(f"✅ Found {len(result.data)} task executions")
                return result.data
            else:
                logger.info("🔍 No task executions found")
                return []
        except Exception as e:
            logger.error(f"❌ Error getting all task executions: {e}")
            return None

    async def store_workflow_result(
        self, 
        workflow_name: str, 
        inputs: Dict[str, Any], 
        result: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Store workflow execution result in Supabase.
        
        Args:
            workflow_name: Name of the executed workflow
            inputs: Input parameters used
            result: Workflow execution result
            metadata: Additional metadata
            
        Returns:
            Stored record or None if disabled/failed
        """
        if not self.enabled:
            logger.debug("Supabase client disabled - skipping storage")
            return None
        
        try:
            # Prepare record
            record = {
                "workflow_name": workflow_name,
                "inputs": inputs,
                "result": result,
                "metadata": metadata or {},
                "created_at": datetime.now().isoformat(),
                "status": result.get("status", "unknown")
            }
            
            # Store in database using SDK
            result = self.client.table('workflow_results').insert(record).execute()
            if result.data:
                stored_record = result.data[0]
                logger.info(f"Stored workflow result for '{workflow_name}' with ID: {stored_record.get('id')}")
                return stored_record
            else:
                logger.error(f"Failed to store workflow result: {result}")
                return None
                    
        except Exception as e:
            logger.error(f"Error storing workflow result: {e}")
            return None
    
    async def get_workflow_results(
        self, 
        workflow_name: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Retrieve workflow results from Supabase.
        
        Args:
            workflow_name: Filter by workflow name (optional)
            limit: Maximum number of results
            
        Returns:
            List of workflow results
        """
        if not self.enabled:
            logger.debug("Supabase client disabled - returning empty list")
            return []
        
        try:
            query = self.client.table('workflow_results').select('*').order('created_at', desc=True).limit(limit)
            
            if workflow_name:
                query = query.eq('workflow_name', workflow_name)
            
            result = query.execute()
            if result.data:
                logger.debug(f"Retrieved {len(result.data)} workflow results")
                return result.data
            else:
                logger.debug("No workflow results found")
                return []
                    
        except Exception as e:
            logger.error(f"Error retrieving workflow results: {e}")
            return []
    
    async def get_workflow_result_by_id(self, result_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific workflow result by ID.
        
        Args:
            result_id: ID of the workflow result
            
        Returns:
            Workflow result or None if not found
        """
        if not self.enabled:
            logger.debug("Supabase client disabled - returning None")
            return None
        
        try:
            result = self.client.table('workflow_results').select('*').eq('id', result_id).execute()
            if result.data:
                logger.debug(f"Retrieved workflow result with ID: {result_id}")
                return result.data[0]
            else:
                logger.warning(f"Workflow result not found: {result_id}")
                return None
                    
        except Exception as e:
            logger.error(f"Error retrieving workflow result by ID: {e}")
            return None
    
    async def store_evaluation_metadata(
        self,
        tld_string: str,
        workflow_type: str,
        use_case: str,
        result_summary: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Store evaluation metadata"""
        if not self.enabled:
            logger.debug("Supabase client disabled - skipping storage")
            return None
        
        try:
            record = {
                "tld_string": tld_string,
                "workflow_type": workflow_type,
                "use_case": use_case,
                "result_summary": result_summary,
                "created_at": datetime.now().isoformat()
            }
            
            result = self.client.table('evaluation_metadata').insert(record).execute()
            if result.data:
                logger.info(f"Stored evaluation metadata for '{tld_string}'")
                return result.data[0]
            else:
                logger.error(f"Failed to store evaluation metadata: {result}")
                return None
                
        except Exception as e:
            logger.error(f"Error storing evaluation metadata: {e}")
            return None

    async def get_tld_evaluation_history(self, tld_string: str) -> List[Dict[str, Any]]:
        """Get evaluation history for a TLD string"""
        if not self.enabled:
            logger.debug("Supabase client disabled - returning empty list")
            return []
        
        try:
            result = self.client.table('evaluation_metadata').select('*').eq('tld_string', tld_string).order('created_at', desc=True).execute()
            if result.data:
                logger.debug(f"Retrieved {len(result.data)} evaluation records for '{tld_string}'")
                return result.data
            else:
                logger.debug(f"No evaluation history found for '{tld_string}'")
                return []
                
        except Exception as e:
            logger.error(f"Error retrieving evaluation history: {e}")
            return []


# Global client instance
_supabase_client = None

def get_supabase_client() -> SupabaseClient:
    """Get a configured Supabase client instance (singleton)."""
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = SupabaseClient()
    return _supabase_client 