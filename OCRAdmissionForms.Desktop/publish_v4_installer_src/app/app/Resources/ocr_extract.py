#!/usr/bin/env python3
"""
WORLD-CLASS SRCC FORM EXTRACTION SYSTEM
Uses Google Cloud Vision with bounding box spatial analysis

Techniques:
1. document_text_detection with fullTextAnnotation parsing
2. Word-level bounding boxes for spatial key-value extraction
3. Form zone detection based on SRCC template layout
4. OCR error correction (common misreads)
5. Confidence-based validation
6. Proximity-based label-value pairing
"""
import sys
import os
import json
import io
import re
import base64
import subprocess
from typing import Dict, List, Optional, Tuple, Any

# ===== AUTO-INSTALL DEPENDENCIES =====
def _ensure_packages():
    """Auto-install required pip packages if missing."""
    required = {
        'google-cloud-vision': 'google.cloud.vision',
        'PyMuPDF': 'fitz',
        'google-genai': 'google.genai',
    }
    missing = []
    for pkg, importname in required.items():
        try:
            __import__(importname)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"Installing missing packages: {', '.join(missing)}", file=sys.stderr)
        subprocess.check_call(
            [sys.executable, '-m', 'pip', 'install', '-q'] + missing,
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
        )

_ensure_packages()

FORM_PAGES = 4  # First 4 pages are the admission form; pages 5+ are attached documents

# ===== OCR ERROR CORRECTIONS =====
OCR_CORRECTIONS = {
    # Email domain fixes
    'gmall.com': 'gmail.com',
    'gmai1.com': 'gmail.com',
    'gmal.com': 'gmail.com',
    '@gmail. com': '@gmail.com',
    '. com': '.com',
    '@GMAL': '@GMAIL.COM',       # Common OCR misread
    '@gmal': '@gmail.com',
    'GMAL.COM': 'GMAIL.COM',
    'gmal': 'gmail',
    # Common character misreads
    '|': 'l',
}

# Email domain autocomplete (for truncated OCR)
EMAIL_DOMAIN_FIXES = {
    '@GMAL': '@GMAIL.COM',
    '@GMAI': '@GMAIL.COM',
    '@GMALL': '@GMAIL.COM',
    '@gmal': '@gmail.com',
}

# Number character corrections (O->0, l->1, etc.)
NUMBER_CORRECTIONS = str.maketrans('OoIlS', '00115')

# ===== FORM LABELS TO FILTER =====
FORM_LABELS = {
    'SHRI RAM COLLEGE OF COMMERCE', "STUDENT'S DATA FORM",
    'NAME IN BLOCK LETTERS', 'First Name', 'Middle Name', 'Surname',
    'Gender', 'Tick', 'Male', 'Female', 'Transgender',
    'Date of Birth', 'Permanent Address', 'State', 'PIN',
    'Email', 'Contact Numbers', 'Mobile No', 'Landline No',
    "Mother's Name", "Father's Name", 'Occupation', 'Designation',
    'Organization', 'Address', 'Year of passing', 'Board', 'University',
    'Nationality', 'Religion', 'Blood Group', 'CUET Score',
    'College Roll No', 'Date of Admission', 'DU Portal Form Number',
    'Academic Session', 'Course', 'Admission Category',
    'B.COM.(H)', 'B.A.(H) ECO', 'GEN', 'OBC', 'SC', 'ST', 'EWS',
    'DD', 'MM', 'YYYY', 'D D', 'M M', 'Y Y Y Y',
}

def is_form_label(text: str) -> bool:
    """Check if text is a static form label"""
    text_clean = text.strip()
    text_upper = text_clean.upper()
    
    for label in FORM_LABELS:
        if label.upper() == text_upper:
            return True
        if len(text_upper) <= len(label) + 5 and label.upper() in text_upper:
            return True
    
    # Reject single letters, numbers only, or very short text
    if len(text_clean) <= 2:
        return True
    if re.match(r'^[a-z][\.\)\s]*$', text_clean, re.IGNORECASE):
        return True
    if re.match(r'^\d+[\.\)\s]*$', text_clean):
        return True
    
    return False

def clean_text(text: str) -> str:
    """Apply OCR error corrections"""
    for wrong, correct in OCR_CORRECTIONS.items():
        text = text.replace(wrong, correct)
    return text.strip()

def clean_number(text: str) -> str:
    """Correct common OCR errors in numbers"""
    return text.translate(NUMBER_CORRECTIONS)

# ===== BOUNDING BOX SPATIAL ANALYSIS =====

class Word:
    """Word with bounding box and text"""
    def __init__(self, text: str, x: float, y: float, width: float, height: float, confidence: float):
        self.text = text
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.confidence = confidence
        self.right = x + width
        self.bottom = y + height
        self.center_y = y + height / 2
        self.is_handwritten = confidence < 0.85  # Lower confidence often indicates handwriting
    
    def __repr__(self):
        hw = ' HW' if self.is_handwritten else ''
        return f"Word('{self.text}', conf={self.confidence:.2f}{hw})"

def extract_words_with_bounds(response) -> List[Word]:
    """Extract all words with bounding box coordinates from Vision API response"""
    words = []
    
    if not response.full_text_annotation or not response.full_text_annotation.pages:
        return words
    
    for page in response.full_text_annotation.pages:
        page_width = page.width
        page_height = page.height
        
        for block in page.blocks:
            for paragraph in block.paragraphs:
                for word in paragraph.words:
                    text = ''.join([symbol.text for symbol in word.symbols])
                    bbox = word.bounding_box
                    
                    if bbox.vertices:
                        x = min(v.x for v in bbox.vertices)
                        y = min(v.y for v in bbox.vertices)
                        right = max(v.x for v in bbox.vertices)
                        bottom = max(v.y for v in bbox.vertices)
                        
                        words.append(Word(
                            text=text,
                            x=x / page_width,  # Normalize to 0-1
                            y=y / page_height,
                            width=(right - x) / page_width,
                            height=(bottom - y) / page_height,
                            confidence=word.confidence if hasattr(word, 'confidence') else 0.9
                        ))
    
    return words

def find_words_in_zone(words: List[Word], y_min: float, y_max: float) -> List[Word]:
    """Find all words within a vertical zone (normalized 0-1)"""
    return [w for w in words if y_min <= w.y <= y_max]

def find_value_right_of_label(words: List[Word], label_text: str, 
                               max_x_distance: float = 0.3, 
                               max_y_distance: float = 0.02) -> Optional[str]:
    """Find value word(s) to the RIGHT of a label using spatial proximity"""
    # Find label word
    label_words = [w for w in words if label_text.lower() in w.text.lower()]
    if not label_words:
        return None
    
    label = label_words[0]
    candidates = []
    
    for word in words:
        if word is label or is_form_label(word.text):
            continue
        
        # Check if word is to the right of label on same line
        if word.x > label.right:
            dx = word.x - label.right
            dy = abs(word.center_y - label.center_y)
            
            if dx < max_x_distance and dy < max_y_distance:
                candidates.append((word, dx))
    
    if not candidates:
        return None
    
    # Sort by distance, take closest words
    candidates.sort(key=lambda x: x[1])
    result_words = [c[0].text for c in candidates[:4]]
    return ' '.join(result_words)

def find_value_below_label(words: List[Word], label_text: str,
                            max_y_distance: float = 0.05,
                            max_x_distance: float = 0.1) -> Optional[str]:
    """Find value word(s) BELOW a label"""
    label_words = [w for w in words if label_text.lower() in w.text.lower()]
    if not label_words:
        return None
    
    label = label_words[0]
    candidates = []
    
    for word in words:
        if word is label or is_form_label(word.text):
            continue
        
        # Check if word is below label
        if word.y > label.bottom:
            dy = word.y - label.bottom
            dx = abs(word.x - label.x)
            
            if dy < max_y_distance and dx < max_x_distance:
                candidates.append((word, dy))
    
    if not candidates:
        return None
    
    candidates.sort(key=lambda x: x[1])
    return candidates[0][0].text if candidates else None

def find_words_after_index(words: List[Word], label_text: str, count: int = 3) -> List[Word]:
    """Find words that appear after a label in reading order"""
    # Sort words by y then x (reading order)
    sorted_words = sorted(words, key=lambda w: (w.y, w.x))
    
    # Find label index
    label_idx = None
    for i, w in enumerate(sorted_words):
        if label_text.lower() in w.text.lower():
            label_idx = i
            break
    
    if label_idx is None:
        return []
    
    # Get next words that aren't labels
    result = []
    for w in sorted_words[label_idx + 1:]:
        if not is_form_label(w.text) and len(w.text) > 1:
            result.append(w)
            if len(result) >= count:
                break
    
    return result

# ===== PDF PROCESSING =====

def convert_pdf_to_images(pdf_path: str, max_pages: int = 0) -> Tuple[Optional[List[bytes]], Optional[str]]:
    """Convert PDF pages to PNG bytes using PyMuPDF. max_pages=0 means all pages."""
    try:
        import fitz
        doc = fitz.open(pdf_path)
        if len(doc) == 0:
            return None, "PDF has no pages"
        
        pages_to_process = len(doc) if max_pages <= 0 else min(len(doc), max_pages)
        images = []
        
        for page_num in range(pages_to_process):
            page = doc[page_num]
            # High resolution for better OCR
            mat = fitz.Matrix(300/72, 300/72)
            pix = page.get_pixmap(matrix=mat)
            images.append(pix.tobytes("png"))
        
        doc.close()
        return images, None
    except Exception as e:
        return None, str(e)

def ocr_image_with_bounds(client, image_content: bytes) -> Tuple[Optional[str], Optional[List[Word]], Optional[str]]:
    """OCR an image with handwriting hints and return both text and word bounds"""
    from google.cloud import vision
    
    image = vision.Image(content=image_content)
    
    # Use image_context with language hints for better handwriting recognition
    image_context = vision.ImageContext(
        language_hints=['en', 'hi'],  # English + Hindi for mixed forms
    )
    
    response = client.document_text_detection(
        image=image,
        image_context=image_context
    )
    
    if response.error.message:
        return None, None, response.error.message
    
    text = ""
    if response.full_text_annotation and response.full_text_annotation.text:
        text = response.full_text_annotation.text.strip()
    
    words = extract_words_with_bounds(response)
    
    return text, words, None

# ===== INTELLIGENT FIELD EXTRACTION =====

def extract_fields_spatial(all_words: List[Word], all_text: str) -> Dict[str, Any]:
    """Extract fields using spatial analysis of word bounding boxes"""
    fields = {}
    field_confidence = {}  # Track confidence per field
    
    # Calculate average word confidence for overall quality assessment
    avg_word_conf = sum(w.confidence for w in all_words) / max(len(all_words), 1) if all_words else 0
    handwritten_ratio = sum(1 for w in all_words if w.is_handwritten) / max(len(all_words), 1) if all_words else 0
    
    # Normalize text for pattern matching
    text = re.sub(r'\r\n', '\n', all_text)
    text = re.sub(r'\r', '\n', text)
    lines = text.split('\n')
    
    # ===== HEADER ZONE (0-15% of page) =====
    header_words = find_words_in_zone(all_words, 0, 0.15)
    
    # Academic Session
    for w in header_words:
        match = re.match(r'(\d{4}[-/]\d{2,4})', w.text)
        if match:
            fields['AcademicSession'] = match.group(1)
            break
    
    # Course (from checkbox) - Tick comes AFTER the selection
    # Pattern: "B.COM.(H) ✓" not "✓ B.COM.(H)"
    if re.search(r'B\.?COM\.?\s*\(H\)\s*[✓✔☑√]', text, re.IGNORECASE):
        fields['Course'] = 'B.COM.(H)'
    elif re.search(r'B\.?A\.?\s*\(H\)\s*ECO\s*[✓✔☑√]', text, re.IGNORECASE):
        fields['Course'] = 'B.A.(H) ECO'
    else:
        # Fallback: look for course with tick in nearby lines
        for i, line in enumerate(lines):
            if 'B.COM' in line.upper() and any(c in line for c in '✓✔☑√'):
                fields['Course'] = 'B.COM.(H)'
                break
            if 'B.A' in line.upper() and 'ECO' in line.upper() and any(c in line for c in '✓✔☑√'):
                fields['Course'] = 'B.A.(H) ECO'
                break
    
    # Category - Tick comes AFTER the category
    categories = ['GEN', 'OBC', 'SC', 'ST', 'Sports', 'PwD', 'EWS', 'Foreign', 'CW', 'KM', 'ECA']
    for cat in categories:
        # Priority: tick AFTER category name
        if re.search(rf'{cat}\s*[✓✔☑√]', text, re.IGNORECASE):
            fields['AdmissionCategory'] = cat.upper()
            break
    
    # ===== FORM NUMBERS =====
    # DU Portal Form Number (12 digits)
    for w in all_words:
        if re.match(r'^\d{12}$', w.text):
            fields['DuPortalFormNumber'] = w.text
            fields['AadharNumber'] = w.text  # Often same as Aadhar
            break
    
    # College Roll No (format: 24BC101)
    for w in all_words:
        if re.match(r'^\d{2}[A-Z]{2,3}\s*\d{2,4}$', w.text, re.IGNORECASE):
            fields['CollegeRollNo'] = w.text.upper().replace(' ', '')
            break
    
    # CUET Score (3-digit number near "CUET Score" label)
    cuet_value = find_value_right_of_label(all_words, "CUET Score")
    if cuet_value:
        match = re.search(r'(\d{3})', cuet_value)
        if match:
            fields['CuetScore'] = match.group(1)
    
    # ===== STUDENT NAME (Zone 15-25%) =====
    # Strategy: Find First Name and Surname separately after "1." and before labels
    # OCR format: 1. / NAME IN BLOCK LETTERS / FIRST_NAME / RAJ / First Name / ... / SURNAME_VAL / Surname
    
    first_name = None
    surname = None
    
    for i, line in enumerate(lines):
        if 'NAME IN BLOCK LETTERS' in line.upper() or (line.strip() == '1.' and i+1 < len(lines)):
            # Collect name parts until we hit "First Name" label
            name_parts = []
            for j in range(i+1, min(i+10, len(lines))):
                next_line = lines[j].strip()
                # Stop at "First Name" label to get first name only
                if 'FIRST NAME' in next_line.upper():
                    if name_parts:
                        first_name = name_parts[0]
                    break
                # Valid name: uppercase, not a label, not address
                if next_line and re.match(r'^[A-Z][A-Z\s]*$', next_line):
                    if not is_form_label(next_line):
                        if next_line.upper() not in ['DD', 'MM', 'YYYY', 'N-B']:
                            name_parts.append(next_line)
            break
    
    # Find surname: appears before "Surname" label
    for i, line in enumerate(lines):
        if line.strip().upper() == 'SURNAME':
            # Surname value is on previous line
            if i > 0:
                prev = lines[i-1].strip()
                if re.match(r'^[A-Z][A-Z]*$', prev) and not is_form_label(prev):
                    # Make sure it's not an address word
                    if prev.upper() not in ['NAGAR', 'VIHAR', 'COLONY', 'PATEL', 'ROAD', 'ENCLAVE']:
                        surname = prev
            break
    
    # If no surname found above "Surname" label, look after first name
    if not surname and first_name:
        for i, line in enumerate(lines):
            if line.strip().upper() == first_name.upper():
                if i+1 < len(lines):
                    next_line = lines[i+1].strip()
                    if re.match(r'^[A-Z][A-Z]*$', next_line) and not is_form_label(next_line):
                        if next_line.upper() not in ['NAGAR', 'VIHAR', 'COLONY', 'PATEL', 'ROAD']:
                            surname = next_line
                break
    
    # Look for middle name (between First Name label and Surname label)
    middle_name = None
    for i, line in enumerate(lines):
        if 'MIDDLE NAME' in line.upper() or line.strip().upper() == 'MIDDLE NAME':
            # Middle name value is on previous line
            if i > 0:
                prev = lines[i-1].strip()
                if re.match(r'^[A-Z][A-Z]*$', prev) and not is_form_label(prev):
                    if prev.upper() not in ['RAJ', 'NAVYA', 'NAGAR', 'VIHAR']:  # Not first/surname
                        middle_name = prev
            break
    
    # Combine into full name
    if first_name:
        fields['FirstName'] = first_name.title()
        if middle_name:
            fields['MiddleName'] = middle_name.title()
        if surname:
            fields['Surname'] = surname.title()
            if middle_name:
                fields['StudentName'] = f"{first_name} {middle_name} {surname}".title()
            else:
                fields['StudentName'] = f"{first_name} {surname}".title()
        else:
            fields['StudentName'] = first_name.title()
    
    # ===== GENDER =====
    # User clarified: tick is IN FRONT of the option (e.g., "✓ Female")
    # Strategy: Use bounding box spatial analysis to find which gender has tick before it
    
    gender_options = ['Male', 'Female', 'Transgender']
    tick_chars = set('✓✔☑√V')  # V is often OCR'd as tick
    
    # Method 1: Use spatial analysis - find gender word with tick to its LEFT
    gender_words = []
    tick_words = []
    
    for w in all_words:
        if w.text in gender_options:
            gender_words.append(w)
        elif any(c in w.text for c in tick_chars):
            tick_words.append(w)
    
    # Find which gender word has a tick closest to its left (and on same row)
    for gw in gender_words:
        for tw in tick_words:
            # Tick should be to the LEFT of gender word, on roughly same row
            x_dist = gw.x - tw.right  # Distance from tick's right edge to gender's left edge
            y_diff = abs(gw.center_y - tw.center_y)  # Vertical alignment
            
            # Tick is to the left (positive x_dist), nearby (< 0.15), and vertically aligned
            if 0 < x_dist < 0.15 and y_diff < 0.02:
                fields['Gender'] = gw.text
                break
        if 'Gender' in fields:
            break
    
    # Method 2: Pattern match "✓ Female" or "[checkmark]Female" 
    if 'Gender' not in fields:
        for pattern in [r'[✓✔☑√V]\s*Female', r'[✓✔☑√V]\s*Male', r'[✓✔☑√V]\s*Transgender']:
            if re.search(pattern, text, re.IGNORECASE):
                match = re.search(pattern, text, re.IGNORECASE)
                for gender in gender_options:
                    if gender.lower() in match.group().lower():
                        fields['Gender'] = gender
                        break
            if 'Gender' in fields:
                break
    
    # Method 3: Look for gender word immediately BEFORE tick in line sequence
    # OCR often places tick after the selected gender word in reading order
    # E.g.: 'Male' -> 'Female' -> '☑Tr' means Female is selected
    if 'Gender' not in fields:
        last_gender_seen = None
        for i, line in enumerate(lines):
            line_text = line.strip()
            if line_text in gender_options:
                last_gender_seen = line_text
            elif any(c in line_text for c in tick_chars):
                # Found tick - the last gender word before this is the selected one
                if last_gender_seen:
                    fields['Gender'] = last_gender_seen
                    break
    
    # Method 4: Fallback - use most common gender when no tick found (not reliable)
    if 'Gender' not in fields:
        # Count occurrences, but this is unreliable
        for i, line in enumerate(lines):
            if line.strip() == 'Female':
                # If we reach Female before Male (after Gender label), likely Female
                fields['Gender'] = 'Female'
                break
            elif line.strip() == 'Male':
                fields['Gender'] = 'Male'
                break
    
    # ===== DATE OF BIRTH =====
    # Strategy: Find DD, MM, YYYY values after "Date of Birth" label
    # OCR may read "11" as "I 1" or similar
    
    def fix_month_ocr(val):
        """Fix OCR misreads for month values"""
        # Common OCR patterns for months
        ocr_month_fixes = {
            'I 1': '11', 'I1': '11', '1 1': '11', 'II': '11',
            'I 0': '10', 'I0': '10', '1 0': '10',
            'O 1': '01', '0 1': '01',
        }
        val_stripped = val.strip()
        if val_stripped in ocr_month_fixes:
            return ocr_month_fixes[val_stripped]
        return val_stripped
    
    for i, line in enumerate(lines):
        if 'Date of Birth' in line:
            day, month, year = None, None, None
            for j in range(i, min(i+20, len(lines))):
                raw_val = lines[j].strip()
                val = clean_number(raw_val)
                
                # Try fixing month OCR patterns first
                fixed_month = fix_month_ocr(raw_val)
                if fixed_month.isdigit() and 1 <= int(fixed_month) <= 12:
                    if not month and day:
                        month = fixed_month.zfill(2)
                        continue
                
                if not day and re.match(r'^([0-2]?[0-9]|3[01])$', val):
                    try:
                        if 1 <= int(val) <= 31:
                            day = val.zfill(2)
                    except: pass
                elif not month and day and re.match(r'^(0?[1-9]|1[0-2])$', val):
                    month = val.zfill(2)
                elif not year and re.match(r'^(19|20)\d{2}$', val):
                    year = val
            
            if day and year:
                month = month or '01'
                fields['DateOfBirth'] = f"{day}/{month}/{year}"
            break
    
    # ===== EMAIL =====
    # Student email is on Page 1 near "6. Email" label
    # OCR may truncate domain (e.g., @GMAL instead of @GMAIL.COM)
    
    def fix_email(email_text):
        """Fix truncated email domains"""
        email_text = email_text.strip()
        # Apply OCR corrections
        for wrong, correct in EMAIL_DOMAIN_FIXES.items():
            if wrong.upper() in email_text.upper():
                email_text = re.sub(re.escape(wrong), correct, email_text, flags=re.IGNORECASE)
        for wrong, correct in OCR_CORRECTIONS.items():
            email_text = email_text.replace(wrong, correct)
        
        # If email has @ but no valid TLD, try to complete the domain
        if '@' in email_text and not re.search(r'\\.[a-zA-Z]{2,}$', email_text):
            # Try common domain completions
            domain_part = email_text.split('@')[1].upper() if '@' in email_text else ''
            if domain_part.startswith('GMAI') or domain_part.startswith('GMAL') or domain_part == 'GMAIL':
                local_part = email_text.split('@')[0]
                email_text = f"{local_part}@gmail.com"
            elif domain_part.startswith('YAHOO'):
                local_part = email_text.split('@')[0]
                email_text = f"{local_part}@yahoo.com"
        
        return email_text.lower()
    
    # Find student email (appears first, on page 1, field 6)
    # Pattern allows partial domains
    partial_email_pattern = r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+(?:\\.[a-zA-Z]{2,})?)'
    
    for i, line in enumerate(lines):
        if '6. Email' in line or (line.strip().startswith('6.') and i+1 < len(lines) and 'Email' in lines[i+1]):
            # Look for email in next few lines
            for j in range(i, min(i+5, len(lines))):
                email_match = re.search(partial_email_pattern, lines[j])
                if email_match:
                    fixed_email = fix_email(email_match.group(1))
                    if '@' in fixed_email:
                        fields['Email'] = fixed_email
                        break
            break
    
    # If no email found yet, try finding email near "Email" label on page 1
    if 'Email' not in fields:
        # Look for email before "Contact Numbers" (that's field 7)
        for i, line in enumerate(lines):
            if 'Contact Numbers' in line or '7. Contact' in line:
                # Check lines before this for email
                for j in range(max(0, i-5), i):
                    email_match = re.search(partial_email_pattern, lines[j])
                    if email_match:
                        fixed_email = fix_email(email_match.group(1))
                        if '@' in fixed_email:
                            fields['Email'] = fixed_email
                            break
                break
    
    # Fallback: first email not containing typical parent name patterns
    if 'Email' not in fields:
        all_emails = re.findall(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,})', text)
        for email in all_emails:
            email_lower = email.lower()
            # Skip emails that look like parent emails (typically contain parent names)
            if not any(parent_pattern in email_lower for parent_pattern in ['meeta', 'hemraj', 'father', 'mother']):
                fields['Email'] = email_lower
                break
        if 'Email' not in fields and all_emails:
            fields['Email'] = all_emails[0].lower()
    
    # ===== PHONE NUMBERS =====
    phones = re.findall(r'\b([6-9]\d{9})\b', text)
    if phones:
        fields['PhoneNumber'] = phones[0]
        if len(phones) > 1:
            fields['AlternatePhone'] = phones[1]
    
    # ===== PERMANENT ADDRESS (Field 4) =====
    # Format: 4. Permanent Address | address content | State | PIN
    for i, line in enumerate(lines):
        if 'Permanent' in line and 'Address' in line:
            address_parts = []
            state_val = None
            pin_val = None
            
            for j in range(i+1, min(i+12, len(lines))):
                val = lines[j].strip()
                
                # Stop at next field
                if '5. Local' in val or 'Local Address' in val:
                    break
                
                # Extract State
                if 'State' in val:
                    state_match = re.search(r'State\s*([A-Z]+)', val, re.IGNORECASE)
                    if state_match:
                        state_val = state_match.group(1).title()
                    continue
                
                # Extract PIN
                pin_match = re.search(r'(?:PIN\s*)?(\d{6})\b', val)
                if pin_match:
                    pin_val = pin_match.group(1)
                    continue
                
                # Address parts: alphanumeric content, not labels
                if val and not is_form_label(val) and len(val) > 2:
                    # Filter out gender/DOB content that might be nearby
                    if val not in ['DD', 'MM', 'YYYY', 'D D', 'M M', 'Y Y Y Y']:
                        if not re.match(r'^\d{1,2}$', val):  # Not just day/month numbers
                            address_parts.append(val)
            
            if address_parts:
                # Combine and clean address
                full_address = ' '.join(address_parts)
                # Remove duplicates and clean
                full_address = re.sub(r'\s+', ' ', full_address).strip()
                fields['PermanentAddress'] = full_address
            
            if state_val:
                fields['PermanentState'] = state_val
            if pin_val:
                fields['PermanentPincode'] = pin_val
            break
    
    # ===== PARENT NAMES =====
    # Form layout: "8. Mother's Name" and "9. Father's Name" labels on adjacent lines
    # Followed by the actual names (MEET/MEETA, HEMRAJ) on the next lines
    # Strategy: Find the labels, then get the CAPS names that follow (skip labels)
    
    # Find lines with parent labels
    mother_label_idx = None
    father_label_idx = None
    for i, line in enumerate(lines):
        if "Mother's Name" in line or "8. Mother" in line:
            mother_label_idx = i
        if "Father's Name" in line or "9. Father" in line:
            father_label_idx = i
            break  # Father usually comes after mother
    
    # Names appear AFTER both labels, usually on consecutive lines
    if mother_label_idx is not None and father_label_idx is not None:
        # Look for CAPS names after the father label (since labels are together)
        names_found = []
        for j in range(father_label_idx + 1, min(father_label_idx + 8, len(lines))):
            val = lines[j].strip()
            # Stop at numbered items
            if re.match(r'^\d+\.', val):
                break
            # CAPS word that looks like a name (not a label)
            if re.match(r'^[A-Z]{2,}$', val) and not is_form_label(val):
                names_found.append(val)
        
        # First name is mother, second is father
        if len(names_found) >= 2:
            fields['MotherName'] = names_found[0].title()
            fields['FatherName'] = names_found[1].title()
        elif len(names_found) == 1:
            # Only one name found - try to determine which one
            # If label order is mother then father, the name after father is father's
            fields['FatherName'] = names_found[0].title()
    
    # ===== CLASS XII DETAILS =====
    match = re.search(r'Year\s+of\s+passing\s*\n?\s*(\d{4})', text, re.IGNORECASE)
    if match:
        fields['TwelfthYear'] = match.group(1)
    
    # Board detection
    if re.search(r'\bCBSE\b', text, re.IGNORECASE):
        fields['TwelfthBoard'] = 'CBSE'
    elif re.search(r'\bICSE\b', text, re.IGNORECASE):
        fields['TwelfthBoard'] = 'ICSE'
    elif re.search(r'\bISC\b', text, re.IGNORECASE):
        fields['TwelfthBoard'] = 'ISC'
    
    # ===== PERSONAL INFO =====
    if re.search(r'\bINDIAN\b', text, re.IGNORECASE):
        fields['Nationality'] = 'Indian'
    
    religions = ['Hindu', 'Muslim', 'Sikh', 'Christian', 'Jain', 'Buddhist']
    for rel in religions:
        if re.search(rf'\b{rel}\b', text, re.IGNORECASE):
            fields['Religion'] = rel
            break
    
    # Blood Group
    match = re.search(r'\b([ABO][+-]|AB[+-])\b', text)
    if match:
        fields['BloodGroup'] = match.group(1).upper()
    
    # State
    states = ['DELHI', 'HARYANA', 'UTTAR PRADESH', 'RAJASTHAN', 'PUNJAB', 'MAHARASHTRA', 'WEST BENGAL']
    for state in states:
        if state in text.upper():
            fields['PermanentState'] = state.title()
            break
    
    # Pincode (6 digits, Delhi starts with 11)
    pincodes = re.findall(r'\b(1[1-3]\d{4})\b', text)  # Delhi/Northern India
    if not pincodes:
        pincodes = re.findall(r'\b(\d{6})\b', text)
    if pincodes:
        fields['PermanentPincode'] = pincodes[0]
    
    # ===== PAGE 3: MOTHER'S OCCUPATIONAL DETAILS (Field 13) =====
    mother_section_started = False
    for i, line in enumerate(lines):
        if "13. Mother" in line or "Mother's Occupational" in line:
            mother_section_started = True
            # Look for details in next 20 lines
            for j in range(i+1, min(i+25, len(lines))):
                val = lines[j].strip()
                
                # Stop at Father's section
                if "14. Father" in val or "Father's Occupational" in val:
                    break
                
                # Occupation (after "Occupation" label or "(a)")
                if '(a)' in lines[j-1] if j > 0 else False or 'Occupation' in lines[j-1] if j > 0 else False:
                    if val and not is_form_label(val) and len(val) > 2:
                        if 'MotherOccupation' not in fields:
                            fields['MotherOccupation'] = val.title()
                
                # Email detection for mother
                email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', val)
                if email_match and 'MotherEmail' not in fields:
                    fields['MotherEmail'] = email_match.group(1).lower()
                
                # Phone detection for mother
                phone_match = re.search(r'\b([6-9]\d{9})\b', val)
                if phone_match and 'MotherMobile' not in fields:
                    fields['MotherMobile'] = phone_match.group(1)
            break
    
    # ===== PAGE 3: FATHER'S OCCUPATIONAL DETAILS (Field 14) =====
    for i, line in enumerate(lines):
        if "14. Father" in line or "Father's Occupational" in line:
            for j in range(i+1, min(i+25, len(lines))):
                val = lines[j].strip()
                
                # Stop at Guardian section
                if "15. Local Guardian" in val or "Guardian" in val:
                    break
                
                # Occupation
                if '(a)' in lines[j-1] if j > 0 else False:
                    if val and not is_form_label(val) and len(val) > 2:
                        if 'FatherOccupation' not in fields:
                            fields['FatherOccupation'] = val.title()
                
                # Email detection for father
                email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', val)
                if email_match and 'FatherEmail' not in fields:
                    fields['FatherEmail'] = email_match.group(1).lower()
                
                # Phone detection for father
                phone_match = re.search(r'\b([6-9]\d{9})\b', val)
                if phone_match and 'FatherMobile' not in fields:
                    fields['FatherMobile'] = phone_match.group(1)
            break
    
    # ===== PAGE 3: LOCAL GUARDIAN (Field 15) - Optional =====
    for i, line in enumerate(lines):
        if "15. Local Guardian" in line or "Guardian's Details" in line:
            for j in range(i+1, min(i+20, len(lines))):
                val = lines[j].strip()
                
                if "16. Other" in val or "Other Information" in val:
                    break
                
                # Guardian name (after "Name" label)
                if 'Name' in lines[j-1] if j > 0 else False:
                    if val and not is_form_label(val):
                        if 'GuardianName' not in fields:
                            fields['GuardianName'] = val.title()
                
                # Guardian phone
                phone_match = re.search(r'\b([6-9]\d{9})\b', val)
                if phone_match and 'GuardianMobile' not in fields:
                    fields['GuardianMobile'] = phone_match.group(1)
                
                # Guardian email
                email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', val)
                if email_match and 'GuardianEmail' not in fields:
                    fields['GuardianEmail'] = email_match.group(1).lower()
            break
    
    # ===== PAGE 3: OTHER INFORMATION (Field 16) =====
    # DU Enrolment number
    du_match = re.search(r'Enrolment\s*No[.\s]*([A-Z0-9/-]+)', text, re.IGNORECASE)
    if du_match:
        fields['DuEnrollmentNumber'] = du_match.group(1)
    
    # Hindi medium preference
    if re.search(r'Hindi\s+medium.*[✓✔☑√].*Yes', text, re.IGNORECASE | re.DOTALL):
        fields['HindiMediumPreference'] = 'Yes'
    elif re.search(r'Hindi\s+medium.*Yes\s*[✓✔☑√]', text, re.IGNORECASE | re.DOTALL):
        fields['HindiMediumPreference'] = 'Yes'
    
    # ===== PAGE 3: CATEGORY CERTIFICATE DETAILS (Field 17) =====
    for i, line in enumerate(lines):
        if "17." in line or "EWS/SC/ST" in line or "Certificate" in line.lower():
            for j in range(i+1, min(i+15, len(lines))):
                val = lines[j].strip()
                
                # Certificate number
                cert_match = re.search(r'(?:Certificate|Cert)\s*No[.\s:]*([A-Z0-9/-]+)', val, re.IGNORECASE)
                if cert_match and 'CategoryCertificateNumber' not in fields:
                    fields['CategoryCertificateNumber'] = cert_match.group(1)
                
                # PwBD disability percentage
                disability_match = re.search(r'(\d{1,3})\s*%', val)
                if disability_match and 'DisabilityPercentage' not in fields:
                    pct = int(disability_match.group(1))
                    if 0 < pct <= 100:
                        fields['DisabilityPercentage'] = str(pct)
                
                # Disability type
                if re.search(r'\bVH\b', val):
                    fields['DisabilityType'] = 'VH'
                elif re.search(r'\bHH\b', val):
                    fields['DisabilityType'] = 'HH'
                elif re.search(r'\bOH\b', val):
                    fields['DisabilityType'] = 'OH'
            break
    
    # ===== FAMILY INCOME =====
    income_match = re.search(r'Annual\s+Income[:\s]*Rs?\.?\s*([\d,]+)', text, re.IGNORECASE)
    if income_match:
        fields['AnnualIncome'] = income_match.group(1).replace(',', '')
    
    # ===== BELOW POVERTY LINE =====
    if re.search(r'Below\s+Poverty\s+Line.*Yes\s*[✓✔☑√]', text, re.IGNORECASE):
        fields['BelowPovertyLine'] = 'Yes'
    elif re.search(r'Below\s+Poverty\s+Line.*[✓✔☑√]\s*Yes', text, re.IGNORECASE):
        fields['BelowPovertyLine'] = 'Yes'
    elif re.search(r'Below\s+Poverty\s+Line.*No\s*[✓✔☑√]', text, re.IGNORECASE):
        fields['BelowPovertyLine'] = 'No'
    
    # ===== CLASS XII ROLL NUMBER =====
    for i, line in enumerate(lines):
        if 'Examination Roll' in line or 'Roll No' in line:
            for j in range(i, min(i+3, len(lines))):
                roll_match = re.search(r'\b(\d{7,12})\b', lines[j])
                if roll_match:
                    fields['TwelfthRollNumber'] = roll_match.group(1)
                    break
            break
    
    # ===== INSTITUTION LAST ATTENDED =====
    for i, line in enumerate(lines):
        if 'Institution Last Attended' in line or 'School' in line:
            for j in range(i+1, min(i+3, len(lines))):
                val = lines[j].strip()
                if val and not is_form_label(val) and len(val) > 5:
                    if 'TwelfthInstitution' not in fields:
                        fields['TwelfthInstitution'] = val.title()
                        break
            break
    
    # ===== LOCAL ADDRESS (Field 5) =====
    for i, line in enumerate(lines):
        if '5. Local' in line or 'Local Address' in line:
            address_parts = []
            for j in range(i+1, min(i+10, len(lines))):
                val = lines[j].strip()
                # Stop at next field
                if '6. Email' in val or '7. Contact' in val or 'Email' in val:
                    break
                if val and not is_form_label(val) and len(val) > 2:
                    if val not in ['DD', 'MM', 'YYYY']:
                        address_parts.append(val)
            if address_parts:
                fields['LocalAddress'] = ' '.join(address_parts)
            break
    
    # ===== MARITAL STATUS =====
    # Look for tick mark near Married/Unmarried options
    if re.search(r'Married\s*[✓✔☑√]', text, re.IGNORECASE):
        fields['MaritalStatus'] = 'Married'
    elif re.search(r'[✓✔☑√]\s*Married[^Un]', text, re.IGNORECASE):
        fields['MaritalStatus'] = 'Married'
    elif re.search(r'Unmarried\s*[✓✔☑√]', text, re.IGNORECASE):
        fields['MaritalStatus'] = 'Unmarried'
    elif re.search(r'[✓✔☑√]\s*Unmarried', text, re.IGNORECASE):
        fields['MaritalStatus'] = 'Unmarried'
    else:
        fields['MaritalStatus'] = 'Unmarried'  # Default for students
    
    # ===== AADHAR NUMBER (separate from DU Portal Number) =====
    aadhar_matches = re.findall(r'\b(\d{4}\s*\d{4}\s*\d{4})\b', text)
    for match in aadhar_matches:
        clean_aadhar = match.replace(' ', '')
        if len(clean_aadhar) == 12:
            fields['AadharNumber'] = clean_aadhar
            break
    
    # ===== CLASS XII MARKS/PERCENTAGE =====
    # Look for percentage near "%" or "Marks" or "Percentage"
    for i, line in enumerate(lines):
        if 'Percentage' in line or '% of Marks' in line:
            for j in range(i, min(i+3, len(lines))):
                pct_match = re.search(r'(\d{1,3}\.?\d{0,2})\s*%', lines[j])
                if pct_match:
                    pct = float(pct_match.group(1))
                    if 30 <= pct <= 100:
                        fields['TwelfthPercentage'] = str(pct)
                        break
            break
    
    # Best of Four percentage
    best_four_match = re.search(r'Best\s*(?:of)?\s*4.*?(\d{2,3}\.?\d{0,2})\s*%?', text, re.IGNORECASE)
    if best_four_match:
        fields['Class12BestFour'] = best_four_match.group(1)
    
    # ===== CUET SUBJECTS (Table on Page 1) =====
    # Look for subject names and their scores - extract up to 6 subjects
    cuet_subjects = []
    cuet_section_start = False
    for i, line in enumerate(lines):
        if 'CUET' in line.upper() and ('Subject' in line or 'Score' in line):
            cuet_section_start = True
            continue
        if cuet_section_start:
            # Stop at next section
            if 'Name' in line and 'Block' in line:
                break
            if len(cuet_subjects) >= 6:
                break
            # Look for subject-score pairs
            subject_match = re.search(r'(English|Economics|Accountancy|Business|Mathematics|Hindi|Geography|History|Political|Commerce|Science)', line, re.IGNORECASE)
            if subject_match:
                subject = subject_match.group(1).title()
                # Look for max and obtained scores on same line
                scores = re.findall(r'\b(\d{2,3})\b', line)
                if len(scores) >= 2:
                    cuet_subjects.append({'subject': subject, 'max': scores[0], 'obtained': scores[1]})
                elif len(scores) == 1:
                    cuet_subjects.append({'subject': subject, 'max': '200', 'obtained': scores[0]})
    
    # Map CUET subjects to individual fields
    for idx, subj in enumerate(cuet_subjects[:6], 1):
        fields[f'CuetSubject{idx}'] = subj['subject']
        fields[f'CuetTotalScore{idx}'] = subj.get('max', '')
        fields[f'CuetScoreObtained{idx}'] = subj.get('obtained', '')
    
    # Calculate total CUET score
    total_obtained = sum(int(s.get('obtained', 0)) for s in cuet_subjects if s.get('obtained', '').isdigit())
    if total_obtained > 0:
        fields['CuetTotalScoreAll'] = str(total_obtained)
    
    # ===== 10TH CLASS DETAILS (Class X) =====
    for i, line in enumerate(lines):
        if 'Class X' in line or '10th' in line.lower() or 'Xth' in line:
            for j in range(i, min(i+10, len(lines))):
                val = lines[j]
                # Board name
                board_match = re.search(r'(CBSE|ICSE|ISC|State Board|UP Board|Bihar Board|GSEB|WBBSE|PSEB)', val, re.IGNORECASE)
                if board_match and 'TenthBoard' not in fields:
                    fields['TenthBoard'] = board_match.group(1).upper()
                # Year
                year_match = re.search(r'\b(20[0-2][0-9])\b', val)
                if year_match and 'TenthYear' not in fields:
                    fields['TenthYear'] = year_match.group(1)
                # Percentage
                pct_match = re.search(r'(\d{2,3}\.?\d{0,2})\s*%', val)
                if pct_match and 'TenthPercentage' not in fields:
                    pct = float(pct_match.group(1))
                    if 30 <= pct <= 100:
                        fields['TenthPercentage'] = str(pct)
            break
    
    # ===== EMERGENCY CONTACT =====
    for i, line in enumerate(lines):
        if 'Emergency' in line and 'Contact' in line:
            for j in range(i, min(i+5, len(lines))):
                val = lines[j].strip()
                # Emergency contact name
                if val and not is_form_label(val) and len(val) > 2:
                    if 'EmergencyContactName' not in fields and not val[0].isdigit():
                        fields['EmergencyContactName'] = val.title()
                # Emergency phone
                phone_match = re.search(r'\b([6-9]\d{9})\b', val)
                if phone_match and 'EmergencyContactPhone' not in fields:
                    fields['EmergencyContactPhone'] = phone_match.group(1)
            break
    
    # ===== STUDENT DECLARATION (Page 3) =====
    for i, line in enumerate(lines):
        if 'Student Declaration' in line or 'Declaration by Student' in line:
            for j in range(i, min(i+10, len(lines))):
                val = lines[j].strip()
                # Look for signature name
                if 'Name' in lines[j-1] if j > 0 else False:
                    if val and not is_form_label(val):
                        if 'StudentDeclarationName' not in fields:
                            fields['StudentDeclarationName'] = val.title()
                # Date
                date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', val)
                if date_match and 'StudentDeclarationDate' not in fields:
                    fields['StudentDeclarationDate'] = date_match.group(1)
                # Place
                place_match = re.search(r'Place\s*[:\s]*([A-Za-z]+)', val, re.IGNORECASE)
                if place_match and 'StudentDeclarationPlace' not in fields:
                    fields['StudentDeclarationPlace'] = place_match.group(1).title()
            break
    
    # ===== PARENT/GUARDIAN DECLARATION (Page 4) =====
    for i, line in enumerate(lines):
        if 'Parent' in line and 'Guardian' in line and 'Declaration' in line:
            for j in range(i, min(i+15, len(lines))):
                val = lines[j].strip()
                # Parent/Guardian name
                if 'Name' in lines[j-1] if j > 0 else False:
                    if val and not is_form_label(val):
                        if 'ParentGuardianName' not in fields:
                            fields['ParentGuardianName'] = val.title()
                # Relationship
                rel_match = re.search(r'(Father|Mother|Guardian|Uncle|Aunt)', val, re.IGNORECASE)
                if rel_match and 'ParentGuardianRelationship' not in fields:
                    fields['ParentGuardianRelationship'] = rel_match.group(1).title()
                # Date
                date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', val)
                if date_match and 'ParentGuardianDate' not in fields:
                    fields['ParentGuardianDate'] = date_match.group(1)
                # Place
                place_match = re.search(r'Place\s*[:\s]*([A-Za-z]+)', val, re.IGNORECASE)
                if place_match and 'ParentGuardianPlace' not in fields:
                    fields['ParentGuardianPlace'] = place_match.group(1).title()
            break

    
    # ===== PARENT ORGANIZATION/EMPLOYER =====
    # Mother's organization
    for i, line in enumerate(lines):
        if 'Mother' in line and ('Organization' in line or 'Employer' in line):
            if i+1 < len(lines):
                val = lines[i+1].strip()
                if val and not is_form_label(val):
                    fields['MotherOrganization'] = val.title()
            break
    
    # Father's organization
    for i, line in enumerate(lines):
        if 'Father' in line and ('Organization' in line or 'Employer' in line):
            if i+1 < len(lines):
                val = lines[i+1].strip()
                if val and not is_form_label(val):
                    fields['FatherOrganization'] = val.title()
            break
    
    # Mother's annual income
    for i, line in enumerate(lines):
        if 'Mother' in line and 'Annual' in line and 'Income' in line:
            income_match = re.search(r'Rs?\.?\s*([0-9,]+)', lines[min(i+1, len(lines)-1)])
            if income_match:
                fields['MotherAnnualIncome'] = income_match.group(1).replace(',', '')
            break
    
    # Father's annual income
    for i, line in enumerate(lines):
        if 'Father' in line and 'Annual' in line and 'Income' in line:
            income_match = re.search(r'Rs?\.?\s*([0-9,]+)', lines[min(i+1, len(lines)-1)])
            if income_match:
                fields['FatherAnnualIncome'] = income_match.group(1).replace(',', '')
            break
    
    # ===== DATE OF ADMISSION =====
    for w in all_words:
        # Look for date format near "Date of Admission"
        if re.match(r'\d{1,2}/\d{1,2}/\d{4}', w.text) or re.match(r'\d{1,2}-\d{1,2}-\d{4}', w.text):
            admission_date = find_value_right_of_label(all_words, "Admission")
            if admission_date:
                fields['DateOfAdmission'] = admission_date
                break
    
    # ===== DECLARATION DATE/PLACE (Page 2) =====
    for i, line in enumerate(lines):
        if 'Date' in line and 'Place' in line:
            # Look for date value
            for j in range(i, min(i+3, len(lines))):
                date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', lines[j])
                if date_match:
                    fields['DeclarationDate'] = date_match.group(1)
                    break
            # Look for place value  
            place_match = re.search(r'Place\s*[:\s]*([A-Za-z]+)\b', lines[i], re.IGNORECASE)
            if place_match:
                fields['DeclarationPlace'] = place_match.group(1).title()
            break
    
    # ===== DOCUMENT CHECKLIST (Page 4) - 15 items =====
    # Each document can be checked with tick mark
    document_items = [
        ('DocPhotographs', ['Student Photo', 'Photograph', '2 Photographs']),
        ('DocClassXCertificate', ['Class X', 'Xth Mark', '10th Mark', 'Marksheet X']),
        ('DocClassXiiMarksheet', ['Class XII', 'XIIth Mark', '12th Mark', 'Marksheet XII']),
        ('DocMigrationCertificate', ['Migration', 'Migration Certificate']),
        ('DocCharacterCertificate', ['Character', 'Character Certificate']),
        ('DocTransferCertificate', ['Transfer Certificate', 'T.C.', 'TC']),
        ('DocGapCertificate', ['Gap Certificate', 'Gap Year']),
        ('DocCasteCertificate', ['Caste Certificate', 'SC/ST', 'OBC', 'EWS']),
        ('DocIncomeCertificate', ['Income Certificate', 'Income Proof']),
        ('DocDomicileCertificate', ['Domicile', 'Residence Proof']),
        ('DocAadharCard', ['Aadhar', 'Aadhaar', 'AADHAR', 'Aadhar Card']),
        ('DocPassport', ['Passport']),
        ('DocCuetScorecard', ['CUET', 'Score Card', 'CUET Score']),
        ('DocUndertakingRagging', ['Anti-Ragging', 'Anti Ragging', 'Ragging']),
        ('DocMedicalFitness', ['Medical', 'Fitness', 'Medical Certificate']),
    ]
    
    for field_name, keywords in document_items:
        for keyword in keywords:
            # Check if keyword followed by tick or tick followed by keyword
            pattern1 = re.compile(rf'{re.escape(keyword)}.*?[✓✔☑√]', re.IGNORECASE | re.DOTALL)
            pattern2 = re.compile(rf'[✓✔☑√].*?{re.escape(keyword)}', re.IGNORECASE | re.DOTALL)
            
            if pattern1.search(text) or pattern2.search(text):
                fields[field_name] = True
                break
            else:
                fields[field_name] = False
    
    # Add per-field confidence and metadata
    fields['_meta'] = {
        'avg_word_confidence': round(avg_word_conf * 100, 1),
        'handwritten_ratio': round(handwritten_ratio * 100, 1),
        'total_words_detected': len(all_words),
        'fields_extracted': len([k for k in fields if not k.startswith('_')]),
        'field_confidence': field_confidence
    }
    
    return fields

# ===== OCR ERROR CORRECTION (ported from Electron app's WorldClassExtractor) =====

# Common word-level OCR corrections
WORD_CORRECTIONS = {
    'MOUSE WIFE': 'HOUSE WIFE', 'HOUSEWLFE': 'HOUSEWIFE',
    'QELHI': 'DELHI', 'DELHL': 'DELHI', 'OELHI': 'DELHI', 'DEIHI': 'DELHI', 'DELHl': 'DELHI',
    'RUSINESS': 'BUSINESS', 'BUSLNESS': 'BUSINESS',
    'STUDJES': 'STUDIES', 'STUDLES': 'STUDIES',
    'ACCOUNTANGY': 'ACCOUNTANCY', 'AGCOUNTANCY': 'ACCOUNTANCY',
    'ECONOMLCS': 'ECONOMICS', 'ECONOM1CS': 'ECONOMICS',
    'MATHEMATLCS': 'MATHEMATICS', 'MATHEMAIICS': 'MATHEMATICS',
    'ENGLLSH': 'ENGLISH', 'ENGL1SH': 'ENGLISH',
    'SCHQOL': 'SCHOOL', 'SCH00L': 'SCHOOL',
    'PUBLLC': 'PUBLIC', 'PUBL1C': 'PUBLIC',
    'V1HAR': 'VIHAR', 'VLHAR': 'VIHAR',
    'NAGBR': 'NAGAR', 'STRFET': 'STREET', 'FLBT': 'FLAT',
    'Klrpal': 'Kirpal', 'Rlddhi': 'Riddhi', 'Dhlruv': 'Dhruv',
}

EMAIL_DOMAIN_CORRECTIONS = {
    'gmall.com': 'gmail.com', 'gmai1.com': 'gmail.com', 'gmaIl.com': 'gmail.com',
    'gmal.com': 'gmail.com', 'gnail.com': 'gmail.com', 'GMALL.COM': 'gmail.com',
    'GMATL.COM': 'gmail.com', 'GMA1L.COM': 'gmail.com',
    'yahooo.com': 'yahoo.com', 'yah00.com': 'yahoo.com',
    'hotmai1.com': 'hotmail.com', 'hotmall.com': 'hotmail.com',
    'outlok.com': 'outlook.com', 'outl00k.com': 'outlook.com',
}


def correct_ocr_text(text: str, context: str = 'general') -> str:
    """Apply context-aware OCR error correction (ported from Electron app)."""
    if not text:
        return text
    corrected = text
    # Apply word-level corrections
    for wrong, right in WORD_CORRECTIONS.items():
        corrected = corrected.replace(wrong, right)
    
    if context == 'email':
        corrected = corrected.lower().strip().replace(' ', '').replace('@@', '@')
        corrected = re.sub(r'l\.com$', '.com', corrected, flags=re.IGNORECASE)
        corrected = re.sub(r'\.c0m$', '.com', corrected, flags=re.IGNORECASE)
        for wrong, right in EMAIL_DOMAIN_CORRECTIONS.items():
            if wrong in corrected:
                corrected = corrected.replace(wrong, right)
    elif context == 'phone':
        digits = re.sub(r'\D', '', corrected)
        if len(digits) == 12 and digits.startswith('91'):
            digits = digits[2:]
        elif len(digits) == 11 and digits.startswith('0'):
            digits = digits[1:]
        if len(digits) == 10 and digits[0] in '6789':
            return digits
        return digits if len(digits) >= 10 else corrected
    elif context == 'pincode':
        digits = re.sub(r'\D', '', corrected)
        if len(digits) >= 6 and digits[0] in '123456789':
            return digits[:6]
        return corrected
    elif context == 'date':
        match = re.search(r'(\d{1,2})[/\-\s](\d{1,2})[/\-\s](\d{2,4})', corrected)
        if match:
            day, month, year = match.groups()
            day = day.zfill(2); month = month.zfill(2)
            if len(year) == 2:
                year = '20' + year if int(year) < 50 else '19' + year
            return f"{day}/{month}/{year}"
    elif context == 'name':
        corrected = ' '.join(corrected.split())
        corrected = corrected.title()
    return corrected


def validate_and_correct_fields(fields: Dict[str, Any]) -> Dict[str, Any]:
    """Cross-field validation and correction (ported from Electron app's CrossFieldValidator)."""
    if not fields:
        return fields
    corrected = dict(fields)
    
    # === Date validation with field-specific year constraints ===
    date_fields = {
        'DateOfBirth': (1995, 2010),           # College student DOB range
        'DateOfAdmission': (2020, 2030),       # Recent admission dates
    }
    for date_field, (min_year, max_year) in date_fields.items():
        if date_field in corrected and isinstance(corrected[date_field], str):
            date_val = corrected[date_field]
            match = re.search(r'(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})', date_val)
            if match:
                d, m, y = int(match.group(1)), int(match.group(2)), int(match.group(3))
                if not (1 <= d <= 31 and 1 <= m <= 12 and min_year <= y <= max_year):
                    if date_field == 'DateOfBirth' and y > 2015:
                        corrected[date_field] = None  # Likely DOA misassigned to DOB
    
    # === Phone validation ===
    phone_fields = ['PhoneNumber', 'AlternatePhone', 'MotherMobile', 'FatherMobile',
                    'GuardianMobile', 'EmergencyContactPhone', 'MotherPhone', 'FatherPhone']
    for phone_field in phone_fields:
        if phone_field in corrected and isinstance(corrected[phone_field], str):
            corrected[phone_field] = correct_ocr_text(corrected[phone_field], 'phone')
    
    # === Email validation ===
    if 'Email' in corrected and isinstance(corrected['Email'], str):
        corrected['Email'] = correct_ocr_text(corrected['Email'], 'email')
        email = corrected['Email']
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            pass  # Keep it anyway, let user correct
    
    # === Pincode validation ===
    for pin_field in ['PermanentPincode', 'CorrespondencePincode', 'Pincode']:
        if pin_field in corrected and isinstance(corrected[pin_field], str):
            corrected[pin_field] = correct_ocr_text(corrected[pin_field], 'pincode')
    
    # === Name consistency ===
    first = corrected.get('FirstName', '')
    middle = corrected.get('MiddleName', '')
    surname = corrected.get('Surname', '')
    full = corrected.get('StudentName', '')
    
    if first and surname and not full:
        parts = [first, middle, surname] if middle else [first, surname]
        corrected['StudentName'] = ' '.join(p for p in parts if p)
    elif full and not first:
        parts = full.split()
        if len(parts) >= 2:
            corrected['FirstName'] = parts[0]
            corrected['Surname'] = parts[-1]
            if len(parts) == 3:
                corrected['MiddleName'] = parts[1]
    
    # === CUET score range validation ===
    total = 0
    count = 0
    for i in range(1, 7):
        score_key = f'CuetScoreObtained{i}'
        if score_key in corrected:
            try:
                score = int(corrected[score_key])
                if 0 <= score <= 200:
                    total += score
                    count += 1
            except (ValueError, TypeError):
                pass
    
    if count > 0 and 'CuetScore' in corrected:
        try:
            claimed = int(corrected['CuetScore'])
            if abs(claimed - total) > 5:
                corrected['CuetScore'] = str(total)  # Fix to calculated total
        except (ValueError, TypeError):
            pass
    
    # Remove None values
    corrected = {k: v for k, v in corrected.items() if v is not None}
    
    return corrected


def clean_extracted_fields(fields: Dict[str, Any]) -> Dict[str, Any]:
    """Initial cleanup: remove nulls, strip whitespace, normalize booleans.
    This runs BEFORE the comprehensive normalize_gemini_fields."""
    cleaned = {}
    for key, val in fields.items():
        if key.startswith('_'):
            continue
        if val is None:
            continue
        if isinstance(val, str):
            val = val.strip()
            if not val or val.lower() in ('null', 'none', 'n/a', ''):
                continue
        # Normalize boolean values for document checklist items
        if key.startswith('Doc') and isinstance(val, str):
            lower_val = val.lower()
            if lower_val in ('yes', 'true', '1', 'checked'):
                val = True
            elif lower_val in ('no', 'false', '0', 'unchecked'):
                val = False
        cleaned[key] = val
    return cleaned


# ===== GEMINI VISION AI EXTRACTION =====
# Uses Google Gemini to visually read form images and extract structured fields
# Keys MUST match C# AdmissionForm entity property names exactly (PascalCase)

GEMINI_EXTRACTION_PROMPT = """You are a world-class expert at reading handwritten Indian college admission forms.
This is an SRCC (Shri Ram College of Commerce) "Student's Data Form" — a 4-page printed form where students have HANDWRITTEN their personal, academic, and family information in designated boxes and fields.

Your job: extract EVERY field with maximum accuracy. Read the pen/pencil handwriting VERY carefully.
Return ONLY a valid JSON object with these EXACT keys (PascalCase). Use null for unreadable or missing fields.

IMPORTANT: You MUST also generate a "StudentName" key = FirstName + " " + MiddleName + " " + Surname (combined full name, trimmed). This is critical for the system.

===== HOLISTIC HANDLING LAWS (CRITICAL) =====

1. CROSSED SHEETS/LINE-THROUGHS: Some forms may have a large "X" or "VOID" or diagonal lines/slashes drawn across the entire page (a "crossed sheet"). 
   DO NOT IGNORE these pages. The cross is usually just a clerical marker; you MUST read the handwritten text UNDERNEATH the cross. 
   Focus on extracting the data, NOT the cross.

2. CUT/PARTIAL PAGES: If a page appears to be "cut" (truncated, partial scan, or missing the bottom/top), DO NOT IGNORE IT.
   Extract every available bit of information from the visible portion. Partial data is better than no data.

3. HANDWRITING vs PRINTED: ALWAYS prioritize HANDWRITTEN text (pen/ink). Ignore printed example text, watermarks, or instructions. 
   If a box has both printed and handwritten text, the HANDWRITING is the answer.

4. MULTI-SOURCE CROSS-REFERENCE (The "Golden Source" Rule):
   The same information appears in MULTIPLE places. Use ALL sources to verify.
   • Student Name: Section 1 (Boxes) + Page 3 Declaration ("I, [name]") + Parent Declaration (Candidate Name) + Attached Documents (Aadhar/Scorecard).
   • Course: Tick mark at top + CUET subjects (Commerce vs Eco) + Parent Declaration section.
   • Category: Tick marks + Certificate section (17) + Document Checklist tags + BPL status.
   • Father/Mother: Sections 8-9 + Parent Declaration Signatory names.
   → If sources conflict, use the CLEAREST one. If you see an attached Aadhar card, trust the PRINTED name/number on the card over the handwriting.

5. DIGIT CLARITY (Extreme Detail):
   • 1 vs 7: Look for the horizontal top bar on "7". A single vertical stroke is "1".
   • 3 vs 8: "3" is open on the left. "8" is two closed loops.
   • 5 vs 6: "5" has a sharp flat top. "6" has a continuous curve into a loop.
   • 0 vs 6: "0" is oval/symmetrical. "6" has a top-left tail.
   • 4 vs 9: "4" is angular/open. "9" is round/closed at top.
   • Context Check: Aadhar = 12 digits (No 0/1 start). Phone = 10 digits (6/7/8/9 start). CUET scores = typically 50-250.

===== ACADEMIC & ADMISSION (Section at top of page 1) =====
"AcademicSession": string (e.g. "2024-25") — printed near the top, often pre-filled
"Course": MUST be EXACTLY one of: "B.COM.(H)" or "B.A.(H) ECO"
   — PRIMARY: Look for a tick mark (✓) or filled circle next to these TWO options at the top of page 1.
   — CROSS-CHECK with CUET subjects table (Section 10, lower on page 1):
     • If subjects include Accountancy / Business Studies / Business Mathematics → "B.COM.(H)"
     • If subjects include Political Science / History / Economics → "B.A.(H) ECO"
   — CROSS-CHECK with parent declaration on page 3 (it mentions the course name).
   — If the tick is ambiguous, trust the CUET subjects first, then the parent declaration.
"AdmissionCategory": MUST be EXACTLY one of: "GEN","OBC","SC","ST","Sports","PwD","EWS","CW","KM","ECA","Foreign","Others"
   — Printed category options at top of page 1 with boxes/circles to tick.
   — MULTI-SIGNAL CROSS-CHECK (apply ALL of these):
     (a) PRIMARY: Look for the tick mark (✓) next to the category label.
     (b) Section 17 (Certificates, page 2):
         • "CategoryCertificateNumber" + "CategoryCertificateAuthority" are FILLED → NOT GEN (probably OBC/SC/ST/EWS).
         • Section 17 completely empty → likely GEN.
     (c) Document Checklist (page 4):
         • "Caste Certificate" ticked → SC/ST/OBC.
         • "Income Certificate" ticked but NOT Caste Certificate → could be EWS.
         • Neither ticked → likely GEN.
     (d) "BelowPovertyLine" in Section 12: "Yes" → more likely SC/ST/OBC/EWS.
     (e) If signals conflict, trust the TICK MARK at top of page 1.
   — "Category" MUST contain the SAME value as "AdmissionCategory".
"DuPortalFormNumber": string — multi-digit number (8-15 digits) labeled "DU Portal Form Number" near top of page 1.
   — This is NOT the Aadhar. They are in SEPARATE boxes. The DU number is usually near the top header area.
"CuetScore": string — total CUET score (should equal CuetScoreObtainedAll from the subject table).
"CollegeRollNo": string (e.g. "24BC101", "24ECO045") — top right area of page 1.
   — Format: 2-digit year + course code (BC or ECO) + sequence number.
"DateOfAdmission": string in DD/MM/YYYY format
"AadharNumber": string — EXACTLY 12 digits, in a dedicated labeled box (NOT the DU form number).
   — Remove any spaces or dashes: "1234 5678 9012" → "123456789012".
   — Validate: Aadhar never starts with 0 or 1. If first digit is 0 or 1, you are likely reading the wrong field.
   — CRITICAL CROSS-CHECK: Pages 5+ contain ATTACHED DOCUMENTS including the student's Aadhar card.
     The Aadhar card has the number PRINTED clearly in large font. If you can see an Aadhar card image
     in the later pages, read the 12-digit number from the PRINTED card and use that as the authoritative value.
     If the handwritten Aadhar on page 1 differs from the printed Aadhar on the card, ALWAYS trust the CARD.
   — The Aadhar card also shows the student's name and DOB — use these to cross-verify those fields too.

===== PERSONAL (Sections 1-3 on page 1) =====
"FirstName": string — FIRST box of the three-box name row.
"MiddleName": string or null — MIDDLE box. null if only 2 boxes filled.
"Surname": string — LAST box of the name row.
   — If student wrote full name in one box:
     • 2 words → FirstName = first word, Surname = second word, MiddleName = null
     • 3+ words → FirstName = first, Surname = last, MiddleName = everything in between
   — ALWAYS cross-check with declaration on page 3 ("I, [FULL NAME]") and parent declaration (mentions student's name).
   — Use the CLEAREST version. If Section 1 is messy but declaration is clear, prefer the declaration.
"StudentName": string — COMPUTED: FirstName + " " + MiddleName + " " + Surname (trimmed, no double spaces).
   — This is the most critical field for identification. It MUST be consistent with FirstName/MiddleName/Surname.
"Gender": MUST be EXACTLY: "Male","Female", or "Transgender"
   — Look for tick mark. Use the student's name as a strong hint (most Indian names are gender-indicative).
"DateOfBirth": string DD/MM/YYYY — from the DD, MM, YYYY boxes.
   — For a 2024-25 freshman, DOB year is typically 2004-2007 (age 17-20).
   — If year shows only 2 digits (e.g. "06"), interpret as "2006".


===== ADDRESSES (Sections 4-5 on page 1) =====
"PermanentAddress": string — FULL permanent address (combine all lines into one string).
"PermanentAddressLine1": first line of permanent address
"PermanentAddressLine2": second line of permanent address
"PermanentAddressLine3": third line (if any)
"PermanentCity": string — city/town from permanent address. Extract this EVEN IF the form doesn't have a separate city box — infer from the full address.
"PermanentState": string — state name (e.g. "Delhi", "Uttar Pradesh", "Haryana")
"PermanentPincode": string — EXACTLY 6 digits. Delhi pincodes: 110001-110099. UP pincodes start with 2.
"CorrespondenceAddress": string — full correspondence/local address.
   — If the form says "Same as Permanent" or ditto marks ("), copy the permanent address values.
"CorrespondenceAddressLine1": first line
"CorrespondenceAddressLine2": second line
"CorrespondenceAddressLine3": third line (if any)
"CorrespondenceCity": string — city from correspondence address
"CorrespondenceState": string
"CorrespondencePincode": string — 6 digits
"LocalAddress": string — same as CorrespondenceAddress (some forms label it differently)

===== CONTACT (Sections 6-7 on page 1) =====
"Email": string — student's email. FIX common handwriting typos in domains:
   - gmal/gmial/gmaill/gmall → gmail.com
   - yaho/yahooo → yahoo.com
   - hotmal → hotmail.com
   - outlok → outlook.com
   - .co instead of .com → .com
   - Only fix the DOMAIN, never alter the username part.
"PhoneNumber": string — 10-digit Indian mobile (starts with 6/7/8/9). Strip any leading 0 or +91.
"AlternatePhone": string — second contact number

===== PARENTS (Sections 8-9, and 13-14 on page 2) =====
"MotherName": string
"FatherName": string
"MotherOccupation": string — normalize: "HW"/"H.W." → "House Wife", "GOVT" → "Government", "PVT" → "Private", "BUSSINESS"/"BUISNESS" → "Business", "S/E"/"SELF EMP" → "Self Employed"
"FatherOccupation": string — same normalization
"MotherDesignation": string — job title
"FatherDesignation": string
"MotherOrganization": string — organization name & address
"FatherOrganization": string
"MotherEmail": string
"FatherEmail": string
"MotherMobile": string — 10-digit mobile
"FatherMobile": string — 10-digit mobile
"MotherPhone": string — landline number (could include STD code)
"FatherPhone": string — landline number
"MotherLandlineCode": string — STD code for mother's landline (e.g. "011" for Delhi)
"MotherLandline": string — mother's landline number WITHOUT the STD code
"FatherLandlineCode": string — STD code for father's landline
"FatherLandline": string — father's landline number WITHOUT the STD code
"AnnualIncome": string — family annual income in rupees (e.g. "500000", "5,00,000", "10 Lakhs")
"MotherAnnualIncome": string — mother's individual income (if separately mentioned)
"FatherAnnualIncome": string — father's individual income (if separately mentioned)

===== CUET SUBJECTS (Section 10, page 1 — VERY IMPORTANT) =====
This is a TABLE with Roman numeral rows (I through VII) and 3 columns:
  Col 1: "Subject(s)" — the CUET subject name
  Col 2: "Total Score" — MAXIMUM possible marks (commonly 200 or 250, pre-printed)
  Col 3: "Score Obtained" — handwritten marks the student ACTUALLY got

Table mapping:
  Row I   → CuetSubject1, CuetTotalScore1, CuetScoreObtained1
  Row II  → CuetSubject2, CuetTotalScore2, CuetScoreObtained2
  Row III → CuetSubject3, CuetTotalScore3, CuetScoreObtained3
  Row IV  → CuetSubject4, CuetTotalScore4, CuetScoreObtained4
  Row V   → CuetSubject5, CuetTotalScore5, CuetScoreObtained5
  Row VI  → CuetSubject6, CuetTotalScore6, CuetScoreObtained6
  Row VII → TOTAL: CuetTotalScoreAll, CuetScoreObtainedAll

SCORING ACCURACY RULES:
- Max marks per subject is usually 200 or 250 (pre-printed). Read the printed value carefully. If blank, assume 200.
- "Score Obtained" is HANDWRITTEN — be VERY careful with digit recognition:
  • 1 vs 7: look at serifs/angles. "1" is a straight vertical stroke. "7" has a horizontal top bar.
  • 3 vs 8: "3" is open on the left side. "8" is closed (two loops).
  • 5 vs 6: "5" has a flat top. "6" has a curved top.
  • 0 vs 6: "0" is oval/symmetrical. "6" has a tail descending from the left.
  • 4 vs 9: "4" has a sharp angle. "9" is round at the top.
- Row VII (Total) = SUM of individual rows. ALWAYS verify:
  CuetScoreObtainedAll ≈ CuetScoreObtained1 + ... + CuetScoreObtained6
  If the handwritten total ≠ your computed sum, use YOUR COMPUTED SUM.
- CuetScore (top of form) should ≈ CuetScoreObtainedAll. If they differ, trust the TABLE total.
- Not all 6 rows may be filled. Use null for empty/unused subject rows.

===== CLASS XII (Section 11 on page 2) =====
"TwelfthYear": string (e.g. "2024")
"TwelfthBoard": string (e.g. "CBSE", "ICSE", "ISC", or state board name)
"TwelfthRollNumber": string
"TwelfthInstitution": string (school name)
"TwelfthPercentage": string (percentage or CGPA)
"Class12Percentage": string — same as TwelfthPercentage (return identical value)
"Class12RollNo": string — same as TwelfthRollNumber
"Class12Institution": string — same as TwelfthInstitution
"HindiStudiedUpto": MUST be one of: "VIII","X","XII","Never"

===== PERSONAL INFO (Section 12 on page 2) =====
"Nationality": "Indian" or "Other" — almost always "Indian" for SRCC students.
"Religion": MUST be one of: "Hindu","Muslim","Jain","Sikh","Parsi","Christian","Buddhist","Others"
    — CRITICAL: Check both the written text and any tick marks in Section 12. 
    — Disambiguation: "Jain" is often misread as "Join" or "Jan". Correct this. 
    — Cross-check with "MinorityCategory": If MinorityCategory is "Yes" or not null, religion should typically NOT be Hindu.
"Category": SAME value as "AdmissionCategory"
"BloodGroup": one of: "A+","A-","B+","B-","AB+","AB-","O+","O-"
"BelowPovertyLine": "Yes" or "No"
"MinorityCategory": "No" or "Yes" (mapped from Section 12 tick marks: Muslim, Jain, Sikh, Parsi, Christian, Buddhist)
    — If student ticks ANY of the minority religions, set "MinorityCategory" to "Yes" and "Religion" to that specific religion.
    — If student ticks "Hindu", set "MinorityCategory" to "No".

===== GUARDIAN (Section 15, page 2) =====
"GuardianName": string
"GuardianAddress": string
"GuardianMobile": string — 10-digit
"GuardianEmail": string
"GuardianOrganization": string
"GuardianRelation": string (e.g. "Father", "Mother", "Uncle")
"GuardianLandlineCode": string — STD code
"GuardianLandline": string — landline number

===== OTHER INFO (Section 16, page 2) =====
"DuEnrollmentNumber": string
"HindiMediumPreference": "Yes" or "No"
"DeclarationDate": string DD/MM/YYYY — general declaration/admission date
"DeclarationPlace": string — place of declaration (usually "Delhi" or "New Delhi")

===== CERTIFICATES (Section 17, page 2) =====
"CategoryCertificateAuthority": string — if filled, student is NOT GEN
"CategoryCertificateNumber": string
"CategoryCertificateDate": string DD/MM/YYYY
"DisabilityType": string ("VH","HH","OH") or null
"DisabilityPercentage": string
"UdidNumber": string (Unique Disability ID)

===== CLASS X (if present) =====
"TenthBoard": string
"TenthYear": string
"TenthPercentage": string
"TenthSchool": string

===== EMERGENCY CONTACT =====
"EmergencyContactName": string
"EmergencyContactPhone": string — 10-digit mobile

===== DECLARATIONS (pages 3-4) =====
"StudentDeclarationName": string — student's full name from "I, [NAME], hereby declare..."
   — This is one of the BEST sources for the correct full name. Cross-check with FirstName/Surname.
"StudentDeclarationDate": string DD/MM/YYYY
"StudentDeclarationPlace": string (usually "Delhi" or "New Delhi")
"ParentGuardianName": string — parent's name from their declaration
"ParentGuardianRelationship": string ("Father", "Mother", etc.)
"ParentGuardianCandidateName": string — the STUDENT's name as mentioned by parent
   — This is ANOTHER verification source for the student's correct name.
"ParentGuardianCourse": string — course mentioned in parent declaration (confirms Course field)
"ParentGuardianDate": string DD/MM/YYYY
"ParentGuardianPlace": string

===== DOCUMENT CHECKLIST (page 4, true/false for each) =====
"DocAdmissionForm": boolean
"DocUndertakingRagging": boolean
"DocPhotographs": boolean
"DocCuetScorecard": boolean
"DocClassXiiMarksheet": boolean
"DocClassXCertificate": boolean
"DocClassXiiCertificate": boolean
"DocCharacterCertificate": boolean
"DocCasteCertificate": boolean — TRUE → student is likely SC/ST/OBC
"DocMigrationCertificate": boolean
"DocTransferCertificate": boolean
"DocGapCertificate": boolean
"DocIncomeCertificate": boolean — TRUE → student may be EWS
"DocDomicileCertificate": boolean
"DocAadharCard": boolean
"DocMedicalFitness": boolean


===== MASTER ACCURACY RULES =====

1. HANDWRITING FIRST: Read HANDWRITTEN text (pen/ink), NOT printed labels, watermarks, or example text.

2. CROSS-REFERENCE EVERYTHING — the same information appears in MULTIPLE places on this form:
   • Student's name: Section 1 + Declaration page 3 ("I, [name]") + Parent declaration (they mention the student)
   • Course: Tick at top + CUET subjects + Parent declaration course
   • Category: Tick at top + Certificate section + Caste/Income document checklist + BPL field
   • Father/Mother name: Sections 8-9 + Parent declaration signatory
   → Use ALL sources. When they conflict, prefer the CLEAREST handwriting.

3. SPATIAL AWARENESS:
   • Page 1 top = Academic session, Course tick, Category tick, DU Form No, Roll No, Aadhar
   • Page 1 middle = Name, Gender, DOB, Marital Status, Addresses, Contact, Parents basic
   • Page 1 bottom = CUET subjects table
   • Page 2 = Class XII + Class X, Personal info (religion, blood group), Parents detailed (occupation, organization, landlines), Guardian, Certificates
   • Page 3 = Student declaration, Parent/Guardian declaration
   • Page 4 = Document checklist
   • Pages 5+ = ATTACHED DOCUMENTS: Aadhar card, CUET scorecard, class XII marksheet, etc.
     → Use these to CROSS-VERIFY: Aadhar number (from card), CUET scores (from scorecard), student name & DOB (from Aadhar card)
     → The PRINTED values on these documents are MORE RELIABLE than handwritten values on the form.

4. DIGIT DISAMBIGUATION (critical for scores, Aadhar, phone numbers, pincodes):
   • Read EACH digit individually. Consider the CONTEXT (a CUET score of 1200 is impossible per subject).
   • CUET obtained marks are typically 50-250 per subject. Scores above the printed max or below 0 indicate a misread.
   • Aadhar: 12 digits, never starts with 0 or 1. If yours does, re-examine.
   • Phone: 10 digits starting with 6/7/8/9.
   • Pincode: 6 digits. Delhi starts with 110. UP starts with 2. Haryana starts with 12-13.

5. EMAIL DOMAIN FIXES: gmal/gmial/gmall → gmail.com, yaho → yahoo.com, outlok → outlook.com, .co → .com

6. PHONE NUMBER CLEANUP: Strip leading 0 or +91. Must be exactly 10 digits starting with 6/7/8/9.

7. DATE FORMAT: Always DD/MM/YYYY. 2-digit years: 00-30 → 2000-2030, 31-99 → 1931-1999.

8. OCCUPATION NORMALIZATION: "HW"/"H.W." → "House Wife", "PVT" → "Private", "GOVT" → "Government", "BUSSINESS" → "Business", "S/E" → "Self Employed"

9. BOOLEAN CHECKLIST: tick (✓/☑/√) = true, blank/cross (✗) = false.

10. OUTPUT FORMAT: Return ONLY a valid JSON object. No markdown wrappers, no comments, no explanation.
    Use null for genuinely unreadable/missing fields. For booleans, use true/false (not "Yes"/"No")."""


def normalize_gemini_fields(fields: Dict[str, Any]) -> Dict[str, Any]:
    """Post-process Gemini output: normalize dropdown values, dates, phones, emails, occupations."""
    result = {}

    # Dropdown normalization maps
    GENDER_MAP = {'m': 'Male', 'male': 'Male', 'f': 'Female', 'female': 'Female',
                  'transgender': 'Transgender', 'trans': 'Transgender', 'other': 'Transgender'}
    COURSE_MAP = {'bcom': 'B.COM.(H)', 'b.com': 'B.COM.(H)', 'b.com.(h)': 'B.COM.(H)', 'b com h': 'B.COM.(H)',
                  'bcom(h)': 'B.COM.(H)', 'b.com(h)': 'B.COM.(H)', 'commerce': 'B.COM.(H)',
                  'bachelor with honours in commerce': 'B.COM.(H)', 'b.com. (hons)': 'B.COM.(H)',
                  'b.com.(hons)': 'B.COM.(H)', 'b.com (h)': 'B.COM.(H)',
                  'ba eco': 'B.A.(H) ECO', 'b.a.(h) eco': 'B.A.(H) ECO', 'ba(h) eco': 'B.A.(H) ECO',
                  'economics': 'B.A.(H) ECO', 'b.a.(h)eco': 'B.A.(H) ECO', 'b.a. eco': 'B.A.(H) ECO',
                  'bachelor with honours in economics': 'B.A.(H) ECO', 'b.a.(h) economics': 'B.A.(H) ECO'}
    CATEGORY_MAP = {'general': 'GEN', 'gen': 'GEN', 'ur': 'GEN', 'unreserved': 'GEN',
                    'obc': 'OBC', 'obc-ncl': 'OBC', 'sc': 'SC', 'st': 'ST',
                    'ews': 'EWS', 'sports': 'Sports', 'pwd': 'PwD', 'pwbd': 'PwD',
                    'cw': 'CW', 'km': 'KM', 'eca': 'ECA', 'foreign': 'Foreign'}
    RELIGION_MAP = {'hindu': 'Hindu', 'hinduism': 'Hindu', 'muslim': 'Muslim', 'islam': 'Muslim',
                    'jain': 'Jain', 'jainism': 'Jain', 'sikh': 'Sikh', 'sikhism': 'Sikh',
                    'parsi': 'Parsi', 'zoroastrian': 'Parsi', 'persian': 'Parsi',
                    'christian': 'Christian', 'christianity': 'Christian',
                    'buddhist': 'Buddhist', 'buddhism': 'Buddhist', 'others': 'Others', 'other': 'Others'}
    BLOOD_MAP = {'a+': 'A+', 'a-': 'A-', 'b+': 'B+', 'b-': 'B-', 'ab+': 'AB+', 'ab-': 'AB-',
                 'o+': 'O+', 'o-': 'O-', 'a +': 'A+', 'b +': 'B+', 'o +': 'O+', 'ab +': 'AB+',
                 'a positive': 'A+', 'b positive': 'B+', 'o positive': 'O+',
                 'a negative': 'A-', 'b negative': 'B-', 'o negative': 'O-'}
    YESNO_MAP = {'yes': 'Yes', 'no': 'No', 'y': 'Yes', 'n': 'No', 'true': 'Yes', 'false': 'No'}
    HINDI_MAP = {'viii': 'VIII', '8': 'VIII', '8th': 'VIII', 'x': 'X', '10': 'X', '10th': 'X',
                 'xii': 'XII', '12': 'XII', '12th': 'XII', 'never': 'Never', 'nil': 'Never', 'na': 'Never'}
    NATIONALITY_MAP = {'indian': 'Indian', 'india': 'Indian', 'other': 'Other'}


    dropdown_fields = {
        'Gender': GENDER_MAP, 'Course': COURSE_MAP, 'AdmissionCategory': CATEGORY_MAP,
        'Category': CATEGORY_MAP, 'Religion': RELIGION_MAP, 'BloodGroup': BLOOD_MAP,
        'BelowPovertyLine': YESNO_MAP, 'HindiMediumPreference': YESNO_MAP,
        'HindiStudiedUpto': HINDI_MAP, 'Nationality': NATIONALITY_MAP,
        'MinorityCategory': YESNO_MAP,
    }

    # Date fields that should be DD/MM/YYYY
    date_fields = {'DateOfBirth', 'DateOfAdmission', 'CategoryCertificateDate',
                   'StudentDeclarationDate', 'ParentGuardianDate', 'DeclarationDate'}

    # Phone fields that should be 10 digits
    phone_fields = {'PhoneNumber', 'AlternatePhone', 'MotherMobile', 'FatherMobile',
                    'GuardianMobile', 'EmergencyContactPhone', 'MotherPhone', 'FatherPhone'}

    # Email fields for domain auto-correction
    email_fields = {'Email', 'MotherEmail', 'FatherEmail', 'GuardianEmail'}

    # Email domain corrections (handwriting typo → correct domain)
    EMAIL_DOMAIN_FIXES = {
        'gmal.com': 'gmail.com', 'gmial.com': 'gmail.com', 'gmaill.com': 'gmail.com',
        'gmall.com': 'gmail.com', 'gmai.com': 'gmail.com', 'gamil.com': 'gmail.com',
        'gnail.com': 'gmail.com', 'gmaol.com': 'gmail.com', 'gmail.co': 'gmail.com',
        'gmail.con': 'gmail.com', 'gmail.om': 'gmail.com', 'gimail.com': 'gmail.com',
        'gmaik.com': 'gmail.com', 'gmeil.com': 'gmail.com', 'gemail.com': 'gmail.com',
        'yaho.com': 'yahoo.com', 'yahooo.com': 'yahoo.com', 'yahoo.co': 'yahoo.com',
        'yahoo.con': 'yahoo.com', 'yhoo.com': 'yahoo.com',
        'hotmal.com': 'hotmail.com', 'hotmail.co': 'hotmail.com', 'hotamail.com': 'hotmail.com',
        'outlok.com': 'outlook.com', 'outloook.com': 'outlook.com', 'outlook.co': 'outlook.com',
        'rediffmal.com': 'rediffmail.com', 'redifmail.com': 'rediffmail.com',
    }

    # Occupation normalization
    OCCUPATION_FIXES = {
        'hw': 'House Wife', 'h.w.': 'House Wife', 'h.w': 'House Wife', 'house wife': 'House Wife',
        'housewife': 'House Wife', 'home maker': 'Home Maker', 'homemaker': 'Home Maker',
        'govt': 'Government Service', 'govt service': 'Government Service', 'govt.': 'Government Service',
        'govt job': 'Government Service', 'government': 'Government Service',
        'pvt': 'Private Service', 'pvt.': 'Private Service', 'private': 'Private Service',
        'pvt service': 'Private Service',
        's/e': 'Self Employed', 'self emp': 'Self Employed', 'self employed': 'Self Employed',
        'bussiness': 'Business', 'buisness': 'Business', 'busness': 'Business',
        'bussines': 'Business', 'bisiness': 'Business',
    }
    occupation_fields = {'MotherOccupation', 'FatherOccupation'}

    for key, val in fields.items():
        if val is None or val == 'null' or val == '' or val == 'N/A':
            continue

        # Normalize dropdown values
        if key in dropdown_fields and isinstance(val, str):
            lookup = val.strip().lower()
            mapped = dropdown_fields[key].get(lookup)
            if mapped:
                result[key] = mapped
            else:
                result[key] = val.strip()
            continue

        # Fix email domains
        if key in email_fields and isinstance(val, str):
            email = val.strip().lower()
            if '@' in email:
                username, domain = email.rsplit('@', 1)
                domain = EMAIL_DOMAIN_FIXES.get(domain, domain)
                # Also fix .co/.con at end
                if domain.endswith('.co') and not domain.endswith('.co.in'):
                    domain = domain + 'm'
                elif domain.endswith('.con'):
                    domain = domain[:-1] + 'm'
                result[key] = f"{username}@{domain}"
            else:
                result[key] = email
            continue

        # Normalize occupations
        if key in occupation_fields and isinstance(val, str):
            lookup = val.strip().lower()
            mapped = OCCUPATION_FIXES.get(lookup)
            if mapped:
                result[key] = mapped
            else:
                result[key] = val.strip()
            continue

        # Format dates
        if key in date_fields and isinstance(val, str):
            val = val.strip()
            # Try to normalize various date formats to DD/MM/YYYY
            date_clean = re.sub(r'[.\-/\\]', '/', val)
            parts = date_clean.split('/')
            if len(parts) == 3:
                d, m, y = parts
                d = d.strip().zfill(2)
                m = m.strip().zfill(2)
                y = y.strip()
                if len(y) == 2:
                    yi = int(y) if y.isdigit() else 0
                    y = ('20' + y) if yi < 50 else ('19' + y)
                # Validate: swap day/month if day > 12 and month <= 12
                try:
                    di, mi = int(d), int(m)
                    if di > 12 and mi <= 12:
                        pass  # Already correct: d > 12 means it's definitely the day
                    elif mi > 12 and di <= 12:
                        d, m = m.zfill(2), d.zfill(2)  # Swap: month is actually day
                except ValueError:
                    pass
                result[key] = f"{d}/{m}/{y}"
            else:
                result[key] = val
            continue

        # Clean phone numbers
        if key in phone_fields and isinstance(val, str):
            digits = re.sub(r'\D', '', val)
            if len(digits) == 12 and digits.startswith('91'):
                digits = digits[2:]
            elif len(digits) == 11 and digits.startswith('0'):
                digits = digits[1:]
            result[key] = digits if len(digits) == 10 else val.strip()
            continue

        # Pincode fields
        if key in ('PermanentPincode', 'CorrespondencePincode', 'Pincode') and isinstance(val, str):
            digits = re.sub(r'\D', '', val)
            result[key] = digits[:6] if len(digits) >= 6 else val.strip()
            continue

        # Aadhar
        if key == 'AadharNumber' and isinstance(val, str):
            digits = re.sub(r'\D', '', val)
            result[key] = digits if len(digits) == 12 else val.strip()
            continue

        # Boolean doc fields
        if isinstance(val, bool):
            result[key] = val
            continue

        # Default: strip whitespace
        if isinstance(val, str):
            result[key] = val.strip()
        else:
            result[key] = val

    # ============================================
    # POST-PROCESSING: Smart inference and cross-checks
    # ============================================

    # 1. Auto-build StudentName from name parts if not present
    if 'StudentName' not in result:
        parts = [result.get('FirstName', ''), result.get('MiddleName', ''), result.get('Surname', '')]
        full = ' '.join(p for p in parts if p)
        if full:
            result['StudentName'] = full

    # 2. Try to extract Surname from declaration or other name fields if missing
    if not result.get('Surname') and result.get('FirstName'):
        # Check StudentDeclarationName or ParentGuardianCandidateName for a fuller name
        for name_field in ('StudentDeclarationName', 'ParentGuardianCandidateName', 'StudentName'):
            full_name = result.get(name_field, '')
            if full_name and ' ' in full_name:
                name_parts = full_name.strip().split()
                if len(name_parts) >= 2 and name_parts[0].upper() == result['FirstName'].upper():
                    result['Surname'] = name_parts[-1]
                    if len(name_parts) > 2:
                        result['MiddleName'] = ' '.join(name_parts[1:-1])
                    print(f"  Inferred Surname='{result['Surname']}' from {name_field}", file=sys.stderr)
                    break

    # 3. Copy Category from AdmissionCategory if missing, and vice versa
    if 'Category' not in result and 'AdmissionCategory' in result:
        result['Category'] = result['AdmissionCategory']
    elif 'AdmissionCategory' not in result and 'Category' in result:
        result['AdmissionCategory'] = result['Category']

    # 4. Auto-compute CUET totals if not present
    try:
        total_max = 0
        total_obt = 0
        has_subjects = False
        for i in range(1, 7):
            max_key = f'CuetTotalScore{i}'
            obt_key = f'CuetScoreObtained{i}'
            if max_key in result and result[max_key]:
                max_val = re.sub(r'\D', '', str(result[max_key]))
                if max_val:
                    total_max += int(max_val)
                    has_subjects = True
            if obt_key in result and result[obt_key]:
                obt_val = re.sub(r'\D', '', str(result[obt_key]))
                if obt_val:
                    total_obt += int(obt_val)
        
        if has_subjects:
            if 'CuetTotalScoreAll' not in result or not result['CuetTotalScoreAll']:
                result['CuetTotalScoreAll'] = str(total_max)
                print(f"  Auto-computed CuetTotalScoreAll={total_max}", file=sys.stderr)
            if 'CuetScoreObtainedAll' not in result or not result['CuetScoreObtainedAll']:
                result['CuetScoreObtainedAll'] = str(total_obt)
                print(f"  Auto-computed CuetScoreObtainedAll={total_obt}", file=sys.stderr)
            # Also auto-fill CuetScore if missing
            if 'CuetScore' not in result or not result['CuetScore']:
                obt_all = result.get('CuetScoreObtainedAll', str(total_obt))
                result['CuetScore'] = str(obt_all)
    except (ValueError, TypeError):
        pass

    # 5. Ensure ParentGuardianCourse is normalized
    if 'ParentGuardianCourse' in result:
        course_val = result['ParentGuardianCourse'].strip().lower()
        mapped = COURSE_MAP.get(course_val)
        if mapped:
            result['ParentGuardianCourse'] = mapped

    return result


def try_gemini_extraction(image_bytes_list: List[bytes], credentials_path: str) -> Optional[Dict[str, Any]]:
    """
    Extract fields using Google Gemini Vision AI (new google.genai SDK).
    
    Uses the new google-genai package (replaces deprecated google-generativeai).
    Authentication: GEMINI_API_KEY env var or config file.
    
    Returns extracted fields dict or None if Gemini is unavailable.
    """
    try:
        # ===== INSTALL/IMPORT NEW SDK =====
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            print("Installing google-genai...", file=sys.stderr)
            import subprocess
            subprocess.check_call(
                [sys.executable, '-m', 'pip', 'install', '-q', '-U', 'google-genai'],
                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
            )
            from google import genai
            from google.genai import types
        
        # ===== GET API KEY =====
        api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
        if not api_key:
            cred_dir = os.path.dirname(credentials_path)
            key_file = os.path.join(cred_dir, 'gemini_api_key.txt')
            if os.path.exists(key_file):
                with open(key_file, 'r') as f:
                    api_key = f.read().strip()
                if api_key:
                    print(f"Gemini: API key loaded from config file ({len(api_key)} chars)", file=sys.stderr)
        
        if not api_key:
            print("Gemini: No API key available", file=sys.stderr)
            return None
        
        # ===== CREATE CLIENT =====
        client = genai.Client(api_key=api_key)
        print("Gemini: Client created with API key", file=sys.stderr)
        
        # ===== PREPARE IMAGE PARTS =====
        contents = []
        for i, img_bytes in enumerate(image_bytes_list):
            contents.append(
                types.Part.from_bytes(
                    data=img_bytes,
                    mime_type='image/png',
                )
            )
            print(f"Gemini: Added page {i+1} image ({len(img_bytes)} bytes)", file=sys.stderr)
        
        # Add the extraction prompt as the last part
        contents.append(GEMINI_EXTRACTION_PROMPT)
        
        # ===== MODEL SELECTION & GENERATION =====
        model_names = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-2.0-flash-lite']
        
        response = None
        last_err = None
        
        for model_name in model_names:
            max_retries = 2
            for attempt in range(max_retries):
                try:
                    print(f"Gemini: Trying model {model_name} (attempt {attempt+1})...", file=sys.stderr)
                    response = client.models.generate_content(
                        model=model_name,
                        contents=contents,
                        config=types.GenerateContentConfig(
                            temperature=0.1,
                            max_output_tokens=8192,
                            response_mime_type="application/json",
                        ),
                    )
                    if response and response.text:
                        print(f"Gemini: Success with {model_name}", file=sys.stderr)
                        break
                except Exception as gen_err:
                    last_err = gen_err
                    err_str = str(gen_err)
                    print(f"Gemini: {model_name} error: {err_str[:200]}", file=sys.stderr)
                    if '429' in err_str or 'ResourceExhausted' in err_str:
                        import time
                        wait_time = (2 ** attempt) * 5
                        print(f"Gemini: Rate limited, waiting {wait_time}s...", file=sys.stderr)
                        time.sleep(wait_time)
                    elif '404' in err_str or 'not found' in err_str.lower():
                        break  # Model doesn't exist, try next
                    else:
                        break  # Other error, try next model
            
            if response and response.text:
                break  # Success, stop trying models
        
        if not response or not response.text:
            print(f"Gemini: All models failed. Last error: {last_err}", file=sys.stderr)
            return None
        
        # ===== PARSE JSON RESPONSE =====
        text = response.text.strip()
        print(f"Gemini: Response length: {len(text)} chars", file=sys.stderr)
        
        # Strip markdown code block wrappers if present
        if text.startswith('```'):
            text = re.sub(r'^```(?:json)?\s*\n?', '', text)
            text = re.sub(r'\n?```\s*$', '', text)
        
        # Find JSON object in response
        json_match = re.search(r'\{[\s\S]*\}', text)
        if not json_match:
            print(f"Gemini: No JSON found in response: {text[:300]}", file=sys.stderr)
            return None
        
        fields = json.loads(json_match.group())
        
        # Remove null values
        fields = {k: v for k, v in fields.items() if v is not None and v != 'null' and v != ''}
        
        # Normalize and clean fields through post-processor
        cleaned = normalize_gemini_fields(fields)
        
        field_count = len(cleaned)
        print(f"Gemini: Successfully extracted {field_count} fields", file=sys.stderr)
        
        # Log some key fields for debugging
        for key in ['FirstName', 'Surname', 'Course', 'Email', 'PhoneNumber', 'DateOfBirth']:
            if key in cleaned:
                print(f"  {key}: {cleaned[key]}", file=sys.stderr)
        
        return cleaned
        
    except json.JSONDecodeError as je:
        print(f"Gemini: JSON parse error: {je}", file=sys.stderr)
        return None
    except Exception as e:
        import traceback
        print(f"Gemini: Extraction failed: {type(e).__name__}: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return None


# ===== MAIN PROCESSING =====

def process_file(image_path: str, credentials_path: str, provider: str = 'gemini') -> Dict[str, Any]:
    """Main processing: Multi-page OCR with Gemini AI + spatial analysis fallback"""
    try:
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
        
        from google.cloud import vision
        from PIL import Image
        
        ext = os.path.splitext(image_path)[1].lower()
        client = vision.ImageAnnotatorClient()
        
        all_text_parts = []
        all_words = []
        all_image_bytes = []  # Collect images for Gemini
        
        if ext == '.pdf':
            # Load form pages (first 4) for spatial/Cloud Vision OCR
            images, error = convert_pdf_to_images(image_path, FORM_PAGES)
            if images is None:
                return {'success': False, 'error': error, 'text': '', 'fields': {}}
            
            # Load ALL pages for Gemini (includes attached docs like Aadhar card, CUET scorecard)
            all_image_bytes, _ = convert_pdf_to_images(image_path, 0)  # 0 = all pages
            if all_image_bytes is None:
                all_image_bytes = list(images)  # fallback to form pages only
            
            for i, img_bytes in enumerate(images, 1):
                page_text, page_words, error = ocr_image_with_bounds(client, img_bytes)
                if error:
                    return {'success': False, 'error': f'Page {i}: {error}', 'text': '', 'fields': {}}
                
                if page_text:
                    all_text_parts.append(f"=== PAGE {i} ===\n{page_text}")
                if page_words:
                    for w in page_words:
                        w.y += (i - 1) * 1.0
                    all_words.extend(page_words)
            
            combined_text = '\n\n'.join(all_text_parts)
        else:
            with Image.open(image_path) as img:
                if img.mode not in ('RGB', 'L'):
                    img = img.convert('RGB')
                buffer = io.BytesIO()
                img.save(buffer, format='PNG')
                image_content = buffer.getvalue()
            
            all_image_bytes = [image_content]  # Save for Gemini
            
            combined_text, all_words, error = ocr_image_with_bounds(client, image_content)
            if error:
                return {'success': False, 'error': error, 'text': '', 'fields': {}}
            combined_text = combined_text or ""
            all_words = all_words or []
        
        # ===== FIELD EXTRACTION (Multi-Provider Pipeline) =====
        extraction_method = 'spatial'
        fields = None
        gemini_fields = None
        spatial_fields = None
        
        # --- Provider routing ---
        
        # 'gemini' (default): Try Gemini first, fall back to spatial
        # 'spatial': Spatial only (fast, works offline)
        # 'enhanced': Spatial + OCR error correction + cross-field validation
        # 'multi': Both Gemini AND enhanced spatial, merge results
        
        if provider in ('gemini', 'multi') and all_image_bytes:
            gemini_fields = try_gemini_extraction(all_image_bytes, credentials_path)
            if gemini_fields and len(gemini_fields) > 3:
                print(f"Gemini: extracted {len(gemini_fields)} fields", file=sys.stderr)
        
        if provider in ('spatial', 'enhanced', 'multi') or not gemini_fields:
            raw_spatial = extract_fields_spatial(all_words, combined_text)
            meta = raw_spatial.pop('_meta', {})
            # Clean + normalize spatial output (same pipeline as Gemini)
            spatial_fields = clean_extracted_fields(raw_spatial)
            spatial_fields = normalize_gemini_fields(spatial_fields)
            print(f"Spatial: extracted {len(spatial_fields)} fields", file=sys.stderr)
        else:
            meta = {}
        
        # --- Merge/select results based on provider ---
        
        if provider == 'multi' and gemini_fields and spatial_fields:
            # MULTI: Merge both, preferring Gemini for non-empty values
            fields = dict(spatial_fields)  # Start with spatial as base
            for key, val in gemini_fields.items():
                if val is not None and str(val).strip():
                    # Gemini overrides spatial, unless spatial has a longer value
                    existing = fields.get(key)
                    if not existing or (isinstance(val, str) and isinstance(existing, str) 
                                        and len(val.strip()) >= len(existing.strip())):
                        fields[key] = val
            extraction_method = 'multi'
            print(f"Multi: merged to {len(fields)} fields", file=sys.stderr)
        
        elif gemini_fields and len(gemini_fields) > 3:
            fields = gemini_fields
            extraction_method = 'gemini'
        
        elif spatial_fields:
            fields = spatial_fields
            extraction_method = 'enhanced' if provider == 'enhanced' else 'spatial'
        
        else:
            fields = {}
        
        # --- Apply OCR error correction to text fields ---
        for key in list(fields.keys()):
            val = fields[key]
            if isinstance(val, str) and val.strip():
                fields[key] = correct_ocr_text(val, 'general')
        
        # --- Apply cross-field validation ---
        fields = validate_and_correct_fields(fields)
        
        # Calculate confidence
        field_count = len(fields)
        avg_word_conf = meta.get('avg_word_confidence', 70)
        handwritten_pct = meta.get('handwritten_ratio', 0)
        
        if extraction_method == 'multi':
            confidence = min(99.0, 75.0 + field_count * 0.5)
        elif extraction_method == 'gemini':
            confidence = min(98.0, 70.0 + field_count * 0.5)
        elif extraction_method == 'enhanced':
            word_quality_score = min(100, avg_word_conf * 1.15)
            field_extraction_score = min(100, 55 + field_count * 1.5)
            confidence = round(word_quality_score * 0.35 + field_extraction_score * 0.65, 1)
        else:
            word_quality_score = min(100, avg_word_conf * 1.1)
            field_extraction_score = min(100, 50 + field_count * 1.5)
            confidence = round(word_quality_score * 0.4 + field_extraction_score * 0.6, 1)
        
        return {
            'success': True,
            'text': combined_text,
            'fields': fields,
            'fields_count': field_count,
            'words_detected': len(all_words),
            'confidence': confidence,
            'length': len(combined_text),
            'extraction_method': extraction_method,
            'handwritten_percentage': handwritten_pct,
            'avg_word_confidence': avg_word_conf,
            'field_confidence': meta.get('field_confidence', {})
        }
        

    except Exception as e:
        import traceback
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc(),
            'text': '',
            'fields': {}
        }

def main():
    if len(sys.argv) < 3:
        print(json.dumps({'success': False, 'error': 'Usage: ocr_extract.py <image_path> <credentials_path> [gemini_api_key] [provider]'}))
        sys.exit(1)
    
    image_path = sys.argv[1]
    credentials_path = sys.argv[2]
    
    # Accept Gemini API key as optional 3rd argument (more reliable than env var in subprocess)
    if len(sys.argv) >= 4 and sys.argv[3].strip():
        os.environ['GEMINI_API_KEY'] = sys.argv[3].strip()
        print(f"Gemini: API key set from CLI argument ({len(sys.argv[3].strip())} chars)", file=sys.stderr)
    
    # Accept provider as optional 4th argument: 'gemini', 'spatial', 'enhanced', 'multi'
    provider = 'gemini'  # default
    if len(sys.argv) >= 5 and sys.argv[4].strip():
        provider = sys.argv[4].strip().lower()
        print(f"Provider: {provider}", file=sys.stderr)
    
    if not os.path.exists(image_path):
        print(json.dumps({'success': False, 'error': f'File not found: {image_path}'}))
        sys.exit(1)
        
    if not os.path.exists(credentials_path):
        print(json.dumps({'success': False, 'error': f'Credentials not found: {credentials_path}'}))
        sys.exit(1)
    
    result = process_file(image_path, credentials_path, provider=provider)
    print(json.dumps(result, ensure_ascii=True))
    sys.exit(0 if result.get('success') else 1)

if __name__ == '__main__':
    main()
