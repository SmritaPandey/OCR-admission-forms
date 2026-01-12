"""
Student Export/Import Routes
Handles CSV and Excel export/import for student records
"""
from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, asc, desc, func
from typing import Optional, List
from backend.database import get_db, StudentProfile, AdmissionForm, StudentDocument
from datetime import datetime
import csv
import io
from typing import Dict, Any
import pandas as pd

router = APIRouter()


def get_excel_column_letter(col_idx: int) -> str:
    """
    Convert a column index (0-based) to Excel column letter(s).
    Examples: 0 -> A, 1 -> B, 25 -> Z, 26 -> AA, 27 -> AB, etc.
    """
    result = ""
    col_idx += 1  # Convert to 1-based
    while col_idx > 0:
        col_idx -= 1
        result = chr(65 + (col_idx % 26)) + result
        col_idx //= 26
    return result

# Sort options
SORT_OPTIONS = {
    "name": "student_name",
    "roll_number": "roll_number",
    "aadhar": "aadhar_number",
    "created": "created_date",
    "updated": "updated_date",
}

def get_student_data_query(
    db: Session,
    student_name: Optional[str] = None,
    roll_number: Optional[str] = None,
    aadhar_number: Optional[str] = None,
    phone_number: Optional[str] = None,
    email: Optional[str] = None,
    course_applied: Optional[str] = None,
    academic_session: Optional[str] = None,
    gender: Optional[str] = None,
    category: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    sort_by: str = "updated",
    sort_order: str = "desc"
):
    """Build query for student records with filters and sorting"""
    query = db.query(StudentProfile)
    
    # Build filters
    profile_filters = []
    if student_name:
        profile_filters.append(StudentProfile.student_name.ilike(f"%{student_name}%"))
    if roll_number:
        profile_filters.append(StudentProfile.roll_number.ilike(f"%{roll_number}%"))
    if aadhar_number:
        profile_filters.append(StudentProfile.aadhar_number.ilike(f"%{aadhar_number}%"))
    
    # Join with forms if form filters are provided
    has_form_filters = any([phone_number, email, course_applied, academic_session, gender, category, city, state])
    if has_form_filters:
        query = query.join(AdmissionForm, StudentProfile.id == AdmissionForm.student_profile_id)
        form_filters = []
        if phone_number:
            form_filters.append(AdmissionForm.phone_number.ilike(f"%{phone_number}%"))
        if email:
            form_filters.append(AdmissionForm.email.ilike(f"%{email}%"))
        if course_applied:
            form_filters.append(AdmissionForm.course_applied.ilike(f"%{course_applied}%"))
        if academic_session:
            # Filter by academic session - can match full session string or just the year
            form_filters.append(
                or_(
                    AdmissionForm.academic_session.ilike(f"%{academic_session}%"),
                    AdmissionForm.academic_session.ilike(f"%{academic_session}-%"),
                    AdmissionForm.academic_session.ilike(f"%-{academic_session}%")
                )
            )
        if gender:
            # Use case-insensitive exact match for gender (not partial match)
            form_filters.append(func.lower(AdmissionForm.gender) == func.lower(gender))
        if category:
            form_filters.append(AdmissionForm.category.ilike(f"%{category}%"))
        if city:
            form_filters.append(AdmissionForm.city.ilike(f"%{city}%"))
        if state:
            form_filters.append(AdmissionForm.state.ilike(f"%{state}%"))
        if form_filters:
            query = query.filter(and_(*form_filters))
        query = query.distinct()
    
    if profile_filters:
        query = query.filter(and_(*profile_filters))
    
    # Apply sorting
    sort_column = SORT_OPTIONS.get(sort_by, "updated_date")
    if sort_order.lower() == "asc":
        query = query.order_by(asc(getattr(StudentProfile, sort_column)))
    else:
        query = query.order_by(desc(getattr(StudentProfile, sort_column)))
    
    return query

def get_student_export_data(profile: StudentProfile, db: Session) -> Dict[str, Any]:
    """Get comprehensive student data for export with ALL form fields"""
    # Get latest verified form, or most recent form
    latest_form = db.query(AdmissionForm).filter(
        AdmissionForm.student_profile_id == profile.id
    ).order_by(AdmissionForm.upload_date.desc()).first()
    
    # Start with profile data
    data = {
        "ID": profile.id,
        "Student Name": profile.student_name or "",
        "Roll Number": profile.roll_number or "",
        "Aadhar Number": profile.aadhar_number or "",
        "Created Date": profile.created_date.strftime("%Y-%m-%d %H:%M:%S") if profile.created_date else "",
        "Updated Date": profile.updated_date.strftime("%Y-%m-%d %H:%M:%S") if profile.updated_date else "",
    }
    
    # Add ALL form fields if available
    if latest_form:
        # Academic & Admission Details
        data.update({
            "Academic Session": latest_form.academic_session or "",
            "Course": latest_form.course or "",
            "Admission Category": latest_form.admission_category or "",
            "Admission Category Other": latest_form.admission_category_other or "",
            "DU Portal Form Number": latest_form.du_portal_form_number or "",
            "CUET Score": latest_form.cuet_score or "",
            "Total CUET Score": latest_form.cuet_total_score or "",
            "College Roll No": latest_form.college_roll_no or "",
            "Date of Admission": latest_form.date_of_admission or "",
        })
        
        # CUET Marks (all 6 subjects)
        data.update({
            "CUET Subject 1": latest_form.cuet_subject_1 or "",
            "CUET Total Score 1": latest_form.cuet_total_score_1 or "",
            "CUET Score Obtained 1": latest_form.cuet_score_obtained_1 or "",
            "CUET Subject 2": latest_form.cuet_subject_2 or "",
            "CUET Total Score 2": latest_form.cuet_total_score_2 or "",
            "CUET Score Obtained 2": latest_form.cuet_score_obtained_2 or "",
            "CUET Subject 3": latest_form.cuet_subject_3 or "",
            "CUET Total Score 3": latest_form.cuet_total_score_3 or "",
            "CUET Score Obtained 3": latest_form.cuet_score_obtained_3 or "",
            "CUET Subject 4": latest_form.cuet_subject_4 or "",
            "CUET Total Score 4": latest_form.cuet_total_score_4 or "",
            "CUET Score Obtained 4": latest_form.cuet_score_obtained_4 or "",
            "CUET Subject 5": latest_form.cuet_subject_5 or "",
            "CUET Total Score 5": latest_form.cuet_total_score_5 or "",
            "CUET Score Obtained 5": latest_form.cuet_score_obtained_5 or "",
            "CUET Subject 6": latest_form.cuet_subject_6 or "",
            "CUET Total Score 6": latest_form.cuet_total_score_6 or "",
            "CUET Score Obtained 6": latest_form.cuet_score_obtained_6 or "",
        })
        
        # Personal Details
        data.update({
            "First Name": latest_form.first_name or "",
            "Middle Name": latest_form.middle_name or "",
            "Surname": latest_form.surname or "",
            "Date of Birth": latest_form.date_of_birth or "",
            "Gender": latest_form.gender or "",
            "Category": latest_form.category or "",
            "Nationality": latest_form.nationality or "",
            "Religion": latest_form.religion or "",
            "Blood Group": latest_form.blood_group or "",
            "Below Poverty Line": latest_form.below_poverty_line or "",
            "Minority Category": latest_form.minority_category or "",
            "Annual Income": latest_form.annual_income or "",
        })
        
        # Permanent Address
        data.update({
            "Permanent Address Line 1": latest_form.permanent_address_line1 or "",
            "Permanent Address Line 2": latest_form.permanent_address_line2 or "",
            "Permanent Address Line 3": latest_form.permanent_address_line3 or "",
            "Permanent State": latest_form.permanent_state or "",
            "Permanent Pincode": latest_form.permanent_pincode or "",
            "Permanent Address": latest_form.permanent_address or "",
        })
        
        # Correspondence Address
        data.update({
            "Correspondence Address Line 1": latest_form.correspondence_address_line1 or "",
            "Correspondence Address Line 2": latest_form.correspondence_address_line2 or "",
            "Correspondence Address Line 3": latest_form.correspondence_address_line3 or "",
            "Correspondence State": latest_form.correspondence_state or "",
            "Correspondence Pincode": latest_form.correspondence_pincode or "",
            "Correspondence Address": latest_form.correspondence_address or "",
            "City": latest_form.city or "",
            "State": latest_form.state or "",
            "Pincode": latest_form.pincode or "",
        })
        
        # Contact Details
        data.update({
            "Email": latest_form.email or "",
            "Phone Number": latest_form.phone_number or "",
            "Alternate Phone": latest_form.alternate_phone or "",
            "Emergency Contact Name": latest_form.emergency_contact_name or "",
            "Emergency Contact Phone": latest_form.emergency_contact_phone or "",
        })
        
        # Mother's Details
        data.update({
            "Mother Name": latest_form.mother_name or "",
            "Mother Occupation": latest_form.mother_occupation or "",
            "Mother Designation": latest_form.mother_designation or "",
            "Mother Organization": latest_form.mother_organization or "",
            "Mother Email": latest_form.mother_email or "",
            "Mother Mobile": latest_form.mother_mobile or "",
            "Mother Landline Code": latest_form.mother_landline_code or "",
            "Mother Landline": latest_form.mother_landline or "",
            "Mother Phone": latest_form.mother_phone or "",
        })
        
        # Father's Details
        data.update({
            "Father Name": latest_form.father_name or "",
            "Father Occupation": latest_form.father_occupation or "",
            "Father Designation": latest_form.father_designation or "",
            "Father Organization": latest_form.father_organization or "",
            "Father Email": latest_form.father_email or "",
            "Father Mobile": latest_form.father_mobile or "",
            "Father Landline Code": latest_form.father_landline_code or "",
            "Father Landline": latest_form.father_landline or "",
            "Father Phone": latest_form.father_phone or "",
        })
        
        # Local Guardian's Details
        data.update({
            "Guardian Name": latest_form.guardian_name or "",
            "Guardian Relation": latest_form.guardian_relation or "",
            "Guardian Residential Address": latest_form.guardian_residential_address or "",
            "Guardian Organization": latest_form.guardian_organization or "",
            "Guardian Email": latest_form.guardian_email or "",
            "Guardian Mobile": latest_form.guardian_mobile or "",
            "Guardian Landline Code": latest_form.guardian_landline_code or "",
            "Guardian Landline": latest_form.guardian_landline or "",
            "Guardian Phone": latest_form.guardian_phone or "",
        })
        
        # Qualifying Examination
        data.update({
            "12th Year": latest_form.twelfth_year or "",
            "12th Board": latest_form.twelfth_board or "",
            "12th Roll Number": latest_form.twelfth_roll_number or "",
            "12th Institution": latest_form.twelfth_institution or "",
            "12th Percentage": latest_form.twelfth_percentage or "",
            "12th School": latest_form.twelfth_school or "",
            "Hindi Studied Upto": latest_form.hindi_studied_upto or "",
            "10th Board": latest_form.tenth_board or "",
            "10th Year": latest_form.tenth_year or "",
            "10th Percentage": latest_form.tenth_percentage or "",
            "10th School": latest_form.tenth_school or "",
            "Previous Qualification": latest_form.previous_qualification or "",
            "Graduation Details": latest_form.graduation_details or "",
        })
        
        # Other Information
        data.update({
            "DU Enrollment Number": latest_form.du_enrollment_number or "",
            "Hindi Medium Preference": latest_form.hindi_medium_preference or "",
        })
        
        # Category Certificate Details
        data.update({
            "Category Certificate Authority": latest_form.category_certificate_authority or "",
            "Category Certificate Number": latest_form.category_certificate_number or "",
            "Category Certificate Date": latest_form.category_certificate_date or "",
            "Disability Percentage": latest_form.disability_percentage or "",
            "Disability Type": latest_form.disability_type or "",
            "UDID Number": latest_form.udid_number or "",
        })
        
        # Legacy/Backward Compatibility
        data.update({
            "Course Applied": latest_form.course_applied or "",
            "Application Number": latest_form.application_number or "",
            "Enrollment Number": latest_form.enrollment_number or "",
            "Admission Date": latest_form.admission_date or "",
        })
    else:
        # Fill all fields with empty strings for consistency
        all_fields = [
            # Academic & Admission Details
            "Academic Session", "Course", "Admission Category", "Admission Category Other",
            "DU Portal Form Number", "CUET Score", "Total CUET Score", "College Roll No",
            "Date of Admission",
            # CUET Marks
            "CUET Subject 1", "CUET Total Score 1", "CUET Score Obtained 1",
            "CUET Subject 2", "CUET Total Score 2", "CUET Score Obtained 2",
            "CUET Subject 3", "CUET Total Score 3", "CUET Score Obtained 3",
            "CUET Subject 4", "CUET Total Score 4", "CUET Score Obtained 4",
            "CUET Subject 5", "CUET Total Score 5", "CUET Score Obtained 5",
            "CUET Subject 6", "CUET Total Score 6", "CUET Score Obtained 6",
            # Personal Details
            "First Name", "Middle Name", "Surname", "Date of Birth", "Gender", "Category",
            "Nationality", "Religion", "Blood Group", "Below Poverty Line", "Minority Category",
            "Annual Income",
            # Address
            "Permanent Address Line 1", "Permanent Address Line 2", "Permanent Address Line 3",
            "Permanent State", "Permanent Pincode", "Permanent Address",
            "Correspondence Address Line 1", "Correspondence Address Line 2", "Correspondence Address Line 3",
            "Correspondence State", "Correspondence Pincode", "Correspondence Address",
            "City", "State", "Pincode",
            # Contact
            "Email", "Phone Number", "Alternate Phone", "Emergency Contact Name", "Emergency Contact Phone",
            # Mother's Details
            "Mother Name", "Mother Occupation", "Mother Designation", "Mother Organization",
            "Mother Email", "Mother Mobile", "Mother Landline Code", "Mother Landline", "Mother Phone",
            # Father's Details
            "Father Name", "Father Occupation", "Father Designation", "Father Organization",
            "Father Email", "Father Mobile", "Father Landline Code", "Father Landline", "Father Phone",
            # Guardian's Details
            "Guardian Name", "Guardian Relation", "Guardian Residential Address", "Guardian Organization",
            "Guardian Email", "Guardian Mobile", "Guardian Landline Code", "Guardian Landline", "Guardian Phone",
            # Qualifying Examination
            "12th Year", "12th Board", "12th Roll Number", "12th Institution", "12th Percentage", "12th School",
            "Hindi Studied Upto", "10th Board", "10th Year", "10th Percentage", "10th School",
            "Previous Qualification", "Graduation Details",
            # Other Information
            "DU Enrollment Number", "Hindi Medium Preference",
            # Category Certificate
            "Category Certificate Authority", "Category Certificate Number", "Category Certificate Date",
            "Disability Percentage", "Disability Type", "UDID Number",
            # Legacy
            "Course Applied", "Application Number", "Enrollment Number", "Admission Date",
        ]
        for field in all_fields:
            data[field] = ""
    
    # Add counts
    data["Forms Count"] = db.query(AdmissionForm).filter(
        AdmissionForm.student_profile_id == profile.id
    ).count()
    data["Documents Count"] = db.query(StudentDocument).filter(
        StudentDocument.student_profile_id == profile.id
    ).count()
    
    return data

@router.get("/export/csv")
async def export_students_csv(
    student_name: Optional[str] = Query(None),
    roll_number: Optional[str] = Query(None),
    aadhar_number: Optional[str] = Query(None),
    phone_number: Optional[str] = Query(None),
    email: Optional[str] = Query(None),
    course_applied: Optional[str] = Query(None),
    academic_session: Optional[str] = Query(None),
    gender: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    sort_by: str = Query("updated", description="Sort field: name, roll_number, aadhar, created, updated"),
    sort_order: str = Query("desc", description="Sort order: asc or desc"),
    db: Session = Depends(get_db)
):
    """Export student records to CSV with filtering and sorting - includes ALL form fields"""
    from fastapi.responses import StreamingResponse
    
    # Build query
    query = get_student_data_query(
        db, student_name, roll_number, aadhar_number,
        phone_number, email, course_applied, academic_session, gender, category, city, state,
        sort_by, sort_order
    )
    
    profiles = query.all()
    
    if not profiles:
        raise HTTPException(status_code=404, detail="No students found matching the criteria")
    
    # Create CSV in memory
    output = io.StringIO()
    writer = None
    
    for profile in profiles:
        data = get_student_export_data(profile, db)
        if writer is None:
            # Initialize writer with headers from first record
            fieldnames = list(data.keys())
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
        writer.writerow(data)
    
    output.seek(0)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"students_export_{timestamp}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@router.get("/export/excel")
async def export_students_excel(
    student_name: Optional[str] = Query(None),
    roll_number: Optional[str] = Query(None),
    aadhar_number: Optional[str] = Query(None),
    phone_number: Optional[str] = Query(None),
    email: Optional[str] = Query(None),
    course_applied: Optional[str] = Query(None),
    academic_session: Optional[str] = Query(None),
    gender: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    sort_by: str = Query("updated", description="Sort field: name, roll_number, aadhar, created, updated"),
    sort_order: str = Query("desc", description="Sort order: asc or desc"),
    db: Session = Depends(get_db)
):
    """Export student records to Excel with filtering and sorting - includes ALL form fields"""
    from fastapi.responses import StreamingResponse
    
    # Build query
    query = get_student_data_query(
        db, student_name, roll_number, aadhar_number,
        phone_number, email, course_applied, academic_session, gender, category, city, state,
        sort_by, sort_order
    )
    
    profiles = query.all()
    
    if not profiles:
        raise HTTPException(status_code=404, detail="No students found matching the criteria")
    
    # Build data for DataFrame
    all_data = []
    for profile in profiles:
        data = get_student_export_data(profile, db)
        all_data.append(data)
    
    # Create DataFrame
    df = pd.DataFrame(all_data)
    
    # Create Excel in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Students', index=False)
        
        # Get the worksheet to format it
        worksheet = writer.sheets['Students']
        
        # Auto-adjust column widths
        for idx, col in enumerate(df.columns):
            max_length = max(
                df[col].astype(str).map(len).max(),  # Max length in data
                len(col)  # Length of header
            )
            # Cap at 50 characters for readability
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[get_excel_column_letter(idx)].width = adjusted_width
    
    output.seek(0)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"students_export_{timestamp}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/export/json")
async def export_students_json(
    student_name: Optional[str] = Query(None),
    roll_number: Optional[str] = Query(None),
    aadhar_number: Optional[str] = Query(None),
    phone_number: Optional[str] = Query(None),
    email: Optional[str] = Query(None),
    course_applied: Optional[str] = Query(None),
    academic_session: Optional[str] = Query(None),
    gender: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    sort_by: str = Query("updated", description="Sort field: name, roll_number, aadhar, created, updated"),
    sort_order: str = Query("desc", description="Sort order: asc or desc"),
    db: Session = Depends(get_db)
):
    """Export student records to JSON with filtering and sorting - includes ALL form fields"""
    from fastapi.responses import StreamingResponse
    import json
    
    # Build query
    query = get_student_data_query(
        db, student_name, roll_number, aadhar_number,
        phone_number, email, course_applied, academic_session, gender, category, city, state,
        sort_by, sort_order
    )
    
    profiles = query.all()
    
    if not profiles:
        raise HTTPException(status_code=404, detail="No students found matching the criteria")
    
    # Build data list
    all_data = []
    for profile in profiles:
        data = get_student_export_data(profile, db)
        all_data.append(data)
    
    # Create JSON string
    json_output = json.dumps(all_data, indent=2, ensure_ascii=False, default=str)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"students_export_{timestamp}.json"
    
    return StreamingResponse(
        iter([json_output]),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/export/pdf")
async def export_students_pdf(
    student_name: Optional[str] = Query(None),
    roll_number: Optional[str] = Query(None),
    aadhar_number: Optional[str] = Query(None),
    phone_number: Optional[str] = Query(None),
    email: Optional[str] = Query(None),
    course_applied: Optional[str] = Query(None),
    academic_session: Optional[str] = Query(None),
    gender: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    sort_by: str = Query("updated", description="Sort field: name, roll_number, aadhar, created, updated"),
    sort_order: str = Query("desc", description="Sort order: asc or desc"),
    db: Session = Depends(get_db)
):
    """Export student records to PDF with filtering and sorting"""
    from fastapi.responses import StreamingResponse
    
    # Build query
    query = get_student_data_query(
        db, student_name, roll_number, aadhar_number,
        phone_number, email, course_applied, academic_session, gender, category, city, state,
        sort_by, sort_order
    )
    
    profiles = query.all()
    
    if not profiles:
        raise HTTPException(status_code=404, detail="No students found matching the criteria")
    
    # Build data list
    all_data = []
    for profile in profiles:
        data = get_student_export_data(profile, db)
        all_data.append(data)
    
    # Try to use reportlab for PDF generation
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch, cm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        
        output = io.BytesIO()
        doc = SimpleDocTemplate(output, pagesize=landscape(A4), topMargin=0.5*inch, bottomMargin=0.5*inch)
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            alignment=TA_CENTER,
            spaceAfter=20
        )
        
        elements = []
        
        # Title
        elements.append(Paragraph("SRCC Student Records Export", title_style))
        elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        elements.append(Paragraph(f"Total Records: {len(all_data)}", styles['Normal']))
        elements.append(Spacer(1, 20))
        
        # Key fields for summary table
        summary_headers = ['#', 'Student Name', 'Roll Number', 'Course', 'Category', 'Phone', 'Email']
        table_data = [summary_headers]
        
        for idx, student in enumerate(all_data, 1):
            row = [
                str(idx),
                str(student.get('Student Name', '-'))[:30],
                str(student.get('Roll Number', '-'))[:15],
                str(student.get('Course', '-'))[:20],
                str(student.get('Category', '-'))[:10],
                str(student.get('Phone Number', '-'))[:15],
                str(student.get('Email', '-'))[:25],
            ]
            table_data.append(row)
        
        # Create table
        col_widths = [0.4*inch, 2*inch, 1.2*inch, 1.5*inch, 0.8*inch, 1.2*inch, 2*inch]
        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.1, 0.23, 0.43)),  # Navy blue header
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.Color(0.95, 0.95, 0.95)]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        elements.append(table)
        
        doc.build(elements)
        output.seek(0)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"students_export_{timestamp}.pdf"
        
        return StreamingResponse(
            output,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
        
    except ImportError:
        # Fallback: return error if reportlab not installed
        raise HTTPException(
            status_code=500, 
            detail="PDF export requires reportlab library. Install with: pip install reportlab"
        )


# Field mapping for import - maps CSV/Excel column names to database fields
IMPORT_FIELD_MAPPING = {
    # Profile fields
    'student name': 'student_name',
    'roll number': 'roll_number',
    'aadhar number': 'aadhar_number',
    # Academic & Admission Details
    'academic session': 'academic_session',
    'course': 'course',
    'admission category': 'admission_category',
    'admission category other': 'admission_category_other',
    'du portal form number': 'du_portal_form_number',
    'cuet score': 'cuet_score',
    'total cuet score': 'cuet_total_score',
    'college roll no': 'college_roll_no',
    'date of admission': 'date_of_admission',
    # CUET Marks
    'cuet subject 1': 'cuet_subject_1', 'cuet total score 1': 'cuet_total_score_1', 'cuet score obtained 1': 'cuet_score_obtained_1',
    'cuet subject 2': 'cuet_subject_2', 'cuet total score 2': 'cuet_total_score_2', 'cuet score obtained 2': 'cuet_score_obtained_2',
    'cuet subject 3': 'cuet_subject_3', 'cuet total score 3': 'cuet_total_score_3', 'cuet score obtained 3': 'cuet_score_obtained_3',
    'cuet subject 4': 'cuet_subject_4', 'cuet total score 4': 'cuet_total_score_4', 'cuet score obtained 4': 'cuet_score_obtained_4',
    'cuet subject 5': 'cuet_subject_5', 'cuet total score 5': 'cuet_total_score_5', 'cuet score obtained 5': 'cuet_score_obtained_5',
    'cuet subject 6': 'cuet_subject_6', 'cuet total score 6': 'cuet_total_score_6', 'cuet score obtained 6': 'cuet_score_obtained_6',
    # Personal Details
    'first name': 'first_name', 'middle name': 'middle_name', 'surname': 'surname',
    'date of birth': 'date_of_birth', 'gender': 'gender', 'category': 'category',
    'nationality': 'nationality', 'religion': 'religion', 'blood group': 'blood_group',
    'below poverty line': 'below_poverty_line', 'minority category': 'minority_category', 'annual income': 'annual_income',
    # Address
    'permanent address line 1': 'permanent_address_line1', 'permanent address line 2': 'permanent_address_line2',
    'permanent address line 3': 'permanent_address_line3', 'permanent state': 'permanent_state',
    'permanent pincode': 'permanent_pincode', 'permanent address': 'permanent_address',
    'correspondence address line 1': 'correspondence_address_line1', 'correspondence address line 2': 'correspondence_address_line2',
    'correspondence address line 3': 'correspondence_address_line3', 'correspondence state': 'correspondence_state',
    'correspondence pincode': 'correspondence_pincode', 'correspondence address': 'correspondence_address',
    'city': 'city', 'state': 'state', 'pincode': 'pincode',
    # Contact
    'email': 'email', 'phone number': 'phone_number', 'alternate phone': 'alternate_phone',
    'emergency contact name': 'emergency_contact_name', 'emergency contact phone': 'emergency_contact_phone',
    # Mother's Details
    'mother name': 'mother_name', 'mother occupation': 'mother_occupation', 'mother designation': 'mother_designation',
    'mother organization': 'mother_organization', 'mother email': 'mother_email', 'mother mobile': 'mother_mobile',
    'mother landline code': 'mother_landline_code', 'mother landline': 'mother_landline', 'mother phone': 'mother_phone',
    # Father's Details
    'father name': 'father_name', 'father occupation': 'father_occupation', 'father designation': 'father_designation',
    'father organization': 'father_organization', 'father email': 'father_email', 'father mobile': 'father_mobile',
    'father landline code': 'father_landline_code', 'father landline': 'father_landline', 'father phone': 'father_phone',
    # Guardian's Details
    'guardian name': 'guardian_name', 'guardian relation': 'guardian_relation',
    'guardian residential address': 'guardian_residential_address', 'guardian organization': 'guardian_organization',
    'guardian email': 'guardian_email', 'guardian mobile': 'guardian_mobile',
    'guardian landline code': 'guardian_landline_code', 'guardian landline': 'guardian_landline', 'guardian phone': 'guardian_phone',
    # Qualifying Examination
    '12th year': 'twelfth_year', '12th board': 'twelfth_board', '12th roll number': 'twelfth_roll_number',
    '12th institution': 'twelfth_institution', '12th percentage': 'twelfth_percentage', '12th school': 'twelfth_school',
    'hindi studied upto': 'hindi_studied_upto', '10th board': 'tenth_board', '10th year': 'tenth_year',
    '10th percentage': 'tenth_percentage', '10th school': 'tenth_school',
    'previous qualification': 'previous_qualification', 'graduation details': 'graduation_details',
    # Other Information
    'du enrollment number': 'du_enrollment_number', 'hindi medium preference': 'hindi_medium_preference',
    # Category Certificate
    'category certificate authority': 'category_certificate_authority', 'category certificate number': 'category_certificate_number',
    'category certificate date': 'category_certificate_date', 'disability percentage': 'disability_percentage',
    'disability type': 'disability_type', 'udid number': 'udid_number',
    # Legacy
    'course applied': 'course_applied', 'application number': 'application_number',
    'enrollment number': 'enrollment_number', 'admission date': 'admission_date',
}

def normalize_field_name(field_name: str) -> str:
    """Normalize field name to lowercase and strip whitespace"""
    return field_name.lower().strip()

@router.post("/import/csv")
async def import_students_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Import student records from CSV file - requires all form fields"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV file")
    
    # Read CSV
    contents = await file.read()
    csv_data = io.StringIO(contents.decode('utf-8'))
    reader = csv.DictReader(csv_data)
    
    # Get column names and normalize them
    original_columns = reader.fieldnames or []
    normalized_columns = {normalize_field_name(col): col for col in original_columns}
    
    imported = 0
    errors = []
    
    for idx, row in enumerate(reader, start=2):  # Start at 2 (1 is header)
        try:
            # Required field: Student Name
            student_name_key = None
            for key in ['student name', 'student_name', 'name']:
                if key in normalized_columns:
                    student_name_key = normalized_columns[key]
                    break
            
            if not student_name_key or not row.get(student_name_key):
                errors.append(f"Row {idx}: Student Name is required")
                continue
            
            student_name = str(row[student_name_key]).strip()
            
            # Get aadhar_number for matching
            aadhar_key = None
            for key in ['aadhar number', 'aadhar_number', 'aadhar']:
                if key in normalized_columns:
                    aadhar_key = normalized_columns[key]
                    break
            aadhar_number = str(row.get(aadhar_key, '')).strip() if aadhar_key and row.get(aadhar_key) else None
            
            # Get or create student profile
            from backend.api.routes.students import get_or_create_student_profile
            profile = get_or_create_student_profile(db, student_name, aadhar_number=aadhar_number)
            
            # Map all CSV columns to form fields
            form_data = {}
            for norm_col, orig_col in normalized_columns.items():
                value = row.get(orig_col, '')
                if value and str(value).strip():
                    # Map normalized column name to database field
                    db_field = IMPORT_FIELD_MAPPING.get(norm_col)
                    if db_field and hasattr(AdmissionForm, db_field):
                        form_data[db_field] = str(value).strip()
            
            # Always create a form record with all available data
            form = AdmissionForm(
                filename=f"imported_{profile.id}_{idx}.csv",
                file_path="imported",
                ocr_provider="csv_import",
                status="verified",
                student_profile_id=profile.id,
                student_name=student_name,
                extracted_data={"imported_from_csv": True, "row_number": idx},
                **{k: v for k, v in form_data.items() if hasattr(AdmissionForm, k)}
            )
            db.add(form)
            db.commit()
            imported += 1
                    
        except Exception as e:
            errors.append(f"Row {idx}: {str(e)}")
            db.rollback()
    
    return {
        "message": f"Import completed",
        "imported": imported,
        "errors": errors,
        "error_count": len(errors)
    }

@router.post("/import/excel")
async def import_students_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Import student records from Excel file - requires all form fields"""
    if not (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
        raise HTTPException(status_code=400, detail="File must be an Excel file (.xlsx or .xls)")
    
    # Read Excel
    contents = await file.read()
    excel_data = io.BytesIO(contents)
    
    try:
        df = pd.read_excel(excel_data, sheet_name=0)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading Excel file: {str(e)}")
    
    # Normalize column names
    normalized_columns = {normalize_field_name(col): col for col in df.columns}
    
    imported = 0
    errors = []
    
    for idx, row in df.iterrows():
        try:
            # Required field: Student Name
            student_name_key = None
            for key in ['student name', 'student_name', 'name']:
                if key in normalized_columns:
                    student_name_key = normalized_columns[key]
                    break
            
            if not student_name_key or pd.isna(row.get(student_name_key)) or not str(row.get(student_name_key)).strip():
                errors.append(f"Row {idx + 2}: Student Name is required")  # +2 because Excel is 1-indexed and has header
                continue
            
            student_name = str(row[student_name_key]).strip()
            
            # Get aadhar_number for matching
            aadhar_key = None
            for key in ['aadhar number', 'aadhar_number', 'aadhar']:
                if key in normalized_columns:
                    aadhar_key = normalized_columns[key]
                    break
            aadhar_value = row.get(aadhar_key) if aadhar_key else None
            aadhar_number = str(aadhar_value).strip() if not pd.isna(aadhar_value) and aadhar_value else None
            
            # Get or create student profile
            from backend.api.routes.students import get_or_create_student_profile
            profile = get_or_create_student_profile(db, student_name, aadhar_number=aadhar_number)
            
            # Map all Excel columns to form fields
            form_data = {}
            for norm_col, orig_col in normalized_columns.items():
                value = row.get(orig_col)
                if not pd.isna(value) and value and str(value).strip():
                    # Map normalized column name to database field
                    db_field = IMPORT_FIELD_MAPPING.get(norm_col)
                    if db_field and hasattr(AdmissionForm, db_field):
                        form_data[db_field] = str(value).strip()
            
            # Always create a form record with all available data
            form = AdmissionForm(
                filename=f"imported_{profile.id}_{idx + 2}.xlsx",
                file_path="imported",
                ocr_provider="excel_import",
                status="verified",
                student_profile_id=profile.id,
                student_name=student_name,
                extracted_data={"imported_from_excel": True, "row_number": idx + 2},
                **{k: v for k, v in form_data.items() if hasattr(AdmissionForm, k)}
            )
            db.add(form)
            db.commit()
            imported += 1
                    
        except Exception as e:
            errors.append(f"Row {idx + 2}: {str(e)}")
            db.rollback()
    
    return {
        "message": f"Import completed",
        "imported": imported,
        "errors": errors,
        "error_count": len(errors)
    }
