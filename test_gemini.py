"""Quick test of Gemini Vision API extraction on a sample form"""
import os, sys, json

# Set API key
os.environ['GEMINI_API_KEY'] = 'AIzaSyCOm3U7iCxxROyuUhgB_vkXbl_6yeCtgiw'

log = open('gemini_test_output.txt', 'w', encoding='utf-8')

def p(msg):
    print(msg)
    log.write(msg + '\n')
    log.flush()

try:
    import google.generativeai as genai
    from PIL import Image
    p("1. google-generativeai imported OK")
except ImportError as e:
    p(f"FAIL: {e}")
    sys.exit(1)

try:
    genai.configure(api_key=os.environ['GEMINI_API_KEY'])
    p("2. API key configured")
except Exception as e:
    p(f"FAIL configure: {e}")
    sys.exit(1)

try:
    model = genai.GenerativeModel('gemini-2.0-flash')
    p("3. Model created: gemini-2.0-flash")
except Exception as e:
    p(f"FAIL model: {e}")
    sys.exit(1)

img_path = r'c:\Users\as\Documents\GitHub\OCR-admission-forms\data\samples\images\student_data_form_scanned_page_01.png'
if not os.path.exists(img_path):
    p(f"FAIL: Image not found: {img_path}")
    sys.exit(1)

try:
    img = Image.open(img_path)
    p(f"4. Image loaded: {img.size}")
except Exception as e:
    p(f"FAIL image: {e}")
    sys.exit(1)

try:
    p("5. Calling Gemini API...")
    response = model.generate_content(
        [img, 'Extract the student name, date of birth, gender, and course from this Indian college admission form. Return as JSON.'],
        generation_config={'temperature': 0.1, 'max_output_tokens': 1024}
    )
    p(f"6. Response received!")
    p(f"Response text: {response.text[:500]}")
except Exception as e:
    p(f"FAIL generate: {type(e).__name__}: {e}")
    import traceback
    p(traceback.format_exc())
    sys.exit(1)

log.close()
