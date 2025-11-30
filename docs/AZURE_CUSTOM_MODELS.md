# Azure Document Intelligence Custom Models Guide

This guide explains how to use custom models with Azure Form Recognizer for improved accuracy on your specific admission forms.

## Overview

Azure Document Intelligence supports two types of custom models:

1. **Custom Template Models** - Best for forms with consistent visual structure
2. **Custom Neural Models** - Best for forms with varying layouts but same information

According to the [Azure documentation](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/train/custom-model?view=doc-intel-4.0.0), custom neural models are recommended for better accuracy, especially when documents have the same information but different page structures.

## Benefits of Custom Models

- **Higher Accuracy**: Trained specifically on your document types
- **Better Field Extraction**: Understands your specific form fields
- **Signature Detection**: Custom models support signature field detection
- **Overlapping Fields**: Neural models support overlapping field extraction
- **Table Confidence**: Row and cell-level confidence scores (v4.0+)

## Prerequisites

1. Azure Document Intelligence resource (already configured)
2. At least 5 labeled training documents (more recommended for better accuracy)
3. Document Intelligence Studio access or REST API access

## Training a Custom Model

### Option 1: Using Document Intelligence Studio (Recommended)

1. **Access Document Intelligence Studio**
   - Go to https://formrecognizer.appliedai.azure.com/studio
   - Sign in with your Azure account

2. **Create a Project**
   - Select "Custom extraction models"
   - Click "Create a project"
   - Enter project details:
     - Project name: e.g., "Admission Forms"
     - Description: "Custom model for college admission forms"
   - Connect your storage account and blob container with training documents

3. **Label Your Documents**
   - Upload at least 5 sample admission forms
   - Label the fields you want to extract:
     - Student name
     - Date of birth
     - Address
     - Phone number
     - Course applied
     - etc.
   - Use different values in each field across documents

4. **Train the Model**
   - Choose model type:
     - **Neural** (recommended): Better for varying layouts
     - **Template**: Better for consistent visual structure
   - Click "Train" and wait for training to complete

5. **Get Model ID**
   - After training, copy the Model ID
   - Format: `{project-name}_{model-name}_{version}`

### Option 2: Using REST API

See the [Azure documentation](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/train/custom-model?view=doc-intel-4.0.0) for REST API training instructions.

## Configuring Custom Model in This Application

Once you have your custom model ID, configure it in your `.env` file:

```env
# Azure Form Recognizer Configuration
AZURE_FORM_RECOGNIZER_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_FORM_RECOGNIZER_KEY=your-api-key

# Custom Model ID (optional - leave empty to use prebuilt-document)
AZURE_FORM_RECOGNIZER_CUSTOM_MODEL_ID=admission-forms_model_v1.0
```

## Training Data Best Practices

According to Azure documentation:

### Optimal Training Data

- **Use text-based PDFs** instead of image-based when possible
- **Organize documents** by format (JPEG, PNG, PDF, TIFF)
- **Use complete forms** with all fields filled in
- **Vary field values** across training documents
- **Use larger datasets** (10-15+ documents) for low-quality images
- **Balance your dataset** across formats and document types

### Minimum Requirements

- **Custom Template**: 5 documents minimum, 500 pages max
- **Custom Neural**: 5 documents minimum, 50,000 pages max
- **Training data size**: 50 MB for template, 1 GB for neural

### File Requirements

- **Formats**: PDF, JPEG/JPG, PNG, BMP, TIFF
- **File size**: Max 500 MB (paid tier) or 4 MB (free tier)
- **Dimensions**: 50x50 to 10,000x10,000 pixels
- **Pages**: Up to 2,000 pages per document

## Using Custom Models

### Automatic Detection

Once configured, the application automatically uses your custom model:

1. Upload a form via the web interface
2. Select "azure-form-recognizer" as the OCR provider
3. The system uses your custom model automatically

### API Usage

The custom model is used automatically when:
- `ocr_provider=azure-form-recognizer` is specified
- `AZURE_FORM_RECOGNIZER_CUSTOM_MODEL_ID` is set in `.env`

### Checking Model Status

Query the `/api/providers` endpoint to see model information:

```bash
curl http://localhost:8000/api/providers
```

Response includes:
```json
{
  "providers": ["tesseract", "azure-form-recognizer", "best"],
  "default": "azure-form-recognizer",
  "model_info": {
    "model_id": "admission-forms_model_v1.0",
    "model_type": "custom",
    "supports": {
      "form_fields": true,
      "selection_marks": true,
      "tables": true,
      "signatures": true,
      "overlapping_fields": true
    }
  }
}
```

## Model Lifecycle

- Custom models follow the API version lifecycle
- GA (General Availability) models are supported long-term
- Preview models may be deprecated with API version changes
- Keep your models updated to the latest API version

## Troubleshooting

### Model Not Found

If you get a "model not found" error:
1. Verify the model ID is correct
2. Ensure the model was trained in the same Azure region
3. Check that the model is not deleted or expired

### Low Accuracy

If accuracy is lower than expected:
1. Add more training documents (10-15+ recommended)
2. Ensure training documents are diverse
3. Consider using a neural model instead of template
4. Verify training documents match your production forms

### Model Training Fails

Common issues:
- Insufficient training data (need at least 5 documents)
- Documents are password-protected (remove passwords)
- File size exceeds limits
- Unsupported file format

## Additional Resources

- [Azure Document Intelligence Custom Models Documentation](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/train/custom-model?view=doc-intel-4.0.0)
- [Document Intelligence Studio](https://formrecognizer.appliedai.azure.com/studio)
- [Custom Neural Models Guide](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/concept-custom-neural)
- [Custom Template Models Guide](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/concept-custom-template)

## Support

For issues with:
- **Model Training**: Check Azure Document Intelligence Studio
- **Model Configuration**: Verify `.env` settings
- **Application Integration**: Check application logs









