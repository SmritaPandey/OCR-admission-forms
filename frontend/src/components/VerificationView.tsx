import { useState, useEffect, useMemo, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { apiService, FormDetail, FormVerification } from '../services/api';
import { parseOCRText } from '../utils/ocrParser';
import DocumentUpload from './DocumentUpload';
import DocumentList from './DocumentList';
import './VerificationView.css';

const PROVIDER_LABELS: Record<string, string> = {
  tesseract: 'Tesseract (Local)',
  google: 'Google Vision',
  'google-vision': 'Google Vision',
  'google-documentai': 'Google Document AI',
  'azure-vision': 'Azure Vision',
  azure: 'Azure Vision',
  'azure-form-recognizer': 'Azure Form Recognizer',
  'aws-textract': 'AWS Textract',
  abbyy: 'ABBYY FineReader',
  multi: 'Automatic (Best)',
  best: 'Automatic (Best)',
};

const FORM_FIELD_KEYS: (keyof FormVerification)[] = [
  'student_name',
  'date_of_birth',
  'gender',
  'category',
  'nationality',
  'religion',
  'aadhar_number',
  'blood_group',
  'permanent_address',
  'correspondence_address',
  'pincode',
  'city',
  'state',
  'phone_number',
  'alternate_phone',
  'email',
  'emergency_contact_name',
  'emergency_contact_phone',
  'father_name',
  'father_occupation',
  'father_phone',
  'mother_name',
  'mother_occupation',
  'mother_phone',
  'guardian_name',
  'guardian_relation',
  'guardian_phone',
  'annual_income',
  'tenth_board',
  'tenth_year',
  'tenth_percentage',
  'tenth_school',
  'twelfth_board',
  'twelfth_year',
  'twelfth_percentage',
  'twelfth_school',
  'previous_qualification',
  'graduation_details',
  'course_applied',
  'application_number',
  'enrollment_number',
  'admission_date',
];

const normalizeConfidence = (value?: number | null): number | undefined => {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return undefined;
  }
  if (value <= 1) {
    return value * 100;
  }
  return value;
};

const formatConfidenceValue = (value?: number | null): string => {
  const normalized = normalizeConfidence(value);
  return normalized !== undefined ? `${normalized.toFixed(1)}%` : 'n/a';
};

const determineConfidenceClass = (value?: number): { label: string; className: string } => {
  if (value === undefined) {
    return { label: 'Confidence: n/a', className: 'confidence-chip neutral' };
  }
  const formatted = `${formatConfidenceValue(value)}`;
  if (value >= 90) {
    return { label: `Confidence: ${formatted}`, className: 'confidence-chip high' };
  }
  if (value >= 75) {
    return { label: `Confidence: ${formatted}`, className: 'confidence-chip medium' };
  }
  return { label: `Confidence: ${formatted}`, className: 'confidence-chip low' };
};

const formatProviderName = (provider?: string | null): string => {
  if (!provider) {
    return 'Not specified';
  }
  const key = provider.toLowerCase();
  return PROVIDER_LABELS[key] || provider.replace(/[-_]/g, ' ').replace(/\b\w/g, (ch) => ch.toUpperCase());
};

const buildVerificationState = (data: FormDetail): FormVerification => {
  const result: FormVerification = {};
  FORM_FIELD_KEYS.forEach((field) => {
    const value = (data as Record<string, unknown>)[field];
    result[field] = (value ?? '') as string;
  });
  if (data.additional_info) {
    result.additional_info = data.additional_info;
  }
  return result;
};

const mergeIntoVerification = (
  base: FormVerification,
  updates: Record<string, any> | undefined,
  options: { overwrite?: boolean } = {}
): FormVerification => {
  if (!updates) {
    return base;
  }
  const { overwrite = false } = options;
  const next: FormVerification = { ...base };
  Object.entries(updates).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') {
      return;
    }
    const fieldKey = key as keyof FormVerification;
    if (!(fieldKey in next)) {
      return;
    }
    if (fieldKey === 'additional_info') {
      const current = typeof next.additional_info === 'object' && next.additional_info !== null ? next.additional_info : {};
      next.additional_info = { ...current, ...(value as Record<string, any>) };
      return;
    }
    if (overwrite || !next[fieldKey]) {
      next[fieldKey] = value as string;
    }
  });
  return next;
};

function VerificationView() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [form, setForm] = useState<FormDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [verification, setVerification] = useState<FormVerification>({});
  const [initialVerification, setInitialVerification] = useState<FormVerification>({});
  const [reExtractProvider, setReExtractProvider] = useState<string>('');
  const [availableProviders, setAvailableProviders] = useState<string[]>([]);
  const [reExtracting, setReExtracting] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [isPdf, setIsPdf] = useState(false);
  const [showAllPages, setShowAllPages] = useState(false);

  const currentProviderLabel = useMemo(
    () => formatProviderName(form?.extracted_data?.provider || form?.ocr_provider),
    [form?.extracted_data?.provider, form?.ocr_provider]
  );

  const normalizedConfidenceValue = useMemo(
    () => normalizeConfidence(form?.extracted_data?.confidence ?? null),
    [form?.extracted_data?.confidence]
  );

  const confidenceInfo = useMemo(
    () => determineConfidenceClass(normalizedConfidenceValue),
    [normalizedConfidenceValue]
  );

  const pageResults = useMemo(
    () => form?.extracted_data?.page_results || [],
    [form?.extracted_data?.page_results]
  );

  const pagesProcessed = useMemo(() => {
    if (form?.extracted_data?.pages_processed) {
      return form.extracted_data.pages_processed;
    }
    if (pageResults.length > 0) {
      return pageResults.length;
    }
    return form ? 1 : 0;
  }, [form, pageResults]);

  const handleResetVerification = useCallback(() => {
    setVerification(initialVerification);
  }, [initialVerification]);

  const handleApplyParsedData = useCallback(() => {
    if (!form?.extracted_data?.raw_text) {
      return;
    }
    const parsed = parseOCRText(form.extracted_data.raw_text);
    const parsedData: Record<string, any> = { ...parsed };
    if (parsed.address && !parsedData.permanent_address) {
      parsedData.permanent_address = parsed.address;
    }
    setVerification((prev) => mergeIntoVerification(prev, parsedData, { overwrite: false }));
  }, [form?.extracted_data?.raw_text]);

  useEffect(() => {
    if (id) {
      loadForm(parseInt(id));
    }
    loadProviders();
  }, [id]);

  const loadProviders = async () => {
    try {
      const providers = await apiService.getProviders();
      const normalized = providers.providers.map((name) => name.toLowerCase());
      setAvailableProviders(normalized);
      const defaultProvider = (providers.default || normalized[0] || '').toLowerCase();
      setReExtractProvider((current) => {
        const currentNormalized = current ? current.toLowerCase() : '';
        if (currentNormalized && normalized.includes(currentNormalized)) {
          return currentNormalized;
        }
        const adjustedDefault = defaultProvider === 'multi' ? 'best' : defaultProvider;
        if (adjustedDefault && normalized.includes(adjustedDefault)) {
          return adjustedDefault;
        }
        if (normalized.includes('best')) {
          return 'best';
        }
        return normalized[0] || currentNormalized || '';
      });
    } catch (error) {
      console.error('Failed to load providers:', error);
    }
  };

  const loadForm = async (formId: number) => {
    try {
      setLoading(true);
      const data = await apiService.getForm(formId);
      setForm(data);
      const normalizedProvider = data.ocr_provider ? data.ocr_provider.toLowerCase() : '';
      const selection = normalizedProvider === 'multi' ? 'best' : normalizedProvider;
      setReExtractProvider((prev) => selection || prev || '');
      
      // Check if PDF and get page info
      if (data.filename?.toLowerCase().endsWith('.pdf')) {
        setIsPdf(true);
        setCurrentPage(1); // Reset to first page
        try {
          const apiUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
          const response = await fetch(`${apiUrl}/api/preview/${formId}/pages`);
          if (response.ok) {
            const pageInfo = await response.json();
            setTotalPages(pageInfo.total_pages || 1);
            setIsPdf(pageInfo.is_pdf !== false);
          } else {
            // Fallback: assume it's a PDF even if endpoint fails
            setTotalPages(1);
            setIsPdf(true);
          }
        } catch (error) {
          console.error('Failed to get page info:', error);
          // Fallback: assume it's a PDF
          setTotalPages(1);
          setIsPdf(true);
        }
      } else {
        setIsPdf(false);
        setTotalPages(1);
        setShowAllPages(false);
      }
      
      // Pre-fill verification using stored values and optionally overlay OCR extraction
      const baseVerification = buildVerificationState(data);
      let nextVerification = baseVerification;

      if (data.status !== 'verified') {
        if (data.extracted_data?.structured_data) {
          nextVerification = mergeIntoVerification(nextVerification, data.extracted_data.structured_data, { overwrite: true });
        } else if (data.extracted_data?.raw_text) {
          const parsed = parseOCRText(data.extracted_data.raw_text);
          const parsedData: Record<string, any> = { ...parsed };
          if (parsed.address && !parsedData.permanent_address) {
            parsedData.permanent_address = parsed.address;
          }
          nextVerification = mergeIntoVerification(nextVerification, parsedData, { overwrite: false });
        }
      }

      setInitialVerification(nextVerification);
      setVerification(nextVerification);
    } catch (error) {
      console.error('Failed to load form:', error);
      alert('Failed to load form details');
    } finally {
      setLoading(false);
    }
  };

  const handleReExtract = async () => {
    if (!id) return;
    try {
      setReExtracting(true);
      const response = await apiService.reExtractForm(parseInt(id), reExtractProvider || undefined);
      await loadForm(parseInt(id));
      const usedProvider = response.result.provider || reExtractProvider;
      alert(`Re-extraction completed with ${formatProviderName(usedProvider)}`);
    } catch (error: any) {
      alert(`Re-extraction failed: ${error.response?.data?.detail || error.message}`);
    } finally {
      setReExtracting(false);
    }
  };

  const handleSave = async () => {
    if (!id) return;
    try {
      setSaving(true);
      await apiService.verifyForm(parseInt(id), verification);
      alert('Form verified and saved successfully');
      navigate('/');
    } catch (error: any) {
      alert(`Save failed: ${error.response?.data?.detail || error.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleUpdate = async () => {
    if (!id) return;
    try {
      setSaving(true);
      await apiService.updateForm(parseInt(id), verification);
      await loadForm(parseInt(id));
      alert('Form updated successfully');
    } catch (error: any) {
      alert(`Update failed: ${error.response?.data?.detail || error.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!id || !form) return;
    if (!window.confirm(`Are you sure you want to delete "${form.filename}"? This action cannot be undone.`)) {
      return;
    }

    try {
      await apiService.deleteForm(parseInt(id));
      alert('Form deleted successfully');
      navigate('/');
    } catch (error: any) {
      alert(`Delete failed: ${error.response?.data?.detail || error.message}`);
    }
  };

  const handleChange = (field: keyof FormVerification, value: string) => {
    setVerification(prev => ({ ...prev, [field]: value }));
  };

  if (loading) {
    return <div className="loading">Loading form...</div>;
  }

  if (!form) {
    return <div className="error">Form not found</div>;
  }

  return (
    <div className="verification-view">
      <div className="verification-header">
        <h2>Verify Form: {form.filename}</h2>
        <div className="header-actions">
          <button onClick={handleUpdate} className="btn btn-secondary" disabled={saving}>
            {saving ? 'Updating...' : 'Update'}
          </button>
          <button onClick={handleDelete} className="btn btn-danger" disabled={saving}>
            Delete
          </button>
          <button onClick={() => navigate('/')} className="btn btn-secondary">
            Back
          </button>
        </div>
      </div>

      <div className="provider-toolbar">
        <div className="provider-summary">
          <span className="provider-chip">
            Current provider: <strong>{currentProviderLabel}</strong>
          </span>
          <span className={confidenceInfo.className}>{confidenceInfo.label}</span>
          {pagesProcessed ? <span className="summary-pill">Pages: {pagesProcessed}</span> : null}
          {form.extracted_data?.word_count ? (
            <span className="summary-pill">Words: {form.extracted_data.word_count}</span>
          ) : null}
          {form.extracted_data?.psm_mode ? (
            <span className="summary-pill">PSM {form.extracted_data.psm_mode}</span>
          ) : null}
        </div>
        <div className="provider-controls">
          <label htmlFor="provider-select">Switch provider</label>
          <div className="provider-actions">
            <select
              id="provider-select"
              value={reExtractProvider}
              onChange={(e) => setReExtractProvider(e.target.value.toLowerCase())}
              disabled={availableProviders.length === 0}
            >
              {availableProviders.map((provider) => (
                <option key={provider} value={provider}>
                  {formatProviderName(provider)}
                </option>
              ))}
            </select>
            <button
              onClick={handleReExtract}
              className="btn btn-primary"
              disabled={reExtracting || !reExtractProvider}
            >
              {reExtracting ? 'Re-extracting...' : 'Run OCR'}
            </button>
          </div>
        </div>
      </div>

      <div className="verification-content">
        <div className="image-section">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3>Scanned Form</h3>
            {isPdf && totalPages > 1 && (
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                <button
                  onClick={() => setShowAllPages(!showAllPages)}
                  className="btn btn-sm"
                  style={{ 
                    fontSize: '0.85rem', 
                    padding: '0.4rem 0.8rem',
                    backgroundColor: showAllPages ? 'var(--primary-color)' : 'var(--bg-secondary)',
                    color: showAllPages ? 'white' : 'var(--text-primary)',
                    border: '1px solid var(--border-color)'
                  }}
                >
                  {showAllPages ? '📄 Single View' : '📑 View All Pages'}
                </button>
                {showAllPages && (
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                    Showing all {totalPages} pages
                  </span>
                )}
              </div>
            )}
          </div>
          <div className="image-container">
            {isPdf && totalPages > 1 && showAllPages ? (
              // Show all pages in a scrollable grid
              <div className="all-pages-view" style={{ minHeight: '400px' }}>
                {Array.from({ length: totalPages }, (_, i) => i + 1).map((pageNum) => (
                  <div key={pageNum} className="page-preview-item" style={{ marginBottom: '1.5rem' }}>
                    <div className="page-header">
                      <span className="page-number">Page {pageNum} of {totalPages}</span>
                    </div>
                    <img
                      src={`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/preview/${form.id}?page=${pageNum}`}
                      alt={`Scanned form - Page ${pageNum}`}
                      className="page-preview-image"
                      style={{ 
                        width: '100%', 
                        height: 'auto',
                        display: 'block',
                        marginTop: '0.5rem'
                      }}
                      onError={(e) => {
                        console.error(`Failed to load page ${pageNum}:`, e);
                        const apiUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
                        const img = e.target as HTMLImageElement;
                        img.src = `${apiUrl}/uploads/${form.file_path}`;
                      }}
                    />
                  </div>
                ))}
              </div>
            ) : isPdf && totalPages > 1 ? (
              // For multi-page PDFs, show page navigation
              <div>
                <div style={{ marginBottom: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <button
                    onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                    disabled={currentPage === 1}
                    className="btn btn-sm"
                    style={{ fontSize: '0.85rem', padding: '0.4rem 0.8rem' }}
                  >
                    ← Previous
                  </button>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <span style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                      Page {currentPage} of {totalPages}
                    </span>
                    {totalPages > 1 && (
                      <select
                        value={currentPage}
                        onChange={(e) => setCurrentPage(parseInt(e.target.value))}
                        style={{ padding: '0.4rem 0.8rem', borderRadius: '4px', border: '1px solid var(--border-color)' }}
                      >
                        {Array.from({ length: totalPages }, (_, i) => i + 1).map((pageNum) => (
                          <option key={pageNum} value={pageNum}>
                            Page {pageNum}
                          </option>
                        ))}
                      </select>
                    )}
                  </div>
                  <button
                    onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                    disabled={currentPage === totalPages}
                    className="btn btn-sm"
                    style={{ fontSize: '0.85rem', padding: '0.4rem 0.8rem' }}
                  >
                    Next →
                  </button>
                </div>
                <img
                  src={`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/preview/${form.id}?page=${currentPage}`}
                  alt={`Scanned form - Page ${currentPage}`}
                  onError={(e) => {
                    const apiUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
                    const img = e.target as HTMLImageElement;
                    img.src = `${apiUrl}/uploads/${form.file_path}`;
                  }}
                />
              </div>
            ) : form.filename?.toLowerCase().endsWith('.pdf') ? (
              // For single-page PDFs or first load
              <img
                src={`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/preview/${form.id}?page=${currentPage}`}
                alt="Scanned form"
                onError={(e) => {
                  const apiUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
                  const img = e.target as HTMLImageElement;
                  img.src = `${apiUrl}/uploads/${form.file_path}`;
                }}
              />
            ) : (
              // For images, use direct path
              <img
                src={`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/uploads/${form.file_path}`}
                alt="Scanned form"
                onError={(e) => {
                  // Try alternative paths if the first one fails
                  const apiUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
                  const img = e.target as HTMLImageElement;
                  if (!img.src.includes('/uploads/')) {
                    img.src = `${apiUrl}/uploads/${form.file_path}`;
                  } else if (form.file_path) {
                    img.src = `${apiUrl}/${form.file_path}`;
                  } else {
                    // Last resort: try preview endpoint
                    img.src = `${apiUrl}/api/preview/${form.id}`;
                  }
                }}
              />
            )}
          </div>
        </div>

        <div className="data-section">
          <h3>Extracted & Verified Data</h3>
          
          {form.extracted_data && (
            <div className="extracted-text">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                <h4>Extracted Text (Raw)</h4>
                <div className="extraction-actions">
                  {form.extracted_data?.raw_text && (
                    <button
                      onClick={handleApplyParsedData}
                      className="btn btn-sm btn-secondary"
                      style={{ fontSize: '0.8rem', padding: '0.4rem 0.8rem' }}
                    >
                      🔄 Auto-fill Fields
                    </button>
                  )}
                  <button
                    onClick={handleResetVerification}
                    className="btn btn-sm"
                    style={{ fontSize: '0.8rem', padding: '0.4rem 0.8rem' }}
                  >
                    ↩ Reset Changes
                  </button>
                </div>
              </div>
              <div className="raw-text-box">
                {form.extracted_data.raw_text || 'No text extracted'}
              </div>
              {form.extracted_data && (
                <p className="confidence">
                  Confidence: {formatConfidenceValue(form.extracted_data.confidence)}
                </p>
              )}
              {pageResults.length > 1 && (
                <div className="page-confidence-list">
                  {pageResults.map((page) => (
                    <div key={page.page} className="page-confidence-item">
                      <div className="page-confidence-meta">
                        <span className="page-confidence-page">Page {page.page}</span>
                        {page.provider && (
                          <span className="page-confidence-provider">
                            {formatProviderName(page.provider)}
                          </span>
                        )}
                      </div>
                      <span className="page-confidence-value">
                        {formatConfidenceValue(page.confidence)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          <div className="form-editor" style={{ maxHeight: '600px', overflowY: 'auto' }}>
            {/* Basic Details Section */}
            <div className="form-section">
              <h4 className="form-section-title">Basic Details</h4>
              <div className="form-grid">
                <div className="form-row">
                  <label>Student Name *</label>
                  <input type="text" value={verification.student_name || ''} onChange={(e) => handleChange('student_name', e.target.value)} placeholder="Enter student name" />
                </div>
                <div className="form-row">
                  <label>Date of Birth</label>
                  <input type="text" value={verification.date_of_birth || ''} onChange={(e) => handleChange('date_of_birth', e.target.value)} placeholder="DD/MM/YYYY" />
                </div>
                <div className="form-row">
                  <label>Gender</label>
                  <select value={verification.gender || ''} onChange={(e) => handleChange('gender', e.target.value)}>
                    <option value="">Select</option>
                    <option value="MALE">Male</option>
                    <option value="FEMALE">Female</option>
                    <option value="OTHER">Other</option>
                  </select>
                </div>
                <div className="form-row">
                  <label>Category</label>
                  <select value={verification.category || ''} onChange={(e) => handleChange('category', e.target.value)}>
                    <option value="">Select</option>
                    <option value="GENERAL">General</option>
                    <option value="OBC">OBC</option>
                    <option value="SC">SC</option>
                    <option value="ST">ST</option>
                    <option value="OTHER">Other</option>
                  </select>
                </div>
                <div className="form-row">
                  <label>Nationality</label>
                  <input type="text" value={verification.nationality || ''} onChange={(e) => handleChange('nationality', e.target.value)} placeholder="Nationality" />
                </div>
                <div className="form-row">
                  <label>Religion</label>
                  <input type="text" value={verification.religion || ''} onChange={(e) => handleChange('religion', e.target.value)} placeholder="Religion" />
                </div>
                <div className="form-row">
                  <label>Aadhar Number</label>
                  <input type="text" value={verification.aadhar_number || ''} onChange={(e) => handleChange('aadhar_number', e.target.value)} placeholder="Aadhar Number" />
                </div>
                <div className="form-row">
                  <label>Blood Group</label>
                  <select value={verification.blood_group || ''} onChange={(e) => handleChange('blood_group', e.target.value)}>
                    <option value="">Select</option>
                    <option value="A+">A+</option>
                    <option value="A-">A-</option>
                    <option value="B+">B+</option>
                    <option value="B-">B-</option>
                    <option value="AB+">AB+</option>
                    <option value="AB-">AB-</option>
                    <option value="O+">O+</option>
                    <option value="O-">O-</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Address Details Section */}
            <div className="form-section">
              <h4 className="form-section-title">Address Details</h4>
              <div className="form-grid">
                <div className="form-row" style={{ gridColumn: '1 / -1' }}>
                  <label>Permanent Address</label>
                  <textarea value={verification.permanent_address || ''} onChange={(e) => handleChange('permanent_address', e.target.value)} placeholder="Permanent Address" rows={3} />
                </div>
                <div className="form-row" style={{ gridColumn: '1 / -1' }}>
                  <label>Correspondence Address</label>
                  <textarea value={verification.correspondence_address || ''} onChange={(e) => handleChange('correspondence_address', e.target.value)} placeholder="Correspondence Address" rows={3} />
                </div>
                <div className="form-row">
                  <label>City</label>
                  <input type="text" value={verification.city || ''} onChange={(e) => handleChange('city', e.target.value)} placeholder="City" />
                </div>
                <div className="form-row">
                  <label>State</label>
                  <input type="text" value={verification.state || ''} onChange={(e) => handleChange('state', e.target.value)} placeholder="State" />
                </div>
                <div className="form-row">
                  <label>Pincode</label>
                  <input type="text" value={verification.pincode || ''} onChange={(e) => handleChange('pincode', e.target.value)} placeholder="Pincode" />
                </div>
              </div>
            </div>

            {/* Contact Details Section */}
            <div className="form-section">
              <h4 className="form-section-title">Contact Details</h4>
              <div className="form-grid">
                <div className="form-row">
                  <label>Phone Number</label>
                  <input type="text" value={verification.phone_number || ''} onChange={(e) => handleChange('phone_number', e.target.value)} placeholder="Phone Number" />
                </div>
                <div className="form-row">
                  <label>Alternate Phone</label>
                  <input type="text" value={verification.alternate_phone || ''} onChange={(e) => handleChange('alternate_phone', e.target.value)} placeholder="Alternate Phone" />
                </div>
                <div className="form-row">
                  <label>Email</label>
                  <input type="email" value={verification.email || ''} onChange={(e) => handleChange('email', e.target.value)} placeholder="Email" />
                </div>
                <div className="form-row">
                  <label>Emergency Contact Name</label>
                  <input type="text" value={verification.emergency_contact_name || ''} onChange={(e) => handleChange('emergency_contact_name', e.target.value)} placeholder="Emergency Contact Name" />
                </div>
                <div className="form-row">
                  <label>Emergency Contact Phone</label>
                  <input type="text" value={verification.emergency_contact_phone || ''} onChange={(e) => handleChange('emergency_contact_phone', e.target.value)} placeholder="Emergency Contact Phone" />
                </div>
              </div>
            </div>

            {/* Parent/Guardian Details Section */}
            <div className="form-section">
              <h4 className="form-section-title">Parent/Guardian Details</h4>
              <div className="form-grid">
                <div className="form-row">
                  <label>Father Name</label>
                  <input type="text" value={verification.father_name || ''} onChange={(e) => handleChange('father_name', e.target.value)} placeholder="Father Name" />
                </div>
                <div className="form-row">
                  <label>Father Occupation</label>
                  <input type="text" value={verification.father_occupation || ''} onChange={(e) => handleChange('father_occupation', e.target.value)} placeholder="Father Occupation" />
                </div>
                <div className="form-row">
                  <label>Father Phone</label>
                  <input type="text" value={verification.father_phone || ''} onChange={(e) => handleChange('father_phone', e.target.value)} placeholder="Father Phone" />
                </div>
                <div className="form-row">
                  <label>Mother Name</label>
                  <input type="text" value={verification.mother_name || ''} onChange={(e) => handleChange('mother_name', e.target.value)} placeholder="Mother Name" />
                </div>
                <div className="form-row">
                  <label>Mother Occupation</label>
                  <input type="text" value={verification.mother_occupation || ''} onChange={(e) => handleChange('mother_occupation', e.target.value)} placeholder="Mother Occupation" />
                </div>
                <div className="form-row">
                  <label>Mother Phone</label>
                  <input type="text" value={verification.mother_phone || ''} onChange={(e) => handleChange('mother_phone', e.target.value)} placeholder="Mother Phone" />
                </div>
                <div className="form-row">
                  <label>Guardian Name</label>
                  <input type="text" value={verification.guardian_name || ''} onChange={(e) => handleChange('guardian_name', e.target.value)} placeholder="Guardian Name" />
                </div>
                <div className="form-row">
                  <label>Guardian Relation</label>
                  <input type="text" value={verification.guardian_relation || ''} onChange={(e) => handleChange('guardian_relation', e.target.value)} placeholder="Guardian Relation" />
                </div>
                <div className="form-row">
                  <label>Guardian Phone</label>
                  <input type="text" value={verification.guardian_phone || ''} onChange={(e) => handleChange('guardian_phone', e.target.value)} placeholder="Guardian Phone" />
                </div>
                <div className="form-row">
                  <label>Annual Income</label>
                  <input type="text" value={verification.annual_income || ''} onChange={(e) => handleChange('annual_income', e.target.value)} placeholder="Annual Income" />
                </div>
              </div>
            </div>

            {/* Educational Qualifications Section */}
            <div className="form-section">
              <h4 className="form-section-title">Educational Qualifications</h4>
              <div className="form-grid">
                <h5 style={{ gridColumn: '1 / -1', marginTop: '1rem', marginBottom: '0.5rem', fontSize: '0.9rem', color: '#666' }}>10th Standard</h5>
                <div className="form-row">
                  <label>10th Board</label>
                  <input type="text" value={verification.tenth_board || ''} onChange={(e) => handleChange('tenth_board', e.target.value)} placeholder="Board" />
                </div>
                <div className="form-row">
                  <label>10th Year</label>
                  <input type="text" value={verification.tenth_year || ''} onChange={(e) => handleChange('tenth_year', e.target.value)} placeholder="Year" />
                </div>
                <div className="form-row">
                  <label>10th Percentage</label>
                  <input type="text" value={verification.tenth_percentage || ''} onChange={(e) => handleChange('tenth_percentage', e.target.value)} placeholder="%" />
                </div>
                <div className="form-row" style={{ gridColumn: '1 / -1' }}>
                  <label>10th School</label>
                  <input type="text" value={verification.tenth_school || ''} onChange={(e) => handleChange('tenth_school', e.target.value)} placeholder="School Name" />
                </div>
                <h5 style={{ gridColumn: '1 / -1', marginTop: '1rem', marginBottom: '0.5rem', fontSize: '0.9rem', color: '#666' }}>12th Standard</h5>
                <div className="form-row">
                  <label>12th Board</label>
                  <input type="text" value={verification.twelfth_board || ''} onChange={(e) => handleChange('twelfth_board', e.target.value)} placeholder="Board" />
                </div>
                <div className="form-row">
                  <label>12th Year</label>
                  <input type="text" value={verification.twelfth_year || ''} onChange={(e) => handleChange('twelfth_year', e.target.value)} placeholder="Year" />
                </div>
                <div className="form-row">
                  <label>12th Percentage</label>
                  <input type="text" value={verification.twelfth_percentage || ''} onChange={(e) => handleChange('twelfth_percentage', e.target.value)} placeholder="%" />
                </div>
                <div className="form-row" style={{ gridColumn: '1 / -1' }}>
                  <label>12th School</label>
                  <input type="text" value={verification.twelfth_school || ''} onChange={(e) => handleChange('twelfth_school', e.target.value)} placeholder="School Name" />
                </div>
                <div className="form-row" style={{ gridColumn: '1 / -1' }}>
                  <label>Previous Qualification</label>
                  <input type="text" value={verification.previous_qualification || ''} onChange={(e) => handleChange('previous_qualification', e.target.value)} placeholder="Previous Qualification" />
                </div>
                <div className="form-row" style={{ gridColumn: '1 / -1' }}>
                  <label>Graduation Details</label>
                  <textarea value={verification.graduation_details || ''} onChange={(e) => handleChange('graduation_details', e.target.value)} placeholder="Graduation Details" rows={3} />
                </div>
              </div>
            </div>

            {/* Course Application Details Section */}
            <div className="form-section">
              <h4 className="form-section-title">Course Application Details</h4>
              <div className="form-grid">
                <div className="form-row">
                  <label>Course Applied</label>
                  <input type="text" value={verification.course_applied || ''} onChange={(e) => handleChange('course_applied', e.target.value)} placeholder="Course Applied" />
                </div>
                <div className="form-row">
                  <label>Application Number</label>
                  <input type="text" value={verification.application_number || ''} onChange={(e) => handleChange('application_number', e.target.value)} placeholder="Application Number" />
                </div>
                <div className="form-row">
                  <label>Enrollment Number</label>
                  <input type="text" value={verification.enrollment_number || ''} onChange={(e) => handleChange('enrollment_number', e.target.value)} placeholder="Enrollment Number" />
                </div>
                <div className="form-row">
                  <label>Admission Date</label>
                  <input type="text" value={verification.admission_date || ''} onChange={(e) => handleChange('admission_date', e.target.value)} placeholder="DD/MM/YYYY" />
                </div>
              </div>
            </div>
          </div>

          <div className="form-actions">
            <button
              onClick={handleSave}
              disabled={saving || !verification.student_name}
              className="btn btn-primary btn-large"
            >
              {saving ? 'Saving...' : 'Save & Verify'}
            </button>
          </div>
        </div>
      </div>

      {/* Documents Section */}
      {form && (
        <div className="verification-section documents-section">
          <h2>Attached Documents</h2>
          <DocumentUpload
            formId={form.id}
            onUploadComplete={() => {
              loadForm(form.id);
            }}
          />
          <DocumentList
            formId={form.id}
            onRefresh={() => {
              loadForm(form.id);
            }}
          />
        </div>
      )}

    </div>
  );
}

export default VerificationView;

