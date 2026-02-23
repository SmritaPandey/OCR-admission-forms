"""
Training Manager for OCR Extraction Improvement

This module captures user corrections during form verification and uses
them to improve future OCR extractions.

Features:
1. Capture before/after values when users verify forms
2. Store correction patterns in a persistent database
3. Apply learned corrections to future extractions
4. Export training data for model fine-tuning
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


class TrainingManager:
    """
    Manages training data collection and application for OCR improvement.
    
    Corrections are stored per-field and per-pattern, allowing the system
    to learn common OCR errors and fix them automatically.
    """
    
    def __init__(self, data_dir: Optional[str] = None):
        """
        Initialize training manager.
        
        Args:
            data_dir: Directory to store training data. Defaults to project's data folder.
        """
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            self.data_dir = Path(__file__).parent.parent.parent / "data" / "training"
        
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # File paths for different training data
        self.corrections_file = self.data_dir / "corrections.json"
        self.patterns_file = self.data_dir / "patterns.json"
        self.training_samples_file = self.data_dir / "samples.jsonl"
        
        # Load existing corrections
        self.corrections = self._load_corrections()
        self.patterns = self._load_patterns()
    
    def _load_corrections(self) -> Dict[str, Dict[str, str]]:
        """Load saved corrections from file"""
        if self.corrections_file.exists():
            try:
                with open(self.corrections_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load corrections: {e}")
        return {}
    
    def _save_corrections(self):
        """Save corrections to file"""
        try:
            with open(self.corrections_file, 'w', encoding='utf-8') as f:
                json.dump(self.corrections, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save corrections: {e}")
    
    def _load_patterns(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load learned patterns from file"""
        if self.patterns_file.exists():
            try:
                with open(self.patterns_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load patterns: {e}")
        return {}
    
    def _save_patterns(self):
        """Save patterns to file"""
        try:
            with open(self.patterns_file, 'w', encoding='utf-8') as f:
                json.dump(self.patterns, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save patterns: {e}")
    
    def record_correction(self, field_name: str, original_value: str, corrected_value: str):
        """
        Record a user correction for training.
        
        Args:
            field_name: Name of the field being corrected
            original_value: OCR-extracted value
            corrected_value: User-verified correct value
        """
        if not original_value or not corrected_value:
            return
        
        if original_value.strip() == corrected_value.strip():
            return  # No correction needed
        
        # Store correction keyed by field name
        if field_name not in self.corrections:
            self.corrections[field_name] = {}
        
        original_normalized = original_value.strip().lower()
        self.corrections[field_name][original_normalized] = corrected_value.strip()
        
        # Save immediately
        self._save_corrections()
        
        logger.info(f"Recorded correction for {field_name}: '{original_value}' -> '{corrected_value}'")
    
    def record_verification(self, form_id: int, original_data: Dict[str, Any], 
                           verified_data: Dict[str, Any], raw_ocr_text: Optional[str] = None):
        """
        Record a complete form verification for training.
        
        This captures all corrections made during verification and saves
        them as a training sample.
        
        Args:
            form_id: ID of the form being verified
            original_data: Data as originally extracted by OCR
            verified_data: Data after user verification/correction
            raw_ocr_text: Optional raw OCR text for training
        """
        corrections_made = {}
        
        for field, verified_value in verified_data.items():
            if field.startswith('_'):
                continue
                
            original_value = original_data.get(field, '')
            
            if original_value and verified_value:
                if str(original_value).strip() != str(verified_value).strip():
                    # This field was corrected
                    corrections_made[field] = {
                        'original': str(original_value).strip(),
                        'corrected': str(verified_value).strip()
                    }
                    
                    # Record individual correction
                    self.record_correction(field, str(original_value), str(verified_value))
        
        # Save training sample
        if corrections_made or raw_ocr_text:
            sample = {
                'form_id': form_id,
                'timestamp': datetime.now().isoformat(),
                'corrections': corrections_made,
                'total_fields': len(verified_data),
                'fields_corrected': len(corrections_made),
                'accuracy': (len(verified_data) - len(corrections_made)) / len(verified_data) if verified_data else 0,
                'raw_ocr_text': raw_ocr_text[:5000] if raw_ocr_text else None  # Limit size
            }
            
            try:
                with open(self.training_samples_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(sample, ensure_ascii=False) + '\n')
            except Exception as e:
                logger.error(f"Failed to save training sample: {e}")
        
        logger.info(f"Recorded verification for form {form_id}: {len(corrections_made)} corrections")
    
    def apply_corrections(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply learned corrections to newly extracted data.
        
        Args:
            extracted_data: Data extracted by OCR
            
        Returns:
            Data with corrections applied
        """
        corrected = dict(extracted_data)
        
        for field, value in extracted_data.items():
            if not value or field.startswith('_'):
                continue
            
            value_normalized = str(value).strip().lower()
            
            # Check if we have a correction for this field/value combination
            if field in self.corrections:
                if value_normalized in self.corrections[field]:
                    corrected[field] = self.corrections[field][value_normalized]
                    logger.debug(f"Applied learned correction for {field}: '{value}' -> '{corrected[field]}'")
        
        return corrected
    
    def get_field_accuracy(self) -> Dict[str, float]:
        """
        Calculate per-field accuracy based on training data.
        
        Returns:
            Dictionary mapping field names to accuracy percentages
        """
        field_stats = defaultdict(lambda: {'correct': 0, 'total': 0})
        
        if not self.training_samples_file.exists():
            return {}
        
        try:
            with open(self.training_samples_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    sample = json.loads(line)
                    corrections = sample.get('corrections', {})
                    
                    for field in corrections:
                        field_stats[field]['total'] += 1
                    
                    # Estimate total fields from sample
                    total = sample.get('total_fields', 0)
                    corrected = sample.get('fields_corrected', 0)
                    if total > 0:
                        # Distribute "correct" fields proportionally
                        correct_count = total - corrected
                        if correct_count > 0:
                            # We don't know which specific fields were correct,
                            # so we just track the ones that needed correction
                            pass
        except Exception as e:
            logger.error(f"Failed to calculate field accuracy: {e}")
        
        # Calculate accuracy per field
        accuracy = {}
        for field, stats in field_stats.items():
            if stats['total'] > 0:
                # Lower correction rate = higher accuracy
                # This is an inverse metric: more corrections = less accurate
                accuracy[field] = 100 - (stats['total'] / max(stats['total'] + 10, 1) * 100)
        
        return accuracy
    
    def export_training_data(self) -> List[Dict[str, Any]]:
        """
        Export all training samples for external training.
        
        Returns:
            List of training samples with OCR text and corrections
        """
        samples = []
        
        if not self.training_samples_file.exists():
            return samples
        
        try:
            with open(self.training_samples_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        samples.append(json.loads(line))
        except Exception as e:
            logger.error(f"Failed to export training data: {e}")
        
        return samples
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get training statistics.
        
        Returns:
            Dictionary with training stats
        """
        total_samples = 0
        total_corrections = 0
        
        if self.training_samples_file.exists():
            try:
                with open(self.training_samples_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            sample = json.loads(line)
                            total_samples += 1
                            total_corrections += len(sample.get('corrections', {}))
            except Exception:
                pass
        
        return {
            'total_samples': total_samples,
            'total_corrections': total_corrections,
            'correction_patterns': len(self.corrections),
            'fields_with_corrections': list(self.corrections.keys())
        }


# Create global instance
training_manager = TrainingManager()
