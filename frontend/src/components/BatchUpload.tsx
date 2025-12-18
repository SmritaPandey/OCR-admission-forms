import { useState, useEffect } from 'react';
import { apiService } from '../services/api';
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
  const [ocrProvider, setOcrProvider] = useState<string>('tesseract');
  const [availableProviders, setAvailableProviders] = useState<string[]>([]);
  const [pagesPerForm, setPagesPerForm] = useState<number>(3);
  const [uploading, setUploading] = useState(false);
  const [currentJob, setCurrentJob] = useState<BatchJob | null>(null);
  const [jobStatusInterval, setJobStatusInterval] = useState<NodeJS.Timeout | null>(null);

  useEffect(() => {
    loadProviders();
    return () => {
      if (jobStatusInterval) {
        clearInterval(jobStatusInterval);
      }
    };
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
      setCurrentJob({
        job_id: result.job_id,
        status: 'processing',
        total_items: result.total_files,
        processed_items: 0,
        successful_items: 0,
        failed_items: 0,
        progress_percentage: 0,
        created_at: new Date().toISOString(),
      });

      // Start polling for job status
      startJobStatusPolling(result.job_id);
    } catch (error: any) {
      console.error('Batch upload failed:', error);
      alert(`Upload failed: ${error.message || 'Unknown error'}`);
    } finally {
      setUploading(false);
    }
  };

  const startJobStatusPolling = (jobId: string) => {
    const interval = setInterval(async () => {
      try {
        const status = await apiService.getBatchJobStatus(jobId);
        setCurrentJob(status);

        if (status.status === 'completed' || status.status === 'failed' || status.status === 'cancelled') {
          clearInterval(interval);
          setJobStatusInterval(null);
        }
      } catch (error) {
        console.error('Failed to get job status:', error);
        clearInterval(interval);
        setJobStatusInterval(null);
      }
    }, 2000); // Poll every 2 seconds

    setJobStatusInterval(interval);
  };

  const handleCancel = async () => {
    if (currentJob && currentJob.status === 'processing') {
      try {
        await apiService.cancelBatchJob(currentJob.job_id);
        if (jobStatusInterval) {
          clearInterval(jobStatusInterval);
          setJobStatusInterval(null);
        }
        setCurrentJob(prev => prev ? { ...prev, status: 'cancelled' } : null);
      } catch (error) {
        console.error('Failed to cancel job:', error);
      }
    }
  };

  return (
    <div className="batch-upload">
      <h2>Batch Upload Forms</h2>
      <p className="description">
        Upload multiple PDF forms at once. Each form should be a PDF with {pagesPerForm} pages.
        Perfect for processing large volumes of admission forms.
      </p>

      <div className="upload-section">
        <div className="form-group">
          <label>Pages per Form:</label>
          <input
            type="number"
            min="1"
            max="10"
            value={pagesPerForm}
            onChange={(e) => setPagesPerForm(parseInt(e.target.value) || 3)}
          />
        </div>

        <div className="form-group">
          <label>OCR Provider:</label>
          <select value={ocrProvider} onChange={(e) => setOcrProvider(e.target.value)}>
            <option value="tesseract">Tesseract (Default)</option>
            {availableProviders.map(provider => (
              <option key={provider} value={provider}>
                {provider.charAt(0).toUpperCase() + provider.slice(1)}
              </option>
            ))}
            <option value="gpt4-vision">GPT-4 Vision (AI)</option>
            <option value="claude-vision">Claude Vision (AI)</option>
            <option value="ollama">Ollama (Local AI)</option>
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
          <h3>Job Status: {currentJob.job_id}</h3>
          <div className="status-info">
            <div className="status-item">
              <span>Status:</span>
              <span className={`status-badge status-${currentJob.status}`}>
                {currentJob.status}
              </span>
            </div>
            <div className="status-item">
              <span>Progress:</span>
              <span>{currentJob.progress_percentage.toFixed(1)}%</span>
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
              style={{ width: `${currentJob.progress_percentage}%` }}
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
                  const results = await apiService.getBatchJobResults(currentJob.job_id);
                  console.log('Job results:', results);
                  alert(`Job completed! ${results.total_results} results available. Check console for details.`);
                } catch (error) {
                  console.error('Failed to get results:', error);
                }
              }}
            >
              View Results
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export default BatchUpload;

