
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import io
import json
from datetime import datetime

from backend.models.form import FormStatus

# Mock data matches Form 73 scenario
MOCK_EXTRACTION_RESULT = {
    "raw_text": "SHRI RAM COLLEGE OF COMMERCE... KARAN... YADAV... 194",
    "confidence": 0.95,
    "provider": "mock_provider",
    "structured_data": {
        "student_name": "Karan Yadav",
        "date_of_birth": "27/06/2006",
        "father_name": "Ani L Yadav",
        "cuet_score": "963",
        "cuet_total_score": "1250",
        "cuet_subject_1": "English",
        "cuet_score_obtained_1": "165",
        "cuet_subject_2": "Accountancy",
        "cuet_score_obtained_2": "194"
    }
}

def test_full_lifecycle(client: TestClient, db: Session, monkeypatch):
    """
    Test the full lifecycle of a form:
    1. Upload
    2. Extract (Mocked)
    3. Get Details
    4. Verify/Update
    5. Search
    6. Delete
    """
    
    # 1. Upload Form
    # We mock the OCR extraction called implicitly ideally, 
    # but for integration test on API level, let's upload first.
    # Note: real background tasks might not run in this TestClient environment easily 
    # unless we stick to synchronous endpoints or mock the background task.
    # For now, we tested upload endpoint in isolation before. 
    # Let's direct-create a form in DB to simulate 'Uploaded' state if file handling is complex to mock.
    
    # Simulating file upload by creating DB entry directly for stability
    from backend.database import AdmissionForm
    form = AdmissionForm(
        filename="test_form_73.pdf",
        file_path="uploads/test_form_73.pdf",
        status=FormStatus.UPLOADED,
        upload_date=datetime.utcnow(),
        ocr_provider="mock_provider"
    )
    db.add(form)
    db.commit()
    db.refresh(form)
    
    form_id = form.id
    assert form_id is not None
    
    # 2. Extract (Mocked)
    # We call the re-extract endpoint, mocking the pipeline
    async def mock_extraction(*args, **kwargs):
        return MOCK_EXTRACTION_RESULT

    monkeypatch.setattr("backend.utils.extraction_pipeline.run_enhanced_extraction", mock_extraction)
    
    response = client.post(f"/api/forms/{form_id}/extract")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Re-extraction completed"
    assert data["result"]["structured_data"]["student_name"] == "Karan Yadav"
    
    # Verify DB updated
    db.refresh(form)
    assert form.status == FormStatus.EXTRACTED
    assert form.extracted_data["structured_data"]["cuet_score"] == "963"
    
    # 3. Get Details
    response = client.get(f"/api/forms/{form_id}")
    assert response.status_code == 200
    details = response.json()
    assert details["filename"] == "test_form_73.pdf"
    
    # 4. Verify/Update (The Autofill -> Save flow)
    # The frontend Autofill takes 'extracted_data' and puts it into 'verification' payload
    verification_payload = {
        "student_name": "Karan Yadav Verified", # User corrected/verified name
        "date_of_birth": "27/06/2006",
        "cuet_score": "963",
        "college_roll_no": "24BC105",
        "aadhar_number": "123456789012"
    }
    
    response = client.put(f"/api/forms/{form_id}/verify", json=verification_payload)
    if response.status_code != 200:
        print(response.json())
        
    assert response.status_code == 200
    verified_data = response.json()
    assert verified_data["status"] == "verified"
    assert verified_data["student_name"] == "Karan Yadav Verified"
    assert verified_data["student_profile_id"] is not None
    
    # 5. Search
    response = client.get("/api/forms/search/results?student_name=Karan")
    assert response.status_code == 200
    results = response.json()
    assert len(results) >= 1
    assert results[0]["student_name"] == "Karan Yadav Verified"
    
    # 6. Delete
    response = client.delete(f"/api/forms/{form_id}")
    assert response.status_code == 200
    
    # Verify gone
    response = client.get(f"/api/forms/{form_id}")
    assert response.status_code == 404
