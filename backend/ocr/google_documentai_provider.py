"""
Google Cloud Document AI provider - Best for forms and handwriting
Specifically designed for structured document parsing
"""
from typing import Dict, Any, Optional
from PIL import Image
import io
import os
from backend.ocr.base_provider import OCRProvider
from backend.config import settings

class GoogleDocumentAIProvider(OCRProvider):
    """Google Cloud Document AI - Excellent for forms and handwriting"""
    
    def __init__(self):
        self.name = "google-documentai"
        self._client = None
    
    def _get_client(self):
        """Get or create Document AI client"""
        if self._client is None:
            try:
                from google.cloud import documentai
                
                # Check for credentials
                if settings.GOOGLE_APPLICATION_CREDENTIALS:
                    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = settings.GOOGLE_APPLICATION_CREDENTIALS
                
                if not settings.GOOGLE_DOCUMENT_AI_PROJECT_ID:
                    raise ValueError("GOOGLE_DOCUMENT_AI_PROJECT_ID not configured")
                
                self._client = documentai.DocumentProcessorServiceClient()
            except ImportError:
                raise ImportError("google-cloud-documentai not installed. Install with: pip install google-cloud-documentai")
        
        return self._client
    
    async def extract_text(self, image: Image.Image, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract text using Google Document AI Form Parser
        Excellent for structured forms with checkboxes, radio buttons, and dropdowns
        """
        try:
            client = self._get_client()
            
            # Convert PIL Image to bytes
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            
            # Get processor path
            project_id = settings.GOOGLE_DOCUMENT_AI_PROJECT_ID
            location = settings.GOOGLE_DOCUMENT_AI_LOCATION
            processor_id = settings.GOOGLE_DOCUMENT_AI_PROCESSOR_ID
            
            if not processor_id:
                # Use general form parser if no specific processor
                processor_id = "form-parser"  # Default form parser
            
            processor_name = f"projects/{project_id}/locations/{location}/processors/{processor_id}"
            
            # Create request
            raw_document = documentai.RawDocument(
                content=img_byte_arr.getvalue(),
                mime_type="image/png"
            )
            
            request = documentai.ProcessRequest(
                name=processor_name,
                raw_document=raw_document
            )
            
            # Process document
            result = client.process_document(request=request)
            document = result.document
            
            # Extract text
            raw_text = document.text if hasattr(document, 'text') else ""
            
            # Extract form fields (key-value pairs)
            form_fields = {}
            if hasattr(document, 'entities') and document.entities:
                for entity in document.entities:
                    if hasattr(entity, 'type_') and hasattr(entity, 'mention_text'):
                        form_fields[entity.type_] = entity.mention_text
            
            # Extract structured data (forms, tables, etc.)
            structured_data = {
                "text": raw_text,
                "form_fields": form_fields,
                "pages": len(document.pages) if hasattr(document, 'pages') else 1
            }
            
            # Document AI doesn't provide confidence scores directly
            # Using a high default for handwriting recognition
            avg_confidence = 92.0 if raw_text.strip() else 0.0
            
            return {
                "raw_text": raw_text.strip(),
                "confidence": round(avg_confidence, 2),
                "structured_data": structured_data,
                "provider": self.get_provider_name()
            }
            
        except Exception as e:
            raise Exception(f"Google Document AI error: {str(e)}")
    
    def is_available(self) -> bool:
        """Check if Google Document AI is configured"""
        try:
            if not settings.GOOGLE_DOCUMENT_AI_PROJECT_ID:
                return False
            # Try to import
            from google.cloud import documentai
            return True
        except ImportError:
            return False
    
    def get_provider_name(self) -> str:
        return "google-documentai"

