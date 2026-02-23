import sqlite3
import os

def migrate():
    db_path = './admission_forms.db'
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    print(f"Connecting to database at: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if roll_number column exists
        cursor.execute("PRAGMA table_info(student_profiles)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'roll_number' not in columns:
            print("Adding 'roll_number' column to 'student_profiles' table...")
            cursor.execute("ALTER TABLE student_profiles ADD COLUMN roll_number VARCHAR")
            conn.commit()
            print("'roll_number' column added successfully.")
        else:
            print("'roll_number' column already exists.")

    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
