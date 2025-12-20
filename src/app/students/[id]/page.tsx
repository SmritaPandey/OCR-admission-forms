"use client";

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { apiService, StudentProfileDetail } from '@/lib/api';
import { 
  Card, 
  CardContent, 
  CardDescription, 
  CardHeader, 
  CardTitle 
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { 
  User, 
  FileText, 
  ChevronLeft, 
  Mail, 
  Phone, 
  MapPin, 
  Calendar,
  Eye,
  Download
} from "lucide-react";
import { toast } from "sonner";
import Link from 'next/link';

export default function StudentProfilePage() {
  const { id } = useParams();
  const router = useRouter();
  const profileId = parseInt(id as string);
  
  const [profile, setProfile] = useState<StudentProfileDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadProfile();
  }, [profileId]);

  const loadProfile = async () => {
    try {
      setLoading(true);
      const data = await apiService.getStudentProfile(profileId);
      setProfile(data);
    } catch (error) {
      toast.error("Failed to load student profile");
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadDoc = async (docId: number, filename: string) => {
    try {
      const blob = await apiService.downloadDocument(docId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      a.click();
    } catch (error) {
      toast.error("Download failed");
    }
  };

  if (loading) return <div className="flex h-[80vh] items-center justify-center animate-pulse">Loading profile...</div>;
  if (!profile) return <div>Profile not found</div>;

  return (
    <div className="space-y-8">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => router.back()}>
          <ChevronLeft className="h-5 w-5" />
        </Button>
        <h2 className="text-3xl font-bold tracking-tight">Student Profile</h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        <Card className="md:col-span-1">
          <CardContent className="pt-8 text-center space-y-4">
            <div className="mx-auto h-24 w-24 rounded-full bg-primary/10 flex items-center justify-center text-primary">
              <User className="h-12 w-12" />
            </div>
            <div>
              <h3 className="text-xl font-bold">{profile.student_name}</h3>
              <p className="text-sm text-muted-foreground">Roll No: {profile.roll_number || 'Pending'}</p>
            </div>
            <div className="flex justify-center gap-2">
              <Badge variant="secondary">Active</Badge>
              <Badge variant="outline">Year {new Date().getFullYear()}</Badge>
            </div>
            <div className="pt-4 space-y-3 text-left border-t">
              <div className="flex items-center gap-3 text-sm">
                <Mail className="h-4 w-4 text-muted-foreground" />
                <span>{profile.forms[0]?.email || 'No email on record'}</span>
              </div>
              <div className="flex items-center gap-3 text-sm">
                <Phone className="h-4 w-4 text-muted-foreground" />
                <span>{profile.forms[0]?.phone_number || 'No phone on record'}</span>
              </div>
              <div className="flex items-center gap-3 text-sm">
                <MapPin className="h-4 w-4 text-muted-foreground" />
                <span className="truncate">{profile.forms[0]?.city || 'No address on record'}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="md:col-span-2 space-y-8">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5 text-primary" /> Admission History
              </CardTitle>
              <CardDescription>Digitized forms associated with this student.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {profile.forms.map((form) => (
                  <div key={form.id} className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/30 transition-colors">
                    <div className="flex items-center gap-4">
                      <div className="h-10 w-10 rounded bg-muted flex items-center justify-center">
                        <FileText className="h-5 w-5 text-muted-foreground" />
                      </div>
                      <div>
                        <p className="font-semibold text-sm">{form.filename}</p>
                        <p className="text-xs text-muted-foreground">Uploaded on {new Date(form.upload_date).toLocaleDateString()}</p>
                      </div>
                    </div>
                    <Button variant="ghost" size="sm" asChild>
                      <Link href={`/forms/${form.id}`}>View Record</Link>
                    </Button>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5 text-primary" /> Supporting Documents
              </CardTitle>
              <CardDescription>Academic certificates and identity proofs.</CardDescription>
            </CardHeader>
            <CardContent>
              {profile.documents.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground border-2 border-dashed rounded-lg">
                  No supporting documents uploaded.
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {profile.documents.map((doc) => (
                    <div key={doc.id} className="p-4 border rounded-lg flex items-center justify-between">
                      <div className="space-y-1">
                        <p className="font-semibold text-xs truncate max-w-[150px]">{doc.filename}</p>
                        <Badge variant="outline" className="text-[10px]">{doc.document_category}</Badge>
                      </div>
                      <div className="flex gap-1">
                        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleDownloadDoc(doc.id, doc.filename)}>
                          <Download className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
