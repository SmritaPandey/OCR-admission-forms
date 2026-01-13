import logging

from fastapi import APIRouter, Response, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, Iterable
from datetime import datetime
from backend.database import get_db, AdmissionForm, FormStatus
from backend.api.routes.forms import apply_form_filters
import csv
import json
import io

router = APIRouter()
logger = logging.getLogger(__name__)

EXPORT_FIELDS = [
    ("id", "Form ID"),
    ("filename", "Filename"),
    ("status", "Status"),
    ("ocr_provider", "OCR Provider"),
    ("student_profile_id", "Student Profile ID"),
    ("upload_date", "Upload Date"),
    ("verified_date", "Verified Date"),
    ("verified_by", "Verified By"),
    # Basic Details
    ("student_name", "Student Name"),
    ("date_of_birth", "Date of Birth"),
    ("gender", "Gender"),
    ("category", "Category"),
    ("nationality", "Nationality"),
    ("religion", "Religion"),
    ("aadhar_number", "Aadhar Number"),
    ("blood_group", "Blood Group"),
    # Address Details
    ("permanent_address", "Permanent Address"),
    ("correspondence_address", "Correspondence Address"),
    ("city", "City"),
    ("state", "State"),
    ("pincode", "Pincode"),
    # Contact Details
    ("phone_number", "Phone Number"),
    ("alternate_phone", "Alternate Phone"),
    ("email", "Email"),
    ("emergency_contact_name", "Emergency Contact Name"),
    ("emergency_contact_phone", "Emergency Contact Phone"),
    # Guardian / Parent Details
    ("father_name", "Father Name"),
    ("father_occupation", "Father Occupation"),
    ("father_phone", "Father Phone"),
    ("mother_name", "Mother Name"),
    ("mother_occupation", "Mother Occupation"),
    ("mother_phone", "Mother Phone"),
    ("guardian_name", "Guardian Name"),
    ("guardian_relation", "Guardian Relation"),
    ("guardian_phone", "Guardian Phone"),
    ("annual_income", "Annual Income"),
    # Educational Qualifications
    ("tenth_board", "10th Board"),
    ("tenth_year", "10th Year"),
    ("tenth_percentage", "10th Percentage"),
    ("tenth_school", "10th School"),
    ("twelfth_board", "12th Board"),
    ("twelfth_year", "12th Year"),
    ("twelfth_percentage", "12th Percentage"),
    ("twelfth_school", "12th School"),
    ("previous_qualification", "Previous Qualification"),
    ("graduation_details", "Graduation Details"),
    # Course Application Details
    ("course_applied", "Course Applied"),
    ("application_number", "Application Number"),
    ("enrollment_number", "Enrollment Number"),
    ("admission_date", "Admission Date"),
    ("additional_info", "Additional Info"),
]

def form_to_csv_row(form: AdmissionForm) -> list[str]:
    row: list[str] = []
    for attr, _ in EXPORT_FIELDS:
        value = getattr(form, attr, None)
        if isinstance(value, datetime):
            value = value.isoformat()
        elif isinstance(value, FormStatus):
            value = value.value
        elif isinstance(value, dict):
            value = json.dumps(value, ensure_ascii=False)
        elif value is None:
            value = ""
        row.append(str(value) if not isinstance(value, str) else value)
    return row


def form_to_json_dict(form: AdmissionForm) -> Dict[str, Any]:
    record: Dict[str, Any] = {}
    for attr, _ in EXPORT_FIELDS:
        value = getattr(form, attr, None)
        if isinstance(value, datetime):
            record[attr] = value.isoformat()
        elif isinstance(value, FormStatus):
            record[attr] = value.value
        elif isinstance(value, dict):
            record[attr] = value
        else:
            record[attr] = value
    if record.get("additional_info") is None:
        record["additional_info"] = {}
    return record

@router.get("/export")
async def export_forms(
    format: str = Query("csv", regex="^(csv|json|excel|pdf)$"),
    status: Optional[FormStatus] = Query(None),
    student_name: Optional[str] = Query(None),
    phone_number: Optional[str] = Query(None),
    email: Optional[str] = Query(None),
    enrollment_number: Optional[str] = Query(None),
    application_number: Optional[str] = Query(None),
    course_applied: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    db: Session = Depends(get_db)
):
    """Export verified forms to CSV or JSON"""
    query = db.query(AdmissionForm)

    query = apply_form_filters(
        query,
        student_name=student_name,
        phone_number=phone_number,
        email=email,
        enrollment_number=enrollment_number,
        application_number=application_number,
        course_applied=course_applied,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )

    if status is None:
        query = query.filter(AdmissionForm.status == FormStatus.VERIFIED)
    
    forms = query.order_by(AdmissionForm.upload_date.desc(), AdmissionForm.id.desc()).all()

    filters_snapshot = {
        "student_name": student_name,
        "phone_number": phone_number,
        "email": email,
        "enrollment_number": enrollment_number,
        "application_number": application_number,
        "course_applied": course_applied,
        "status": status.value if status else None,
        "date_from": date_from.isoformat() if date_from else None,
        "date_to": date_to.isoformat() if date_to else None,
    }
    filters_snapshot = {key: value for key, value in filters_snapshot.items() if value}

    logger.info(
        "Exporting forms format=%s count=%s filters=%s",
        format,
        len(forms),
        filters_snapshot,
    )
    
    if format == "csv":
        return export_to_csv(forms)
    elif format == "excel":
        return export_to_excel_forms(forms)
    elif format == "pdf":
        return export_to_pdf_forms(forms)
    else:
        return export_to_json(forms, filters_snapshot)

def export_to_excel_forms(forms: Iterable[AdmissionForm]) -> StreamingResponse:
    """Export forms to Excel format"""
    import pandas as pd
    
    all_data = []
    for form in forms:
        record = form_to_json_dict(form)
        # Flatten additional_info if needed or handle as string
        if "additional_info" in record and record["additional_info"]:
            record["additional_info"] = json.dumps(record["additional_info"])
        all_data.append(record)
        
    df = pd.DataFrame(all_data)
    
    # Map internal IDs to Headers
    header_map = {attr: header for attr, header in EXPORT_FIELDS}
    df = df.rename(columns=header_map)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Admission Forms', index=False)
    
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=admission_forms.xlsx"}
    )

def export_to_pdf_forms(forms: Iterable[AdmissionForm]) -> StreamingResponse:
    """Export forms to PDF format"""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.enums import TA_CENTER
        
        output = io.BytesIO()
        doc = SimpleDocTemplate(output, pagesize=landscape(A4), topMargin=0.5*inch, bottomMargin=0.5*inch)
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('Title', parent=styles['Heading1'], alignment=TA_CENTER)
        
        elements = [Paragraph("Admission Forms Export", title_style), Spacer(1, 20)]
        
        # Select key fields for PDF (A4 landscape can't fit all 75 fields)
        key_fields = [
            ("id", "ID"), ("student_name", "Student Name"), ("status", "Status"),
            ("course_applied", "Course"), ("phone_number", "Phone"), ("upload_date", "Date")
        ]
        
        table_data = [[header for _, header in key_fields]]
        for form in forms:
            row = []
            for attr, _ in key_fields:
                val = getattr(form, attr, "")
                if isinstance(val, datetime): val = val.strftime("%Y-%m-%d")
                elif isinstance(val, FormStatus): val = val.value
                row.append(str(val) if val is not None else "-")
            table_data.append(row)
            
        t = Table(table_data)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.navy),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey)
        ]))
        elements.append(t)
        
        doc.build(elements)
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=admission_forms.pdf"}
        )
    except ImportError:
        raise HTTPException(status_code=500, detail="PDF export requires reportlab library. Install with: pip install reportlab")

def export_to_csv(forms: Iterable[AdmissionForm]) -> StreamingResponse:
    """Export forms to CSV format using a streaming response."""

    def row_iterator():
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([header for _, header in EXPORT_FIELDS])
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)

        for form in forms:
            writer.writerow(form_to_csv_row(form))
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    return StreamingResponse(
        row_iterator(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=admission_forms.csv"},
    )

def export_to_json(forms: Iterable[AdmissionForm], filters: Dict[str, Any]) -> Response:
    """Export forms to JSON format."""
    forms_list = list(forms)
    payload = {
        "generated_at": datetime.utcnow().isoformat(),
        "count": len(forms_list),
        "filters": filters,
        "forms": [form_to_json_dict(form) for form in forms_list],
    }

    return Response(
        content=json.dumps(payload, indent=2, ensure_ascii=False),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=admission_forms.json"},
    )

