"""
Claude Vision OCR Provider
Uses Anthropic's Claude Vision model for form understanding and OCR
"""
from typing import Dict, Any, Optional
from PIL import Image
import io
import base64
from backend.ocr.base_provider import OCRProvider
from backend.config import settings

class ClaudeVisionProvider(OCRProvider):
    """OCR provider using Anthropic Claude Vision"""
    
    def __init__(self):
        self._client = None
        self.api_key = settings.ANTHROPIC_API_KEY if hasattr(settings, 'ANTHROPIC_API_KEY') else ""
        self.model = getattr(settings, 'CLAUDE_VISION_MODEL', 'claude-3-5-sonnet-20241022')
    
    def _get_client(self):
        """Lazy load Anthropic client"""
        if self._client is None:
            try:
                import anthropic
                if not self.api_key:
                    raise ValueError("ANTHROPIC_API_KEY not configured")
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "Anthropic package not installed. Install with: pip install anthropic"
                )
        return self._client
    
    def _image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL Image to base64 string"""
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return img_str
    
    async def extract_text(self, image: Image.Image, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract text and structured data using Claude Vision
        
        Uses structured output for form field extraction
        """
        try:
            client = self._get_client()
            
            # Convert image to base64
            base64_image = self._image_to_base64(image)
            
            # Create prompt for form extraction
            prompt = """Analyze this admission form image and extract all information as structured JSON.
            Extract fields including:
            - Student name, date of birth, gender, category, nationality, religion
            - Aadhar number, blood group
            - Permanent and correspondence addresses with pincode, city, state
            - Phone numbers (student, alternate, emergency contact)
            - Email
            - Guardian/Parent details (name, occupation, phone)
            - Educational qualifications (10th, 12th, graduation details)
            - Course applied, application number, admission date
            
            Also detect any checked checkboxes or selected options.
            
            Return ONLY a valid JSON object with all extracted fields. For checkboxes, include the label and whether it's checked.
            If a field is not found, set it to null.
            
            Format your response as pure JSON without markdown formatting."""
            
            # Call Claude Vision API
            message = client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.1,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": base64_image
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )
            
            # Extract response text
            response_text = message.content[0].text
            
            # Try to parse JSON from response
            import json
            import re
            
            # Try to extract JSON from markdown code blocks or plain JSON
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    json_str = response_text
            
            try:
                structured_data = json.loads(json_str)
            except json.JSONDecodeError:
                # Fallback: treat as raw text
                structured_data = {}
            
            # Extract raw text from structured data for compatibility
            raw_text = self._structured_to_text(structured_data)
            
            # Calculate confidence (Claude doesn't provide confidence scores)
            # Use a default high confidence value
            confidence = 88.0
            
            return {
                "raw_text": raw_text,
                "confidence": confidence,
                "structured_data": structured_data,
                "provider": "claude-vision",
                "metadata": {
                    "model": self.model,
                    "response_length": len(response_text)
                }
            }
            
        except Exception as e:
            raise Exception(f"Claude Vision OCR failed: {str(e)}")
    
    def _structured_to_text(self, structured_data: Dict[str, Any]) -> str:
        """Convert structured data to readable text"""
        import json
        text_lines = []
        
        for key, value in structured_data.items():
            if value is not None and value != "":
                if isinstance(value, dict):
                    text_lines.append(f"{key}: {json.dumps(value)}")
                elif isinstance(value, list):
                    text_lines.append(f"{key}: {', '.join(str(v) for v in value)}")
                else:
                    text_lines.append(f"{key}: {value}")
        
        return "\n".join(text_lines)
    
    def is_available(self) -> bool:
        """Check if Claude Vision is available"""
        try:
            if not self.api_key:
                return False
            self._get_client()
            return True
        except Exception:
            return False
    
    def get_provider_name(self) -> str:
        """Return provider name"""
        return "claude-vision"

