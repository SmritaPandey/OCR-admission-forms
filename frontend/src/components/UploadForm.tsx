import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiService } from '../services/api';
import './UploadForm.css';

function UploadForm() {
  const [files, setFiles] = useState<File[]>([]);
  const [ocrProvider, setOcrProvider] = useState<string>('tesseract');
  const [availableProviders, setAvailableProviders] = useState<string[]>([]);
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [filePreviews, setFilePreviews] = useState<{ [key: string]: string }>({});
  const navigate = useNavigate();

  useEffect(() => {
    loadProviders();
  }, []);

  const loadProviders = async () => {
    // Optimization: Skip API call if providers are already loaded
    if (availableProviders && availableProviders.length > 0) {
      return;
    }

    try {
      const providers = await apiService.getProviders();
      if (providers && providers.providers && providers.providers.length > 0) {
        setAvailableProviders(providers.providers);
        setOcrProvider(providers.default || providers.providers[0]);
      } else {
        // Fallback to default providers if API fails
        console.warn('No providers returned from API, using defaults');
        setAvailableProviders(['tesseract']);
        setOcrProvider('tesseract');
      }
    } catch (error) {
      console.error('Failed to load providers:', error);
      // Fallback to default providers on error
      setAvailableProviders(['tesseract']);
      setOcrProvider('tesseract');
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(Array.from(e.dataTransfer.files));
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(Array.from(e.target.files));
    }
  };

  const handleFiles = (newFiles: File[]) => {
    const validFiles = newFiles.filter(file => {
      const ext = file.name.split('.').pop()?.toLowerCase();
      return ['jpg', 'jpeg', 'png', 'pdf', 'tiff', 'bmp'].includes(ext || '');
    });

    setFiles(prev => [...prev, ...validFiles]);

    // Generate previews for image files
    validFiles.forEach(file => {
      if (file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = (e) => {
          if (e.target?.result) {
            setFilePreviews(prev => ({
              ...prev,
              [file.name]: e.target!.result as string
            }));
          }
        };
        reader.readAsDataURL(file);
      }
    });
  };

  const removeFile = (fileName: string) => {
    setFiles(prev => prev.filter(f => f.name !== fileName));
    setFilePreviews(prev => {
      const newPreviews = { ...prev };
      delete newPreviews[fileName];
      return newPreviews;
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (files.length === 0) return;

    try {
      setUploading(true);
      // Upload files sequentially to avoid overwhelming the server
      const uploadPromises = files.map(file =>
        apiService.uploadForm(file, ocrProvider)
      );

      const results = await Promise.all(uploadPromises);

      // Navigate to the last uploaded form
      if (results.length > 0) {
        navigate(`/forms/${results[results.length - 1].id}`);
      }
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail ||
        error.message ||
        'Network error. Please check your connection and try again.';
      console.error('Upload error:', error);
      alert(`Upload failed: ${errorMessage}`);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="upload-form">
      <div className="upload-header">
        <div className="upload-heading">
          <span className="page-eyebrow">Document Intake</span>
          <h2>Upload Admission Form</h2>
          <p>
            Submit scanned admission forms and supporting paperwork to route them into the admissions
            review workflow. You can import multiple files at once using drag &amp; drop.
          </p>
        </div>
        <ul className="upload-guidelines">
          <li>Use high-resolution scans (300&nbsp;DPI recommended) for handwritten content.</li>
          <li>Merge multi-page documents into a single PDF before uploading.</li>
          <li>Ensure each file remains under 10&nbsp;MB to preserve processing speed.</li>
        </ul>
      </div>

      <form onSubmit={handleSubmit} className="upload-container">
        <div
          className={`file-dropzone ${dragActive ? 'drag-active' : ''}`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <input
            type="file"
            id="file-input"
            accept="image/*,.pdf"
            onChange={handleFileChange}
            className="file-input"
            multiple
          />
          <label htmlFor="file-input" className="file-label">
            <div className="dropzone-graphic" aria-hidden="true">
              <span className="dropzone-icon">⬆︎</span>
              <span className="dropzone-pulse" />
            </div>
            <div className="dropzone-copy">
              <p className="dropzone-text">
                Drag &amp; drop scanned forms here or click to browse your computer.
              </p>
              <p className="dropzone-hint">
                Supports: JPG, PNG, PDF, TIFF, BMP · Multiple files allowed
              </p>
              <button
                type="button"
                className="btn btn-secondary file-trigger"
                onClick={(e) => {
                  e.preventDefault();
                  document.getElementById('file-input')?.click();
                }}
              >
                Select Files
              </button>
            </div>
          </label>
        </div>

        {files.length > 0 && (
          <div className="file-list">
            <div className="file-list-header">
              <h4>Selected Files</h4>
              <span className="file-count">{files.length} file(s)</span>
            </div>
            {files.map((file) => (
              <div key={file.name} className="file-item">
                {filePreviews[file.name] ? (
                  <img
                    src={filePreviews[file.name]}
                    alt={file.name}
                    className="file-preview"
                  />
                ) : (
                  <div className="file-preview file-preview-placeholder" aria-hidden="true">
                    <span>📄</span>
                    <span>{file.name.split('.').pop()?.toUpperCase()}</span>
                  </div>
                )}
                <div className="file-info">
                  <p className="file-name">{file.name}</p>
                  <p className="file-size">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                </div>
                <button
                  type="button"
                  className="btn-remove"
                  onClick={() => removeFile(file.name)}
                  aria-label={`Remove ${file.name}`}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="form-group">
          <label htmlFor="ocr-provider">OCR Provider</label>
          {availableProviders.length > 0 ? (
            <select
              id="ocr-provider"
              value={ocrProvider}
              onChange={(e) => setOcrProvider(e.target.value)}
              className="form-select"
            >
              {availableProviders.map((provider) => {
                // Format provider names for display
                const providerLabels: Record<string, string> = {
                  'tesseract': 'Tesseract (Local)',
                  'google-vision': 'Google Vision',
                  'google': 'Google Vision',
                  'google-documentai': 'Google Document AI',
                  'azure-vision': 'Azure Vision',
                  'azure': 'Azure Vision',
                  'azure-form-recognizer': 'Azure Form Recognizer',
                  'aws-textract': 'AWS Textract',
                  'craft-trocr': 'CRAFT + TR-OCR (Handwritten) ⭐',
                  'craft': 'CRAFT (Text Detection Only)',
                  'trocr': 'TR-OCR (Text Recognition Only)',
                  'best': 'Automatic (Best)',
                  'multi': 'Automatic (Best)'
                };

                const label = providerLabels[provider.toLowerCase()] ||
                  provider.charAt(0).toUpperCase() + provider.slice(1).replace(/-/g, ' ');

                return (
                  <option key={provider} value={provider}>
                    {label}
                  </option>
                );
              })}
            </select>
          ) : (
            <div className="form-select" style={{ padding: '0.9rem 1rem', background: '#f5f5f5', color: '#666' }}>
              Loading providers...
            </div>
          )}
          <small className="form-hint">
            Select the OCR provider to use for text extraction.
          </small>
        </div>

        <button
          type="submit"
          disabled={files.length === 0 || uploading}
          className="btn btn-primary btn-large"
        >
          {uploading ? `Uploading ${files.length} file(s)...` : `Upload & Extract ${files.length} file(s)`}
        </button>

        <p className="upload-footer-hint">
          Need to capture new documents? Schedule a scan session with the admissions desk to keep
          your intake queue current.
        </p>
      </form>
    </div>
  );
}

export default UploadForm;

