using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using DocumentFormat.OpenXml;
using DocumentFormat.OpenXml.Packaging;
using DocumentFormat.OpenXml.Spreadsheet;
using OCRAdmissionForms.Core.Entities;
using OCRAdmissionForms.Core.Interfaces;

namespace OCRAdmissionForms.Infrastructure.Services;

public class OpenXmlExcelService : IExcelService
{
    public byte[] ExportAdmissionForms(IEnumerable<AdmissionForm> forms)
    {
        using var memoryStream = new MemoryStream();
        using (var spreadsheetDocument = SpreadsheetDocument.Create(memoryStream, SpreadsheetDocumentType.Workbook))
        {
            var workbookPart = spreadsheetDocument.AddWorkbookPart();
            workbookPart.Workbook = new Workbook();

            var worksheetPart = workbookPart.AddNewPart<WorksheetPart>();
            worksheetPart.Worksheet = new Worksheet(new SheetData());

            var sheets = spreadsheetDocument.WorkbookPart.Workbook.AppendChild(new Sheets());
            var sheet = new Sheet()
            {
                Id = spreadsheetDocument.WorkbookPart.GetIdOfPart(worksheetPart),
                SheetId = 1,
                Name = "AdmissionForms"
            };
            sheets.Append(sheet);

            var sheetData = worksheetPart.Worksheet.GetFirstChild<SheetData>();

            // Create Header Row via Reflection
            var properties = typeof(AdmissionForm).GetProperties()
                .Where(p => p.PropertyType == typeof(string) || p.PropertyType == typeof(int) || p.PropertyType == typeof(DateTime) || p.PropertyType == typeof(DateTime?))
                .ToList();

            var headerRow = new Row();
            foreach (var prop in properties)
            {
                headerRow.Append(CreateCell(prop.Name));
            }
            sheetData.Append(headerRow);

            // Create Data Rows
            foreach (var form in forms)
            {
                var row = new Row();
                foreach (var prop in properties)
                {
                    var val = prop.GetValue(form)?.ToString() ?? "";
                    row.Append(CreateCell(val));
                }
                sheetData.Append(row);
            }

            workbookPart.Workbook.Save();
        }

        return memoryStream.ToArray();
    }

    public IEnumerable<AdmissionForm> ImportAdmissionForms(Stream excelStream)
    {
        // Basic import skeleton - implementing robust import requires careful mapping
        var list = new List<AdmissionForm>();
        using (var spreadsheetDocument = SpreadsheetDocument.Open(excelStream, false))
        {
            var workbookPart = spreadsheetDocument.WorkbookPart;
            var sheet = workbookPart.Workbook.Descendants<Sheet>().FirstOrDefault(s => s.Name == "AdmissionForms");
            if (sheet == null) return list;

            var worksheetPart = (WorksheetPart)workbookPart.GetPartById(sheet.Id);
            var sheetData = worksheetPart.Worksheet.Elements<SheetData>().First();
            var rows = sheetData.Elements<Row>().ToList();

            // Assume first row is header, map by index
            // Simplified for now: just return empty list as placeholder for robust logic
            // Real implementation would read headers, map to properties, then read rows
        }
        return list;
    }

    private Cell CreateCell(string text)
    {
        return new Cell(new InlineString(new Text(text))) { DataType = CellValues.InlineString };
    }
}
