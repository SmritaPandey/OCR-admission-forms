"""
Best TrOCR Models from HuggingFace
List of best performing TrOCR models for different use cases
"""
from typing import Dict, List

# Best TrOCR models on HuggingFace
BEST_TROCR_MODELS = {
    # Handwritten text (best for admission forms)
    "handwritten": {
        "best": "microsoft/trocr-base-handwritten",  # Best general handwritten
        "large": "microsoft/trocr-large-handwritten",  # Larger, more accurate
        "small": "microsoft/trocr-small-handwritten",  # Faster, smaller
    },
    
    # Printed text
    "printed": {
        "best": "microsoft/trocr-base-printed",
        "large": "microsoft/trocr-large-printed",
        "small": "microsoft/trocr-small-printed",
    },
    
    # Stage 1 (encoder only)
    "stage1": {
        "base": "microsoft/trocr-base-stage1",
    },
    
    # Stage 2 (decoder only)
    "stage2": {
        "base": "microsoft/trocr-base-stage2",
    },
}

# Recommended model for admission forms
RECOMMENDED_MODEL = "microsoft/trocr-large-handwritten"  # Best accuracy for handwritten forms

# Fallback models (if large not available)
FALLBACK_MODELS = [
    "microsoft/trocr-base-handwritten",  # Good balance
    "microsoft/trocr-small-handwritten",  # Fast fallback
    "microsoft/trocr-base-printed",  # Last resort
]

def get_best_trocr_model(preference: str = "accuracy") -> str:
    """
    Get the best TrOCR model based on preference
    
    Args:
        preference: "accuracy" (best), "speed" (fastest), "balanced" (good balance)
    
    Returns:
        Model name string
    """
    if preference == "accuracy":
        return RECOMMENDED_MODEL
    elif preference == "speed":
        return BEST_TROCR_MODELS["handwritten"]["small"]
    elif preference == "balanced":
        return BEST_TROCR_MODELS["handwritten"]["best"]
    else:
        return RECOMMENDED_MODEL

def get_available_models() -> List[str]:
    """Get list of all available TrOCR models"""
    models = []
    for category in BEST_TROCR_MODELS.values():
        models.extend(category.values())
    return models
