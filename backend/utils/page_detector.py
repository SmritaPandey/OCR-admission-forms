"""
Page Detection Utility
Detects which page type each page is based on content markers.
This makes extraction robust to page order variations (e.g., pages 2 and 3 swapped).
"""
from typing import Optional, Dict, List
import re


class PageDetector:
    """Detect page types based on content markers"""
    
    # Content markers for each page type
    PAGE_MARKERS = {
        'page1': [
            r"STUDENT'?S\s+DATA\s+FORM",
            r"NAME\s+IN\s+BLOCK\s+LETTERS",
            r"CUET\s+SCORE",
            r"COLLEGE\s+ROLL\s+NO",
            r"DU\s+PORTAL\s+FORM\s+NUMBER",
            r"ACADEMIC\s+SESSION",
            r"DETAILS\s+OF\s+MARKS\s+OBTAINED\s+IN\s+QUALIFYING\s+EXAMINATION",
            r"COURSE\s*\(.*?\)",
        ],
        'page2': [
            r"DECLARATION\s+&\s+UNDERTAKING\s+BY\s+THE\s+STUDENT",
            r"DETAILS\s+OF\s+QUALIFYING\s+EXAMINATION\s+PASSED",
            r"CLASS[-\s]*XII",
            r"YEAR\s+OF\s+PASSING",
            r"BOARD\s*/\s*UNIVERSITY",
            r"PERSONAL\s+INFORMATION",
            r"NATIONALITY",
            r"RELIGION",
            r"BLOOD\s+GROUP",
        ],
        'page3': [
            r"MOTHER'?S\s+OCCUPATIONAL\s+DETAILS",
            r"FATHER'?S\s+OCCUPATIONAL\s+DETAILS",
            r"LOCAL\s+GUARDIAN'?S\s+DETAILS",
            r"WHETHER\s+BELOW\s+POVERTY\s+LINE",
            r"PARENT'?S\s*/\s*FAMILY\s+ANNUAL\s+INCOME",
            r"DU\s+ENROLLMENT",
            r"OTHER\s+INFORMATION",
            r"DELHI\s+UNIVERSITY\s+ENROLMENT",
        ],
        'page4': [
            r"DOCUMENTS\s+REQUIRED",
            r"SELF[-\s]*ATTESTED\s+COPIES",
            r"PHOTOGRAPHS\s+PASTED",
            r"CUET\s+SCORE\s+CARD",
            r"DETAILED\s+MARK\s+SHEET",
            r"CERTIFICATE\s+AND\s+MARK\s+SHEET",
            r"CHARACTER\s+CERTIFICATE",
            r"TRANSFER\s+CERTIFICATE",
            r"MIGRATION\s+CERTIFICATE",
        ]
    }
    
    @classmethod
    def detect_page_type(cls, text: str) -> Optional[str]:
        """
        Detect which type of page this is based on content markers.
        
        Args:
            text: OCR text from a single page
            
        Returns:
            Page type: 'page1', 'page2', 'page3', 'page4', or None
        """
        text_upper = text.upper()
        
        # Count matches for each page type
        scores = {}
        for page_type, markers in cls.PAGE_MARKERS.items():
            score = 0
            for marker_pattern in markers:
                if re.search(marker_pattern, text_upper, re.IGNORECASE):
                    score += 1
            scores[page_type] = score
        
        # Return page type with highest score
        max_score = max(scores.values())
        if max_score > 0:
            return max(scores, key=scores.get)
        
        return None
    
    @classmethod
    def detect_pages_from_text(cls, combined_text: str) -> List[Dict[str, any]]:
        """
        Detect page types from combined text with page markers.
        
        Args:
            combined_text: Combined OCR text with page markers like "--- Page X ---"
            
        Returns:
            List of dicts with 'page_number', 'page_type', 'text'
        """
        # Split text by page markers
        page_pattern = r'---\s*Page\s+(\d+)\s*---'
        pages = []
        
        # Find all page markers
        matches = list(re.finditer(page_pattern, combined_text, re.IGNORECASE))
        
        if not matches:
            # No page markers - treat as single page
            page_type = cls.detect_page_type(combined_text)
            return [{
                'page_number': 1,
                'page_type': page_type,
                'text': combined_text
            }]
        
        # Extract each page's text
        for i, match in enumerate(matches):
            page_num = int(match.group(1))
            start_pos = match.end()
            
            # Find end position (start of next page or end of text)
            if i + 1 < len(matches):
                end_pos = matches[i + 1].start()
            else:
                end_pos = len(combined_text)
            
            page_text = combined_text[start_pos:end_pos].strip()
            page_type = cls.detect_page_type(page_text)
            
            pages.append({
                'page_number': page_num,
                'page_type': page_type,
                'text': page_text
            })
        
        return pages
    
    @classmethod
    def reorder_pages_by_type(cls, pages: List[Dict[str, any]]) -> List[Dict[str, any]]:
        """
        Reorder pages to standard order (page1, page2, page3, page4) based on detected types.
        
        Args:
            pages: List of page dicts with 'page_type' field
            
        Returns:
            Reordered pages list
        """
        # Standard order
        type_order = {'page1': 1, 'page2': 2, 'page3': 3, 'page4': 4}
        
        # Sort by detected type (unknown types go last)
        def get_sort_key(page):
            page_type = page.get('page_type')
            return type_order.get(page_type, 99)
        
        return sorted(pages, key=get_sort_key)
