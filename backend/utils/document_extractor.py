"""
Document Extractor - Extract supporting documents from PDF pages after the form

This module provides functionality to:
1. Identify pages that are supporting documents (pages 5+)
2. Extract and save these pages as individual PDF/image files
3. Name them appropriately using student name and DU portal number
4. Create StudentDocument records in the database
"""

import logging
import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from PIL import Image
import io

logger = logging.getLogger(__name__)


# Number of pages that constitute the main form
FORM_PAGE_COUNT = 4


def extract_supporting_documents(
    pdf_images: List[Any],
    form_id: int,
    student_name: str,
    du_portal_number: str,
    db: Session,
    upload_dir: Path,
    page_offset: int = FORM_PAGE_COUNT,
) -> List[Dict[str, Any]]:
    """
    Extract supporting documents from PDF page images and save as a single multi-page PDF.
    
    Args:
        pdf_images: List of PIL images from the PDF (the document pages only)
        form_id: ID of the admission form
        student_name: Student name for file naming
        du_portal_number: DU portal form number for file naming
        db: Database session
        upload_dir: Directory for uploads
        page_offset: Starting page number offset (for description)
        
    Returns:
        List of created document records (will contain single entry with all pages)
    """
    from backend.database import StudentDocument, DocumentCategory, AdmissionForm
    import os
    
    if not pdf_images:
        logger.info(f"Form {form_id}: No supporting document pages provided")
        return []
    
    # Get the form to link documents
    form = db.query(AdmissionForm).filter(AdmissionForm.id == form_id).first()
    if not form:
        logger.error(f"Form {form_id} not found")
        return []
    
    # Delete any existing auto-extracted documents for this form to avoid duplicates
    existing_docs = db.query(StudentDocument).filter(
        StudentDocument.form_id == form_id,
        StudentDocument.description.like("%Supporting document%")
    ).all()
    
    for doc in existing_docs:
        try:
            # Delete file if exists
            full_path = upload_dir / doc.file_path
            if full_path.exists():
                os.remove(full_path)
            db.delete(doc)
            logger.info(f"Deleted old auto-extracted document: {doc.filename}")
        except Exception as e:
            logger.warning(f"Failed to delete old document {doc.id}: {e}")
    
    if existing_docs:
        db.commit()
    
    # Clean student name for filename
    safe_name = _sanitize_filename(student_name or "unknown")
    safe_portal = _sanitize_filename(du_portal_number or "")
    
    # Generate filename with student name and portal number
    if safe_name and safe_portal:
        filename = f"{safe_name}_{safe_portal}_supporting_documents.pdf"
    elif safe_name:
        filename = f"{safe_name}_supporting_documents.pdf"
    elif safe_portal:
        filename = f"{safe_portal}_supporting_documents.pdf"
    else:
        filename = f"form{form_id}_supporting_documents.pdf"
    
    try:
        # Save the pages as a single multi-page PDF
        doc_dir = upload_dir / "documents" / str(form_id)
        doc_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = doc_dir / filename
        relative_path = f"documents/{form_id}/{filename}"
        
        # Save all pages as single PDF
        _save_images_as_pdf(pdf_images, file_path)
        
        # Get file size
        file_size = file_path.stat().st_size if file_path.exists() else 0
        
        # Determine number of pages for description
        num_pages = len(pdf_images)
        start_page = page_offset + 1
        end_page = page_offset + num_pages
        
        # Create single document record for all pages
        document = StudentDocument(
            filename=filename,
            file_path=relative_path,
            upload_date=datetime.utcnow(),
            document_category=DocumentCategory.OTHER,
            description=f"Supporting documents ({num_pages} pages, pages {start_page}-{end_page} from original PDF)",
            file_size=file_size,
            form_id=form_id,
            student_profile_id=form.student_profile_id,
        )
        
        db.add(document)
        db.commit()
        
        logger.info(f"Created document: {filename} ({num_pages} pages)")
        
        return [{
            'filename': filename,
            'file_path': relative_path,
            'category': DocumentCategory.OTHER.value,
            'page_count': num_pages,
            'page_range': f"{start_page}-{end_page}",
        }]
        
    except Exception as e:
        logger.error(f"Error extracting supporting documents: {str(e)}")
        return []


def _sanitize_filename(name: str) -> str:
    """Convert a name to a safe filename component"""
    if not name:
        return ""
    # Remove or replace unsafe characters
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = re.sub(r'\s+', '_', name)
    name = re.sub(r'[^\w\-_]', '', name)
    return name[:50]  # Limit length


def _classify_document_page(page_image: Any, page_num: int) -> "DocumentCategory":
    """
    Attempt to classify the document type based on content.
    Default to OTHER if cannot determine.
    """
    from backend.database import DocumentCategory
    
    # For now, default to OTHER
    # In the future, could use OCR + keyword matching to classify:
    # - "CBSE", "ICSE", "Board" -> Academic Certificate
    # - "Aadhar", "PAN", "Voter ID" -> ID Proof
    # - "Birth Certificate", "DOB" -> Birth Certificate
    # - "Income", "BPL" -> Income Certificate
    # - "Caste", "OBC", "SC/ST" -> Caste Certificate
    
    return DocumentCategory.OTHER


def _save_image_as_pdf(image: Any, output_path: Path):
    """Save a PIL Image as PDF"""
    if isinstance(image, Image.Image):
        # Convert to RGB if necessary (PDF doesn't support RGBA)
        if image.mode == 'RGBA':
            rgb_image = Image.new('RGB', image.size, (255, 255, 255))
            rgb_image.paste(image, mask=image.split()[3])
            image = rgb_image
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        
        image.save(str(output_path), 'PDF', resolution=100.0)
    else:
        # If it's bytes, write directly
        with open(output_path, 'wb') as f:
            f.write(image)


def _save_images_as_pdf(images: List[Any], output_path: Path):
    """Save multiple PIL Images as a single multi-page PDF"""
    if not images:
        return
    
    # Convert all images to RGB mode
    rgb_images = []
    for img in images:
        if isinstance(img, Image.Image):
            if img.mode == 'RGBA':
                rgb_image = Image.new('RGB', img.size, (255, 255, 255))
                rgb_image.paste(img, mask=img.split()[3])
                rgb_images.append(rgb_image)
            elif img.mode != 'RGB':
                rgb_images.append(img.convert('RGB'))
            else:
                rgb_images.append(img)
    
    if not rgb_images:
        return
    
    # Save first image with remaining images appended
    if len(rgb_images) == 1:
        rgb_images[0].save(str(output_path), 'PDF', resolution=100.0)
    else:
        rgb_images[0].save(
            str(output_path), 
            'PDF', 
            resolution=100.0,
            save_all=True,
            append_images=rgb_images[1:]
        )


async def extract_documents_from_form(
    form_id: int,
    db: Session,
) -> List[Dict[str, Any]]:
    """
    Extract supporting documents from an already-uploaded form.
    This is called after OCR extraction to find and save attached documents.
    
    Args:
        form_id: ID of the form
        db: Database session
        
    Returns:
        List of created document records
    """
    from backend.database import AdmissionForm
    from backend.config import settings
    from backend.utils.file_handler import load_all_pdf_pages, get_file_extension
    
    form = db.query(AdmissionForm).filter(AdmissionForm.id == form_id).first()
    if not form:
        logger.error(f"Form {form_id} not found")
        return []
    
    upload_dir = Path(settings.UPLOAD_DIR).resolve()
    full_file_path = upload_dir / form.file_path
    
    if not full_file_path.exists():
        logger.error(f"Form file not found: {form.file_path}")
        return []
    
    file_ext = get_file_extension(str(full_file_path))
    if file_ext != 'pdf':
        logger.info(f"Form {form_id}: Not a PDF, no documents to extract")
        return []
    
    # Load all pages
    try:
        pages = load_all_pdf_pages(str(full_file_path))
    except Exception as e:
        logger.error(f"Error loading PDF pages: {str(e)}")
        return []
    
    if len(pages) <= FORM_PAGE_COUNT:
        logger.info(f"Form {form_id}: Only {len(pages)} pages, no supporting documents")
        return []
    
    # Get student info for naming
    student_name = form.student_name or ""
    du_portal_number = form.du_portal_form_number or ""
    
    return extract_supporting_documents(
        pdf_images=pages,
        form_id=form_id,
        student_name=student_name,
        du_portal_number=du_portal_number,
        db=db,
        upload_dir=upload_dir,
    )


def get_attached_documents(form_id: int, db: Session) -> List[Dict[str, Any]]:
    """
    Get list of attached documents for a form.
    
    Args:
        form_id: ID of the form
        db: Database session
        
    Returns:
        List of document info dictionaries
    """
    from backend.database import StudentDocument
    
    documents = db.query(StudentDocument).filter(
        StudentDocument.form_id == form_id
    ).order_by(StudentDocument.upload_date.desc()).all()
    
    return [
        {
            'id': doc.id,
            'filename': doc.filename,
            'file_path': doc.file_path,
            'category': doc.document_category.value if doc.document_category else 'Other',
            'description': doc.description,
            'file_size': doc.file_size,
            'upload_date': doc.upload_date.isoformat() if doc.upload_date else None,
        }
        for doc in documents
    ]
