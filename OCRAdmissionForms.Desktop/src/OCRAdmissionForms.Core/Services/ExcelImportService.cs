using System.IO;
using DocumentFormat.OpenXml.Packaging;
using DocumentFormat.OpenXml.Spreadsheet;
using Microsoft.EntityFrameworkCore;
using OCRAdmissionForms.Core.Data;
using OCRAdmissionForms.Core.Entities;

namespace OCRAdmissionForms.Core.Services;

/// <summary>
/// Service for importing data from Excel files
/// </summary>
public class ExcelImportService
{
    /// <summary>
    /// Import students from Excel file
    /// </summary>
    public async Task<ImportResult> ImportStudentsAsync(string filePath)
    {
        var result = new ImportResult();
        
        try
        {
            using var doc = SpreadsheetDocument.Open(filePath, false);
            var workbookPart = doc.WorkbookPart;
            if (workbookPart == null)
            {
                result.Errors.Add("Invalid Excel file");
                return result;
            }

            var sheet = workbookPart.Workbook.Sheets?.GetFirstChild<Sheet>();
            if (sheet?.Id?.Value == null)
            {
                result.Errors.Add("No worksheet found");
                return result;
            }

            var worksheetPart = (WorksheetPart)workbookPart.GetPartById(sheet.Id.Value);
            var rows = worksheetPart.Worksheet.Descendants<Row>().ToList();

            // Get header row to determine column mapping
            var headerRow = rows.FirstOrDefault();
            if (headerRow == null)
            {
                result.Errors.Add("Empty file");
                return result;
            }

            var headers = GetRowValues(headerRow, workbookPart);
            var columnMap = MapColumns(headers);

            // Import data rows
            using var context = new AppDbContext();
            
            foreach (var row in rows.Skip(1))
            {
                try
                {
                    var values = GetRowValues(row, workbookPart);
                    var student = ParseStudent(values, columnMap);
                    
                    if (!string.IsNullOrEmpty(student.StudentName))
                    {
                        context.StudentProfiles.Add(student);
                        result.Imported++;
                    }
                    else
                    {
                        result.Skipped++;
                    }
                }
                catch (Exception ex)
                {
                    result.Errors.Add($"Row {row.RowIndex}: {ex.Message}");
                    result.Skipped++;
                }
            }

            await context.SaveChangesAsync();
            result.Success = true;
        }
        catch (Exception ex)
        {
            result.Errors.Add($"Import failed: {ex.Message}");
        }

        return result;
    }

    /// <summary>
    /// Import admission forms from Excel
    /// </summary>
    public async Task<ImportResult> ImportFormsAsync(string filePath)
    {
        var result = new ImportResult();
        
        try
        {
            using var doc = SpreadsheetDocument.Open(filePath, false);
            var workbookPart = doc.WorkbookPart;
            if (workbookPart == null)
            {
                result.Errors.Add("Invalid Excel file");
                return result;
            }

            var sheet = workbookPart.Workbook.Sheets?.GetFirstChild<Sheet>();
            if (sheet?.Id?.Value == null)
            {
                result.Errors.Add("No worksheet found");
                return result;
            }

            var worksheetPart = (WorksheetPart)workbookPart.GetPartById(sheet.Id.Value);
            var rows = worksheetPart.Worksheet.Descendants<Row>().ToList();

            var headerRow = rows.FirstOrDefault();
            if (headerRow == null)
            {
                result.Errors.Add("Empty file");
                return result;
            }

            var headers = GetRowValues(headerRow, workbookPart);
            var columnMap = MapFormColumns(headers);

            using var context = new AppDbContext();
            
            foreach (var row in rows.Skip(1))
            {
                try
                {
                    var values = GetRowValues(row, workbookPart);
                    var form = ParseForm(values, columnMap);
                    
                    if (!string.IsNullOrEmpty(form.StudentName))
                    {
                        context.AdmissionForms.Add(form);
                        result.Imported++;
                    }
                    else
                    {
                        result.Skipped++;
                    }
                }
                catch (Exception ex)
                {
                    result.Errors.Add($"Row {row.RowIndex}: {ex.Message}");
                    result.Skipped++;
                }
            }

            await context.SaveChangesAsync();
            result.Success = true;
        }
        catch (Exception ex)
        {
            result.Errors.Add($"Import failed: {ex.Message}");
        }

        return result;
    }

    private static List<string> GetRowValues(Row row, WorkbookPart workbookPart)
    {
        var values = new List<string>();
        var sharedStrings = workbookPart.SharedStringTablePart?.SharedStringTable;

        foreach (var cell in row.Elements<Cell>())
        {
            var value = cell.CellValue?.Text ?? "";
            
            if (cell.DataType?.Value == CellValues.SharedString && sharedStrings != null)
            {
                if (int.TryParse(value, out var index))
                {
                    value = sharedStrings.ElementAt(index).InnerText;
                }
            }
            
            values.Add(value);
        }

        return values;
    }

    private static Dictionary<string, int> MapColumns(List<string> headers)
    {
        var map = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
        
        for (int i = 0; i < headers.Count; i++)
        {
            var header = headers[i].Trim().ToLower();
            
            if (header.Contains("name") && !header.Contains("father") && !header.Contains("mother"))
                map["StudentName"] = i;
            else if (header.Contains("roll"))
                map["RollNumber"] = i;
            else if (header.Contains("aadhar") || header.Contains("aadhaar"))
                map["AadharNumber"] = i;
        }

        return map;
    }

    private static Dictionary<string, int> MapFormColumns(List<string> headers)
    {
        var map = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
        
        for (int i = 0; i < headers.Count; i++)
        {
            var header = headers[i].Trim().ToLower();
            
            if (header.Contains("student") && header.Contains("name"))
                map["StudentName"] = i;
            else if (header.Contains("roll"))
                map["CollegeRollNo"] = i;
            else if (header.Contains("course"))
                map["Course"] = i;
            else if (header.Contains("gender"))
                map["Gender"] = i;
            else if (header.Contains("dob") || header.Contains("birth"))
                map["DateOfBirth"] = i;
            else if (header.Contains("phone") || header.Contains("mobile"))
                map["PhoneNumber"] = i;
            else if (header.Contains("email"))
                map["Email"] = i;
            else if (header.Contains("aadhar"))
                map["AadharNumber"] = i;
            else if (header.Contains("father"))
                map["FatherName"] = i;
            else if (header.Contains("mother"))
                map["MotherName"] = i;
        }

        return map;
    }

    private static StudentProfile ParseStudent(List<string> values, Dictionary<string, int> map)
    {
        return new StudentProfile
        {
            StudentName = GetValue(values, map, "StudentName") ?? "",
            RollNumber = GetValue(values, map, "RollNumber"),
            AadharNumber = GetValue(values, map, "AadharNumber"),
            CreatedDate = DateTime.Now
        };
    }

    private static AdmissionForm ParseForm(List<string> values, Dictionary<string, int> map)
    {
        return new AdmissionForm
        {
            StudentName = GetValue(values, map, "StudentName"),
            CollegeRollNo = GetValue(values, map, "CollegeRollNo"),
            Course = GetValue(values, map, "Course"),
            Gender = GetValue(values, map, "Gender"),
            DateOfBirth = GetValue(values, map, "DateOfBirth"),
            PhoneNumber = GetValue(values, map, "PhoneNumber"),
            Email = GetValue(values, map, "Email"),
            AadharNumber = GetValue(values, map, "AadharNumber"),
            FatherName = GetValue(values, map, "FatherName"),
            MotherName = GetValue(values, map, "MotherName"),
            Status = FormStatus.Uploaded,
            UploadDate = DateTime.Now
        };
    }

    private static string? GetValue(List<string> values, Dictionary<string, int> map, string key)
    {
        if (map.TryGetValue(key, out var index) && index < values.Count)
        {
            var value = values[index].Trim();
            return string.IsNullOrEmpty(value) ? null : value;
        }
        return null;
    }
}

public class ImportResult
{
    public bool Success { get; set; }
    public int Imported { get; set; }
    public int Skipped { get; set; }
    public List<string> Errors { get; set; } = new();
}
