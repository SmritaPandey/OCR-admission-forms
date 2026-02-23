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

def _get_gpt4_vision_provider():
    try:
        from backend.ocr.gpt4_vision_provider import GPT4VisionProvider
        return GPT4VisionProvider
    except ImportError:
        return None

def _get_claude_vision_provider():
    try:
        from backend.ocr.claude_vision_provider import ClaudeVisionProvider
        return ClaudeVisionProvider
    except ImportError:
        return None

def _get_ollama_provider():
    try:
        from backend.ocr.ollama_provider import OllamaProvider
        return OllamaProvider
    except ImportError:
        return None

def _get_tesseract_google_combined_provider():
    try:
        from backend.ocr.tesseract_google_combined_provider import TesseractGoogleCombinedProvider
        return TesseractGoogleCombinedProvider
    except ImportError:
        return None

def _get_craft_trocr_provider():
    try:
        from backend.ocr.craft_trocr_provider import CraftTrocrProvider
        return CraftTrocrProvider
    except ImportError:
        return None

def _get_craft_provider():
    try:
        from backend.ocr.craft_provider import CraftProvider
        return CraftProvider
    except ImportError:
        return None

def _get_trocr_provider():
    try:
        from backend.ocr.trocr_provider import TrocrProvider
        return TrocrProvider
    except ImportError:
        return None

def _get_unified_extractor():
    """Get unified extractor (combines Google Vision + SRCC extractors)"""
    try:
        from backend.ocr.unified_extractor import UnifiedExtractorWithTraining
        return UnifiedExtractorWithTraining
    except ImportError:
        return None

def _get_ensemble_provider():
    """Get ensemble OCR provider (combines fine-tuned TrOCR + Tesseract)"""
    try:
        from backend.ocr.ensemble_provider import EnsembleOCRProvider
        return EnsembleOCRProvider
    except ImportError:
        return None

def _get_smart_document_ai_provider():
    """Get Smart Document AI provider (VLM-based — Qwen2.5-VL)"""
    try:
        from backend.ocr.smart_document_ai import SmartDocumentAI
        return SmartDocumentAI
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
        
        # Combined Tesseract + Google Vision (best of both worlds)
        if (settings.OCR_ENABLE_TESSERACT and settings.OCR_ENABLE_GOOGLE_VISION and 
            settings.OCR_ENABLE_TESSERACT_GOOGLE_COMBINED):
            combined_provider = _get_tesseract_google_combined_provider()
            if combined_provider:
                providers["tesseract-google-combined"] = combined_provider
                providers["combined"] = combined_provider  # Alias
        
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
        
        # GPT-4 Vision (only if enabled)
        if settings.OCR_ENABLE_GPT4_VISION:
            gpt4_vision_provider = _get_gpt4_vision_provider()
            if gpt4_vision_provider:
                providers["gpt4-vision"] = gpt4_vision_provider
        
        # Claude Vision (only if enabled)
        if settings.OCR_ENABLE_CLAUDE_VISION:
            claude_vision_provider = _get_claude_vision_provider()
            if claude_vision_provider:
                providers["claude-vision"] = claude_vision_provider
        
        # Ollama (only if enabled)
        if settings.OCR_ENABLE_OLLAMA:
            ollama_provider = _get_ollama_provider()
            if ollama_provider:
                providers["ollama"] = ollama_provider
        
        # CRAFT + TR-OCR for handwritten text recognition
        if settings.OCR_ENABLE_CRAFT_TROCR:
            craft_trocr_provider = _get_craft_trocr_provider()
            if craft_trocr_provider:
                providers["craft-trocr"] = craft_trocr_provider
        
        # Separate CRAFT provider (text detection only)
        if settings.OCR_ENABLE_CRAFT:
            craft_provider = _get_craft_provider()
            if craft_provider:
                providers["craft"] = craft_provider
        
        # Separate TR-OCR provider (text recognition only)
        if settings.OCR_ENABLE_TROCR:
            trocr_provider = _get_trocr_provider()
            if trocr_provider:
                providers["trocr"] = trocr_provider
        
        # Unified extractor - combines Google Vision + SRCC-specific extractors with training
        # This is the recommended provider for SRCC admission forms
        unified = _get_unified_extractor()
        if unified:
            providers["unified"] = unified
            providers["best"] = unified  # Alias - unified is the best provider for SRCC forms
        
        # Ensemble OCR - combines fine-tuned TrOCR + enhanced Tesseract
        ensemble = _get_ensemble_provider()
        if ensemble:
            providers["ensemble"] = ensemble
        
        # Smart Document AI - VLM-based (Qwen2.5-VL) — world-class form extraction
        smart_doc_ai = _get_smart_document_ai_provider()
        if smart_doc_ai:
            providers["smart-document-ai"] = smart_doc_ai
            providers["document-ai"] = smart_doc_ai  # Alias
            # Override 'best' — VLM-based is the most accurate
            providers["best"] = smart_doc_ai
        
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
        """Get list of available and configured providers (no duplicates/aliases)"""
        available = []
        providers = cls._get_providers()
        
        # Define canonical names (skip aliases like "google", "azure", "combined")
        alias_names = {"google", "azure", "combined"}
        
        for name, provider_class in providers.items():
            # Skip alias names to avoid duplicates
            if name in alias_names:
                continue
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
                    provider = providers[default_provider]()
                    if provider.is_available():
                        available.append(default_provider)
                    else:
                        for name, provider_class in providers.items():
                            if name in alias_names:
                                continue
                            try:
                                test_provider = provider_class()
                                if test_provider.is_available():
                                    available.append(name)
                                    break
                            except Exception:
                                pass
                except Exception:
                    for name, provider_class in providers.items():
                        if name != default_provider and name not in alias_names:
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

