using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using DocumentFormat.OpenXml;
using DocumentFormat.OpenXml.Packaging;
using DocumentFormat.OpenXml.Spreadsheet;
using OCRAdmissionForms.Core.Entities;
using OCRAdmissionForms.Core.Enums;
using OCRAdmissionForms.Infrastructure.Data;

namespace OCRAdmissionForms.Web.Controllers;

[ApiController]
[Route("api/[controller]")]
public class ExportController : ControllerBase
{
    private readonly AppDbContext _context;
    private readonly IWebHostEnvironment _env;
    private readonly ILogger<ExportController> _logger;

    public ExportController(
        AppDbContext context,
        IWebHostEnvironment env,
        ILogger<ExportController> logger)
    {
        _context = context;
        _env = env;
        _logger = logger;
    }

    /// <summary>
    /// Export all forms to Excel
    /// </summary>
    [HttpGet("forms/excel")]
    public async Task<ActionResult> ExportFormsToExcel(
        [FromQuery] FormStatus? status = null,
        [FromQuery] string? course = null)
    {
        var query = _context.AdmissionForms.AsQueryable();

        if (status.HasValue)
        {
            query = query.Where(f => f.Status == status.Value);
        }

        if (!string.IsNullOrEmpty(course))
        {
            query = query.Where(f => f.Course == course);
        }

        var forms = await query.OrderBy(f => f.CollegeRollNo).ToListAsync();

        using var memStream = new MemoryStream();
        using (var document = SpreadsheetDocument.Create(memStream, SpreadsheetDocumentType.Workbook))
        {
            var workbookPart = document.AddWorkbookPart();
            workbookPart.Workbook = new Workbook();
            
            var worksheetPart = workbookPart.AddNewPart<WorksheetPart>();
            worksheetPart.Worksheet = new Worksheet(new SheetData());
            
            var sheets = document.WorkbookPart!.Workbook.AppendChild(new Sheets());
            var sheet = new Sheet
            {
                Id = document.WorkbookPart.GetIdOfPart(worksheetPart),
                SheetId = 1,
                Name = "Admission Forms"
            };
            sheets.Append(sheet);
            
            var sheetData = worksheetPart.Worksheet.GetFirstChild<SheetData>()!;
            
            // Header row
            var headerRow = new Row { RowIndex = 1 };
            var headers = new[]
            {
                "S.No", "College Roll No", "Student Name", "Academic Session", "Course",
                "DU Portal Form No", "CUET Score", "Date of Admission",
                "Gender", "Date of Birth", "Category", "Blood Group",
                "Aadhar Number", "Nationality", "Religion",
                "Father's Name", "Mother's Name",
                "Phone Number", "Email",
                "Permanent Address", "State", "Pincode",
                "XII Board", "XII Year", "XII Percentage",
                "Status", "Upload Date"
            };
            
            for (int i = 0; i < headers.Length; i++)
            {
                headerRow.Append(CreateCell(GetColumnName(i + 1), 1, headers[i]));
            }
            sheetData.Append(headerRow);
            
            // Data rows
            uint rowIndex = 2;
            int sNo = 1;
            foreach (var form in forms)
            {
                var row = new Row { RowIndex = rowIndex };
                var values = new[]
                {
                    sNo.ToString(),
                    form.CollegeRollNo ?? "",
                    form.StudentName ?? "",
                    form.AcademicSession ?? "",
                    form.Course ?? "",
                    form.DuPortalFormNumber ?? "",
                    form.CuetScore ?? "",
                    form.DateOfAdmission ?? "",
                    form.Gender ?? "",
                    form.DateOfBirth ?? "",
                    form.Category ?? "",
                    form.BloodGroup ?? "",
                    form.AadharNumber ?? "",
                    form.Nationality ?? "",
                    form.Religion ?? "",
                    form.FatherName ?? "",
                    form.MotherName ?? "",
                    form.PhoneNumber ?? "",
                    form.Email ?? "",
                    form.PermanentAddress ?? "",
                    form.PermanentState ?? "",
                    form.Pincode ?? "",
                    form.TwelfthBoard ?? "",
                    form.TwelfthYear ?? "",
                    form.TwelfthPercentage ?? "",
                    form.Status.ToString(),
                    form.UploadDate.ToString("yyyy-MM-dd HH:mm")
                };
                
                for (int i = 0; i < values.Length; i++)
                {
                    row.Append(CreateCell(GetColumnName(i + 1), rowIndex, values[i]));
                }
                sheetData.Append(row);
                rowIndex++;
                sNo++;
            }
            
            workbookPart.Workbook.Save();
        }

        memStream.Position = 0;
        var fileName = $"AdmissionForms_{DateTime.Now:yyyyMMdd_HHmmss}.xlsx";
        return File(memStream.ToArray(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", fileName);
    }

    /// <summary>
    /// Export students to Excel
    /// </summary>
    [HttpGet("students/excel")]
    public async Task<ActionResult> ExportStudentsToExcel()
    {
        var students = await _context.StudentProfiles
            .Include(p => p.Forms)
            .OrderBy(p => p.StudentName)
            .ToListAsync();

        using var memStream = new MemoryStream();
        using (var document = SpreadsheetDocument.Create(memStream, SpreadsheetDocumentType.Workbook))
        {
            var workbookPart = document.AddWorkbookPart();
            workbookPart.Workbook = new Workbook();
            
            var worksheetPart = workbookPart.AddNewPart<WorksheetPart>();
            worksheetPart.Worksheet = new Worksheet(new SheetData());
            
            var sheets = document.WorkbookPart!.Workbook.AppendChild(new Sheets());
            var sheet = new Sheet
            {
                Id = document.WorkbookPart.GetIdOfPart(worksheetPart),
                SheetId = 1,
                Name = "Students"
            };
            sheets.Append(sheet);
            
            var sheetData = worksheetPart.Worksheet.GetFirstChild<SheetData>()!;
            
            // Header row
            var headerRow = new Row { RowIndex = 1 };
            var headers = new[] { "S.No", "Student Name", "Roll Number", "Aadhar Number", "Verified", "Forms Count", "Created Date" };
            
            for (int i = 0; i < headers.Length; i++)
            {
                headerRow.Append(CreateCell(GetColumnName(i + 1), 1, headers[i]));
            }
            sheetData.Append(headerRow);
            
            // Data rows
            uint rowIndex = 2;
            int sNo = 1;
            foreach (var student in students)
            {
                var row = new Row { RowIndex = rowIndex };
                var values = new[]
                {
                    sNo.ToString(),
                    student.StudentName,
                    student.RollNumber ?? "",
                    student.AadharNumber ?? "",
                    "Yes", // Defaulting to Yes since verified in workflow
                    student.Forms.Count.ToString(),
                    student.CreatedDate.ToString("yyyy-MM-dd")
                };
                
                for (int i = 0; i < values.Length; i++)
                {
                    row.Append(CreateCell(GetColumnName(i + 1), rowIndex, values[i]));
                }
                sheetData.Append(row);
                rowIndex++;
                sNo++;
            }
            
            workbookPart.Workbook.Save();
        }

        memStream.Position = 0;
        var fileName = $"Students_{DateTime.Now:yyyyMMdd_HHmmss}.xlsx";
        return File(memStream.ToArray(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", fileName);
    }

    #region Helpers

    private static Cell CreateCell(string columnName, uint rowIndex, string value)
    {
        return new Cell
        {
            CellReference = columnName + rowIndex,
            CellValue = new CellValue(value),
            DataType = CellValues.String
        };
    }

    private static string GetColumnName(int columnNumber)
    {
        string columnName = "";
        while (columnNumber > 0)
        {
            int modulo = (columnNumber - 1) % 26;
            columnName = Convert.ToChar('A' + modulo) + columnName;
            columnNumber = (columnNumber - modulo) / 26;
        }
        return columnName;
    }

    #endregion
}
