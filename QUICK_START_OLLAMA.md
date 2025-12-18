# Quick Start: Using Ollama for Form Extraction

## 5-Minute Setup Guide

### Step 1: Install Ollama (2 minutes)

**macOS:**
```bash
brew install ollama
```

**Linux:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

**Windows:**
Download from https://ollama.ai/download

### Step 2: Download Vision Model (1 minute)

```bash
ollama pull llama3.2-vision
```

This downloads ~4GB. Wait for completion.

### Step 3: Verify Installation (30 seconds)

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Should return list of models including llama3.2-vision
```

### Step 4: Configure Application (30 seconds)

Create/update `.env` file in project root:

```bash
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_VISION_MODEL=llama3.2-vision
```

### Step 5: Test with Empty Form (1 minute)

```bash
# Upload form using Ollama
curl -X POST http://127.0.0.1:8000/api/upload \
  -F "file=@data/samples/pdfs/student data form scanned.pdf" \
  -F "ocr_provider=ollama"
```

Or use the frontend:
1. Go to http://localhost:5173/upload
2. Select **"Ollama (Local AI)"** from dropdown
3. Upload form
4. View extracted structured data

## What You Get

✅ **Free OCR** - No API costs  
✅ **Private** - Data stays local  
✅ **Structured JSON** - Direct field extraction  
✅ **Checkbox Detection** - Visual checkbox recognition  
✅ **Multi-page Support** - Handles 3-page forms  

## Example Output

```json
{
  "structured_data": {
    "student_name": "John Doe",
    "date_of_birth": "01/01/2000",
    "gender": "Male",
    "phone_number": "9876543210",
    "email": "john@example.com",
    "permanent_address": "123 Main St, City, State",
    "pincode": "123456",
    "father_name": "Father Name",
    "course_applied": "B.Tech Computer Science",
    "checkboxes": {
      "general_category": {"checked": true},
      "hostel_required": {"checked": false}
    }
  }
}
```

## Troubleshooting

**Ollama not found:**
```bash
# Start Ollama server
ollama serve
```

**Model not downloaded:**
```bash
# List downloaded models
ollama list

# Pull model if missing
ollama pull llama3.2-vision
```

**Backend can't connect:**
- Check `OLLAMA_BASE_URL` in `.env`
- Verify Ollama is running: `curl http://localhost:11434/api/tags`
- Restart backend server

## Next Steps

- See `TRAINING_AND_IMPROVEMENT_GUIDE.md` for:
  - Training custom models
  - Improving accuracy
  - Collecting training data
  - Batch processing 150,000 pages

