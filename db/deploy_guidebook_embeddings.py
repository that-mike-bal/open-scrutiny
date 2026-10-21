#!/usr/bin/env python3
"""
Deploy Guidebook Embeddings Schema to Supabase

This script deploys the guidebook embeddings tables and functions to your Supabase database.

Usage:
    python deploy_guidebook_embeddings.py
    python deploy_guidebook_embeddings.py --dry-run  # Preview SQL only
"""

import os
import sys
import argparse
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.supabase_client import get_supabase

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_schema_sql() -> str:
    """Load the guidebook embeddings schema SQL"""
    schema_path = os.path.join(os.path.dirname(__file__), 'guidebook_embeddings_schema.sql')
    
    try:
        with open(schema_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"Schema file not found: {schema_path}")
        return ""
    except Exception as e:
        logger.error(f"Failed to load schema: {e}")
        return ""

def deploy_schema(dry_run: bool = False) -> bool:
    """Deploy the schema to Supabase"""
    schema_sql = load_schema_sql()
    if not schema_sql:
        return False
    
    if dry_run:
        print("=== DRY RUN: SQL that would be executed ===")
        print(schema_sql)
        print("=== END DRY RUN ===")
        return True
    
    try:
        logger.info("Connecting to Supabase...")
        supabase = get_supabase()
        
        if not supabase.is_enabled():
            logger.error("Supabase client is not enabled - check your credentials")
            return False
        
        logger.info("Deploying guidebook embeddings schema...")
        
        # Split SQL into individual statements for better error handling
        statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
        
        success_count = 0
        for i, statement in enumerate(statements, 1):
            try:
                logger.info(f"Executing statement {i}/{len(statements)}...")
                
                # Skip comments and empty statements
                if statement.startswith('--') or not statement:
                    continue
                
                # Execute the statement
                response = supabase.execute_query(statement + ';')
                
                if response:
                    success_count += 1
                    logger.info(f"✅ Statement {i} executed successfully")
                else:
                    logger.warning(f"⚠️ Statement {i} may have failed (no response)")
                
            except Exception as e:
                logger.error(f"❌ Failed to execute statement {i}: {e}")
                logger.error(f"Statement: {statement[:100]}...")
                # Continue with other statements
                continue
        
        logger.info(f"Schema deployment complete. {success_count}/{len(statements)} statements executed successfully.")
        
        # Verify deployment by checking if tables exist
        if verify_deployment(supabase):
            logger.info("✅ Schema deployment verified successfully!")
            return True
        else:
            logger.warning("⚠️ Schema deployment may be incomplete")
            return False
            
    except Exception as e:
        logger.error(f"Failed to deploy schema: {e}")
        return False

def verify_deployment(supabase) -> bool:
    """Verify that the tables were created successfully"""
    try:
        # Check if main table exists by trying to query it
        response = supabase.table('guidebook_embeddings').select('id').limit(1).execute()
        
        # If we get here without exception, table exists
        logger.info("✅ guidebook_embeddings table exists")
        
        # Check other tables
        tables_to_check = [
            'guidebook_sections',
            'guidebook_search_queries',
            'guidebook_search_results'
        ]
        
        for table_name in tables_to_check:
            try:
                response = supabase.table(table_name).select('id').limit(1).execute()
                logger.info(f"✅ {table_name} table exists")
            except Exception as e:
                logger.warning(f"⚠️ {table_name} table may not exist: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        return False

def show_next_steps():
    """Show user what to do next"""
    print("\n" + "="*60)
    print("🎉 GUIDEBOOK EMBEDDINGS SCHEMA DEPLOYED!")
    print("="*60)
    print("\n📋 Next Steps:")
    print("\n1. Populate the embeddings table:")
    print("   python db/populate_guidebook_embeddings.py --test-mode")
    print("   # Or with actual PDF:")
    print("   python db/populate_guidebook_embeddings.py --pdf-path /path/to/guidebook.pdf")
    
    print("\n2. Test semantic search:")
    print("   python -c \"")
    print("   from db.guidebook_search import search_guidebook")
    print("   results = search_guidebook('string similarity review')")
    print("   print(f'Found {len(results)} results')")
    print("   \"")
    
    print("\n3. Integrate with your CrewAI tools:")
    print("   - Import GuidebookSearcher in your tools")
    print("   - Use get_tld_context() for evaluation context")
    print("   - Use get_question_context() for ICANN questions")
    
    print("\n4. Monitor usage:")
    print("   - Check guidebook_search_queries table for search analytics")
    print("   - Review guidebook_search_results for performance metrics")
    
    print("\n📊 Database Tables Created:")
    print("   ✅ guidebook_embeddings       - Main content with vectors")
    print("   ✅ guidebook_sections         - Hierarchical structure")
    print("   ✅ guidebook_search_queries   - Search analytics")
    print("   ✅ guidebook_search_results   - Result tracking")
    
    print("\n🔧 Functions Available:")
    print("   ✅ search_guidebook_content() - Semantic search function")
    print("   ✅ get_guidebook_context_for_question() - Question context")
    
    print("\n" + "="*60)

def main():
    parser = argparse.ArgumentParser(description='Deploy guidebook embeddings schema')
    parser.add_argument('--dry-run', action='store_true', help='Preview SQL without executing')
    
    args = parser.parse_args()
    
    logger.info("Starting guidebook embeddings schema deployment...")
    
    success = deploy_schema(dry_run=args.dry_run)
    
    if success and not args.dry_run:
        show_next_steps()
        return 0
    elif args.dry_run:
        logger.info("Dry run completed - review the SQL above")
        return 0
    else:
        logger.error("Schema deployment failed")
        return 1

if __name__ == "__main__":
    exit(main())
