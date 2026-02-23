import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { apiService } from '../services/api';
import { useBatchUpload } from '../contexts/BatchUploadContext';
import './BatchUpload.css';

interface BatchJob {
  job_id: string;
  status: string;
  total_items: number;
  processed_items: number;
  successful_items: number;
  failed_items: number;
  progress_percentage: number;
  created_at: string;
  started_at?: string;
  completed_at?: string;
}

function BatchUpload() {
  const [files, setFiles] = useState<File[]>([]);
  const [ocrProvider, setOcrProvider] = useState<string>('craft-trocr');
  const [availableProviders, setAvailableProviders] = useState<string[]>([]);
  const [pagesPerForm, setPagesPerForm] = useState<number>(4); // First 4 pages = form
  const [uploading, setUploading] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const [jobResults, setJobResults] = useState<any[]>([]);

  // Use global batch upload context
  const { currentJob, startJob, cancelJob } = useBatchUpload();

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
      setAvailableProviders(providers.providers);
      if (providers.providers.length > 0) {
        setOcrProvider(providers.default || providers.providers[0]);
      }
    } catch (error) {
      console.error('Failed to load providers:', error);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const selectedFiles = Array.from(e.target.files);
      // Filter to only PDFs
      const pdfFiles = selectedFiles.filter(file => file.type === 'application/pdf' || file.name.endsWith('.pdf'));
      setFiles(prev => [...prev, ...pdfFiles]);
    }
  };

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleUpload = async () => {
    if (files.length === 0) {
      alert('Please select at least one PDF file');
      return;
    }

    setUploading(true);
    try {
      const result = await apiService.batchUploadForms(files, ocrProvider, pagesPerForm);

      // Start the global job tracking
      startJob({
        job_id: result.job_id,
        status: 'processing',
        total_items: result.total_files,
        processed_items: 0,
        successful_items: 0,
        failed_items: 0,
        progress_percentage: 0,
        created_at: new Date().toISOString(),
      });

      // Clear the file list after successful upload start
      setFiles([]);
    } catch (error: any) {
      console.error('Batch upload failed:', error);
      alert(`Upload failed: ${error.message || 'Unknown error'}`);
    } finally {
      setUploading(false);
    }
  };

  const handleCancel = async () => {
    await cancelJob();
  };

  return (
    <div className="batch-upload">
      <h2>Batch Upload Forms</h2>
      <p className="description">
        Upload multiple PDF forms at once. First {pagesPerForm} pages will be processed as admission form, remaining pages will be saved as attached documents.
        Perfect for processing large volumes of admission forms.
      </p>

      <div className="upload-section">
        <div className="form-group">
          <label>Form Pages (first N pages):</label>
          <input
            type="number"
            min="1"
            max="10"
            value={pagesPerForm}
            onChange={(e) => setPagesPerForm(parseInt(e.target.value) || 4)}
          />
          <small style={{ display: 'block', marginTop: '0.25rem', color: '#666' }}>
            First {pagesPerForm} pages will be processed as admission form. Remaining pages will be saved as documents.
          </small>
        </div>

        <div className="form-group">
          <label>OCR Provider:</label>
          <select value={ocrProvider} onChange={(e) => setOcrProvider(e.target.value)}>
            {availableProviders.map((provider) => {
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
                'multi': 'Automatic (Best)',
                'gpt4-vision': 'GPT-4 Vision (AI)',
                'claude-vision': 'Claude Vision (AI)',
                'ollama': 'Ollama (Local AI)'
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
        </div>

        <div className="file-input-section">
          <label>Select PDF Files:</label>
          <input
            type="file"
            multiple
            accept=".pdf"
            onChange={handleFileSelect}
            disabled={uploading}
          />
        </div>

        {files.length > 0 && (
          <div className="files-list">
            <h3>Selected Files ({files.length})</h3>
            <ul>
              {files.map((file, index) => (
                <li key={index}>
                  <span>{file.name}</span>
                  <span className="file-size">({(file.size / 1024 / 1024).toFixed(2)} MB)</span>
                  <button onClick={() => removeFile(index)} disabled={uploading}>Remove</button>
                </li>
              ))}
            </ul>
          </div>
        )}

        <button
          className="upload-button"
          onClick={handleUpload}
          disabled={uploading || files.length === 0}
        >
          {uploading ? 'Uploading...' : `Upload ${files.length} Form(s)`}
        </button>
      </div>

      {currentJob && (
        <div className="job-status">
          <h3>Job Status: <span className="mono-text">{currentJob.job_id}</span></h3>
          <div className="status-info">
            <div className="status-item">
              <span>Status:</span>
              <span className={`status-badge status-${currentJob.status}`}>
                {currentJob.status}
              </span>
            </div>
            <div className="status-item">
              <span>Progress:</span>
              <span>{(currentJob.progress_percentage || 0).toFixed(1)}%</span>
            </div>
            <div className="status-item">
              <span>Processed:</span>
              <span>{currentJob.processed_items} / {currentJob.total_items}</span>
            </div>
            <div className="status-item">
              <span>Successful:</span>
              <span className="success">{currentJob.successful_items}</span>
            </div>
            <div className="status-item">
              <span>Failed:</span>
              <span className="error">{currentJob.failed_items}</span>
            </div>
          </div>

          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{ width: `${currentJob.progress_percentage || 0}%` }}
            />
          </div>

          {currentJob.status === 'processing' && (
            <button className="cancel-button" onClick={handleCancel}>
              Cancel Job
            </button>
          )}

          {currentJob.status === 'completed' && (
            <button
              className="view-results-button"
              onClick={async () => {
                try {
                  const resultsResponse = await apiService.getBatchJobResults(currentJob.job_id, 1, 100);
                  console.log('Job results:', resultsResponse);
                  if (resultsResponse && resultsResponse.results && resultsResponse.results.length > 0) {
                    setJobResults(resultsResponse.results);
                    setShowResults(true);
                  } else if (resultsResponse && resultsResponse.total_results === 0) {
                    alert('No results found for this job.');
                  } else {
                    // Try to get results from status endpoint
                    const statusResponse = await apiService.getBatchJobStatus(currentJob.job_id);
                    if (statusResponse && statusResponse.results && statusResponse.results.length > 0) {
                      setJobResults(statusResponse.results);
                      setShowResults(true);
                    } else {
                      alert('No results found for this job.');
                    }
                  }
                } catch (error: any) {
                  console.error('Failed to get results:', error);
                  alert(`Failed to fetch results: ${error.response?.data?.detail || error.message || 'Unknown error'}`);
                }
              }}
            >
              View Results
            </button>
          )}

          {showResults && (
            <div className="results-modal-overlay">
              <div className="results-modal">
                <div className="results-header">
                  <h3>Batch Processing Results</h3>
                  <button className="close-button" onClick={() => setShowResults(false)}>×</button>
                </div>
                <div className="results-content">
                  <table className="results-table">
                    <thead>
                      <tr>
                        <th>Filename</th>
                        <th>Status</th>
                        <th>Confidence</th>
                        <th>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {jobResults.length > 0 ? (
                        jobResults.map((result: any, index: number) => (
                          <tr key={index}>
                            <td>{result.filename}</td>
                            <td>
                              <span className={`status-badge status-${result.status === 'success' ? 'verified' : 'error'}`}>
                                {result.status}
                              </span>
                            </td>
                            <td>{result.confidence ? `${(result.confidence * 100).toFixed(1)}%` : '-'}</td>
                            <td>
                              {result.form_id ? (
                                <Link to={`/forms/${result.form_id}`} target="_blank" rel="noopener noreferrer" className="view-link">
                                  View Form
                                </Link>
                              ) : (
                                <span className="text-muted">-</span>
                              )}
                            </td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan={4} className="text-center">No results available</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
                <div className="results-footer">
                  <button className="btn btn-primary" onClick={() => setShowResults(false)}>Close</button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default BatchUpload;

