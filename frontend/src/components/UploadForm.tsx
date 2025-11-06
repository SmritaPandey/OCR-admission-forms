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
  const [filePreviews, setFilePreviews] = useState<{[key: string]: string}>({});
  const navigate = useNavigate();

  useEffect(() => {
    loadProviders();
  }, []);

  const loadProviders = async () => {
    try {
      const providers = await apiService.getProviders();
      setAvailableProviders(providers.providers);
      if (providers.providers.length > 0) {
        setOcrProvider(providers.default || providers.providers[0]);
      }
    } catch (error) {
      console.error('Failed to load providers:', error);
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
      alert(`Upload failed: ${error.response?.data?.detail || error.message}`);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="upload-form">
      <h2>Upload Admission Form</h2>
      
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
            <div>
              <p className="dropzone-text">
                Drag and drop your scanned forms here, or click to browse
              </p>
              <p className="dropzone-hint">
                Supports: JPG, PNG, PDF, TIFF, BMP (Multiple files allowed)
              </p>
              <button
                type="button"
                className="btn btn-secondary"
                style={{ marginTop: '1rem' }}
                onClick={(e) => {
                  e.preventDefault();
                  document.getElementById('file-input')?.click();
                }}
              >
                Choose Files
              </button>
            </div>
          </label>
        </div>

        {files.length > 0 && (
          <div className="file-list">
            <h4>Selected Files ({files.length}):</h4>
            {files.map((file) => (
              <div key={file.name} className="file-item">
                {filePreviews[file.name] ? (
                  <img
                    src={filePreviews[file.name]}
                    alt={file.name}
                    className="file-preview"
                  />
                ) : (
                  <div className="file-preview file-preview-placeholder">
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
          <select
            id="ocr-provider"
            value={ocrProvider}
            onChange={(e) => setOcrProvider(e.target.value)}
            className="form-select"
          >
            {availableProviders.map((provider) => (
              <option key={provider} value={provider}>
                {provider.charAt(0).toUpperCase() + provider.slice(1)}
              </option>
            ))}
          </select>
          <small className="form-hint">
            Select the OCR provider to use for text extraction
          </small>
        </div>

        <button
          type="submit"
          disabled={files.length === 0 || uploading}
          className="btn btn-primary btn-large"
        >
          {uploading ? `Uploading ${files.length} file(s)...` : `Upload & Extract ${files.length} file(s)`}
        </button>
      </form>
    </div>
  );
}

export default UploadForm;

