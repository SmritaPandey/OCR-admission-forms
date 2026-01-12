"""
Field Validator - Comprehensive validation rules for SRCC form fields.

Validates extracted field values and provides suggestions for fixes.
Implements:
1. Pattern-based validation (regex)
2. Range validation (dates, numbers)
3. Cross-field validation
4. Garbage detection
"""

import re
import logging
from datetime import datetime, date
from typing import Dict, Any, Optional, List, Tuple, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of field validation."""
    is_valid: bool
    field_name: str
    value: Any
    error_message: Optional[str] = None
    suggestion: Optional[str] = None
    confidence: float = 1.0


@dataclass
class FormValidationResult:
    """Result of validating an entire form."""
    is_valid: bool
    field_results: Dict[str, ValidationResult] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: Dict[str, str] = field(default_factory=dict)
    
    @property
    def error_count(self) -> int:
        return len(self.errors)
    
    @property
    def valid_fields(self) -> List[str]:
        return [name for name, result in self.field_results.items() if result.is_valid]
    
    @property
    def invalid_fields(self) -> List[str]:
        return [name for name, result in self.field_results.items() if not result.is_valid]


class FieldValidator:
    """
    Validates form field values against expected patterns and constraints.
    """
    
    # Regex patterns for field validation
    PATTERNS = {
        'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
        'phone_number': r'^[6-9]\d{9}$',
        'pincode': r'^\d{6}$',
        'aadhar_number': r'^\d{12}$',
        'date': r'^\d{2}/\d{2}/\d{4}$',
        'du_portal_form_number': r'^\d{12}$',
        'college_roll_no': r'^\d{1,2}[A-Z]{2,3}\d{2,4}$',
        'cuet_score': r'^\d{1,3}(\.\d+)?$',
        'year': r'^(19|20)\d{2}$',
    }
    
    # Valid options for categorical fields
    VALID_OPTIONS = {
        'gender': ['Male', 'Female', 'Transgender'],
        'category': ['GEN', 'OBC', 'SC', 'ST', 'EWS', 'PwD', 'Sports', 'Foreign', 'CW', 'KM', 'Others', 'ECA'],
        'course': ['B.COM.(H)', 'B.A.(H) ECO'],
        'blood_group': ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'],
        'nationality': ['Indian', 'Nepalese', 'Bhutanese', 'Tibetan'],
        'religion': ['Hindu', 'Muslim', 'Sikh', 'Christian', 'Jain', 'Buddhist', 'Parsi', 'Zoroastrian'],
        'hindi_studied_upto': ['VIII', 'X', 'XII', 'Never'],
        'below_poverty_line': ['Yes', 'No'],
        'hindi_medium': ['Yes', 'No'],
    }
    
    # Known garbage patterns that indicate extraction error
    GARBAGE_PATTERNS = [
        r'^please\s+tick',
        r'^if\s+different',
        r'^mandatory',
        r'^self\s+attested',
        r'^\d+\.\s*$',  # Just field numbers
        r'^name\s*$',
        r'^address\s*$',
        r'^phone\s*$',
        r'^email\s*$',
        r'^date\s*$',
        r'^gender\s*$',
        r'^category\s*$',
        r'^details\s*$',
        r'^occupation\s*$',
        r'^designation\s*$',
        r'^organization\s*$',
        r'^specify\s*$',
        r'^tick\s*\(',
        r'^fill\s+in',
        r'^write\s+',
        r'^enter\s+',
        r'^block\s+letters',
        r'^in\s+block\s+letters',
        r'^of\s+the\s+student',
        r'^of\s+student',
        r'^particulars',
        r'^information',
    ]
    
    # State pincode prefixes (for cross-validation)
    STATE_PINCODE_PREFIXES = {
        'Delhi': ['110'],
        'Haryana': ['121', '122', '123', '124', '125', '126', '127', '131', '132', '133', '134', '135', '136'],
        'Uttar Pradesh': ['20', '21', '22', '23', '24', '25', '26', '27', '28'],
        'Punjab': ['14', '15', '16'],
        'Rajasthan': ['30', '31', '32', '33', '34'],
        'Maharashtra': ['40', '41', '42', '43', '44'],
        'Karnataka': ['56', '57', '58', '59'],
        'Tamil Nadu': ['60', '61', '62', '63', '64'],
        'West Bengal': ['70', '71', '72', '73', '74'],
    }
    
    def __init__(self):
        self._custom_validators: Dict[str, Callable] = {}
        self._setup_validators()
    
    def _setup_validators(self):
        """Set up custom validator functions for specific fields."""
        self._custom_validators = {
            'date_of_birth': self._validate_date_of_birth,
            'date_of_admission': self._validate_date_of_admission,
            'student_name': self._validate_name,
            'father_name': self._validate_name,
            'mother_name': self._validate_name,
            'guardian_name': self._validate_name,
            'email': self._validate_email,
            'phone_number': self._validate_phone,
            'mother_phone': self._validate_phone,
            'father_phone': self._validate_phone,
            'guardian_phone': self._validate_phone,
            'pincode': self._validate_pincode,
            'aadhar_number': self._validate_aadhar,
            'cuet_score': self._validate_cuet_score,
            'annual_income': self._validate_income,
            'year_of_passing': self._validate_year,
        }
    
    def validate_field(self, field_name: str, value: Any) -> ValidationResult:
        """
        Validate a single field value.
        
        Args:
            field_name: Name of the field
            value: Value to validate
            
        Returns:
            ValidationResult with validation status and details
        """
        if value is None or str(value).strip() == '':
            return ValidationResult(
                is_valid=True,  # Empty is valid (not required check)
                field_name=field_name,
                value=value
            )
        
        value_str = str(value).strip()
        
        # Check for garbage patterns first
        if self._is_garbage(value_str):
            return ValidationResult(
                is_valid=False,
                field_name=field_name,
                value=value,
                error_message=f"Value appears to be a form label, not actual data",
                suggestion=None,
                confidence=0.0
            )
        
        # Use custom validator if available
        if field_name in self._custom_validators:
            return self._custom_validators[field_name](field_name, value_str)
        
        # Check against valid options for categorical fields
        if field_name in self.VALID_OPTIONS:
            return self._validate_categorical(field_name, value_str)
        
        # Check against pattern if available
        if field_name in self.PATTERNS:
            return self._validate_pattern(field_name, value_str)
        
        # Default: valid if has content
        return ValidationResult(
            is_valid=len(value_str) >= 2,
            field_name=field_name,
            value=value,
            confidence=0.8
        )
    
    def validate_form(self, data: Dict[str, Any]) -> FormValidationResult:
        """
        Validate all fields in a form.
        
        Args:
            data: Dictionary of field names to values
            
        Returns:
            FormValidationResult with all validation details
        """
        result = FormValidationResult(is_valid=True)
        
        # Validate each field
        for field_name, value in data.items():
            # Skip metadata fields
            if field_name.startswith('_'):
                continue
            
            field_result = self.validate_field(field_name, value)
            result.field_results[field_name] = field_result
            
            if not field_result.is_valid:
                result.is_valid = False
                result.errors.append(f"{field_name}: {field_result.error_message}")
                if field_result.suggestion:
                    result.suggestions[field_name] = field_result.suggestion
        
        # Run cross-field validation
        cross_results = self._validate_cross_fields(data)
        for warning in cross_results.get('warnings', []):
            result.warnings.append(warning)
        for error in cross_results.get('errors', []):
            result.errors.append(error)
            result.is_valid = False
        
        return result
    
    def _is_garbage(self, value: str) -> bool:
        """Check if value matches known garbage patterns."""
        value_lower = value.lower().strip()
        
        for pattern in self.GARBAGE_PATTERNS:
            if re.match(pattern, value_lower, re.IGNORECASE):
                return True
        
        return False
    
    def _validate_pattern(self, field_name: str, value: str) -> ValidationResult:
        """Validate value against a regex pattern."""
        pattern = self.PATTERNS.get(field_name)
        if not pattern:
            return ValidationResult(is_valid=True, field_name=field_name, value=value)
        
        if re.match(pattern, value, re.IGNORECASE):
            return ValidationResult(
                is_valid=True,
                field_name=field_name,
                value=value,
                confidence=0.95
            )
        else:
            return ValidationResult(
                is_valid=False,
                field_name=field_name,
                value=value,
                error_message=f"Value '{value}' does not match expected format",
                confidence=0.0
            )
    
    def _validate_categorical(self, field_name: str, value: str) -> ValidationResult:
        """Validate value against valid options."""
        options = self.VALID_OPTIONS.get(field_name, [])
        
        # Check exact match
        if value in options:
            return ValidationResult(
                is_valid=True,
                field_name=field_name,
                value=value,
                confidence=1.0
            )
        
        # Check case-insensitive match
        value_upper = value.upper()
        for option in options:
            if option.upper() == value_upper:
                return ValidationResult(
                    is_valid=True,
                    field_name=field_name,
                    value=option,  # Return correctly cased value
                    suggestion=option,
                    confidence=0.9
                )
        
        # Check partial match
        for option in options:
            if option.upper() in value_upper or value_upper in option.upper():
                return ValidationResult(
                    is_valid=False,
                    field_name=field_name,
                    value=value,
                    error_message=f"Partial match found",
                    suggestion=option,
                    confidence=0.5
                )
        
        return ValidationResult(
            is_valid=False,
            field_name=field_name,
            value=value,
            error_message=f"Invalid {field_name}: '{value}'. Valid options: {', '.join(options)}",
            confidence=0.0
        )
    
    def _validate_date_of_birth(self, field_name: str, value: str) -> ValidationResult:
        """Validate date of birth is within reasonable range."""
        try:
            # Parse date
            if '/' in value:
                parts = value.split('/')
                if len(parts) == 3:
                    day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
                else:
                    return ValidationResult(
                        is_valid=False, field_name=field_name, value=value,
                        error_message="Invalid date format. Expected DD/MM/YYYY"
                    )
            else:
                return ValidationResult(
                    is_valid=False, field_name=field_name, value=value,
                    error_message="Invalid date format. Expected DD/MM/YYYY"
                )
            
            # Validate ranges
            if day < 1 or day > 31:
                return ValidationResult(
                    is_valid=False, field_name=field_name, value=value,
                    error_message=f"Invalid day: {day}"
                )
            if month < 1 or month > 12:
                return ValidationResult(
                    is_valid=False, field_name=field_name, value=value,
                    error_message=f"Invalid month: {month}"
                )
            
            # Check year is reasonable for a student (born 1990-2010)
            if year < 1990 or year > 2010:
                return ValidationResult(
                    is_valid=False, field_name=field_name, value=value,
                    error_message=f"Year {year} seems unlikely for a college student",
                    confidence=0.3
                )
            
            return ValidationResult(
                is_valid=True, field_name=field_name, value=value,
                confidence=0.95
            )
            
        except (ValueError, IndexError) as e:
            return ValidationResult(
                is_valid=False, field_name=field_name, value=value,
                error_message=f"Could not parse date: {e}"
            )
    
    def _validate_date_of_admission(self, field_name: str, value: str) -> ValidationResult:
        """Validate admission date is recent."""
        try:
            if '/' in value:
                parts = value.split('/')
                if len(parts) == 3:
                    day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
                    
                    # Admission should be in last 2 years
                    current_year = datetime.now().year
                    if year < current_year - 2 or year > current_year + 1:
                        return ValidationResult(
                            is_valid=False, field_name=field_name, value=value,
                            error_message=f"Admission year {year} seems incorrect"
                        )
                    
                    return ValidationResult(
                        is_valid=True, field_name=field_name, value=value,
                        confidence=0.9
                    )
            
            return ValidationResult(
                is_valid=False, field_name=field_name, value=value,
                error_message="Invalid date format"
            )
            
        except (ValueError, IndexError):
            return ValidationResult(
                is_valid=False, field_name=field_name, value=value,
                error_message="Could not parse date"
            )
    
    def _validate_name(self, field_name: str, value: str) -> ValidationResult:
        """Validate name doesn't contain garbage."""
        # Check for garbage patterns
        if self._is_garbage(value):
            return ValidationResult(
                is_valid=False, field_name=field_name, value=value,
                error_message="Value appears to be a form label"
            )
        
        # Name should contain only letters and spaces
        if not re.match(r'^[A-Za-z\s]+$', value):
            return ValidationResult(
                is_valid=False, field_name=field_name, value=value,
                error_message="Name should contain only letters and spaces"
            )
        
        # Name should have at least 2 characters
        if len(value.strip()) < 2:
            return ValidationResult(
                is_valid=False, field_name=field_name, value=value,
                error_message="Name too short"
            )
        
        # Names with only one very short word might be incomplete
        words = value.strip().split()
        if len(words) == 1 and len(words[0]) < 3:
            return ValidationResult(
                is_valid=True, field_name=field_name, value=value,
                error_message="Name might be incomplete",
                confidence=0.5
            )
        
        return ValidationResult(
            is_valid=True, field_name=field_name, value=value,
            confidence=0.9 if len(words) >= 2 else 0.7
        )
    
    def _validate_email(self, field_name: str, value: str) -> ValidationResult:
        """Validate email format."""
        value = value.lower().strip()
        
        if not re.match(self.PATTERNS['email'], value):
            return ValidationResult(
                is_valid=False, field_name=field_name, value=value,
                error_message="Invalid email format"
            )
        
        return ValidationResult(
            is_valid=True, field_name=field_name, value=value,
            confidence=0.95
        )
    
    def _validate_phone(self, field_name: str, value: str) -> ValidationResult:
        """Validate Indian phone number."""
        # Remove any non-digit characters
        digits = re.sub(r'\D', '', value)
        
        # Should be 10 digits starting with 6-9
        if len(digits) != 10:
            return ValidationResult(
                is_valid=False, field_name=field_name, value=value,
                error_message=f"Phone number should be 10 digits, got {len(digits)}"
            )
        
        if digits[0] not in '6789':
            return ValidationResult(
                is_valid=False, field_name=field_name, value=value,
                error_message="Indian mobile numbers start with 6, 7, 8, or 9"
            )
        
        return ValidationResult(
            is_valid=True, field_name=field_name, value=digits,
            confidence=0.95
        )
    
    def _validate_pincode(self, field_name: str, value: str) -> ValidationResult:
        """Validate Indian pincode."""
        digits = re.sub(r'\D', '', value)
        
        if len(digits) != 6:
            return ValidationResult(
                is_valid=False, field_name=field_name, value=value,
                error_message=f"Pincode should be 6 digits, got {len(digits)}"
            )
        
        # First digit should be 1-8
        if digits[0] not in '12345678':
            return ValidationResult(
                is_valid=False, field_name=field_name, value=value,
                error_message="Invalid pincode - first digit should be 1-8"
            )
        
        return ValidationResult(
            is_valid=True, field_name=field_name, value=digits,
            confidence=0.95
        )
    
    def _validate_aadhar(self, field_name: str, value: str) -> ValidationResult:
        """Validate Aadhar number."""
        digits = re.sub(r'\D', '', value)
        
        if len(digits) != 12:
            return ValidationResult(
                is_valid=False, field_name=field_name, value=value,
                error_message=f"Aadhar should be 12 digits, got {len(digits)}"
            )
        
        # First digit cannot be 0 or 1
        if digits[0] in '01':
            return ValidationResult(
                is_valid=False, field_name=field_name, value=value,
                error_message="Aadhar number cannot start with 0 or 1"
            )
        
        return ValidationResult(
            is_valid=True, field_name=field_name, value=digits,
            confidence=0.95
        )
    
    def _validate_cuet_score(self, field_name: str, value: str) -> ValidationResult:
        """Validate CUET score is in valid range."""
        try:
            # Remove any non-numeric characters except decimal point
            cleaned = re.sub(r'[^\d.]', '', value)
            score = float(cleaned)
            
            # CUET score typically 0-800 or percentage
            if score < 0 or score > 1000:
                return ValidationResult(
                    is_valid=False, field_name=field_name, value=value,
                    error_message=f"CUET score {score} seems invalid"
                )
            
            return ValidationResult(
                is_valid=True, field_name=field_name, value=cleaned,
                confidence=0.9
            )
            
        except (ValueError, TypeError):
            return ValidationResult(
                is_valid=False, field_name=field_name, value=value,
                error_message="Could not parse CUET score as number"
            )
    
    def _validate_income(self, field_name: str, value: str) -> ValidationResult:
        """Validate annual income is reasonable."""
        try:
            # Remove currency symbols and commas
            cleaned = re.sub(r'[^\d]', '', value)
            if not cleaned:
                return ValidationResult(
                    is_valid=False, field_name=field_name, value=value,
                    error_message="Could not parse income value"
                )
            
            income = int(cleaned)
            
            # Check reasonable range (10,000 to 10 crore)
            if income < 10000 or income > 100000000:
                return ValidationResult(
                    is_valid=False, field_name=field_name, value=value,
                    error_message=f"Annual income {income} seems unusual",
                    confidence=0.5
                )
            
            return ValidationResult(
                is_valid=True, field_name=field_name, value=str(income),
                confidence=0.9
            )
            
        except (ValueError, TypeError):
            return ValidationResult(
                is_valid=False, field_name=field_name, value=value,
                error_message="Could not parse income value"
            )
    
    def _validate_year(self, field_name: str, value: str) -> ValidationResult:
        """Validate year is reasonable."""
        try:
            year = int(re.sub(r'\D', '', value))
            current_year = datetime.now().year
            
            # Year should be within last 10 years
            if year < current_year - 10 or year > current_year:
                return ValidationResult(
                    is_valid=False, field_name=field_name, value=value,
                    error_message=f"Year {year} seems incorrect for recent passing"
                )
            
            return ValidationResult(
                is_valid=True, field_name=field_name, value=str(year),
                confidence=0.95
            )
            
        except (ValueError, TypeError):
            return ValidationResult(
                is_valid=False, field_name=field_name, value=value,
                error_message="Could not parse year"
            )
    
    def _validate_cross_fields(self, data: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Validate fields against each other for consistency.
        
        Returns dict with 'errors' and 'warnings' lists.
        """
        results = {'errors': [], 'warnings': []}
        
        # Check: If category is SC/ST, certificate fields should be filled
        category = data.get('category', '').upper()
        if category in ['SC', 'ST', 'OBC', 'EWS', 'PWD']:
            if not data.get('certificate_number') and not data.get('certificate_authority'):
                results['warnings'].append(
                    f"Category is {category} but certificate details are missing"
                )
        
        # Check: State and pincode should match
        state = data.get('state', data.get('permanent_state', '')).lower()
        pincode = data.get('pincode', '')
        if state and pincode and len(pincode) >= 3:
            for state_name, prefixes in self.STATE_PINCODE_PREFIXES.items():
                if state_name.lower() in state:
                    if not any(pincode.startswith(prefix) for prefix in prefixes):
                        results['warnings'].append(
                            f"Pincode {pincode} doesn't match state {state_name}"
                        )
                    break
        
        # Check: Father and mother names should be different
        father = data.get('father_name', '').lower()
        mother = data.get('mother_name', '').lower()
        if father and mother and father == mother:
            results['errors'].append(
                "Father's name and mother's name are the same"
            )
        
        # Check: Student name should not equal parent names
        student = data.get('student_name', '').lower()
        if student:
            if student == father:
                results['warnings'].append(
                    "Student name is same as father's name"
                )
            if student == mother:
                results['warnings'].append(
                    "Student name is same as mother's name"
                )
        
        return results


# Convenience functions
def validate_form_data(data: Dict[str, Any]) -> FormValidationResult:
    """Validate form data and return detailed results."""
    validator = FieldValidator()
    return validator.validate_form(data)


def validate_field(field_name: str, value: Any) -> ValidationResult:
    """Validate a single field."""
    validator = FieldValidator()
    return validator.validate_field(field_name, value)


def is_garbage_value(value: str) -> bool:
    """Check if a value appears to be garbage/form label."""
    validator = FieldValidator()
    return validator._is_garbage(value)
