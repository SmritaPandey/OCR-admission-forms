"""
AI-Powered Checkbox Detector
Uses vision models to detect checkboxes visually instead of regex patterns
"""
from typing import List, Dict, Any, Optional
from PIL import Image
import json

class AICheckboxDetector:
    """Detect checkboxes using AI vision models"""
    
    def __init__(self):
        pass
    
    def extract_checkboxes_from_ai_result(
        self,
        ai_result: Dict[str, Any],
        image: Optional[Image.Image] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract checkboxes from AI OCR result
        
        Args:
            ai_result: Dictionary with structured_data from AI OCR
            image: Optional PIL Image (for future bounding box extraction)
        
        Returns:
            List of detected checkboxes with labels and states
        """
        checkboxes = []
        structured_data = ai_result.get('structured_data', {})
        
        # Look for checkbox-related fields
        for key, value in structured_data.items():
            key_lower = key.lower()
            
            # Check if this looks like a checkbox field
            if any(indicator in key_lower for indicator in ['checkbox', 'checked', 'option', 'select']):
                checkbox_info = self._parse_checkbox_field(key, value)
                if checkbox_info:
                    checkboxes.append(checkbox_info)
            
            # Also check boolean values (might be checkboxes)
            if isinstance(value, bool):
                checkboxes.append({
                    'label': key,
                    'checked': value,
                    'confidence': 0.9,
                    'type': 'boolean'
                })
        
        # Look for checkbox arrays/objects
        for key, value in structured_data.items():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and 'checked' in item:
                        checkboxes.append({
                            'label': item.get('label', key),
                            'checked': item.get('checked', False),
                            'confidence': item.get('confidence', 0.8),
                            'type': 'checkbox'
                        })
        
        return checkboxes
    
    def _parse_checkbox_field(self, key: str, value: Any) -> Optional[Dict[str, Any]]:
        """Parse a checkbox field from structured data"""
        if isinstance(value, dict):
            # Dictionary with checkbox info
            return {
                'label': value.get('label', key),
                'checked': value.get('checked', False) if isinstance(value.get('checked'), bool) else False,
                'confidence': value.get('confidence', 0.8),
                'type': 'checkbox',
                'bounding_box': value.get('bounding_box'),
                'page': value.get('page')
            }
        elif isinstance(value, str):
            # String might indicate checked state
            value_lower = value.lower().strip()
            checked = value_lower in ['yes', 'true', '1', 'checked', 'x', '✓']
            return {
                'label': key,
                'checked': checked,
                'confidence': 0.7,
                'type': 'checkbox'
            }
        elif isinstance(value, bool):
            # Boolean value
            return {
                'label': key,
                'checked': value,
                'confidence': 0.9,
                'type': 'checkbox'
            }
        
        return None
    
    def extract_checkboxes_from_text(
        self,
        text: str,
        context_lines: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Fallback method: Extract checkboxes from raw text using patterns
        
        Args:
            text: Raw OCR text
            context_lines: Number of lines for context
        
        Returns:
            List of detected checkboxes
        """
        import re
        checkboxes = []
        lines = text.split('\n')
        
        # Checkbox patterns
        checkbox_patterns = [
            r'\[([\sxX✓])\]',  # [ ] or [x] or [✓]
            r'\(([\sxX✓])\)',  # ( ) or (x) or (✓)
            r'☐|☑|✓',  # Unicode checkbox symbols
            r'□|■',  # Square symbols
        ]
        
        for i, line in enumerate(lines):
            for pattern in checkbox_patterns:
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
                            'label': label.strip(),
                            'checked': is_checked,
                            'confidence': 0.6,  # Lower confidence for text-based detection
                            'type': 'checkbox',
                            'line': i + 1,
                            'position': match.start()
                        })
        
        return checkboxes
    
    def combine_checkbox_results(
        self,
        ai_checkboxes: List[Dict[str, Any]],
        text_checkboxes: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Combine checkbox results from AI and text-based detection
        
        Args:
            ai_checkboxes: Checkboxes from AI vision model
            text_checkboxes: Checkboxes from text pattern matching
        
        Returns:
            Combined list of checkboxes (AI results take priority)
        """
        combined = {}
        
        # Add AI checkboxes first (higher confidence)
        for cb in ai_checkboxes:
            label = cb.get('label', '').lower().strip()
            if label:
                combined[label] = cb
        
        # Add text checkboxes if not already present
        for cb in text_checkboxes:
            label = cb.get('label', '').lower().strip()
            if label and label not in combined:
                combined[label] = cb
        
        return list(combined.values())

