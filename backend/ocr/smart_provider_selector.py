"""
Smart Provider Selector
Automatically select the best OCR provider based on form characteristics
"""
from typing import Dict, Any, Optional, List
from PIL import Image
from backend.ocr.ocr_factory import OCRFactory
from backend.config import settings

class SmartProviderSelector:
    """Intelligently select OCR provider based on form characteristics"""
    
    def __init__(self):
        self.available_providers = OCRFactory.get_available_providers()
        self.provider_capabilities = {
            "gpt4-vision": {
                "handwriting": 95,
                "printed": 90,
                "checkboxes": 90,
                "speed": 60,
                "cost": 30,
                "local": False
            },
            "claude-vision": {
                "handwriting": 93,
                "printed": 88,
                "checkboxes": 88,
                "speed": 65,
                "cost": 30,
                "local": False
            },
            "ollama": {
                "handwriting": 75,
                "printed": 80,
                "checkboxes": 70,
                "speed": 50,
                "cost": 95,
                "local": True
            },
            "google": {
                "handwriting": 85,
                "printed": 90,
                "checkboxes": 75,
                "speed": 70,
                "cost": 50,
                "local": False
            },
            "azure": {
                "handwriting": 70,
                "printed": 85,
                "checkboxes": 80,
                "speed": 75,
                "cost": 50,
                "local": False
            },
            "tesseract": {
                "handwriting": 50,
                "printed": 80,
                "checkboxes": 40,
                "speed": 85,
                "cost": 100,
                "local": True
            }
        }
    
    def select_best_provider(
        self,
        form_characteristics: Optional[Dict[str, Any]] = None,
        priority: str = "accuracy"
    ) -> str:
        """
        Select best provider based on form characteristics
        
        Args:
            form_characteristics: Dict with keys like 'is_handwritten', 'has_checkboxes', etc.
            priority: 'accuracy', 'speed', 'cost', or 'balanced'
        
        Returns:
            Provider name
        """
        if form_characteristics is None:
            form_characteristics = {}
        
        is_handwritten = form_characteristics.get('is_handwritten', True)
        has_checkboxes = form_characteristics.get('has_checkboxes', True)
        is_high_volume = form_characteristics.get('is_high_volume', False)
        requires_local = form_characteristics.get('requires_local', False)
        
        # Filter available providers
        candidates = [
            p for p in self.available_providers
            if p in self.provider_capabilities
        ]
        
        if not candidates:
            return "tesseract"  # Fallback
        
        # Score providers based on requirements
        scored_providers = []
        
        for provider in candidates:
            caps = self.provider_capabilities[provider]
            score = 0
            
            # Handwriting requirement
            if is_handwritten:
                score += caps['handwriting'] * 0.4
            
            # Checkbox requirement
            if has_checkboxes:
                score += caps['checkboxes'] * 0.3
            
            # Speed requirement (for high volume)
            if is_high_volume:
                score += caps['speed'] * 0.2
            else:
                score += (100 - caps['speed']) * 0.2  # Prefer accuracy over speed
            
            # Cost consideration (for high volume)
            if is_high_volume:
                score += caps['cost'] * 0.1
            
            # Local requirement
            if requires_local and not caps['local']:
                score = 0  # Disqualify
            
            scored_providers.append((provider, score))
        
        # Sort by score
        scored_providers.sort(key=lambda x: x[1], reverse=True)
        
        # Select based on priority
        if priority == "cost" and is_high_volume:
            # Prefer local/cost-effective providers for high volume
            for provider, _ in scored_providers:
                caps = self.provider_capabilities[provider]
                if caps['cost'] > 70:  # Prefer cheaper options
                    return provider
        
        # Return highest scoring provider
        return scored_providers[0][0] if scored_providers else "tesseract"
    
    def get_provider_recommendation(
        self,
        is_handwritten: bool = True,
        has_checkboxes: bool = True,
        is_high_volume: bool = False
    ) -> Dict[str, Any]:
        """Get provider recommendation with reasoning"""
        characteristics = {
            'is_handwritten': is_handwritten,
            'has_checkboxes': has_checkboxes,
            'is_high_volume': is_high_volume
        }
        
        best_provider = self.select_best_provider(characteristics)
        caps = self.provider_capabilities.get(best_provider, {})
        
        return {
            "recommended_provider": best_provider,
            "reasoning": self._generate_reasoning(best_provider, characteristics, caps),
            "capabilities": caps,
            "alternatives": self._get_alternatives(best_provider, characteristics)
        }
    
    def _generate_reasoning(
        self,
        provider: str,
        characteristics: Dict[str, Any],
        capabilities: Dict[str, Any]
    ) -> str:
        """Generate human-readable reasoning for provider selection"""
        reasons = []
        
        if characteristics.get('is_handwritten'):
            reasons.append(f"High handwriting accuracy ({capabilities.get('handwriting', 0)}%)")
        
        if characteristics.get('has_checkboxes'):
            reasons.append(f"Good checkbox detection ({capabilities.get('checkboxes', 0)}%)")
        
        if characteristics.get('is_high_volume'):
            if capabilities.get('cost', 0) > 70:
                reasons.append("Cost-effective for high volume")
            if capabilities.get('local', False):
                reasons.append("Local processing (no API costs)")
        
        return "; ".join(reasons) if reasons else "Default recommendation"
    
    def _get_alternatives(
        self,
        selected_provider: str,
        characteristics: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Get alternative provider options"""
        alternatives = []
        
        for provider in self.available_providers:
            if provider != selected_provider and provider in self.provider_capabilities:
                caps = self.provider_capabilities[provider]
                alternatives.append({
                    "provider": provider,
                    "capabilities": caps
                })
        
        return alternatives[:3]  # Return top 3 alternatives

