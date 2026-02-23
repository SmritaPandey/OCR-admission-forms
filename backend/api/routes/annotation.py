"""
Annotation API Routes
Handle form field annotation for training data collection
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from backend.database import get_db, AdmissionForm
from backend.models.form import FormDetailResponse
from backend.api.dependencies import RequireStaffOrAdmin
from backend.models.auth_models import CurrentUser
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

class AnnotationField(BaseModel):
    """Field annotation model"""
    field_name: str
    value: str
    bounding_box: Optional[Dict[str, float]] = None  # x, y, width, height
    page_number: Optional[int] = None
    confidence: Optional[float] = None

class AnnotationCheckbox(BaseModel):
    """Checkbox annotation model"""
    label: str
    checked: bool
    bounding_box: Optional[Dict[str, float]] = None
    page_number: Optional[int] = None

class FormAnnotation(BaseModel):
    """Complete form annotation"""
    form_id: int
    fields: List[AnnotationField]
    checkboxes: List[AnnotationCheckbox] = []
    notes: Optional[str] = None

@router.post("/annotate/{form_id}", status_code=201)
async def save_annotation(
    form_id: int,
    annotation: FormAnnotation = Body(...),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(RequireStaffOrAdmin),
):
    """
    Save annotation for a form with key-value pairs and checkbox states.
    
    Supports:
    - Field annotations with bounding boxes
    - Checkbox annotations with checked/unchecked states
    - Key-value extraction for training
    """
    form = db.query(AdmissionForm).filter(AdmissionForm.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    
    # Store annotation in form's additional_info
    if form.additional_info is None:
        form.additional_info = {}
    
    # Create key-value mapping for training
    key_value_pairs = {}
    for field in annotation.fields:
        key_value_pairs[field.field_name] = field.value
    
    form.additional_info['annotation'] = {
        'fields': [f.dict() for f in annotation.fields],
        'checkboxes': [cb.dict() for cb in annotation.checkboxes],
        'key_value_pairs': key_value_pairs,  # Added for easier training data access
        'notes': annotation.notes,
        'annotated_at': datetime.utcnow().isoformat(),
        'annotated_by': 'api'  # Could be extended with user authentication
    }
    
    # Update form status to indicate it's been annotated
    # (Optional: you might want to keep this separate from verification)
    
    db.commit()
    db.refresh(form)
    
    return {
        "form_id": form_id,
        "status": "saved",
        "fields_annotated": len(annotation.fields),
        "checkboxes_annotated": len(annotation.checkboxes),
        "key_value_pairs": len(key_value_pairs),
        "message": f"Annotation saved successfully. {len(key_value_pairs)} key-value pairs extracted."
    }

@router.get("/annotate/{form_id}")
async def get_annotation(
    form_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(RequireStaffOrAdmin),
):
    """Get annotation for a form"""
    form = db.query(AdmissionForm).filter(AdmissionForm.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    
    annotation = form.additional_info.get('annotation') if form.additional_info else None
    
    if not annotation:
        return {
            "form_id": form_id,
            "annotated": False
        }
    
    return {
        "form_id": form_id,
        "annotated": True,
        "annotation": annotation
    }

@router.get("/export/training-data")
async def export_training_data(
    format: str = Query("json", pattern="^(json|coco|yolo)$"),
    include_extracted_data: bool = Query(True),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(RequireStaffOrAdmin),
):
    """Export annotated forms as training data"""
    from backend.utils.training_data_manager import TrainingDataManager
    
    # Get all annotated forms
    forms = db.query(AdmissionForm).filter(
        AdmissionForm.additional_info.isnot(None)
    ).all()
    
    annotated_forms = []
    for form in forms:
        if form.additional_info and 'annotation' in form.additional_info:
            form_data = {
                'form_id': form.id,
                'file_path': form.file_path,
                'filename': form.filename,
                'annotation': form.additional_info['annotation']
            }
            
            # Include extracted data if requested (useful for training)
            if include_extracted_data and form.extracted_data:
                form_data['extracted_data'] = form.extracted_data
                form_data['ocr_text'] = form.raw_text
            
            annotated_forms.append(form_data)
    
    if format == "json":
        manager = TrainingDataManager()
        export_file = manager.export_to_json(annotated_forms)
        
        return {
            "format": "json",
            "total_annotations": len(annotated_forms),
            "export_file": str(export_file),
            "data": annotated_forms[:10],  # Return first 10 as preview
            "message": f"Full export saved to {export_file}"
        }
    elif format == "coco":
        # Convert to COCO format for object detection
        coco_data = convert_to_coco_format(annotated_forms)
        return {
            "format": "coco",
            "total_annotations": len(annotated_forms),
            "coco_format": coco_data,
            "message": "COCO format for object detection models"
        }
    elif format == "yolo":
        # Convert to YOLO format
        yolo_data = convert_to_yolo_format(annotated_forms)
        return {
            "format": "yolo",
            "total_annotations": len(annotated_forms),
            "yolo_format": yolo_data,
            "message": "YOLO format for object detection"
        }
    
    raise HTTPException(status_code=400, detail="Invalid format")


def convert_to_coco_format(annotated_forms: List[Dict]) -> Dict:
    """Convert annotations to COCO format for object detection"""
    coco = {
        "info": {
            "description": "Student Admission Form Training Data",
            "version": "1.0",
            "year": datetime.now().year
        },
        "licenses": [],
        "images": [],
        "annotations": [],
        "categories": [
            {"id": 1, "name": "field", "supercategory": "form_element"},
            {"id": 2, "name": "checkbox", "supercategory": "form_element"}
        ]
    }
    
    image_id = 1
    annotation_id = 1
    
    for form_data in annotated_forms:
        annotation = form_data.get('annotation', {})
        file_path = form_data.get('file_path', '')
        
        # Add image (would need to load image to get dimensions)
        coco["images"].append({
            "id": image_id,
            "file_name": file_path,
            "width": 0,  # Would need to load image
            "height": 0
        })
        
        # Add field annotations
        for field in annotation.get('fields', []):
            bbox = field.get('bounding_box', {})
            if bbox:
                coco["annotations"].append({
                    "id": annotation_id,
                    "image_id": image_id,
                    "category_id": 1,
                    "bbox": [bbox.get('x', 0), bbox.get('y', 0), bbox.get('width', 0), bbox.get('height', 0)],
                    "area": bbox.get('width', 0) * bbox.get('height', 0),
                    "iscrowd": 0,
                    "attributes": {
                        "field_name": field.get('field_name'),
                        "value": field.get('value')
                    }
                })
                annotation_id += 1
        
        # Add checkbox annotations
        for checkbox in annotation.get('checkboxes', []):
            bbox = checkbox.get('bounding_box', {})
            if bbox:
                coco["annotations"].append({
                    "id": annotation_id,
                    "image_id": image_id,
                    "category_id": 2,
                    "bbox": [bbox.get('x', 0), bbox.get('y', 0), bbox.get('width', 0), bbox.get('height', 0)],
                    "area": bbox.get('width', 0) * bbox.get('height', 0),
                    "iscrowd": 0,
                    "attributes": {
                        "label": checkbox.get('label'),
                        "checked": checkbox.get('checked')
                    }
                })
                annotation_id += 1
        
        image_id += 1
    
    return coco


def convert_to_yolo_format(annotated_forms: List[Dict]) -> List[Dict]:
    """Convert annotations to YOLO format"""
    yolo_data = []
    
    for form_data in annotated_forms:
        annotation = form_data.get('annotation', {})
        file_path = form_data.get('file_path', '')
        
        yolo_annotations = {
            "image_path": file_path,
            "annotations": []
        }
        
        # Add field annotations (class 0)
        for field in annotation.get('fields', []):
            bbox = field.get('bounding_box', {})
            if bbox:
                # YOLO format: class_id center_x center_y width height (normalized 0-1)
                # Would need image dimensions for normalization
                yolo_annotations["annotations"].append({
                    "class": 0,  # field
                    "bbox": bbox,
                    "field_name": field.get('field_name'),
                    "value": field.get('value')
                })
        
        # Add checkbox annotations (class 1)
        for checkbox in annotation.get('checkboxes', []):
            bbox = checkbox.get('bounding_box', {})
            if bbox:
                yolo_annotations["annotations"].append({
                    "class": 1,  # checkbox
                    "bbox": bbox,
                    "label": checkbox.get('label'),
                    "checked": checkbox.get('checked')
                })
        
        yolo_data.append(yolo_annotations)
    
    return yolo_data

