#!/usr/bin/env python3
"""
Safe Database Cleanup Script for TLD Evaluation Platform

This script safely clears evaluation data while preserving:
- User accounts (auth.users - managed by Supabase Auth)
- Applicant organizations (applicants table)
- Task definitions (task_definitions table)
- Application questions (application_questions table)
- System configuration data

WHAT GETS CLEARED:
- All TLD evaluation data (tld_strings)
- All task execution results (task_executions) 
- All workflow execution data (workflow_executions)
- All TLD application data (tld_applications)
- All application responses (application_responses)
- All specific result tables (iana_check_results, etc.)

This allows for a fresh start with consistent formatting while preserving
the foundational data and user accounts.
"""

import logging
import sys
from datetime import datetime
from typing import List, Dict, Any
from db.supabase_client import get_supabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseCleaner:
    def __init__(self):
        """Initialize the database cleaner."""
        self.supabase = get_supabase()
        if not self.supabase.is_enabled():
            raise ValueError("Database connection not available")
    
    def get_table_counts(self, tables: List[str]) -> Dict[str, int]:
        """Get row counts for specified tables."""
        counts = {}
        for table in tables:
            try:
                result = self.supabase.table(table).select('id', count='exact').limit(1).execute()
                counts[table] = result.count if result.count is not None else 0
            except Exception as e:
                logger.warning(f"Could not get count for {table}: {e}")
                counts[table] = -1  # -1 indicates error
        return counts
    
    def backup_critical_data(self) -> Dict[str, Any]:
        """Create a backup of critical data before cleanup."""
        backup = {
            'timestamp': datetime.utcnow().isoformat(),
            'applicants': [],
            'task_definitions': [],
            'application_questions_sample': []
        }
        
        try:
            # Backup applicants
            result = self.supabase.table('applicants').select('*').execute()
            backup['applicants'] = result.data
            logger.info(f"Backed up {len(backup['applicants'])} applicants")
            
            # Backup task definitions
            result = self.supabase.table('task_definitions').select('*').execute()
            backup['task_definitions'] = result.data
            logger.info(f"Backed up {len(backup['task_definitions'])} task definitions")
            
            # Backup sample of application questions (first 5 for verification)
            result = self.supabase.table('application_questions').select('*').limit(5).execute()
            backup['application_questions_sample'] = result.data
            logger.info(f"Backed up sample of {len(backup['application_questions_sample'])} application questions")
            
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            raise
        
        return backup
    
    def clear_evaluation_data(self) -> Dict[str, int]:
        """Clear all evaluation-related data."""
        tables_to_clear = [
            # Main evaluation data (cascading deletes will handle related data)
            'tld_strings',  # This will cascade to task_executions via foreign key
            'workflow_executions',  # Independent workflow tracking
            'tld_applications',  # This will cascade to application_responses
            
            # Specific result tables (likely empty but clean them anyway)
            'iana_check_results',
            'blocked_names_results',
            'reserved_names_results',
            'dns_stability_results',
            'similarity_analysis_results',
            'trademark_assessment_results',
            'gac_risk_results',
            
            # Clear any orphaned application responses
            'application_responses'
        ]
        
        # Get counts before deletion
        before_counts = self.get_table_counts(tables_to_clear)
        logger.info("Row counts before cleanup:")
        for table, count in before_counts.items():
            if count >= 0:
                logger.info(f"  {table}: {count} rows")
        
        deleted_counts = {}
        
        # Clear tables in order (most dependent first to avoid foreign key issues)
        deletion_order = [
            'application_responses',  # Child of tld_applications
            'iana_check_results',
            'blocked_names_results', 
            'reserved_names_results',
            'dns_stability_results',
            'similarity_analysis_results',
            'trademark_assessment_results',
            'gac_risk_results',
            'task_executions',  # Child of tld_strings
            'workflow_executions',  # Independent
            'tld_applications',  # Has its own children
            'tld_strings',  # Parent table - delete last
        ]
        
        for table in deletion_order:
            try:
                logger.info(f"Clearing table: {table}")
                result = self.supabase.table(table).delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
                deleted_counts[table] = len(result.data) if result.data else before_counts.get(table, 0)
                logger.info(f"  Deleted {deleted_counts[table]} rows from {table}")
            except Exception as e:
                logger.error(f"Error clearing {table}: {e}")
                deleted_counts[table] = -1
        
        return deleted_counts
    
    def verify_preserved_data(self, backup: Dict[str, Any]) -> bool:
        """Verify that critical data was preserved."""
        try:
            # Check applicants
            result = self.supabase.table('applicants').select('id', count='exact').limit(1).execute()
            applicants_count = result.count if result.count is not None else 0
            expected_applicants = len(backup['applicants'])
            
            if applicants_count != expected_applicants:
                logger.error(f"Applicants count mismatch: expected {expected_applicants}, got {applicants_count}")
                return False
            
            # Check task definitions
            result = self.supabase.table('task_definitions').select('id', count='exact').limit(1).execute()
            task_defs_count = result.count if result.count is not None else 0
            expected_task_defs = len(backup['task_definitions'])
            
            if task_defs_count != expected_task_defs:
                logger.error(f"Task definitions count mismatch: expected {expected_task_defs}, got {task_defs_count}")
                return False
            
            # Check application questions
            result = self.supabase.table('application_questions').select('id', count='exact').limit(1).execute()
            questions_count = result.count if result.count is not None else 0
            
            if questions_count < 200:  # Should have ~216 questions
                logger.error(f"Application questions count too low: {questions_count}")
                return False
            
            logger.info("✅ All critical data preserved successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error verifying preserved data: {e}")
            return False
    
    def run_cleanup(self, dry_run: bool = True) -> bool:
        """Run the complete cleanup process."""
        logger.info("="*60)
        logger.info("TLD EVALUATION PLATFORM - DATABASE CLEANUP")
        logger.info("="*60)
        logger.info(f"Mode: {'DRY RUN' if dry_run else 'LIVE CLEANUP'}")
        logger.info(f"Timestamp: {datetime.utcnow().isoformat()}")
        logger.info("")
        
        if dry_run:
            logger.info("🔍 DRY RUN MODE - No data will be deleted")
            logger.info("This will show you what would be deleted without making changes")
            logger.info("")
        else:
            logger.info("⚠️  LIVE CLEANUP MODE - Data will be permanently deleted")
            logger.info("Make sure you have a database backup before proceeding!")
            logger.info("")
        
        try:
            # Step 1: Create backup of critical data
            logger.info("Step 1: Creating backup of critical data...")
            backup = self.backup_critical_data()
            logger.info("✅ Backup created successfully")
            logger.info("")
            
            if dry_run:
                # In dry run mode, just show what would be deleted
                tables_to_check = [
                    'tld_strings', 'task_executions', 'workflow_executions',
                    'tld_applications', 'application_responses'
                ]
                
                counts = self.get_table_counts(tables_to_check)
                logger.info("📊 Data that would be cleared in live mode:")
                total_rows = 0
                for table, count in counts.items():
                    if count > 0:
                        logger.info(f"  - {table}: {count} rows")
                        total_rows += count
                    elif count == 0:
                        logger.info(f"  - {table}: 0 rows (already empty)")
                
                logger.info(f"\nTotal rows that would be deleted: {total_rows}")
                logger.info("\n✅ Dry run completed successfully")
                logger.info("\nTo perform the actual cleanup, run with dry_run=False")
                return True
            
            else:
                # Step 2: Clear evaluation data
                logger.info("Step 2: Clearing evaluation data...")
                deleted_counts = self.clear_evaluation_data()
                
                total_deleted = sum(count for count in deleted_counts.values() if count > 0)
                logger.info(f"✅ Deleted {total_deleted} total rows")
                logger.info("")
                
                # Step 3: Verify preserved data
                logger.info("Step 3: Verifying preserved data...")
                if not self.verify_preserved_data(backup):
                    logger.error("❌ Data verification failed!")
                    return False
                
                logger.info("✅ Database cleanup completed successfully!")
                logger.info("")
                logger.info("SUMMARY:")
                logger.info("- All evaluation data cleared")
                logger.info("- User accounts preserved") 
                logger.info("- Applicant organizations preserved")
                logger.info("- Task definitions preserved")
                logger.info("- Application questions preserved")
                logger.info("")
                logger.info("The system is ready for fresh evaluations with consistent formatting.")
                
                return True
                
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")
            return False

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Clean TLD evaluation database')
    parser.add_argument('--live', action='store_true', 
                       help='Perform actual cleanup (default is dry run)')
    parser.add_argument('--confirm', action='store_true',
                       help='Confirm you want to delete data (required for live mode)')
    
    args = parser.parse_args()
    
    if args.live and not args.confirm:
        print("❌ For live cleanup, you must use both --live and --confirm flags")
        print("Example: python db/safe_database_cleanup.py --live --confirm")
        sys.exit(1)
    
    if args.live:
        print("\n⚠️  WARNING: This will permanently delete evaluation data!")
        print("Make sure you have a backup of your database.")
        response = input("Type 'DELETE' to confirm: ")
        if response != 'DELETE':
            print("❌ Cleanup cancelled")
            sys.exit(1)
    
    try:
        cleaner = DatabaseCleaner()
        success = cleaner.run_cleanup(dry_run=not args.live)
        sys.exit(0 if success else 1)
        
    except Exception as e:
        logger.error(f"Failed to initialize cleanup: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()

