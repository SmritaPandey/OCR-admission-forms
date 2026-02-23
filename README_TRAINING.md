# Training & Using Local OCR for Form Extraction

## 🎯 Quick Summary

This guide shows you how to:
1. **Use Ollama** - Free, local AI OCR (no API costs for 150,000 pages!)
2. **Train Custom Models** - Improve accuracy with your specific forms
3. **Collect Training Data** - Annotate forms for better results

---

## 🚀 Quick Start: Ollama (5 minutes)

### Install & Setup

```bash
# 1. Install Ollama
brew install ollama  # macOS
# OR download from https://ollama.ai

# 2. Download vision model
ollama pull llama3.2-vision

# 3. Verify it's running
curl http://localhost:11434/api/tags
```

### Configure Application

Create `.env` file (copy from `.env.example`):

```bash
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_VISION_MODEL=llama3.2-vision
```

### Use in Application

**Via Frontend:**
1. Go to http://localhost:5173/upload
2. Select **"Ollama"** from OCR Provider dropdown
3. Upload form
4. View structured JSON output

**Via API:**
```bash
curl -X POST http://127.0.0.1:8000/api/upload \
  -F "file=@form.pdf" \
  -F "ocr_provider=ollama"
```

---

## 📚 Detailed Guides

- **`QUICK_START_OLLAMA.md`** - 5-minute Ollama setup
- **`TRAINING_AND_IMPROVEMENT_GUIDE.md`** - Complete training guide
  - Training TrOCR/Donut models
  - Collecting annotation data
  - Improving accuracy
  - Batch processing 150k pages

---

## 🎓 Training Custom Models

### Why Train?

- **Better Accuracy** - Fine-tuned on your specific forms
- **Handwriting Recognition** - Improved for cursive text
- **Form-Specific Fields** - Understands your field names
- **Cost Savings** - No API costs after training

### Steps

1. **Collect 50-100 annotated forms**
2. **Export training data** via annotation API
3. **Train TrOCR or Donut** model
4. **Deploy trained model**

See `TRAINING_AND_IMPROVEMENT_GUIDE.md` for details.

---

## 📊 Current Status

✅ **Ollama Provider** - Implemented and ready  
✅ **AI Form Parser** - Structured field extraction  
✅ **Checkbox Detection** - Visual checkbox recognition  
✅ **Annotation API** - Training data collection  
✅ **Multi-page Support** - Handles 3-page forms  
✅ **Batch Processing** - Process 150k pages efficiently  

📝 **Training Scripts** - Placeholder (needs implementation)

---

## 🔧 Configuration

### Ollama Settings

```bash
# .env file
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_VISION_MODEL=llama3.2-vision
```

### Available Models

- `llama3.2-vision` - Best for structured forms (recommended)
- `llava` - Alternative vision model
- `llava-phi3` - Smaller, faster option

### Provider Selection

The system automatically detects available providers. Ollama will appear in the dropdown once:
1. Ollama is installed and running
2. Vision model is downloaded
3. Backend can connect to Ollama API

---

## 💡 Tips for Best Results

### For Handwritten Forms

1. **Use Ollama or GPT-4/Claude** (vision-language models)
2. **Improve image quality** - 300 DPI scanning
3. **Preprocess images** - Increase contrast, denoise
4. **Train custom model** - Fine-tune on your handwriting

### For Checkbox Detection

1. **Use AI vision models** (not text-based)
2. **Visual detection** handles handwritten checkmarks
3. **Combines AI + regex** for best results

### For 150,000 Pages

1. **Use Ollama** - Free, no rate limits
2. **Enable caching** - `OCR_CACHE_ENABLED=true`
3. **Batch processing** - Upload multiple forms
4. **Parallel processing** - `BATCH_MAX_CONCURRENT=10`

---

## 🐛 Troubleshooting

**Ollama not showing in dropdown:**
- Check Ollama is running: `curl http://localhost:11434/api/tags`
- Restart backend server
- Check `.env` configuration

**Low accuracy:**
- Improve image quality
- Adjust preprocessing settings
- Try different model (`llava` instead of `llama3.2-vision`)
- Train custom model on your forms

**Slow processing:**
- Use GPU acceleration (if available)
- Reduce image size
- Enable caching
- Process in batches

---

## 📖 Next Steps

1. ✅ **Set up Ollama** - Get local OCR running
2. ✅ **Test with sample forms** - Verify extraction
3. 📝 **Annotate 50-100 forms** - Collect training data
4. 🎯 **Train custom model** - Fine-tune TrOCR/Donut
5. 🚀 **Deploy to production** - Process 150,000 pages

---

## 📁 Related Files

- `backend/ocr/ollama_provider.py` - Ollama implementation
- `backend/utils/ai_form_parser.py` - Form parsing
- `backend/utils/ai_checkbox_detector.py` - Checkbox detection
- `backend/api/routes/annotation.py` - Annotation API
- `backend/training/` - Training scripts (placeholders)

---

For detailed instructions, see:
- **Quick Setup:** `QUICK_START_OLLAMA.md`
- **Full Guide:** `TRAINING_AND_IMPROVEMENT_GUIDE.md`

