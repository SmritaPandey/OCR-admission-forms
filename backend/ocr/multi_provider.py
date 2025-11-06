"""
Multi-provider OCR service that tries multiple providers and selects the best result
"""
from typing import Dict, Any, Optional, List
from PIL import Image
from backend.ocr.ocr_factory import OCRFactory
from backend.ocr.base_provider import OCRProvider
import asyncio

class MultiProviderOCR:
    """OCR service that tries multiple providers and returns the best result"""
    
    def __init__(self):
        self.available_providers = OCRFactory.get_available_providers()
    
    async def extract_with_best_provider(self, image: Image.Image, 
                                         language: Optional[str] = None,
                                         providers: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Try multiple OCR providers and return the best result based on confidence
        
        Args:
            image: PIL Image to process
            language: Optional language code
            providers: List of provider names to try. If None, tries all available.
        
        Returns:
            Dictionary with OCR result from the best provider
        """
        if providers is None:
            providers = self.available_providers
        
        if not providers:
            raise ValueError("No OCR providers available")
        
        results = []
        
        # Try each provider
        for provider_name in providers:
            try:
                provider = OCRFactory.create_provider(provider_name)
                result = await provider.extract_text(image, language)
                result['provider_used'] = provider_name
                results.append(result)
            except Exception as e:
                # If provider fails, continue with others
                continue
        
        if not results:
            raise Exception("All OCR providers failed")
        
        # Select best result based on confidence and text length
        best_result = max(results, key=lambda r: self._score_result(r))
        
        # Add information about all attempts
        best_result['all_attempts'] = [
            {
                'provider': r['provider_used'],
                'confidence': r.get('confidence', 0),
                'text_length': len(r.get('raw_text', ''))
            }
            for r in results
        ]
        
        return best_result
    
    def _score_result(self, result: Dict[str, Any]) -> float:
        """
        Score a result based on confidence and text quality
        
        Args:
            result: OCR result dictionary
        
        Returns:
            Score (higher is better)
        """
        confidence = result.get('confidence', 0)
        text = result.get('raw_text', '')
        text_length = len(text.strip())
        
        # Score = confidence * (1 + text_length/1000)
        # This favors longer text with good confidence
        score = confidence * (1 + text_length / 1000)
        
        return score
    
    async def extract_with_all_providers(self, image: Image.Image,
                                        language: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract text using all available providers and return all results
        
        Args:
            image: PIL Image to process
            language: Optional language code
        
        Returns:
            Dictionary with results from all providers
        """
        providers = self.available_providers
        all_results = {}
        
        # Try all providers in parallel
        tasks = []
        for provider_name in providers:
            try:
                provider = OCRFactory.create_provider(provider_name)
                tasks.append(self._extract_with_provider(provider, image, language, provider_name))
            except Exception:
                continue
        
        if not tasks:
            raise Exception("No OCR providers available")
        
        # Run all extractions
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect successful results
        for i, result in enumerate(results):
            if not isinstance(result, Exception):
                provider_name = providers[i]
                all_results[provider_name] = result
        
        if not all_results:
            raise Exception("All OCR providers failed")
        
        # Find best result
        best_provider = max(all_results.keys(), 
                           key=lambda p: self._score_result(all_results[p]))
        
        return {
            'best_provider': best_provider,
            'best_result': all_results[best_provider],
            'all_results': all_results
        }
    
    async def _extract_with_provider(self, provider: OCRProvider, image: Image.Image,
                                    language: Optional[str], provider_name: str) -> Dict[str, Any]:
        """Extract text with a specific provider"""
        try:
            result = await provider.extract_text(image, language)
            result['provider_used'] = provider_name
            return result
        except Exception as e:
            raise Exception(f"{provider_name} failed: {str(e)}")

