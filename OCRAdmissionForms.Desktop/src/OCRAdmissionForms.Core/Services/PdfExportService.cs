using System.IO;
using DocumentFormat.OpenXml;
using DocumentFormat.OpenXml.Packaging;
using DocumentFormat.OpenXml.Wordprocessing;
using OCRAdmissionForms.Core.Entities;

namespace OCRAdmissionForms.Core.Services;

/// <summary>
/// Service for exporting data to PDF/Word format
/// Uses OpenXML to generate Word documents which can be saved as PDF
/// </summary>
public class PdfExportService
{
    /// <summary>
    /// Export admission form to Word document
    /// </summary>
    public async Task ExportFormAsync(AdmissionForm form, string filePath)
    {
        await Task.Run(() => CreateFormDocument(form, filePath));
    }

    /// <summary>
    /// Export student profile to Word document
    /// </summary>
    public async Task ExportStudentAsync(StudentProfile student, string filePath)
    {
        await Task.Run(() => CreateStudentDocument(student, filePath));
    }

    /// <summary>
    /// Export multiple forms to a single Word document
    /// </summary>
    public async Task ExportBulkFormsAsync(IEnumerable<AdmissionForm> forms, string filePath)
    {
        await Task.Run(() =>
        {
            using var doc = WordprocessingDocument.Create(filePath, WordprocessingDocumentType.Document);
            var mainPart = doc.AddMainDocumentPart();
            mainPart.Document = new Document(new Body());
            var body = mainPart.Document.Body!;

            var isFirst = true;
            foreach (var form in forms)
            {
                if (!isFirst)
                {
                    body.Append(new Paragraph(new Run(new Break { Type = BreakValues.Page })));
                }
                AddFormContent(body, form);
                isFirst = false;
            }

            mainPart.Document.Save();
        });
    }

    private static void CreateFormDocument(AdmissionForm form, string filePath)
    {
        using var doc = WordprocessingDocument.Create(filePath, WordprocessingDocumentType.Document);
        var mainPart = doc.AddMainDocumentPart();
        mainPart.Document = new Document(new Body());
        var body = mainPart.Document.Body!;

        AddFormContent(body, form);
        mainPart.Document.Save();
    }

    private static void CreateStudentDocument(StudentProfile student, string filePath)
    {
        using var doc = WordprocessingDocument.Create(filePath, WordprocessingDocumentType.Document);
        var mainPart = doc.AddMainDocumentPart();
        mainPart.Document = new Document(new Body());
        var body = mainPart.Document.Body!;

        // Header
        body.Append(CreateHeading("SHRI RAM COLLEGE OF COMMERCE", 24, true));
        body.Append(CreateHeading("University of Delhi", 14, false));
        body.Append(CreateHeading("STUDENT PROFILE", 16, true));
        body.Append(new Paragraph());

        // Student details
        AddField(body, "Student Name", student.StudentName);
        AddField(body, "Roll Number", student.RollNumber ?? "N/A");
        AddField(body, "Aadhar Number", student.AadharNumber ?? "N/A");
        AddField(body, "Created Date", student.CreatedDate.ToString("dd/MM/yyyy"));

        // Footer
        body.Append(new Paragraph());
        body.Append(CreateParagraph($"Generated on: {DateTime.Now:dd/MM/yyyy HH:mm}", 10));

        mainPart.Document.Save();
    }

    private static void AddFormContent(Body body, AdmissionForm form)
    {
        // Header
        body.Append(CreateHeading("SHRI RAM COLLEGE OF COMMERCE", 24, true));
        body.Append(CreateHeading("University of Delhi", 14, false));
        body.Append(CreateHeading("ADMISSION FORM", 18, true));
        body.Append(new Paragraph());

        // Academic Details
        body.Append(CreateSectionHeader("ACADEMIC DETAILS"));
        AddField(body, "Academic Session", form.AcademicSession);
        AddField(body, "Course", form.Course);
        AddField(body, "College Roll No", form.CollegeRollNo);
        AddField(body, "DU Portal Form No", form.DuPortalFormNumber);
        AddField(body, "CUET Score", form.CuetScore);
        AddField(body, "Admission Category", form.AdmissionCategory);
        
        body.Append(new Paragraph());

        // Personal Details
        body.Append(CreateSectionHeader("PERSONAL DETAILS"));
        AddField(body, "Student Name", form.StudentName);
        AddField(body, "Gender", form.Gender);
        AddField(body, "Date of Birth", form.DateOfBirth);
        AddField(body, "Category", form.Category);
        AddField(body, "Nationality", form.Nationality);
        AddField(body, "Religion", form.Religion);
        AddField(body, "Blood Group", form.BloodGroup);
        AddField(body, "Aadhar Number", form.AadharNumber);
        
        body.Append(new Paragraph());

        // Contact Details
        body.Append(CreateSectionHeader("CONTACT DETAILS"));
        AddField(body, "Phone Number", form.PhoneNumber);
        AddField(body, "Alternate Phone", form.AlternatePhone);
        AddField(body, "Email", form.Email);
        AddField(body, "Permanent Address", form.PermanentAddress);
        AddField(body, "State", form.PermanentState);
        AddField(body, "Pincode", form.PermanentPincode);
        
        body.Append(new Paragraph());

        // Parent Details
        body.Append(CreateSectionHeader("PARENT DETAILS"));
        AddField(body, "Father's Name", form.FatherName);
        AddField(body, "Father's Occupation", form.FatherOccupation);
        AddField(body, "Father's Mobile", form.FatherMobile);
        AddField(body, "Mother's Name", form.MotherName);
        AddField(body, "Mother's Occupation", form.MotherOccupation);
        AddField(body, "Mother's Mobile", form.MotherMobile);
        
        body.Append(new Paragraph());

        // Education Details
        body.Append(CreateSectionHeader("CLASS XII DETAILS"));
        AddField(body, "Board", form.TwelfthBoard);
        AddField(body, "Year", form.TwelfthYear);
        AddField(body, "Percentage", form.TwelfthPercentage);
        AddField(body, "Institution", form.TwelfthInstitution);
        
        body.Append(new Paragraph());

        // Status
        AddField(body, "Status", form.Status.ToString());
        AddField(body, "Upload Date", form.UploadDate.ToString("dd/MM/yyyy HH:mm"));

        // Footer
        body.Append(new Paragraph());
        body.Append(CreateParagraph($"Generated on: {DateTime.Now:dd/MM/yyyy HH:mm}", 10));
    }

    private static Paragraph CreateHeading(string text, int fontSize, bool bold)
    {
        var run = new Run(new Text(text));
        var runProps = new RunProperties
        {
            FontSize = new FontSize { Val = (fontSize * 2).ToString() }
        };
        if (bold) runProps.Bold = new Bold();
        run.PrependChild(runProps);

        return new Paragraph(run)
        {
            ParagraphProperties = new ParagraphProperties
            {
                Justification = new Justification { Val = JustificationValues.Center }
            }
        };
    }

    private static Paragraph CreateSectionHeader(string text)
    {
        var run = new Run(new Text(text));
        run.PrependChild(new RunProperties
        {
            Bold = new Bold(),
            FontSize = new FontSize { Val = "24" },
            Color = new Color { Val = "800020" }
        });

        return new Paragraph(run)
        {
            ParagraphProperties = new ParagraphProperties
            {
                SpacingBetweenLines = new SpacingBetweenLines { Before = "200", After = "100" }
            }
        };
    }

    private static void AddField(Body body, string label, string? value)
    {
        var para = new Paragraph();
        
        var labelRun = new Run(new Text(label + ": "));
        labelRun.PrependChild(new RunProperties { Bold = new Bold() });
        para.Append(labelRun);
        
        para.Append(new Run(new Text(value ?? "N/A")));
        
        body.Append(para);
    }

    private static Paragraph CreateParagraph(string text, int fontSize)
    {
        var run = new Run(new Text(text));
        run.PrependChild(new RunProperties
        {
            FontSize = new FontSize { Val = (fontSize * 2).ToString() },
            Color = new Color { Val = "666666" }
        });
        return new Paragraph(run);
    }
}
