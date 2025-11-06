"""
File serving routes for previews
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from backend.database import get_db, AdmissionForm
from backend.utils.file_handler import load_image
from backend.config import settings
from pathlib import Path
import io
from PIL import Image

router = APIRouter()

@router.get("/preview/{form_id}")
async def get_form_preview(form_id: int, page: int = 1, db: Session = Depends(get_db)):
    """
    Get form preview as image (converts PDF to image if needed)
    For PDFs, use ?page=1, ?page=2, etc. to view specific pages
    """
    form = db.query(AdmissionForm).filter(AdmissionForm.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    
    try:
        # Construct full path
        upload_dir = Path(settings.UPLOAD_DIR).resolve()
        full_file_path = upload_dir / form.file_path
        
        if not full_file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        # Check if it's a PDF
        from backend.utils.file_handler import get_file_extension, load_all_pdf_pages
        file_ext = get_file_extension(str(full_file_path))
        
        if file_ext == 'pdf':
            # Load all pages
            pages = load_all_pdf_pages(str(full_file_path))
            
            # Validate page number
            if page < 1 or page > len(pages):
                raise HTTPException(status_code=400, detail=f"Page {page} not found. PDF has {len(pages)} pages.")
            
            # Get requested page (1-indexed)
            image = pages[page - 1]
        else:
            # Single image file
            image = load_image(str(full_file_path))
        
        # Convert to JPEG for web display
        img_byte_arr = io.BytesIO()
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Save as JPEG with high quality
        image.save(img_byte_arr, format='JPEG', quality=95, optimize=True)
        img_byte_arr.seek(0)
        
        return StreamingResponse(
            img_byte_arr,
            media_type="image/jpeg",
            headers={
                "Cache-Control": "public, max-age=3600"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate preview: {str(e)}")

@router.get("/preview/{form_id}/pages")
async def get_form_pages_info(form_id: int, db: Session = Depends(get_db)):
    """
    Get information about PDF pages (number of pages)
    """
    form = db.query(AdmissionForm).filter(AdmissionForm.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    
    try:
        from backend.utils.file_handler import get_file_extension, load_all_pdf_pages
        from pathlib import Path
        upload_dir = Path(settings.UPLOAD_DIR).resolve()
        full_file_path = upload_dir / form.file_path
        
        file_ext = get_file_extension(str(full_file_path))
        
        if file_ext == 'pdf':
            pages = load_all_pdf_pages(str(full_file_path))
            return {"total_pages": len(pages), "is_pdf": True}
        else:
            return {"total_pages": 1, "is_pdf": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get page info: {str(e)}")

