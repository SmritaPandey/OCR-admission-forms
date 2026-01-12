"use client";

import { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { apiService, FormDetail, FormVerification, OCRProvider } from '@/lib/api';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Checkbox } from "@/components/ui/checkbox";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  CheckCircle2,
  RefreshCw,
  ChevronLeft,
  Save,
  FileSearch,
  ExternalLink,
  AlertTriangle,
  User,
  MapPin,
  Phone,
  Users,
  GraduationCap,
  FileText,
  ClipboardCheck,
  Award,
  Calculator
} from "lucide-react";
import { toast } from "sonner";

// Form field component for consistency
function FormField({ label, field, value, onChange, placeholder, type = "text" }: {
  label: string;
  field: string;
  value: string;
  onChange: (field: string, value: string) => void;
  placeholder?: string;
  type?: string;
}) {
  return (
    <div className="space-y-1.5">
      <Label className="text-xs text-muted-foreground">{label}</Label>
      <Input
        type={type}
        value={value}
        onChange={(e) => onChange(field, e.target.value)}
        placeholder={placeholder || label}
        className="h-9"
      />
    </div>
  );
}

// Checkbox field component for document checklist
function CheckboxField({ label, field, checked, onChange }: {
  label: string;
  field: string;
  checked: boolean;
  onChange: (field: string, value: string) => void;
}) {
  return (
    <div className="flex items-center space-x-2">
      <Checkbox
        id={field}
        checked={checked}
        onCheckedChange={(c) => onChange(field, c ? 'Yes' : 'No')}
      />
      <label htmlFor={field} className="text-sm cursor-pointer">{label}</label>
    </div>
  );
}

export default function VerificationPage() {
  const { id } = useParams();
  const router = useRouter();
  const formId = parseInt(id as string);

  const [form, setForm] = useState<FormDetail | null>(null);
  const [editedData, setEditedData] = useState<FormVerification>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [reExtracting, setReExtracting] = useState(false);
  const [providers, setProviders] = useState<string[]>([]);
  const [selectedProvider, setSelectedProvider] = useState<string>('');

  // Initialize form data from extracted structured data
  const initializeFormData = useCallback((formData: FormDetail) => {
    const verificationData: FormVerification = {};

    // First, copy direct form fields
    const directFields = [
      'student_name', 'first_name', 'middle_name', 'surname',
      'date_of_birth', 'gender', 'category', 'nationality', 'religion',
      'aadhar_number', 'blood_group', 'below_poverty_line', 'minority_category',
      'academic_session', 'course', 'admission_category', 'admission_category_other',
      'du_portal_form_number', 'cuet_score', 'college_roll_no', 'date_of_admission',
      'course_applied', 'application_number', 'enrollment_number', 'admission_date',
      'du_enrollment_number', 'hindi_medium_preference',
      'permanent_address', 'permanent_address_line1', 'permanent_address_line2',
      'permanent_address_line3', 'permanent_state', 'permanent_pincode',
      'correspondence_address', 'correspondence_address_line1', 'correspondence_address_line2',
      'correspondence_address_line3', 'correspondence_state', 'correspondence_pincode',
      'pincode', 'city', 'state',
      'phone_number', 'alternate_phone', 'email',
      'emergency_contact_name', 'emergency_contact_phone',
      'mother_name', 'mother_occupation', 'mother_designation', 'mother_organization',
      'mother_email', 'mother_mobile', 'mother_phone',
      'father_name', 'father_occupation', 'father_designation', 'father_organization',
      'father_email', 'father_mobile', 'father_phone',
      'guardian_name', 'guardian_relation', 'guardian_residential_address',
      'guardian_organization', 'guardian_email', 'guardian_mobile', 'guardian_phone',
      'annual_income',
      'tenth_board', 'tenth_year', 'tenth_percentage', 'tenth_school',
      'twelfth_board', 'twelfth_year', 'twelfth_percentage', 'twelfth_school',
      'twelfth_roll_number', 'twelfth_institution', 'hindi_studied_upto',
      'previous_qualification', 'graduation_details',
      'category_certificate_authority', 'category_certificate_number', 'category_certificate_date',
      'disability_percentage', 'disability_type', 'udid_number',
      'doc_admission_form', 'doc_undertaking_ragging', 'doc_photographs',
      'doc_cuet_scorecard', 'doc_class_xii_marksheet', 'doc_class_x_certificate',
      'doc_class_xii_certificate', 'doc_character_certificate', 'doc_transfer_certificate',
      'doc_hindi_certificate', 'doc_caste_certificate', 'doc_sports_eca',
      'doc_originals', 'doc_photo_id'
    ];

    // Copy direct form fields
    directFields.forEach(field => {
      const value = (formData as any)[field];
      if (value !== undefined && value !== null) {
        (verificationData as any)[field] = String(value);
      }
    });

    // Then, overlay with structured data from OCR (these are more up-to-date)
    const structuredData = formData.extracted_data?.structured_data || {};
    Object.keys(structuredData).forEach(key => {
      const value = structuredData[key];
      if (value !== undefined && value !== null && value !== '') {
        (verificationData as any)[key] = String(value);
      }
    });

    return verificationData;
  }, []);

  useEffect(() => {
    loadForm();
    loadProviders();
  }, [formId]);

  const loadForm = async () => {
    try {
      setLoading(true);
      const data = await apiService.getForm(formId);
      setForm(data);
      setEditedData(initializeFormData(data));
      setSelectedProvider(data.ocr_provider);
    } catch (error) {
      toast.error("Failed to load form details");
    } finally {
      setLoading(false);
    }
  };

  const loadProviders = async () => {
    try {
      const data = await apiService.getProviders();
      setProviders(data.providers);
    } catch (error) { }
  };

  const handleInputChange = (field: string, value: string) => {
    setEditedData(prev => ({ ...prev, [field]: value }));
  };

  const handleVerify = async () => {
    try {
      setSaving(true);
      await apiService.verifyForm(formId, editedData);
      toast.success("Record verified and saved successfully");
      loadForm();
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Verification failed");
    } finally {
      setSaving(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      await apiService.updateForm(formId, editedData);
      toast.success("Changes saved");
      loadForm();
    } catch (error) {
      toast.error("Failed to save changes");
    } finally {
      setSaving(false);
    }
  };

  const handleReExtract = async () => {
    try {
      setReExtracting(true);
      await apiService.reExtractForm(formId, selectedProvider);
      toast.success("Re-extraction complete");
      loadForm();
    } catch (error) {
      toast.error("Re-extraction failed");
    } finally {
      setReExtracting(false);
    }
  };

  // Get field value with fallback
  const getField = (field: string): string => {
    return (editedData as any)[field] || '';
  };

  // Check if document is attached
  const isDocChecked = (field: string): boolean => {
    const value = (editedData as any)[field];
    return value === 'Yes' || value === 'yes' || value === true || value === 'true';
  };

  if (loading) {
    return <div className="flex h-[80vh] items-center justify-center animate-pulse text-muted-foreground">Loading extraction results...</div>;
  }

  if (!form) return <div>Form not found</div>;

  const imageUrl = `http://localhost:8000/${form.file_path}`;
  const confidence = form.extracted_data?.confidence || 0;

  return (
    <div className="space-y-4 p-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ChevronLeft className="h-5 w-5" />
          </Button>
          <div>
            <h2 className="text-xl font-bold tracking-tight">{form.filename}</h2>
            <p className="text-xs text-muted-foreground">
              {form.ocr_provider} • Confidence: {confidence.toFixed(1)}% • {new Date(form.upload_date).toLocaleString()}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <select
            className="text-sm border rounded px-2 py-1"
            value={selectedProvider}
            onChange={(e) => setSelectedProvider(e.target.value)}
          >
            {providers.map(p => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
          <Button variant="outline" size="sm" onClick={handleReExtract} disabled={reExtracting}>
            {reExtracting ? <RefreshCw className="mr-1 h-3 w-3 animate-spin" /> : <RefreshCw className="mr-1 h-3 w-3" />}
            Re-Extract
          </Button>
          <Button variant="outline" size="sm" onClick={handleSave} disabled={saving}>
            <Save className="mr-1 h-3 w-3" />
            Save
          </Button>
          <Button size="sm" onClick={handleVerify} disabled={saving}>
            {saving ? <RefreshCw className="mr-1 h-3 w-3 animate-spin" /> : <CheckCircle2 className="mr-1 h-3 w-3" />}
            Verify & Finalize
          </Button>
        </div>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 h-[calc(100vh-140px)]">
        {/* Left Side: Document Preview */}
        <Card className="overflow-hidden flex flex-col">
          <CardHeader className="py-2 px-3 border-b">
            <CardTitle className="text-sm font-medium flex items-center justify-between">
              Original Scan
              <Button variant="ghost" size="sm" asChild>
                <a href={imageUrl} target="_blank" rel="noreferrer">
                  <ExternalLink className="h-3 w-3 mr-1" /> Full View
                </a>
              </Button>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0 flex-1 bg-zinc-100 relative overflow-auto">
            {/* Loading skeleton with shimmer animation */}
            <div
              id="image-skeleton"
              className="absolute inset-0 bg-gradient-to-r from-zinc-200 via-zinc-100 to-zinc-200 animate-pulse"
              style={{
                backgroundSize: '200% 100%',
                animation: 'shimmer 1.5s infinite linear',
              }}
            >
              <div className="h-full flex flex-col items-center justify-center text-muted-foreground">
                <FileSearch className="h-12 w-12 mb-3 opacity-50 animate-pulse" />
                <p className="text-sm font-medium">Loading document...</p>
                <p className="text-xs mt-1 opacity-70">Please wait while the scan loads</p>
              </div>
            </div>
            <img
              src={imageUrl}
              alt="Form Scan"
              className="max-w-none w-full shadow-lg relative z-10"
              onLoad={(e) => {
                // Hide skeleton when image loads
                const skeleton = document.getElementById('image-skeleton');
                if (skeleton) skeleton.style.display = 'none';
              }}
              onError={(e) => {
                // Show error state
                const skeleton = document.getElementById('image-skeleton');
                if (skeleton) {
                  skeleton.innerHTML = '<div class="h-full flex flex-col items-center justify-center text-red-500"><p class="text-sm font-medium">Failed to load document</p><p class="text-xs mt-1">Please try refreshing the page</p></div>';
                }
              }}
            />
          </CardContent>
        </Card>

        {/* Right Side: Form Fields */}
        <Card className="flex flex-col overflow-hidden">
          <CardHeader className="py-2 px-3 border-b">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-medium">Extracted Data ({Object.keys(editedData).filter(k => editedData[k as keyof FormVerification]).length} fields)</CardTitle>
              {form.status === 'verified' && (
                <div className="flex items-center text-emerald-600 text-xs font-bold bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-100">
                  <CheckCircle2 className="h-3 w-3 mr-1" /> VERIFIED
                </div>
              )}
            </div>
          </CardHeader>

          <ScrollArea className="flex-1">
            <Tabs defaultValue="personal" className="w-full">
              <div className="border-b px-2 sticky top-0 bg-white z-10">
                <TabsList className="bg-transparent h-10 gap-1 flex-wrap">
                  <TabsTrigger value="personal" className="text-xs px-2 py-1 data-[state=active]:bg-primary/10">
                    <User className="h-3 w-3 mr-1" />Personal
                  </TabsTrigger>
                  <TabsTrigger value="address" className="text-xs px-2 py-1 data-[state=active]:bg-primary/10">
                    <MapPin className="h-3 w-3 mr-1" />Address
                  </TabsTrigger>
                  <TabsTrigger value="contact" className="text-xs px-2 py-1 data-[state=active]:bg-primary/10">
                    <Phone className="h-3 w-3 mr-1" />Contact
                  </TabsTrigger>
                  <TabsTrigger value="parents" className="text-xs px-2 py-1 data-[state=active]:bg-primary/10">
                    <Users className="h-3 w-3 mr-1" />Parents
                  </TabsTrigger>
                  <TabsTrigger value="education" className="text-xs px-2 py-1 data-[state=active]:bg-primary/10">
                    <GraduationCap className="h-3 w-3 mr-1" />Education
                  </TabsTrigger>
                  <TabsTrigger value="cuet" className="text-xs px-2 py-1 data-[state=active]:bg-primary/10">
                    <Calculator className="h-3 w-3 mr-1" />CUET
                  </TabsTrigger>
                  <TabsTrigger value="admission" className="text-xs px-2 py-1 data-[state=active]:bg-primary/10">
                    <Award className="h-3 w-3 mr-1" />Admission
                  </TabsTrigger>
                  <TabsTrigger value="documents" className="text-xs px-2 py-1 data-[state=active]:bg-primary/10">
                    <ClipboardCheck className="h-3 w-3 mr-1" />Docs
                  </TabsTrigger>
                </TabsList>
              </div>

              <div className="p-4 space-y-4">
                {/* Personal Details Tab */}
                <TabsContent value="personal" className="m-0 space-y-4">
                  <div className="grid grid-cols-3 gap-3">
                    <FormField label="First Name" field="first_name" value={getField('first_name')} onChange={handleInputChange} />
                    <FormField label="Middle Name" field="middle_name" value={getField('middle_name')} onChange={handleInputChange} />
                    <FormField label="Surname" field="surname" value={getField('surname')} onChange={handleInputChange} />
                  </div>
                  <FormField label="Full Name" field="student_name" value={getField('student_name')} onChange={handleInputChange} />
                  <div className="grid grid-cols-2 gap-3">
                    <FormField label="Date of Birth" field="date_of_birth" value={getField('date_of_birth')} onChange={handleInputChange} placeholder="DD/MM/YYYY" />
                    <FormField label="Gender" field="gender" value={getField('gender')} onChange={handleInputChange} />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <FormField label="Category" field="category" value={getField('category')} onChange={handleInputChange} />
                    <FormField label="Admission Category" field="admission_category" value={getField('admission_category')} onChange={handleInputChange} />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <FormField label="Nationality" field="nationality" value={getField('nationality')} onChange={handleInputChange} />
                    <FormField label="Religion" field="religion" value={getField('religion')} onChange={handleInputChange} />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <FormField label="Blood Group" field="blood_group" value={getField('blood_group')} onChange={handleInputChange} />
                    <FormField label="Aadhar Number" field="aadhar_number" value={getField('aadhar_number')} onChange={handleInputChange} placeholder="12 digits" />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <FormField label="Below Poverty Line" field="below_poverty_line" value={getField('below_poverty_line')} onChange={handleInputChange} />
                    <FormField label="Minority Category" field="minority_category" value={getField('minority_category')} onChange={handleInputChange} />
                  </div>
                </TabsContent>

                {/* Address Tab */}
                <TabsContent value="address" className="m-0 space-y-4">
                  <div className="space-y-3">
                    <h4 className="font-semibold text-sm text-primary border-b pb-1">Permanent Address</h4>
                    <FormField label="Address Line 1" field="permanent_address_line1" value={getField('permanent_address_line1')} onChange={handleInputChange} />
                    <FormField label="Address Line 2" field="permanent_address_line2" value={getField('permanent_address_line2')} onChange={handleInputChange} />
                    <FormField label="Address Line 3" field="permanent_address_line3" value={getField('permanent_address_line3')} onChange={handleInputChange} />
                    <div className="grid grid-cols-2 gap-3">
                      <FormField label="State" field="permanent_state" value={getField('permanent_state')} onChange={handleInputChange} />
                      <FormField label="PIN Code" field="permanent_pincode" value={getField('permanent_pincode')} onChange={handleInputChange} placeholder="6 digits" />
                    </div>
                  </div>
                  <div className="space-y-3">
                    <h4 className="font-semibold text-sm text-primary border-b pb-1">Correspondence Address</h4>
                    <FormField label="Address Line 1" field="correspondence_address_line1" value={getField('correspondence_address_line1')} onChange={handleInputChange} />
                    <FormField label="Address Line 2" field="correspondence_address_line2" value={getField('correspondence_address_line2')} onChange={handleInputChange} />
                    <FormField label="Address Line 3" field="correspondence_address_line3" value={getField('correspondence_address_line3')} onChange={handleInputChange} />
                    <div className="grid grid-cols-2 gap-3">
                      <FormField label="State" field="correspondence_state" value={getField('correspondence_state')} onChange={handleInputChange} />
                      <FormField label="PIN Code" field="correspondence_pincode" value={getField('correspondence_pincode')} onChange={handleInputChange} placeholder="6 digits" />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <FormField label="City" field="city" value={getField('city')} onChange={handleInputChange} />
                    <FormField label="State" field="state" value={getField('state')} onChange={handleInputChange} />
                  </div>
                </TabsContent>

                {/* Contact Tab */}
                <TabsContent value="contact" className="m-0 space-y-4">
                  <div className="grid grid-cols-2 gap-3">
                    <FormField label="Phone Number" field="phone_number" value={getField('phone_number')} onChange={handleInputChange} placeholder="10 digits" />
                    <FormField label="Alternate Phone" field="alternate_phone" value={getField('alternate_phone')} onChange={handleInputChange} />
                  </div>
                  <FormField label="Email Address" field="email" value={getField('email')} onChange={handleInputChange} type="email" />
                  <div className="grid grid-cols-2 gap-3">
                    <FormField label="Emergency Contact Name" field="emergency_contact_name" value={getField('emergency_contact_name')} onChange={handleInputChange} />
                    <FormField label="Emergency Contact Phone" field="emergency_contact_phone" value={getField('emergency_contact_phone')} onChange={handleInputChange} />
                  </div>
                </TabsContent>

                {/* Parents Tab */}
                <TabsContent value="parents" className="m-0 space-y-4">
                  {/* Mother's Details */}
                  <div className="space-y-3">
                    <h4 className="font-semibold text-sm text-primary border-b pb-1">Mother's Details</h4>
                    <FormField label="Name" field="mother_name" value={getField('mother_name')} onChange={handleInputChange} />
                    <div className="grid grid-cols-2 gap-3">
                      <FormField label="Occupation" field="mother_occupation" value={getField('mother_occupation')} onChange={handleInputChange} />
                      <FormField label="Designation" field="mother_designation" value={getField('mother_designation')} onChange={handleInputChange} />
                    </div>
                    <FormField label="Organization & Address" field="mother_organization" value={getField('mother_organization')} onChange={handleInputChange} />
                    <div className="grid grid-cols-2 gap-3">
                      <FormField label="Email" field="mother_email" value={getField('mother_email')} onChange={handleInputChange} type="email" />
                      <FormField label="Mobile" field="mother_mobile" value={getField('mother_mobile')} onChange={handleInputChange} />
                    </div>
                  </div>

                  {/* Father's Details */}
                  <div className="space-y-3">
                    <h4 className="font-semibold text-sm text-primary border-b pb-1">Father's Details</h4>
                    <FormField label="Name" field="father_name" value={getField('father_name')} onChange={handleInputChange} />
                    <div className="grid grid-cols-2 gap-3">
                      <FormField label="Occupation" field="father_occupation" value={getField('father_occupation')} onChange={handleInputChange} />
                      <FormField label="Designation" field="father_designation" value={getField('father_designation')} onChange={handleInputChange} />
                    </div>
                    <FormField label="Organization & Address" field="father_organization" value={getField('father_organization')} onChange={handleInputChange} />
                    <div className="grid grid-cols-2 gap-3">
                      <FormField label="Email" field="father_email" value={getField('father_email')} onChange={handleInputChange} type="email" />
                      <FormField label="Mobile" field="father_mobile" value={getField('father_mobile')} onChange={handleInputChange} />
                    </div>
                  </div>

                  {/* Guardian Details */}
                  <div className="space-y-3">
                    <h4 className="font-semibold text-sm text-primary border-b pb-1">Local Guardian's Details</h4>
                    <div className="grid grid-cols-2 gap-3">
                      <FormField label="Name" field="guardian_name" value={getField('guardian_name')} onChange={handleInputChange} />
                      <FormField label="Relation" field="guardian_relation" value={getField('guardian_relation')} onChange={handleInputChange} />
                    </div>
                    <FormField label="Residential Address" field="guardian_residential_address" value={getField('guardian_residential_address')} onChange={handleInputChange} />
                    <FormField label="Organization & Address" field="guardian_organization" value={getField('guardian_organization')} onChange={handleInputChange} />
                    <div className="grid grid-cols-2 gap-3">
                      <FormField label="Email" field="guardian_email" value={getField('guardian_email')} onChange={handleInputChange} type="email" />
                      <FormField label="Mobile" field="guardian_mobile" value={getField('guardian_mobile')} onChange={handleInputChange} />
                    </div>
                  </div>

                  <FormField label="Annual Family Income" field="annual_income" value={getField('annual_income')} onChange={handleInputChange} />
                </TabsContent>

                {/* Education Tab */}
                <TabsContent value="education" className="m-0 space-y-4">
                  {/* Class X */}
                  <div className="space-y-3">
                    <h4 className="font-semibold text-sm text-primary border-b pb-1">Class X Details</h4>
                    <div className="grid grid-cols-2 gap-3">
                      <FormField label="Board" field="tenth_board" value={getField('tenth_board')} onChange={handleInputChange} />
                      <FormField label="Year" field="tenth_year" value={getField('tenth_year')} onChange={handleInputChange} />
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <FormField label="Percentage" field="tenth_percentage" value={getField('tenth_percentage')} onChange={handleInputChange} />
                      <FormField label="School" field="tenth_school" value={getField('tenth_school')} onChange={handleInputChange} />
                    </div>
                  </div>

                  {/* Class XII */}
                  <div className="space-y-3">
                    <h4 className="font-semibold text-sm text-primary border-b pb-1">Class XII Details</h4>
                    <div className="grid grid-cols-2 gap-3">
                      <FormField label="Board" field="twelfth_board" value={getField('twelfth_board')} onChange={handleInputChange} />
                      <FormField label="Year" field="twelfth_year" value={getField('twelfth_year')} onChange={handleInputChange} />
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <FormField label="Roll Number" field="twelfth_roll_number" value={getField('twelfth_roll_number')} onChange={handleInputChange} />
                      <FormField label="Percentage" field="twelfth_percentage" value={getField('twelfth_percentage')} onChange={handleInputChange} />
                    </div>
                    <FormField label="Institution Last Attended" field="twelfth_institution" value={getField('twelfth_institution')} onChange={handleInputChange} />
                    <FormField label="Hindi Studied Upto" field="hindi_studied_upto" value={getField('hindi_studied_upto')} onChange={handleInputChange} placeholder="VIII/X/XII/Never" />
                  </div>

                  <FormField label="Previous Qualification" field="previous_qualification" value={getField('previous_qualification')} onChange={handleInputChange} />
                  <FormField label="Graduation Details" field="graduation_details" value={getField('graduation_details')} onChange={handleInputChange} />
                </TabsContent>

                {/* CUET Tab */}
                <TabsContent value="cuet" className="m-0 space-y-4">
                  <div className="rounded-lg border overflow-hidden">
                    <table className="w-full text-sm">
                      <thead className="bg-muted/50">
                        <tr>
                          <th className="px-3 py-2 text-left">Subject</th>
                          <th className="px-3 py-2 text-center w-24">Total</th>
                          <th className="px-3 py-2 text-center w-24">Obtained</th>
                        </tr>
                      </thead>
                      <tbody>
                        {/* Dynamic rendering of up to 10 subjects */}
                        {Array.from({ length: 10 }, (_, i) => i + 1).map(i => {
                          const hasData = getField(`cuet_subject_${i}`) || getField(`cuet_total_score_${i}`) || getField(`cuet_score_obtained_${i}`);
                          // Show if it has data OR if it's one of the first 4 rows (default empty state)
                          if (!hasData && i > 4) return null;

                          return (
                            <tr key={i} className="border-t">
                              <td className="px-1 py-1">
                                <Input
                                  value={getField(`cuet_subject_${i}`)}
                                  onChange={(e) => handleInputChange(`cuet_subject_${i}`, e.target.value)}
                                  placeholder={`Subject ${i}`}
                                  className="h-8 text-sm"
                                />
                              </td>
                              <td className="px-1 py-1">
                                <Input
                                  value={getField(`cuet_total_score_${i}`)}
                                  onChange={(e) => handleInputChange(`cuet_total_score_${i}`, e.target.value)}
                                  placeholder="200"
                                  className="h-8 text-sm text-center"
                                />
                              </td>
                              <td className="px-1 py-1">
                                <Input
                                  value={getField(`cuet_score_obtained_${i}`)}
                                  onChange={(e) => handleInputChange(`cuet_score_obtained_${i}`, e.target.value)}
                                  placeholder="Score"
                                  className="h-8 text-sm text-center"
                                />
                              </td>
                            </tr>
                          );
                        })}
                        <tr className="border-t bg-muted/30 font-semibold">
                          <td className="px-3 py-2">TOTAL</td>
                          <td className="px-3 py-2 text-center">-</td>
                          <td className="px-1 py-1">
                            <Input
                              value={getField('cuet_total_score') || getField('cuet_score')}
                              onChange={(e) => handleInputChange('cuet_total_score', e.target.value)}
                              placeholder="Total"
                              className="h-8 text-sm text-center font-semibold"
                            />
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </TabsContent>

                {/* Admission Tab */}
                <TabsContent value="admission" className="m-0 space-y-4">
                  <div className="grid grid-cols-2 gap-3">
                    <FormField label="Academic Session" field="academic_session" value={getField('academic_session')} onChange={handleInputChange} placeholder="2024-2025" />
                    <FormField label="Course" field="course" value={getField('course')} onChange={handleInputChange} placeholder="B.COM.(H) / B.A.(H) ECO" />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <FormField label="Course Applied For" field="course_applied" value={getField('course_applied')} onChange={handleInputChange} />
                    <FormField label="Category" field="admission_category" value={getField('admission_category')} onChange={handleInputChange} />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <FormField label="DU Portal Form Number" field="du_portal_form_number" value={getField('du_portal_form_number')} onChange={handleInputChange} />
                    <FormField label="Application Number" field="application_number" value={getField('application_number')} onChange={handleInputChange} />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <FormField label="College Roll No" field="college_roll_no" value={getField('college_roll_no')} onChange={handleInputChange} placeholder="e.g., 24BC156" />
                    <FormField label="DU Enrollment Number" field="du_enrollment_number" value={getField('du_enrollment_number')} onChange={handleInputChange} />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <FormField label="Date of Admission" field="date_of_admission" value={getField('date_of_admission')} onChange={handleInputChange} placeholder="DD/MM/YYYY" />
                    <FormField label="Hindi Medium Preference" field="hindi_medium_preference" value={getField('hindi_medium_preference')} onChange={handleInputChange} placeholder="Yes/No" />
                  </div>

                  {/* Certificate Details */}
                  <div className="space-y-3 pt-2">
                    <h4 className="font-semibold text-sm text-primary border-b pb-1">Category Certificate Details (for SC/ST/OBC/EWS/PwBD)</h4>
                    <FormField label="Certificate Issuing Authority" field="category_certificate_authority" value={getField('category_certificate_authority')} onChange={handleInputChange} />
                    <div className="grid grid-cols-2 gap-3">
                      <FormField label="Certificate Number" field="category_certificate_number" value={getField('category_certificate_number')} onChange={handleInputChange} />
                      <FormField label="Date of Issue" field="category_certificate_date" value={getField('category_certificate_date')} onChange={handleInputChange} />
                    </div>
                    <div className="grid grid-cols-3 gap-3">
                      <FormField label="Disability %" field="disability_percentage" value={getField('disability_percentage')} onChange={handleInputChange} />
                      <FormField label="Disability Type" field="disability_type" value={getField('disability_type')} onChange={handleInputChange} placeholder="VH/HH/OH" />
                      <FormField label="UDID Number" field="udid_number" value={getField('udid_number')} onChange={handleInputChange} />
                    </div>
                  </div>
                </TabsContent>

                {/* Documents Tab */}
                <TabsContent value="documents" className="m-0 space-y-4">
                  <h4 className="font-semibold text-sm text-primary border-b pb-1 mb-3">Document Checklist</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {[
                      { key: 'doc_admission_form', label: '1. Admission/Registration Form' },
                      { key: 'doc_undertaking_ragging', label: '2. Anti-Ragging Undertaking' },
                      { key: 'doc_photographs', label: '3. Photographs' },
                      { key: 'doc_cuet_scorecard', label: '4. CUET Score Card' },
                      { key: 'doc_class_xii_marksheet', label: '5. Class XII Mark Sheet' },
                      { key: 'doc_class_x_certificate', label: '6. Class X Certificate' },
                      { key: 'doc_class_xii_certificate', label: '7. Class XII Certificate' },
                      { key: 'doc_character_certificate', label: '8. Character Certificate' },
                      { key: 'doc_transfer_certificate', label: '9. Transfer Certificate' },
                      { key: 'doc_hindi_certificate', label: '10. Hindi Certificate' },
                      { key: 'doc_caste_certificate', label: '11. Caste/Category Certificate' },
                      { key: 'doc_sports_eca', label: '12. Sports/ECA Certificates' },
                      { key: 'doc_originals', label: '13. Original Documents' },
                      { key: 'doc_photo_id', label: '14. Photo ID Proof' },
                    ].map(({ key, label }) => {
                      const isChecked = isDocChecked(key);
                      return (
                        <div
                          key={key}
                          onClick={() => handleInputChange(key, isChecked ? 'No' : 'Yes')}
                          className={`
                            flex items-center gap-3 p-3 rounded-md border cursor-pointer transition-all
                            ${isChecked
                              ? 'bg-emerald-50 border-emerald-500 text-emerald-700 font-medium'
                              : 'bg-white border-zinc-200 hover:border-zinc-300 text-zinc-600'}
                          `}
                        >
                          <div className={`
                            flex items-center justify-center w-5 h-5 rounded border transition-colors
                            ${isChecked ? 'bg-emerald-500 border-emerald-500' : 'bg-white border-zinc-300'}
                          `}>
                            {isChecked && <CheckCircle2 className="h-3.5 w-3.5 text-white" />}
                          </div>
                          <span className="text-sm">{label}</span>
                        </div>
                      );
                    })}
                  </div>
                </TabsContent>
              </div>
            </Tabs>
          </ScrollArea>

          {/* Footer */}
          <div className="p-3 border-t bg-muted/20">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <AlertTriangle className="h-3 w-3 text-amber-500" />
              <span>Verifying will save changes and link to student profile. For large batches (50,000+), use batch upload.</span>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
