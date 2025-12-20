import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 120000, // 120 second timeout for OCR processing
});

export interface OCRProvider {
  providers: string[];
  default: string;
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
  student_name?: string;
  date_of_birth?: string;
  gender?: string;
  category?: string;
  nationality?: string;
  religion?: string;
  aadhar_number?: string;
  blood_group?: string;
  permanent_address?: string;
  correspondence_address?: string;
  pincode?: string;
  city?: string;
  state?: string;
  phone_number?: string;
  alternate_phone?: string;
  email?: string;
  emergency_contact_name?: string;
  emergency_contact_phone?: string;
  father_name?: string;
  father_occupation?: string;
  father_phone?: string;
  mother_name?: string;
  mother_occupation?: string;
  mother_phone?: string;
  guardian_name?: string;
  guardian_relation?: string;
  guardian_phone?: string;
  annual_income?: string;
  tenth_board?: string;
  tenth_year?: string;
  tenth_percentage?: string;
  tenth_school?: string;
  twelfth_board?: string;
  twelfth_year?: string;
  twelfth_percentage?: string;
  twelfth_school?: string;
  previous_qualification?: string;
  graduation_details?: string;
  course_applied?: string;
  application_number?: string;
  enrollment_number?: string;
  admission_date?: string;
  additional_info?: any;
  verified_date?: string;
}

export interface FormVerification {
  student_name?: string;
  date_of_birth?: string;
  gender?: string;
  category?: string;
  nationality?: string;
  religion?: string;
  aadhar_number?: string;
  blood_group?: string;
  permanent_address?: string;
  correspondence_address?: string;
  pincode?: string;
  city?: string;
  state?: string;
  phone_number?: string;
  alternate_phone?: string;
  email?: string;
  emergency_contact_name?: string;
  emergency_contact_phone?: string;
  father_name?: string;
  father_occupation?: string;
  father_phone?: string;
  mother_name?: string;
  mother_occupation?: string;
  mother_phone?: string;
  guardian_name?: string;
  guardian_relation?: string;
  guardian_phone?: string;
  annual_income?: string;
  tenth_board?: string;
  tenth_year?: string;
  tenth_percentage?: string;
  tenth_school?: string;
  twelfth_board?: string;
  twelfth_year?: string;
  twelfth_percentage?: string;
  twelfth_school?: string;
  previous_qualification?: string;
  graduation_details?: string;
  course_applied?: string;
  application_number?: string;
  enrollment_number?: string;
  admission_date?: string;
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

export const apiService = {
  uploadForm: async (file: File, ocrProvider?: string): Promise<FormResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post<FormResponse>('/api/upload', formData, {
      params: ocrProvider ? { ocr_provider: ocrProvider } : undefined,
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  getProviders: async (): Promise<OCRProvider> => {
    try {
      const response = await api.get<OCRProvider>('/api/providers');
      return response.data;
    } catch (error) {
      return { providers: ['tesseract'], default: 'tesseract' };
    }
  },

  listForms: async (skip: number = 0, limit: number = 20, status?: string): Promise<FormDetail[]> => {
    const response = await api.get<FormDetail[]>('/api/forms/', {
      params: { skip, limit, status },
    });
    return response.data;
  },

  getForm: async (formId: number): Promise<FormDetail> => {
    const response = await api.get<FormDetail>(`/api/forms/${formId}`);
    return response.data;
  },

  reExtractForm: async (formId: number, ocrProvider?: string): Promise<FormExtractionResponse> => {
    const response = await api.post<FormExtractionResponse>(`/api/forms/${formId}/extract`, null, {
      params: ocrProvider ? { ocr_provider: ocrProvider } : undefined,
    });
    return response.data;
  },

  verifyForm: async (formId: number, verification: FormVerification): Promise<FormDetail> => {
    const response = await api.put<FormDetail>(`/api/forms/${formId}/verify`, verification);
    return response.data;
  },

  updateForm: async (formId: number, verification: FormVerification): Promise<FormDetail> => {
    const response = await api.put<FormDetail>(`/api/forms/${formId}`, verification);
    return response.data;
  },

  searchForms: async (params: FormSearchQuery): Promise<FormDetail[]> => {
    const sanitizedParams = Object.fromEntries(
      Object.entries(params).filter(([, value]) => value !== undefined && value !== '')
    );
    const response = await api.get<FormDetail[]>('/api/forms/search/results', { params: sanitizedParams });
    return response.data;
  },

  exportForms: async (format: 'csv' | 'json', filters?: FormSearchQuery): Promise<Blob> => {
    const params: Record<string, any> = { format };
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (key !== 'page' && key !== 'limit' && value !== undefined && value !== '') {
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

  deleteForm: async (formId: number): Promise<void> => {
    await api.delete(`/api/forms/${formId}`);
  },

  uploadFormPages: async (files: File[], ocrProvider?: string): Promise<FormResponse> => {
    const formData = new FormData();
    files.forEach((file) => formData.append('files', file));
    const response = await api.post<FormResponse>('/api/upload/pages', formData, {
      params: ocrProvider ? { ocr_provider: ocrProvider } : undefined,
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

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
      headers: { 'Content-Type': 'multipart/form-data' },
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

  searchDocuments: async (params: any): Promise<Document[]> => {
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

  listStudentProfiles: async (skip: number = 0, limit: number = 100, studentName?: string, rollNumber?: string, aadharNumber?: string, filters?: any): Promise<StudentProfile[]> => {
    const params: any = { skip, limit, student_name: studentName, roll_number: rollNumber, aadhar_number: aadharNumber };
    if (filters) Object.assign(params, filters);
    const response = await api.get<StudentProfile[]>('/api/students/', { params });
    return response.data;
  },

  getStudentProfile: async (profileId: number): Promise<StudentProfileDetail> => {
    const response = await api.get<StudentProfileDetail>(`/api/students/${profileId}`);
    return response.data;
  },

  createStudentProfile: async (studentName: string, aadharNumber?: string): Promise<StudentProfile> => {
    const response = await api.post<StudentProfile>('/api/students/', null, {
      params: { student_name: studentName, aadhar_number: aadharNumber },
    });
    return response.data;
  },

  getStudentForms: async (profileId: number): Promise<FormDetail[]> => {
    const response = await api.get<FormDetail[]>(`/api/students/${profileId}/forms`);
    return response.data;
  },

  searchStudentProfiles: async (params: any): Promise<StudentProfile[]> => {
    const response = await api.get<StudentProfile[]>('/api/students/search/results', { params });
    return response.data;
  },

  batchUploadForms: async (files: File[], ocrProvider?: string, pagesPerForm: number = 3): Promise<any> => {
    const formData = new FormData();
    files.forEach((file) => formData.append('files', file));
    if (ocrProvider) formData.append('ocr_provider', ocrProvider);
    formData.append('pages_per_form', pagesPerForm.toString());
    const response = await api.post('/api/batch-upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  getBatchJobStatus: async (jobId: string): Promise<any> => {
    const response = await api.get(`/api/batch-upload/${jobId}/status`);
    return response.data;
  },

  getBatchJobResults: async (jobId: string, page: number = 1, limit: number = 50): Promise<any> => {
    const response = await api.get(`/api/batch-upload/${jobId}/results`, { params: { page, limit } });
    return response.data;
  },

  cancelBatchJob: async (jobId: string): Promise<void> => {
    await api.delete(`/api/batch-upload/${jobId}`);
  },

  listBatchJobs: async (status?: string, limit: number = 20): Promise<any> => {
    const response = await api.get('/api/batch-upload/jobs/list', { params: { status, limit } });
    return response.data;
  },

  downloadDocument: async (documentId: number): Promise<Blob> => {
    const response = await api.get(`/api/documents/${documentId}/download`, { responseType: 'blob' });
    return response.data;
  },

  previewDocument: async (documentId: number): Promise<Blob> => {
    const response = await api.get(`/api/documents/${documentId}/preview`, { responseType: 'blob' });
    return response.data;
  },

  bulkUploadDocuments: async (files: File[], documentCategory: DocumentCategory, studentProfileId?: number, formId?: number): Promise<Document[]> => {
    const formData = new FormData();
    files.forEach((file) => formData.append('files', file));
    formData.append('document_category', documentCategory);
    if (studentProfileId) formData.append('student_profile_id', studentProfileId.toString());
    if (formId) formData.append('form_id', formId.toString());
    const response = await api.post<Document[]>('/api/documents/bulk-upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  saveAnnotation: async (formId: number, annotation: any): Promise<any> => {
    const response = await api.post(`/api/annotate/${formId}`, annotation);
    return response.data;
  },

  getAnnotation: async (formId: number): Promise<any> => {
    const response = await api.get(`/api/annotate/${formId}`);
    return response.data;
  },

  exportTrainingData: async (format: 'json' | 'coco' | 'yolo' = 'json'): Promise<any> => {
    const response = await api.get('/api/export/training-data', { params: { format } });
    return response.data;
  },
};

export default api;
