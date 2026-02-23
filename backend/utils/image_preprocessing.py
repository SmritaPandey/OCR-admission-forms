"""
Image preprocessing utilities for better OCR accuracy.
"""
from PIL import Image, ImageEnhance, ImageFilter
from typing import Optional

from backend.config import settings


def _auto_threshold(gray: Image.Image) -> int:
    """Calculate an automatic threshold using the median of the histogram."""
    hist = gray.histogram()
    total_pixels = sum(hist)
    cumulative = 0
    threshold = 128
    for level, count in enumerate(hist):
        cumulative += count
        if cumulative >= total_pixels / 2:
            threshold = level
            break
    return threshold


def _resize_with_limit(image: Image.Image, scale_factor: float, max_dimension: Optional[int]) -> Image.Image:
    """
    Resize an image by the provided scale factor while respecting an optional maximum dimension.
    """
    if scale_factor <= 1.0 and not max_dimension:
        return image

    width, height = image.size
    largest_edge = max(width, height)

    target_scale = scale_factor
    if max_dimension and max_dimension > 0:
        # Clamp scale to avoid exceeding the max dimension
        if largest_edge * target_scale > max_dimension:
            target_scale = max_dimension / largest_edge
        if target_scale < 1.0 and scale_factor > 1.0:
            # Respect explicit upscaling request even if max dimension would shrink it
            target_scale = min(scale_factor, max_dimension / largest_edge)

    if target_scale <= 0 or abs(target_scale - 1.0) < 1e-3:
        return image

    new_size = (int(width * target_scale), int(height * target_scale))
    return image.resize(new_size, Image.Resampling.LANCZOS)


def binarize_image(image: Image.Image, threshold: Optional[int] = 128) -> Image.Image:
    """
    Convert image to black and white (binarization) for better OCR.
    If threshold is None or negative, an automatic threshold is calculated.
    """
    gray = image.convert("L")
    if threshold is None or threshold < 0 or threshold > 255:
        threshold = _auto_threshold(gray)
    binary = gray.point(lambda x: 0 if x < threshold else 255, "1")
    return binary.convert("RGB")

def deskew_image(image: Image.Image) -> Image.Image:
    """
    Attempt to deskew (rotate) image if it's tilted
    Simple implementation - can be enhanced
    """
    # Convert to grayscale for analysis
    gray = image.convert('L')
    # Simple deskewing - in production, use more sophisticated algorithms
    # For now, return original (can be enhanced with scikit-image if needed)
    return image

def preprocess_image(
    image: Image.Image,
    enhance_contrast: bool = True,
    denoise: bool = True,
    sharpen: bool = False,
    scale_factor: float = 1.0,
    binarize: bool = False,
    contrast_factor: float = 1.5,
    sharpness_factor: float = 1.3,
    denoise_size: int = 3,
    binarize_threshold: Optional[int] = 128,
    max_dimension: Optional[int] = None,
) -> Image.Image:
    """
    Preprocess image to improve OCR accuracy.

    Args:
        image: PIL Image to preprocess.
        enhance_contrast: Whether to enhance contrast for better text recognition.
        denoise: Whether to apply a median filter to reduce noise.
        sharpen: Whether to sharpen the image after other adjustments.
        scale_factor: Scale factor applied before other adjustments (1.0 = no scaling).
        binarize: Whether to convert the image to pure black/white.
        contrast_factor: Intensity multiplier for contrast enhancement.
        sharpness_factor: Intensity multiplier for sharpening.
        denoise_size: Kernel size for median filtering; must be an odd integer.
        binarize_threshold: Threshold for binarization (0-255). Use None or <0 for auto.
        max_dimension: Optional cap for the largest image dimension after scaling.

    Returns:
        Preprocessed PIL Image.
    """
    processed = image.copy()

    if processed.mode != "RGB":
        processed = processed.convert("RGB")

    processed = _resize_with_limit(processed, scale_factor, max_dimension)

    if enhance_contrast:
        enhancer = ImageEnhance.Contrast(processed)
        processed = enhancer.enhance(contrast_factor)

    if sharpen:
        enhancer = ImageEnhance.Sharpness(processed)
        processed = enhancer.enhance(sharpness_factor)

    if denoise:
        gray = processed.convert("L")
        # Ensure kernel size is an odd integer >= 3
        kernel = denoise_size if denoise_size % 2 == 1 else denoise_size + 1
        kernel = max(3, kernel)
        gray = gray.filter(ImageFilter.MedianFilter(size=kernel))
        processed = gray.convert("RGB")

    if binarize:
        processed = binarize_image(processed, binarize_threshold)

    return processed

def enhance_for_ocr(image: Image.Image) -> Image.Image:
    """
    Apply the configured preprocessing profile before OCR extraction.
    """
    if not settings.OCR_PREPROCESSING_ENABLED:
        return image

    return preprocess_image(
        image=image,
        enhance_contrast=settings.OCR_PREPROCESSING_ENHANCE_CONTRAST,
        denoise=settings.OCR_PREPROCESSING_DENOISE,
        sharpen=settings.OCR_PREPROCESSING_SHARPEN,
        scale_factor=settings.OCR_PREPROCESSING_SCALE_FACTOR,
        binarize=settings.OCR_PREPROCESSING_BINARIZE,
        contrast_factor=settings.OCR_PREPROCESSING_CONTRAST_FACTOR,
        sharpness_factor=settings.OCR_PREPROCESSING_SHARPNESS_FACTOR,
        denoise_size=settings.OCR_PREPROCESSING_DENOISE_SIZE,
        binarize_threshold=settings.OCR_PREPROCESSING_BINARIZE_THRESHOLD,
        max_dimension=settings.OCR_PREPROCESSING_MAX_DIMENSION or None,
    )

