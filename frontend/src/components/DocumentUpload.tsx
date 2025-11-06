import { useState, useEffect } from 'react';
import { apiService, DocumentCategory } from '../services/api';
import './DocumentUpload.css';

interface DocumentUploadProps {
  formId?: number;
  studentProfileId?: number;
  onUploadComplete?: () => void;
}

function DocumentUpload({ formId, studentProfileId, onUploadComplete }: DocumentUploadProps) {
  const [file, setFile] = useState<File | null>(null);
  const [category, setCategory] = useState<DocumentCategory>('Other');
  const [description, setDescription] = useState('');
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [categories, setCategories] = useState<{ value: string; name: string }[]>([]);

  useState(() => {
    loadCategories();
  });

  const loadCategories = async () => {
    try {
      const result = await apiService.getDocumentCategories();
      setCategories(result.categories);
    } catch (err) {
      console.error('Failed to load categories:', err);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!file) {
      setError('Please select a file');
      return;
    }

    if (!formId && !studentProfileId) {
      setError('Either form ID or student profile ID is required');
      return;
    }

    setUploading(true);
    setError(null);

    try {
      await apiService.uploadDocument(
        file,
        category,
        description || undefined,
        formId,
        studentProfileId
      );
      
      // Reset form
      setFile(null);
      setDescription('');
      setCategory('Other');
      
      if (onUploadComplete) {
        onUploadComplete();
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="document-upload">
      <h3>Upload Document</h3>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="file">Select File</label>
          <input
            type="file"
            id="file"
            accept=".jpg,.jpeg,.png,.pdf,.tiff,.bmp"
            onChange={handleFileChange}
            disabled={uploading}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="category">Document Category</label>
          <select
            id="category"
            value={category}
            onChange={(e) => setCategory(e.target.value as DocumentCategory)}
            disabled={uploading}
            required
          >
            {categories.map((cat) => (
              <option key={cat.value} value={cat.value}>
                {cat.name}
              </option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="description">Description (Optional)</label>
          <textarea
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            disabled={uploading}
            rows={3}
          />
        </div>

        {error && <div className="error-message">{error}</div>}

        <button type="submit" disabled={uploading || !file}>
          {uploading ? 'Uploading...' : 'Upload Document'}
        </button>
      </form>
    </div>
  );
}

export default DocumentUpload;

