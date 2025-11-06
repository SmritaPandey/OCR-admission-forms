from typing import Dict, Any, Optional
from PIL import Image
import io
import requests
import base64
from backend.ocr.base_provider import OCRProvider
from backend.config import settings

class ABBYYProvider(OCRProvider):
    """ABBYY FineReader provider - excellent handwriting recognition"""
    
    def __init__(self):
        self.name = "abbyy"
        self._server_url = settings.ABBYY_SERVER_URL
        self._application_id = settings.ABBYY_APPLICATION_ID
        self._password = settings.ABBYY_PASSWORD
    
    async def extract_text(self, image: Image.Image, language: Optional[str] = None) -> Dict[str, Any]:
        """Extract text using ABBYY FineReader Server or Cloud OCR SDK"""
        try:
            # Convert PIL Image to base64
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            image_base64 = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
            
            # If server URL is configured, use FineReader Server API
            if self._server_url:
                return await self._extract_via_server(image_base64, language)
            # Otherwise, try Cloud OCR SDK (REST API)
            else:
                return await self._extract_via_cloud_sdk(image_base64, language)
                
        except Exception as e:
            raise Exception(f"ABBYY FineReader error: {str(e)}")
    
    async def _extract_via_server(self, image_base64: str, language: Optional[str]) -> Dict[str, Any]:
        """Extract text using ABBYY FineReader Server"""
        # FineReader Server REST API endpoint
        url = f"{self._server_url}/documentprocessing/processDocument"
        
        headers = {
            "Content-Type": "application/json"
        }
        
        payload = {
            "image": f"data:image/png;base64,{image_base64}",
            "language": language or "English",
            "exportFormat": "txt"
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        raw_text = result.get("text", "")
        confidence = result.get("confidence", 90.0)
        
        return {
            "raw_text": raw_text.strip(),
            "confidence": round(confidence, 2),
            "structured_data": None,
            "provider": self.get_provider_name()
        }
    
    async def _extract_via_cloud_sdk(self, image_base64: str, language: Optional[str]) -> Dict[str, Any]:
        """Extract text using ABBYY Cloud OCR SDK"""
        # ABBYY Cloud OCR SDK REST API
        url = "https://cloud-eu.ocrsdk.com/v2/processDocument"
        
        auth = (self._application_id, self._password)
        
        # Upload image
        files = {
            "file": base64.b64decode(image_base64)
        }
        
        params = {
            "language": language or "English",
            "exportFormat": "txt"
        }
        
        response = requests.post(url, files=files, params=params, auth=auth, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        raw_text = result.get("text", "")
        confidence = result.get("confidence", 90.0)
        
        return {
            "raw_text": raw_text.strip(),
            "confidence": round(confidence, 2),
            "structured_data": None,
            "provider": self.get_provider_name()
        }
    
    def is_available(self) -> bool:
        """Check if ABBYY is configured"""
        try:
            # Check if either server URL or application credentials are configured
            return bool(
                (self._server_url) or 
                (self._application_id and self._password)
            )
        except Exception:
            return False
    
    def get_provider_name(self) -> str:
        return "abbyy"

