"use client";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { apiService } from '@/lib/api';
import { 
  Card, 
  CardContent, 
  CardDescription, 
  CardHeader, 
  CardTitle 
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Upload, FileText, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import { toast } from "sonner";

export default function UploadPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [providers, setProviders] = useState<string[]>([]);
  const [selectedProvider, setSelectedProvider] = useState<string>('');
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setProgress] = useState(0);

  useEffect(() => {
    loadProviders();
  }, []);

  const loadProviders = async () => {
    try {
      const data = await apiService.getProviders();
      setProviders(data.providers);
      setSelectedProvider(data.default);
    } catch (error) {
      console.error('Failed to load providers:', error);
      toast.error("Failed to load OCR providers");
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    try {
      setIsUploading(true);
      setProgress(10);
      
      // Simulating progress since axios upload progress is tricky with simple implementation
      const interval = setInterval(() => {
        setProgress(prev => (prev < 90 ? prev + 5 : prev));
      }, 500);

      const result = await apiService.uploadForm(file, selectedProvider);
      
      clearInterval(interval);
      setProgress(100);
      toast.success("Form uploaded and extraction started");
      
      // Redirect to verification view
      router.push(`/forms/${result.id}`);
    } catch (error: any) {
      setIsUploading(false);
      setProgress(0);
      toast.error(`Upload failed: ${error.message}`);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      <div>
        <h2 className="text-3xl font-bold tracking-tight text-center">New Application Intake</h2>
        <p className="text-muted-foreground text-center">
          Upload a scanned admission form to start the digital extraction process.
        </p>
      </div>

      <Card className="border-2 border-dashed">
        <CardHeader>
          <CardTitle>Form Submission</CardTitle>
          <CardDescription>Supported formats: JPG, PNG, PDF (up to 10MB)</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleUpload} className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="ocr-provider">OCR Intelligence Provider</Label>
              <Select 
                value={selectedProvider} 
                onValueChange={setSelectedProvider}
                disabled={isUploading}
              >
                <SelectTrigger id="ocr-provider">
                  <SelectValue placeholder="Select OCR Engine" />
                </SelectTrigger>
                <SelectContent>
                  {providers.map(p => (
                    <SelectItem key={p} value={p}>
                      {p.charAt(0).toUpperCase() + p.slice(1).replace('-', ' ')}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-[10px] text-muted-foreground uppercase tracking-widest font-bold">
                Recommended: Craft-TrOCR for handwriting
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="form-file">Admission Form Scan</Label>
              <div 
                className={`relative group border-2 border-dashed rounded-lg p-12 transition-all text-center ${
                  file ? 'border-emerald-500 bg-emerald-50/50' : 'hover:border-primary hover:bg-muted/50'
                }`}
              >
                <Input
                  id="form-file"
                  type="file"
                  accept=".jpg,.jpeg,.png,.pdf"
                  className="absolute inset-0 opacity-0 cursor-pointer z-10"
                  onChange={handleFileChange}
                  disabled={isUploading}
                />
                <div className="space-y-4">
                  <div className={`mx-auto w-12 h-12 rounded-full flex items-center justify-center ${
                    file ? 'bg-emerald-100 text-emerald-600' : 'bg-primary/10 text-primary'
                  }`}>
                    {file ? <FileText className="h-6 w-6" /> : <Upload className="h-6 w-6" />}
                  </div>
                  <div>
                    <p className="text-sm font-semibold">
                      {file ? file.name : "Click or drag to upload form"}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {file ? `${(file.size / 1024 / 1024).toFixed(2)} MB` : "No file selected"}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {isUploading && (
              <div className="space-y-2">
                <div className="flex justify-between text-xs font-medium">
                  <span>Processing digital conversion...</span>
                  <span>{uploadProgress}%</span>
                </div>
                <Progress value={uploadProgress} className="h-2" />
              </div>
            )}

            <Button 
              type="submit" 
              className="w-full h-12 text-base font-bold transition-all"
              disabled={!file || isUploading}
            >
              {isUploading ? (
                <>
                  <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                  Running OCR Extraction
                </>
              ) : (
                <>
                  <CheckCircle2 className="mr-2 h-5 w-5" />
                  Begin Extraction
                </>
              )}
            </Button>
          </form>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="flex items-start gap-3 p-4 bg-muted/30 rounded-lg border">
          <AlertCircle className="h-5 w-5 text-amber-500 mt-0.5" />
          <div className="text-sm">
            <p className="font-semibold">Quality Tip</p>
            <p className="text-muted-foreground">Ensure scans are 300 DPI or higher for best handwriting recognition.</p>
          </div>
        </div>
        <div className="flex items-start gap-3 p-4 bg-muted/30 rounded-lg border">
          <AlertCircle className="h-5 w-5 text-blue-500 mt-0.5" />
          <div className="text-sm">
            <p className="font-semibold">Automation</p>
            <p className="text-muted-foreground">The system will automatically create student profiles if not found.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
