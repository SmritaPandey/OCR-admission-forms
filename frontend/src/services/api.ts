import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
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

export interface ExtractedData {
  raw_text: string;
  confidence?: number;
  structured_data?: any;
  provider?: string;
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
  // Basic Details
  student_name?: string;
  date_of_birth?: string;
  gender?: string;
  category?: string;
  nationality?: string;
  religion?: string;
  aadhar_number?: string;
  blood_group?: string;
  // Address Details
  permanent_address?: string;
  correspondence_address?: string;
  pincode?: string;
  city?: string;
  state?: string;
  // Contact Details
  phone_number?: string;
  alternate_phone?: string;
  email?: string;
  emergency_contact_name?: string;
  emergency_contact_phone?: string;
  // Guardian/Parent Details
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
  // Educational Qualifications
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
  // Course Application Details
  course_applied?: string;
  application_number?: string;
  admission_date?: string;
  additional_info?: any;
  verified_date?: string;
}

export interface FormVerification {
  // Basic Details
  student_name?: string;
  date_of_birth?: string;
  gender?: string;
  category?: string;
  nationality?: string;
  religion?: string;
  aadhar_number?: string;
  blood_group?: string;
  
  // Address Details
  permanent_address?: string;
  correspondence_address?: string;
  pincode?: string;
  city?: string;
  state?: string;
  
  // Contact Details
  phone_number?: string;
  alternate_phone?: string;
  email?: string;
  emergency_contact_name?: string;
  emergency_contact_phone?: string;
  
  // Guardian/Parent Details
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
  
  // Educational Qualifications
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
  
  // Course Application Details
  course_applied?: string;
  application_number?: string;
  admission_date?: string;
  
  additional_info?: any;
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
    const response = await api.get<OCRProvider>('/api/providers');
    return response.data;
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
  reExtractForm: async (formId: number, ocrProvider?: string): Promise<any> => {
    const response = await api.post(`/api/forms/${formId}/extract`, null, {
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
  updateForm: async (formId: number, verification: FormVerification): Promise<FormDetail> => {
    const response = await api.put<FormDetail>(`/api/forms/${formId}`, verification);
    return response.data;
  },

  // Search forms
  searchForms: async (params: {
    student_name?: string;
    phone_number?: string;
    email?: string;
    course_applied?: string;
    status?: string;
    page?: number;
    limit?: number;
  }): Promise<FormDetail[]> => {
    const response = await api.get<FormDetail[]>('/api/forms/search/results', { params });
    return response.data;
  },

  // Export forms
  exportForms: async (format: 'csv' | 'json', status?: string): Promise<Blob> => {
    const response = await api.get(`/api/forms/export`, {
      params: { format, status },
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
    limit: number = 20,
    studentName?: string,
    aadharNumber?: string
  ): Promise<StudentProfile[]> => {
    const response = await api.get<StudentProfile[]>('/api/students/', {
      params: { skip, limit, student_name: studentName, aadhar_number: aadharNumber },
    });
    return response.data;
  },

  getStudentProfile: async (profileId: number): Promise<StudentProfileDetail> => {
    const response = await api.get<StudentProfileDetail>(`/api/students/${profileId}`);
    return response.data;
  },

  createStudentProfile: async (
    studentName: string,
    aadharNumber?: string
  ): Promise<StudentProfile> => {
    const response = await api.post<StudentProfile>('/api/students/', null, {
      params: { student_name: studentName, aadhar_number: aadharNumber },
    });
    return response.data;
  },

  getStudentForms: async (profileId: number): Promise<FormDetail[]> => {
    const response = await api.get<FormDetail[]>(`/api/students/${profileId}/forms`);
    return response.data;
  },

  searchStudentProfiles: async (params: {
    student_name?: string;
    aadhar_number?: string;
    page?: number;
    limit?: number;
  }): Promise<StudentProfile[]> => {
    const response = await api.get<StudentProfile[]>('/api/students/search/results', { params });
    return response.data;
  },
};

export default api;

