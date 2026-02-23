"""
Training Workflow API Routes
Complete training pipeline for OCR models on admission forms
"""
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks, Body
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from pathlib import Path
import json
import os

from backend.database import get_db, AdmissionForm
from backend.utils.training_data_manager import TrainingDataManager
from backend.training.prepare_data import TrainingDataPreparator
from backend.api.dependencies import RequireAdmin
from backend.models.auth_models import CurrentUser

router = APIRouter()


class BulkAnnotationRequest(BaseModel):
    """Bulk annotation for multiple forms"""
    form_ids: List[int]
    annotation_template: Dict[str, Any]  # Template with field mappings
    auto_label: bool = False  # Try to auto-label using OCR results


class TrainingConfig(BaseModel):
    """Configuration for model training"""
    model_type: str = Field(default="trocr", pattern="^(trocr|donut)$")
    base_model: Optional[str] = None
    epochs: int = Field(default=10, ge=1, le=100)
    batch_size: int = Field(default=8, ge=1, le=32)
    learning_rate: float = Field(default=5e-5, ge=1e-6, le=1e-2)
    train_ratio: float = Field(default=0.8, ge=0.5, le=0.95)
    val_ratio: float = Field(default=0.1, ge=0.05, le=0.3)
    test_ratio: float = Field(default=0.1, ge=0.05, le=0.3)
    output_model_dir: Optional[str] = None
    use_checkpoint: bool = True


class TrainingJob(BaseModel):
    """Training job information"""
    job_id: str
    status: str
    model_type: str
    config: Dict[str, Any]
    created_at: str
    progress: Optional[Dict[str, Any]] = None


@router.get("/training/stats")
async def get_training_stats(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(RequireAdmin),
):
    """Get statistics about available training data"""
    # Get all annotated forms
    forms = db.query(AdmissionForm).filter(
        AdmissionForm.additional_info.isnot(None)
    ).all()
    
    annotated_forms = []
    for form in forms:
        if form.additional_info and 'annotation' in form.additional_info:
            annotated_forms.append({
                'form_id': form.id,
                'file_path': form.file_path,
                'annotation': form.additional_info['annotation']
            })
    
    manager = TrainingDataManager()
    stats = manager.export_stats(annotated_forms)
    
    # Additional stats
    total_forms = db.query(AdmissionForm).count()
    unannotated_forms = total_forms - stats['total_forms']
    
    return {
        "total_forms": total_forms,
        "annotated_forms": stats['total_forms'],
        "unannotated_forms": unannotated_forms,
        "annotation_percentage": (stats['total_forms'] / total_forms * 100) if total_forms > 0 else 0,
        "total_fields": stats['total_fields'],
        "total_checkboxes": stats['total_checkboxes'],
        "field_types": stats['field_types'],
        "checkbox_labels": stats['checkbox_labels'],
        "forms_with_all_fields": stats['forms_with_all_fields'],
        "forms_with_checkboxes": stats['forms_with_checkboxes']
    }


@router.post("/training/prepare-data")
async def prepare_training_data(
    format: str = Query("both", pattern="^(trocr|donut|both)$"),
    split: bool = Query(True),
    output_dir: Optional[str] = Query(None),
    use_images: bool = Query(True),  # Use converted images if available
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(RequireAdmin),
):
    """Prepare training data from annotated forms or converted images"""
    project_root = Path(__file__).parent.parent.parent.parent
    images_training_data = project_root / "training_data" / "student_forms.json"
    
    # Check if we have training data from images
    if use_images and images_training_data.exists():
        import json
        with open(images_training_data, 'r') as f:
            data = json.load(f)
        if data:
            return {
                "samples_extracted": len(data),
                "output_dir": str(images_training_data.parent),
                "datasets": {
                    "trocr": {
                        "path": str(images_training_data),
                        "samples": len(data)
                    }
                },
                "source": "converted_images"
            }
    
    # Fallback to annotated forms
    forms = db.query(AdmissionForm).filter(
        AdmissionForm.additional_info.isnot(None)
    ).all()
    
    if not forms:
        raise HTTPException(
            status_code=400, 
            detail="No annotated forms found. Using converted images instead. Run image conversion first."
        )
    
    annotated_forms = []
    for form in forms:
        if form.additional_info and 'annotation' in form.additional_info:
            annotated_forms.append({
                'form_id': form.id,
                'file_path': form.file_path,
                'annotation': form.additional_info['annotation']
            })
    
    if not annotated_forms:
        raise HTTPException(status_code=400, detail="No valid annotations found.")
    
    # Initialize preparator
    preparator = TrainingDataPreparator()
    if output_dir:
        preparator.training_dir = Path(output_dir)
        preparator.training_dir.mkdir(parents=True, exist_ok=True)
    
    # Extract images
    try:
        training_samples = preparator.extract_images_from_forms(annotated_forms)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting images: {str(e)}")
    
    results = {
        "samples_extracted": len(training_samples),
        "output_dir": str(preparator.training_dir),
        "datasets": {}
    }
    
    # Prepare datasets
    if format in ["trocr", "both"]:
        try:
            trocr_path = preparator.prepare_trocr_dataset(training_samples)
            results["datasets"]["trocr"] = {
                "path": str(trocr_path),
                "samples": len(training_samples)
            }
            
            if split:
                train_path, val_path, test_path = preparator.split_dataset(str(trocr_path))
                results["datasets"]["trocr"]["splits"] = {
                    "train": str(train_path),
                    "val": str(val_path),
                    "test": str(test_path)
                }
        except Exception as e:
            results["datasets"]["trocr"] = {"error": str(e)}
    
    if format in ["donut", "both"]:
        try:
            donut_path = preparator.prepare_donut_dataset(training_samples)
            results["datasets"]["donut"] = {
                "path": str(donut_path),
                "samples": len(training_samples)
            }
            
            if split:
                train_path, val_path, test_path = preparator.split_dataset(str(donut_path))
                results["datasets"]["donut"]["splits"] = {
                    "train": str(train_path),
                    "val": str(val_path),
                    "test": str(test_path)
                }
        except Exception as e:
            results["datasets"]["donut"] = {"error": str(e)}
    
    return results


@router.post("/training/export-annotations")
async def export_training_annotations(
    format: str = Query("json", pattern="^(json|coco|yolo|trocr|donut)$"),
    include_images: bool = Query(False),
    output_dir: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(RequireAdmin),
):
    """Export annotations in various training formats"""
    from backend.api.routes.annotation import export_training_data
    
    # Get annotations
    forms = db.query(AdmissionForm).filter(
        AdmissionForm.additional_info.isnot(None)
    ).all()
    
    annotated_forms = []
    for form in forms:
        if form.additional_info and 'annotation' in form.additional_info:
            annotated_forms.append({
                'form_id': form.id,
                'file_path': form.file_path,
                'annotation': form.additional_info['annotation']
            })
    
    if not annotated_forms:
        raise HTTPException(status_code=400, detail="No annotated forms found")
    
    manager = TrainingDataManager()
    if output_dir:
        manager.output_dir = Path(output_dir)
        manager.output_dir.mkdir(parents=True, exist_ok=True)
    
    results = {}
    
    if format in ["json", "trocr", "donut"]:
        # Export to JSON
        json_file = manager.export_to_json(annotated_forms)
        results["json_export"] = str(json_file)
        
        if format in ["trocr", "donut"] or include_images:
            # Prepare training data with images
            preparator = TrainingDataPreparator()
            if output_dir:
                preparator.training_dir = Path(output_dir)
                preparator.training_dir.mkdir(parents=True, exist_ok=True)
            
            training_samples = preparator.extract_images_from_forms(annotated_forms)
            
            if format == "trocr" or format == "json":
                trocr_path = preparator.prepare_trocr_dataset(training_samples)
                results["trocr_dataset"] = str(trocr_path)
            
            if format == "donut" or format == "json":
                donut_path = preparator.prepare_donut_dataset(training_samples)
                results["donut_dataset"] = str(donut_path)
    
    elif format == "coco":
        # COCO format export (for object detection models)
        results["message"] = "COCO format export - Implement using cv2 or similar"
        results["status"] = "pending"
    
    elif format == "yolo":
        # YOLO format export (for object detection)
        results["message"] = "YOLO format export - Implement using YOLO annotation format"
        results["status"] = "pending"
    
    return {
        "format": format,
        "total_annotations": len(annotated_forms),
        "exports": results
    }


@router.post("/training/start")
async def start_training(
    config: TrainingConfig = Body(...),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(RequireAdmin),
):
    """Start training a model with prepared data"""
    import uuid
    from backend.training.train_trocr import main as train_trocr
    from backend.training.train_donut import main as train_donut
    
    # Check if training data exists
    preparator = TrainingDataPreparator()
    training_dir = preparator.training_dir
    
    # Determine dataset path based on model type
    # Check for training data in multiple locations
    project_root = Path(__file__).parent.parent.parent.parent
    possible_paths = [
        training_dir / "train.json",
        project_root / "training_data" / "student_forms.json",
        project_root / "training_data" / "images_training_data.json"
    ]
    
    train_data_path = None
    for path in possible_paths:
        if path.exists():
            train_data_path = path
            break
    
    if not train_data_path:
        raise HTTPException(
            status_code=400,
            detail=f"Training data not found. Checked: {[str(p) for p in possible_paths]}. Run /training/prepare-data first or ensure training_data/student_forms.json exists."
        )
    
    if config.model_type == "trocr":
        base_model = config.base_model or "microsoft/trocr-base-handwritten"
    elif config.model_type == "donut":
        base_model = config.base_model or "naver-clova-ix/donut-base"
    else:
        raise HTTPException(status_code=400, detail=f"Unknown model type: {config.model_type}")
    
    # Create output directory
    if config.output_model_dir is None:
        from backend.config import settings
        output_dir = Path(settings.UPLOAD_DIR) / "models" / f"{config.model_type}_finetuned_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    else:
        output_dir = Path(config.output_model_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create job ID
    job_id = str(uuid.uuid4())
    
    # Store job info (in production, use Redis or database)
    job_info = {
        "job_id": job_id,
        "status": "queued",
        "model_type": config.model_type,
        "config": config.dict(),
        "created_at": datetime.utcnow().isoformat(),
        "output_dir": str(output_dir)
    }
    
    # Run training in background
    if background_tasks:
        async def run_training():
            try:
                from backend.training.train_craft_trocr import train_craft_trocr
                # Update job status to running
                job_info["status"] = "running"
                
                # Run training
                if config.model_type == "trocr":
                    from backend.training.train_craft_trocr import train_craft_trocr
                    train_craft_trocr(
                        training_data_path=str(train_data_path),
                        output_model_path=str(output_dir),
                        epochs=config.epochs,
                        batch_size=config.batch_size,
                        learning_rate=config.learning_rate,
                        base_model=base_model,
                        image_dir=str(project_root)
                    )
                    job_info["status"] = "completed"
                else:
                    job_info["status"] = "error"
                    job_info["error"] = f"Model type {config.model_type} training not yet implemented"
            except Exception as e:
                job_info["status"] = "error"
                job_info["error"] = str(e)
        
        background_tasks.add_task(run_training)
    
    return {
        "job_id": job_id,
        "status": "queued",
        "message": "Training job started. Training runs in background.",
        "config": config.dict(),
        "output_dir": str(output_dir)
    }


@router.get("/training/job/{job_id}")
async def get_training_job_status(job_id: str, user: CurrentUser = Depends(RequireAdmin)):
    """Get training job status"""
    # TODO: Implement job tracking (Redis, database, etc.)
    return {
        "job_id": job_id,
        "status": "not_implemented",
        "message": "Job tracking not yet implemented"
    }


@router.get("/training/forms/unannotated")
async def get_unannotated_forms(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(RequireAdmin),
):
    """Get list of forms that need annotation"""
    # Get all forms
    all_forms = db.query(AdmissionForm).order_by(AdmissionForm.upload_date.desc()).offset(offset).limit(limit).all()
    
    unannotated = []
    for form in all_forms:
        if not form.additional_info or 'annotation' not in form.additional_info:
            unannotated.append({
                "id": form.id,
                "filename": form.filename,
                "upload_date": form.upload_date.isoformat() if form.upload_date else None,
                "status": form.status.value if form.status else None,
                "student_name": form.student_name
            })
    
    return {
        "total": len(unannotated),
        "forms": unannotated
    }


@router.post("/training/bulk-annotate")
async def bulk_annotate_forms(
    form_ids: List[int] = Body(..., embed=True),
    annotation_template: Optional[Dict[str, Any]] = Body(None),
    auto_label: bool = Body(False),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(RequireAdmin),
):
    """
    Bulk annotate multiple forms
    
    If auto_label=True, will try to extract labels from OCR results.
    If annotation_template is provided, will use it to map fields.
    """
    forms = db.query(AdmissionForm).filter(AdmissionForm.id.in_(form_ids)).all()
    
    if len(forms) != len(form_ids):
        raise HTTPException(status_code=404, detail="Some forms not found")
    
    annotated_count = 0
    errors = []
    
    for form in forms:
        try:
            if auto_label and form.extracted_data:
                # Auto-create annotation from extracted_data
                annotation = {
                    'fields': [],
                    'checkboxes': [],
                    'auto_generated': True,
                    'annotated_at': datetime.utcnow().isoformat()
                }
                
                # Extract fields from extracted_data
                if isinstance(form.extracted_data, dict):
                    for key, value in form.extracted_data.items():
                        if value and isinstance(value, str):
                            annotation['fields'].append({
                                'field_name': key,
                                'value': value,
                                'confidence': 0.9,
                                'auto_extracted': True
                            })
                
                # Store annotation
                if form.additional_info is None:
                    form.additional_info = {}
                form.additional_info['annotation'] = annotation
                annotated_count += 1
                
        except Exception as e:
            errors.append({"form_id": form.id, "error": str(e)})
    
    db.commit()
    
    return {
        "total_forms": len(form_ids),
        "annotated": annotated_count,
        "errors": errors,
        "message": f"Successfully annotated {annotated_count} forms"
    }
