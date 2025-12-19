"""
Google Cloud Vision API Setup Helper
This script helps set up Google Cloud Vision API credentials.
"""
import os
import sys
import json
from pathlib import Path


def check_credentials():
    """Check if Google Cloud credentials are configured"""
    # Check environment variable
    creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    if creds_path and Path(creds_path).exists():
        print(f"✓ Found credentials at: {creds_path}")
        return creds_path
    
    # Check default location
    default_paths = [
        Path.home() / ".config" / "gcloud" / "application_default_credentials.json",
        Path.home() / "google-cloud-credentials.json",
        Path.cwd() / "google-cloud-credentials.json",
    ]
    
    for path in default_paths:
        if path.exists():
            print(f"✓ Found credentials at: {path}")
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(path)
            return str(path)
    
    print("✗ No credentials found")
    return None


def validate_credentials(creds_path: str) -> bool:
    """Validate that credentials file is valid JSON"""
    try:
        with open(creds_path, 'r') as f:
            creds = json.load(f)
        
        # Check for required fields
        required_fields = ['type', 'project_id']
        missing = [f for f in required_fields if f not in creds]
        
        if missing:
            print(f"✗ Missing required fields: {', '.join(missing)}")
            return False
        
        print(f"✓ Valid credentials file")
        print(f"  Project ID: {creds.get('project_id', 'N/A')}")
        print(f"  Type: {creds.get('type', 'N/A')}")
        return True
        
    except json.JSONDecodeError:
        print(f"✗ Invalid JSON in credentials file")
        return False
    except Exception as e:
        print(f"✗ Error reading credentials: {e}")
        return False


def test_vision_api():
    """Test if Google Vision API is accessible"""
    try:
        from google.cloud import vision
        client = vision.ImageAnnotatorClient()
        print("✓ Google Vision client initialized successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to initialize Google Vision client: {e}")
        return False


def print_setup_instructions():
    """Print instructions for setting up Google Cloud"""
    print("\n" + "="*80)
    print("GOOGLE CLOUD VISION API SETUP INSTRUCTIONS")
    print("="*80)
    print("""
To use Google Cloud Vision API, you need to:

1. CREATE A GOOGLE CLOUD PROJECT
   - Go to: https://console.cloud.google.com/
   - Click "Select a project" → "New Project"
   - Enter project name (e.g., "ocr-admission-forms")
   - Click "Create"

2. ENABLE THE VISION API
   - Go to: https://console.cloud.google.com/apis/library/vision.googleapis.com
   - Select your project
   - Click "Enable"

3. CREATE A SERVICE ACCOUNT
   - Go to: https://console.cloud.google.com/iam-admin/serviceaccounts
   - Click "Create Service Account"
   - Enter name (e.g., "ocr-service")
   - Click "Create and Continue"
   - Grant role: "Cloud Vision API User" or "Owner"
   - Click "Continue" → "Done"

4. CREATE AND DOWNLOAD KEY
   - Click on the service account you just created
   - Go to "Keys" tab
   - Click "Add Key" → "Create new key"
   - Choose "JSON" format
   - Download the JSON file
   - Save it as: google-cloud-credentials.json (in project root)

5. SET ENVIRONMENT VARIABLE
   - Linux/Mac:
     export GOOGLE_APPLICATION_CREDENTIALS="/path/to/google-cloud-credentials.json"
   
   - Windows:
     set GOOGLE_APPLICATION_CREDENTIALS=C:\path\to\google-cloud-credentials.json

6. VERIFY SETUP
   - Run this script again to verify credentials are working

NOTE: The first 1000 pages per month are FREE!
      After that, it costs $1.50 per 1000 pages.
""")
    print("="*80)


def main():
    print("Google Cloud Vision API Setup Check")
    print("="*80)
    
    # Check for credentials
    creds_path = check_credentials()
    
    if not creds_path:
        print_setup_instructions()
        return False
    
    # Validate credentials
    if not validate_credentials(creds_path):
        print_setup_instructions()
        return False
    
    # Test API
    if not test_vision_api():
        print("\nTroubleshooting:")
        print("1. Make sure Vision API is enabled in your project")
        print("2. Check that your service account has the correct permissions")
        print("3. Verify billing is enabled (free tier is fine)")
        return False
    
    print("\n" + "="*80)
    print("✓ SETUP COMPLETE! Google Cloud Vision API is ready to use.")
    print("="*80)
    
    # Update .env file if it exists
    env_file = Path(".env")
    if env_file.exists():
        print("\nUpdating .env file...")
        with open(env_file, 'r') as f:
            content = f.read()
        
        if 'GOOGLE_APPLICATION_CREDENTIALS' not in content:
            with open(env_file, 'a') as f:
                f.write(f"\nGOOGLE_APPLICATION_CREDENTIALS={creds_path}\n")
            print(f"✓ Added GOOGLE_APPLICATION_CREDENTIALS to .env")
    else:
        print(f"\nTip: Create a .env file with:")
        print(f"GOOGLE_APPLICATION_CREDENTIALS={creds_path}")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
