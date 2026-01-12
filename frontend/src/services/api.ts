import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 120000, // 120 second timeout for OCR processing
});

// Add request interceptor for debugging
api.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Add response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.code === 'ECONNABORTED') {
      console.error('API Request timeout');
      error.message = 'Request timeout. Please try again.';
    } else if (error.response) {
      // Server responded with error status
      console.error('API Error Response:', error.response.status, error.response.data);
    } else if (error.request) {
      // Request made but no response received
      console.error('API Network Error:', error.request);
      error.message = 'Network error. Please check if the backend server is running.';
    } else {
      console.error('API Error:', error.message);
    }
    return Promise.reject(error);
  }
);

export interface OCRProvider {
  providers: string[];
  default: string;
  model_info?: {
    [key: string]: {
      custom_model?: boolean;
      model_path?: string;
      model_name?: string;
      description?: string;
    };
  };
}

export interface FormResponse {
  id: number;
  filename: string;
  upload_date: string;
  status: string;
  file_path: string;
  ocr_provider: string;
}

export interface PageExtraction {
  page: number;
  raw_text?: string;
  confidence?: number;
  provider?: string;
}

export interface ExtractedData {
  raw_text: string;
  confidence?: number | null;
  structured_data?: any;
  provider?: string;
  word_count?: number;
  psm_mode?: number;
  pages_processed?: number;
  page_results?: PageExtraction[];
}

export interface FormExtractionResponse {
  message: string;
  result: ExtractedData;
}

export type DocumentCategory = 
  | "ID Proof"
  | "Academic Certificate"
  | "Medical Certificate"
  | "Birth Certificate"
  | "Income Certificate"
  | "Caste Certificate"
  | "Other";

export interface Document {
  id: number;
  filename: string;
  file_path: string;
  upload_date: string;
  document_category: DocumentCategory;
  description?: string;
  file_size: number;
  form_id?: number;
  student_profile_id?: number;
}

export interface StudentProfile {
  id: number;
  student_name: string;
  aadhar_number?: string;
  roll_number?: string;
  phone_number?: string;
  email?: string;
  course_applied?: string;
  application_number?: string;
  enrollment_number?: string;
  created_date: string;
  updated_date: string;
  forms_count: number;
  documents_count: number;
}

export interface StudentProfileDetail extends StudentProfile {
  forms: FormDetail[];
  documents: Document[];
}

export interface FormDetail extends FormResponse {
  extracted_data?: ExtractedData;
  student_profile_id?: number;
  documents?: Document[];
  
  // Academic & Admission Details
  academic_session?: string;
  course?: string;
  admission_category?: string;
  admission_category_other?: string;
  du_portal_form_number?: string;
  cuet_score?: string;
  college_roll_no?: string;
  date_of_admission?: string;
  
  // Personal Details
  student_name?: string;
  first_name?: string;
  middle_name?: string;
  surname?: string;
  date_of_birth?: string;
  gender?: string;
  category?: string;
  nationality?: string;
  religion?: string;
  aadhar_number?: string;
  blood_group?: string;
  below_poverty_line?: string;
  minority_category?: string;
  
  // Address Details
  permanent_address?: string;
  permanent_address_line1?: string;
  permanent_address_line2?: string;
  permanent_address_line3?: string;
  permanent_state?: string;
  permanent_pincode?: string;
  correspondence_address?: string;
  correspondence_address_line1?: string;
  correspondence_address_line2?: string;
  correspondence_address_line3?: string;
  correspondence_state?: string;
  correspondence_pincode?: string;
  pincode?: string;
  city?: string;
  state?: string;
  
  // Contact Details
  phone_number?: string;
  alternate_phone?: string;
  email?: string;
  emergency_contact_name?: string;
  emergency_contact_phone?: string;
  
  // CUET Marks
  cuet_subject_1?: string;
  cuet_total_score_1?: string;
  cuet_score_obtained_1?: string;
  cuet_subject_2?: string;
  cuet_total_score_2?: string;
  cuet_score_obtained_2?: string;
  cuet_subject_3?: string;
  cuet_total_score_3?: string;
  cuet_score_obtained_3?: string;
  cuet_subject_4?: string;
  cuet_total_score_4?: string;
  cuet_score_obtained_4?: string;
  cuet_subject_5?: string;
  cuet_total_score_5?: string;
  cuet_score_obtained_5?: string;
  cuet_subject_6?: string;
  cuet_total_score_6?: string;
  cuet_score_obtained_6?: string;
  cuet_total_score?: string;
  
  // Qualifying Examination
  twelfth_year?: string;
  twelfth_board?: string;
  twelfth_roll_number?: string;
  twelfth_institution?: string;
  twelfth_percentage?: string;
  twelfth_school?: string;
  hindi_studied_upto?: string;
  
  // Mother's Occupational Details
  mother_name?: string;
  mother_occupation?: string;
  mother_designation?: string;
  mother_organization?: string;
  mother_email?: string;
  mother_mobile?: string;
  mother_landline_code?: string;
  mother_landline?: string;
  mother_phone?: string;
  
  // Father's Occupational Details
  father_name?: string;
  father_occupation?: string;
  father_designation?: string;
  father_organization?: string;
  father_email?: string;
  father_mobile?: string;
  father_landline_code?: string;
  father_landline?: string;
  father_phone?: string;
  
  // Local Guardian's Details
  guardian_name?: string;
  guardian_relation?: string;
  guardian_residential_address?: string;
  guardian_organization?: string;
  guardian_email?: string;
  guardian_mobile?: string;
  guardian_landline_code?: string;
  guardian_landline?: string;
  guardian_phone?: string;
  
  // Personal Information
  annual_income?: string;
  
  // Other Information
  du_enrollment_number?: string;
  hindi_medium_preference?: string;
  
  // Category Certificate Details
  category_certificate_authority?: string;
  category_certificate_number?: string;
  category_certificate_date?: string;
  disability_percentage?: string;
  disability_type?: string;
  udid_number?: string;
  
  // Educational Qualifications (Legacy)
  tenth_board?: string;
  tenth_year?: string;
  tenth_percentage?: string;
  tenth_school?: string;
  previous_qualification?: string;
  graduation_details?: string;
  
  // Course Application Details (Legacy)
  course_applied?: string;
  application_number?: string;
  enrollment_number?: string;
  admission_date?: string;
  
  // Document Checklist (Page 4)
  doc_admission_form?: string;
  doc_undertaking_ragging?: string;
  doc_photographs?: string;
  doc_cuet_scorecard?: string;
  doc_class_xii_marksheet?: string;
  doc_class_x_certificate?: string;
  doc_class_xii_certificate?: string;
  doc_character_certificate?: string;
  doc_transfer_certificate?: string;
  doc_hindi_certificate?: string;
  doc_caste_certificate?: string;
  doc_sports_eca?: string;
  doc_originals?: string;
  doc_photo_id?: string;
  
  additional_info?: any;
  verified_date?: string;
}

// Alias for backward compatibility
export type AdmissionForm = FormDetail;

export interface FormVerification {
  // Academic & Admission Details (Page 1 - Top)
  academic_session?: string;
  course?: string; // B.COM.(H) / B.A.(H) ECO
  admission_category?: string; // GEN/OBC/SC/ST/Sports/PwD/EWS/Foreign/CW/KM/Others/ECA
  admission_category_other?: string;
  du_portal_form_number?: string;
  cuet_score?: string;
  college_roll_no?: string;
  date_of_admission?: string;

  // Personal Details (Section 1-3)
  student_name?: string;
  first_name?: string;
  middle_name?: string;
  surname?: string;
  gender?: string; // Male/Female/Transgender
  date_of_birth?: string;
  category?: string; // Reservation category (may differ from admission_category)
  nationality?: string;
  religion?: string;
  aadhar_number?: string;
  blood_group?: string;
  below_poverty_line?: string; // Yes/No
  minority_category?: string; // Muslim/Jain/Sikh/Persian/Christian/Buddhists/Others

  // Address Details (Section 4-5)
  permanent_address?: string;
  permanent_address_line1?: string;
  permanent_address_line2?: string;
  permanent_address_line3?: string;
  permanent_state?: string;
  permanent_pincode?: string;
  correspondence_address?: string;
  correspondence_address_line1?: string;
  correspondence_address_line2?: string;
  correspondence_address_line3?: string;
  correspondence_state?: string;
  correspondence_pincode?: string;
  city?: string;
  state?: string;
  pincode?: string;

  // Contact Details (Section 6-7)
  email?: string;
  phone_number?: string;
  alternate_phone?: string;
  emergency_contact_name?: string;
  emergency_contact_phone?: string;

  // Parent Names (Section 8-9)
  mother_name?: string;
  father_name?: string;

  // CUET Marks (Section 10)
  cuet_subject_1?: string;
  cuet_total_score_1?: string;
  cuet_score_obtained_1?: string;
  cuet_subject_2?: string;
  cuet_total_score_2?: string;
  cuet_score_obtained_2?: string;
  cuet_subject_3?: string;
  cuet_total_score_3?: string;
  cuet_score_obtained_3?: string;
  cuet_subject_4?: string;
  cuet_total_score_4?: string;
  cuet_score_obtained_4?: string;
  cuet_subject_5?: string;
  cuet_total_score_5?: string;
  cuet_score_obtained_5?: string;
  cuet_subject_6?: string;
  cuet_total_score_6?: string;
  cuet_score_obtained_6?: string;
  cuet_total_score?: string;

  // Qualifying Examination (Section 11)
  twelfth_year?: string;
  twelfth_board?: string;
  twelfth_roll_number?: string;
  twelfth_institution?: string;
  hindi_studied_upto?: string; // VIII/X/XII/Never

  // Personal Information (Section 12)
  annual_income?: string;

  // Mother's Occupational Details (Section 13)
  mother_occupation?: string;
  mother_designation?: string;
  mother_organization?: string;
  mother_email?: string;
  mother_mobile?: string;
  mother_landline_code?: string;
  mother_landline?: string;
  mother_phone?: string;

  // Father's Occupational Details (Section 14)
  father_occupation?: string;
  father_designation?: string;
  father_organization?: string;
  father_email?: string;
  father_mobile?: string;
  father_landline_code?: string;
  father_landline?: string;
  father_phone?: string;

  // Local Guardian's Details (Section 15)
  guardian_name?: string;
  guardian_residential_address?: string;
  guardian_organization?: string;
  guardian_email?: string;
  guardian_mobile?: string;
  guardian_landline_code?: string;
  guardian_landline?: string;
  guardian_phone?: string;
  guardian_relation?: string;

  // Other Information (Section 16)
  du_enrollment_number?: string;
  hindi_medium_preference?: string; // Yes/No

  // Category Certificate (Section 17)
  category_certificate_authority?: string;
  category_certificate_number?: string;
  category_certificate_date?: string;
  disability_percentage?: string;
  disability_type?: string; // VH/HH/OH
  udid_number?: string;

  // Legacy/Backward Compatibility
  course_applied?: string;
  application_number?: string;
  enrollment_number?: string;
  admission_date?: string;
  tenth_board?: string;
  tenth_year?: string;
  tenth_percentage?: string;
  tenth_school?: string;
  twelfth_percentage?: string;
  twelfth_school?: string;
  previous_qualification?: string;
  graduation_details?: string;
  
  // Document Checklist (Page 4)
  doc_admission_form?: string;
  doc_undertaking_ragging?: string;
  doc_photographs?: string;
  doc_cuet_scorecard?: string;
  doc_class_xii_marksheet?: string;
  doc_class_x_certificate?: string;
  doc_class_xii_certificate?: string;
  doc_character_certificate?: string;
  doc_transfer_certificate?: string;
  doc_hindi_certificate?: string;
  doc_caste_certificate?: string;
  doc_sports_eca?: string;
  doc_originals?: string;
  doc_photo_id?: string;
  
  additional_info?: any;
}

export interface FormSearchQuery {
  student_name?: string;
  phone_number?: string;
  email?: string;
  enrollment_number?: string;
  application_number?: string;
  course_applied?: string;
  status?: string;
  date_from?: string;
  date_to?: string;
  page?: number;
  limit?: number;
}

// API functions
export const apiService = {
  // Upload form
  uploadForm: async (file: File, ocrProvider?: string): Promise<FormResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post<FormResponse>('/api/upload', formData, {
      params: ocrProvider ? { ocr_provider: ocrProvider } : undefined,
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Get available OCR providers
  getProviders: async (): Promise<OCRProvider> => {
    try {
      const response = await api.get<OCRProvider>('/api/providers');
      return response.data;
    } catch (error: any) {
      console.error('Failed to fetch OCR providers:', error);
      // Return default provider if API fails
      return {
        providers: ['tesseract'],
        default: 'tesseract'
      };
    }
  },

  // List forms
  listForms: async (skip: number = 0, limit: number = 20, status?: string): Promise<FormDetail[]> => {
    const response = await api.get<FormDetail[]>('/api/forms/', {
      params: { skip, limit, status },
    });
    return response.data;
  },

  // Get form details
  getForm: async (formId: number): Promise<FormDetail> => {
    const response = await api.get<FormDetail>(`/api/forms/${formId}`);
    return response.data;
  },

  // Re-extract form
  reExtractForm: async (formId: number, ocrProvider?: string): Promise<FormExtractionResponse> => {
    const response = await api.post<FormExtractionResponse>(`/api/forms/${formId}/extract`, null, {
      params: ocrProvider ? { ocr_provider: ocrProvider } : undefined,
    });
    return response.data;
  },

  // Verify form
  verifyForm: async (formId: number, verification: FormVerification): Promise<FormDetail> => {
    const response = await api.put<FormDetail>(`/api/forms/${formId}/verify`, verification);
    return response.data;
  },

  // Update form (general update)
  updateForm: async (formId: number, verification: FormVerification, verify: boolean = false): Promise<FormDetail> => {
    const response = await api.put<FormDetail>(`/api/forms/${formId}?verify=${verify}`, verification);
    return response.data;
  },

  // Search forms
  searchForms: async (params: FormSearchQuery): Promise<FormDetail[]> => {
    const sanitizedParams = Object.fromEntries(
      Object.entries(params).filter(([, value]) => value !== undefined && value !== '')
    );
    const response = await api.get<FormDetail[]>('/api/forms/search/results', { params: sanitizedParams });
    return response.data;
  },

  // Export forms
  exportForms: async (format: 'csv' | 'json', filters?: FormSearchQuery): Promise<Blob> => {
    const params: Record<string, any> = { format };
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (key === 'page' || key === 'limit') {
          return;
        }
        if (value !== undefined && value !== '') {
          params[key] = value;
        }
      });
    }
    const response = await api.get(`/api/forms/export`, {
      params,
      responseType: 'blob',
    });
    return response.data;
  },

  // Delete form
  deleteForm: async (formId: number): Promise<void> => {
    await api.delete(`/api/forms/${formId}`);
  },

  // Upload multiple files for a form (multiple pages)
  uploadFormPages: async (files: File[], ocrProvider?: string): Promise<FormResponse> => {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });
    const response = await api.post<FormResponse>('/api/upload/pages', formData, {
      params: ocrProvider ? { ocr_provider: ocrProvider } : undefined,
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Document operations
  uploadDocument: async (
    file: File,
    documentCategory: DocumentCategory,
    description?: string,
    formId?: number,
    studentProfileId?: number
  ): Promise<Document> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_category', documentCategory);
    if (description) formData.append('description', description);
    if (formId) formData.append('form_id', formId.toString());
    if (studentProfileId) formData.append('student_profile_id', studentProfileId.toString());
    
    const response = await api.post<Document>('/api/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  getDocument: async (documentId: number): Promise<Document> => {
    const response = await api.get<Document>(`/api/documents/${documentId}`);
    return response.data;
  },

  getFormDocuments: async (formId: number): Promise<Document[]> => {
    const response = await api.get<Document[]>(`/api/documents/forms/${formId}/documents`);
    return response.data;
  },

  getStudentDocuments: async (profileId: number): Promise<Document[]> => {
    const response = await api.get<Document[]>(`/api/documents/students/${profileId}/documents`);
    return response.data;
  },

  searchDocuments: async (params: {
    document_category?: string;
    student_name?: string;
    form_id?: number;
    student_profile_id?: number;
    date_from?: string;
    date_to?: string;
    page?: number;
    limit?: number;
  }): Promise<Document[]> => {
    const response = await api.get<Document[]>('/api/documents/search/results', { params });
    return response.data;
  },

  deleteDocument: async (documentId: number): Promise<void> => {
    await api.delete(`/api/documents/${documentId}`);
  },

  getDocumentCategories: async (): Promise<{ categories: { value: string; name: string }[] }> => {
    const response = await api.get('/api/documents/categories/list');
    return response.data;
  },

  // Student profile operations
  listStudentProfiles: async (
    skip: number = 0,
    limit: number = 100,
    studentName?: string,
    rollNumber?: string,
    aadharNumber?: string,
    filters?: {
      phone_number?: string;
      email?: string;
      enrollment_number?: string;
      application_number?: string;
      course_applied?: string;
      gender?: string;
      category?: string;
      father_name?: string;
      mother_name?: string;
      city?: string;
      state?: string;
      pincode?: string;
    }
  ): Promise<StudentProfile[]> => {
    const params: any = { 
      skip, 
      limit, 
      student_name: studentName, 
      roll_number: rollNumber,
      aadhar_number: aadharNumber 
    };
    
    if (filters) {
      Object.assign(params, filters);
    }
    
    const response = await api.get<StudentProfile[]>('/api/students/', { params });
    return response.data;
  },

  getStudentProfile: async (profileId: number): Promise<StudentProfileDetail> => {
    const response = await api.get<StudentProfileDetail>(`/api/students/${profileId}`);
    return response.data;
  },

  createStudentProfile: async (
    studentName: string,
    rollNumber?: string,
    aadharNumber?: string
  ): Promise<StudentProfile> => {
    const response = await api.post<StudentProfile>('/api/students/', {
      student_name: studentName,
      roll_number: rollNumber,
      aadhar_number: aadharNumber,
    });
    return response.data;
  },

  updateStudentProfile: async (
    profileId: number,
    updateData: {
      student_name?: string;
      roll_number?: string;
      aadhar_number?: string;
    }
  ): Promise<StudentProfile> => {
    const response = await api.patch<StudentProfile>(`/api/students/${profileId}`, updateData);
    return response.data;
  },

  deleteStudentProfile: async (
    profileId: number,
    force: boolean = false
  ): Promise<void> => {
    await api.delete(`/api/students/${profileId}`, {
      params: { force },
    });
  },

  getStudentForms: async (profileId: number): Promise<FormDetail[]> => {
    const response = await api.get<FormDetail[]>(`/api/students/${profileId}/forms`);
    return response.data;
  },

  searchStudentProfiles: async (params: {
    student_name?: string;
    roll_number?: string;
    aadhar_number?: string;
    phone_number?: string;
    email?: string;
    enrollment_number?: string;
    application_number?: string;
    course_applied?: string;
    academic_session?: string;
    gender?: string;
    category?: string;
    father_name?: string;
    mother_name?: string;
    city?: string;
    state?: string;
    pincode?: string;
    page?: number;
    limit?: number;
    sort_by?: string;
    sort_order?: string;
  }): Promise<StudentProfile[]> => {
    const response = await api.get<StudentProfile[]>('/api/students/search/results', { params });
    return response.data;
  },

  // Export students
  exportStudentsCSV: async (params: {
    student_name?: string;
    roll_number?: string;
    aadhar_number?: string;
    phone_number?: string;
    email?: string;
    enrollment_number?: string;
    application_number?: string;
    course_applied?: string;
    academic_session?: string;
    gender?: string;
    category?: string;
    father_name?: string;
    mother_name?: string;
    city?: string;
    state?: string;
    pincode?: string;
    sort_by?: string;
    sort_order?: string;
  }): Promise<Blob> => {
    const response = await api.get('/api/students/export/csv', {
      params,
      responseType: 'blob',
    });
    return response.data;
  },

  exportStudentsExcel: async (params: {
    student_name?: string;
    roll_number?: string;
    aadhar_number?: string;
    phone_number?: string;
    email?: string;
    enrollment_number?: string;
    application_number?: string;
    course_applied?: string;
    academic_session?: string;
    gender?: string;
    category?: string;
    father_name?: string;
    mother_name?: string;
    city?: string;
    state?: string;
    pincode?: string;
    sort_by?: string;
    sort_order?: string;
  }): Promise<Blob> => {
    const response = await api.get('/api/students/export/excel', {
      params,
      responseType: 'blob',
    });
    return response.data;
  },

  // Import students
  importStudentsCSV: async (file: File): Promise<{ message: string; imported: number; errors: string[]; error_count: number }> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post('/api/students/import/csv', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  importStudentsExcel: async (file: File): Promise<{ message: string; imported: number; errors: string[]; error_count: number }> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post('/api/students/import/excel', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Batch upload operations
  batchUploadForms: async (
    files: File[],
    ocrProvider?: string,
    pagesPerForm: number = 3
  ): Promise<{ job_id: string; total_files: number; status: string; message: string }> => {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });
    if (ocrProvider) formData.append('ocr_provider', ocrProvider);
    formData.append('pages_per_form', pagesPerForm.toString());
    
    const response = await api.post('/api/batch-upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  getBatchJobStatus: async (jobId: string): Promise<any> => {
    const response = await api.get(`/api/batch-upload/${jobId}/status`);
    return response.data;
  },

  getBatchJobResults: async (jobId: string, page: number = 1, limit: number = 50): Promise<any> => {
    const response = await api.get(`/api/batch-upload/${jobId}/results`, {
      params: { page, limit },
    });
    return response.data;
  },

  cancelBatchJob: async (jobId: string): Promise<void> => {
    await api.delete(`/api/batch-upload/${jobId}`);
  },

  listBatchJobs: async (status?: string, limit: number = 20): Promise<any> => {
    const response = await api.get('/api/batch-upload/jobs/list', {
      params: { status, limit },
    });
    return response.data;
  },

  // Document download/preview
  downloadDocument: async (documentId: number): Promise<Blob> => {
    const response = await api.get(`/api/documents/${documentId}/download`, {
      responseType: 'blob',
    });
    return response.data;
  },

  previewDocument: async (documentId: number): Promise<Blob> => {
    const response = await api.get(`/api/documents/${documentId}/preview`, {
      responseType: 'blob',
    });
    return response.data;
  },

  bulkUploadDocuments: async (
    files: File[],
    documentCategory: DocumentCategory,
    studentProfileId?: number,
    formId?: number
  ): Promise<Document[]> => {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });
    formData.append('document_category', documentCategory);
    if (studentProfileId) formData.append('student_profile_id', studentProfileId.toString());
    if (formId) formData.append('form_id', formId.toString());
    
    const response = await api.post<Document[]>('/api/documents/bulk-upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Annotation operations
  saveAnnotation: async (formId: number, annotation: any): Promise<any> => {
    const response = await api.post(`/api/annotate/${formId}`, annotation);
    return response.data;
  },

  getAnnotation: async (formId: number): Promise<any> => {
    const response = await api.get(`/api/annotate/${formId}`);
    return response.data;
  },

  exportTrainingData: async (format: 'json' | 'coco' | 'yolo' = 'json'): Promise<any> => {
    const response = await api.get('/api/export/training-data', {
      params: { format },
    });
    return response.data;
  },

  // Training operations
  getTrainingStats: async (): Promise<any> => {
    const response = await api.get('/api/training/stats');
    return response.data;
  },

  prepareTrainingData: async (format: 'trocr' | 'donut' | 'both' = 'both', split: boolean = true): Promise<any> => {
    const response = await api.post('/api/training/prepare-data', null, {
      params: { format, split },
    });
    return response.data;
  },

  startTraining: async (config: {
    model_type?: string;
    base_model?: string;
    epochs?: number;
    batch_size?: number;
    learning_rate?: number;
  }): Promise<any> => {
    const response = await api.post('/api/training/start', config);
    return response.data;
  },

  getTrainingJobStatus: async (jobId: string): Promise<any> => {
    const response = await api.get(`/api/training/job/${jobId}`);
    return response.data;
  },

  getUnannotatedForms: async (limit: number = 50, offset: number = 0): Promise<any> => {
    const response = await api.get('/api/training/forms/unannotated', {
      params: { limit, offset },
    });
    return response.data;
  },

  getImprovementStats: async (): Promise<any> => {
    const response = await api.get('/api/training/improvement-stats');
    return response.data;
  },

  triggerRetraining: async (config: {
    epochs?: number;
    batch_size?: number;
    learning_rate?: number;
    base_model?: string;
  }): Promise<any> => {
    const response = await api.post('/api/training/trigger-retraining', config);
    return response.data;
  },
};

export default api;

