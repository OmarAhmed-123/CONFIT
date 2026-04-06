"""
CONFIT Backend — Database Migration Runner
==========================================
Run SQL migrations programmatically (for Windows without psql).
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from database.session import engine, SessionLocal


def run_migration(migration_file: str) -> bool:
    """
    Run a SQL migration file.
    
    Args:
        migration_file: Path to the .sql file
        
    Returns:
        True if successful, False otherwise
    """
    migration_path = Path(migration_file)
    
    if not migration_path.exists():
        print(f"❌ Migration file not found: {migration_file}")
        return False
    
    print(f"📄 Reading migration: {migration_path.name}")
    
    with open(migration_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # Split by semicolons but handle functions correctly
    # This is a simplified approach - for complex migrations, use a proper tool
    
    db = SessionLocal()
    try:
        # Execute the entire SQL content
        # PostgreSQL can handle multiple statements
        print("⚙️  Executing migration...")
        
        # Split into individual statements
        statements = []
        current_statement = []
        in_function = False
        
        for line in sql_content.split('\n'):
            # Track if we're inside a function definition
            if 'CREATE OR REPLACE FUNCTION' in line or 'CREATE FUNCTION' in line:
                in_function = True
            
            current_statement.append(line)
            
            # Check for function end
            if in_function and "$$" in line and current_statement[0] != line:
                if line.strip().endswith('$$') or line.strip().endswith('$$;'):
                    in_function = False
                    if line.strip().endswith(';'):
                        statements.append('\n'.join(current_statement))
                        current_statement = []
            elif not in_function and line.strip().endswith(';'):
                statements.append('\n'.join(current_statement))
                current_statement = []
        
        # Add any remaining statement
        if current_statement:
            statements.append('\n'.join(current_statement))
        
        # Execute each statement
        success_count = 0
        error_count = 0
        
        for i, statement in enumerate(statements):
            statement = statement.strip()
            if not statement or statement == ';':
                continue
            
            try:
                db.execute(text(statement))
                db.commit()
                success_count += 1
            except Exception as e:
                error_msg = str(e)
                # Ignore "already exists" errors for idempotent migrations
                if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower():
                    print(f"  ⚠️  Statement {i+1}: Already exists (skipped)")
                    success_count += 1
                else:
                    print(f"  ❌ Statement {i+1} failed: {error_msg[:100]}")
                    error_count += 1
                    db.rollback()
        
        print(f"\n✅ Migration completed: {success_count} statements executed, {error_count} errors")
        return error_count == 0
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def main():
    """Run the metrics aggregation migration."""
    migration_dir = Path(__file__).parent
    migration_file = migration_dir / "20260405_metrics_aggregation.sql"
    
    print("=" * 60)
    print("CONFIT Database Migration Runner")
    print("=" * 60)
    print()
    
    # Check database connection
    print("🔌 Testing database connection...")
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        print("✅ Database connection successful")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("\nPlease check your database configuration in .env")
        return 1
    
    print()
    
    # Run migration
    if run_migration(str(migration_file)):
        print("\n🎉 Migration completed successfully!")
        return 0
    else:
        print("\n❌ Migration failed. Check errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
