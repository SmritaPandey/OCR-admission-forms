using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using ClosedXML.Excel;
using OCRAdmissionForms.Core.Entities;
using QuestPDF.Fluent;
using QuestPDF.Helpers;
using QuestPDF.Infrastructure;

namespace OCRAdmissionForms.Core.Services;

/// <summary>
/// Comprehensive export service: Excel, CSV, PDF
/// </summary>
public class ExcelExportService
{
    // ── Field Section Definitions ────────────────────────────
    public static readonly Dictionary<string, List<(string Header, Func<AdmissionForm, string> Getter)>> FieldSections = new()
    {
        ["Personal"] = new()
        {
            ("First Name", f => f.FirstName ?? ""),
            ("Middle Name", f => f.MiddleName ?? ""),
            ("Surname", f => f.Surname ?? ""),
            ("Student Name", f => f.StudentName ?? ""),
            ("Gender", f => f.Gender ?? ""),
            ("Date of Birth", f => f.DateOfBirth ?? ""),
            ("Category", f => f.Category ?? ""),
            ("Blood Group", f => f.BloodGroup ?? ""),
            ("Nationality", f => f.Nationality ?? ""),
            ("Religion", f => f.Religion ?? ""),
            ("Minority Category", f => f.MinorityCategory ?? ""),
            ("Aadhar Number", f => f.AadharNumber ?? ""),
            ("Annual Income", f => f.AnnualIncome ?? ""),
            ("Below Poverty Line", f => f.BelowPovertyLine ?? ""),

        },
        ["Academic"] = new()
        {
            ("Academic Session", f => f.AcademicSession ?? ""),
            ("Course", f => f.Course ?? ""),
            ("Admission Category", f => f.AdmissionCategory ?? ""),
            ("College Roll No", f => f.CollegeRollNo ?? ""),
            ("DU Portal Form No", f => f.DuPortalFormNumber ?? ""),
            ("Date of Admission", f => f.DateOfAdmission ?? ""),
            ("DU Enrollment Number", f => f.DuEnrollmentNumber ?? ""),
            ("Hindi Medium Preference", f => f.HindiMediumPreference ?? ""),
        },
        ["CUET Scores"] = new()
        {
            ("CUET Score", f => f.CuetScore ?? ""),
            ("CUET Subject 1", f => f.CuetSubject1 ?? ""),
            ("CUET Total 1", f => f.CuetTotalScore1 ?? ""),
            ("CUET Obtained 1", f => f.CuetScoreObtained1 ?? ""),
            ("CUET Subject 2", f => f.CuetSubject2 ?? ""),
            ("CUET Total 2", f => f.CuetTotalScore2 ?? ""),
            ("CUET Obtained 2", f => f.CuetScoreObtained2 ?? ""),
            ("CUET Subject 3", f => f.CuetSubject3 ?? ""),
            ("CUET Total 3", f => f.CuetTotalScore3 ?? ""),
            ("CUET Obtained 3", f => f.CuetScoreObtained3 ?? ""),
            ("CUET Subject 4", f => f.CuetSubject4 ?? ""),
            ("CUET Total 4", f => f.CuetTotalScore4 ?? ""),
            ("CUET Obtained 4", f => f.CuetScoreObtained4 ?? ""),
            ("CUET Subject 5", f => f.CuetSubject5 ?? ""),
            ("CUET Total 5", f => f.CuetTotalScore5 ?? ""),
            ("CUET Obtained 5", f => f.CuetScoreObtained5 ?? ""),
            ("CUET Subject 6", f => f.CuetSubject6 ?? ""),
            ("CUET Total 6", f => f.CuetTotalScore6 ?? ""),
            ("CUET Obtained 6", f => f.CuetScoreObtained6 ?? ""),
            ("CUET Total (All)", f => f.CuetTotalScoreAll ?? ""),
            ("CUET Obtained (All)", f => f.CuetScoreObtainedAll ?? ""),
        },
        ["12th Class"] = new()
        {
            ("XII Board", f => f.TwelfthBoard ?? ""),
            ("XII Year", f => f.TwelfthYear ?? ""),
            ("XII Roll Number", f => f.TwelfthRollNumber ?? ""),
            ("XII Institution", f => f.TwelfthInstitution ?? ""),
            ("XII Percentage", f => f.TwelfthPercentage ?? f.Class12Percentage ?? ""),
            ("Hindi Studied Upto", f => f.HindiStudiedUpto ?? ""),
        },
        ["10th Class"] = new()
        {
            ("X Board", f => f.TenthBoard ?? ""),
            ("X Year", f => f.TenthYear ?? ""),
            ("X Percentage", f => f.TenthPercentage ?? ""),
            ("X School", f => f.TenthSchool ?? ""),
        },
        ["Parents"] = new()
        {
            ("Father's Name", f => f.FatherName ?? ""),
            ("Father's Occupation", f => f.FatherOccupation ?? ""),
            ("Father's Designation", f => f.FatherDesignation ?? ""),
            ("Father's Organization", f => f.FatherOrganization ?? ""),
            ("Father's Mobile", f => f.FatherMobile ?? ""),
            ("Father's Phone", f => f.FatherPhone ?? ""),
            ("Father's Email", f => f.FatherEmail ?? ""),
            ("Father's Annual Income", f => f.FatherAnnualIncome ?? ""),
            ("Mother's Name", f => f.MotherName ?? ""),
            ("Mother's Occupation", f => f.MotherOccupation ?? ""),
            ("Mother's Designation", f => f.MotherDesignation ?? ""),
            ("Mother's Organization", f => f.MotherOrganization ?? ""),
            ("Mother's Mobile", f => f.MotherMobile ?? ""),
            ("Mother's Phone", f => f.MotherPhone ?? ""),
            ("Mother's Email", f => f.MotherEmail ?? ""),
            ("Mother's Annual Income", f => f.MotherAnnualIncome ?? ""),
        },
        ["Contact & Address"] = new()
        {
            ("Phone Number", f => f.PhoneNumber ?? ""),
            ("Alternate Phone", f => f.AlternatePhone ?? ""),
            ("Email", f => f.Email ?? ""),
            ("Permanent Address", f => f.PermanentAddress ?? ""),
            ("Permanent State", f => f.PermanentState ?? ""),
            ("Permanent Pincode", f => f.PermanentPincode ?? f.Pincode ?? ""),
            ("Correspondence Address", f => f.CorrespondenceAddress ?? ""),
            ("Correspondence State", f => f.CorrespondenceState ?? ""),
            ("Correspondence Pincode", f => f.CorrespondencePincode ?? ""),
            ("Local Address", f => f.LocalAddress ?? ""),
        },
        ["Guardian"] = new()
        {
            ("Guardian Name", f => f.GuardianName ?? ""),
            ("Guardian Relation", f => f.GuardianRelation ?? ""),
            ("Guardian Mobile", f => f.GuardianMobile ?? ""),
            ("Guardian Email", f => f.GuardianEmail ?? ""),
            ("Guardian Address", f => f.GuardianAddress ?? ""),
            ("Guardian Organization", f => f.GuardianOrganization ?? ""),
        },
        ["Emergency"] = new()
        {
            ("Emergency Contact Name", f => f.EmergencyContactName ?? ""),
            ("Emergency Contact Phone", f => f.EmergencyContactPhone ?? ""),
        },
        ["Certificates"] = new()
        {
            ("Category Certificate Authority", f => f.CategoryCertificateAuthority ?? ""),
            ("Category Certificate Number", f => f.CategoryCertificateNumber ?? ""),
            ("Category Certificate Date", f => f.CategoryCertificateDate ?? ""),
            ("Disability Type", f => f.DisabilityType ?? ""),
            ("Disability Percentage", f => f.DisabilityPercentage ?? ""),
            ("UDID Number", f => f.UdidNumber ?? ""),
        },
        ["Documents Checklist"] = new()
        {
            ("Doc: Admission Form", f => (f.DocAdmissionForm ?? false) ? "Yes" : "No"),
            ("Doc: Photographs", f => (f.DocPhotographs ?? false) ? "Yes" : "No"),
            ("Doc: CUET Scorecard", f => (f.DocCuetScorecard ?? false) ? "Yes" : "No"),
            ("Doc: XII Marksheet", f => (f.DocClassXiiMarksheet ?? false) ? "Yes" : "No"),
            ("Doc: X Certificate", f => (f.DocClassXCertificate ?? false) ? "Yes" : "No"),
            ("Doc: XII Certificate", f => (f.DocClassXiiCertificate ?? false) ? "Yes" : "No"),
            ("Doc: Character Certificate", f => (f.DocCharacterCertificate ?? false) ? "Yes" : "No"),
            ("Doc: Caste Certificate", f => (f.DocCasteCertificate ?? false) ? "Yes" : "No"),
            ("Doc: Migration Certificate", f => (f.DocMigrationCertificate ?? false) ? "Yes" : "No"),
            ("Doc: Transfer Certificate", f => (f.DocTransferCertificate ?? false) ? "Yes" : "No"),
            ("Doc: Gap Certificate", f => (f.DocGapCertificate ?? false) ? "Yes" : "No"),
            ("Doc: Income Certificate", f => (f.DocIncomeCertificate ?? false) ? "Yes" : "No"),
            ("Doc: Domicile Certificate", f => (f.DocDomicileCertificate ?? false) ? "Yes" : "No"),
            ("Doc: Aadhar Card", f => (f.DocAadharCard ?? false) ? "Yes" : "No"),
            ("Doc: Medical Fitness", f => (f.DocMedicalFitness ?? false) ? "Yes" : "No"),
            ("Doc: Anti-Ragging Undertaking", f => (f.DocUndertakingRagging ?? false) ? "Yes" : "No"),
        },
        ["Declarations"] = new()
        {
            ("Declaration Date", f => f.DeclarationDate ?? ""),
            ("Declaration Place", f => f.DeclarationPlace ?? ""),
            ("Student Declaration Name", f => f.StudentDeclarationName ?? ""),
            ("Student Declaration Date", f => f.StudentDeclarationDate ?? ""),
            ("Student Declaration Place", f => f.StudentDeclarationPlace ?? ""),
            ("Parent/Guardian Name", f => f.ParentGuardianName ?? ""),
            ("Parent/Guardian Relationship", f => f.ParentGuardianRelationship ?? ""),
            ("Parent/Guardian Course", f => f.ParentGuardianCourse ?? ""),
            ("Parent/Guardian Date", f => f.ParentGuardianDate ?? ""),
            ("Parent/Guardian Place", f => f.ParentGuardianPlace ?? ""),
        },
        ["Metadata"] = new()
        {
            ("Status", f => f.Status.ToString()),
            ("Upload Date", f => f.UploadDate.ToString("yyyy-MM-dd HH:mm")),
            ("Verified Date", f => f.VerifiedDate?.ToString("yyyy-MM-dd") ?? ""),
            ("Verified By", f => f.VerifiedBy ?? ""),
            ("OCR Provider", f => f.OcrProvider ?? ""),
            ("File Name", f => f.Filename ?? ""),
        },
    };

    // ── Always-included columns ─────────────────────────────
    private static readonly List<(string Header, Func<AdmissionForm, string> Getter)> CoreColumns = new()
    {
        ("S.No", _ => ""),  // filled separately
        ("College Roll No", f => f.CollegeRollNo ?? ""),
        ("Student Name", f => f.StudentName ?? ""),
        ("Course", f => f.Course ?? ""),
    };

    // ── Export Students (Excel) ─────────────────────────────
    public async Task ExportStudentsAsync(IEnumerable<StudentProfile> students, string filePath)
    {
        await Task.Run(() =>
        {
            using var wb = new XLWorkbook();
            var ws = wb.Worksheets.Add("Students");

            // Headers
            var headers = new[] { "S.No", "Student Name", "Roll Number", "Aadhar Number", "Forms Count", "Created Date", "Updated Date" };
            for (int i = 0; i < headers.Length; i++)
                ws.Cell(1, i + 1).Value = headers[i];

            StyleHeaderRow(ws, headers.Length);

            // Data
            int row = 2, sNo = 1;
            foreach (var s in students)
            {
                ws.Cell(row, 1).Value = sNo;
                ws.Cell(row, 2).Value = s.StudentName ?? "";
                ws.Cell(row, 3).Value = s.RollNumber ?? "";
                ws.Cell(row, 4).Value = s.AadharNumber ?? "";
                ws.Cell(row, 5).Value = s.Forms?.Count ?? 0;
                ws.Cell(row, 6).Value = s.CreatedDate.ToString("yyyy-MM-dd");
                ws.Cell(row, 7).Value = s.UpdatedDate.ToString("yyyy-MM-dd");
                row++; sNo++;
            }

            ws.Columns().AdjustToContents(1, 80);
            ws.SheetView.FreezeRows(1);
            wb.SaveAs(filePath);
        });
    }

    // ── Export Forms (Excel) with section selection ──────────
    public async Task ExportFormsAsync(IEnumerable<AdmissionForm> forms, string filePath,
        IEnumerable<string>? selectedSections = null)
    {
        await Task.Run(() =>
        {
            using var wb = new XLWorkbook();
            var ws = wb.Worksheets.Add("Admission Forms");
            var columns = BuildColumnList(selectedSections);

            // Headers
            for (int i = 0; i < columns.Count; i++)
                ws.Cell(1, i + 1).Value = columns[i].Header;

            StyleHeaderRow(ws, columns.Count);

            // Data
            int row = 2, sNo = 1;
            foreach (var f in forms)
            {
                for (int i = 0; i < columns.Count; i++)
                {
                    var val = columns[i].Header == "S.No" ? sNo.ToString() : columns[i].Getter(f);
                    ws.Cell(row, i + 1).Value = val;
                }
                row++; sNo++;
            }

            ws.Columns().AdjustToContents(1, 50);
            ws.SheetView.FreezeRows(1);
            wb.SaveAs(filePath);
        });
    }

    // ── Export Forms (CSV) ───────────────────────────────────
    public async Task ExportFormsToCsvAsync(IEnumerable<AdmissionForm> forms, string filePath,
        IEnumerable<string>? selectedSections = null)
    {
        await Task.Run(() =>
        {
            var columns = BuildColumnList(selectedSections);
            var sb = new StringBuilder();

            // Header
            sb.AppendLine(string.Join(",", columns.Select(c => EscapeCsv(c.Header))));

            // Data
            int sNo = 1;
            foreach (var f in forms)
            {
                var values = columns.Select(c =>
                    EscapeCsv(c.Header == "S.No" ? sNo.ToString() : c.Getter(f)));
                sb.AppendLine(string.Join(",", values));
                sNo++;
            }

            File.WriteAllText(filePath, sb.ToString(), Encoding.UTF8);
        });
    }

    // ── Export Forms (PDF via QuestPDF) ──────────────────────
    public async Task ExportFormsToPdfAsync(IEnumerable<AdmissionForm> forms, string filePath,
        IEnumerable<string>? selectedSections = null)
    {
        await Task.Run(() =>
        {
            QuestPDF.Settings.License = QuestPDF.Infrastructure.LicenseType.Community;
            var columns = BuildColumnList(selectedSections);
            // Limit to reasonable columns for PDF (max 12 to fit on a page)
            var pdfCols = columns.Take(12).ToList();
            var formsList = forms.ToList();

            QuestPDF.Fluent.Document.Create(container =>
            {
                container.Page(page =>
                {
                    page.Size(QuestPDF.Helpers.PageSizes.A4.Landscape());
                    page.Margin(20);
                    page.DefaultTextStyle(x => x.FontSize(8));

                    page.Header().Column(col =>
                    {
                        col.Item().AlignCenter().Text("SRCC Student Document Management System")
                            .FontSize(14).Bold().FontColor(QuestPDF.Helpers.Colors.Blue.Darken3);
                        col.Item().AlignCenter().Text($"Admission Forms Export — {DateTime.Now:dd MMM yyyy HH:mm}")
                            .FontSize(10).FontColor(QuestPDF.Helpers.Colors.Grey.Medium);
                        col.Item().AlignCenter().Text($"Total Records: {formsList.Count}")
                            .FontSize(9).FontColor(QuestPDF.Helpers.Colors.Grey.Darken1);
                        col.Item().PaddingVertical(4).LineHorizontal(1).LineColor(QuestPDF.Helpers.Colors.Grey.Lighten2);
                    });

                    page.Content().Table(table =>
                    {
                        table.ColumnsDefinition(def =>
                        {
                            foreach (var _ in pdfCols)
                                def.RelativeColumn();
                        });

                        // Header
                        foreach (var col in pdfCols)
                        {
                            table.Cell().Background(QuestPDF.Helpers.Colors.Blue.Darken3)
                                .Padding(4).Text(col.Header).FontColor(QuestPDF.Helpers.Colors.White)
                                .FontSize(7).Bold();
                        }

                        // Data
                        int sNo = 1;
                        bool alt = false;
                        foreach (var f in formsList)
                        {
                            var bg = alt ? QuestPDF.Helpers.Colors.Grey.Lighten4 : QuestPDF.Helpers.Colors.White;
                            foreach (var col in pdfCols)
                            {
                                var val = col.Header == "S.No" ? sNo.ToString() : col.Getter(f);
                                table.Cell().Background(bg).BorderBottom(1).BorderColor(QuestPDF.Helpers.Colors.Grey.Lighten3)
                                    .Padding(3).Text(val).FontSize(7);
                            }
                            sNo++; alt = !alt;
                        }
                    });

                    page.Footer().AlignCenter().Text(x =>
                    {
                        x.Span("Page ");
                        x.CurrentPageNumber();
                        x.Span(" of ");
                        x.TotalPages();
                    });
                });
            }).GeneratePdf(filePath);
        });
    }

    // ── Export Students (CSV) ────────────────────────────────
    public async Task ExportStudentsToCsvAsync(IEnumerable<StudentProfile> students, string filePath)
    {
        await Task.Run(() =>
        {
            var sb = new StringBuilder();
            sb.AppendLine("S.No,Student Name,Roll Number,Aadhar Number,Forms Count,Created Date,Updated Date");

            int sNo = 1;
            foreach (var s in students)
            {
                sb.AppendLine(string.Join(",",
                    sNo.ToString(),
                    EscapeCsv(s.StudentName ?? ""),
                    EscapeCsv(s.RollNumber ?? ""),
                    EscapeCsv(s.AadharNumber ?? ""),
                    (s.Forms?.Count ?? 0).ToString(),
                    s.CreatedDate.ToString("yyyy-MM-dd"),
                    s.UpdatedDate.ToString("yyyy-MM-dd")));
                sNo++;
            }

            File.WriteAllText(filePath, sb.ToString(), Encoding.UTF8);
        });
    }

    // ── Helpers ──────────────────────────────────────────────
    private List<(string Header, Func<AdmissionForm, string> Getter)> BuildColumnList(IEnumerable<string>? selectedSections)
    {
        var columns = new List<(string Header, Func<AdmissionForm, string> Getter)>();
        columns.AddRange(CoreColumns);

        var sections = selectedSections?.ToHashSet() ?? FieldSections.Keys.ToHashSet();

        foreach (var sectionName in FieldSections.Keys)
        {
            if (sections.Contains(sectionName))
            {
                columns.AddRange(FieldSections[sectionName]);
            }
        }

        return columns;
    }

    private static string EscapeCsv(string value)
    {
        if (string.IsNullOrEmpty(value)) return "";
        if (value.Contains(',') || value.Contains('"') || value.Contains('\n'))
            return $"\"{value.Replace("\"", "\"\"")}\"";
        return value;
    }

    private static void StyleHeaderRow(IXLWorksheet ws, int columnCount)
    {
        var headerRange = ws.Range(1, 1, 1, columnCount);
        headerRange.Style.Font.Bold = true;
        headerRange.Style.Fill.BackgroundColor = XLColor.FromHtml("#1B365D"); // SRCC Navy
        headerRange.Style.Font.FontColor = XLColor.White;
        headerRange.Style.Alignment.Horizontal = XLAlignmentHorizontalValues.Center;
        headerRange.Style.Border.BottomBorder = XLBorderStyleValues.Thin;
    }
}
