#!/usr/bin/env python3
"""
Apply the policy assessment migration to the database.

This script adds:
1. Geographic names assessment table
2. Safeguard assessment table  
3. Enhanced GAC risk assessment fields
"""

import os
import sys
from pathlib import Path
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_supabase_client() -> Client:
    """Get Supabase client from environment variables."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
    
    return create_client(url, key)

def read_migration_file() -> str:
    """Read the migration SQL file."""
    migration_path = Path(__file__).parent / "add_policy_assessment_tables.sql"
    
    if not migration_path.exists():
        raise FileNotFoundError(f"Migration file not found: {migration_path}")
    
    with open(migration_path, 'r') as f:
        return f.read()

def execute_sql_statement(supabase: Client, statement: str) -> bool:
    """Execute a single SQL statement."""
    try:
        # Use the SQL editor function if available
        result = supabase.rpc('exec_sql', {'sql': statement}).execute()
        return True
    except Exception as e:
        print(f"   ❌ Error executing statement: {e}")
        return False

def apply_migration(supabase: Client, migration_sql: str) -> None:
    """Apply the migration SQL to Supabase."""
    print("📋 Applying policy assessment migration...")
    
    # Split the migration into individual statements
    statements = []
    current_statement = ""
    in_function = False
    
    for line in migration_sql.split('\n'):
        line = line.strip()
        
        # Skip comments and empty lines
        if not line or line.startswith('--'):
            continue
        
        # Track if we're inside a function definition
        if 'CREATE OR REPLACE FUNCTION' in line.upper() or 'CREATE FUNCTION' in line.upper():
            in_function = True
        elif line.upper().startswith('$$ LANGUAGE'):
            in_function = False
            current_statement += line + '\n'
            statements.append(current_statement.strip())
            current_statement = ""
            continue
        elif 'DO $$' in line.upper():
            in_function = True
        elif line == '$$;' and in_function:
            in_function = False
            current_statement += line + '\n'
            statements.append(current_statement.strip())
            current_statement = ""
            continue
            
        current_statement += line + '\n'
        
        # If line ends with semicolon and we're not in a function, it's the end of a statement
        if line.endswith(';') and not in_function:
            statements.append(current_statement.strip())
            current_statement = ""
    
    # Execute each statement
    success_count = 0
    error_count = 0
    
    for i, statement in enumerate(statements):
        if not statement.strip():
            continue
            
        try:
            # Use RPC to execute raw SQL
            result = supabase.rpc('exec_sql', {'sql': statement}).execute()
            success_count += 1
            
            # Print progress for major operations
            if any(keyword in statement.upper() for keyword in ['CREATE TABLE', 'CREATE INDEX', 'CREATE VIEW', 'CREATE FUNCTION', 'ALTER TABLE']):
                if 'CREATE TABLE' in statement.upper():
                    table_name = statement.split('CREATE TABLE')[1].split('(')[0].strip()
                    print(f"   ✅ Created table: {table_name}")
                elif 'ALTER TABLE' in statement.upper():
                    table_name = statement.split('ALTER TABLE')[1].split('ADD')[0].strip()
                    print(f"   ✅ Enhanced table: {table_name}")
                elif 'CREATE INDEX' in statement.upper():
                    index_name = statement.split('CREATE INDEX')[1].split('ON')[0].strip()
                    print(f"   ✅ Created index: {index_name}")
                elif 'CREATE VIEW' in statement.upper():
                    view_name = statement.split('CREATE VIEW')[1].split('AS')[0].strip()
                    print(f"   ✅ Created view: {view_name}")
                elif 'CREATE FUNCTION' in statement.upper() or 'CREATE OR REPLACE FUNCTION' in statement.upper():
                    func_name = statement.split('FUNCTION')[1].split('(')[0].strip()
                    print(f"   ✅ Created function: {func_name}")
                    
        except Exception as e:
            error_count += 1
            print(f"   ❌ Error executing statement {i+1}: {e}")
            print(f"      Statement: {statement[:100]}...")
    
    print(f"\n📊 Migration application complete:")
    print(f"   ✅ Successful statements: {success_count}")
    print(f"   ❌ Failed statements: {error_count}")

def verify_migration(supabase: Client) -> None:
    """Verify that the migration was applied successfully."""
    print("\n🔍 Verifying migration...")
    
    expected_tables = [
        "geographic_names_assessments",
        "safeguard_assessments"
    ]
    
    expected_columns = [
        ("gac_risk_results", "pattern_match_risk"),
        ("gac_risk_results", "multi_government_risk"),
        ("gac_risk_results", "expert_consultation_required")
    ]
    
    try:
        # Check tables
        result = supabase.rpc('exec_sql', {
            'sql': """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('geographic_names_assessments', 'safeguard_assessments')
            ORDER BY table_name;
            """
        }).execute()
        
        if result.data:
            created_tables = [row['table_name'] for row in result.data]
            print(f"   📋 Found {len(created_tables)} new tables:")
            for table in created_tables:
                print(f"      ✅ {table}")
            
            missing_tables = set(expected_tables) - set(created_tables)
            if missing_tables:
                print(f"   ⚠️  Missing tables: {', '.join(missing_tables)}")
        
        # Check enhanced columns
        result = supabase.rpc('exec_sql', {
            'sql': """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'gac_risk_results'
            AND column_name IN ('pattern_match_risk', 'multi_government_risk', 'expert_consultation_required')
            ORDER BY column_name;
            """
        }).execute()
        
        if result.data:
            enhanced_columns = [row['column_name'] for row in result.data]
            print(f"   📋 Enhanced GAC risk table with {len(enhanced_columns)} new columns:")
            for column in enhanced_columns:
                print(f"      ✅ {column}")
        
        # Test the utility function
        result = supabase.rpc('exec_sql', {
            'sql': "SELECT get_policy_assessment_summary('test') LIMIT 1;"
        }).execute()
        
        if result.data:
            print(f"   ✅ Policy assessment utility function working")
        else:
            print(f"   ⚠️  Policy assessment utility function may have issues")
            
        print(f"\n   🎉 Migration verification complete!")
        
    except Exception as e:
        print(f"   ❌ Error verifying migration: {e}")

def main():
    """Main function to apply the migration."""
    print("🚀 TLD Evaluation Platform - Policy Assessment Migration")
    print("=" * 60)
    
    try:
        # Get Supabase client
        print("🔌 Connecting to Supabase...")
        supabase = get_supabase_client()
        print("   ✅ Connected successfully")
        
        # Read migration file
        print("\n📖 Reading migration file...")
        migration_sql = read_migration_file()
        print(f"   ✅ Migration file loaded ({len(migration_sql)} characters)")
        
        # Apply migration
        apply_migration(supabase, migration_sql)
        
        # Verify migration
        verify_migration(supabase)
        
        print("\n🎉 Policy assessment migration complete!")
        print("   The database now supports enhanced policy assessment workflows.")
        
    except Exception as e:
        print(f"\n❌ Error applying migration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 