"""
Utility to automatically apply extracted structured data to AdmissionForm objects.
Ensures all fields are mapped correctly from extractor output to database model.
Includes intelligent field mapping and cross-field population.
"""
from typing import Dict, Any
from backend.database import AdmissionForm


# Field mapping: maps extractor field names to database field names
# This handles cases where extractor produces different field names
FIELD_MAPPING = {
    # Legacy/alternative field names -> standard field names
    'application_number': 'du_portal_form_number',  # Some extractors use application_number
    'enrollment_number': 'college_roll_no',  # Some extractors use enrollment_number
    'admission_date': 'date_of_admission',  # Some extractors use admission_date
    'course_applied': 'course',  # Some extractors use course_applied
    # Class XII field mappings (extractor outputs these, need to map to database fields)
    'year_of_passing': 'twelfth_year',
    'board_university': 'twelfth_board',
    'exam_roll_no': 'twelfth_roll_number',
    'institution_last_attended': 'twelfth_institution',
    # DU Enrollment mapping
    'du_enrollment_number': 'du_enrollment_number',  # Keep as is (duplicate to ensure it's applied)
    # Address line mappings - populate individual lines from combined address if available
    # These will be handled separately in the apply function
}

# Cross-field population rules: if field A is set but field B is empty, populate B from A
CROSS_FIELD_RULES = [
    # Phone/Mobile cross-population
    ('mother_phone', 'mother_mobile'),  # If mother_phone exists but mother_mobile doesn't, use mother_phone
    ('father_phone', 'father_mobile'),  # If father_phone exists but father_mobile doesn't, use father_phone
    ('guardian_phone', 'guardian_mobile'),  # If guardian_phone exists but guardian_mobile doesn't, use guardian_phone
    # Address cross-population
    ('permanent_address', 'correspondence_address'),  # If permanent exists but correspondence doesn't, copy it
    ('permanent_state', 'correspondence_state'),  # If permanent state exists but correspondence doesn't, copy it
    ('permanent_pincode', 'correspondence_pincode'),  # If permanent pincode exists but correspondence doesn't, copy it
    # PIN code cross-population (pincode -> permanent_pincode if permanent_pincode not set)
    ('pincode', 'permanent_pincode'),  # If pincode exists but permanent_pincode doesn't, use pincode
    ('permanent_pincode', 'pincode'),  # If permanent_pincode exists but pincode doesn't, use permanent_pincode
    ('pincode', 'correspondence_pincode'),  # If pincode exists but correspondence_pincode doesn't, use pincode
    # State cross-population
    ('permanent_state', 'state'),  # If permanent_state exists but state doesn't, use permanent_state
    ('state', 'permanent_state'),  # If state exists but permanent_state doesn't, use state
    # Category sync
    ('admission_category', 'category'),  # Sync admission_category to category
    ('category', 'admission_category'),  # Sync category to admission_category
    # Course sync
    ('course', 'course_applied'),  # Sync course to course_applied
    ('course_applied', 'course'),  # Sync course_applied to course
    # Roll number sync
    ('college_roll_no', 'enrollment_number'),  # Sync college_roll_no to enrollment_number
    ('enrollment_number', 'college_roll_no'),  # Sync enrollment_number to college_roll_no
]


def apply_structured_data_to_form(form: AdmissionForm, structured_data: Dict[str, Any]) -> int:
    """
    Apply all fields from structured_data to the form object intelligently.
    Only sets fields that exist in the AdmissionForm model.
    Includes field mapping and cross-field population.
    Returns the number of fields successfully set.
    """
    if not structured_data:
        return 0
    
    # Get all valid column names from the AdmissionForm model
    form_columns = {column.name for column in AdmissionForm.__table__.columns}
    
    # Step 1: Map field names using FIELD_MAPPING
    # IMPORTANT: Keep original fields AND create mapped versions
    mapped_data = {}
    for field_name, value in structured_data.items():
        # Skip internal/metadata fields
        if field_name.startswith('_'):
            continue
        
        # Skip empty values
        if value is None or (isinstance(value, str) and not value.strip()):
            continue
            
        # First, check if field exists directly in model - keep it
        if field_name in form_columns:
            mapped_data[field_name] = value
        # Also check if there's a mapping - create mapped version
        elif field_name in FIELD_MAPPING:
            mapped_field = FIELD_MAPPING[field_name]
            if mapped_field in form_columns:
                # IMPORTANT: Always map to the mapped field if it exists in model
                # This ensures fields like year_of_passing -> twelfth_year are applied
                # Only skip if the mapped field already exists in mapped_data (to avoid overwriting)
                if mapped_field not in mapped_data:
                    mapped_data[mapped_field] = value
                    print(f"[Field Applier] Mapped {field_name} -> {mapped_field}")
    # If field doesn't exist in model and has no mapping, skip it (logged in debug)
    
    # Step 2: Apply fields with validation
    fields_set = 0
    applied_fields = set()
    
    # Debug: Log what fields we're trying to apply
    print(f"[Field Applier] Attempting to apply {len(mapped_data)} fields to form")
    
    for field_name, value in mapped_data.items():
        # Skip if field doesn't exist in the model (shouldn't happen, but safety check)
        if field_name not in form_columns:
            continue
        
        # Skip empty values
        if value is None:
            continue
        
        # Convert to string and check if empty
        value_str = str(value).strip()
        if not value_str:
            continue
        
        # Skip if it's a dict/list and empty
        if isinstance(value, (dict, list)) and len(value) == 0:
            continue
        
        # Special handling for name fields - reject if it contains "block letters"
        # But be less aggressive - only reject if it's clearly the label itself
        if field_name in ['student_name', 'mother_name', 'father_name', 'guardian_name']:
            value_lower = value_str.lower().strip()
            # Only reject if it's exactly the label text or very short label-like text
            if value_lower in ['name in block letters', 'in block letters', 'block letters', 'name', 'block', 'letters']:
                continue  # Skip this field - it's a label
            # Reject if it's very short (1-2 words) and contains "block letters"
            elif len(value_lower.split()) <= 2:
                if 'block letters' in value_lower or 'in block letters' in value_lower:
                    continue  # Skip this field - it's likely a label
            # Otherwise, trust the extractor - it already filtered this
        
        try:
            # Set the attribute
            setattr(form, field_name, value_str)
            applied_fields.add(field_name)
            fields_set += 1
            print(f"[Field Applier] ✓ Set {field_name} = {value_str[:50]}...")
        except Exception as e:
            # Skip fields that can't be set (relationships, etc.)
            print(f"[Field Applier] ✗ Warning: Could not set {field_name}: {e}")
            continue
    
    # Step 3: Apply cross-field population rules
    for source_field, target_field in CROSS_FIELD_RULES:
        # Only apply if both fields exist in model
        if source_field not in form_columns or target_field not in form_columns:
            continue
        
        # Only populate if source is set, target is empty, and source was actually applied
        source_value = getattr(form, source_field, None)
        target_value = getattr(form, target_field, None)
        
        if source_value and not target_value and source_field in applied_fields:
            try:
                setattr(form, target_field, str(source_value).strip())
                fields_set += 1
                print(f"[Field Applier] ✓ Cross-populated {target_field} from {source_field}")
            except Exception as e:
                print(f"[Field Applier] ✗ Warning: Could not cross-populate {target_field} from {source_field}: {e}")
        
    # Step 4: Handle address line fields - split combined addresses into line fields if needed
    # Populate address_line1, address_line2, address_line3 from combined address
    address_fields = [
        ('permanent_address', 'permanent_address_line1', 'permanent_address_line2', 'permanent_address_line3'),
        ('correspondence_address', 'correspondence_address_line1', 'correspondence_address_line2', 'correspondence_address_line3'),
    ]
    
    for combined_field, line1_field, line2_field, line3_field in address_fields:
        if combined_field in form_columns:
            combined_value = getattr(form, combined_field, None)
            if combined_value and combined_value.strip():
                # Only split if line fields are empty
                line1_value = getattr(form, line1_field, None) if line1_field in form_columns else None
                if not line1_value and line1_field in form_columns:
                    # Split address by newlines or commas (take first 3 parts)
                    lines = [line.strip() for line in str(combined_value).replace('\n', ',').split(',') if line.strip()]
                    if len(lines) >= 1 and line1_field in form_columns:
                        try:
                            setattr(form, line1_field, lines[0])
                            fields_set += 1
                        except: pass
                    if len(lines) >= 2 and line2_field in form_columns:
                        try:
                            setattr(form, line2_field, lines[1])
                            fields_set += 1
                        except: pass
                    if len(lines) >= 3 and line3_field in form_columns:
                        try:
                            setattr(form, line3_field, lines[2])
                            fields_set += 1
                        except: pass
    
    print(f"[Field Applier] ✓ Successfully applied {fields_set} fields to form")
    return fields_set
