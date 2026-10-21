#!/usr/bin/env python3
"""
Apply the task_name column migration to the task_executions table.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.supabase_client import create_client
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def apply_migration():
    """Apply the task_name column migration."""
    try:
        # Get Supabase client
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_SERVICE_KEY"]
        
        supabase = create_client(url, key)
        
        # Read the migration SQL
        migration_path = Path(__file__).parent / "add_task_name_column.sql"
        with open(migration_path, 'r') as f:
            migration_sql = f.read()
        
        logger.info("🚀 Applying task_name column migration...")
        
        # Execute the migration
        # Split by semicolon and execute each statement
        statements = migration_sql.split(';')
        for statement in statements:
            statement = statement.strip()
            if statement:
                logger.info(f"Executing: {statement[:50]}...")
                result = supabase.rpc('execute_sql', {'sql': statement}).execute()
                logger.info(f"✅ Statement executed successfully")
        
        logger.info("🎉 Migration completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    success = apply_migration()
    sys.exit(0 if success else 1) 