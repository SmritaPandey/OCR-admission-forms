from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
from msrest.authentication import CognitiveServicesCredentials
from typing import Dict, Any, Optional
from PIL import Image
import io
import time
from backend.ocr.base_provider import OCRProvider
from backend.config import settings

class AzureVisionProvider(OCRProvider):
    """Azure Computer Vision API provider"""
    
    def __init__(self):
        self.name = "azure"
        self._client = None
    
    def _get_client(self):
        """Initialize and return Azure Vision client"""
        if self._client is None:
            if not settings.AZURE_VISION_KEY or not settings.AZURE_VISION_ENDPOINT:
                raise Exception("Azure Vision API key and endpoint not configured")
            
            credentials = CognitiveServicesCredentials(settings.AZURE_VISION_KEY)
            self._client = ComputerVisionClient(
                settings.AZURE_VISION_ENDPOINT,
                credentials
            )
        return self._client
    
    async def extract_text(self, image: Image.Image, language: Optional[str] = None) -> Dict[str, Any]:
        """Extract text using Azure Computer Vision API"""
        try:
            client = self._get_client()
            
            # Convert PIL Image to bytes
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            
            # Perform OCR
            read_response = client.read_in_stream(img_byte_arr, raw=True)
            read_operation_location = read_response.headers["Operation-Location"]
            operation_id = read_operation_location.split("/")[-1]
            
            # Wait for OCR to complete
            while True:
                read_result = client.get_read_result(operation_id)
                if read_result.status not in [OperationStatusCodes.running, OperationStatusCodes.not_started]:
                    break
                time.sleep(1)
            
            # Extract text
            raw_text = ""
            if read_result.status == OperationStatusCodes.succeeded:
                for text_result in read_result.analyze_result.read_results:
                    for line in text_result.lines:
                        raw_text += line.text + "\n"
            
            # Azure doesn't provide confidence scores in the standard API
            # Using a reasonable default for handwriting recognition
            avg_confidence = 90.0 if raw_text.strip() else 0.0
            
            return {
                "raw_text": raw_text.strip(),
                "confidence": round(avg_confidence, 2),
                "structured_data": None,
                "provider": self.get_provider_name()
            }
        except Exception as e:
            raise Exception(f"Azure Vision API error: {str(e)}")
    
    def is_available(self) -> bool:
        """Check if Azure Vision is configured"""
        try:
            return bool(settings.AZURE_VISION_KEY and settings.AZURE_VISION_ENDPOINT)
        except Exception:
            return False
    
    def get_provider_name(self) -> str:
        return "azure"

