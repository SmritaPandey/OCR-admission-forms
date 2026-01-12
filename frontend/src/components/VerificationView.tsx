import { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { apiService, FormDetail, FormVerification } from '../services/api';
import { parseOCRText } from '../utils/ocrParser';
import { extractStructuredData } from '../utils/structuredDataParser';
import DocumentUpload from './DocumentUpload';
import DocumentList from './DocumentList';
import './VerificationView.css';

// Component for rendering a single PDF page - Adobe-style viewer
const PDFPageImage = ({ formId, pageNum, filePath, zoomLevel, fitZoomLevel, onImageLoad, API_BASE_URL, getFileUrl }: {
  formId: number;
  pageNum: number;
  filePath?: string;
  zoomLevel: number | null;
  fitZoomLevel: number;
  onImageLoad?: (width: number, height: number) => void;
  API_BASE_URL: string;
  getFileUrl: (path: string | undefined, id?: number, page?: number) => string;
}) => {
  const [imageError, setImageError] = useState(false);
  const [imageLoading, setImageLoading] = useState(true);
  const [naturalWidth, setNaturalWidth] = useState<number | null>(null);
  const [naturalHeight, setNaturalHeight] = useState<number | null>(null);
  
  const previewUrl = `${API_BASE_URL}/api/preview/${formId}?page=${pageNum}`;
  const fallbackUrl = filePath ? getFileUrl(filePath, formId, pageNum) : previewUrl;
  
  // Calculate actual zoom: zoomLevel is relative to fitZoomLevel (1.0 = 100% = fit-to-window)
  const effectiveZoom = (zoomLevel ?? 1.0) * fitZoomLevel;
  
  // Calculate actual scaled dimensions
  const displayWidth = naturalWidth ? naturalWidth * effectiveZoom : null;
  const displayHeight = naturalHeight ? naturalHeight * effectiveZoom : null;
  
  return (
    <div className="page-wrapper" style={{ 
      marginBottom: '30px', 
      position: 'relative',
      display: 'inline-block',
      boxSizing: 'content-box',
      // Container expands to fit scaled image
      width: displayWidth ? `${displayWidth}px` : 'auto',
      height: displayHeight ? `${displayHeight}px` : 'auto'
    }}>
      <div className="page-label" style={{ 
        position: 'absolute', 
        top: '10px', 
        left: '10px', 
        background: 'rgba(51, 65, 85, 0.9)', 
        color: 'white', 
        padding: '6px 12px', 
        borderRadius: '4px',
        fontSize: '12px',
        fontWeight: 600,
        boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
        zIndex: 10,
        pointerEvents: 'none'
      }}>
        Page {pageNum}
      </div>
      
      {imageLoading && (
        <div style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          color: '#e5e7eb',
          fontSize: '14px',
          zIndex: 5
        }}>
          Loading page {pageNum}...
        </div>
      )}
      
      {imageError ? (
        <div style={{
          padding: '2rem',
          textAlign: 'center',
          color: '#ef4444',
          fontSize: '14px',
          background: 'rgba(239, 68, 68, 0.1)',
          borderRadius: '4px'
        }}>
          Failed to load page {pageNum}. 
          <br />
          <a 
            href={fallbackUrl} 
            target="_blank" 
            rel="noopener noreferrer"
            style={{ color: '#60a5fa', textDecoration: 'underline', marginTop: '0.5rem', display: 'inline-block' }}
          >
            Open PDF directly
          </a>
        </div>
      ) : (
        <img
          src={previewUrl}
          alt={`Scanned form page ${pageNum}`}
          style={{ 
            display: imageLoading ? 'none' : 'block', 
            width: displayWidth ? `${displayWidth}px` : 'auto',
            height: displayHeight ? `${displayHeight}px` : 'auto',
            borderRadius: '2px', 
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.4)',
            background: 'white',
            transition: 'width 0.2s ease-out, height 0.2s ease-out',
            imageRendering: 'auto',
            // Ensure image doesn't get clipped - use actual dimensions
            maxWidth: 'none',
            maxHeight: 'none',
            objectFit: 'contain',
            margin: '0'
          }}
          onLoad={(e) => {
            const img = e.target as HTMLImageElement;
            setImageLoading(false);
            setImageError(false);
            setNaturalWidth(img.naturalWidth);
            setNaturalHeight(img.naturalHeight);
            // Notify parent to calculate fit zoom
            if (onImageLoad) {
              onImageLoad(img.naturalWidth, img.naturalHeight);
            }
          }}
          onError={(e) => {
            const img = e.target as HTMLImageElement;
            setImageLoading(false);
            
            // Try fallback URL if preview failed and we haven't tried it yet
            if (fallbackUrl && img.src === previewUrl && img.src !== fallbackUrl) {
              // Retry with fallback URL
              img.src = fallbackUrl;
            } else {
              // Both URLs failed
              setImageError(true);
            }
          }}
        />
      )}
    </div>
  );
};

// API Base URL - handle TypeScript import.meta.env
const API_BASE_URL = (typeof import.meta !== 'undefined' && (import.meta as any).env?.VITE_API_BASE_URL) || 'http://localhost:8000';

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
  'craft-trocr': 'CRAFT + TrOCR',
  'craft': 'CRAFT (Detection Only)',
  'trocr': 'TrOCR (Recognition Only)',
  'combined': 'Tesseract + Google Combined',
  'tesseract-google-combined': 'Tesseract + Google Combined',
  'ollama': 'Ollama (Local)',
  multi: 'Automatic (Best)',
  best: 'Automatic (Best)',
};

const FORM_FIELD_KEYS: (keyof FormVerification)[] = [
  // Academic & Admission Details
  'academic_session',
  'course',
  'admission_category',
  'admission_category_other',
  'du_portal_form_number',
  'cuet_score',
  'college_roll_no',
  'date_of_admission',
  // Personal Details
  'student_name',
  'first_name',
  'middle_name',
  'surname',
  'date_of_birth',
  'gender',
  'category',
  'nationality',
  'religion',
  'aadhar_number',
  'blood_group',
  'below_poverty_line',
  'minority_category',
  // Address Details
  'permanent_address',
  'permanent_address_line1',
  'permanent_address_line2',
  'permanent_address_line3',
  'permanent_state',
  'permanent_pincode',
  'correspondence_address',
  'correspondence_address_line1',
  'correspondence_address_line2',
  'correspondence_address_line3',
  'correspondence_state',
  'correspondence_pincode',
  'pincode',
  'city',
  'state',
  // Contact Details
  'phone_number',
  'alternate_phone',
  'email',
  'emergency_contact_name',
  'emergency_contact_phone',
  // Parent Names
  'father_name',
  'mother_name',
  // CUET Marks
  'cuet_subject_1',
  'cuet_total_score_1',
  'cuet_score_obtained_1',
  'cuet_subject_2',
  'cuet_total_score_2',
  'cuet_score_obtained_2',
  'cuet_subject_3',
  'cuet_total_score_3',
  'cuet_score_obtained_3',
  'cuet_subject_4',
  'cuet_total_score_4',
  'cuet_score_obtained_4',
  'cuet_subject_5',
  'cuet_total_score_5',
  'cuet_score_obtained_5',
  'cuet_subject_6',
  'cuet_total_score_6',
  'cuet_score_obtained_6',
  'cuet_total_score',
  // Qualifying Examination
  'twelfth_year',
  'twelfth_board',
  'twelfth_roll_number',
  'twelfth_institution',
  'hindi_studied_upto',
  // Personal Information
  'annual_income',
  // Mother's Occupational Details
  'mother_occupation',
  'mother_designation',
  'mother_organization',
  'mother_email',
  'mother_mobile',
  'mother_landline_code',
  'mother_landline',
  'mother_phone',
  // Father's Occupational Details
  'father_occupation',
  'father_designation',
  'father_organization',
  'father_email',
  'father_mobile',
  'father_landline_code',
  'father_landline',
  'father_phone',
  // Local Guardian's Details
  'guardian_name',
  'guardian_residential_address',
  'guardian_organization',
  'guardian_email',
  'guardian_mobile',
  'guardian_landline_code',
  'guardian_landline',
  'guardian_phone',
  'guardian_relation',
  // Other Information
  'du_enrollment_number',
  'hindi_medium_preference',
  // Category Certificate
  'category_certificate_authority',
  'category_certificate_number',
  'category_certificate_date',
  'disability_percentage',
  'disability_type',
  'udid_number',
  // Legacy/Backward Compatibility
  'course_applied',
  'application_number',
  'enrollment_number',
  'admission_date',
  'tenth_board',
  'tenth_year',
  'tenth_percentage',
  'tenth_school',
  'twelfth_percentage',
  'twelfth_school',
  'previous_qualification',
  'graduation_details',
  // Document Checklist (Page 4)
  'doc_admission_form',
  'doc_undertaking_ragging',
  'doc_photographs',
  'doc_cuet_scorecard',
  'doc_class_xii_marksheet',
  'doc_class_x_certificate',
  'doc_class_xii_certificate',
  'doc_character_certificate',
  'doc_transfer_certificate',
  'doc_hindi_certificate',
  'doc_caste_certificate',
  'doc_sports_eca',
  'doc_originals',
  'doc_photo_id',
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

// Helper to get the correct file URL
const getFileUrl = (filePath: string | undefined, formId?: number, page?: number): string => {
  if (!filePath) {
    // Fallback to preview endpoint if no file path
    return formId ? `${API_BASE_URL}/api/preview/${formId}${page ? `?page=${page}` : ''}` : '';
  }
  
  // Normalize the file path - remove any leading 'uploads/' to avoid duplication
  let normalizedPath = filePath;
  if (normalizedPath.startsWith('uploads/')) {
    normalizedPath = normalizedPath.substring(8);
  }
  if (normalizedPath.startsWith('/uploads/')) {
    normalizedPath = normalizedPath.substring(9);
  }
  if (normalizedPath.startsWith('/')) {
    normalizedPath = normalizedPath.substring(1);
  }
  
  // Return the direct PDF URL - browser will handle page navigation via #page= anchor
  return `${API_BASE_URL}/uploads/${normalizedPath}`;
};

const formatProviderName = (provider?: string | null, modelInfo?: Record<string, any>): string => {
  if (!provider) return 'Unknown';
  
  // Clean up the provider string (remove any "trained-" prefixes from backend)
  let cleanProvider = provider.replace(/^trained-/, '');
  
  // Use known label or format the string
  let label = PROVIDER_LABELS[cleanProvider] || 
    cleanProvider.split(/[-_]/).map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');

  // Add "Trained" badge if applicable
  if (modelInfo && modelInfo[cleanProvider]?.is_finetuned) {
    label = label + ' ⭐ (Trained)';
  } else if (provider.startsWith('trained-')) {
    // Fallback if modelInfo not available but provider name indicates training
    if (cleanProvider === 'trocr') {
      label = 'TrOCR (Fine-tuned) ⭐';
    } else {
      label = label + ' ⭐ (Trained)';
    }
  }
  
  return label;
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
  const [verification, setVerification] = useState<FormVerification>({});
  const [initialVerification, setInitialVerification] = useState<FormVerification>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [reExtracting, setReExtracting] = useState(false);
  const [reExtractProvider, setReExtractProvider] = useState<string>('');
  const [availableProviders, setAvailableProviders] = useState<string[]>([]);
  const [providerModelInfo, setProviderModelInfo] = useState<Record<string, any>>({});
  const [zoomLevel, setZoomLevel] = useState<number | null>(null); // null = auto-fit, value is relative to fitZoom
  const [fitZoomLevel, setFitZoomLevel] = useState(1); // Base zoom level for fit-to-window
  const imageContainerRef = useRef<HTMLDivElement>(null);

  // Calculate fit-to-window zoom when image loads
  const calculateFitZoom = useCallback((imageWidth: number, imageHeight: number) => {
    if (!imageContainerRef.current) return 1;
    
    const container = imageContainerRef.current;
    const containerWidth = container.clientWidth - 40; // Account for padding (20px each side)
    const containerHeight = container.clientHeight - 60; // Account for padding and controls
    
    // Calculate zoom to fit width (with some margin)
    const widthZoom = (containerWidth * 0.98) / imageWidth;
    // Calculate zoom to fit height (with some margin)  
    const heightZoom = (containerHeight * 0.98) / imageHeight;
    
    // Use the smaller zoom to ensure image fits completely
    const fitZoom = Math.min(widthZoom, heightZoom, 2); // Cap at 200%
    
    setFitZoomLevel(fitZoom);
    // Set initial zoom to 1.0 (which represents 100% = fit-to-window)
    if (zoomLevel === null) {
      setZoomLevel(1.0);
    }
    return fitZoom;
  }, [zoomLevel]);

  // Get actual zoom level for rendering (zoomLevel * fitZoomLevel)
  const actualZoomLevel = (zoomLevel ?? 1.0) * fitZoomLevel;
  
  // Get display percentage (zoomLevel * 100, where 1.0 = 100%)
  const displayZoomPercent = Math.round((zoomLevel ?? 1.0) * 100);

  const handleZoomIn = () => {
    const current = zoomLevel ?? 1.0;
    setZoomLevel(Math.min(current + 0.25, 5)); // Max 500% relative to fit
  };
  
  const handleZoomOut = () => {
    const current = zoomLevel ?? 1.0;
    setZoomLevel(Math.max(current - 0.25, 0.25)); // Min 25% relative to fit
  };
  
  const handleZoomReset = () => setZoomLevel(1.0); // Reset to 100% (fit)
  const handleZoomFit = () => setZoomLevel(1.0); // Fit to window (100%)


  const handleApplyParsedData = useCallback(() => {
    if (!form?.extracted_data) {
      alert('No OCR data available to autofill');
      return;
    }

    // Count fields before updating state
    let totalFieldsFilled = 0;
    let fieldsFromStructured = 0;
    let fieldsFromRawText = 0;

    // First pass: count what will be filled
    const newValues: Partial<FormVerification> = {};
    
    // Priority 1: Use structured_data from backend
    if (form.extracted_data?.structured_data) {
      const structuredData = extractStructuredData({ structured_data: form.extracted_data.structured_data });
      console.log('[Auto-fill] Structured data:', structuredData);
      
      Object.entries(structuredData).forEach(([key, value]) => {
        if (value && typeof value === 'string' && value.trim()) {
          const fieldKey = key as keyof FormVerification;
          if (FORM_FIELD_KEYS.includes(fieldKey)) {
            newValues[fieldKey] = value.trim();
            fieldsFromStructured++;
          }
        }
      });
    }

    // Priority 2: Parse raw_text for any missing fields
    if (form.extracted_data?.raw_text) {
      const parsedFromText = parseOCRText(form.extracted_data.raw_text);
      console.log('[Auto-fill] Parsed from text fields:', Object.keys(parsedFromText).filter(k => parsedFromText[k]).length);
      
      Object.entries(parsedFromText).forEach(([key, value]) => {
        if (value && typeof value === 'string' && value.trim()) {
          const fieldKey = key as keyof FormVerification;
          // Only fill fields not already filled from structured data
          if (FORM_FIELD_KEYS.includes(fieldKey) && !newValues[fieldKey]) {
            newValues[fieldKey] = value.trim();
            fieldsFromRawText++;
          }
        }
      });
    }

    totalFieldsFilled = fieldsFromStructured + fieldsFromRawText;

    // Now update the state
    setVerification((prev) => {
      const updated = { ...prev };
      
      Object.entries(newValues).forEach(([key, value]) => {
        if (value) {
          (updated as Record<string, string>)[key] = value;
        }
      });

      // Auto-calculate CUET total after autofill
      const cuetTotal = calculateCuetTotal(updated as FormVerification);
      if (cuetTotal) {
        updated.cuet_score = cuetTotal;
        updated.cuet_total_score = cuetTotal;
      }

      console.log('[Auto-fill] Updated verification - student_name:', updated.student_name);
      console.log('[Auto-fill] Updated verification - date_of_birth:', updated.date_of_birth);
      console.log('[Auto-fill] Updated verification - cuet_score:', updated.cuet_score);
      
      return updated;
    });
    
    // Show success message with field count
    setTimeout(() => {
      if (totalFieldsFilled > 0) {
        alert(`✅ Auto-fill complete! ${totalFieldsFilled} field${totalFieldsFilled > 1 ? 's' : ''} filled from OCR data.`);
      } else {
        alert('ℹ️ No new fields to fill. All fields may already have values or no data was extracted.');
      }
    }, 100);
  }, [form?.extracted_data]);

  useEffect(() => {
    if (id) {
      loadForm(parseInt(id));
    }
    loadProviders();
  }, [id]);

  const loadProviders = async () => {
    try {
      const providers = await apiService.getProviders();
      console.log('Loaded providers:', providers);
      
      if (providers && providers.providers && providers.providers.length > 0) {
      const normalized = providers.providers.map((name) => name.toLowerCase());
      setAvailableProviders(normalized);
      
      // Store model info for display
      if (providers.model_info) {
        setProviderModelInfo(providers.model_info);
      }
      
      const defaultProvider = (providers.default || normalized[0] || '').toLowerCase();
      setReExtractProvider((current) => {
        const currentNormalized = current ? current.toLowerCase() : '';
          return normalized.includes(currentNormalized) ? currentNormalized : defaultProvider;
        });
      } else {
        console.warn('No providers returned from API, using fallback');
        // Fallback to default providers
        setAvailableProviders(['tesseract', 'google-vision']);
      }
    } catch (error) {
      console.error('Failed to load providers:', error);
      // Fallback on error
      setAvailableProviders(['tesseract', 'google-vision']);
    }
  };

  const loadForm = async (formId: number) => {
    try {
      setLoading(true);
      const data = await apiService.getForm(formId);
      setForm(data);

      // Start with empty verification state
      let nextVerification: FormVerification = {};
      
      // Initialize all form field keys with empty strings
      FORM_FIELD_KEYS.forEach((field) => {
        nextVerification[field] = '';
      });

      // ALWAYS start with saved form data (fields that were applied to the form object)
      // This ensures we show what was actually extracted and saved
      FORM_FIELD_KEYS.forEach((field) => {
        const value = (data as Record<string, unknown>)[field];
        if (value && typeof value === 'string' && value.trim()) {
          nextVerification[field] = value.trim();
        }
      });
      
      // Then, for non-verified forms, supplement with structured_data if fields are missing
      if (data.status !== 'verified' && data.extracted_data?.structured_data) {
        const structuredData = extractStructuredData({ structured_data: data.extracted_data.structured_data });
        console.log('[loadForm] Structured data fields:', Object.keys(structuredData).length);
        
        // Apply structured data only to empty fields (don't overwrite saved data)
        Object.entries(structuredData).forEach(([key, value]) => {
          if (value && typeof value === 'string' && value.trim()) {
            const fieldKey = key as keyof FormVerification;
            if (fieldKey in nextVerification && !nextVerification[fieldKey]) {
              nextVerification[fieldKey] = value.trim();
            }
          }
        });
      }

      // Finally, parse raw_text as last resort for any still-missing fields
      if (data.extracted_data?.raw_text) {
        const parsedFromText = parseOCRText(data.extracted_data.raw_text);
        console.log('[loadForm] Parsed from text fields:', Object.keys(parsedFromText).filter(k => parsedFromText[k]).length);
        
        // Apply parsed text data only for empty fields
        Object.entries(parsedFromText).forEach(([key, value]) => {
          if (value && typeof value === 'string' && value.trim()) {
            const fieldKey = key as keyof FormVerification;
            // Only fill if the field is empty
            if (fieldKey in nextVerification && !nextVerification[fieldKey]) {
              nextVerification[fieldKey] = value.trim();
            }
          }
        });
      }

      // Log key fields for debugging
      console.log('[loadForm] Final verification state:');
      console.log('  student_name:', nextVerification.student_name);
      console.log('  date_of_birth:', nextVerification.date_of_birth);
      console.log('  gender:', nextVerification.gender);
      console.log('  email:', nextVerification.email);
      console.log('  phone_number:', nextVerification.phone_number);

      setInitialVerification({ ...nextVerification });
      setVerification({ ...nextVerification });
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
      const usedProvider = response.result.provider || reExtractProvider;
      
      // Reload form to get updated data with auto-filled fields
      await loadForm(parseInt(id));
      
      // Count how many fields were auto-filled
      const formData = await apiService.getForm(parseInt(id));
      let fieldsFilled = 0;
      if (formData.extracted_data?.structured_data) {
        fieldsFilled = Object.keys(formData.extracted_data.structured_data).filter(
          k => formData.extracted_data?.structured_data?.[k]
        ).length;
      }
      
      alert(
        `Re-extraction completed with ${formatProviderName(usedProvider)}!\n` +
        `${fieldsFilled} fields automatically extracted and filled.`
      );
    } catch (error: any) {
      alert(`Re-extraction failed: ${error.response?.data?.detail || error.message}`);
    } finally {
      setReExtracting(false);
    }
  };

  const handleSaveProgress = async () => {
    if (!id) return;

    try {
      setSaving(true);
      // Save without verifying (preserves current status)
      await apiService.updateForm(parseInt(id), verification, false);
      alert('Progress saved successfully! Form status unchanged.');
      // Reload form to show updated data
      loadForm(parseInt(id));
    } catch (error: any) {
      console.error('Failed to save progress:', error);
      alert(`Failed to save: ${error.response?.data?.detail || error.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleSave = async () => {
    if (!id) return;

    try {
      setSaving(true);
      // Save and verify (changes status to verified)
      const updatedForm = await apiService.updateForm(parseInt(id), verification, true);

      // Navigate to student profile if linked, otherwise show success message
      if (updatedForm.student_profile_id) {
        alert(`Form verified and saved successfully! Student profile created/updated.`);
        navigate(`/students/${updatedForm.student_profile_id}`);
      } else {
        alert('Form verified and saved successfully!');
        navigate('/students');
      }
    } catch (error: any) {
      console.error('Failed to save verification:', error);
      alert(`Failed to save: ${error.response?.data?.detail || error.message}`);
    } finally {
      setSaving(false);
    }
  };

  // Calculate CUET total from obtained scores
  const calculateCuetTotal = (data: FormVerification): string => {
    let total = 0;
    for (let i = 1; i <= 6; i++) {
      const score = (data as any)[`cuet_score_obtained_${i}`];
      if (score) {
        const num = parseFloat(String(score).replace(/[^\d.]/g, ''));
        if (!isNaN(num)) total += num;
      }
    }
    if (total > 0) {
      // Show decimals only if present, max 2 decimal places
      return total % 1 === 0 ? String(total) : total.toFixed(2).replace(/\.?0+$/, '');
    }
    return '';
  };

  const handleChange = (field: keyof FormVerification, value: string) => {
    setVerification((prev) => {
      const updated = { ...prev, [field]: value };
      
      // Auto-sync CUET total when any obtained score changes
      if (field.toString().startsWith('cuet_score_obtained_')) {
        const newTotal = calculateCuetTotal(updated);
        if (newTotal) {
          updated.cuet_score = newTotal;
          updated.cuet_total_score = newTotal;
        }
      }
      
      return updated;
    });
  };

  const handleResetVerification = () => {
    if (window.confirm('Are you sure you want to discard your changes and revert to the original extracted data?')) {
      setVerification(initialVerification);
    }
  };

  const isDirty = useMemo(() => {
    return JSON.stringify(verification) !== JSON.stringify(initialVerification);
  }, [verification, initialVerification]);

  const pageResults = useMemo(() => {
    if (!form?.extracted_data?.page_results) return [];
    return form.extracted_data.page_results;
  }, [form]);

  if (loading) {
    return <div className="loading">Loading form data...</div>;
  }

  if (!form) {
    return <div className="error">Form not found</div>;
  }

  return (
    <div className="verification-view">
      <div className="verification-header">
        <h2>Verify Form Data</h2>
        <div className="header-actions">
          <div className="re-extract-control">
            <select 
              className="provider-select input"
              value={reExtractProvider}
              onChange={(e) => setReExtractProvider(e.target.value)}
              disabled={reExtracting}
            >
              <option value="">Auto Select Provider</option>
              {availableProviders.length > 0 ? (
                availableProviders.map(p => (
                  <option key={p} value={p}>{formatProviderName(p, providerModelInfo)}</option>
                ))
              ) : (
                <option value="tesseract">Tesseract (Fallback)</option>
              )}
            </select>
            <button
              onClick={handleReExtract}
              disabled={reExtracting}
              className="btn btn-secondary"
            >
              {reExtracting ? 'Extracting...' : 'Re-Extract'}
            </button>
          </div>
          <button onClick={handleSave} className="btn btn-primary" disabled={saving}>
            {saving ? 'Saving...' : 'Save & Verify'}
          </button>
        </div>
      </div>

      <div className="verification-content">
        <div className="form-preview">
          <div className="pdf-controls" style={{ 
            position: 'sticky', 
            top: 0, 
            zIndex: 100, 
            background: 'rgba(42, 42, 42, 0.95)', 
            backdropFilter: 'blur(8px)',
            padding: '8px 16px', 
            marginBottom: '0',
            display: 'flex', 
            justifyContent: 'center', 
            alignItems: 'center',
            gap: '8px',
            boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
            borderBottom: '1px solid rgba(255,255,255,0.1)'
          }}>
            <button 
              onClick={handleZoomOut} 
              className="btn btn-sm" 
              title="Zoom Out"
              style={{
                background: 'rgba(255,255,255,0.1)',
                border: '1px solid rgba(255,255,255,0.2)',
                color: '#e5e7eb',
                padding: '6px 12px',
                minWidth: '36px'
              }}
            >
              <span style={{ fontSize: '1.1rem', lineHeight: 1 }}>−</span>
            </button>
            <button 
              onClick={handleZoomFit} 
              className="btn btn-sm" 
              title="Fit to Window"
              style={{
                background: zoomLevel === null ? 'rgba(59, 130, 246, 0.3)' : 'rgba(255,255,255,0.1)',
                border: '1px solid rgba(255,255,255,0.2)',
                color: '#e5e7eb',
                padding: '6px 12px',
                fontSize: '0.85rem'
              }}
            >
              Fit
            </button>
            <span style={{ 
              display: 'flex', 
              alignItems: 'center', 
              minWidth: '70px', 
              justifyContent: 'center', 
              fontWeight: 600,
              color: '#e5e7eb',
              fontSize: '0.9rem'
            }}>
              {displayZoomPercent}%
            </span>
            <button 
              onClick={handleZoomIn} 
              className="btn btn-sm" 
              title="Zoom In"
              style={{
                background: 'rgba(255,255,255,0.1)',
                border: '1px solid rgba(255,255,255,0.2)',
                color: '#e5e7eb',
                padding: '6px 12px',
                minWidth: '36px'
              }}
            >
              <span style={{ fontSize: '1.1rem', lineHeight: 1 }}>+</span>
            </button>
          </div>

          <div className="image-container" ref={imageContainerRef}>
            {Array.from({ length: form.extracted_data?.total_pages || form.extracted_data?.pages_processed || 1 }).map((_, idx) => {
              const pageNum = idx + 1;
              return (
                <PDFPageImage
                  key={pageNum}
                  formId={form.id}
                  pageNum={pageNum}
                  filePath={form.file_path}
                  zoomLevel={zoomLevel}
                  fitZoomLevel={fitZoomLevel}
                  onImageLoad={pageNum === 1 ? calculateFitZoom : undefined}
                  API_BASE_URL={API_BASE_URL}
                  getFileUrl={getFileUrl}
                />
              );
            })}
          </div>
        </div>

        <div className="data-section">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3 style={{ margin: 0 }}>Verify Form Fields</h3>
            <div className="extraction-actions" style={{ display: 'flex', gap: '0.5rem' }}>
                  {form.extracted_data?.raw_text && (
                    <button
                      onClick={handleApplyParsedData}
                      className="btn btn-sm btn-secondary"
                      style={{ fontSize: '0.8rem', padding: '0.4rem 0.8rem' }}
                    >
                  🔄 Auto-fill
                    </button>
                  )}
                  <button
                    onClick={handleResetVerification}
                    className="btn btn-sm"
                    style={{ fontSize: '0.8rem', padding: '0.4rem 0.8rem' }}
                  >
                ↩ Reset
                  </button>
                </div>
              </div>
          
          {form.extracted_data && (
            <div style={{ marginBottom: '1rem', padding: '0.5rem', background: '#f8f9fa', borderRadius: '8px', fontSize: '0.85rem' }}>
              <span style={{ fontWeight: 500 }}>Confidence: {formatConfidenceValue(form.extracted_data.confidence)}</span>
              <details style={{ marginTop: '0.5rem' }}>
                <summary style={{ cursor: 'pointer', color: '#667085', fontSize: '0.8rem' }}>View Raw Extracted Text</summary>
                <div className="raw-text-box" style={{ marginTop: '0.5rem', maxHeight: '200px', overflow: 'auto', fontSize: '0.75rem' }}>
                {form.extracted_data.raw_text || 'No text extracted'}
              </div>
              </details>
            </div>
          )}

          <div className="form-editor">

            {/* Academic & Admission Details */}
            <div className="form-section">
              <h4 className="form-section-title">Academic & Admission Details</h4>
              <div className="form-grid">
                <div className="form-row">
                  <label className="input-label">Academic Session</label>
                  <input type="text" className="input" value={verification.academic_session || ''} onChange={(e) => handleChange('academic_session', e.target.value)} placeholder="2025-2026" />
                      </div>
                <div className="form-row">
                  <label className="input-label">Course</label>
                  <select className="input select" value={verification.course || ''} onChange={(e) => handleChange('course', e.target.value)}>
                    <option value="">Select Course</option>
                    <option value="B.COM.(H)">B.COM.(H)</option>
                    <option value="B.A.(H) ECO">B.A.(H) ECO</option>
                  </select>
                    </div>
                <div className="form-row">
                  <label className="input-label">Admission Category</label>
                  <select className="input select" value={verification.admission_category || ''} onChange={(e) => handleChange('admission_category', e.target.value)}>
                    <option value="">Select Category</option>
                    <option value="GEN">GEN</option>
                    <option value="OBC">OBC</option>
                    <option value="SC">SC</option>
                    <option value="ST">ST</option>
                    <option value="EWS">EWS</option>
                    <option value="PWD">PWD</option>
                    <option value="Sports">Sports</option>
                    <option value="Foreign">Foreign</option>
                    <option value="CW">CW</option>
                    <option value="KM">KM</option>
                    <option value="Others">Others</option>
                  </select>
                </div>
                <div className="form-row">
                  <label className="input-label">Other Category (Specify)</label>
                  <input type="text" className="input" value={verification.admission_category_other || ''} onChange={(e) => handleChange('admission_category_other', e.target.value)} placeholder="If Others selected" />
            </div>
                <div className="form-row">
                  <label className="input-label">DU Portal Form No.</label>
                  <input type="text" className="input" value={verification.du_portal_form_number || ''} onChange={(e) => handleChange('du_portal_form_number', e.target.value)} placeholder="Form Number" />
                </div>
                <div className="form-row">
                  <label className="input-label">CUET Score (Total)</label>
                  <input
                    type="text"
                    className="input"
                    readOnly
                    value={calculateCuetTotal(verification) || verification.cuet_score || ''}
                    placeholder="Auto-calculated from CUET Marks"
                    style={{ backgroundColor: '#f8fafc', cursor: 'default' }}
                    title="This is auto-calculated from CUET Marks section below"
                  />
                </div>
                <div className="form-row">
                  <label className="input-label">College Roll No.</label>
                  <input type="text" className="input" value={verification.college_roll_no || ''} onChange={(e) => handleChange('college_roll_no', e.target.value)} placeholder="Roll No" />
                </div>
                <div className="form-row">
                  <label className="input-label">Date of Admission</label>
                  <input type="text" className="input" value={verification.date_of_admission || ''} onChange={(e) => handleChange('date_of_admission', e.target.value)} placeholder="DD/MM/YYYY" />
                </div>
              </div>
            </div>

            {/* Basic Details Section */}
            <div className="form-section">
              <h4 className="form-section-title">Personal Details</h4>
              <div className="form-grid">
                <div className="form-row" style={{ gridColumn: '1 / -1' }}>
                  <label className="input-label">Student Name (Block Letters) *</label>
                  <input type="text" className="input" value={verification.student_name || ''} onChange={(e) => handleChange('student_name', e.target.value)} placeholder="Enter student name" />
                </div>
                <div className="form-row">
                  <label className="input-label">Date of Birth</label>
                  <input type="text" className="input" value={verification.date_of_birth || ''} onChange={(e) => handleChange('date_of_birth', e.target.value)} placeholder="DD/MM/YYYY" />
                </div>
                <div className="form-row">
                  <label className="input-label">Gender</label>
                  <select className="input select" value={verification.gender || ''} onChange={(e) => handleChange('gender', e.target.value)}>
                    <option value="">Select</option>
                    <option value="MALE">Male</option>
                    <option value="FEMALE">Female</option>
                    <option value="TRANSGENDER">Transgender</option>
                    <option value="OTHER">Other</option>
                  </select>
                </div>
                <div className="form-row">
                  <label className="input-label">Nationality</label>
                  <input type="text" className="input" value={verification.nationality || ''} onChange={(e) => handleChange('nationality', e.target.value)} placeholder="Nationality" />
                </div>
                <div className="form-row">
                  <label className="input-label">Religion</label>
                  <input type="text" className="input" value={verification.religion || ''} onChange={(e) => handleChange('religion', e.target.value)} placeholder="Religion" />
                </div>
                <div className="form-row">
                  <label className="input-label">Aadhar Number</label>
                  <input type="text" className="input" value={verification.aadhar_number || ''} onChange={(e) => handleChange('aadhar_number', e.target.value)} placeholder="Aadhar Number" />
                </div>
                <div className="form-row">
                  <label className="input-label">Category</label>
                  <select className="input select" value={verification.category || ''} onChange={(e) => handleChange('category', e.target.value)}>
                    <option value="">Select Category</option>
                    <option value="GEN">GEN</option>
                    <option value="OBC">OBC</option>
                    <option value="SC">SC</option>
                    <option value="ST">ST</option>
                    <option value="EWS">EWS</option>
                    <option value="PWD">PWD</option>
                    <option value="Sports">Sports</option>
                    <option value="Foreign">Foreign</option>
                    <option value="CW">CW</option>
                    <option value="KM">KM</option>
                    <option value="Others">Others</option>
                  </select>
                </div>
                <div className="form-row">
                  <label className="input-label">Blood Group</label>
                  <select className="input select" value={verification.blood_group || ''} onChange={(e) => handleChange('blood_group', e.target.value)}>
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
                <div className="form-row">
                  <label className="input-label">Below Poverty Line</label>
                  <select className="input select" value={verification.below_poverty_line || ''} onChange={(e) => handleChange('below_poverty_line', e.target.value)}>
                    <option value="">Select</option>
                    <option value="YES">Yes</option>
                    <option value="NO">No</option>
                  </select>
                </div>
                <div className="form-row">
                  <label className="input-label">Annual Family Income</label>
                  <input type="text" className="input" value={verification.annual_income || ''} onChange={(e) => handleChange('annual_income', e.target.value)} placeholder="Annual Income" />
                </div>
                <div className="form-row">
                  <label className="input-label">Minority Category</label>
                  <input type="text" className="input" value={verification.minority_category || ''} onChange={(e) => handleChange('minority_category', e.target.value)} placeholder="e.g. Muslim, Jain, Sikh" />
                </div>
              </div>
            </div>

            {/* Address Details Section */}
            <div className="form-section">
              <h4 className="form-section-title">Address Details</h4>
              <div className="form-grid">
                <div className="form-row" style={{ gridColumn: '1 / -1' }}>
                  <label className="input-label">Permanent Address (Combined)</label>
                  <textarea className="input textarea" value={verification.permanent_address || ''} onChange={(e) => handleChange('permanent_address', e.target.value)} placeholder="Permanent Address" rows={2} />
                </div>
                <div className="form-row">
                  <label className="input-label">Permanent Address Line 1</label>
                  <input type="text" className="input" value={verification.permanent_address_line1 || ''} onChange={(e) => handleChange('permanent_address_line1', e.target.value)} placeholder="Line 1" />
                </div>
                <div className="form-row">
                  <label className="input-label">Permanent Address Line 2</label>
                  <input type="text" className="input" value={verification.permanent_address_line2 || ''} onChange={(e) => handleChange('permanent_address_line2', e.target.value)} placeholder="Line 2" />
                </div>
                <div className="form-row">
                  <label className="input-label">Permanent Address Line 3</label>
                  <input type="text" className="input" value={verification.permanent_address_line3 || ''} onChange={(e) => handleChange('permanent_address_line3', e.target.value)} placeholder="Line 3" />
                </div>
                <div className="form-row">
                  <label className="input-label">Permanent State</label>
                  <input type="text" className="input" value={verification.permanent_state || ''} onChange={(e) => handleChange('permanent_state', e.target.value)} placeholder="State" />
                </div>
                <div className="form-row">
                  <label className="input-label">Permanent PIN</label>
                  <input type="text" className="input" value={verification.permanent_pincode || ''} onChange={(e) => handleChange('permanent_pincode', e.target.value)} placeholder="PIN Code" />
                </div>
                
                <div className="form-row" style={{ gridColumn: '1 / -1', marginTop: '1rem' }}>
                  <label className="input-label">Correspondence Address (Combined)</label>
                  <textarea className="input textarea" value={verification.correspondence_address || ''} onChange={(e) => handleChange('correspondence_address', e.target.value)} placeholder="Correspondence Address" rows={2} />
                </div>
                <div className="form-row">
                  <label className="input-label">Correspondence Address Line 1</label>
                  <input type="text" className="input" value={verification.correspondence_address_line1 || ''} onChange={(e) => handleChange('correspondence_address_line1', e.target.value)} placeholder="Line 1" />
                </div>
                <div className="form-row">
                  <label className="input-label">Correspondence Address Line 2</label>
                  <input type="text" className="input" value={verification.correspondence_address_line2 || ''} onChange={(e) => handleChange('correspondence_address_line2', e.target.value)} placeholder="Line 2" />
                </div>
                <div className="form-row">
                  <label className="input-label">Correspondence Address Line 3</label>
                  <input type="text" className="input" value={verification.correspondence_address_line3 || ''} onChange={(e) => handleChange('correspondence_address_line3', e.target.value)} placeholder="Line 3" />
                </div>
                <div className="form-row">
                  <label className="input-label">Correspondence State</label>
                  <input type="text" className="input" value={verification.correspondence_state || ''} onChange={(e) => handleChange('correspondence_state', e.target.value)} placeholder="State" />
                </div>
                <div className="form-row">
                  <label className="input-label">Correspondence PIN</label>
                  <input type="text" className="input" value={verification.correspondence_pincode || ''} onChange={(e) => handleChange('correspondence_pincode', e.target.value)} placeholder="PIN Code" />
                </div>
                <div className="form-row">
                  <label className="input-label">City</label>
                  <input type="text" className="input" value={verification.city || ''} onChange={(e) => handleChange('city', e.target.value)} placeholder="City" />
                </div>
                <div className="form-row">
                  <label className="input-label">State (Legacy)</label>
                  <input type="text" className="input" value={verification.state || ''} onChange={(e) => handleChange('state', e.target.value)} placeholder="State" />
                </div>
                <div className="form-row">
                  <label className="input-label">PIN Code (Legacy)</label>
                  <input type="text" className="input" value={verification.pincode || ''} onChange={(e) => handleChange('pincode', e.target.value)} placeholder="PIN" />
                </div>
              </div>
            </div>

            {/* Contact Details Section */}
            <div className="form-section">
              <h4 className="form-section-title">Contact Details</h4>
              <div className="form-grid">
                <div className="form-row">
                  <label className="input-label">Email</label>
                  <input type="email" className="input" value={verification.email || ''} onChange={(e) => handleChange('email', e.target.value)} placeholder="Student Email" />
                </div>
                <div className="form-row">
                  <label className="input-label">Phone Number</label>
                  <input type="text" className="input" value={verification.phone_number || ''} onChange={(e) => handleChange('phone_number', e.target.value)} placeholder="Phone Number" />
                </div>
                <div className="form-row">
                  <label className="input-label">Alternate Phone</label>
                  <input type="text" className="input" value={verification.alternate_phone || ''} onChange={(e) => handleChange('alternate_phone', e.target.value)} placeholder="Alternate Phone" />
                </div>
                <div className="form-row">
                  <label className="input-label">Emergency Contact Name</label>
                  <input type="text" className="input" value={verification.emergency_contact_name || ''} onChange={(e) => handleChange('emergency_contact_name', e.target.value)} placeholder="Emergency Contact" />
                </div>
                <div className="form-row">
                  <label className="input-label">Emergency Contact Phone</label>
                  <input type="text" className="input" value={verification.emergency_contact_phone || ''} onChange={(e) => handleChange('emergency_contact_phone', e.target.value)} placeholder="Emergency Phone" />
                </div>
              </div>
            </div>

            {/* Parent Details Section */}
            <div className="form-section">
              <h4 className="form-section-title">Mother's Details</h4>
              <div className="form-grid">
                <div className="form-row">
                  <label className="input-label">Mother's Name</label>
                  <input type="text" className="input" value={verification.mother_name || ''} onChange={(e) => handleChange('mother_name', e.target.value)} placeholder="Mother's Name" />
                </div>
                <div className="form-row">
                  <label className="input-label">Occupation</label>
                  <input type="text" className="input" value={verification.mother_occupation || ''} onChange={(e) => handleChange('mother_occupation', e.target.value)} placeholder="Occupation" />
                </div>
                <div className="form-row">
                  <label className="input-label">Designation</label>
                  <input type="text" className="input" value={verification.mother_designation || ''} onChange={(e) => handleChange('mother_designation', e.target.value)} placeholder="Designation" />
                </div>
                <div className="form-row">
                  <label className="input-label">Organization</label>
                  <input type="text" className="input" value={verification.mother_organization || ''} onChange={(e) => handleChange('mother_organization', e.target.value)} placeholder="Organization" />
                </div>
                <div className="form-row">
                  <label className="input-label">Mother's Email</label>
                  <input type="email" className="input" value={verification.mother_email || ''} onChange={(e) => handleChange('mother_email', e.target.value)} placeholder="Email" />
                </div>
                <div className="form-row">
                  <label className="input-label">Mother's Mobile</label>
                  <input type="text" className="input" value={verification.mother_mobile || ''} onChange={(e) => handleChange('mother_mobile', e.target.value)} placeholder="Mobile No." />
                </div>
                <div className="form-row">
                  <label className="input-label">Mother's Landline Code</label>
                  <input type="text" className="input" value={verification.mother_landline_code || ''} onChange={(e) => handleChange('mother_landline_code', e.target.value)} placeholder="Code" />
                </div>
                <div className="form-row">
                  <label className="input-label">Mother's Landline</label>
                  <input type="text" className="input" value={verification.mother_landline || ''} onChange={(e) => handleChange('mother_landline', e.target.value)} placeholder="Landline No." />
                </div>
                <div className="form-row">
                  <label className="input-label">Mother's Phone (Combined)</label>
                  <input type="text" className="input" value={verification.mother_phone || ''} onChange={(e) => handleChange('mother_phone', e.target.value)} placeholder="Phone" />
                </div>
              </div>

              <h4 className="form-section-title" style={{ marginTop: '1.5rem' }}>Father's Details</h4>
              <div className="form-grid">
                <div className="form-row">
                  <label className="input-label">Father's Name</label>
                  <input type="text" className="input" value={verification.father_name || ''} onChange={(e) => handleChange('father_name', e.target.value)} placeholder="Father's Name" />
                </div>
                <div className="form-row">
                  <label className="input-label">Occupation</label>
                  <input type="text" className="input" value={verification.father_occupation || ''} onChange={(e) => handleChange('father_occupation', e.target.value)} placeholder="Occupation" />
                </div>
                <div className="form-row">
                  <label className="input-label">Designation</label>
                  <input type="text" className="input" value={verification.father_designation || ''} onChange={(e) => handleChange('father_designation', e.target.value)} placeholder="Designation" />
                </div>
                <div className="form-row">
                  <label className="input-label">Organization</label>
                  <input type="text" className="input" value={verification.father_organization || ''} onChange={(e) => handleChange('father_organization', e.target.value)} placeholder="Organization" />
                </div>
                <div className="form-row">
                  <label className="input-label">Father's Email</label>
                  <input type="email" className="input" value={verification.father_email || ''} onChange={(e) => handleChange('father_email', e.target.value)} placeholder="Email" />
                </div>
                <div className="form-row">
                  <label className="input-label">Father's Mobile</label>
                  <input type="text" className="input" value={verification.father_mobile || ''} onChange={(e) => handleChange('father_mobile', e.target.value)} placeholder="Mobile No." />
                </div>
                <div className="form-row">
                  <label className="input-label">Father's Landline Code</label>
                  <input type="text" className="input" value={verification.father_landline_code || ''} onChange={(e) => handleChange('father_landline_code', e.target.value)} placeholder="Code" />
                </div>
                <div className="form-row">
                  <label className="input-label">Father's Landline</label>
                  <input type="text" className="input" value={verification.father_landline || ''} onChange={(e) => handleChange('father_landline', e.target.value)} placeholder="Landline No." />
                </div>
                <div className="form-row">
                  <label className="input-label">Father's Phone (Combined)</label>
                  <input type="text" className="input" value={verification.father_phone || ''} onChange={(e) => handleChange('father_phone', e.target.value)} placeholder="Phone" />
                </div>
              </div>
            </div>

            {/* Local Guardian Details */}
            <div className="form-section">
              <h4 className="form-section-title">Local Guardian's Details</h4>
              <div className="form-grid">
                <div className="form-row">
                  <label className="input-label">Guardian Name</label>
                  <input type="text" className="input" value={verification.guardian_name || ''} onChange={(e) => handleChange('guardian_name', e.target.value)} placeholder="Name" />
                </div>
                <div className="form-row">
                  <label className="input-label">Residential Address</label>
                  <input type="text" className="input" value={verification.guardian_residential_address || ''} onChange={(e) => handleChange('guardian_residential_address', e.target.value)} placeholder="Address" />
                </div>
                <div className="form-row">
                  <label className="input-label">Organization</label>
                  <input type="text" className="input" value={verification.guardian_organization || ''} onChange={(e) => handleChange('guardian_organization', e.target.value)} placeholder="Organization" />
                </div>
                <div className="form-row">
                  <label className="input-label">Email</label>
                  <input type="email" className="input" value={verification.guardian_email || ''} onChange={(e) => handleChange('guardian_email', e.target.value)} placeholder="Email" />
                </div>
                <div className="form-row">
                  <label className="input-label">Mobile Number</label>
                  <input type="text" className="input" value={verification.guardian_mobile || ''} onChange={(e) => handleChange('guardian_mobile', e.target.value)} placeholder="Mobile No." />
                </div>
                <div className="form-row">
                  <label className="input-label">Guardian's Landline Code</label>
                  <input type="text" className="input" value={verification.guardian_landline_code || ''} onChange={(e) => handleChange('guardian_landline_code', e.target.value)} placeholder="Code" />
                </div>
                <div className="form-row">
                  <label className="input-label">Guardian's Landline</label>
                  <input type="text" className="input" value={verification.guardian_landline || ''} onChange={(e) => handleChange('guardian_landline', e.target.value)} placeholder="Landline No." />
                </div>
                <div className="form-row">
                  <label className="input-label">Guardian's Phone (Combined)</label>
                  <input type="text" className="input" value={verification.guardian_phone || ''} onChange={(e) => handleChange('guardian_phone', e.target.value)} placeholder="Phone" />
                </div>
                <div className="form-row">
                  <label className="input-label">Guardian's Relation</label>
                  <input type="text" className="input" value={verification.guardian_relation || ''} onChange={(e) => handleChange('guardian_relation', e.target.value)} placeholder="Relationship" />
                </div>
              </div>
            </div>

            {/* CUET Marks Section */}
            <div className="form-section">
              <h4 className="form-section-title">CUET Marks</h4>
              <div className="form-grid" style={{ gridTemplateColumns: '1fr 100px 100px' }}>
                <div className="form-row"><strong>Subject</strong></div>
                <div className="form-row"><strong>Total</strong></div>
                <div className="form-row"><strong>Obtained</strong></div>
                
                {[1, 2, 3, 4, 5, 6].map(i => (
                  <div key={i} style={{ display: 'contents' }}>
                    <input type="text" className="input" value={(verification as any)[`cuet_subject_${i}`] || ''} onChange={(e) => handleChange(`cuet_subject_${i}` as any, e.target.value)} placeholder={`Subject ${i}`} />
                    <input type="text" className="input" value={(verification as any)[`cuet_total_score_${i}`] || ''} onChange={(e) => handleChange(`cuet_total_score_${i}` as any, e.target.value)} placeholder="Total" />
                    <input type="text" className="input" value={(verification as any)[`cuet_score_obtained_${i}`] || ''} onChange={(e) => handleChange(`cuet_score_obtained_${i}` as any, e.target.value)} placeholder="Score" />
                  </div>
                ))}
                
                <div style={{ gridColumn: '1 / -1', marginTop: '12px', paddingTop: '12px', borderTop: '2px solid #e2e8f0', display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: '12px' }}>
                  <strong style={{ color: '#334155' }}>Total CUET Score:</strong>
                  <input
                    type="text"
                    readOnly
                    value={calculateCuetTotal(verification) || verification.cuet_score || '0'}
                    style={{ 
                      padding: '10px 16px', 
                      backgroundColor: '#ecfdf5', 
                      borderRadius: '8px', 
                      fontWeight: '700',
                      fontSize: '1rem',
                      width: '100px',
                      textAlign: 'center',
                      border: '2px solid #a7f3d0',
                      color: '#059669',
                      cursor: 'default'
                    }}
                  />
                  <span style={{ fontSize: '0.75rem', color: '#64748b' }}>Auto-calculated</span>
                </div>
              </div>
            </div>

            {/* Qualifying Exam Section */}
            <div className="form-section">
              <h4 className="form-section-title">Qualifying Examination (Class XII)</h4>
              <div className="form-grid">
                <div className="form-row">
                  <label className="input-label">Year of Passing</label>
                  <input type="text" className="input" value={verification.twelfth_year || ''} onChange={(e) => handleChange('twelfth_year', e.target.value)} placeholder="Year" />
                </div>
                <div className="form-row">
                  <label className="input-label">Board/University</label>
                  <input type="text" className="input" value={verification.twelfth_board || ''} onChange={(e) => handleChange('twelfth_board', e.target.value)} placeholder="Board" />
                </div>
                <div className="form-row">
                  <label className="input-label">Percentage</label>
                  <input type="text" className="input" value={verification.twelfth_percentage || ''} onChange={(e) => handleChange('twelfth_percentage', e.target.value)} placeholder="%" />
                </div>
                <div className="form-row">
                  <label className="input-label">School Name</label>
                  <input type="text" className="input" value={verification.twelfth_school || ''} onChange={(e) => handleChange('twelfth_school', e.target.value)} placeholder="School" />
                </div>
                <div className="form-row">
                  <label className="input-label">Exam Roll No.</label>
                  <input type="text" className="input" value={verification.twelfth_roll_number || ''} onChange={(e) => handleChange('twelfth_roll_number', e.target.value)} placeholder="Roll No" />
                </div>
                <div className="form-row">
                  <label className="input-label">Institution Last Attended</label>
                  <input type="text" className="input" value={verification.twelfth_institution || ''} onChange={(e) => handleChange('twelfth_institution', e.target.value)} placeholder="School Name" />
                </div>
                <div className="form-row">
                  <label className="input-label">Hindi Studied Upto</label>
                  <select className="input select" value={verification.hindi_studied_upto || ''} onChange={(e) => handleChange('hindi_studied_upto', e.target.value)}>
                    <option value="">Select</option>
                    <option value="VIII">VIII</option>
                    <option value="X">X</option>
                    <option value="XII">XII</option>
                    <option value="NEVER">Never</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Class X Details (Legacy) */}
            <div className="form-section">
              <h4 className="form-section-title">Class X Details (Legacy)</h4>
              <div className="form-grid">
                <div className="form-row">
                  <label className="input-label">Class X Board</label>
                  <input type="text" className="input" value={verification.tenth_board || ''} onChange={(e) => handleChange('tenth_board', e.target.value)} placeholder="Board" />
                </div>
                <div className="form-row">
                  <label className="input-label">Class X Year</label>
                  <input type="text" className="input" value={verification.tenth_year || ''} onChange={(e) => handleChange('tenth_year', e.target.value)} placeholder="Year" />
                </div>
                <div className="form-row">
                  <label className="input-label">Class X Percentage</label>
                  <input type="text" className="input" value={verification.tenth_percentage || ''} onChange={(e) => handleChange('tenth_percentage', e.target.value)} placeholder="%" />
                </div>
                <div className="form-row">
                  <label className="input-label">Class X School</label>
                  <input type="text" className="input" value={verification.tenth_school || ''} onChange={(e) => handleChange('tenth_school', e.target.value)} placeholder="School" />
                </div>
              </div>
            </div>

            {/* Other Educational Details */}
            <div className="form-section">
              <h4 className="form-section-title">Other Educational Details</h4>
              <div className="form-grid">
                <div className="form-row" style={{ gridColumn: '1 / -1' }}>
                  <label className="input-label">Previous Qualification</label>
                  <input type="text" className="input" value={verification.previous_qualification || ''} onChange={(e) => handleChange('previous_qualification', e.target.value)} placeholder="Previous Qualification" />
                </div>
                <div className="form-row" style={{ gridColumn: '1 / -1' }}>
                  <label className="input-label">Graduation Details</label>
                  <textarea className="input textarea" value={verification.graduation_details || ''} onChange={(e) => handleChange('graduation_details', e.target.value)} placeholder="Graduation Details" rows={2} />
                </div>
              </div>
            </div>

            {/* Other Information & Certificate */}
            <div className="form-section">
              <h4 className="form-section-title">Other Information & Certificates</h4>
              <div className="form-grid">
                <div className="form-row">
                  <label className="input-label">DU Enrollment No.</label>
                  <input type="text" className="input" value={verification.du_enrollment_number || ''} onChange={(e) => handleChange('du_enrollment_number', e.target.value)} placeholder="Enrollment No" />
                </div>
                <div className="form-row">
                  <label className="input-label">Hindi Medium Pref.</label>
                  <select className="input select" value={verification.hindi_medium_preference || ''} onChange={(e) => handleChange('hindi_medium_preference', e.target.value)}>
                    <option value="">Select</option>
                    <option value="YES">Yes</option>
                    <option value="NO">No</option>
                  </select>
                </div>
                <div className="form-row" style={{ gridColumn: '1 / -1' }}>
                  <label className="input-label">Certificate Issuing Authority</label>
                  <input type="text" className="input" value={verification.category_certificate_authority || ''} onChange={(e) => handleChange('category_certificate_authority', e.target.value)} placeholder="Authority Name & Address" />
                </div>
                <div className="form-row">
                  <label className="input-label">Certificate No.</label>
                  <input type="text" className="input" value={verification.category_certificate_number || ''} onChange={(e) => handleChange('category_certificate_number', e.target.value)} placeholder="Cert No" />
                </div>
                <div className="form-row">
                  <label className="input-label">Date of Issue</label>
                  <input type="text" className="input" value={verification.category_certificate_date || ''} onChange={(e) => handleChange('category_certificate_date', e.target.value)} placeholder="DD/MM/YYYY" />
                </div>
                <div className="form-row">
                  <label className="input-label">Disability Percentage</label>
                  <input type="text" className="input" value={verification.disability_percentage || ''} onChange={(e) => handleChange('disability_percentage', e.target.value)} placeholder="%" />
                </div>
                <div className="form-row">
                  <label className="input-label">Disability Type</label>
                  <select className="input select" value={verification.disability_type || ''} onChange={(e) => handleChange('disability_type', e.target.value)}>
                    <option value="">Select</option>
                    <option value="VH">VH (Visual)</option>
                    <option value="HH">HH (Hearing)</option>
                    <option value="OH">OH (Orthopedic)</option>
                  </select>
                </div>
                <div className="form-row">
                  <label className="input-label">UDID Number</label>
                  <input type="text" className="input" value={verification.udid_number || ''} onChange={(e) => handleChange('udid_number', e.target.value)} placeholder="UDID No." />
                </div>
              </div>
            </div>

          </div>

          <div className="form-actions">
            <button
              onClick={handleSaveProgress}
              disabled={saving}
              className="btn btn-secondary btn-large"
            >
              {saving ? 'Saving...' : 'Save Progress'}
            </button>
            <button
              onClick={handleSave}
              disabled={saving || !verification.student_name}
              className="btn btn-primary btn-large"
            >
              {saving ? 'Saving...' : 'Save & Verify'}
            </button>
          </div>

          {/* Document Checklist from Page 4 */}
          <div className="form-section" style={{ marginTop: '2rem' }}>
            <h3 className="section-title">📋 Document Checklist</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px', padding: '12px', backgroundColor: '#f8f9fa', borderRadius: '8px' }}>
              {[
                { key: 'doc_admission_form', label: 'Admission/Registration Form' },
                { key: 'doc_undertaking_ragging', label: 'Anti-Ragging Undertaking' },
                { key: 'doc_photographs', label: 'Photographs' },
                { key: 'doc_cuet_scorecard', label: 'CUET Score Card' },
                { key: 'doc_class_xii_marksheet', label: 'Class XII Mark Sheet' },
                { key: 'doc_class_x_certificate', label: 'Class X Certificate' },
                { key: 'doc_class_xii_certificate', label: 'Class XII Certificate' },
                { key: 'doc_character_certificate', label: 'Character Certificate' },
                { key: 'doc_transfer_certificate', label: 'Transfer/Migration Certificate' },
                { key: 'doc_hindi_certificate', label: 'Hindi Certificate' },
                { key: 'doc_caste_certificate', label: 'Caste/Category Certificate' },
                { key: 'doc_sports_eca', label: 'Sports/ECA Certificates' },
                { key: 'doc_originals', label: 'Original Documents' },
                { key: 'doc_photo_id', label: 'Photo ID Proof' },
              ].map(({ key, label }) => {
                const value = (verification as any)[key] || 'No';
                const isChecked = value === 'Yes';
                return (
                  <label 
                    key={key} 
                    style={{ 
                      display: 'flex', 
                      alignItems: 'center', 
                      gap: '8px',
                      padding: '8px 12px',
                      backgroundColor: isChecked ? '#e8f5e9' : '#fff',
                      borderRadius: '4px',
                      border: `1px solid ${isChecked ? '#4caf50' : '#ddd'}`,
                      cursor: 'pointer',
                      transition: 'all 0.2s ease'
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={(e) => handleChange(key, e.target.checked ? 'Yes' : 'No')}
                      style={{ 
                        width: '18px', 
                        height: '18px',
                        accentColor: '#4caf50',
                        cursor: 'pointer'
                      }}
                    />
                    <span style={{ fontSize: '13px', color: isChecked ? '#2e7d32' : '#666' }}>
                      {label}
                    </span>
                  </label>
                );
              })}
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
                onRefresh={() => loadForm(form.id)}
                studentInfo={{
                  duPortalNumber: verification.du_portal_form_number || verification.du_enrollment_number || '',
                  fullName: [verification.first_name, verification.middle_name, verification.surname].filter(Boolean).join(' ')
                }}
              />
            </div>
          )}
          
          {/* Bottom spacing */}
          <div style={{ height: '4rem' }}></div>
        </div>
      </div>
    </div>
  );
}

export default VerificationView;
