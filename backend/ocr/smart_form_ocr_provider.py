"""
Smart Form OCR Provider - Premium AI-powered OCR for Admission Forms
Combines multiple OCR providers with intelligent selection and fallback
Specifically optimized for SRCC Student Data Forms

Provider Priority:
1. Claude Vision (best for complex handwritten forms)
2. GPT-4 Vision (excellent form understanding)
3. Google Vision (great handwriting recognition)
4. CRAFT+TrOCR (trainable, good for specific forms)
5. Tesseract (free, always available fallback)
"""
import os
import io
import base64
import json
import re
from typing import Dict, Any, Optional, List, Tuple
from PIL import Image
import asyncio

from backend.ocr.base_provider import OCRProvider
from backend.config import settings
from backend.utils.image_preprocessing import enhance_for_ocr


class SmartFormOCRProvider(OCRProvider):
    """
    Premium AI-powered OCR provider optimized for handwritten admission forms.
    
    Features:
    - Multi-page PDF processing
    - Claude Vision for high-accuracy form extraction
    - Intelligent field mapping for SRCC forms
    - Checkbox and selection detection
    - Confidence scoring
    - Automatic fallback to local models
    """
    
    # SRCC Form field definitions with exact positions
    FORM_FIELDS = {
        # Page 1 - Academic & Personal Details
        "page_1": {
            "academic_session": {"label": "Academic Session", "type": "text"},
            "course": {"label": "Course", "type": "checkbox", "options": ["B.COM.(H)", "B.A.(H) ECO"]},
            "admission_category": {"label": "Admission Category", "type": "checkbox", 
                "options": ["GEN", "OBC", "SC", "ST", "Sports", "PwD", "EWS", "Foreign", "CW", "KM", "Others", "ECA"]},
            "du_portal_form_number": {"label": "DU Portal Form Number", "type": "text"},
            "cuet_score": {"label": "CUET Score", "type": "number"},
            "college_roll_no": {"label": "College Roll No.", "type": "text"},
            "date_of_admission": {"label": "Date of Admission", "type": "date"},
            "first_name": {"label": "First Name", "type": "text"},
            "middle_name": {"label": "Middle Name", "type": "text"},
            "surname": {"label": "Surname", "type": "text"},
            "gender": {"label": "Gender", "type": "checkbox", "options": ["Male", "Female", "Transgender"]},
            "date_of_birth": {"label": "Date of Birth", "type": "date"},
            "permanent_address": {"label": "Permanent Address", "type": "multiline"},
            "permanent_state": {"label": "State (Permanent)", "type": "text"},
            "permanent_pincode": {"label": "PIN (Permanent)", "type": "number"},
            "correspondence_address": {"label": "Correspondence Address", "type": "multiline"},
            "correspondence_state": {"label": "State (Correspondence)", "type": "text"},
            "correspondence_pincode": {"label": "PIN (Correspondence)", "type": "number"},
            "email": {"label": "Email", "type": "email"},
            "phone_number": {"label": "Contact Number 1", "type": "phone"},
            "alternate_phone": {"label": "Contact Number 2", "type": "phone"},
            "mother_name": {"label": "Mother's Name", "type": "text"},
            "father_name": {"label": "Father's Name", "type": "text"},
        },
        # Page 2 - CUET Marks & Additional Details
        "page_2": {
            "cuet_subject_1": {"label": "CUET Subject 1", "type": "text"},
            "cuet_score_obtained_1": {"label": "CUET Score 1", "type": "number"},
            "cuet_subject_2": {"label": "CUET Subject 2", "type": "text"},
            "cuet_score_obtained_2": {"label": "CUET Score 2", "type": "number"},
            "cuet_subject_3": {"label": "CUET Subject 3", "type": "text"},
            "cuet_score_obtained_3": {"label": "CUET Score 3", "type": "number"},
            "cuet_subject_4": {"label": "CUET Subject 4", "type": "text"},
            "cuet_score_obtained_4": {"label": "CUET Score 4", "type": "number"},
            "cuet_subject_5": {"label": "CUET Subject 5", "type": "text"},
            "cuet_score_obtained_5": {"label": "CUET Score 5", "type": "number"},
            "cuet_subject_6": {"label": "CUET Subject 6", "type": "text"},
            "cuet_score_obtained_6": {"label": "CUET Score 6", "type": "number"},
            "cuet_total_score": {"label": "Total CUET Score", "type": "number"},
            "twelfth_year": {"label": "Year of Passing (Class XII)", "type": "year"},
            "twelfth_board": {"label": "Board / University", "type": "text"},
            "twelfth_roll_number": {"label": "Examination Roll No.", "type": "text"},
            "twelfth_institution": {"label": "Institution Last Attended", "type": "text"},
            "hindi_studied_upto": {"label": "Hindi Studied Upto", "type": "text"},
            "nationality": {"label": "Nationality", "type": "text"},
            "religion": {"label": "Religion", "type": "text"},
            "blood_group": {"label": "Blood Group", "type": "text"},
            "below_poverty_line": {"label": "Below Poverty Line", "type": "text"},
            "annual_income": {"label": "Parent's Annual Income", "type": "number"},
            "minority_category": {"label": "Minority Category", "type": "checkbox",
                "options": ["Muslim", "Jain", "Sikh", "Persian", "Christian", "Buddhists", "Others"]},
        },
        # Page 3 - Parent/Guardian Details
        "page_3": {
            "mother_occupation": {"label": "Mother's Occupation", "type": "text"},
            "mother_designation": {"label": "Mother's Designation", "type": "text"},
            "mother_organization": {"label": "Mother's Organization", "type": "text"},
            "mother_email": {"label": "Mother's Email", "type": "email"},
            "mother_mobile": {"label": "Mother's Mobile", "type": "phone"},
            "father_occupation": {"label": "Father's Occupation", "type": "text"},
            "father_designation": {"label": "Father's Designation", "type": "text"},
            "father_organization": {"label": "Father's Organization", "type": "text"},
            "father_email": {"label": "Father's Email", "type": "email"},
            "father_mobile": {"label": "Father's Mobile", "type": "phone"},
            "guardian_name": {"label": "Local Guardian Name", "type": "text"},
            "guardian_residential_address": {"label": "Guardian Address", "type": "multiline"},
            "guardian_organization": {"label": "Guardian Organization", "type": "text"},
            "guardian_email": {"label": "Guardian Email", "type": "email"},
            "guardian_mobile": {"label": "Guardian Mobile", "type": "phone"},
            "du_enrollment_number": {"label": "DU Enrollment Number", "type": "text"},
            "hindi_medium_preference": {"label": "Hindi Medium Preference", "type": "checkbox", "options": ["Yes", "No"]},
            "category_certificate_authority": {"label": "Certificate Issuing Authority", "type": "text"},
            "category_certificate_number": {"label": "Certificate Number", "type": "text"},
            "category_certificate_date": {"label": "Certificate Date", "type": "date"},
            "disability_percentage": {"label": "Disability Percentage", "type": "number"},
            "disability_type": {"label": "Disability Type", "type": "text"},
            "udid_number": {"label": "UDID Number", "type": "text"},
        },
    }

    def __init__(self):
        self._claude_client = None
        self._openai_client = None
        self.api_key = getattr(settings, 'ANTHROPIC_API_KEY', '')
        self.openai_key = getattr(settings, 'OPENAI_API_KEY', '')
        self.model = getattr(settings, 'CLAUDE_VISION_MODEL', 'claude-3-5-sonnet-20241022')
        from backend.ocr.ocr_factory import OCRFactory
        from backend.utils.ai_form_parser import AIFormParser
        self.ocr_factory_class = OCRFactory  # Store class, not instance (to avoid recursion)
        self.ai_form_parser = AIFormParser()
    
    def _get_claude_client(self):
        """Lazy load Anthropic client"""
        if self._claude_client is None:
            try:
                import anthropic
                if not self.api_key:
                    raise ValueError("ANTHROPIC_API_KEY not configured")
                self._claude_client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("Anthropic package not installed. Install with: pip install anthropic")
        return self._claude_client
    
    def _image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL Image to base64 string"""
        buffered = io.BytesIO()
        # Convert to RGB if necessary
        if image.mode in ('RGBA', 'LA', 'P'):
            image = image.convert('RGB')
        image.save(buffered, format="JPEG", quality=95)
        return base64.b64encode(buffered.getvalue()).decode()
    
    def _get_extraction_prompt(self, page_num: int = 1) -> str:
        """Generate extraction prompt based on page number"""
        base_prompt = """You are an expert OCR system specialized in extracting data from handwritten Indian college admission forms.

Analyze this SRCC (Shri Ram College of Commerce) Student Data Form image and extract ALL handwritten information.

CRITICAL INSTRUCTIONS:
1. Extract ONLY handwritten text, ignore printed form labels
2. For checkboxes, identify which options are ticked/marked
3. Read handwritten text carefully - many names are Indian names
4. Dates are in DD/MM/YYYY format
5. Phone numbers are 10-digit Indian mobile numbers
6. PINs are 6-digit postal codes
7. Return null for empty/blank fields

Extract the following fields as JSON:
"""
        
        fields_prompt = ""
        if page_num == 1:
            fields_prompt = """
{
    "academic_session": "string or null",
    "course": "B.COM.(H) or B.A.(H) ECO or null - check which box is ticked",
    "admission_category": "GEN/OBC/SC/ST/Sports/PwD/EWS/Foreign/CW/KM/Others/ECA - check ticked box",
    "du_portal_form_number": "string or null",
    "cuet_score": "number or null",
    "college_roll_no": "string or null",
    "date_of_admission": "DD/MM/YYYY or null",
    "first_name": "string or null - handwritten in NAME boxes",
    "middle_name": "string or null",
    "surname": "string or null",
    "student_name": "full name combining first, middle, surname",
    "gender": "Male/Female/Transgender - check which box is ticked",
    "date_of_birth": "DD/MM/YYYY or null",
    "permanent_address_line1": "first line of address",
    "permanent_address_line2": "second line of address",
    "permanent_address_line3": "third line of address",
    "permanent_state": "state name",
    "permanent_pincode": "6-digit PIN",
    "correspondence_address_line1": "first line",
    "correspondence_address_line2": "second line",
    "correspondence_address_line3": "third line",
    "correspondence_state": "state name",
    "correspondence_pincode": "6-digit PIN",
    "email": "email address",
    "phone_number": "10-digit mobile number",
    "alternate_phone": "10-digit mobile number",
    "mother_name": "mother's full name",
    "father_name": "father's full name"
}"""
        elif page_num == 2:
            fields_prompt = """
{
    "cuet_subjects": [
        {"subject": "name", "total_score": number, "score_obtained": number},
        ...
    ],
    "cuet_total_score": "total marks obtained",
    "twelfth_year": "year of passing (YYYY)",
    "twelfth_board": "board/university name",
    "twelfth_roll_number": "examination roll number",
    "twelfth_institution": "school/college name",
    "hindi_studied_upto": "VIII/X/XII/Never",
    "nationality": "string",
    "religion": "string",
    "blood_group": "A+/A-/B+/B-/O+/O-/AB+/AB-",
    "below_poverty_line": "Yes/No",
    "annual_income": "number",
    "minority_category": "Muslim/Jain/Sikh/Persian/Christian/Buddhists/Others or null"
}"""
        elif page_num == 3:
            fields_prompt = """
{
    "mother_occupation": "string",
    "mother_designation": "string",
    "mother_organization": "string with address",
    "mother_email": "email",
    "mother_mobile": "10-digit number",
    "mother_landline_code": "3-digit code",
    "mother_landline": "8-digit number",
    "father_occupation": "string",
    "father_designation": "string",
    "father_organization": "string with address",
    "father_email": "email",
    "father_mobile": "10-digit number",
    "father_landline_code": "3-digit code",
    "father_landline": "8-digit number",
    "guardian_name": "string",
    "guardian_residential_address": "full address",
    "guardian_organization": "string with address",
    "guardian_email": "email",
    "guardian_mobile": "10-digit number",
    "guardian_landline_code": "3-digit code",
    "guardian_landline": "8-digit number",
    "du_enrollment_number": "string",
    "hindi_medium_preference": "Yes/No",
    "category_certificate_authority": "issuing authority name & address",
    "category_certificate_number": "certificate number",
    "category_certificate_date": "DD/MM/YYYY",
    "disability_percentage": "number (percentage)",
    "disability_type": "VH/HH/OH",
    "udid_number": "string"
}"""
        else:
            fields_prompt = """
{
    "all_fields": "Extract all visible handwritten content as key-value pairs"
}"""
        
        return base_prompt + fields_prompt + """

IMPORTANT: 
- Return ONLY valid JSON, no markdown formatting
- Set fields to null if not filled/visible
- For names, maintain proper capitalization (e.g., "Rahul Kumar Singh")
- For addresses, preserve line breaks as separate line fields
- Phone numbers should be digits only
"""

    async def extract_text(self, image: Image.Image, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract text and structured data from form image using best available OCR provider.
        Prioritizes: Google Document AI > Google Vision > Claude Vision > CRAFT+TrOCR > Tesseract
        """
        all_results = {}
        raw_text_candidates = []
        structured_data_candidates = []
        confidence_scores = []

        # Priority order for best accuracy on forms
        priority_providers = [
            "google-documentai",  # Best for structured forms
            "google-vision",      # Excellent for handwriting
            "claude-vision",      # AI-powered understanding
            "craft-trocr",        # Trained local model
            "tesseract",          # Fallback
        ]

        tasks = []
        # Get providers dict directly to avoid recursion
        providers_dict = self.ocr_factory_class._get_providers()
        for provider_name in priority_providers:
            if provider_name in providers_dict:
                try:
                    # Quick check if provider is available without full recursion
                    provider_class = providers_dict[provider_name]
                    # Only check if it's not SmartFormOCRProvider to avoid recursion
                    if provider_class.__name__ != 'SmartFormOCRProvider':
                        provider_instance = provider_class()
                        if provider_instance.is_available():
                            tasks.append(self._run_provider_extraction(provider_name, image, language))
                    else:
                        # Skip self to avoid recursion
                        continue
                except Exception:
                    continue

        # Run priority extractions in parallel (or sequentially if needed)
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for res in results:
            if not isinstance(res, Exception) and res:
                provider_name = res.get("provider")
                all_results[provider_name] = res
                if res.get("raw_text"):
                    raw_text_candidates.append(res["raw_text"])
                if res.get("structured_data"):
                    structured_data_candidates.append(res["structured_data"])
                if res.get("confidence") is not None:
                    confidence_scores.append(res["confidence"])

        # Combine raw text from best candidates
        combined_raw_text = " ".join(raw_text_candidates)

        # Parse structured data from combined raw text and best structured candidates
        final_structured_data = {}
        if combined_raw_text:
            # Use the advanced SRCC extractor first (better decimal support and extraction)
            from backend.utils.srcc_form_extractor import extract_srcc_form
            final_structured_data.update(extract_srcc_form(combined_raw_text))
            # Then overlay with AI parser results
            ai_parsed_from_text = self.ai_form_parser.parse_from_text(combined_raw_text)
            final_structured_data.update(ai_parsed_from_text)

        # Merge structured data from providers that returned it
        for sd in structured_data_candidates:
            if isinstance(sd, dict):
                final_structured_data.update(sd)  # Simple merge, could be smarter

        # Calculate overall confidence
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        
        # Improve confidence based on structured data validation
        from backend.utils.confidence_scorer import improve_ocr_confidence
        improved_confidence = improve_ocr_confidence(final_structured_data, avg_confidence)

        return {
            "raw_text": combined_raw_text.strip(),
            "confidence": round(improved_confidence, 2),
            "structured_data": final_structured_data,
            "provider": self.get_provider_name(),
            "metadata": {
                "providers_attempted": list(all_results.keys()),
                "all_provider_results": {k: {
                    "raw_text_len": len(v.get("raw_text", "")),
                    "confidence": v.get("confidence"),
                    "provider": v.get("provider")
                } for k, v in all_results.items()}
            }
        }

    async def _run_provider_extraction(self, provider_name: str, image: Image.Image, language: Optional[str]) -> Optional[Dict[str, Any]]:
        """Helper to run a single provider's extraction."""
        try:
            # Create provider directly to avoid recursion issues
            providers_dict = self.ocr_factory_class._get_providers()
            if provider_name in providers_dict:
                provider_class = providers_dict[provider_name]
                provider = provider_class()
                result = await provider.extract_text(image, language)
                result["provider"] = provider_name  # Ensure provider name is in result
                return result
            else:
                raise ValueError(f"Provider {provider_name} not found")
        except Exception as e:
            print(f"SmartFormOCRProvider: {provider_name} failed: {e}")
            return None
    
    async def _extract_with_claude(self, image: Image.Image, page_num: int = 1) -> Dict[str, Any]:
        """Extract using Claude Vision"""
        client = self._get_claude_client()
        base64_image = self._image_to_base64(image)
        prompt = self._get_extraction_prompt(page_num)
        
        message = client.messages.create(
            model=self.model,
            max_tokens=4000,
            temperature=0.1,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
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
        
        response_text = message.content[0].text
        
        # Parse JSON from response
        structured_data = self._parse_json_response(response_text)
        
        # Build raw text from structured data
        raw_text = self._structured_to_text(structured_data)
        
        # Calculate confidence based on fields extracted
        filled_fields = sum(1 for v in structured_data.values() if v is not None and v != "" and v != [])
        total_fields = len(structured_data)
        confidence = min(95.0, 70.0 + (filled_fields / max(total_fields, 1)) * 25)
        
        return {
            "raw_text": raw_text,
            "confidence": confidence,
            "structured_data": structured_data,
            "provider": "smart-form-ocr",
            "metadata": {
                "model": self.model,
                "page": page_num,
                "fields_extracted": filled_fields
            }
        }
    
    async def extract_multi_page(self, images: List[Image.Image]) -> Dict[str, Any]:
        """Extract from multiple pages and merge results"""
        all_data = {}
        all_raw_text = []
        total_confidence = 0
        
        for i, image in enumerate(images):
            page_num = i + 1
            try:
                result = await self._extract_with_claude(image, page_num)
                
                # Merge structured data
                if result.get("structured_data"):
                    for key, value in result["structured_data"].items():
                        if value is not None and value != "" and value != []:
                            # Don't overwrite existing non-null values
                            if key not in all_data or all_data[key] is None:
                                all_data[key] = value
                
                all_raw_text.append(f"=== Page {page_num} ===\n{result.get('raw_text', '')}")
                total_confidence += result.get("confidence", 0)
                
            except Exception as e:
                all_raw_text.append(f"=== Page {page_num} ===\nError: {str(e)}")
        
        # Process CUET subjects
        all_data = self._process_cuet_subjects(all_data)
        
        # Build combined student name
        if not all_data.get("student_name"):
            name_parts = [
                all_data.get("first_name", ""),
                all_data.get("middle_name", ""),
                all_data.get("surname", "")
            ]
            full_name = " ".join(p for p in name_parts if p).strip()
            if full_name:
                all_data["student_name"] = full_name
        
        # Combine addresses
        for prefix in ["permanent", "correspondence"]:
            if not all_data.get(f"{prefix}_address"):
                lines = [
                    all_data.get(f"{prefix}_address_line1", ""),
                    all_data.get(f"{prefix}_address_line2", ""),
                    all_data.get(f"{prefix}_address_line3", "")
                ]
                addr = ", ".join(l for l in lines if l).strip()
                if addr:
                    all_data[f"{prefix}_address"] = addr
        
        avg_confidence = total_confidence / max(len(images), 1)
        
        return {
            "raw_text": "\n\n".join(all_raw_text),
            "confidence": avg_confidence,
            "structured_data": all_data,
            "provider": "smart-form-ocr",
            "metadata": {
                "pages_processed": len(images),
                "model": self.model
            }
        }
    
    def _process_cuet_subjects(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process CUET subjects from array to individual fields"""
        if "cuet_subjects" in data and isinstance(data["cuet_subjects"], list):
            for i, subject in enumerate(data["cuet_subjects"][:6], 1):
                if isinstance(subject, dict):
                    data[f"cuet_subject_{i}"] = subject.get("subject", "")
                    data[f"cuet_total_score_{i}"] = str(subject.get("total_score", ""))
                    data[f"cuet_score_obtained_{i}"] = str(subject.get("score_obtained", ""))
            del data["cuet_subjects"]
        return data
    
    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """Parse JSON from Claude response"""
        # Try to extract JSON from markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find raw JSON object
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = response_text
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # Try to fix common JSON issues
            fixed = json_str.replace("'", '"').replace("None", "null").replace("True", "true").replace("False", "false")
            try:
                return json.loads(fixed)
            except:
                return {"raw_response": response_text}
    
    def _structured_to_text(self, data: Dict[str, Any]) -> str:
        """Convert structured data to readable text"""
        lines = []
        for key, value in data.items():
            if value is not None and value != "" and value != []:
                key_display = key.replace("_", " ").title()
                if isinstance(value, (dict, list)):
                    lines.append(f"{key_display}: {json.dumps(value)}")
                else:
                    lines.append(f"{key_display}: {value}")
        return "\n".join(lines)
    
    async def _fallback_extraction(self, image: Image.Image) -> Dict[str, Any]:
        """
        Intelligent fallback chain using all available providers
        Priority: GPT-4 Vision -> Google Vision -> CRAFT+TrOCR -> TrOCR -> Tesseract
        """
        fallback_providers = [
            ("gpt4-vision", self._try_gpt4_vision),
            ("google-vision", self._try_google_vision),
            ("craft-trocr", self._try_craft_trocr),
            ("trocr", self._try_trocr),
            ("tesseract", self._try_tesseract),
        ]
        
        last_error = None
        for provider_name, provider_func in fallback_providers:
            try:
                result = await provider_func(image)
                if result and result.get("raw_text"):
                    result["provider"] = f"smart-form-ocr-fallback-{provider_name}"
                    return result
            except Exception as e:
                last_error = e
                continue
        
        return {
            "raw_text": "",
            "confidence": 0.0,
            "structured_data": {},
            "provider": "smart-form-ocr",
            "error": f"All fallback providers failed. Last error: {str(last_error)}"
        }
    
    async def _try_gpt4_vision(self, image: Image.Image) -> Dict[str, Any]:
        """Try GPT-4 Vision"""
        from backend.ocr.gpt4_vision_provider import GPT4VisionProvider
        provider = GPT4VisionProvider()
        if provider.is_available():
            return await provider.extract_text(image)
        raise Exception("GPT-4 Vision not available")
    
    async def _try_google_vision(self, image: Image.Image) -> Dict[str, Any]:
        """Try Google Vision"""
        from backend.ocr.google_vision_provider import GoogleVisionProvider
        provider = GoogleVisionProvider()
        if provider.is_available():
            return await provider.extract_text(image)
        raise Exception("Google Vision not available")
    
    async def _try_craft_trocr(self, image: Image.Image) -> Dict[str, Any]:
        """Try CRAFT+TrOCR"""
        from backend.ocr.craft_trocr_provider import CraftTrocrProvider
        provider = CraftTrocrProvider()
        if provider.is_available():
            return await provider.extract_text(image)
        raise Exception("CRAFT+TrOCR not available")
    
    async def _try_trocr(self, image: Image.Image) -> Dict[str, Any]:
        """Try TrOCR"""
        from backend.ocr.trocr_provider import TrocrProvider
        provider = TrocrProvider()
        if provider.is_available():
            return await provider.extract_text(image)
        raise Exception("TrOCR not available")
    
    async def _try_tesseract(self, image: Image.Image) -> Dict[str, Any]:
        """Try Tesseract (always available fallback)"""
        from backend.ocr.tesseract_provider import TesseractProvider
        provider = TesseractProvider()
        # Preprocess image for better Tesseract results
        enhanced = enhance_for_ocr(image)
        return await provider.extract_text(enhanced, preprocess=False)
    
    async def extract_with_all_providers(self, image: Image.Image) -> Dict[str, Any]:
        """
        Extract using all available providers and combine/compare results
        Useful for benchmarking and getting the best possible extraction
        """
        results = {}
        providers_to_try = [
            ("claude-vision", lambda: self._extract_with_claude(image)),
            ("gpt4-vision", lambda: self._try_gpt4_vision(image)),
            ("google-vision", lambda: self._try_google_vision(image)),
            ("craft-trocr", lambda: self._try_craft_trocr(image)),
            ("trocr", lambda: self._try_trocr(image)),
            ("tesseract", lambda: self._try_tesseract(image)),
        ]
        
        for provider_name, extract_func in providers_to_try:
            try:
                result = await extract_func()
                if result and result.get("raw_text"):
                    results[provider_name] = result
            except Exception as e:
                results[provider_name] = {"error": str(e)}
        
        # Select best result based on confidence and text length
        best_provider = None
        best_score = 0
        
        for provider_name, result in results.items():
            if "error" in result:
                continue
            confidence = result.get("confidence", 0)
            text_len = len(result.get("raw_text", ""))
            # Score = confidence * log(text_length + 1)
            import math
            score = confidence * math.log(text_len + 1)
            if score > best_score:
                best_score = score
                best_provider = provider_name
        
        return {
            "best_provider": best_provider,
            "best_result": results.get(best_provider, {}),
            "all_results": results
        }
    
    def is_available(self) -> bool:
        """Check if provider is available (requires at least one underlying provider)
        
        Note: This method checks providers directly to avoid infinite recursion
        when called from OCRFactory.get_available_providers()
        """
        try:
            # Get providers dict directly (no recursion)
            providers_dict = self.ocr_factory_class._get_providers()
            
            priority_providers = [
                "google-documentai",
                "google-vision",
                "claude-vision",
                "craft-trocr",
                "tesseract",
            ]
            
            for provider_name in priority_providers:
                if provider_name in providers_dict:
                    try:
                        provider_class = providers_dict[provider_name]
                        # Skip self to avoid recursion (check by class name to avoid circular import)
                        if provider_class.__name__ == 'SmartFormOCRProvider':
                            continue
                        # Check if provider is available
                        provider_instance = provider_class()
                        if provider_instance.is_available():
                            return True
                    except Exception:
                        continue
            
            return False
        except Exception:
            return False
    
    def get_provider_name(self) -> str:
        return "smart-form-ocr"

