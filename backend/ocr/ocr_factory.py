from typing import Optional
from backend.ocr.base_provider import OCRProvider
from backend.ocr.tesseract_provider import TesseractProvider
from backend.config import settings

# Lazy imports for optional providers
def _get_google_provider():
    try:
        from backend.ocr.google_vision_provider import GoogleVisionProvider
        return GoogleVisionProvider
    except ImportError:
        return None

def _get_azure_provider():
    try:
        from backend.ocr.azure_vision_provider import AzureVisionProvider
        return AzureVisionProvider
    except ImportError:
        return None

def _get_abbyy_provider():
    try:
        from backend.ocr.abbyy_provider import ABBYYProvider
        return ABBYYProvider
    except ImportError:
        return None

class OCRFactory:
    """Factory class for creating OCR provider instances"""
    
    @classmethod
    def _get_providers(cls) -> dict:
        """Get providers dictionary with lazy loading"""
        providers = {
            "tesseract": TesseractProvider,
        }
        
        google_provider = _get_google_provider()
        if google_provider:
            providers["google"] = google_provider
        
        azure_provider = _get_azure_provider()
        if azure_provider:
            providers["azure"] = azure_provider
        
        abbyy_provider = _get_abbyy_provider()
        if abbyy_provider:
            providers["abbyy"] = abbyy_provider
        
        return providers
    
    @classmethod
    def create_provider(cls, provider_name: Optional[str] = None) -> OCRProvider:
        """
        Create an OCR provider instance
        
        Args:
            provider_name: Name of the provider (tesseract, google, azure, abbyy)
                          If None, uses default from settings
        
        Returns:
            OCRProvider instance
            
        Raises:
            ValueError: If provider name is invalid or provider is not available
        """
        if provider_name is None:
            provider_name = settings.OCR_PROVIDER.lower()
        
        providers = cls._get_providers()
        
        if provider_name not in providers:
            available = ", ".join(providers.keys())
            raise ValueError(f"Invalid OCR provider '{provider_name}'. Available: {available}")
        
        provider_class = providers[provider_name]
        provider = provider_class()
        
        if not provider.is_available():
            raise ValueError(
                f"OCR provider '{provider_name}' is not available. "
                "Please check your configuration."
            )
        
        return provider
    
    @classmethod
    def get_available_providers(cls) -> list[str]:
        """Get list of available and configured providers"""
        available = []
        providers = cls._get_providers()
        for name, provider_class in providers.items():
            try:
                provider = provider_class()
                if provider.is_available():
                    available.append(name)
            except Exception:
                pass
        return available

def get_ocr_provider(provider_name: Optional[str] = None) -> OCRProvider:
    """Convenience function to get OCR provider"""
    return OCRFactory.create_provider(provider_name)

