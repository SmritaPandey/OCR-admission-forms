import { useState, useEffect } from 'react';
import { apiService, Document } from '../services/api';
import './DocumentList.css';

interface DocumentListProps {
  formId?: number;
  studentProfileId?: number;
  onRefresh?: () => void;
}

function DocumentList({ formId, studentProfileId, onRefresh }: DocumentListProps) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDocuments();
  }, [formId, studentProfileId]);

  const loadDocuments = async () => {
    setLoading(true);
    setError(null);
    
    try {
      let docs: Document[] = [];
      
      if (formId) {
        docs = await apiService.getFormDocuments(formId);
      } else if (studentProfileId) {
        docs = await apiService.getStudentDocuments(studentProfileId);
      } else {
        setError('Either form ID or student profile ID is required');
        setLoading(false);
        return;
      }
      
      setDocuments(docs);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to load documents');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (documentId: number) => {
    if (!confirm('Are you sure you want to delete this document?')) {
      return;
    }

    try {
      await apiService.deleteDocument(documentId);
      loadDocuments();
      if (onRefresh) {
        onRefresh();
      }
    } catch (err: any) {
      alert(err.response?.data?.detail || err.message || 'Failed to delete document');
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
  };

  const getDocumentUrl = (filePath: string): string => {
    const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
    return `${baseUrl}/uploads/${filePath}`;
  };

  if (loading) {
    return <div className="document-list loading">Loading documents...</div>;
  }

  if (error) {
    return <div className="document-list error">{error}</div>;
  }

  if (documents.length === 0) {
    return <div className="document-list empty">No documents attached</div>;
  }

  return (
    <div className="document-list">
      <h3>Attached Documents ({documents.length})</h3>
      <div className="documents-grid">
        {documents.map((doc) => (
          <div key={doc.id} className="document-card">
            <div className="document-header">
              <span className="document-category">{doc.document_category}</span>
              <button
                className="delete-btn"
                onClick={() => handleDelete(doc.id)}
                title="Delete document"
              >
                ×
              </button>
            </div>
            <div className="document-body">
              <div className="document-name">{doc.filename}</div>
              {doc.description && (
                <div className="document-description">{doc.description}</div>
              )}
              <div className="document-meta">
                <span>{formatFileSize(doc.file_size)}</span>
                <span>{new Date(doc.upload_date).toLocaleDateString()}</span>
              </div>
            </div>
            <div className="document-actions">
              <a
                href={getDocumentUrl(doc.file_path)}
                target="_blank"
                rel="noopener noreferrer"
                className="view-btn"
              >
                View
              </a>
              <a
                href={getDocumentUrl(doc.file_path)}
                download={doc.filename}
                className="download-btn"
              >
                Download
              </a>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default DocumentList;

