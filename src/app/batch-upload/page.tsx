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
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { 
  FileUp, 
  Files, 
  Loader2, 
  CheckCircle2, 
  Clock, 
  AlertCircle,
  PlayCircle
} from "lucide-react";
import { toast } from "sonner";

export default function BatchUploadPage() {
  const router = useRouter();
  const [files, setFiles] = useState<File[]>([]);
  const [providers, setProviders] = useState<string[]>([]);
  const [selectedProvider, setSelectedProvider] = useState<string>('');
  const [pagesPerForm, setPagesPerForm] = useState(1);
  const [isUploading, setIsUploading] = useState(false);
  const [jobs, setJobs] = useState<any[]>([]);
  const [loadingJobs, setLoadingJobs] = useState(true);

  useEffect(() => {
    loadProviders();
    loadJobs();
    // Poll jobs more frequently (every 2 seconds) for real-time progress
    const interval = setInterval(loadJobs, 2000);
    return () => clearInterval(interval);
  }, []);

  const loadProviders = async () => {
    try {
      const data = await apiService.getProviders();
      setProviders(data.providers);
      setSelectedProvider(data.default);
    } catch (error) {
      toast.error("Failed to load OCR providers");
    }
  };

  const loadJobs = async () => {
    try {
      const data = await apiService.listBatchJobs();
      setJobs(data.jobs || []);
    } catch (error) {
      console.error('Failed to load jobs:', error);
    } finally {
      setLoadingJobs(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFiles(Array.from(e.target.files));
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (files.length === 0) return;

    try {
      setIsUploading(true);
      const result = await apiService.batchUploadForms(files, selectedProvider, pagesPerForm);
      toast.success(`Batch job started: ${result.job_id}`);
      setFiles([]);
      loadJobs();
    } catch (error: any) {
      toast.error(`Batch upload failed: ${error.message}`);
    } finally {
      setIsUploading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <Badge className="bg-emerald-500">Completed</Badge>;
      case 'processing':
        return <Badge variant="outline" className="animate-pulse bg-blue-50 text-blue-700 border-blue-200">Processing</Badge>;
      case 'pending':
        return <Badge variant="secondary">Queued</Badge>;
      case 'failed':
        return <Badge variant="destructive">Failed</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Bulk Intake Command</h2>
        <p className="text-muted-foreground">
          Process multiple admission forms simultaneously using distributed OCR pipelines.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>Batch Submission</CardTitle>
            <CardDescription>Upload up to 100 forms at once.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleUpload} className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="ocr-provider">OCR Engine</Label>
                <Select value={selectedProvider} onValueChange={setSelectedProvider}>
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
              </div>

              <div className="space-y-2">
                <Label htmlFor="pages">Pages per Form</Label>
                <Input 
                  id="pages" 
                  type="number" 
                  min="1" 
                  max="10" 
                  value={pagesPerForm} 
                  onChange={(e) => setPagesPerForm(parseInt(e.target.value))} 
                />
                <p className="text-[10px] text-muted-foreground">How many pages does each admission form have?</p>
              </div>

              <div className="space-y-2">
                <Label>Select Scans</Label>
                <div className="relative border-2 border-dashed rounded-lg p-8 transition-all text-center hover:border-primary hover:bg-muted/50">
                  <Input
                    type="file"
                    multiple
                    accept=".jpg,.jpeg,.png,.pdf"
                    className="absolute inset-0 opacity-0 cursor-pointer z-10"
                    onChange={handleFileChange}
                  />
                  <div className="space-y-2">
                    <FileUp className="mx-auto h-8 w-8 text-muted-foreground" />
                    <p className="text-xs font-semibold">
                      {files.length > 0 ? `${files.length} files selected` : "Drop files here"}
                    </p>
                  </div>
                </div>
              </div>

              <Button 
                type="submit" 
                className="w-full h-11 font-bold"
                disabled={files.length === 0 || isUploading}
              >
                {isUploading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Starting Batch...
                  </>
                ) : (
                  <>
                    <PlayCircle className="mr-2 h-4 w-4" />
                    Execute Intake
                  </>
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Intake Monitoring</CardTitle>
            <CardDescription>Live status of bulk processing jobs.</CardDescription>
          </CardHeader>
          <CardContent>
            {loadingJobs && jobs.length === 0 ? (
              <div className="flex justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : jobs.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-muted-foreground border-2 border-dotted rounded-xl">
                <Files className="h-12 w-12 mb-4 opacity-20" />
                <p>No bulk jobs found in history.</p>
              </div>
            ) : (
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Job ID</TableHead>
                      <TableHead>Progress</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Date</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {jobs.map((job) => (
                      <TableRow key={job.job_id}>
                        <TableCell className="font-mono text-xs">{job.job_id.substring(0, 8)}...</TableCell>
                        <TableCell className="w-[200px]">
                          <div className="space-y-1">
                            <div className="flex justify-between text-[10px]">
                              <span>{job.processed_items || job.completed_files || 0} / {job.total_items || job.total_files || 0}</span>
                              <span>{Math.round(((job.processed_items || job.completed_files || 0) / (job.total_items || job.total_files || 1)) * 100)}%</span>
                            </div>
                            <Progress value={((job.processed_items || job.completed_files || 0) / (job.total_items || job.total_files || 1)) * 100} className="h-1.5" />
                          </div>
                        </TableCell>
                        <TableCell>{getStatusBadge(job.status)}</TableCell>
                        <TableCell className="text-xs text-muted-foreground">
                          {new Date(job.created_at).toLocaleTimeString()}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
