import sqlite3
import os
from backend.config import settings

def migrate():
    db_path = settings.DATABASE_URL.replace("sqlite:///", "")
    print(f"Connecting to database at: {db_path}")
    
    if not os.path.exists(db_path):
        print("Database file does not exist. Skipping migration as it will be created fresh.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(student_profiles)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if "is_verified" not in columns:
            print("Adding 'is_verified' column to 'student_profiles' table...")
            cursor.execute("ALTER TABLE student_profiles ADD COLUMN is_verified BOOLEAN DEFAULT 0")
            # Update existing verified students (if we can infer it)
            # For now, just set to False (0)
            conn.commit()
            print("Successfully added 'is_verified' column.")
        else:
            print("'is_verified' column already exists.")
            
    except Exception as e:
        print(f"Error during migration: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
