"""Inspect the admission_forms.db to find verified training data."""
import sqlite3
import json
import os

# Try both locations
for db_path in ["admission_forms.db", "data/admission_forms.db"]:
    if not os.path.exists(db_path):
        continue
    
    print(f"\n{'='*60}")
    print(f"  Database: {db_path} ({os.path.getsize(db_path)/1024:.0f} KB)")
    print(f"{'='*60}")
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # List tables
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in c.fetchall()]
    print(f"\n  Tables: {tables}")
    
    for table in tables:
        c.execute(f"SELECT COUNT(*) FROM [{table}]")
        count = c.fetchone()[0]
        print(f"    {table}: {count} rows")
        
        # Show columns
        c.execute(f"PRAGMA table_info([{table}])")
        cols = [r[1] for r in c.fetchall()]
        print(f"    Columns: {cols[:15]}{'...' if len(cols) > 15 else ''}")
        print(f"    Total columns: {len(cols)}")
        
        # Show sample of data
        if count > 0 and table == "admission_forms":
            print(f"\n  --- Sample admission_forms data ---")
            c.execute(f"SELECT * FROM [{table}] LIMIT 1")
            row = c.fetchone()
            if row:
                for col in cols[:30]:
                    val = row[col] if col in row.keys() else None
                    if val and str(val).strip():
                        display = str(val)[:80]
                        print(f"    {col}: {display}")
            
            # Count forms with status
            try:
                c.execute("SELECT status, COUNT(*) FROM admission_forms GROUP BY status")
                for r in c.fetchall():
                    print(f"\n  Status '{r[0]}': {r[1]} forms")
            except:
                pass
            
            # Count how many have populated fields
            key_fields = ["first_name", "student_name", "email", "phone_number", "course"]
            for f in key_fields:
                try:
                    c.execute(f"SELECT COUNT(*) FROM admission_forms WHERE [{f}] IS NOT NULL AND [{f}] != ''")
                    cnt = c.fetchone()[0]
                    print(f"  Forms with {f}: {cnt}")
                except:
                    pass
            
            # Check for file_path / image references
            try:
                c.execute("SELECT file_path FROM admission_forms WHERE file_path IS NOT NULL LIMIT 5")
                paths = [r[0] for r in c.fetchall()]
                print(f"\n  Sample file paths: {paths[:3]}")
            except:
                pass
    
    conn.close()

# Also check for SRC_DMS data
for candidate in [
    r"d:\SRC_DMS",
    r"c:\Users\as\Desktop\OCR-Installer-Final",
    r"c:\Users\as\AppData\Local\OCRAdmissionForms",
    r"c:\Users\as\AppData\Roaming\OCRAdmissionForms",
]:
    if os.path.exists(candidate):
        print(f"\n  Found: {candidate}")
        for root, dirs, files in os.walk(candidate):
            for f in files:
                if f.endswith(('.db', '.sqlite', '.json')):
                    full = os.path.join(root, f)
                    print(f"    {full} ({os.path.getsize(full)/1024:.0f} KB)")
            # Only first 3 levels
            if root.count(os.sep) - candidate.count(os.sep) > 3:
                break
