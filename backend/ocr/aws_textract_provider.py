"""
AWS Textract provider - Good for forms and handwriting
Excellent for detecting form fields, checkboxes, and selection elements
"""
from typing import Dict, Any, Optional
from PIL import Image
import io
from backend.ocr.base_provider import OCRProvider
from backend.config import settings

class AWSTextractProvider(OCRProvider):
    """AWS Textract - Good for forms and handwriting"""
    
    def __init__(self):
        self.name = "aws-textract"
        self._client = None
    
    def _get_client(self):
        """Get or create Textract client"""
        if self._client is None:
            try:
                import boto3
                
                if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
                    raise ValueError("AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY required")
                
                self._client = boto3.client(
                    'textract',
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region_name=settings.AWS_REGION
                )
            except ImportError:
                raise ImportError("boto3 not installed. Install with: pip install boto3")
        
        return self._client
    
    async def extract_text(self, image: Image.Image, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract text using AWS Textract
        Good for forms with checkboxes and selection marks
        """
        try:
            client = self._get_client()
            
            # Convert PIL Image to bytes
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            image_bytes = img_byte_arr.getvalue()
            
            # Analyze document (use analyze_document for forms)
            response = client.analyze_document(
                Document={'Bytes': image_bytes},
                FeatureTypes=['FORMS', 'TABLES']  # Include forms and tables
            )
            
            # Extract text blocks
            raw_text = ""
            form_fields = {}
            checkboxes = []
            selection_elements = []
            
            blocks = response.get('Blocks', [])
            
            for block in blocks:
                block_type = block.get('BlockType', '')
                
                if block_type == 'LINE':
                    text = block.get('Text', '')
                    if text:
                        raw_text += text + "\n"
                
                elif block_type == 'KEY_VALUE_SET':
                    # Form field
                    if block.get('EntityTypes', []) == ['KEY']:
                        key_id = block.get('Id')
                        # Find corresponding value
                        for other_block in blocks:
                            if other_block.get('BlockType') == 'KEY_VALUE_SET' and \
                               other_block.get('EntityTypes') == ['VALUE'] and \
                               key_id in other_block.get('Relationships', [{}])[0].get('Ids', []):
                                key_text = ""
                                value_text = ""
                                # Get key text
                                for key_block in blocks:
                                    if key_block.get('Id') == key_id:
                                        for rel in key_block.get('Relationships', []):
                                            if rel.get('Type') == 'CHILD':
                                                for child_id in rel.get('Ids', []):
                                                    child_block = next((b for b in blocks if b.get('Id') == child_id), None)
                                                    if child_block and child_block.get('BlockType') == 'WORD':
                                                        key_text += child_block.get('Text', '') + " "
                                # Get value text
                                for rel in other_block.get('Relationships', []):
                                    if rel.get('Type') == 'CHILD':
                                        for child_id in rel.get('Ids', []):
                                            child_block = next((b for b in blocks if b.get('Id') == child_id), None)
                                            if child_block and child_block.get('BlockType') == 'WORD':
                                                value_text += child_block.get('Text', '') + " "
                                if key_text and value_text:
                                    form_fields[key_text.strip()] = value_text.strip()
                
                elif block_type == 'SELECTION_ELEMENT':
                    # Checkbox or radio button
                    selection_status = block.get('SelectionStatus', '')
                    confidence = block.get('Confidence', 0.0)
                    geometry = block.get('Geometry', {})
                    
                    checkboxes.append({
                        "selected": selection_status == 'SELECTED',
                        "confidence": confidence,
                        "bounding_box": geometry.get('BoundingBox', {}) if geometry else {}
                    })
            
            structured_data = {
                "text": raw_text,
                "form_fields": form_fields,
                "checkboxes": checkboxes,
                "selection_elements": selection_elements,
                "pages": len([b for b in blocks if b.get('BlockType') == 'PAGE']) or 1
            }
            
            # Calculate average confidence
            confidences = [block.get('Confidence', 0.0) for block in blocks if block.get('Confidence')]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 85.0
            
            return {
                "raw_text": raw_text.strip(),
                "confidence": round(avg_confidence, 2),
                "structured_data": structured_data,
                "provider": self.get_provider_name()
            }
            
        except Exception as e:
            raise Exception(f"AWS Textract error: {str(e)}")
    
    def is_available(self) -> bool:
        """Check if AWS Textract is configured"""
        try:
            if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
                return False
            # Try to import
            import boto3
            return True
        except ImportError:
            return False
    
    def get_provider_name(self) -> str:
        return "aws-textract"

