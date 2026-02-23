"""
Google OCR Training and Improvement System

This module provides:
1. Training data collection from verified forms
2. Pattern learning from corrections
3. Field extraction accuracy evaluation
4. Continuous improvement through user feedback
"""
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import re
from collections import defaultdict

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class GoogleOCRTrainer:
    """
    Trains and improves Google OCR field extraction through:
    1. Collecting verified form data
    2. Learning correction patterns
    3. Building field-specific extraction rules
    4. Evaluating and improving accuracy
    """
    
    def __init__(self, training_dir: Optional[str] = None):
        self.training_dir = Path(training_dir or "training_data/google_ocr")
        self.training_dir.mkdir(parents=True, exist_ok=True)
        
        # Training data files
        self.verified_samples_path = self.training_dir / "verified_samples.json"
        self.corrections_path = self.training_dir / "corrections.json"
        self.patterns_path = self.training_dir / "learned_patterns.json"
        self.metrics_path = self.training_dir / "training_metrics.json"
        
        # Load existing data
        self.verified_samples = self._load_json(self.verified_samples_path, [])
        self.corrections = self._load_json(self.corrections_path, {})
        self.learned_patterns = self._load_json(self.patterns_path, {})
        self.metrics = self._load_json(self.metrics_path, {
            'total_samples': 0,
            'field_accuracy': {},
            'training_runs': []
        })
    
    def _load_json(self, path: Path, default: Any) -> Any:
        """Load JSON file or return default"""
        try:
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load {path}: {e}")
        return default
    
    def _save_json(self, path: Path, data: Any):
        """Save data to JSON file"""
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Could not save {path}: {e}")
    
    def add_verified_sample(
        self,
        form_id: str,
        raw_ocr_text: str,
        extracted_fields: Dict[str, str],
        verified_fields: Dict[str, str],
        image_path: Optional[str] = None
    ):
        """
        Add a verified form sample for training.
        
        Args:
            form_id: Unique form identifier
            raw_ocr_text: Raw OCR output text
            extracted_fields: Auto-extracted field values
            verified_fields: User-verified correct values
            image_path: Optional path to form image
        """
        # Calculate accuracy for this sample
        correct_count = 0
        field_results = {}
        
        for field, verified_value in verified_fields.items():
            extracted_value = extracted_fields.get(field, '')
            is_correct = self._values_match(extracted_value, verified_value)
            
            field_results[field] = {
                'extracted': extracted_value,
                'verified': verified_value,
                'correct': is_correct
            }
            
            if is_correct:
                correct_count += 1
            elif extracted_value:
                # Record correction for learning
                self._add_correction(field, extracted_value, verified_value)
        
        accuracy = correct_count / len(verified_fields) if verified_fields else 0.0
        
        sample = {
            'form_id': form_id,
            'raw_ocr_text': raw_ocr_text,
            'extracted_fields': extracted_fields,
            'verified_fields': verified_fields,
            'field_results': field_results,
            'accuracy': round(accuracy, 3),
            'image_path': image_path,
            'timestamp': datetime.now().isoformat()
        }
        
        # Check if sample already exists
        existing_idx = next(
            (i for i, s in enumerate(self.verified_samples) if s['form_id'] == form_id),
            None
        )
        
        if existing_idx is not None:
            self.verified_samples[existing_idx] = sample
        else:
            self.verified_samples.append(sample)
        
        # Save updated data
        self._save_json(self.verified_samples_path, self.verified_samples)
        self._save_json(self.corrections_path, self.corrections)
        
        # Update metrics
        self._update_metrics()
        
        return {
            'accuracy': accuracy,
            'correct_fields': correct_count,
            'total_fields': len(verified_fields),
            'corrections_learned': len([f for f in field_results.values() if not f['correct'] and f['extracted']])
        }
    
    def _values_match(self, extracted: str, verified: str) -> bool:
        """Check if extracted and verified values match (with normalization)"""
        if not extracted or not verified:
            return not extracted and not verified
        
        # Normalize for comparison
        ext_normalized = self._normalize_value(extracted)
        ver_normalized = self._normalize_value(verified)
        
        return ext_normalized == ver_normalized
    
    def _normalize_value(self, value: str) -> str:
        """Normalize a value for comparison"""
        if not value:
            return ""
        
        # Lowercase
        value = value.lower().strip()
        
        # Remove extra spaces
        value = re.sub(r'\s+', ' ', value)
        
        # Remove common punctuation
        value = re.sub(r'[.,;:\-\'\"]+', '', value)
        
        return value
    
    def _add_correction(self, field: str, wrong: str, correct: str):
        """Add a correction for learning"""
        if field not in self.corrections:
            self.corrections[field] = []
        
        # Check if this correction already exists
        for correction in self.corrections[field]:
            if correction['wrong'] == wrong and correction['correct'] == correct:
                correction['count'] = correction.get('count', 1) + 1
                return
        
        self.corrections[field].append({
            'wrong': wrong,
            'correct': correct,
            'count': 1,
            'timestamp': datetime.now().isoformat()
        })
    
    def _update_metrics(self):
        """Update training metrics"""
        self.metrics['total_samples'] = len(self.verified_samples)
        
        # Calculate per-field accuracy
        field_stats = defaultdict(lambda: {'correct': 0, 'total': 0})
        
        for sample in self.verified_samples:
            for field, result in sample.get('field_results', {}).items():
                field_stats[field]['total'] += 1
                if result.get('correct'):
                    field_stats[field]['correct'] += 1
        
        self.metrics['field_accuracy'] = {
            field: {
                'accuracy': round(stats['correct'] / stats['total'], 3) if stats['total'] > 0 else 0,
                'correct': stats['correct'],
                'total': stats['total']
            }
            for field, stats in field_stats.items()
        }
        
        self._save_json(self.metrics_path, self.metrics)
    
    def learn_patterns(self) -> Dict[str, Any]:
        """
        Learn extraction patterns from corrections.
        
        Returns:
            Dictionary of learned patterns per field
        """
        patterns = {}
        
        for field, field_corrections in self.corrections.items():
            if not field_corrections:
                continue
            
            field_patterns = {
                'common_errors': [],
                'value_patterns': [],
                'context_hints': []
            }
            
            # Analyze common errors
            for correction in sorted(field_corrections, key=lambda x: -x.get('count', 1))[:10]:
                wrong = correction['wrong']
                correct = correction['correct']
                
                # Detect error type
                error_type = self._detect_error_type(wrong, correct)
                
                field_patterns['common_errors'].append({
                    'wrong': wrong,
                    'correct': correct,
                    'error_type': error_type,
                    'frequency': correction.get('count', 1)
                })
            
            # Learn value patterns from correct values
            correct_values = [c['correct'] for c in field_corrections]
            value_pattern = self._learn_value_pattern(correct_values)
            if value_pattern:
                field_patterns['value_patterns'].append(value_pattern)
            
            patterns[field] = field_patterns
        
        self.learned_patterns = patterns
        self._save_json(self.patterns_path, patterns)
        
        return patterns
    
    def _detect_error_type(self, wrong: str, correct: str) -> str:
        """Detect the type of OCR error"""
        if not wrong or not correct:
            return 'missing'
        
        # Check for character substitution (similar length)
        if abs(len(wrong) - len(correct)) <= 2:
            # Count different characters
            diff_count = sum(1 for a, b in zip(wrong, correct) if a != b)
            if diff_count <= 3:
                return 'substitution'
        
        # Check for spacing issues
        if wrong.replace(' ', '') == correct.replace(' ', ''):
            return 'spacing'
        
        # Check for case issues
        if wrong.lower() == correct.lower():
            return 'case'
        
        # Check for word order
        wrong_words = set(wrong.lower().split())
        correct_words = set(correct.lower().split())
        if wrong_words == correct_words:
            return 'word_order'
        
        # Check for truncation
        if correct.lower().startswith(wrong.lower()) or wrong.lower().startswith(correct.lower()):
            return 'truncation'
        
        return 'unknown'
    
    def _learn_value_pattern(self, values: List[str]) -> Optional[str]:
        """Learn a regex pattern from correct values"""
        if not values:
            return None
        
        # Group values by structure
        structures = defaultdict(list)
        for value in values:
            # Create structure signature
            structure = re.sub(r'[a-zA-Z]+', 'A', value)
            structure = re.sub(r'\d+', 'D', structure)
            structures[structure].append(value)
        
        # Find most common structure
        if structures:
            most_common = max(structures.keys(), key=lambda k: len(structures[k]))
            # Convert structure to regex
            pattern = most_common
            pattern = re.sub(r'A+', r'[A-Za-z]+', pattern)
            pattern = re.sub(r'D+', r'\\d+', pattern)
            pattern = re.escape(pattern).replace(r'\[', '[').replace(r'\]', ']').replace(r'\\\\', '\\')
            return f"^{pattern}$"
        
        return None
    
    def run_training_evaluation(self) -> Dict[str, Any]:
        """
        Run evaluation on all training samples.
        
        Returns:
            Evaluation results with accuracy metrics
        """
        from backend.ocr.google_ocr_enhancer import GoogleOCREnhancer
        
        enhancer = GoogleOCREnhancer()
        
        results = {
            'total_samples': len(self.verified_samples),
            'overall_accuracy': 0,
            'field_accuracies': {},
            'improvements': [],
            'timestamp': datetime.now().isoformat()
        }
        
        field_correct = defaultdict(int)
        field_total = defaultdict(int)
        total_correct = 0
        total_fields = 0
        
        for sample in self.verified_samples:
            raw_text = sample.get('raw_ocr_text', '')
            verified_fields = sample.get('verified_fields', {})
            
            # Re-extract with current enhancer
            extracted = enhancer.extract_all_fields(raw_text)
            
            for field, verified_value in verified_fields.items():
                field_total[field] += 1
                total_fields += 1
                
                if field in extracted:
                    extracted_value = extracted[field]['value']
                    if self._values_match(extracted_value, verified_value):
                        field_correct[field] += 1
                        total_correct += 1
        
        # Calculate accuracies
        results['overall_accuracy'] = round(total_correct / total_fields, 3) if total_fields > 0 else 0
        
        for field in field_total:
            accuracy = round(field_correct[field] / field_total[field], 3) if field_total[field] > 0 else 0
            results['field_accuracies'][field] = {
                'accuracy': accuracy,
                'correct': field_correct[field],
                'total': field_total[field]
            }
        
        # Record training run
        self.metrics['training_runs'].append({
            'timestamp': results['timestamp'],
            'overall_accuracy': results['overall_accuracy'],
            'samples_evaluated': results['total_samples']
        })
        
        self._save_json(self.metrics_path, self.metrics)
        
        return results
    
    def export_training_data_for_trocr(self, output_path: Optional[str] = None) -> str:
        """
        Export training data in TrOCR format.
        
        Returns:
            Path to exported file
        """
        if output_path is None:
            output_path = self.training_dir / "trocr_training_data.json"
        else:
            output_path = Path(output_path)
        
        trocr_data = []
        
        for sample in self.verified_samples:
            # Create text target from verified fields
            field_texts = []
            for field, value in sample.get('verified_fields', {}).items():
                if value:
                    field_texts.append(f"{field}: {value}")
            
            target_text = "\n".join(field_texts)
            
            trocr_data.append({
                'image_path': sample.get('image_path', ''),
                'text': target_text,
                'raw_ocr': sample.get('raw_ocr_text', ''),
                'fields': sample.get('verified_fields', {}),
                'form_id': sample.get('form_id', '')
            })
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(trocr_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Exported {len(trocr_data)} training samples to {output_path}")
        
        return str(output_path)
    
    def get_training_summary(self) -> Dict[str, Any]:
        """Get summary of training data and performance"""
        summary = {
            'total_samples': len(self.verified_samples),
            'total_corrections': sum(len(c) for c in self.corrections.values()),
            'fields_tracked': list(self.corrections.keys()),
            'field_accuracy': self.metrics.get('field_accuracy', {}),
            'training_runs': len(self.metrics.get('training_runs', [])),
            'last_training': self.metrics.get('training_runs', [{}])[-1] if self.metrics.get('training_runs') else None
        }
        
        # Find fields needing improvement
        low_accuracy_fields = [
            field for field, stats in summary['field_accuracy'].items()
            if stats.get('accuracy', 0) < 0.7
        ]
        summary['fields_needing_improvement'] = low_accuracy_fields
        
        return summary
    
    def generate_improvement_report(self) -> str:
        """Generate a detailed improvement report"""
        summary = self.get_training_summary()
        
        report = []
        report.append("=" * 60)
        report.append("GOOGLE OCR TRAINING REPORT")
        report.append("=" * 60)
        report.append("")
        
        report.append(f"Total Training Samples: {summary['total_samples']}")
        report.append(f"Total Corrections Learned: {summary['total_corrections']}")
        report.append(f"Training Runs Completed: {summary['training_runs']}")
        report.append("")
        
        if summary['field_accuracy']:
            report.append("-" * 40)
            report.append("FIELD ACCURACY (sorted by accuracy)")
            report.append("-" * 40)
            
            sorted_fields = sorted(
                summary['field_accuracy'].items(),
                key=lambda x: x[1].get('accuracy', 0)
            )
            
            for field, stats in sorted_fields:
                acc = stats.get('accuracy', 0) * 100
                correct = stats.get('correct', 0)
                total = stats.get('total', 0)
                status = "✅" if acc >= 80 else "⚠️" if acc >= 60 else "❌"
                report.append(f"{status} {field}: {acc:.1f}% ({correct}/{total})")
        
        report.append("")
        
        if summary['fields_needing_improvement']:
            report.append("-" * 40)
            report.append("FIELDS NEEDING IMPROVEMENT")
            report.append("-" * 40)
            
            for field in summary['fields_needing_improvement']:
                corrections = self.corrections.get(field, [])
                if corrections:
                    report.append(f"\n{field}:")
                    for corr in corrections[:3]:  # Top 3 corrections
                        report.append(f"  '{corr['wrong']}' → '{corr['correct']}' (count: {corr.get('count', 1)})")
        
        report.append("")
        report.append("=" * 60)
        
        return "\n".join(report)


class TrainingDataGenerator:
    """
    Generates training data from existing form database.
    """
    
    def __init__(self, db_session=None):
        self.db = db_session
        self.trainer = GoogleOCRTrainer()
    
    def generate_from_database(self, limit: int = 100) -> Dict[str, Any]:
        """
        Generate training data from database forms.
        
        Args:
            limit: Maximum number of forms to process
            
        Returns:
            Generation results
        """
        if self.db is None:
            from backend.database import SessionLocal
            self.db = SessionLocal()
        
        from backend.database import AdmissionForm
        
        # Get forms with extracted data
        forms = self.db.query(AdmissionForm).filter(
            AdmissionForm.extracted_data.isnot(None)
        ).limit(limit).all()
        
        results = {
            'processed': 0,
            'added': 0,
            'errors': []
        }
        
        for form in forms:
            try:
                if not form.extracted_data:
                    continue
                
                # Get OCR text from form
                raw_text = form.extracted_data.get('raw_text', '')
                if not raw_text:
                    continue
                
                # Get verified fields (from manual corrections or additional_info)
                verified_fields = {}
                
                # Use existing extracted fields as baseline
                for key, value in form.extracted_data.items():
                    if key not in ['raw_text', 'provider', 'confidence', 'structured_data']:
                        if value and isinstance(value, str):
                            verified_fields[key] = value
                
                # Apply any manual corrections
                if form.additional_info:
                    corrections = form.additional_info.get('corrections', {})
                    verified_fields.update(corrections)
                
                if verified_fields:
                    self.trainer.add_verified_sample(
                        form_id=str(form.id),
                        raw_ocr_text=raw_text,
                        extracted_fields=form.extracted_data,
                        verified_fields=verified_fields,
                        image_path=form.file_path
                    )
                    results['added'] += 1
                
                results['processed'] += 1
                
            except Exception as e:
                results['errors'].append({
                    'form_id': form.id,
                    'error': str(e)
                })
        
        return results
    
    def generate_from_json_samples(self, json_path: str) -> Dict[str, Any]:
        """
        Generate training data from JSON samples file.
        
        Args:
            json_path: Path to JSON file with OCR samples
            
        Returns:
            Generation results
        """
        with open(json_path, 'r', encoding='utf-8') as f:
            samples = json.load(f)
        
        results = {
            'processed': 0,
            'added': 0,
            'errors': []
        }
        
        for sample in samples:
            try:
                image_path = sample.get('image_path', '')
                raw_text = sample.get('text', '')
                confidence = sample.get('confidence', 0)
                
                if not raw_text or confidence < 40:  # Skip low confidence samples
                    continue
                
                # For now, use extracted fields as verified
                # In production, these would be manually verified
                from backend.ocr.google_ocr_enhancer import GoogleOCREnhancer
                enhancer = GoogleOCREnhancer()
                extracted = enhancer.extract_all_fields(raw_text)
                
                verified_fields = {k: v['value'] for k, v in extracted.items()}
                
                if verified_fields:
                    self.trainer.add_verified_sample(
                        form_id=image_path,
                        raw_ocr_text=raw_text,
                        extracted_fields=verified_fields,
                        verified_fields=verified_fields,  # Auto-verified for initial training
                        image_path=image_path
                    )
                    results['added'] += 1
                
                results['processed'] += 1
                
            except Exception as e:
                results['errors'].append({
                    'sample': sample.get('image_path', 'unknown'),
                    'error': str(e)
                })
        
        return results


def main():
    """CLI for training system"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Google OCR Training System")
    parser.add_argument(
        'command',
        choices=['generate', 'train', 'evaluate', 'report', 'export'],
        help="Command to run"
    )
    parser.add_argument('--input', help="Input file for generation")
    parser.add_argument('--output', help="Output file for export")
    parser.add_argument('--limit', type=int, default=100, help="Limit for database generation")
    
    args = parser.parse_args()
    
    trainer = GoogleOCRTrainer()
    generator = TrainingDataGenerator()
    
    if args.command == 'generate':
        if args.input:
            results = generator.generate_from_json_samples(args.input)
        else:
            results = generator.generate_from_database(args.limit)
        
        print(f"Processed: {results['processed']}")
        print(f"Added: {results['added']}")
        if results['errors']:
            print(f"Errors: {len(results['errors'])}")
    
    elif args.command == 'train':
        patterns = trainer.learn_patterns()
        print(f"Learned patterns for {len(patterns)} fields")
    
    elif args.command == 'evaluate':
        results = trainer.run_training_evaluation()
        print(f"Overall Accuracy: {results['overall_accuracy']*100:.1f}%")
        print(f"Samples Evaluated: {results['total_samples']}")
    
    elif args.command == 'report':
        report = trainer.generate_improvement_report()
        print(report)
    
    elif args.command == 'export':
        output_path = trainer.export_training_data_for_trocr(args.output)
        print(f"Exported to: {output_path}")


if __name__ == "__main__":
    main()
