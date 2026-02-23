"""
Ensemble OCR Provider

Combines fine-tuned TrOCR + enhanced Tesseract with confidence-weighted
fusion for optimal admission form OCR accuracy.

Implements the OCRProvider interface for seamless integration with the
existing backend OCR pipeline.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from PIL import Image

from backend.ocr.base_provider import OCRProvider

# Conditional imports
try:
    from backend.ocr.craft_trocr_provider import CraftTrocrProvider
    TROCR_AVAILABLE = True
except ImportError:
    TROCR_AVAILABLE = False

try:
    from backend.ocr.tesseract_provider import TesseractProvider
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False


class EnsembleOCRProvider(OCRProvider):
    """
    Ensemble OCR provider that combines multiple OCR engines with
    confidence-weighted fusion for best results.
    
    Providers:
        1. Fine-tuned TrOCR (primary) - best for handwritten text
        2. Tesseract with custom wordlists (secondary) - best for printed text
    
    Fusion strategy:
        - Run both providers on each image
        - Weight results by confidence score
        - Use field validation rules for post-processing
    """

    def __init__(
        self,
        config_path: Optional[str] = None,
        trocr_model_path: Optional[str] = None,
        tesseract_wordlist: Optional[str] = None,
    ):
        """
        Initialize ensemble provider.
        
        Args:
            config_path: Path to ensemble_config.json (auto-detected if None)
            trocr_model_path: Path to fine-tuned TrOCR model
            tesseract_wordlist: Path to custom Tesseract wordlist
        """
        self.config = self._load_config(config_path)
        self.trocr_provider = None
        self.tesseract_provider = None
        self.trocr_weight = 0.6
        self.tesseract_weight = 0.4

        # Override from config
        if self.config:
            for p in self.config.get("providers", []):
                if p["type"] == "trocr":
                    self.trocr_weight = p.get("weight", 0.6)
                    if not trocr_model_path and p.get("model_path"):
                        trocr_model_path = p["model_path"]
                elif p["type"] == "tesseract":
                    self.tesseract_weight = p.get("weight", 0.4)
                    if not tesseract_wordlist and p.get("wordlist_path"):
                        tesseract_wordlist = p["wordlist_path"]

        # Initialize sub-providers
        self._init_trocr(trocr_model_path)
        self._init_tesseract(tesseract_wordlist)

    def _load_config(self, config_path: Optional[str]) -> Optional[Dict]:
        """Load ensemble configuration."""
        if config_path and Path(config_path).exists():
            with open(config_path, "r") as f:
                return json.load(f)

        # Auto-detect
        default = Path(__file__).parent.parent.parent / "training_output" / "models" / "ensemble" / "ensemble_config.json"
        if default.exists():
            with open(default, "r") as f:
                return json.load(f)

        return None

    def _init_trocr(self, model_path: Optional[str] = None):
        """Initialize TrOCR provider."""
        if not TROCR_AVAILABLE:
            return

        try:
            if model_path and Path(model_path).exists():
                self.trocr_provider = CraftTrocrProvider(custom_model_path=model_path)
            else:
                self.trocr_provider = CraftTrocrProvider()

            if not self.trocr_provider.is_available():
                self.trocr_provider = None
        except Exception:
            self.trocr_provider = None

    def _init_tesseract(self, wordlist_path: Optional[str] = None):
        """Initialize Tesseract provider with optional custom wordlist."""
        if not TESSERACT_AVAILABLE:
            return

        try:
            self.tesseract_provider = TesseractProvider()
            if not self.tesseract_provider.is_available():
                self.tesseract_provider = None
            else:
                # Store wordlist path for custom config
                self.tesseract_wordlist = wordlist_path
        except Exception:
            self.tesseract_provider = None

    async def extract_text(
        self, image: Image.Image, language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract text using ensemble of OCR providers.
        
        Runs all available providers, then fuses results using
        confidence-weighted combination.
        """
        results = []

        # Run TrOCR
        if self.trocr_provider:
            try:
                trocr_result = await self.trocr_provider.extract_text(image, language)
                trocr_result["_provider"] = "trocr"
                trocr_result["_weight"] = self.trocr_weight
                results.append(trocr_result)
            except Exception as e:
                pass  # Graceful fallback

        # Run Tesseract
        if self.tesseract_provider:
            try:
                tess_result = await self.tesseract_provider.extract_text(image, language)
                tess_result["_provider"] = "tesseract"
                tess_result["_weight"] = self.tesseract_weight
                results.append(tess_result)
            except Exception as e:
                pass  # Graceful fallback

        if not results:
            return {
                "raw_text": "",
                "confidence": 0,
                "provider": "ensemble",
                "error": "No OCR providers available",
            }

        # --- Fusion: weighted confidence ---
        best_result = self._fuse_results(results)

        # Add ensemble metadata
        best_result["provider"] = "ensemble"
        best_result["ensemble_providers"] = [r.get("_provider") for r in results]
        best_result["ensemble_confidences"] = {
            r.get("_provider"): r.get("confidence", 0) for r in results
        }

        return best_result

    def _fuse_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Fuse multiple OCR results using weighted confidence.
        
        Strategy:
        - Each provider has a base weight from config
        - Multiply by runtime confidence score
        - Take the result with highest weighted score
        """
        if len(results) == 1:
            result = results[0].copy()
            result.pop("_provider", None)
            result.pop("_weight", None)
            return result

        best_score = -1
        best_result = results[0]

        for r in results:
            confidence = r.get("confidence", 0)
            weight = r.get("_weight", 0.5)
            text_length = len(r.get("raw_text", ""))

            # Weighted score: confidence × weight, bonus for longer text
            score = confidence * weight + min(text_length / 1000, 0.1)

            if score > best_score:
                best_score = score
                best_result = r

        result = best_result.copy()
        result.pop("_provider", None)
        result.pop("_weight", None)
        return result

    def is_available(self) -> bool:
        """Check if at least one sub-provider is available."""
        return (
            (self.trocr_provider is not None and self.trocr_provider.is_available()) or
            (self.tesseract_provider is not None and self.tesseract_provider.is_available())
        )

    def get_provider_name(self) -> str:
        """Return provider name."""
        providers = []
        if self.trocr_provider:
            providers.append("trocr")
        if self.tesseract_provider:
            providers.append("tesseract")
        return f"ensemble({'+'.join(providers)})"
