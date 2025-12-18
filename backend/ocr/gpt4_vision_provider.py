"""
GPT-4 Vision OCR Provider
Uses OpenAI's GPT-4 Vision model for form understanding and OCR
"""
from typing import Dict, Any, Optional
from PIL import Image
import io
import base64
from backend.ocr.base_provider import OCRProvider
from backend.config import settings

class GPT4VisionProvider(OCRProvider):
    """OCR provider using OpenAI GPT-4 Vision"""
    
    def __init__(self):
        self._client = None
        self.api_key = settings.OPENAI_API_KEY if hasattr(settings, 'OPENAI_API_KEY') else ""
        self.model = getattr(settings, 'OPENAI_VISION_MODEL', 'gpt-4-vision-preview')
    
    def _get_client(self):
        """Lazy load OpenAI client"""
        if self._client is None:
            try:
                import openai
                if not self.api_key:
                    raise ValueError("OPENAI_API_KEY not configured")
                self._client = openai.OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "OpenAI package not installed. Install with: pip install openai"
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
        Extract text and structured data using GPT-4 Vision
        
        Uses a structured prompt to extract form fields as JSON
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
            
            Return a JSON object with all extracted fields. For checkboxes, include the label and whether it's checked.
            If a field is not found, set it to null."""
            
            # Call GPT-4 Vision API
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=2000,
                temperature=0.1
            )
            
            # Extract response text
            response_text = response.choices[0].message.content
            
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
            
            # Calculate confidence (GPT-4 Vision doesn't provide confidence scores)
            # Use a default high confidence value
            confidence = 85.0
            
            return {
                "raw_text": raw_text,
                "confidence": confidence,
                "structured_data": structured_data,
                "provider": "gpt4-vision",
                "metadata": {
                    "model": self.model,
                    "response_length": len(response_text)
                }
            }
            
        except Exception as e:
            raise Exception(f"GPT-4 Vision OCR failed: {str(e)}")
    
    def _structured_to_text(self, structured_data: Dict[str, Any]) -> str:
        """Convert structured data to readable text"""
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
        """Check if GPT-4 Vision is available"""
        try:
            if not self.api_key:
                return False
            self._get_client()
            return True
        except Exception:
            return False
    
    def get_provider_name(self) -> str:
        """Return provider name"""
        return "gpt4-vision"

