"""
Train Best OCR Model for Student Forms

This script:
1. Analyzes verified forms to determine best OCR model
2. Prepares training data with field mappings
3. Trains the optimal model (CRAFT+TR-OCR, Tesseract, or combo)
4. Tests and evaluates the trained model
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy.orm import Session
from backend.database import get_db, AdmissionForm, FormStatus
from backend.training.prepare_student_forms_training_data import prepare_training_data_from_database
from backend.training.field_mapper import field_mapper, StudentFormFieldMapper
from backend.config import settings


def analyze_form_characteristics(db: Session, limit: int = 50) -> Dict[str, Any]:
    """
    Analyze verified forms to determine:
    - Handwritten vs printed text ratio
    - Average confidence scores
    - Best OCR provider based on results
    """
    forms = db.query(AdmissionForm).filter(
        AdmissionForm.status == FormStatus.VERIFIED
    ).limit(limit).all()
    
    if not forms:
        return {
            'total_forms': 0,
            'recommendation': 'tesseract',
            'reason': 'No verified forms found'
        }
    
    provider_stats = {}
    handwritten_count = 0
    total_confidence = 0
    confidence_count = 0
    
    for form in forms:
        # Count providers used
        provider = form.ocr_provider or 'unknown'
        if provider not in provider_stats:
            provider_stats[provider] = {
                'count': 0,
                'total_confidence': 0,
                'confidence_count': 0
            }
        provider_stats[provider]['count'] += 1
        
        # Analyze confidence
        if form.extracted_data and isinstance(form.extracted_data, dict):
            confidence = form.extracted_data.get('confidence', 0)
            if confidence:
                total_confidence += confidence
                confidence_count += 1
                provider_stats[provider]['total_confidence'] += confidence
                provider_stats[provider]['confidence_count'] += 1
        
        # Check if handwritten (heuristic: low confidence + specific fields)
        if form.extracted_data and isinstance(form.extracted_data, dict):
            raw_text = form.extracted_data.get('raw_text', '')
            # Simple heuristic: if confidence is low and text has variations, likely handwritten
            if confidence and confidence < 70:
                handwritten_count += 1
    
    # Calculate averages
    avg_confidence = total_confidence / confidence_count if confidence_count > 0 else 0
    handwritten_ratio = handwritten_count / len(forms) if forms else 0
    
    # Determine best provider
    best_provider = 'tesseract'
    best_avg_confidence = 0
    
    for provider, stats in provider_stats.items():
        if stats['confidence_count'] > 0:
            avg_conf = stats['total_confidence'] / stats['confidence_count']
            if avg_conf > best_avg_confidence:
                best_avg_confidence = avg_conf
                best_provider = provider
    
    # Recommendation logic
    if handwritten_ratio > 0.5:
        recommendation = 'craft-trocr'
        reason = f'High handwritten text ratio ({handwritten_ratio:.1%}). CRAFT+TR-OCR is best for handwritten forms.'
    elif avg_confidence < 70:
        recommendation = 'craft-trocr'
        reason = f'Low average confidence ({avg_confidence:.1f}%). CRAFT+TR-OCR will improve accuracy.'
    elif 'google-documentai' in provider_stats or 'azure-form-recognizer' in provider_stats:
        recommendation = 'craft-trocr'
        reason = 'Cloud OCR providers used. CRAFT+TR-OCR can match or exceed performance locally.'
    else:
        recommendation = 'tesseract'
        reason = f'Good confidence with current provider ({avg_confidence:.1f}%). Tesseract fine-tuning may be sufficient.'
    
    return {
        'total_forms': len(forms),
        'handwritten_ratio': handwritten_ratio,
        'avg_confidence': avg_confidence,
        'provider_stats': {
            k: {
                'count': v['count'],
                'avg_confidence': v['total_confidence'] / v['confidence_count'] if v['confidence_count'] > 0 else 0
            }
            for k, v in provider_stats.items()
        },
        'best_provider': best_provider,
        'recommendation': recommendation,
        'reason': reason
    }


def prepare_training_data_with_mappings(
    db: Session,
    output_path: str,
    limit: Optional[int] = None
) -> Dict[str, Any]:
    """
    Prepare training data with field mappings for better model training.
    """
    print("=" * 80)
    print("Preparing Training Data with Field Mappings")
    print("=" * 80)
    print()
    
    # Get verified forms
    query = db.query(AdmissionForm).filter(AdmissionForm.status == FormStatus.VERIFIED)
    if limit:
        query = query.limit(limit)
    
    forms = query.order_by(AdmissionForm.verified_date.desc()).all()
    
    print(f"Found {len(forms)} verified forms")
    print()
    
    training_data = []
    stats = {
        'total_forms': len(forms),
        'processed': 0,
        'with_mappings': 0,
        'skipped': 0
    }
    
    for form in forms:
        # Check if file exists
        file_path = Path(form.file_path)
        if not file_path.exists():
            stats['skipped'] += 1
            continue
        
        # Get OCR text
        raw_text = ''
        if form.extracted_data and isinstance(form.extracted_data, dict):
            raw_text = form.extracted_data.get('raw_text', '')
        
        if not raw_text:
            stats['skipped'] += 1
            continue
        
        # Get verified fields - ALL fields from the form
        verified_fields = {}
        additional_info = form.additional_info if isinstance(form.additional_info, dict) else {}
        
        # Standard database fields
        standard_fields = [
            'student_name', 'date_of_birth', 'gender', 'category', 'nationality', 'religion',
            'aadhar_number', 'blood_group', 'permanent_address', 'correspondence_address',
            'city', 'state', 'pincode', 'phone_number', 'alternate_phone', 'email',
            'emergency_contact_name', 'emergency_contact_phone', 'father_name', 'father_occupation',
            'father_phone', 'mother_name', 'mother_occupation', 'mother_phone',
            'guardian_name', 'guardian_relation', 'guardian_phone', 'annual_income',
            'tenth_board', 'tenth_year', 'tenth_percentage', 'tenth_school',
            'twelfth_board', 'twelfth_year', 'twelfth_percentage', 'twelfth_school',
            'previous_qualification', 'graduation_details', 'course_applied',
            'application_number', 'enrollment_number', 'admission_date'
        ]
        
        for key in standard_fields:
            value = getattr(form, key, None)
            if value:
                verified_fields[key] = str(value)
        
        # Additional fields from additional_info
        additional_field_keys = [
            # Academic & Admission
            'academic_session', 'course', 'admission_category', 'admission_category_other',
            'du_portal_form_number', 'cuet_score', 'college_roll_no', 'date_of_admission',
            # Name Fields
            'first_name', 'middle_name', 'surname',
            # Additional Personal
            'below_poverty_line', 'minority_category',
            # Address Details (separate lines)
            'permanent_address_line1', 'permanent_address_line2', 'permanent_address_line3',
            'permanent_state', 'permanent_pincode',
            'correspondence_address_line1', 'correspondence_address_line2', 'correspondence_address_line3',
            'correspondence_state', 'correspondence_pincode',
            # Parent/Guardian Occupational Details
            'father_designation', 'father_organization', 'father_email',
            'father_mobile', 'father_landline_code', 'father_landline',
            'mother_designation', 'mother_organization', 'mother_email',
            'mother_mobile', 'mother_landline_code', 'mother_landline',
            'guardian_residential_address', 'guardian_organization', 'guardian_email',
            'guardian_mobile', 'guardian_landline_code', 'guardian_landline',
            # Educational Details
            'twelfth_roll_number', 'twelfth_institution', 'hindi_studied_upto',
            # CUET Marks
            'cuet_subject_1', 'cuet_total_score_1', 'cuet_score_obtained_1',
            'cuet_subject_2', 'cuet_total_score_2', 'cuet_score_obtained_2',
            'cuet_subject_3', 'cuet_total_score_3', 'cuet_score_obtained_3',
            'cuet_subject_4', 'cuet_total_score_4', 'cuet_score_obtained_4',
            'cuet_subject_5', 'cuet_total_score_5', 'cuet_score_obtained_5',
            'cuet_subject_6', 'cuet_total_score_6', 'cuet_score_obtained_6',
            'cuet_total_score',
            # Other Information
            'du_enrollment_number', 'hindi_medium_preference',
            # Category Certificate Details
            'category_certificate_authority', 'category_certificate_number', 'category_certificate_date',
            'disability_percentage', 'disability_type', 'udid_number',
            # Document Checklist (boolean fields)
            'document_printed_admission_form', 'document_anti_ragging_undertaking', 'document_photographs_pasted',
            'document_cuet_score_card', 'document_twelfth_mark_sheet', 'document_tenth_certificate',
            'document_twelfth_certificate', 'document_character_certificate', 'document_transfer_certificate',
            'document_migration_certificate', 'document_hindi_exemption_certificate', 'document_caste_category_certificate',
            'document_sports_eca_certificates', 'document_original_certificates', 'document_photo_id_proofs',
            # Declaration Fields
            'student_declaration_name', 'student_declaration_date', 'student_declaration_place',
            'parent_guardian_name', 'parent_guardian_relationship', 'parent_guardian_candidate_name',
            'parent_guardian_course', 'parent_guardian_date', 'parent_guardian_place'
        ]
        
        for key in additional_field_keys:
            value = additional_info.get(key)
            if value:
                verified_fields[key] = str(value)
        
        if len(verified_fields) < 5:
            stats['skipped'] += 1
            continue
        
        # Create training example with field mappings
        training_example = field_mapper.create_training_example(raw_text, verified_fields)
        
        # Resolve image path
        if file_path.suffix.lower() == '.pdf':
            from pdf2image import convert_from_path
            try:
                images = convert_from_path(str(file_path), first_page=1, last_page=1)
                if images:
                    image_output = Path(settings.UPLOAD_DIR) / "training_images" / f"form_{form.id}_page1.png"
                    image_output.parent.mkdir(parents=True, exist_ok=True)
                    images[0].save(image_output)
                    image_path = str(image_output)
                else:
                    stats['skipped'] += 1
                    continue
            except Exception as e:
                print(f"⚠️  Error processing PDF {form.id}: {e}")
                stats['skipped'] += 1
                continue
        else:
            image_path = str(file_path)
        
        # Add to training data
        training_data.append({
            'image_path': image_path,
            'text': raw_text,
            'verified_fields': verified_fields,
            'field_mappings': training_example['field_mappings'],
            'form_id': form.id,
            'student_name': form.student_name,
            'field_count': len(verified_fields)
        })
        
        stats['processed'] += 1
        if training_example['field_mappings']:
            stats['with_mappings'] += 1
        
        if stats['processed'] % 10 == 0:
            print(f"✅ Processed {stats['processed']} forms...")
    
    # Save training data
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(training_data, f, indent=2, ensure_ascii=False)
    
    print()
    print("=" * 80)
    print("Training Data Preparation Complete")
    print("=" * 80)
    print(f"✅ Processed: {stats['processed']} forms")
    print(f"✅ With field mappings: {stats['with_mappings']} forms")
    print(f"⚠️  Skipped: {stats['skipped']} forms")
    print(f"📁 Saved to: {output_file}")
    print()
    
    return {
        **stats,
        'output_file': str(output_file),
        'samples': len(training_data)
    }


def train_best_model(
    training_data_path: str,
    output_model_path: str,
    model_type: str = 'auto',
    epochs: int = 20,
    batch_size: int = 8
) -> Dict[str, Any]:
    """
    Train the best model based on analysis.
    
    Args:
        training_data_path: Path to training data JSON
        output_model_path: Path to save trained model
        model_type: 'auto', 'craft-trocr', or 'tesseract'
        epochs: Number of training epochs
        batch_size: Training batch size
    """
    print("=" * 80)
    print("Training Best OCR Model for Student Forms")
    print("=" * 80)
    print()
    
    # Load training data
    with open(training_data_path, 'r', encoding='utf-8') as f:
        training_data = json.load(f)
    
    print(f"Training data: {len(training_data)} samples")
    print()
    
    # Determine model type
    if model_type == 'auto':
        # Analyze to determine best model
        # Default to CRAFT+TR-OCR for handwritten forms (best for student forms)
        model_type = 'craft-trocr'
        print("✅ Auto-selected: CRAFT + TR-OCR")
        print("   Best for handwritten student admission forms")
        print()
    
    # Train based on model type
    if model_type == 'craft-trocr':
        print("Training CRAFT + TR-OCR model...")
        print()
        
        # Convert training data to TR-OCR format
        trocr_data = []
        for item in training_data:
            # Use verified text as ground truth
            text = item.get('text', '')
            # Or use verified fields combined
            verified_fields = item.get('verified_fields', {})
            if verified_fields:
                # Combine verified fields into text
                field_texts = []
                for key, value in verified_fields.items():
                    if value:
                        field_texts.append(f"{key.replace('_', ' ').title()}: {value}")
                if field_texts:
                    text = '\n'.join(field_texts)
            
            trocr_data.append({
                'image_path': item['image_path'],
                'text': text
            })
        
        # Save TR-OCR format data
        trocr_data_path = Path(training_data_path).parent / 'trocr_training_data.json'
        with open(trocr_data_path, 'w', encoding='utf-8') as f:
            json.dump(trocr_data, f, indent=2, ensure_ascii=False)
        
        # Train TR-OCR
        from backend.training.train_craft_trocr import train_craft_trocr
        
        train_craft_trocr(
            training_data_path=str(trocr_data_path),
            output_model_path=output_model_path,
            epochs=epochs,
            batch_size=batch_size,
            learning_rate=5e-5,
            base_model='microsoft/trocr-base-handwritten'
        )
        
        return {
            'model_type': 'craft-trocr',
            'model_path': output_model_path,
            'training_samples': len(trocr_data)
        }
    
    else:
        raise ValueError(f"Unsupported model type: {model_type}")


def main():
    """Main training workflow"""
    parser = argparse.ArgumentParser(
        description="Train best OCR model for student forms",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        '--analyze-only',
        action='store_true',
        help='Only analyze forms, do not train'
    )
    parser.add_argument(
        '--prepare-only',
        action='store_true',
        help='Only prepare training data, do not train'
    )
    parser.add_argument(
        '--training-data',
        help='Path to existing training data (skip preparation)'
    )
    parser.add_argument(
        '--output-data',
        default='training_data/student_forms_with_mappings.json',
        help='Output path for training data'
    )
    parser.add_argument(
        '--output-model',
        default='models/trocr_student_forms',
        help='Output path for trained model'
    )
    parser.add_argument(
        '--model-type',
        choices=['auto', 'craft-trocr', 'tesseract'],
        default='auto',
        help='Model type to train'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of forms to use'
    )
    parser.add_argument(
        '--epochs',
        type=int,
        default=20,
        help='Training epochs'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=8,
        help='Training batch size'
    )
    
    args = parser.parse_args()
    
    # Get database session
    db = next(get_db())
    
    try:
        # Step 1: Analyze forms
        print("Step 1: Analyzing verified forms...")
        print()
        analysis = analyze_form_characteristics(db, limit=args.limit or 100)
        
        print("Analysis Results:")
        print(f"  Total forms: {analysis['total_forms']}")
        print(f"  Handwritten ratio: {analysis['handwritten_ratio']:.1%}")
        print(f"  Average confidence: {analysis['avg_confidence']:.1f}%")
        print(f"  Best provider: {analysis['best_provider']}")
        print()
        print(f"Recommendation: {analysis['recommendation']}")
        print(f"Reason: {analysis['reason']}")
        print()
        
        if args.analyze_only:
            return
        
        # Step 2: Prepare training data
        if not args.training_data:
            print("Step 2: Preparing training data with field mappings...")
            print()
            prep_result = prepare_training_data_with_mappings(
                db=db,
                output_path=args.output_data,
                limit=args.limit
            )
            
            if prep_result['samples'] == 0:
                print("❌ No training data generated!")
                return
            
            training_data_path = args.output_data
        else:
            training_data_path = args.training_data
            print(f"Using existing training data: {training_data_path}")
            print()
        
        if args.prepare_only:
            return
        
        # Step 3: Train model
        print("Step 3: Training model...")
        print()
        
        # Use recommendation if auto
        model_type = analysis['recommendation'] if args.model_type == 'auto' else args.model_type
        
        train_result = train_best_model(
            training_data_path=training_data_path,
            output_model_path=args.output_model,
            model_type=model_type,
            epochs=args.epochs,
            batch_size=args.batch_size
        )
        
        print()
        print("=" * 80)
        print("✅ Training Complete!")
        print("=" * 80)
        print(f"Model type: {train_result['model_type']}")
        print(f"Model path: {train_result['model_path']}")
        print(f"Training samples: {train_result['training_samples']}")
        print()
        print("To use the trained model:")
        print(f"  export TROCR_CUSTOM_MODEL_PATH='{train_result['model_path']}'")
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
