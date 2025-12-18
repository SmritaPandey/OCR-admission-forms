"""
Training Data Manager
Collect and organize labeled forms for model training
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import json
import os
from backend.config import settings

class TrainingDataManager:
    """Manage training data collection and export"""
    
    def __init__(self, output_dir: Optional[str] = None):
        if output_dir is None:
            output_dir = os.path.join(settings.UPLOAD_DIR, "training_data")
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def organize_annotations(
        self,
        annotated_forms: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Organize annotations by category"""
        organized = {
            'total_forms': len(annotated_forms),
            'fields': {},
            'checkboxes': {},
            'forms': []
        }
        
        for form_data in annotated_forms:
            annotation = form_data.get('annotation', {})
            fields = annotation.get('fields', [])
            checkboxes = annotation.get('checkboxes', [])
            
            # Count field types
            for field in fields:
                field_name = field.get('field_name', 'unknown')
                if field_name not in organized['fields']:
                    organized['fields'][field_name] = 0
                organized['fields'][field_name] += 1
            
            # Count checkbox types
            for checkbox in checkboxes:
                label = checkbox.get('label', 'unknown')
                if label not in organized['checkboxes']:
                    organized['checkboxes'][label] = 0
                organized['checkboxes'][label] += 1
            
            organized['forms'].append(form_data)
        
        return organized
    
    def export_to_json(
        self,
        annotated_forms: List[Dict[str, Any]],
        filename: Optional[str] = None
    ) -> Path:
        """Export annotations to JSON format"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"training_data_{timestamp}.json"
        
        output_file = self.output_dir / filename
        
        data = {
            'export_date': datetime.now().isoformat(),
            'total_forms': len(annotated_forms),
            'data': annotated_forms
        }
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        return output_file
    
    def export_stats(self, annotated_forms: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate statistics about training data"""
        stats = {
            'total_forms': len(annotated_forms),
            'total_fields': 0,
            'total_checkboxes': 0,
            'field_types': {},
            'checkbox_labels': {},
            'forms_with_all_fields': 0,
            'forms_with_checkboxes': 0
        }
        
        for form_data in annotated_forms:
            annotation = form_data.get('annotation', {})
            fields = annotation.get('fields', [])
            checkboxes = annotation.get('checkboxes', [])
            
            stats['total_fields'] += len(fields)
            stats['total_checkboxes'] += len(checkboxes)
            
            if len(fields) > 0:
                stats['forms_with_all_fields'] += 1
            
            if len(checkboxes) > 0:
                stats['forms_with_checkboxes'] += 1
            
            # Count field types
            for field in fields:
                field_name = field.get('field_name', 'unknown')
                stats['field_types'][field_name] = stats['field_types'].get(field_name, 0) + 1
            
            # Count checkbox labels
            for checkbox in checkboxes:
                label = checkbox.get('label', 'unknown')
                stats['checkbox_labels'][label] = stats['checkbox_labels'].get(label, 0) + 1
        
        return stats

