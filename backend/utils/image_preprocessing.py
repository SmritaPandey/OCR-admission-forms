"""
Image preprocessing utilities for better OCR accuracy
"""
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from typing import Optional

def binarize_image(image: Image.Image, threshold: int = 128) -> Image.Image:
    """
    Convert image to black and white (binarization) for better OCR
    """
    # Convert to grayscale
    gray = image.convert('L')
    # Apply threshold
    binary = gray.point(lambda x: 0 if x < threshold else 255, '1')
    # Convert back to RGB
    return binary.convert('RGB')

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

def preprocess_image(image: Image.Image, enhance_contrast: bool = True, denoise: bool = True, 
                     sharpen: bool = False, scale_factor: float = 1.0, binarize: bool = False) -> Image.Image:
    """
    Preprocess image to improve OCR accuracy
    
    Args:
        image: PIL Image to preprocess
        enhance_contrast: Enhance contrast for better text recognition
        denoise: Apply denoising filter
        sharpen: Apply sharpening filter
        scale_factor: Scale image up (1.0 = no scaling, 2.0 = double size)
    
    Returns:
        Preprocessed PIL Image
    """
    processed = image.copy()
    
    # Convert to RGB if needed
    if processed.mode != 'RGB':
        processed = processed.convert('RGB')
    
    # Scale up image for better OCR (especially for small text)
    if scale_factor > 1.0:
        new_size = (int(processed.width * scale_factor), int(processed.height * scale_factor))
        processed = processed.resize(new_size, Image.Resampling.LANCZOS)
    
    # Enhance contrast
    if enhance_contrast:
        enhancer = ImageEnhance.Contrast(processed)
        processed = enhancer.enhance(1.5)  # Increase contrast by 50%
    
    # Enhance sharpness
    if sharpen:
        enhancer = ImageEnhance.Sharpness(processed)
        processed = enhancer.enhance(1.3)
    
    # Denoise - convert to grayscale first, then back to RGB
    if denoise:
        # Convert to grayscale for better denoising
        gray = processed.convert('L')
        # Apply median filter to reduce noise
        gray = gray.filter(ImageFilter.MedianFilter(size=3))
        # Convert back to RGB
        processed = gray.convert('RGB')
    
    return processed

def enhance_for_ocr(image: Image.Image) -> Image.Image:
    """
    Apply comprehensive enhancements optimized for OCR
    
    Args:
        image: PIL Image
    
    Returns:
        Enhanced PIL Image
    """
    # Convert to RGB
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    # Scale up significantly for better recognition
    # Higher resolution = better OCR accuracy
    scale = 3.0 if image.width < 1500 else 2.5
    if scale > 1.0:
        new_size = (int(image.width * scale), int(image.height * scale))
        image = image.resize(new_size, Image.Resampling.LANCZOS)
    
    # Convert to grayscale for better processing
    gray = image.convert('L')
    
    # Enhance contrast aggressively
    enhancer = ImageEnhance.Contrast(gray)
    gray = enhancer.enhance(2.0)  # Double contrast
    
    # Enhance sharpness
    enhancer = ImageEnhance.Sharpness(gray)
    gray = enhancer.enhance(2.0)  # Double sharpness
    
    # Apply thresholding (binarization) for better OCR
    # Use histogram to calculate threshold (more efficient)
    hist = gray.histogram()
    # Calculate median threshold
    total_pixels = sum(hist)
    cumulative = 0
    threshold = 128
    for i, count in enumerate(hist):
        cumulative += count
        if cumulative >= total_pixels / 2:
            threshold = i
            break
    
    # Apply binary threshold
    binary = gray.point(lambda x: 0 if x < threshold else 255, '1')
    
    # Convert back to RGB
    image = binary.convert('RGB')
    
    # Final sharpening
    enhancer = ImageEnhance.Sharpness(image)
    image = enhancer.enhance(1.5)
    
    return image

