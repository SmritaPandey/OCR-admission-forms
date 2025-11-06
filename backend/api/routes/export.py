from fastapi import APIRouter, Response, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from backend.database import get_db, AdmissionForm, FormStatus
import csv
import json
import io

router = APIRouter()

@router.get("/export")
async def export_forms(
    format: str = Query("csv", regex="^(csv|json)$"),
    status: Optional[FormStatus] = Query(None),
    db: Session = Depends(get_db)
):
    """Export verified forms to CSV or JSON"""
    query = db.query(AdmissionForm)
    
    # Filter by status if provided
    if status:
        query = query.filter(AdmissionForm.status == status)
    else:
        # Default to verified forms only
        query = query.filter(AdmissionForm.status == FormStatus.VERIFIED)
    
    forms = query.all()
    
    if format == "csv":
        return export_to_csv(forms)
    else:
        return export_to_json(forms)

def export_to_csv(forms: List[AdmissionForm]) -> StreamingResponse:
    """Export forms to CSV format"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        "ID", "Student Name", "Date of Birth", "Address", "Phone Number",
        "Email", "Guardian Name", "Guardian Phone", "Course Applied",
        "Previous Qualification", "Upload Date", "Verified Date", "Status"
    ])
    
    # Write data
    for form in forms:
        writer.writerow([
            form.id,
            form.student_name or "",
            form.date_of_birth or "",
            form.address or "",
            form.phone_number or "",
            form.email or "",
            form.guardian_name or "",
            form.guardian_phone or "",
            form.course_applied or "",
            form.previous_qualification or "",
            form.upload_date.isoformat() if form.upload_date else "",
            form.verified_date.isoformat() if form.verified_date else "",
            form.status.value
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=admission_forms.csv"}
    )

def export_to_json(forms: List[AdmissionForm]) -> Response:
    """Export forms to JSON format"""
    data = []
    for form in forms:
        data.append({
            "id": form.id,
            "filename": form.filename,
            "student_name": form.student_name,
            "date_of_birth": form.date_of_birth,
            "address": form.address,
            "phone_number": form.phone_number,
            "email": form.email,
            "guardian_name": form.guardian_name,
            "guardian_phone": form.guardian_phone,
            "course_applied": form.course_applied,
            "previous_qualification": form.previous_qualification,
            "additional_info": form.additional_info,
            "upload_date": form.upload_date.isoformat() if form.upload_date else None,
            "verified_date": form.verified_date.isoformat() if form.verified_date else None,
            "status": form.status.value
        })
    
    return Response(
        content=json.dumps(data, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=admission_forms.json"}
    )

