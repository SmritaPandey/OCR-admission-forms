"""
Test script to upload multiple PDF files and test OCR functionality
"""
import requests
import os
from pathlib import Path

# API endpoint
API_BASE_URL = "http://localhost:8000"

# List of PDF files to upload
PDF_FILES = [
    r"C:\Users\as\Downloads\OCR\paridhi kiran.pdf",
    r"C:\Users\as\Downloads\OCR\sara hanfi.pdf",
    r"C:\Users\as\Downloads\OCR\ravi chaudhary.pdf",
    r"C:\Users\as\Downloads\OCR\ujjwal kumar.pdf",
    r"C:\Users\as\Downloads\OCR\student data form scanned.pdf",
    r"C:\Users\as\Downloads\OCR\SRCC DATA FORM-1-4.pdf",
    r"C:\Users\as\Downloads\OCR\jatin.pdf",
]

def upload_pdf(file_path: str, ocr_provider: str = "tesseract"):
    """Upload a PDF file and process it with OCR"""
    if not os.path.exists(file_path):
        print(f"ERROR: File not found: {file_path}")
        return None
    
    filename = os.path.basename(file_path)
    print(f"\nUploading: {filename}")
    
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (filename, f, 'application/pdf')}
            params = {'ocr_provider': ocr_provider}
            
            response = requests.post(
                f"{API_BASE_URL}/api/upload",
                files=files,
                params=params,
                timeout=300  # 5 minutes timeout for large files
            )
            
            if response.status_code == 201:
                result = response.json()
                form_id = result.get('id')
                status = result.get('status')
                print(f"SUCCESS! Form ID: {form_id}, Status: {status}")
                
                # Get extracted text preview
                if result.get('extracted_data'):
                    raw_text = result['extracted_data'].get('raw_text', '')
                    if raw_text:
                        preview = raw_text[:200] + "..." if len(raw_text) > 200 else raw_text
                        print(f"Extracted text preview:\n{preview}\n")
                    confidence = result['extracted_data'].get('confidence', 0)
                    print(f"Confidence: {confidence}%")
                
                return result
            else:
                print(f"ERROR {response.status_code}: {response.text}")
                return None
                
    except Exception as e:
        print(f"EXCEPTION: {str(e)}")
        return None

def main():
    print("Starting PDF upload and OCR test...")
    print(f"Testing {len(PDF_FILES)} PDF files\n")
    
    results = []
    for pdf_file in PDF_FILES:
        result = upload_pdf(pdf_file, ocr_provider="tesseract")
        if result:
            results.append(result)
    
    print(f"\nSummary:")
    print(f"Successfully processed: {len(results)}/{len(PDF_FILES)} files")
    
    if results:
        print(f"\nProcessed Forms:")
        for result in results:
            print(f"  - Form ID {result.get('id')}: {result.get('filename')} (Status: {result.get('status')})")

if __name__ == "__main__":
    main()

