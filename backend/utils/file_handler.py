import os
import uuid
import io
from pathlib import Path
from fastapi import UploadFile
from PIL import Image
from backend.config import settings
import fitz  # PyMuPDF for PDF support

def ensure_upload_dir():
    """Ensure upload directory exists"""
    upload_path = Path(settings.UPLOAD_DIR)
    upload_path.mkdir(parents=True, exist_ok=True)
    return upload_path

def ensure_documents_dir():
    """Ensure documents subdirectory exists"""
    upload_path = ensure_upload_dir()
    documents_path = upload_path / "documents"
    documents_path.mkdir(parents=True, exist_ok=True)
    return documents_path

def validate_file(file: UploadFile) -> bool:
    """Validate uploaded file"""
    # Check file extension
    file_ext = file.filename.split('.')[-1].lower() if file.filename else ""
    if file_ext not in settings.ALLOWED_EXTENSIONS:
        return False
    
    return True

def get_file_extension(filename: str) -> str:
    """Get file extension from filename"""
    return filename.split('.')[-1].lower()

async def save_uploaded_file(file: UploadFile) -> tuple[str, str]:
    """
    Save uploaded file to disk
    
    Returns:
        Tuple of (file_path, filename)
    """
    if not validate_file(file):
        raise ValueError(f"Invalid file type. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}")
    
    upload_dir = ensure_upload_dir()
    
    # Generate unique filename
    file_ext = get_file_extension(file.filename)
    unique_filename = f"{uuid.uuid4()}.{file_ext}"
    file_path = upload_dir / unique_filename
    
    # Save file
    with open(file_path, "wb") as buffer:
        content = await file.read()
        if len(content) > settings.MAX_FILE_SIZE:
            raise ValueError(f"File too large. Max size: {settings.MAX_FILE_SIZE / (1024*1024)}MB")
        buffer.write(content)
    
    return str(file_path), unique_filename

async def save_document_file(file: UploadFile) -> tuple[str, str, int]:
    """
    Save uploaded document file to disk in documents subdirectory
    
    Returns:
        Tuple of (file_path, filename, file_size_in_bytes)
    """
    if not validate_file(file):
        raise ValueError(f"Invalid file type. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}")
    
    documents_dir = ensure_documents_dir()
    
    # Generate unique filename
    file_ext = get_file_extension(file.filename)
    unique_filename = f"{uuid.uuid4()}.{file_ext}"
    file_path = documents_dir / unique_filename
    
    # Save file
    with open(file_path, "wb") as buffer:
        content = await file.read()
        file_size = len(content)
        if file_size > settings.MAX_FILE_SIZE:
            raise ValueError(f"File too large. Max size: {settings.MAX_FILE_SIZE / (1024*1024)}MB")
        buffer.write(content)
    
    # Return relative path from uploads directory
    upload_dir = ensure_upload_dir()
    relative_path = os.path.relpath(file_path, upload_dir)
    
    return str(file_path), relative_path, file_size

def load_image(file_path: str) -> Image.Image:
    """
    Load image from file path using PIL.
    Supports image files (JPG, PNG, TIFF, BMP) and PDF files.
    For PDFs, converts the first page to an image.
    """
    try:
        file_ext = get_file_extension(file_path)
        
        # Handle PDF files
        if file_ext == 'pdf':
            try:
                # Open PDF and convert first page to image
                pdf_document = fitz.open(file_path)
                if len(pdf_document) == 0:
                    raise ValueError("PDF file is empty or corrupted")
                
                # Get first page
                page = pdf_document[0]
                
                # Convert to image with very high DPI for better OCR quality
                # Scale factor of 3.0 = 216 DPI (excellent for OCR)
                # Higher DPI = better text recognition
                mat = fitz.Matrix(3.0, 3.0)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                
                # Convert to PIL Image
                img_data = pix.tobytes("png")
                image = Image.open(io.BytesIO(img_data))
                
                # Convert to RGB if necessary
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                
                pdf_document.close()
                return image
                
            except Exception as pdf_error:
                raise ValueError(f"Failed to process PDF: {str(pdf_error)}")
        
        # Handle image files
        else:
            image = Image.open(file_path)
            # Convert to RGB if necessary (for JPEG compatibility)
            if image.mode in ('RGBA', 'LA', 'P'):
                rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                rgb_image.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
                return rgb_image
            elif image.mode != 'RGB':
                image = image.convert('RGB')
            return image
            
    except Exception as e:
        raise ValueError(f"Failed to load image: {str(e)}")

def load_all_pdf_pages(file_path: str) -> list[Image.Image]:
    """
    Load all pages from a PDF file as images.
    
    Args:
        file_path: Path to PDF file
    
    Returns:
        List of PIL Images, one for each page
    """
    try:
        file_ext = get_file_extension(file_path)
        
        if file_ext != 'pdf':
            # For non-PDF files, return single image
            return [load_image(file_path)]
        
        pdf_document = fitz.open(file_path)
        if len(pdf_document) == 0:
            raise ValueError("PDF file is empty or corrupted")
        
        images = []
        
        # Process each page
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            
            # Convert to image with very high DPI for better OCR quality
            mat = fitz.Matrix(3.0, 3.0)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            
            # Convert to PIL Image
            img_data = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_data))
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            images.append(image)
        
        pdf_document.close()
        return images
        
    except Exception as e:
        raise ValueError(f"Failed to process PDF pages: {str(e)}")

