"""
Convert PDFs in data/samples/pdfs/ to images for training
"""
import os
from pathlib import Path
from pdf2image import convert_from_path
from PIL import Image
import sys

def convert_pdfs_to_images(pdf_dir: str, output_dir: str):
    """
    Convert all PDFs in pdf_dir to images and save to output_dir
    
    Args:
        pdf_dir: Directory containing PDF files
        output_dir: Directory to save converted images
    """
    pdf_path = Path(pdf_dir)
    output_path = Path(output_dir)
    
    # Create output directory if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Get all PDF files
    pdf_files = list(pdf_path.glob("*.pdf"))
    
    if not pdf_files:
        print(f"No PDF files found in {pdf_dir}")
        return
    
    print(f"Found {len(pdf_files)} PDF files")
    print(f"Converting to images in {output_dir}...")
    print()
    
    total_images = 0
    
    for pdf_file in pdf_files:
        try:
            print(f"Converting: {pdf_file.name}")
            
            # Convert PDF to images
            images = convert_from_path(str(pdf_file), dpi=300)
            
            # Save each page as an image
            for i, image in enumerate(images):
                # Create filename: original_name_page_01.png
                base_name = pdf_file.stem.replace(" ", "_")
                image_filename = f"{base_name}_page_{i+1:02d}.png"
                image_path = output_path / image_filename
                
                # Save as PNG
                image.save(image_path, "PNG", quality=95)
                total_images += 1
                
                print(f"  ✓ Page {i+1} -> {image_filename}")
            
            print(f"  ✅ Converted {len(images)} pages from {pdf_file.name}")
            print()
            
        except Exception as e:
            print(f"  ❌ Error converting {pdf_file.name}: {e}")
            print()
    
    print(f"✅ Conversion complete!")
    print(f"   Total images created: {total_images}")
    print(f"   Output directory: {output_dir}")

if __name__ == "__main__":
    # Get project root
    project_root = Path(__file__).parent.parent.parent
    pdf_dir = project_root / "data" / "samples" / "pdfs"
    output_dir = project_root / "data" / "samples" / "images"
    
    if not pdf_dir.exists():
        print(f"Error: PDF directory not found: {pdf_dir}")
        sys.exit(1)
    
    convert_pdfs_to_images(str(pdf_dir), str(output_dir))
