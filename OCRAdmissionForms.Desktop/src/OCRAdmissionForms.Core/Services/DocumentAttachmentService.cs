using System;
using System.Collections.Generic;
using System.IO;
using OCRAdmissionForms.Core.Entities;

namespace OCRAdmissionForms.Core.Services;

/// <summary>
/// Service for managing document attachments - copying files and linking to student profiles
/// </summary>
public class DocumentAttachmentService
{
    private readonly string _documentsPath;
    
    public DocumentAttachmentService()
    {
        var appData = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
        _documentsPath = Path.Combine(appData, "SRCC Student DMS", "documents");
        Directory.CreateDirectory(_documentsPath);
    }
    
    /// <summary>
    /// Create document references for a multi-page PDF form
    /// Copies the original PDF to the student folder
    /// </summary>
    public List<StudentDocument> CreateDocumentReferences(
        string pdfPath, 
        string studentName, 
        int formId, 
        int? studentProfileId,
        int pageCount)
    {
        var documents = new List<StudentDocument>();
        var safeStudentName = SanitizeFileName(studentName);
        var studentFolder = Path.Combine(_documentsPath, $"Form_{formId}");
        Directory.CreateDirectory(studentFolder);
        
        // Copy the original PDF to the student folder
        var pdfFilename = $"{safeStudentName}_AdmissionForm.pdf";
        var destPdfPath = Path.Combine(studentFolder, pdfFilename);
        
        try
        {
            if (File.Exists(pdfPath) && !File.Exists(destPdfPath))
            {
                File.Copy(pdfPath, destPdfPath, true);
            }
            
            // Create a document reference for the whole PDF
            var mainDoc = new StudentDocument
            {
                Filename = pdfFilename,
                FilePath = destPdfPath,
                UploadDate = DateTime.UtcNow,
                DocumentCategory = DocumentCategory.AcademicCertificate,
                DocumentType = DocumentType.AdmissionForm,
                Description = $"Complete admission form ({pageCount} pages)",
                FileSize = File.Exists(destPdfPath) ? new FileInfo(destPdfPath).Length : 0,
                FormId = formId,
                StudentProfileId = studentProfileId,
                SyncStatus = SyncStatus.PendingCreate
            };
            
            documents.Add(mainDoc);
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"Error copying PDF: {ex.Message}");
        }
        
        return documents;
    }
    
    /// <summary>
    /// Create document attachment entry for a specific document type
    /// </summary>
    public StudentDocument CreateDocumentEntry(
        string filePath,
        string studentName,
        int formId,
        int? studentProfileId,
        DocumentType docType)
    {
        var safeStudentName = SanitizeFileName(studentName);
        var studentFolder = Path.Combine(_documentsPath, $"Form_{formId}");
        Directory.CreateDirectory(studentFolder);
        
        var extension = Path.GetExtension(filePath);
        var filename = $"{safeStudentName}_{docType}{extension}";
        var destPath = Path.Combine(studentFolder, filename);
        
        try
        {
            if (File.Exists(filePath) && !File.Exists(destPath))
            {
                File.Copy(filePath, destPath, true);
            }
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"Error copying document: {ex.Message}");
        }
        
        return new StudentDocument
        {
            Filename = filename,
            FilePath = destPath,
            UploadDate = DateTime.UtcNow,
            DocumentCategory = GetCategoryForType(docType),
            DocumentType = docType,
            Description = $"{docType} - attached",
            FileSize = File.Exists(destPath) ? new FileInfo(destPath).Length : 0,
            FormId = formId,
            StudentProfileId = studentProfileId,
            SyncStatus = SyncStatus.PendingCreate
        };
    }
    
    /// <summary>
    /// Link checked documents from the document checklist to the student profile
    /// Creates placeholder entries for documents marked as submitted
    /// </summary>
    public List<StudentDocument> CreateChecklistDocuments(AdmissionForm form, int? studentProfileId)
    {
        var documents = new List<StudentDocument>();
        
        // Create list of checked documents with their types
        var checklistItems = new List<(bool? isChecked, DocumentType docType)>
        {
            (form.DocPhotographs, DocumentType.StudentPhotograph),
            (form.DocCuetScorecard, DocumentType.CuetScorecard),
            (form.DocClassXiiMarksheet, DocumentType.ClassXiiMarksheet),
            (form.DocClassXCertificate, DocumentType.ClassXCertificate),
            (form.DocClassXiiCertificate, DocumentType.ClassXiiCertificate),
            (form.DocCharacterCertificate, DocumentType.CharacterCertificate),
            (form.DocCasteCertificate, DocumentType.CasteCertificate),
            (form.DocMigrationCertificate, DocumentType.MigrationCertificate),
            (form.DocTransferCertificate, DocumentType.TransferCertificate),
            (form.DocGapCertificate, DocumentType.GapCertificate),
            (form.DocIncomeCertificate, DocumentType.IncomeCertificate),
            (form.DocDomicileCertificate, DocumentType.DomicileCertificate),
            (form.DocAadharCard, DocumentType.AadharCard),
            (form.DocMedicalFitness, DocumentType.MedicalFitness),
            (form.DocUndertakingRagging, DocumentType.AntiRaggingUndertaking),
        };
        
        foreach (var (isChecked, docType) in checklistItems)
        {
            if (isChecked == true)
            {
                documents.Add(new StudentDocument
                {
                    Filename = $"{docType}_Pending.placeholder",
                    FilePath = "", // Empty until actual file is attached
                    DocumentCategory = GetCategoryForType(docType),
                    DocumentType = docType,
                    Description = $"{docType} - marked as submitted",
                    FormId = form.Id,
                    StudentProfileId = studentProfileId,
                    SyncStatus = SyncStatus.PendingCreate
                });
            }
        }
        
        return documents;
    }
    
    /// <summary>
    /// Get the document storage path for a form
    /// </summary>
    public string GetDocumentsPath(int formId)
    {
        var path = Path.Combine(_documentsPath, $"Form_{formId}");
        Directory.CreateDirectory(path);
        return path;
    }
    
    private static DocumentCategory GetCategoryForType(DocumentType type)
    {
        return type switch
        {
            DocumentType.AadharCard => DocumentCategory.IdProof,
            DocumentType.PhotoIdProof => DocumentCategory.IdProof,
            DocumentType.StudentPhotograph => DocumentCategory.IdProof,
            DocumentType.CasteCertificate => DocumentCategory.CasteCertificate,
            DocumentType.IncomeCertificate => DocumentCategory.IncomeCertificate,
            DocumentType.MedicalFitness => DocumentCategory.MedicalCertificate,
            DocumentType.ClassXiiMarksheet => DocumentCategory.AcademicCertificate,
            DocumentType.ClassXiiCertificate => DocumentCategory.AcademicCertificate,
            DocumentType.ClassXCertificate => DocumentCategory.AcademicCertificate,
            DocumentType.CuetScorecard => DocumentCategory.AcademicCertificate,
            _ => DocumentCategory.Other
        };
    }
    
    private static string SanitizeFileName(string name)
    {
        if (string.IsNullOrEmpty(name)) return "Unknown";
        
        var invalidChars = Path.GetInvalidFileNameChars();
        foreach (var c in invalidChars)
        {
            name = name.Replace(c, '_');
        }
        return name.Trim().Replace(" ", "_");
    }
}
