"""
Form element detection utilities
Detects checkboxes, radio buttons, and dropdowns from OCR results
"""
from typing import Dict, Any, List, Optional
import re

class FormElementDetector:
    """Detect form elements like checkboxes, radio buttons, and dropdowns"""
    
    # Patterns for detecting checkboxes
    CHECKBOX_PATTERNS = [
        r'\[([\sxX])\]',  # [ ] or [x] or [X]
        r'\(([\sxX])\)',  # ( ) or (x) or (X)
        r'☐|☑|✓',  # Unicode checkbox symbols
        r'□|■',  # Square symbols
    ]
    
    # Patterns for radio buttons
    RADIO_PATTERNS = [
        r'○|●',  # Circle symbols
        r'\(([\s•])\)',  # ( ) or (•)
        r'\[([\s•])\]',  # [ ] or [•]
    ]
    
    @staticmethod
    def detect_checkboxes(text: str, context_lines: int = 2) -> List[Dict[str, Any]]:
        """
        Detect checkboxes in text with their labels
        
        Args:
            text: OCR extracted text
            context_lines: Number of lines to include for context
        
        Returns:
            List of detected checkboxes with their state and label
        """
        checkboxes = []
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            # Check for checkbox patterns
            for pattern in FormElementDetector.CHECKBOX_PATTERNS:
                matches = re.finditer(pattern, line)
                for match in matches:
                    checkbox_char = match.group(1) if match.groups() else match.group(0)
                    is_checked = checkbox_char.lower() in ['x', '✓', '☑', '■', '•']
                    
                    # Extract label (text after checkbox)
                    label_start = match.end()
                    label = line[label_start:].strip()
                    
                    # If no label on same line, check next lines
                    if not label:
                        for j in range(1, context_lines + 1):
                            if i + j < len(lines):
                                label += " " + lines[i + j].strip()
                                if label.strip():
                                    break
                    
                    if label.strip():
                        checkboxes.append({
                            "type": "checkbox",
                            "checked": is_checked,
                            "label": label.strip(),
                            "line": i + 1,
                            "position": match.start()
                        })
        
        return checkboxes
    
    @staticmethod
    def detect_radio_buttons(text: str, context_lines: int = 2) -> List[Dict[str, Any]]:
        """
        Detect radio buttons in text with their labels
        
        Args:
            text: OCR extracted text
            context_lines: Number of lines to include for context
        
        Returns:
            List of detected radio buttons with their state and label
        """
        radio_buttons = []
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            # Check for radio button patterns
            for pattern in FormElementDetector.RADIO_PATTERNS:
                matches = re.finditer(pattern, line)
                for match in matches:
                    radio_char = match.group(1) if match.groups() else match.group(0)
                    is_selected = radio_char in ['•', '●'] or match.group(0) == '●'
                    
                    # Extract label (text after radio button)
                    label_start = match.end()
                    label = line[label_start:].strip()
                    
                    # If no label on same line, check next lines
                    if not label:
                        for j in range(1, context_lines + 1):
                            if i + j < len(lines):
                                label += " " + lines[i + j].strip()
                                if label.strip():
                                    break
                    
                    if label.strip():
                        radio_buttons.append({
                            "type": "radio",
                            "selected": is_selected,
                            "label": label.strip(),
                            "line": i + 1,
                            "position": match.start()
                        })
        
        return radio_buttons
    
    @staticmethod
    def detect_dropdowns(text: str) -> List[Dict[str, Any]]:
        """
        Detect dropdown selections in text
        
        Args:
            text: OCR extracted text
        
        Returns:
            List of detected dropdown selections
        """
        dropdowns = []
        lines = text.split('\n')
        
        # Pattern for dropdown labels (often followed by selected value)
        dropdown_patterns = [
            r'([A-Za-z\s]+):\s*([A-Za-z0-9\s]+)',  # "Field: Value"
            r'([A-Za-z\s]+)\s*[-–]\s*([A-Za-z0-9\s]+)',  # "Field - Value"
        ]
        
        for i, line in enumerate(lines):
            for pattern in dropdown_patterns:
                matches = re.finditer(pattern, line)
                for match in matches:
                    label = match.group(1).strip()
                    value = match.group(2).strip()
                    
                    # Check if it looks like a dropdown (common form field names)
                    dropdown_keywords = ['select', 'choose', 'option', 'category', 'type', 'gender', 
                                       'status', 'priority', 'level', 'grade', 'class']
                    
                    if any(keyword in label.lower() for keyword in dropdown_keywords):
                        dropdowns.append({
                            "type": "dropdown",
                            "label": label,
                            "value": value,
                            "line": i + 1
                        })
        
        return dropdowns
    
    @staticmethod
    def extract_all_form_elements(text: str) -> Dict[str, Any]:
        """
        Extract all form elements from text
        
        Args:
            text: OCR extracted text
        
        Returns:
            Dictionary with all detected form elements
        """
        return {
            "checkboxes": FormElementDetector.detect_checkboxes(text),
            "radio_buttons": FormElementDetector.detect_radio_buttons(text),
            "dropdowns": FormElementDetector.detect_dropdowns(text),
            "total_elements": 0
        }

