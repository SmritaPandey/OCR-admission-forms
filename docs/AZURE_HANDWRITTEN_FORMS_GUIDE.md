# Step-by-Step Guide: Using Azure Document Intelligence for Handwritten Student Admission Forms

Based on the [Azure Document Intelligence documentation](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/?view=doc-intel-4.0.0), this guide provides a complete walkthrough for processing handwritten admission forms.

## Which Model Type to Use?

According to the [model selection guide](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/concept/choose-model-feature?view=doc-intel-4.0.0), for **handwritten student admission forms**, you have two options:

### Recommended: **Custom Neural Model** ⭐
- **Best for**: Structured and semi-structured documents with handwritten content
- **Advantages**:
  - Better accuracy for handwritten text
  - Handles variations in form layouts
  - Supports overlapping fields
  - Signature detection support
  - Better for forms with same information but different visual structures

### Alternative: **Custom Template Model**
- **Best for**: Forms with very consistent, static visual layout
- **Use when**: All your forms have identical structure and positioning
- **Limitation**: Less flexible for layout variations

**Recommendation**: Start with a **Custom Neural Model** for best results with handwritten forms.

## Prerequisites

1. ✅ Azure subscription (free tier available)
2. ✅ Document Intelligence resource created
3. ✅ At least 5 sample admission forms with handwritten data
4. ✅ Azure Storage account with blob container (for training data)

## Step-by-Step Implementation

### Step 1: Prepare Your Training Documents

**Requirements:**
- **Minimum**: 5 labeled documents (10-15+ recommended for better accuracy)
- **Formats**: PDF, JPEG/JPG, PNG, BMP, TIFF
- **Quality**: High-resolution scans (300 DPI recommended)
- **Content**: Forms with all fields filled in (preferably handwritten)
- **Variety**: Use different values in each field across documents

**Best Practices:**
- Use text-based PDFs when possible (not scanned images)
- Ensure all fields are completed in training documents
- Include diverse handwriting styles
- Balance your dataset across different form variations

### Step 2: Access Document Intelligence Studio

1. Go to [Document Intelligence Studio](https://formrecognizer.appliedai.azure.com/studio)
2. Sign in with your Azure account
3. Select your Document Intelligence resource

### Step 3: Create a New Project

1. Click **"Custom extraction models"** on the home page
2. Under **"My Projects"**, click **"Create a project"**
3. Fill in project details:
   - **Project name**: `Admission Forms`
   - **Description**: `Custom model for college admission forms with handwritten data`
   - **Service resource**: Select your Document Intelligence resource
4. **Connect your training data source**:
   - **Storage account**: Select your Azure Storage account
   - **Blob container**: Select or create a container for training documents
5. Click **"Review and create"** then **"Create"**

### Step 4: Upload Training Documents

1. In your project, click **"Add documents"** or drag and drop files
2. Upload at least 5 sample admission forms
3. Wait for documents to be processed

### Step 5: Label Your Documents

For each uploaded document:

1. **Select a document** to label
2. **Create field labels** for each field you want to extract:
   - Click on a field value (e.g., student name)
   - Enter the field name (e.g., `student_name`)
   - Press Enter to save
3. **Label all required fields**:
   - **Basic Details**: `student_name`, `date_of_birth`, `gender`, `aadhar_number`
   - **Address**: `permanent_address`, `correspondence_address`, `pincode`, `city`, `state`
   - **Contact**: `phone_number`, `email`, `alternate_phone`
   - **Guardian Info**: `father_name`, `mother_name`, `guardian_name`, `guardian_phone`
   - **Education**: `tenth_board`, `tenth_percentage`, `twelfth_board`, `twelfth_percentage`
   - **Course**: `course_applied`, `application_number`, `enrollment_number`
   - **Additional fields** as needed

4. **Label selection marks** (checkboxes):
   - Click on checkboxes/radio buttons
   - Assign field names (e.g., `category`, `religion`)

5. **Label tables** (if applicable):
   - Select table regions
   - Assign table field names

6. **Label signatures** (if needed):
   - Select signature regions
   - Assign field names (e.g., `student_signature`, `guardian_signature`)

7. **Repeat for all training documents** (minimum 5, recommend 10-15+)

**Important**: 
- Use **consistent field names** across all documents
- Label the **same fields** in all documents
- Ensure **different values** in each field across documents

### Step 6: Train Your Custom Model

1. After labeling all documents, click **"Train"** button
2. **Select model type**:
   - Choose **"Neural"** (recommended for handwritten forms)
   - Or **"Template"** (if forms have identical visual structure)
3. **Enter model name**: e.g., `admission-forms-neural-v1`
4. **Click "Train"** and wait for training to complete (typically 10-30 minutes)

### Step 7: Test Your Model

1. After training completes, click **"Test"** tab
2. Upload a test document (not used in training)
3. Review the extracted fields
4. Check accuracy and confidence scores
5. Make corrections if needed

### Step 8: Get Your Model ID

1. After successful training, go to **"Models"** tab
2. Find your trained model
3. **Copy the Model ID** (format: `{project-name}_{model-name}_{version}`)
   - Example: `admission-forms_admission-forms-neural-v1_1.0`

### Step 9: Configure in Your Application

1. Open your `.env` file
2. Add your custom model ID:

```env
# Azure Form Recognizer Configuration
AZURE_FORM_RECOGNIZER_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_FORM_RECOGNIZER_KEY=your-api-key

# Custom Model ID for Handwritten Forms
AZURE_FORM_RECOGNIZER_CUSTOM_MODEL_ID=admission-forms_admission-forms-neural-v1_1.0
```

3. Restart your backend server

### Step 10: Use Your Custom Model

Your application will automatically use the custom model when:
- `ocr_provider=azure-form-recognizer` is selected
- The custom model ID is configured in `.env`

The system will:
1. Extract handwritten text from form fields
2. Return structured data with field names
3. Provide confidence scores for each field

## Field Mapping

Your custom model will extract fields based on the labels you created. The application's form parser will automatically map these to your database fields:

| Model Field | Database Field | Description |
|------------|---------------|-------------|
| `student_name` | `student_name` | Student's full name |
| `date_of_birth` | `date_of_birth` | Date of birth |
| `phone_number` | `phone_number` | Contact phone |
| `email` | `email` | Email address |
| `course_applied` | `course_applied` | Course name |
| `application_number` | `application_number` | Application ID |
| ... | ... | ... |

## Improving Accuracy

### If Accuracy is Low:

1. **Add more training documents** (15-20+ recommended)
2. **Improve document quality**:
   - Use 300 DPI scans
   - Ensure good contrast
   - Remove shadows and distortions
3. **Diversify training data**:
   - Include different handwriting styles
   - Vary form conditions (clean, slightly damaged, etc.)
4. **Review and correct labels**:
   - Ensure all fields are labeled consistently
   - Fix any labeling errors
5. **Retrain the model** with improved dataset

### Training Data Best Practices:

- ✅ Use text-based PDFs when possible
- ✅ Include forms with all fields completed
- ✅ Vary field values across documents
- ✅ Use larger datasets (10-15+) for better accuracy
- ✅ Balance dataset across formats and conditions
- ✅ Ensure consistent labeling across all documents

## Testing Your Model

1. **In Document Intelligence Studio**:
   - Use the "Test" tab to upload sample documents
   - Review extracted fields and confidence scores
   - Make corrections and retrain if needed

2. **In Your Application**:
   - Upload a form via the web interface
   - Select "azure-form-recognizer" as OCR provider
   - Review extracted data in the verification view
   - Verify accuracy of handwritten field extraction

## Monitoring and Maintenance

1. **Check Model Performance**:
   - Review confidence scores in extracted data
   - Monitor accuracy in production
   - Collect feedback from users

2. **Retrain When Needed**:
   - Add new training documents
   - Correct labeling errors
   - Retrain to improve accuracy

3. **Version Management**:
   - Create new model versions for improvements
   - Test new versions before deploying
   - Update model ID in `.env` when ready

## Troubleshooting

### Model Not Found Error
- Verify model ID is correct
- Ensure model was trained in same Azure region
- Check that model hasn't been deleted

### Low Accuracy
- Add more training documents
- Improve document quality
- Ensure consistent labeling
- Consider using Neural model instead of Template

### Training Fails
- Check minimum 5 documents requirement
- Verify documents aren't password-protected
- Ensure file sizes are within limits (500 MB paid, 4 MB free)
- Check supported file formats

## Additional Resources

- [Azure Document Intelligence Documentation](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/?view=doc-intel-4.0.0)
- [Model Selection Guide](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/concept/choose-model-feature?view=doc-intel-4.0.0)
- [Custom Neural Models](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/train/custom-neural?view=doc-intel-4.0.0)
- [Custom Template Models](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/train/custom-template?view=doc-intel-4.0.0)
- [Document Intelligence Studio](https://formrecognizer.appliedai.azure.com/studio)

## Summary

For handwritten student admission forms:
1. ✅ Use **Custom Neural Model** (recommended)
2. ✅ Prepare 10-15+ training documents with handwritten data
3. ✅ Label all fields consistently across documents
4. ✅ Train model in Document Intelligence Studio
5. ✅ Configure model ID in your `.env` file
6. ✅ Test and refine for better accuracy

Your application is already configured to support custom models - just add your model ID to `.env` and start using it!









