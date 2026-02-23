import logging
import asyncio
from typing import Dict, Any, List, Optional, Union
from sqlalchemy.orm import Session
from datetime import datetime

from backend.database import AdmissionForm, FormStatus, StudentDocument, DocumentCategory
from backend.ocr import get_ocr_provider
from backend.config import settings
from backend.utils.file_handler import load_all_pdf_pages, load_image, get_file_extension, save_document_file
from backend.utils.intelligent_extractor import extract_intelligent
from backend.utils.srcc_form_extractor import extract_srcc_form
from backend.utils.ai_form_parser import AIFormParser
from backend.utils.form_field_applier import apply_structured_data_to_form
from backend.utils.empty_form_detector import EmptyFormDetector
from backend.utils.confidence_scorer import improve_ocr_confidence
from backend.utils.document_extractor import extract_supporting_documents, FORM_PAGE_COUNT

logger = logging.getLogger(__name__)

async def run_enhanced_extraction(
    form: AdmissionForm,
    db: Session,
    ocr_provider: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run the enhanced extraction pipeline on a given form.
    
    This unifies the logic previously found in re_extract_form, providing:
    - Multi-provider support (including "best")
    - Intelligent + SRCC + AI extraction strategies
    - Advanced garbage cleanup and validation
    - Empty form detection
    - Auto-application of fields to the database model
    """
    
    # 1. Determine Provider
    provider_name = (ocr_provider or form.ocr_provider or settings.OCR_PROVIDER).lower()
    if provider_name == "multi":
        provider_name = "best"

    provider = None
    multi_ocr = None
    
    if provider_name == "best":
        from backend.ocr.multi_provider import MultiProviderOCR
        multi_ocr = MultiProviderOCR()
    else:
        try:
            provider = get_ocr_provider(provider_name)
        except ValueError as e:
            raise ValueError(f"OCR provider '{provider_name}' is not available. {str(e)}")

    selected_provider = provider_name

    # 2. Load File
    import os
    from pathlib import Path
    upload_dir = Path(settings.UPLOAD_DIR).resolve()
    full_file_path = upload_dir / form.file_path
    
    if not full_file_path.exists():
        raise FileNotFoundError(f"Form file not found: {form.file_path}")
    
    file_ext = get_file_extension(str(full_file_path))
    is_pdf = file_ext == 'pdf'
    
    ocr_result: Dict[str, Any] = {}
    
    # 3. Perform OCR (Image to Text)
    if is_pdf:
        # Load all pages
        # This can be CPU intensive, might be better in executor if not already
        pages = load_all_pdf_pages(str(full_file_path))
        
        # Split: First 4 pages as form, rest as documents (if specific logic implies this)
        # For general re-extraction, we usually process what's there. 
        # But consistent with upload logic, often first 4 are the form.
        # Let's process ALL pages loaded from the specific file associated with the form.
        
        all_raw_text = []
        all_confidences = []
        page_results = []
        
        for page_index, page_image in enumerate(pages, start=1):
            try:
                if provider_name == "best":
                    page_result = await multi_ocr.extract_with_best_provider(page_image)
                    if page_index == 1:
                        selected_provider = page_result.get('provider_used', 'multi')
                elif provider_name == "tesseract":
                    page_result = await provider.extract_text(page_image, preprocess=True)
                else:
                    page_result = await provider.extract_text(page_image)
                
                if page_result.get('raw_text'):
                    all_raw_text.append(f"\\n--- Page {page_index} ---\\n{page_result['raw_text']}")
                    if page_result.get('confidence'):
                        all_confidences.append(page_result['confidence'])
                
                page_results.append({
                    'page': page_index,
                    'raw_text': page_result.get('raw_text', ''),
                    'confidence': page_result.get('confidence', 0.0),
                    'provider': page_result.get('provider_used', selected_provider)
                })
                
            except Exception as page_error:
                logger.error(f"Error processing page {page_index}: {str(page_error)}")
                continue
        
        combined_text = "\\n".join(all_raw_text)
        avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
        
        ocr_result = {
            "raw_text": combined_text,
            "confidence": round(avg_confidence, 2),
            "structured_data": None,
            "provider": selected_provider,
            "pages_processed": len(pages),
            "page_results": page_results
        }
        
    else:
        # Single Image
        image = load_image(str(full_file_path))
        
        if provider_name == "best":
            ocr_result = await multi_ocr.extract_with_best_provider(image)
            selected_provider = ocr_result.get('provider_used', 'multi')
        elif provider_name == "tesseract":
            ocr_result = await provider.extract_text(image, preprocess=True)
        else:
            ocr_result = await provider.extract_text(image)
        
        ocr_result.setdefault("pages_processed", 1)
        ocr_result.setdefault(
            "page_results",
            [
                {
                    "page": 1,
                    "raw_text": ocr_result.get("raw_text", ""),
                    "confidence": ocr_result.get("confidence"),
                    "provider": ocr_result.get("provider", selected_provider),
                }
            ],
        )
        ocr_result.setdefault("provider", selected_provider)

    # 4. Intelligent Data Extraction (Text to Structured Data)
    if ocr_result.get('raw_text'):
        # Strategies: Intelligent -> SRCC -> AI -> Text Fallback
        
        intelligent_parsed = extract_intelligent(ocr_result['raw_text'])
        srcc_parsed = extract_srcc_form(ocr_result['raw_text'])
        
        structured_data = {}
        
        # Merge: Intelligent first
        for field, value in intelligent_parsed.items():
            if value and str(value).strip():
                structured_data[field] = str(value).strip()
        
        # Merge: SRCC (Priority Overwrite)
        # SRCC extractor is specialized, so its results should take precedence
        for field, value in srcc_parsed.items():
            if value and str(value).strip():
                value_str = str(value).strip()
                value_lower = value_str.lower()
                
                # Basic Label Filtering
                if len(value_lower.split()) <= 1:
                    if value_lower in ['please', 'tick', 'check', 'enter', 'fill', 'select', 'name', 'block', 'letters']:
                        continue
                
                if field == 'student_name':
                    if value_lower in ['name in block letters', 'in block letters', 'block letters']:
                        continue
                    if len(value_str) < 2:
                        continue
                
                # Overwrite or set
                structured_data[field] = value
        
        # AI Parser Fallback
        ai_parser = AIFormParser()
        
        # If we have existing structured data in the OCR result (unlikely for raw extraction, but possible if passed)
        if ocr_result.get('structured_data'):
             # This block handles if the OCR provider itself returned structured data (e.g. Azure Forms)
            ai_parsed = ai_parser.parse_from_ai_result(ocr_result)
            for field, value in ai_parsed.items():
                if field not in structured_data and value:
                    structured_data[field] = value
                    
        # Text-based fallback via AI Parser
        text_parsed = ai_parser.parse_from_text(ocr_result['raw_text'])
        for field, value in text_parsed.items():
            if field not in structured_data and value:
                structured_data[field] = value
                
        # 5. Pre-filter garbage: Remove form labels and field names before processing
        _filter_form_labels(structured_data, ocr_result.get('raw_text', ''))
        
        # 6. Advanced Cleanup & Validation
        _perform_garbage_cleanup(structured_data)
        
        # 6. Confidence Scoring
        try:
            original_confidence = ocr_result.get('confidence', 0)
            improved_confidence = improve_ocr_confidence(structured_data, original_confidence)
            ocr_result['confidence'] = round(improved_confidence, 2)
            ocr_result['confidence_improved'] = True
            ocr_result['original_confidence'] = original_confidence
        except Exception:
            pass
            
        # 7. Name Construction
        _construct_student_name(structured_data)
        
        # 8. Final Garbage Check
        _final_garbage_check(structured_data)
        
        ocr_result['structured_data'] = structured_data
        
        # 9. Apply to DB Model
        fields_set = apply_structured_data_to_form(form, structured_data)
        logger.info(f"Enhanced Extraction: Applied {fields_set} fields to form {form.id}")

    # 10. Empty Form Detection
    empty_detector = EmptyFormDetector()
    empty_check = empty_detector.detect_empty(ocr_result)
    ocr_result['empty_form_detection'] = empty_check
    
    # Update Form Record
    form.extracted_data = ocr_result
    form.ocr_provider = selected_provider
    form.status = FormStatus.EXTRACTED
    
    if empty_check.get('is_empty') and empty_check.get('confidence', 0) > 0.7:
        if form.additional_info is None:
            form.additional_info = {}
        form.additional_info['empty_form_warning'] = {
            'message': empty_detector.get_empty_form_message(),
            'detection': empty_check
        }
        
    db.commit()
    
    # 11. Extract Supporting Documents (pages 5+)
    if is_pdf and len(pages) > FORM_PAGE_COUNT:
        try:
            from pathlib import Path
            upload_dir = Path(settings.UPLOAD_DIR).resolve()
            
            # Get student info for document naming
            structured = ocr_result.get('structured_data', {})
            student_name = structured.get('student_name', '') or form.student_name or ''
            du_portal_number = structured.get('du_portal_form_number', '') or form.du_portal_form_number or ''
            
            # Extract documents from pages beyond the form
            extracted_docs = extract_supporting_documents(
                pdf_images=pages[FORM_PAGE_COUNT:],  # Only pages 5+
                form_id=form.id,
                student_name=student_name,
                du_portal_number=du_portal_number,
                db=db,
                upload_dir=upload_dir,
            )
            
            if extracted_docs:
                ocr_result['extracted_documents'] = extracted_docs
                logger.info(f"Form {form.id}: Extracted {len(extracted_docs)} supporting documents")
        except Exception as doc_error:
            logger.error(f"Error extracting supporting documents: {str(doc_error)}")
    
    return ocr_result

def _filter_form_labels(structured_data: Dict[str, Any], raw_text: str = ''):
    """
    Aggressively filter out form labels, field names, and instructions from extracted data.
    This prevents empty form labels from being extracted as field values.
    """
    # Comprehensive list of form labels, field names, and instructions that should NEVER be extracted as values
    FORM_LABELS_AND_INSTRUCTIONS = [
        # Name fields
        'name', 'student name', 'first name', 'middle name', 'surname', 'last name',
        'name in block letters', 'in block letters', 'block letters', 'name of the student',
        'name of student', 'full name', 'applicant name',
        
        # Date fields
        'date', 'date of birth', 'dob', 'dd', 'mm', 'yyyy', 'd d', 'm m', 'y y y y',
        'date of admission', 'admission date',
        
        # Gender/Category
        'gender', 'sex', 'category', 'admission category', 'please tick', 'tick',
        'male', 'female', 'transgender',  # These are valid values, but if they appear alone as labels, filter
        
        # Address fields
        'address', 'permanent address', 'correspondence address', 'local address',
        'address line 1', 'address line 2', 'address line 3',
        'permanent address line 1', 'permanent address line 2', 'permanent address line 3',
        'correspondence address line 1', 'correspondence address line 2', 'correspondence address line 3',
        'if different from permanent address', 'if different',
        
        # Location fields
        'state', 'city', 'pin', 'pincode', 'pin code', 'postal code',
        'permanent state', 'correspondence state', 'permanent pincode', 'correspondence pincode',
        'domicile', 'domicile state',
        
        # Contact fields
        'phone', 'phone number', 'mobile', 'mobile number', 'contact', 'contact number',
        'contact numbers', 'alternate phone', 'email', 'email id', 'email address',
        'emergency contact name', 'emergency contact phone',
        
        # Parent/Guardian fields
        "father's name", "father name", 'father', "mother's name", "mother name", 'mother',
        "guardian's name", "guardian name", 'guardian', 'local guardian',
        'father occupation', "father's occupation", 'mother occupation', "mother's occupation",
        'guardian occupation', "guardian's occupation",
        'father designation', "father's designation", 'mother designation', "mother's designation",
        'guardian designation', "guardian's designation",
        'father organization', "father's organization", 'mother organization', "mother's organization",
        'guardian organization', "guardian's organization",
        'father email', "father's email", 'mother email', "mother's email",
        'guardian email', "guardian's email",
        'father mobile', "father's mobile", 'mother mobile', "mother's mobile",
        'guardian mobile', "guardian's mobile",
        'father phone', "father's phone", 'mother phone', "mother's phone",
        'guardian phone', "guardian's phone",
        'father landline', "father's landline", 'mother landline', "mother's landline",
        'guardian landline', "guardian's landline",
        'father landline code', "father's landline code", 'mother landline code', "mother's landline code",
        'guardian landline code', "guardian's landline code",
        'father residential address', "father's residential address",
        'guardian residential address', "guardian's residential address",
        'guardian relation', "guardian's relation",
        
        # Personal information
        'nationality', 'religion', 'blood group', 'annual income', 'below poverty line',
        'minority category', 'aadhar', 'aadhar number', 'aadhaar', 'aadhaar number',
        'enrollment number', 'college roll no', 'roll number', 'application number',
        'du enrollment number', 'du portal form number', 'cuet score',
        
        # Academic fields
        'academic session', 'course', 'course applied', 'qualifying examination',
        'class x', 'class xii', '10th', '12th', 'tenth', 'twelfth',
        '10th board', '12th board', 'tenth board', 'twelfth board',
        '10th year', '12th year', 'tenth year', 'twelfth year',
        '10th percentage', '12th percentage', 'tenth percentage', 'twelfth percentage',
        '10th school', '12th school', 'tenth school', 'twelfth school',
        '10th roll number', '12th roll number', 'tenth roll number', 'twelfth roll number',
        '10th institution', '12th institution', 'tenth institution', 'twelfth institution',
        'previous qualification', 'graduation details', 'hindi studied upto',
        'hindi medium preference',
        
        # CUET fields
        'cuet subject', 'cuet total score', 'cuet score obtained', 'total cuet score',
        'cuet subject 1', 'cuet subject 2', 'cuet subject 3', 'cuet subject 4',
        'cuet subject 5', 'cuet subject 6',
        'cuet total score 1', 'cuet total score 2', 'cuet total score 3',
        'cuet total score 4', 'cuet total score 5', 'cuet total score 6',
        'cuet score obtained 1', 'cuet score obtained 2', 'cuet score obtained 3',
        'cuet score obtained 4', 'cuet score obtained 5', 'cuet score obtained 6',
        
        # Certificate fields
        'category certificate authority', 'category certificate number', 'category certificate date',
        'disability percentage', 'disability type', 'udid number',
        
        # Instructions and labels
        'please', 'please tick', 'please fill', 'please enter', 'please write',
        'please select', 'please specify', 'tick()', 'tick (', 'fill', 'enter',
        'write', 'select', 'specify', 'if applicable', 'if yes', 'if no',
        'if different', 'if employed', 'mandatory', 'optional', 'self attested',
        'attach', 'details', 'information', 'particulars', 'of the student',
        'of student', 'son of', 'daughter of', 'ward of',
        
        # Section headers
        'student data form', "student's data form", 'admission form',
        'personal information', 'personal details', 'academic details',
        'admission details', 'address details', 'contact details',
        "mother's occupational details", "father's occupational details",
        "local guardian's details", 'qualifying examination details',
        'cuet marks', 'cuet scores', 'category certificate details',
        'declaration', 'undertaking', 'documents required', 'document checklist',
        
        # Table headers
        'sl no', 'sl. no', 's.no', 's. no', 'serial number',
        'subjects', 'subject', 'score', 'total', 'marks', 'obtained',
        'total score', 'score obtained',
        
        # Common OCR artifacts from empty forms
        '()', '( )', '[]', '[ ]', '--', '- -', '___', '____',
    ]
    
    # Additional patterns that indicate form labels
    LABEL_PATTERNS = [
        r'^name\s*:?\s*$',  # Just "name" or "name:"
        r'^address\s*:?\s*$',
        r'^phone\s*:?\s*$',
        r'^email\s*:?\s*$',
        r'^date\s*:?\s*$',
        r'^gender\s*:?\s*$',
        r'^category\s*:?\s*$',
        r'^\d+\.\s*$',  # Just a number with dot (field numbering)
        r'^\([a-z]\)\s*$',  # Just (a), (b), etc.
    ]
    
    import re
    
    fields_to_remove = []
    for field, value in list(structured_data.items()):
        if not value or not isinstance(value, str):
            continue
            
        value_clean = str(value).strip()
        value_lower = value_clean.lower()
        
        # Check if value exactly matches a form label
        if value_lower in FORM_LABELS_AND_INSTRUCTIONS:
            fields_to_remove.append(field)
            continue
        
        # Check if value matches label patterns
        for pattern in LABEL_PATTERNS:
            if re.match(pattern, value_lower):
                fields_to_remove.append(field)
                break
        
        # Check if value is just a label with colon or common separators
        if value_clean.endswith(':') and len(value_clean) < 30:
            # Likely a label, not a value
            fields_to_remove.append(field)
            continue
        
        # Check if value contains only label words (no actual data)
        words = value_lower.split()
        if len(words) <= 3:
            # If all words are form labels, it's garbage
            if all(word in FORM_LABELS_AND_INSTRUCTIONS for word in words):
                fields_to_remove.append(field)
                continue
        
        # Check for common label phrases
        label_phrases = [
            'name in block letters', 'in block letters', 'block letters',
            'please tick', 'please fill', 'please enter',
            'if different', 'if applicable', 'if yes', 'if no',
            'of the student', 'of student', 'son of', 'daughter of',
        ]
        for phrase in label_phrases:
            if phrase in value_lower and len(value_clean) < 50:
                # If the value is mostly or entirely the label phrase, it's garbage
                if value_lower.replace(phrase, '').strip() == '' or len(value_lower.replace(phrase, '').strip()) < 3:
                    fields_to_remove.append(field)
                    break
    
    # Remove identified garbage fields
    for field in fields_to_remove:
        if field in structured_data:
            del structured_data[field]
            logger.debug(f"Filtered out form label as garbage: {field} = '{structured_data.get(field, '')}'")

def _perform_garbage_cleanup(structured_data: Dict[str, Any]):
    """Helper to run specific validators on fields"""
    
    def validate_name(v):
        if not v: return None
        v = str(v).strip()
        if len(v) > 50: return None
        words = v.lower().split()
        if len(words) > 3 and len(set(words)) < len(words) / 2: return None
        garbage_patterns = ['central board', 'secondary education', 'education central', 'board secondary']
        if any(g in v.lower() for g in garbage_patterns): return None
        return v
    
    def validate_enrollment(v):
        if not v: return None
        v = str(v).strip()
        if v.upper() in ['DATE', 'NO', 'NUMBER', 'CARL', 'NAME']: return None
        if len(v) < 4 or len(v) > 15: return None
        # Valid SRCC roll format: digit(s) + letters + digits (like 24BC156 or 2YBC102)
        import re
        if re.match(r'^\d+[A-Z]+\d+$', v.upper()):
            return v
        if v.isdigit() and len(v) == 4: # Pure year
            return None
        return v

    garbage_cleanup = {
        'annual_income': lambda v: v if v and (str(v).replace(',', '').isdigit() or 'LAKH' in str(v).upper() or 'BELOW' in str(v).upper()) else None,
        'blood_group': lambda v: v if v and v.upper().replace(' ', '') in ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'] else None,
        'nationality': lambda v: v if v and v.upper() in ['INDIAN', 'NEPALESE', 'BHUTANESE', 'TIBETAN'] else None,
        'religion': lambda v: v if v and v.upper() in ['HINDU', 'MUSLIM', 'SIKH', 'CHRISTIAN', 'JAIN', 'BUDDHIST', 'PARSI'] else None,
        'state': lambda v: v if v and len(v) > 1 and v.upper() not in ['OF', 'DOMICILE', 'NA', 'STATE'] else None,
        'course_applied': lambda v: v if v and ('B.COM' in v.upper() or 'B.A' in v.upper() or 'COMMERCE' in v.upper() or 'ECONOMICS' in v.upper()) else None,
        'aadhar_number': lambda v: v if v and len(str(v).replace(' ', '')) == 12 and str(v).replace(' ', '').isdigit() else None,
        'graduation_details': lambda v: v if v and 'honours' not in v.lower() and len(v) > 5 else None,
        'enrollment_number': validate_enrollment,
        'father_name': validate_name,
        'mother_name': validate_name,
        'guardian_name': validate_name,
    }

    for field, validator in garbage_cleanup.items():
        if field in structured_data:
            cleaned = validator(structured_data[field])
            if cleaned is None:
                del structured_data[field]
            else:
                structured_data[field] = cleaned

def _construct_student_name(structured_data: Dict[str, Any]):
    name_parts = []
    if structured_data.get('first_name'):
        name_parts.append(structured_data['first_name'])
    if structured_data.get('middle_name'):
        name_parts.append(structured_data['middle_name'])
    if structured_data.get('surname'):
        name_parts.append(structured_data['surname'])
    
    if name_parts:
        constructed_name = ' '.join(name_parts)
        if 'student_name' not in structured_data or not structured_data['student_name']:
            structured_data['student_name'] = constructed_name
        elif len(name_parts) >= 2 and len(constructed_name.split()) > len(structured_data['student_name'].split()):
            structured_data['student_name'] = constructed_name

def _final_garbage_check(structured_data: Dict[str, Any]):
    """
    Final aggressive garbage check to remove any remaining form labels or instructions
    """
    # Comprehensive list of garbage values that should never be in extracted data
    GARBAGE_VALUES = [
        # Instructions
        'tick()', 'tick', '()', 'please', 'fill', 'enter', 'write', 'select', 'specify',
        'please tick', 'please fill', 'please enter', 'please write', 'please select',
        'tick (', 'fill in', 'enter here', 'write here',
        
        # Field labels (standalone)
        'name', 'address', 'phone', 'email', 'date', 'gender', 'category', 'details',
        'occupation', 'designation', 'organization', 'state', 'city', 'pin', 'pincode',
        'father', 'mother', 'guardian', 'father name', 'mother name', 'guardian name',
        'first name', 'middle name', 'surname', 'last name',
        'permanent', 'correspondence', 'local', 'contact', 'mobile',
        'block letters', 'in block letters', 'name in block letters',
        'of the student', 'of student', 'son of', 'daughter of',
        
        # Common OCR artifacts
        '--', '- -', '___', '____', '[]', '[ ]', '( )', '()',
        'dd', 'mm', 'yyyy', 'd d', 'm m', 'y y y y',
        
        # Table/section headers
        'sl no', 'sl. no', 's.no', 'subjects', 'subject', 'score', 'total', 'marks',
        'student data form', 'admission form', 'personal information', 'academic details',
        'declaration', 'undertaking', 'documents required',
        
        # Empty/placeholder values
        'na', 'n/a', 'nil', 'none', 'not applicable', 'not available',
    ]
    
    # Patterns that indicate garbage
    import re
    GARBAGE_PATTERNS = [
        r'^name\s*:?\s*$',  # Just "name" or "name:"
        r'^address\s*:?\s*$',
        r'^phone\s*:?\s*$',
        r'^email\s*:?\s*$',
        r'^date\s*:?\s*$',
        r'^gender\s*:?\s*$',
        r'^category\s*:?\s*$',
        r'^\d+\.\s*$',  # Just a number with dot
        r'^\([a-z0-9]\)\s*$',  # Just (a), (1), etc.
        r'^please\s+',  # Starts with "please"
        r'^if\s+(different|applicable|yes|no)',  # Starts with "if different/applicable/etc"
        r'^tick\s*\(',
        r'^fill\s+',
        r'^enter\s+',
        r'^write\s+',
        r'^select\s+',
        r'^specify\s*$',
        r'^attach\s*$',
        r'^mandatory\s*$',
        r'^optional\s*$',
    ]
    
    fields_to_remove = []
    for field, value in structured_data.items():
        if not isinstance(value, str):
            continue
            
        value_clean = str(value).strip()
        if not value_clean:
            continue
            
        value_lower = value_clean.lower()
        
        # Check exact matches
        if value_lower in GARBAGE_VALUES:
            fields_to_remove.append(field)
            continue
        
        # Check patterns
        for pattern in GARBAGE_PATTERNS:
            if re.match(pattern, value_lower):
                fields_to_remove.append(field)
                break
        
        # Special checks for specific fields
        if field == 'gender' and value_lower in ['tick', 'please tick', 'tick()', '()']:
            fields_to_remove.append(field)
        elif field in ['student_name', 'first_name', 'middle_name', 'surname']:
            # Names should not be form labels
            if value_lower in ['name', 'first name', 'middle name', 'surname', 'last name',
                              'name in block letters', 'in block letters', 'block letters']:
                fields_to_remove.append(field)
        elif field in ['phone_number', 'mobile', 'alternate_phone']:
            # Phone should not be just "phone" or "mobile"
            if value_lower in ['phone', 'mobile', 'contact', 'phone number', 'mobile number']:
                fields_to_remove.append(field)
        elif field == 'email':
            # Email should not be just "email"
            if value_lower in ['email', 'email id', 'email address']:
                fields_to_remove.append(field)
        elif 'address' in field.lower():
            # Address should not be just "address"
            if value_lower in ['address', 'permanent address', 'correspondence address', 'local address']:
                fields_to_remove.append(field)
    
    # Remove identified garbage fields
    for field in fields_to_remove:
        if field in structured_data:
            del structured_data[field]
            logger.debug(f"Final garbage check removed: {field}")
