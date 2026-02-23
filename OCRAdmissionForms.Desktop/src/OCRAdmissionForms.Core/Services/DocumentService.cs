using OCRAdmissionForms.Core.Data;
using OCRAdmissionForms.Core.Entities;
using PdfSharpCore.Pdf;
using PdfSharpCore.Pdf.IO;

namespace OCRAdmissionForms.Core.Services;

/// <summary>
/// Handles document extraction from PDFs and file attachment operations.
/// First 4 pages of uploaded PDFs are the admission form; pages 5+ are supporting documents.
/// </summary>
public static class DocumentService
{
    private const int FormPageCount = 4;

    /// <summary>
    /// Gets the base directory for storing student documents
    /// </summary>
    public static string GetDocumentsDirectory()
    {
        var dir = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
            "OCRAdmissionForms", "StudentDocuments");
        Directory.CreateDirectory(dir);
        return dir;
    }

    /// <summary>
    /// Extract pages beyond the first 4 (admission form pages) from a PDF and save them
    /// as individual document files linked to the student profile.
    /// Returns the list of created StudentDocument records (not yet saved to DB).
    /// </summary>
    public static List<StudentDocument> ExtractAttachedDocuments(
        string pdfPath, int formId, int studentProfileId)
    {
        var documents = new List<StudentDocument>();
        if (!File.Exists(pdfPath) || !pdfPath.EndsWith(".pdf", StringComparison.OrdinalIgnoreCase))
            return documents;

        try
        {
            using var inputDoc = PdfReader.Open(pdfPath, PdfDocumentOpenMode.Import);
            if (inputDoc.PageCount <= FormPageCount)
                return documents; // No extra pages to extract

            var docsDir = GetDocumentsDirectory();
            var baseName = Path.GetFileNameWithoutExtension(pdfPath);

            // Extract each page beyond page 4 as a separate single-page PDF
            for (int i = FormPageCount; i < inputDoc.PageCount; i++)
            {
                var pageNum = i + 1; // 1-indexed
                var outputFilename = $"{baseName}_page{pageNum}.pdf";
                var outputPath = Path.Combine(docsDir, outputFilename);

                // Avoid overwriting existing files
                if (File.Exists(outputPath))
                {
                    var counter = 1;
                    while (File.Exists(outputPath))
                    {
                        outputFilename = $"{baseName}_page{pageNum}_{counter}.pdf";
                        outputPath = Path.Combine(docsDir, outputFilename);
                        counter++;
                    }
                }

                using var outputDoc = new PdfDocument();
                outputDoc.AddPage(inputDoc.Pages[i]);
                outputDoc.Save(outputPath);

                var fileInfo = new FileInfo(outputPath);
                documents.Add(new StudentDocument
                {
                    Filename = outputFilename,
                    FilePath = outputPath,
                    UploadDate = DateTime.UtcNow,
                    DocumentCategory = DocumentCategory.Other,
                    DocumentType = DocumentType.Other,
                    Description = $"Attached document - Page {pageNum} from {Path.GetFileName(pdfPath)}",
                    FileSize = fileInfo.Length,
                    SourcePageNumber = pageNum,
                    FormId = formId,
                    StudentProfileId = studentProfileId,
                    SyncStatus = SyncStatus.PendingCreate,
                });
            }
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"[DocumentService] PDF extraction error: {ex.Message}");
        }

        return documents;
    }

    /// <summary>
    /// Attach an external file (any type) to a student profile.
    /// Copies the file to the documents directory and returns a StudentDocument record.
    /// </summary>
    public static StudentDocument? AttachFile(
        string sourceFilePath, string label, DocumentType docType,
        int formId, int studentProfileId)
    {
        if (!File.Exists(sourceFilePath))
            return null;

        try
        {
            var docsDir = GetDocumentsDirectory();
            var ext = Path.GetExtension(sourceFilePath);
            var safeName = SanitizeFilename(label) + ext;
            var destPath = Path.Combine(docsDir, safeName);

            // Avoid overwriting
            if (File.Exists(destPath))
            {
                var counter = 1;
                while (File.Exists(destPath))
                {
                    safeName = $"{SanitizeFilename(label)}_{counter}{ext}";
                    destPath = Path.Combine(docsDir, safeName);
                    counter++;
                }
            }

            File.Copy(sourceFilePath, destPath, false);
            var fileInfo = new FileInfo(destPath);

            return new StudentDocument
            {
                Filename = safeName,
                FilePath = destPath,
                UploadDate = DateTime.UtcNow,
                DocumentCategory = MapTypeToCategory(docType),
                DocumentType = docType,
                Description = label,
                FileSize = fileInfo.Length,
                FormId = formId,
                StudentProfileId = studentProfileId,
                SyncStatus = SyncStatus.PendingCreate,
            };
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"[DocumentService] Attach error: {ex.Message}");
            return null;
        }
    }

    private static string SanitizeFilename(string name)
    {
        var invalid = Path.GetInvalidFileNameChars();
        var clean = new string(name.Select(c => invalid.Contains(c) ? '_' : c).ToArray());
        return string.IsNullOrWhiteSpace(clean) ? "document" : clean;
    }

    private static DocumentCategory MapTypeToCategory(DocumentType type) => type switch
    {
        DocumentType.AadharCard or DocumentType.PhotoIdProof => DocumentCategory.IdProof,
        DocumentType.ClassXiiMarksheet or DocumentType.ClassXCertificate
            or DocumentType.ClassXiiCertificate or DocumentType.CuetScorecard
            or DocumentType.MigrationCertificate or DocumentType.TransferCertificate
            or DocumentType.CharacterCertificate or DocumentType.GapCertificate
            => DocumentCategory.AcademicCertificate,
        DocumentType.MedicalFitness => DocumentCategory.MedicalCertificate,
        DocumentType.IncomeCertificate => DocumentCategory.IncomeCertificate,
        DocumentType.CasteCertificate or DocumentType.DomicileCertificate => DocumentCategory.CasteCertificate,
        _ => DocumentCategory.Other,
    };
}
