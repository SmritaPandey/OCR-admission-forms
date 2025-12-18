"""
Auto-Labeling API Routes
Automatically extract key-value pairs and checkbox states from OCR results
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from backend.database import get_db, AdmissionForm
from backend.utils.ai_form_parser import AIFormParser
from backend.utils.ai_checkbox_detector import AICheckboxDetector
from backend.api.routes.annotation import AnnotationField, AnnotationCheckbox, FormAnnotation

router = APIRouter()


class AutoLabelResponse(BaseModel):
    """Response from auto-labeling"""
    form_id: int
    fields_extracted: List[AnnotationField]
    checkboxes_extracted: List[AnnotationCheckbox]
    confidence: float
    method: str


@router.post("/auto-label/{form_id}")
async def auto_label_form(
    form_id: int,
    use_ocr_text: bool = Query(True),
    use_structured_data: bool = Query(True),
    save_annotation: bool = Query(False),
    db: Session = Depends(get_db)
):
    """
    Automatically extract labels (key-value pairs) from form OCR results.
    
    This is useful for quickly generating training data from existing OCR results.
    """
    form = db.query(AdmissionForm).filter(AdmissionForm.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    
    extracted_fields = []
    extracted_checkboxes = []
    
    # Extract fields from structured data if available
    if use_structured_data and form.extracted_data:
        parser = AIFormParser()
        
        # Convert extracted_data to annotation fields
        if isinstance(form.extracted_data, dict):
            for key, value in form.extracted_data.items():
                if value and isinstance(value, str) and value.strip():
                    extracted_fields.append(AnnotationField(
                        field_name=key,
                        value=str(value).strip(),
                        confidence=0.85,  # Default confidence
                        page_number=1
                    ))
    
    # Extract checkboxes using AI checkbox detector
    if form.raw_text or form.extracted_data:
        detector = AICheckboxDetector()
        
        # Create a mock OCR result for checkbox detection
        ocr_result = {
            "raw_text": form.raw_text or "",
            "structured_data": form.extracted_data or {}
        }
        
        checkboxes = detector.extract_checkboxes_from_ai_result(ocr_result)
        
        for cb in checkboxes:
            extracted_checkboxes.append(AnnotationCheckbox(
                label=cb.get('label', ''),
                checked=cb.get('checked', False),
                page_number=1
            ))
    
    # If save_annotation is True, save the annotation
    if save_annotation:
        from datetime import datetime
        
        # Save annotation directly to database
        if form.additional_info is None:
            form.additional_info = {}
        
        key_value_pairs = {f.field_name: f.value for f in extracted_fields}
        
        form.additional_info['annotation'] = {
            'fields': [f.dict() for f in extracted_fields],
            'checkboxes': [cb.dict() for cb in extracted_checkboxes],
            'key_value_pairs': key_value_pairs,
            'notes': "Auto-labeled from OCR results",
            'annotated_at': datetime.utcnow().isoformat(),
            'annotated_by': 'auto-label-api'
        }
        
        db.commit()
        db.refresh(form)
        
        return {
            "form_id": form_id,
            "fields_extracted": [f.dict() for f in extracted_fields],
            "checkboxes_extracted": [cb.dict() for cb in extracted_checkboxes],
            "saved": True,
            "fields_annotated": len(extracted_fields),
            "checkboxes_annotated": len(extracted_checkboxes)
        }
    
    return {
        "form_id": form_id,
        "fields_extracted": [f.dict() for f in extracted_fields],
        "checkboxes_extracted": [cb.dict() for cb in extracted_checkboxes],
        "total_fields": len(extracted_fields),
        "total_checkboxes": len(extracted_checkboxes),
        "saved": False,
        "message": "Set save_annotation=true to save these labels"
    }


@router.post("/auto-label/bulk")
async def bulk_auto_label(
    form_ids: List[int],
    save_annotations: bool = Query(False),
    db: Session = Depends(get_db)
):
    """Auto-label multiple forms at once"""
    forms = db.query(AdmissionForm).filter(AdmissionForm.id.in_(form_ids)).all()
    
    if len(forms) != len(form_ids):
        raise HTTPException(status_code=404, detail="Some forms not found")
    
    results = []
    total_fields = 0
    total_checkboxes = 0
    
    for form in forms:
        try:
            result = await auto_label_form(
                form.id,
                use_ocr_text=True,
                use_structured_data=True,
                save_annotation=save_annotations,
                db=db
            )
            results.append(result)
            total_fields += result.get('total_fields', 0)
            total_checkboxes += result.get('total_checkboxes', 0)
        except Exception as e:
            results.append({
                "form_id": form.id,
                "error": str(e)
            })
    
    return {
        "total_forms": len(form_ids),
        "processed": len([r for r in results if 'error' not in r]),
        "failed": len([r for r in results if 'error' in r]),
        "total_fields_extracted": total_fields,
        "total_checkboxes_extracted": total_checkboxes,
        "results": results
    }


@router.get("/auto-label/preview/{form_id}")
async def preview_auto_label(
    form_id: int,
    db: Session = Depends(get_db)
):
    """Preview what would be extracted without saving"""
    return await auto_label_form(form_id, save_annotation=False, db=db)
