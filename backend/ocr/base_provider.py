from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from PIL import Image
import io

class OCRProvider(ABC):
    """Abstract base class for OCR providers"""
    
    @abstractmethod
    async def extract_text(self, image: Image.Image, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract text from an image using OCR
        
        Args:
            image: PIL Image object
            language: Optional language code (e.g., 'eng', 'fra')
            
        Returns:
            Dictionary containing:
                - raw_text: Extracted text as string
                - confidence: Average confidence score (0-100)
                - structured_data: Optional structured data extracted
                - provider: Name of the OCR provider used
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the OCR provider is available/configured
        
        Returns:
            True if provider can be used, False otherwise
        """
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the name of this OCR provider"""
        pass

