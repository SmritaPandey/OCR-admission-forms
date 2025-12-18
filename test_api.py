#!/usr/bin/env python3
"""
Test script for new API endpoints
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_health():
    """Test health endpoint"""
    print("Testing /health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}\n")
    return response.status_code == 200

def test_batch_upload_jobs():
    """Test batch upload jobs list"""
    print("Testing /api/batch-upload/jobs/list endpoint...")
    response = requests.get(f"{BASE_URL}/api/batch-upload/jobs/list")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}\n")
    return response.status_code == 200

def test_document_categories():
    """Test document categories"""
    print("Testing /api/documents/categories/list endpoint...")
    response = requests.get(f"{BASE_URL}/api/documents/categories/list")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Found {len(data.get('categories', []))} categories")
    for cat in data.get('categories', []):
        print(f"  - {cat.get('name')}")
    print()
    return response.status_code == 200

def test_ocr_providers():
    """Test OCR providers list"""
    print("Testing /api/providers endpoint...")
    response = requests.get(f"{BASE_URL}/api/providers")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Default provider: {data.get('default')}")
    print(f"Available providers: {data.get('providers', [])}\n")
    return response.status_code == 200

def test_forms_list():
    """Test forms list"""
    print("Testing /api/forms/ endpoint...")
    response = requests.get(f"{BASE_URL}/api/forms/")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Total forms: {data.get('total', 0)}")
    print(f"Forms in response: {len(data.get('forms', []))}\n")
    return response.status_code == 200

def test_annotation_export():
    """Test annotation export"""
    print("Testing /api/export/training-data endpoint...")
    response = requests.get(f"{BASE_URL}/api/export/training-data?format=json")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Format: {data.get('format')}")
    print(f"Total annotations: {data.get('total_annotations', 0)}\n")
    return response.status_code == 200

def main():
    """Run all tests"""
    print("=" * 60)
    print("API Endpoint Testing")
    print("=" * 60)
    print()
    
    tests = [
        ("Health Check", test_health),
        ("Batch Upload Jobs", test_batch_upload_jobs),
        ("Document Categories", test_document_categories),
        ("OCR Providers", test_ocr_providers),
        ("Forms List", test_forms_list),
        ("Annotation Export", test_annotation_export),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"Error in {name}: {e}\n")
            results.append((name, False))
    
    print("=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} - {name}")
    
    passed = sum(1 for _, result in results if result)
    print(f"\nTotal: {passed}/{len(results)} tests passed")

if __name__ == "__main__":
    main()

