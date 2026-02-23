"""
Ollama OCR Provider
Uses local Ollama models (Llama 3.2 Vision, LLaVA) for form understanding
"""
from typing import Dict, Any, Optional
from PIL import Image
import io
import base64
import json
import re
from backend.ocr.base_provider import OCRProvider
from backend.config import settings

class OllamaProvider(OCRProvider):
    """OCR provider using Ollama local vision models"""
    
    def __init__(self):
        self._client = None
        self.base_url = getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434')
        self.model = getattr(settings, 'OLLAMA_VISION_MODEL', 'llama3.2-vision')
    
    def _get_client(self):
        """Lazy load requests for Ollama API"""
        if self._client is None:
            try:
                import requests
                self._client = requests
            except ImportError:
                raise ImportError(
                    "Requests package not installed. Install with: pip install requests"
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
        Extract text and structured data using Ollama vision model
        
        Uses local model for private, cost-effective processing
        """
        try:
            requests = self._get_client()
            
            # Convert image to base64
            base64_image = self._image_to_base64(image)
            
            # Create prompt for form extraction with specific field structure
            prompt = """You are an expert at extracting structured data from admission forms. Analyze this form image and extract all information as a valid JSON object.

REQUIRED OUTPUT FORMAT (use these exact field names):
{
  "student_name": "Full name as written",
  "date_of_birth": "DD/MM/YYYY or DD-MM-YYYY format",
  "gender": "Male/Female/Other",
  "category": "General/OBC/SC/ST/Other",
  "nationality": "Country name",
  "religion": "Religion name",
  "aadhar_number": "12-digit number only",
  "blood_group": "A+/B+/O+/AB+/etc",
  "permanent_address": "Complete address line",
  "correspondence_address": "Complete address if different",
  "pincode": "6-digit pincode",
  "city": "City name",
  "state": "State name",
  "phone_number": "10-digit mobile number",
  "alternate_phone": "Alternate contact number",
  "email": "Email address",
  "emergency_contact_name": "Emergency contact person name",
  "emergency_contact_phone": "Emergency contact number",
  "father_name": "Father's full name",
  "father_occupation": "Father's occupation",
  "father_phone": "Father's phone number",
  "mother_name": "Mother's full name",
  "mother_occupation": "Mother's occupation",
  "mother_phone": "Mother's phone number",
  "guardian_name": "Guardian name if different",
  "guardian_relation": "Relationship to student",
  "guardian_phone": "Guardian phone number",
  "annual_income": "Annual family income",
  "tenth_board": "10th board name",
  "tenth_year": "Year of passing",
  "tenth_percentage": "Percentage or CGPA",
  "tenth_school": "School name",
  "twelfth_board": "12th board name",
  "twelfth_year": "Year of passing",
  "twelfth_percentage": "Percentage or CGPA",
  "twelfth_school": "School/College name",
  "previous_qualification": "Previous degree if any",
  "graduation_details": "Graduation details if applicable",
  "course_applied": "Course name",
  "application_number": "Application reference number",
  "admission_date": "Date of admission",
  "enrollment_number": "Enrollment number if present",
  "checkboxes": {
    "category_general": {"label": "General Category", "checked": true/false},
    "category_obc": {"label": "OBC Category", "checked": true/false},
    "category_sc": {"label": "SC Category", "checked": true/false},
    "category_st": {"label": "ST Category", "checked": true/false},
    "hostel_required": {"label": "Hostel Required", "checked": true/false}
  }
}

INSTRUCTIONS:
1. Extract ALL visible text and fields from the form
2. For checkboxes: Look for boxes/squares that are checked (marked with X, ✓, or filled)
3. Use null for fields that are not found or not visible
4. Preserve exact text as written (don't correct spelling)
5. For dates: Keep original format if readable, otherwise use DD/MM/YYYY
6. For phone numbers: Extract only digits (remove spaces, dashes)
7. Return ONLY the JSON object, no markdown, no explanations, no code blocks"""
            
            # Prepare request for Ollama API
            try:
                import aiohttp
            except ImportError:
                raise ImportError("aiohttp not installed. Install with: pip install aiohttp")
            
            async def _make_request():
                async with aiohttp.ClientSession() as session:
                    payload = {
                        "model": self.model,
                        "prompt": prompt,
                        "images": [base64_image],
                        "stream": False,
                        "options": {
                            "temperature": 0.1,
                            "num_predict": 2000
                        }
                    }
                    
                    async with session.post(
                        f"{self.base_url}/api/generate",
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=120)
                    ) as response:
                        if response.status != 200:
                            raise Exception(f"Ollama API returned status {response.status}")
                        result = await response.json()
                        return result.get("response", "")
            
            # Make async request
            response_text = await _make_request()
            
            # Try to parse JSON from response
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
            
            # Calculate confidence (Ollama doesn't provide confidence scores)
            # Use a moderate confidence value for local models
            confidence = 75.0
            
            return {
                "raw_text": raw_text,
                "confidence": confidence,
                "structured_data": structured_data,
                "provider": "ollama",
                "metadata": {
                    "model": self.model,
                    "base_url": self.base_url,
                    "response_length": len(response_text)
                }
            }
            
        except Exception as e:
            raise Exception(f"Ollama OCR failed: {str(e)}")
    
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
        """Check if Ollama is available"""
        try:
            import requests
            # Try to check if Ollama is running
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def get_provider_name(self) -> str:
        """Return provider name"""
        return "ollama"
