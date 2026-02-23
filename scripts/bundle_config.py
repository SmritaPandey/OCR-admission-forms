#!/usr/bin/env python3
"""
Script to bundle configuration files for desktop app.
This copies .env and credential files to the data directory.
"""

import os
import shutil
import sys
from pathlib import Path

def bundle_config():
    """Bundle configuration files for desktop app"""
    project_root = Path(__file__).parent.parent
    data_dir = project_root / "data"
    
    # Create data directory if it doesn't exist
    data_dir.mkdir(exist_ok=True)
    
    # Files to bundle
    files_to_bundle = [
        (".env", "data/.env"),
        ("google-cloud-credentials.json", "data/google-cloud-credentials.json"),
        ("admission_forms.db", "data/admission_forms.db"),
    ]
    
    bundled = []
    skipped = []
    
    for source_file, dest_path in files_to_bundle:
        source_path = project_root / source_file
        dest_full_path = project_root / dest_path
        
        if source_path.exists():
            # Create parent directory if needed
            dest_full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file
            shutil.copy2(source_path, dest_full_path)
            bundled.append(source_file)
            print(f"[OK] Bundled {source_file} -> {dest_path}")
        else:
            skipped.append(source_file)
            print(f"[SKIP] Skipped {source_file} (not found)")
    
    print(f"\nBundled {len(bundled)} file(s), skipped {len(skipped)} file(s)")
    
    if skipped:
        print("\nNote: Missing files will need to be added manually or created by the user.")
    
    return len(bundled) > 0

if __name__ == "__main__":
    try:
        success = bundle_config()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
