"""
Continuous Improvement System
Automatically retrains models based on user corrections
Inspired by Azure Intelligent Form Labeling's continuous learning
"""
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from backend.database import AdmissionForm
from backend.config import settings
from backend.training.prepare_data import TrainingDataPreparator
from backend.training.train_craft_trocr import train_craft_trocr


class ContinuousImprovementManager:
    """
    Manages continuous model improvement based on user corrections
    
    Features:
    - Tracks corrections made to forms
    - Automatically creates training data from corrections
    - Triggers retraining when enough new data is available
    - Maintains model version history
    """
    
    def __init__(self, upload_dir: Optional[str] = None):
        if upload_dir is None:
            upload_dir = settings.UPLOAD_DIR
        self.upload_dir = Path(upload_dir)
        self.models_dir = self.upload_dir / "models"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        self.improvement_log_path = self.models_dir / "improvement_log.json"
        self.improvement_log = self._load_improvement_log()
    
    def _load_improvement_log(self) -> Dict[str, Any]:
        """Load improvement log"""
        if self.improvement_log_path.exists():
            with open(self.improvement_log_path, 'r') as f:
                return json.load(f)
        return {
            "last_training": None,
            "corrections_since_training": 0,
            "model_versions": [],
            "pending_corrections": []
        }
    
    def _save_improvement_log(self):
        """Save improvement log"""
        with open(self.improvement_log_path, 'w') as f:
            json.dump(self.improvement_log, f, indent=2)
    
    def record_correction(
        self,
        form_id: int,
        field_name: str,
        original_value: str,
        corrected_value: str,
        confidence: Optional[float] = None
    ):
        """
        Record a correction made by user
        
        Args:
            form_id: Form ID
            field_name: Name of corrected field
            original_value: Original OCR value
            corrected_value: User-corrected value
            confidence: OCR confidence (if available)
        """
        correction = {
            "form_id": form_id,
            "field_name": field_name,
            "original_value": original_value,
            "corrected_value": corrected_value,
            "confidence": confidence,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.improvement_log["pending_corrections"].append(correction)
        self.improvement_log["corrections_since_training"] += 1
        self._save_improvement_log()
    
    def get_corrections_since_training(self) -> int:
        """Get number of corrections since last training"""
        return self.improvement_log["corrections_since_training"]
    
    def should_retrain(
        self,
        min_corrections: int = 50,
        min_days_since_training: int = 7
    ) -> bool:
        """
        Check if model should be retrained
        
        Args:
            min_corrections: Minimum corrections needed
            min_days_since_training: Minimum days since last training
        
        Returns:
            True if retraining should be triggered
        """
        corrections = self.get_corrections_since_training()
        
        if corrections < min_corrections:
            return False
        
        last_training = self.improvement_log.get("last_training")
        if not last_training:
            return True  # Never trained, should train
        
        last_training_date = datetime.fromisoformat(last_training)
        days_since = (datetime.utcnow() - last_training_date).days
        
        return days_since >= min_days_since_training
    
    def prepare_training_data_from_corrections(
        self,
        db: Session,
        output_dir: Optional[str] = None
    ) -> Optional[Path]:
        """
        Prepare training data from pending corrections
        
        Returns:
            Path to prepared training data JSON, or None if no data
        """
        corrections = self.improvement_log.get("pending_corrections", [])
        
        if not corrections:
            return None
        
        # Get forms with corrections
        form_ids = list(set(c["form_id"] for c in corrections))
        forms = db.query(AdmissionForm).filter(AdmissionForm.id.in_(form_ids)).all()
        
        # Create annotated forms structure
        annotated_forms = []
        for form in forms:
            form_corrections = [c for c in corrections if c["form_id"] == form.id]
            
            # Create annotation from corrections
            fields = []
            for correction in form_corrections:
                fields.append({
                    "field_name": correction["field_name"],
                    "value": correction["corrected_value"],  # Use corrected value
                    "confidence": correction.get("confidence", 0.9),
                    "page_number": 1,
                    "from_correction": True,
                    "original_value": correction["original_value"]
                })
            
            if fields:
                annotated_forms.append({
                    "form_id": form.id,
                    "file_path": form.file_path,
                    "annotation": {
                        "fields": fields,
                        "checkboxes": [],
                        "from_corrections": True,
                        "created_at": datetime.utcnow().isoformat()
                    }
                })
        
        if not annotated_forms:
            return None
        
        # Prepare training data
        preparator = TrainingDataPreparator()
        if output_dir:
            preparator.training_dir = Path(output_dir)
            preparator.training_dir.mkdir(parents=True, exist_ok=True)
        
        # Extract images and prepare dataset
        training_samples = preparator.extract_images_from_forms(annotated_forms)
        if not training_samples:
            return None
        
        # Prepare TrOCR dataset
        dataset_path = preparator.prepare_trocr_dataset(training_samples)
        
        return dataset_path
    
    def trigger_retraining(
        self,
        db: Session,
        base_model: Optional[str] = None,
        epochs: int = 5,  # Fewer epochs for incremental training
        batch_size: int = 8,
        learning_rate: float = 3e-5  # Lower LR for fine-tuning
    ) -> Dict[str, Any]:
        """
        Trigger model retraining with corrections
        
        Returns:
            Dictionary with training results
        """
        if not self.should_retrain():
            return {
                "status": "skipped",
                "reason": "Not enough corrections or too soon since last training",
                "corrections": self.get_corrections_since_training()
            }
        
        # Prepare training data
        training_data_path = self.prepare_training_data_from_corrections(db)
        if not training_data_path:
            return {
                "status": "error",
                "reason": "No training data prepared from corrections"
            }
        
        # Determine model paths
        if base_model is None:
            # Use existing custom model if available, otherwise base
            custom_model_path = getattr(settings, 'TROCR_CUSTOM_MODEL_PATH', None)
            if custom_model_path and os.path.exists(custom_model_path):
                base_model = custom_model_path
            else:
                base_model = "microsoft/trocr-base-handwritten"
        
        # Create new model version
        version = len(self.improvement_log["model_versions"]) + 1
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        output_model_path = self.models_dir / f"trocr_v{version}_{timestamp}"
        
        try:
            # Train model
            train_craft_trocr(
                training_data_path=str(training_data_path),
                output_model_path=str(output_model_path),
                epochs=epochs,
                batch_size=batch_size,
                learning_rate=learning_rate,
                base_model=base_model,
                resume_from_checkpoint=base_model if base_model != "microsoft/trocr-base-handwritten" else None
            )
            
            # Update log
            model_info = {
                "version": version,
                "path": str(output_model_path),
                "trained_at": datetime.utcnow().isoformat(),
                "corrections_used": len(self.improvement_log["pending_corrections"]),
                "base_model": base_model
            }
            
            self.improvement_log["model_versions"].append(model_info)
            self.improvement_log["last_training"] = datetime.utcnow().isoformat()
            self.improvement_log["corrections_since_training"] = 0
            self.improvement_log["pending_corrections"] = []  # Clear after training
            self._save_improvement_log()
            
            return {
                "status": "success",
                "model_path": str(output_model_path),
                "version": version,
                "corrections_used": model_info["corrections_used"]
            }
        
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_improvement_stats(self) -> Dict[str, Any]:
        """Get statistics about model improvement"""
        return {
            "corrections_since_training": self.get_corrections_since_training(),
            "last_training": self.improvement_log.get("last_training"),
            "total_models": len(self.improvement_log.get("model_versions", [])),
            "pending_corrections": len(self.improvement_log.get("pending_corrections", [])),
            "should_retrain": self.should_retrain()
        }
