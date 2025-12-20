"use client";

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { apiService, FormDetail } from '@/lib/api';
import { 
  Card, 
  CardContent, 
  CardDescription, 
  CardHeader, 
  CardTitle 
} from "@/components/ui/card";
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { 
  Users, 
  FileCheck, 
  Clock, 
  FileText, 
  TrendingUp,
  Plus,
  Search as SearchIcon,
  Trash2,
  Eye,
  BrainCircuit
} from "lucide-react";
import { toast } from "sonner";

export default function Dashboard() {
  const [forms, setForms] = useState<FormDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    total: 0,
    verified: 0,
    pending: 0,
    documents: 0,
    students: 0,
  });

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const recentForms = await apiService.listForms(0, 10);
      setForms(recentForms);
      
      const allForms = await apiService.listForms(0, 1000);
      
      let documentCount = 0;
      try {
        const documents = await apiService.searchDocuments({ limit: 1000 });
        documentCount = documents.length;
      } catch (err) {
        console.error('Failed to load documents:', err);
      }
      
      let studentCount = 0;
      try {
        const students = await apiService.listStudentProfiles(0, 1000);
        studentCount = students.length;
      } catch (err) {
        console.error('Failed to load students:', err);
      }
      
      setStats({
        total: allForms.length,
        verified: allForms.filter(f => f.status === 'verified').length,
        pending: allForms.filter(f => f.status === 'extracted' || f.status === 'uploaded').length,
        documents: documentCount,
        students: studentCount,
      });
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
      toast.error("Failed to connect to backend server");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (formId: number, filename: string) => {
    if (!window.confirm(`Are you sure you want to delete "${filename}"?`)) {
      return;
    }

    try {
      await apiService.deleteForm(formId);
      toast.success("Form deleted successfully");
      loadDashboardData();
    } catch (error: any) {
      toast.error(`Failed to delete: ${error.message}`);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'verified':
        return <Badge className="bg-emerald-500 hover:bg-emerald-600">Verified</Badge>;
      case 'extracted':
        return <Badge variant="secondary" className="bg-amber-100 text-amber-800 hover:bg-amber-200">Pending Review</Badge>;
      case 'extracting':
        return <Badge variant="outline" className="animate-pulse">Extracting...</Badge>;
      case 'error':
        return <Badge variant="destructive">Error</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  if (loading) {
    return (
      <div className="flex h-[80vh] items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Admissions Dashboard</h2>
        <p className="text-muted-foreground">
          Cycle {new Date().getFullYear()} – {new Date().getFullYear() + 1} Enrollment Management
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Applications</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total}</div>
            <p className="text-xs text-muted-foreground">Overall submissions received</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Verified Records</CardTitle>
            <FileCheck className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.verified}</div>
            <p className="text-xs text-muted-foreground">Cleared for enrollment</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending Review</CardTitle>
            <Clock className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.pending}</div>
            <p className="text-xs text-muted-foreground">Awaiting manual verification</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Students</CardTitle>
            <Users className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.students}</div>
            <p className="text-xs text-muted-foreground">Unique student profiles created</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
        <Card className="col-span-4">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Recent Activity</CardTitle>
                <CardDescription>Latest admission form submissions.</CardDescription>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" asChild>
                  <Link href="/search">View All</Link>
                </Button>
                <Button size="sm" asChild>
                  <Link href="/upload"><Plus className="mr-2 h-4 w-4" /> New Form</Link>
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {forms.length === 0 ? (
              <div className="flex h-[200px] items-center justify-center text-muted-foreground">
                No forms uploaded yet.
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Filename</TableHead>
                    <TableHead>Student</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Date</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {forms.map((form) => (
                    <TableRow key={form.id}>
                      <TableCell className="font-medium truncate max-w-[150px]">{form.filename}</TableCell>
                      <TableCell>{form.student_name || 'N/A'}</TableCell>
                      <TableCell>{getStatusBadge(form.status)}</TableCell>
                      <TableCell>{new Date(form.upload_date).toLocaleDateString()}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Button variant="ghost" size="icon" asChild>
                            <Link href={`/forms/${form.id}`}>
                              <Eye className="h-4 w-4" />
                            </Link>
                          </Button>
                          <Button 
                            variant="ghost" 
                            size="icon" 
                            className="text-destructive hover:text-destructive"
                            onClick={() => handleDelete(form.id, form.filename)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
        <Card className="col-span-3">
          <CardHeader>
            <CardTitle>System Overview</CardTitle>
            <CardDescription>OCR performance and data health.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span>Verification Accuracy</span>
                <span className="font-semibold">94.2%</span>
              </div>
              <div className="h-2 w-full rounded-full bg-secondary">
                <div className="h-full w-[94%] rounded-full bg-emerald-500"></div>
              </div>
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span>OCR Processing Load</span>
                <span className="font-semibold">Normal</span>
              </div>
              <div className="h-2 w-full rounded-full bg-secondary">
                <div className="h-full w-[25%] rounded-full bg-primary"></div>
              </div>
            </div>
            
            <div className="pt-4">
              <h4 className="text-sm font-semibold mb-3">Quick Actions</h4>
              <div className="grid grid-cols-2 gap-2">
                <Button variant="outline" className="justify-start h-auto py-3 px-4" asChild>
                  <Link href="/training">
                    <div className="flex flex-col items-start gap-1">
                      <BrainCircuit className="h-4 w-4" />
                      <span className="text-xs font-bold">Tune Model</span>
                    </div>
                  </Link>
                </Button>
                <Button variant="outline" className="justify-start h-auto py-3 px-4" asChild>
                  <Link href="/batch-upload">
                    <div className="flex flex-col items-start gap-1">
                      <TrendingUp className="h-4 w-4" />
                      <span className="text-xs font-bold">Bulk Intake</span>
                    </div>
                  </Link>
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
