"use client";

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { apiService, FormDetail, FormSearchQuery } from '@/lib/api';
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Search as SearchIcon, Filter, Download, Eye, RefreshCw } from "lucide-react";
import { toast } from "sonner";

export default function SearchPage() {
  const [filters, setFilters] = useState<FormSearchQuery>({
    student_name: '',
    status: '',
    course_applied: '',
  });
  const [results, setResults] = useState<FormDetail[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    handleSearch();
  }, []);

  const handleSearch = async () => {
    try {
      setLoading(true);
      const data = await apiService.searchForms(filters);
      setResults(data);
    } catch (error) {
      toast.error("Search failed");
    } finally {
      setLoading(false);
    }
  };

  const handleExportTable = async (table: 'forms' | 'students' | 'documents', format: 'csv' | 'json' | 'excel' | 'pdf') => {
    try {
      let blob: Blob;
      const timestamp = new Date().toISOString().split('T')[0];
      let filename: string;

      if (table === 'students') {
        if (format === 'csv') {
          blob = await apiService.exportStudentsCSV(filters);
          filename = `students_export_${timestamp}.csv`;
        } else if (format === 'excel') {
          blob = await apiService.exportStudentsExcel(filters);
          filename = `students_export_${timestamp}.xlsx`;
        } else if (format === 'json') {
          blob = await apiService.exportStudentsJSON(filters);
          filename = `students_export_${timestamp}.json`;
        } else {
          blob = await apiService.exportStudentsPDF(filters);
          filename = `students_export_${timestamp}.pdf`;
        }
      } else if (table === 'documents') {
        blob = await apiService.exportDocuments(format, filters);
        filename = `documents_export_${timestamp}.${format === 'excel' ? 'xlsx' : format}`;
      } else {
        blob = await apiService.exportForms(format, filters);
        filename = `forms_export_${timestamp}.${format === 'excel' ? 'xlsx' : format}`;
      }

      // Create download link to save to downloads folder
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success(`${table.charAt(0).toUpperCase() + table.slice(1)} exported successfully`);
    } catch (error: any) {
      console.error('Export failed:', error);
      toast.error(`Export failed: ${error.response?.data?.detail || error.message || 'Unknown error'}`);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'verified':
        return <Badge className="bg-emerald-500">Verified</Badge>;
      case 'extracted':
        return <Badge variant="secondary">Pending Review</Badge>;
      case 'error':
        return <Badge variant="destructive">Error</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Record Explorer</h2>
          <p className="text-muted-foreground">Search and export digitized admission records.</p>
        </div>
        <div className="flex gap-2">
          <div className="flex flex-col gap-1 items-end">
            <span className="text-xs text-muted-foreground mb-1">Export Admission Forms</span>
            <div className="flex gap-1">
              <Button size="sm" variant="outline" onClick={() => handleExportTable('forms', 'csv')}>CSV</Button>
              <Button size="sm" variant="outline" onClick={() => handleExportTable('forms', 'excel')}>Excel</Button>
              <Button size="sm" variant="outline" onClick={() => handleExportTable('forms', 'pdf')}>PDF</Button>
              <Button size="sm" variant="outline" onClick={() => handleExportTable('forms', 'json')}>JSON</Button>
            </div>
          </div>
          <div className="flex flex-col gap-1 items-end pl-4 border-l">
            <span className="text-xs text-muted-foreground mb-1">Export Students</span>
            <div className="flex gap-1">
              <Button size="sm" variant="outline" onClick={() => handleExportTable('students', 'csv')}>CSV</Button>
              <Button size="sm" variant="outline" onClick={() => handleExportTable('students', 'excel')}>Excel</Button>
            </div>
          </div>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Filter className="h-4 w-4" /> Filters
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="space-y-2">
              <Label>Student Name</Label>
              <Input
                placeholder="Search name..."
                value={filters.student_name}
                onChange={(e) => setFilters({ ...filters, student_name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label>Status</Label>
              <Select
                value={filters.status}
                onValueChange={(v) => setFilters({ ...filters, status: v === 'all' ? '' : v })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="All Statuses" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Statuses</SelectItem>
                  <SelectItem value="verified">Verified</SelectItem>
                  <SelectItem value="extracted">Pending Review</SelectItem>
                  <SelectItem value="error">Error</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Course</Label>
              <Input
                placeholder="Course name..."
                value={filters.course_applied}
                onChange={(e) => setFilters({ ...filters, course_applied: e.target.value })}
              />
            </div>
            <div className="flex items-end pb-0.5">
              <Button className="w-full" onClick={handleSearch} disabled={loading}>
                {loading ? <RefreshCw className="mr-2 h-4 w-4 animate-spin" /> : <SearchIcon className="mr-2 h-4 w-4" />}
                Search
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-6">
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Student Name</TableHead>
                  <TableHead>Course</TableHead>
                  <TableHead>Phone</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Submission</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {results.length === 0 && !loading ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center py-12 text-muted-foreground">
                      No records found matching your criteria.
                    </TableCell>
                  </TableRow>
                ) : (
                  results.map((record) => (
                    <TableRow key={record.id}>
                      <TableCell className="font-semibold">{record.student_name || 'Unidentified'}</TableCell>
                      <TableCell>{record.course_applied || 'N/A'}</TableCell>
                      <TableCell>{record.phone_number || 'N/A'}</TableCell>
                      <TableCell>{getStatusBadge(record.status)}</TableCell>
                      <TableCell>{new Date(record.upload_date).toLocaleDateString()}</TableCell>
                      <TableCell className="text-right flex justify-end gap-2">
                        <Button variant="ghost" size="sm" asChild>
                          <Link href={`/forms/${record.id}`}>
                            <Eye className="mr-2 h-4 w-4" /> Details
                          </Link>
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-destructive hover:text-destructive hover:bg-destructive/10"
                          onClick={() => {
                            if (window.confirm(`Delete form "${record.filename}"?`)) {
                              apiService.deleteForm(record.id).then(() => {
                                toast.success("Form deleted");
                                handleSearch();
                              }).catch(() => toast.error("Delete failed"));
                            }
                          }}
                        >
                          Delete
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
