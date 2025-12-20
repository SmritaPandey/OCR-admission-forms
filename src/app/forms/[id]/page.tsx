"use client";

import { useState, useEffect } from 'react';
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
import { Tabs, TabsContent, TableList, TabsTrigger, TabsList } from "@/components/ui/tabs";
import { 
  CheckCircle2, 
  RefreshCw, 
  ChevronLeft, 
  Save, 
  FileSearch,
  ExternalLink,
  AlertTriangle
} from "lucide-react";
import { toast } from "sonner";

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

  useEffect(() => {
    loadForm();
    loadProviders();
  }, [formId]);

  const loadForm = async () => {
    try {
      setLoading(true);
      const data = await apiService.getForm(formId);
      setForm(data);
      // Initialize edited data with form data
      const verificationData: any = {};
      Object.keys(data).forEach(key => {
        if (typeof (data as any)[key] === 'string' || typeof (data as any)[key] === 'number') {
          verificationData[key] = (data as any)[key];
        }
      });
      setEditedData(verificationData);
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
    } catch (error) {}
  };

  const handleInputChange = (field: string, value: string) => {
    setEditedData(prev => ({ ...prev, [field]: value }));
  };

  const handleVerify = async () => {
    try {
      setSaving(true);
      await apiService.verifyForm(formId, editedData);
      toast.success("Record verified and saved");
      loadForm();
    } catch (error) {
      toast.error("Verification failed");
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

  if (loading) {
    return <div className="flex h-[80vh] items-center justify-center animate-pulse text-muted-foreground">Loading extraction results...</div>;
  }

  if (!form) return <div>Form not found</div>;

  const imageUrl = `http://localhost:8000/${form.file_path}`;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ChevronLeft className="h-5 w-5" />
          </Button>
          <div>
            <h2 className="text-2xl font-bold tracking-tight">{form.filename}</h2>
            <p className="text-sm text-muted-foreground">
              Processed with {form.ocr_provider} • {new Date(form.upload_date).toLocaleString()}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleReExtract} disabled={reExtracting}>
            {reExtracting ? <RefreshCw className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
            Re-Extract
          </Button>
          <Button onClick={handleVerify} disabled={saving}>
            {saving ? <RefreshCw className="mr-2 h-4 w-4 animate-spin" /> : <CheckCircle2 className="mr-2 h-4 w-4" />}
            Verify & Save
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 h-[calc(100vh-200px)]">
        {/* Left Side: Document Preview */}
        <Card className="overflow-hidden flex flex-col">
          <CardHeader className="py-3 px-4 border-b">
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
            <img 
              src={imageUrl} 
              alt="Form Scan" 
              className="max-w-none w-full shadow-lg"
            />
          </CardContent>
        </Card>

        {/* Right Side: Data Verification */}
        <Card className="flex flex-col">
          <CardHeader className="py-3 px-4 border-b">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-medium">Extracted Data Fields</CardTitle>
              {form.status === 'verified' && (
                <div className="flex items-center text-emerald-600 text-xs font-bold bg-emerald-50 px-2 py-1 rounded-full border border-emerald-100">
                  <CheckCircle2 className="h-3 w-3 mr-1" /> VERIFIED
                </div>
              )}
            </div>
          </CardHeader>
          <CardContent className="p-0 flex-1 overflow-auto">
            <Tabs defaultValue="basic" className="w-full">
              <div className="border-b px-4">
                <TabsList className="bg-transparent h-12 gap-4">
                  <TabsTrigger value="basic" className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none h-12 px-0">Personal</TabsTrigger>
                  <TabsTrigger value="contact" className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none h-12 px-0">Contact & Address</TabsTrigger>
                  <TabsTrigger value="family" className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none h-12 px-0">Parents</TabsTrigger>
                  <TabsTrigger value="education" className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none h-12 px-0">Education</TabsTrigger>
                  <TabsTrigger value="admission" className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none h-12 px-0">Admission</TabsTrigger>
                </TabsList>
              </div>

              <div className="p-6 space-y-6">
                <TabsContent value="basic" className="m-0 space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Student Full Name</Label>
                      <Input 
                        value={editedData.student_name || ''} 
                        onChange={(e) => handleInputChange('student_name', e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Aadhar Number</Label>
                      <Input 
                        value={editedData.aadhar_number || ''} 
                        onChange={(e) => handleInputChange('aadhar_number', e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Date of Birth</Label>
                      <Input 
                        value={editedData.date_of_birth || ''} 
                        onChange={(e) => handleInputChange('date_of_birth', e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Gender</Label>
                      <Input 
                        value={editedData.gender || ''} 
                        onChange={(e) => handleInputChange('gender', e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Category</Label>
                      <Input 
                        value={editedData.category || ''} 
                        onChange={(e) => handleInputChange('category', e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Religion</Label>
                      <Input 
                        value={editedData.religion || ''} 
                        onChange={(e) => handleInputChange('religion', e.target.value)}
                      />
                    </div>
                  </div>
                </TabsContent>

                <TabsContent value="contact" className="m-0 space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Phone Number</Label>
                      <Input 
                        value={editedData.phone_number || ''} 
                        onChange={(e) => handleInputChange('phone_number', e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Email Address</Label>
                      <Input 
                        value={editedData.email || ''} 
                        onChange={(e) => handleInputChange('email', e.target.value)}
                      />
                    </div>
                    <div className="col-span-2 space-y-2">
                      <Label>Permanent Address</Label>
                      <Input 
                        value={editedData.permanent_address || ''} 
                        onChange={(e) => handleInputChange('permanent_address', e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>City</Label>
                      <Input 
                        value={editedData.city || ''} 
                        onChange={(e) => handleInputChange('city', e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>State</Label>
                      <Input 
                        value={editedData.state || ''} 
                        onChange={(e) => handleInputChange('state', e.target.value)}
                      />
                    </div>
                  </div>
                </TabsContent>

                <TabsContent value="family" className="m-0 space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Father's Name</Label>
                      <Input 
                        value={editedData.father_name || ''} 
                        onChange={(e) => handleInputChange('father_name', e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Father's Occupation</Label>
                      <Input 
                        value={editedData.father_occupation || ''} 
                        onChange={(e) => handleInputChange('father_occupation', e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Mother's Name</Label>
                      <Input 
                        value={editedData.mother_name || ''} 
                        onChange={(e) => handleInputChange('mother_name', e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Mother's Phone</Label>
                      <Input 
                        value={editedData.mother_phone || ''} 
                        onChange={(e) => handleInputChange('mother_phone', e.target.value)}
                      />
                    </div>
                  </div>
                </TabsContent>

                <TabsContent value="education" className="m-0 space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2 border-b pb-4 col-span-2">
                      <Label className="text-primary font-bold">Class X Details</Label>
                      <div className="grid grid-cols-2 gap-2 mt-2">
                        <Input 
                          placeholder="Board"
                          value={editedData.tenth_board || ''} 
                          onChange={(e) => handleInputChange('tenth_board', e.target.value)}
                        />
                        <Input 
                          placeholder="Year"
                          value={editedData.tenth_year || ''} 
                          onChange={(e) => handleInputChange('tenth_year', e.target.value)}
                        />
                      </div>
                    </div>
                    <div className="space-y-2 col-span-2">
                      <Label className="text-primary font-bold">Class XII Details</Label>
                      <div className="grid grid-cols-2 gap-2 mt-2">
                        <Input 
                          placeholder="Board"
                          value={editedData.twelfth_board || ''} 
                          onChange={(e) => handleInputChange('twelfth_board', e.target.value)}
                        />
                        <Input 
                          placeholder="Year"
                          value={editedData.twelfth_year || ''} 
                          onChange={(e) => handleInputChange('twelfth_year', e.target.value)}
                        />
                      </div>
                    </div>
                  </div>
                </TabsContent>

                <TabsContent value="admission" className="m-0 space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Course Applied For</Label>
                      <Input 
                        value={editedData.course_applied || ''} 
                        onChange={(e) => handleInputChange('course_applied', e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Application Number</Label>
                      <Input 
                        value={editedData.application_number || ''} 
                        onChange={(e) => handleInputChange('application_number', e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Enrollment Number</Label>
                      <Input 
                        value={editedData.enrollment_number || ''} 
                        onChange={(e) => handleInputChange('enrollment_number', e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Admission Date</Label>
                      <Input 
                        value={editedData.admission_date || ''} 
                        onChange={(e) => handleInputChange('admission_date', e.target.value)}
                      />
                    </div>
                  </div>
                </TabsContent>
              </div>
            </Tabs>
          </CardContent>
          <div className="p-4 border-t bg-muted/20">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <AlertTriangle className="h-3 w-3 text-amber-500" />
              <span>Verifying this record will save changes and automatically update the student's profile.</span>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
