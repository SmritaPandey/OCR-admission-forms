@echo off
echo Creating .env template file...
echo.

if exist ".env" (
    echo .env file already exists. Skipping...
    goto :end
)

(
echo # Database Configuration
echo DATABASE_URL=sqlite:///./admission_forms.db
echo.
echo # OCR Provider Configuration
echo OCR_PROVIDER=tesseract
echo OCR_ENABLE_TESSERACT=true
echo OCR_ENABLE_GOOGLE_VISION=false
echo OCR_ENABLE_GOOGLE_DOCUMENT_AI=false
echo OCR_ENABLE_AZURE_VISION=false
echo OCR_ENABLE_AZURE_FORM_RECOGNIZER=false
echo OCR_ENABLE_AWS_TEXTRACT=false
echo OCR_ENABLE_ABBYY=false
echo OCR_ENABLE_CRAFT_TROCR=true
echo OCR_ENABLE_CRAFT=true
echo OCR_ENABLE_TROCR=true
echo.
echo # Google Cloud Vision API
echo GOOGLE_CLOUD_API_KEY=
echo GOOGLE_CLOUD_PROJECT_ID=
echo.
echo # Google Document AI
echo GOOGLE_DOCUMENT_AI_PROJECT_ID=
echo GOOGLE_DOCUMENT_AI_LOCATION=us
echo GOOGLE_DOCUMENT_AI_PROCESSOR_ID=
echo GOOGLE_APPLICATION_CREDENTIALS=
echo.
echo # Azure Computer Vision
echo AZURE_VISION_KEY=
echo AZURE_VISION_ENDPOINT=
echo.
echo # Azure Form Recognizer
echo AZURE_FORM_RECOGNIZER_KEY=
echo AZURE_FORM_RECOGNIZER_ENDPOINT=
echo AZURE_FORM_RECOGNIZER_CUSTOM_MODEL_ID=
echo.
echo # AWS Textract
echo AWS_ACCESS_KEY_ID=
echo AWS_SECRET_ACCESS_KEY=
echo AWS_REGION=us-east-1
echo.
echo # OpenAI GPT-4 Vision
echo OPENAI_API_KEY=
echo OPENAI_VISION_MODEL=gpt-4-vision-preview
echo.
echo # Anthropic Claude Vision
echo ANTHROPIC_API_KEY=
echo CLAUDE_VISION_MODEL=claude-3-5-sonnet-20241022
echo.
echo # Ollama
echo OLLAMA_BASE_URL=http://localhost:11434
echo OLLAMA_VISION_MODEL=llama3.2-vision
echo.
echo # Auth (multi-user, RBAC)
echo AUTH_DISABLED=false
echo JWT_SECRET=change-me-in-production-use-long-random-secret
echo JWT_EXPIRE_MINUTES=10080
echo SEED_ADMIN_PASSWORD=
echo SEED_ADMIN_USERNAME=admin
echo.
echo # File Upload
echo MAX_FILE_SIZE=10485760
echo.
echo # CORS
echo CORS_ORIGINS=http://localhost:5173,http://localhost:8000
echo.
echo # Environment
echo ENVIRONMENT=production
) > .env

echo .env template file created!
echo Please edit .env and add your API keys and configuration.
echo.

:end
pause
