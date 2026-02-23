#!/usr/bin/env python3
"""
Main script to run combined OCR processing and training data generation.
This script processes all PDFs using the combined Tesseract + Google Vision approach.
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.scripts.process_pdfs_combined_ocr import process_all_pdfs
from backend.scripts.setup_google_cloud import check_credentials, test_vision_api

def main():
    print("="*80)
    print("COMBINED OCR PROCESSING & TRAINING DATA GENERATION")
    print("="*80)
    print()
    
    # Check Google Cloud setup
    print("Checking Google Cloud Vision API setup...")
    creds_path = check_credentials()
    
    if not creds_path:
        print("\n❌ Google Cloud credentials not found!")
        print("\nPlease run: python backend/scripts/setup_google_cloud.py")
        print("Or follow the setup instructions in the script.")
        return 1
    
    if not test_vision_api():
        print("\n❌ Google Vision API not accessible!")
        print("Please check your credentials and API enablement.")
        return 1
    
    print("✓ Google Cloud Vision API is ready\n")
    
    # Set paths
    pdfs_dir = Path("data/samples/pdfs")
    blank_form = pdfs_dir / "student data form scanned.pdf"
    output_dir = Path("training_output")
    
    # Check if directories exist
    if not pdfs_dir.exists():
        print(f"❌ PDFs directory not found: {pdfs_dir}")
        return 1
    
    if not blank_form.exists():
        print(f"❌ Blank form not found: {blank_form}")
        print(f"Available PDFs:")
        for pdf in pdfs_dir.glob("*.pdf"):
            print(f"  - {pdf.name}")
        return 1
    
    print(f"PDFs directory: {pdfs_dir}")
    print(f"Blank form: {blank_form}")
    print(f"Output directory: {output_dir}")
    print()
    
    # Process all PDFs
    try:
        process_all_pdfs(
            pdfs_dir=str(pdfs_dir),
            blank_form_path=str(blank_form),
            output_dir=str(output_dir),
            method="method_two"  # Use coordinate matching method
        )
        print("\n✅ Processing complete!")
        return 0
    except Exception as e:
        print(f"\n❌ Error during processing: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
