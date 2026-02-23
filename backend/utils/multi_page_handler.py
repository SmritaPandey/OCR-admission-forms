"""
Multi-Page Form Handler
Treats multiple pages as a single form unit and combines OCR results
"""
from typing import List, Dict, Any, Optional
from PIL import Image
from backend.ocr.base_provider import OCRProvider

class MultiPageFormHandler:
    """Handle multi-page forms (e.g., 3 pages) as single units"""
    
    def __init__(self, pages_per_form: int = 3):
        self.pages_per_form = pages_per_form
    
    async def process_multi_page_form(
        self,
        pages: List[Image.Image],
        ocr_provider: OCRProvider,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process multiple pages as a single form
        
        Args:
            pages: List of PIL Images (one per page)
            ocr_provider: OCR provider instance
            language: Optional language code
        
        Returns:
            Combined OCR result with all pages
        """
        if not pages:
            raise ValueError("No pages provided")
        
        if len(pages) != self.pages_per_form:
            # Allow flexible page count with warning
            pass
        
        # Process each page separately
        page_results = []
        combined_text = []
        all_structured_data = {}
        
        for page_num, page in enumerate(pages, 1):
            try:
                page_result = await ocr_provider.extract_text(page, language)
                page_results.append({
                    "page_number": page_num,
                    "raw_text": page_result.get("raw_text", ""),
                    "confidence": page_result.get("confidence", 0),
                    "structured_data": page_result.get("structured_data", {}),
                    "provider": page_result.get("provider", ""),
                    "metadata": page_result.get("metadata", {})
                })
                
                # Combine text with page separator
                if page_result.get("raw_text"):
                    combined_text.append(f"--- Page {page_num} ---\n{page_result.get('raw_text')}")
                
                # Merge structured data (later pages override earlier ones for same keys)
                if page_result.get("structured_data"):
                    all_structured_data.update(page_result["structured_data"])
                    
            except Exception as e:
                page_results.append({
                    "page_number": page_num,
                    "error": str(e),
                    "raw_text": "",
                    "confidence": 0
                })
        
        # Calculate overall confidence
        valid_confidences = [
            r.get("confidence", 0) 
            for r in page_results 
            if r.get("confidence", 0) > 0
        ]
        avg_confidence = sum(valid_confidences) / len(valid_confidences) if valid_confidences else 0
        
        # Combine all text
        full_text = "\n\n".join(combined_text)
        
        return {
            "raw_text": full_text,
            "confidence": avg_confidence,
            "structured_data": all_structured_data,
            "provider": page_results[0].get("provider", "") if page_results else "",
            "pages": page_results,
            "total_pages": len(pages),
            "pages_per_form": self.pages_per_form,
            "metadata": {
                "form_type": "multi_page",
                "page_count": len(pages)
            }
        }
    
    def extract_fields_across_pages(
        self,
        combined_result: Dict[str, Any],
        field_mappings: Optional[Dict[str, List[int]]] = None
    ) -> Dict[str, Any]:
        """
        Extract fields that may span across multiple pages
        
        Args:
            combined_result: Combined OCR result from process_multi_page_form
            field_mappings: Optional dict mapping field names to page numbers where they appear
        
        Returns:
            Dictionary with extracted fields prioritized by page
        """
        extracted_fields = {}
        
        # If field mappings provided, use them to find fields on specific pages
        if field_mappings:
            for field_name, page_numbers in field_mappings.items():
                for page_num in page_numbers:
                    if page_num <= len(combined_result.get("pages", [])):
                        page_result = combined_result["pages"][page_num - 1]
                        page_data = page_result.get("structured_data", {})
                        if field_name in page_data and field_name not in extracted_fields:
                            extracted_fields[field_name] = page_data[field_name]
                            break
        
        # Otherwise, merge all structured data (later pages override)
        else:
            for page_result in combined_result.get("pages", []):
                page_data = page_result.get("structured_data", {})
                extracted_fields.update(page_data)
        
        return extracted_fields
    
    def validate_page_count(self, pages: List[Any]) -> bool:
        """Validate that the correct number of pages is provided"""
        return len(pages) == self.pages_per_form
    
    def get_page_context(self, pages: List[Image.Image], page_num: int) -> Dict[str, Any]:
        """Get context information for a specific page"""
        if page_num < 1 or page_num > len(pages):
            return {}
        
        page = pages[page_num - 1]
        return {
            "page_number": page_num,
            "total_pages": len(pages),
            "width": page.width,
            "height": page.height,
            "mode": page.mode,
            "is_first": page_num == 1,
            "is_last": page_num == len(pages),
            "is_middle": 1 < page_num < len(pages)
        }

