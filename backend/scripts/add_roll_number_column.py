"""
Migration script to add roll_number column to student_profiles table.
Run this script if you have an existing database that needs the new column.
"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from sqlalchemy import text
from backend.database import engine, SessionLocal
from backend.config import settings

def migrate_database():
    """Add roll_number column to student_profiles table if it doesn't exist."""
    db = SessionLocal()
    try:
        # Check if column already exists
        if settings.DATABASE_URL.startswith("sqlite"):
            # SQLite
            result = db.execute(text("""
                SELECT COUNT(*) as count 
                FROM pragma_table_info('student_profiles') 
                WHERE name='roll_number'
            """))
            count = result.fetchone()[0]
            
            if count == 0:
                print("Adding roll_number column to student_profiles table...")
                db.execute(text("""
                    ALTER TABLE student_profiles 
                    ADD COLUMN roll_number VARCHAR
                """))
                db.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_student_roll 
                    ON student_profiles(roll_number)
                """))
                db.commit()
                print("✓ Successfully added roll_number column and index")
            else:
                print("✓ roll_number column already exists")
        else:
            # PostgreSQL/MySQL
            result = db.execute(text("""
                SELECT COUNT(*) as count 
                FROM information_schema.columns 
                WHERE table_name='student_profiles' 
                AND column_name='roll_number'
            """))
            count = result.fetchone()[0]
            
            if count == 0:
                print("Adding roll_number column to student_profiles table...")
                db.execute(text("""
                    ALTER TABLE student_profiles 
                    ADD COLUMN roll_number VARCHAR
                """))
                db.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_student_roll 
                    ON student_profiles(roll_number)
                """))
                db.commit()
                print("✓ Successfully added roll_number column and index")
            else:
                print("✓ roll_number column already exists")
        
        print("Migration completed successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"✗ Migration failed: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    print("Starting database migration...")
    print(f"Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL}")
    migrate_database()


