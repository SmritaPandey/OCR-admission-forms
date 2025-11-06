"""
Azure Form Recognizer provider - Best for structured forms
Excellent for detecting checkboxes, radio buttons, and form fields
"""
from typing import Dict, Any, Optional
from PIL import Image
import io
from backend.ocr.base_provider import OCRProvider
from backend.config import settings

class AzureFormRecognizerProvider(OCRProvider):
    """Azure Form Recognizer - Excellent for structured forms"""
    
    def __init__(self):
        self.name = "azure-form-recognizer"
        self._client = None
    
    def _get_client(self):
        """Get or create Form Recognizer client"""
        if self._client is None:
            try:
                from azure.ai.formrecognizer import DocumentAnalysisClient
                from azure.core.credentials import AzureKeyCredential
                
                if not settings.AZURE_FORM_RECOGNIZER_ENDPOINT or not settings.AZURE_FORM_RECOGNIZER_KEY:
                    raise ValueError("AZURE_FORM_RECOGNIZER_ENDPOINT and AZURE_FORM_RECOGNIZER_KEY required")
                
                self._client = DocumentAnalysisClient(
                    endpoint=settings.AZURE_FORM_RECOGNIZER_ENDPOINT,
                    credential=AzureKeyCredential(settings.AZURE_FORM_RECOGNIZER_KEY)
                )
            except ImportError:
                raise ImportError("azure-ai-formrecognizer not installed. Install with: pip install azure-ai-formrecognizer")
        
        return self._client
    
    async def extract_text(self, image: Image.Image, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract text using Azure Form Recognizer
        Excellent for structured forms with checkboxes and radio buttons
        """
        try:
            client = self._get_client()
            
            # Convert PIL Image to bytes
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            
            # Analyze document (prebuilt-document model is good for forms)
            poller = client.begin_analyze_document(
                model_id="prebuilt-document",  # Good for forms
                document=img_byte_arr.getvalue()
            )
            result = poller.result()
            
            # Extract text
            raw_text = ""
            if result.content:
                raw_text = result.content
            
            # Extract form fields (key-value pairs)
            form_fields = {}
            if result.key_value_pairs:
                for kvp in result.key_value_pairs:
                    if kvp.key and kvp.value:
                        form_fields[kvp.key.content] = kvp.value.content
            
            # Extract checkboxes and selection marks
            checkboxes = []
            if result.pages:
                for page in result.pages:
                    if hasattr(page, 'selection_marks') and page.selection_marks:
                        for mark in page.selection_marks:
                            checkboxes.append({
                                "state": mark.state,  # 'selected' or 'unselected'
                                "confidence": mark.confidence,
                                "bounding_box": [{"x": p.x, "y": p.y} for p in mark.polygon] if hasattr(mark, 'polygon') else []
                            })
            
            # Extract tables
            tables = []
            if result.tables:
                for table in result.tables:
                    tables.append({
                        "row_count": table.row_count,
                        "column_count": table.column_count,
                        "cells": [{"content": cell.content, "row_index": cell.row_index, "column_index": cell.column_index} 
                                 for cell in table.cells] if hasattr(table, 'cells') else []
                    })
            
            structured_data = {
                "text": raw_text,
                "form_fields": form_fields,
                "checkboxes": checkboxes,
                "tables": tables,
                "pages": len(result.pages) if result.pages else 1
            }
            
            # Calculate average confidence
            confidences = []
            if result.pages:
                for page in result.pages:
                    if hasattr(page, 'confidence') and page.confidence:
                        confidences.append(page.confidence * 100)
            
            avg_confidence = sum(confidences) / len(confidences) if confidences else 90.0
            
            return {
                "raw_text": raw_text.strip(),
                "confidence": round(avg_confidence, 2),
                "structured_data": structured_data,
                "provider": self.get_provider_name()
            }
            
        except Exception as e:
            raise Exception(f"Azure Form Recognizer error: {str(e)}")
    
    def is_available(self) -> bool:
        """Check if Azure Form Recognizer is configured"""
        try:
            if not settings.AZURE_FORM_RECOGNIZER_ENDPOINT or not settings.AZURE_FORM_RECOGNIZER_KEY:
                return False
            # Try to import
            from azure.ai.formrecognizer import DocumentAnalysisClient
            return True
        except ImportError:
            return False
    
    def get_provider_name(self) -> str:
        return "azure-form-recognizer"

