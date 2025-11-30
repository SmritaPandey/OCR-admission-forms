from typing import Optional
from backend.ocr.base_provider import OCRProvider
from backend.ocr.tesseract_provider import TesseractProvider
from backend.config import settings

# Lazy imports for optional providers
def _get_google_vision_provider():
    try:
        from backend.ocr.google_vision_provider import GoogleVisionProvider
        return GoogleVisionProvider
    except ImportError:
        return None

def _get_google_documentai_provider():
    try:
        from backend.ocr.google_documentai_provider import GoogleDocumentAIProvider
        return GoogleDocumentAIProvider
    except ImportError:
        return None

def _get_azure_provider():
    try:
        from backend.ocr.azure_vision_provider import AzureVisionProvider
        return AzureVisionProvider
    except ImportError:
        return None

def _get_azure_form_recognizer_provider():
    try:
        from backend.ocr.azure_form_recognizer_provider import AzureFormRecognizerProvider
        return AzureFormRecognizerProvider
    except ImportError:
        return None

def _get_aws_textract_provider():
    try:
        from backend.ocr.aws_textract_provider import AWSTextractProvider
        return AWSTextractProvider
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
        providers = {}

        if settings.OCR_ENABLE_TESSERACT:
            providers["tesseract"] = TesseractProvider
        
        # Google Cloud Vision
        if settings.OCR_ENABLE_GOOGLE_VISION:
            google_vision = _get_google_vision_provider()
            if google_vision:
                providers["google-vision"] = google_vision
                providers["google"] = google_vision  # Alias for backward compatibility
        
        # Google Cloud Document AI - Best for handwriting
        if settings.OCR_ENABLE_GOOGLE_DOCUMENT_AI:
            google_documentai = _get_google_documentai_provider()
            if google_documentai:
                providers["google-documentai"] = google_documentai
        
        # Azure Computer Vision
        if settings.OCR_ENABLE_AZURE_VISION:
            azure_provider = _get_azure_provider()
            if azure_provider:
                providers["azure-vision"] = azure_provider
                providers["azure"] = azure_provider  # Alias for backward compatibility
        
        # Azure Form Recognizer - Best for structured forms
        if settings.OCR_ENABLE_AZURE_FORM_RECOGNIZER:
            azure_form = _get_azure_form_recognizer_provider()
            if azure_form:
                providers["azure-form-recognizer"] = azure_form
        
        # AWS Textract
        if settings.OCR_ENABLE_AWS_TEXTRACT:
            aws_textract = _get_aws_textract_provider()
            if aws_textract:
                providers["aws-textract"] = aws_textract
        
        # ABBYY FineReader
        if settings.OCR_ENABLE_ABBYY:
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
                if provider.is_available() and name not in available:
                    available.append(name)
            except Exception:
                pass

        # If no providers are available, try to verify the default provider actually works
        if not available:
            default_provider = settings.OCR_PROVIDER.lower()
            if default_provider in providers:
                try:
                    # Actually test if the default provider is available
                    provider = providers[default_provider]()
                    if provider.is_available():
                        available.append(default_provider)
                    else:
                        # If default provider is not available, try to find any working provider
                        for name, provider_class in providers.items():
                            try:
                                test_provider = provider_class()
                                if test_provider.is_available():
                                    available.append(name)
                                    break
                            except Exception:
                                pass
                except Exception:
                    # If we can't instantiate the default provider, try others
                    for name, provider_class in providers.items():
                        if name != default_provider:
                            try:
                                test_provider = provider_class()
                                if test_provider.is_available():
                                    available.append(name)
                                    break
                            except Exception:
                                pass

        return available

def get_ocr_provider(provider_name: Optional[str] = None) -> OCRProvider:
    """Convenience function to get OCR provider"""
    return OCRFactory.create_provider(provider_name)

