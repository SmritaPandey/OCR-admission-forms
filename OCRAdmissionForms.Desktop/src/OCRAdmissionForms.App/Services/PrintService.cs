using System.IO;
using System.Printing;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Documents;
using System.Windows.Media;
using OCRAdmissionForms.Core.Entities;

namespace OCRAdmissionForms.App.Services;

/// <summary>
/// Service for printing student profiles and admission forms
/// </summary>
public class PrintService
{
    /// <summary>
    /// Print a student profile card
    /// </summary>
    public void PrintStudentProfile(StudentProfile student)
    {
        var doc = CreateStudentDocument(student);
        PrintDocument(doc, "Student Profile");
    }

    /// <summary>
    /// Print an admission form
    /// </summary>
    public void PrintAdmissionForm(AdmissionForm form)
    {
        var doc = CreateFormDocument(form);
        PrintDocument(doc, "Admission Form");
    }

    /// <summary>
    /// Print multiple students
    /// </summary>
    public void PrintBulkStudents(IEnumerable<StudentProfile> students)
    {
        var doc = new FlowDocument
        {
            PagePadding = new Thickness(50),
            FontFamily = new FontFamily("Segoe UI")
        };

        foreach (var student in students)
        {
            doc.Blocks.Add(CreateStudentSection(student));
            doc.Blocks.Add(new Paragraph(new Run(" ")) { BreakPageBefore = true });
        }

        PrintDocument(doc, "Student Profiles");
    }

    /// <summary>
    /// Print multiple forms
    /// </summary>
    public void PrintBulkForms(IEnumerable<AdmissionForm> forms)
    {
        var doc = new FlowDocument
        {
            PagePadding = new Thickness(50),
            FontFamily = new FontFamily("Segoe UI")
        };

        foreach (var form in forms)
        {
            doc.Blocks.Add(CreateFormSection(form));
            doc.Blocks.Add(new Paragraph(new Run(" ")) { BreakPageBefore = true });
        }

        PrintDocument(doc, "Admission Forms");
    }

    private FlowDocument CreateStudentDocument(StudentProfile student)
    {
        return new FlowDocument
        {
            PagePadding = new Thickness(50),
            FontFamily = new FontFamily("Segoe UI"),
            Blocks = { CreateStudentSection(student) }
        };
    }

    private FlowDocument CreateFormDocument(AdmissionForm form)
    {
        return new FlowDocument
        {
            PagePadding = new Thickness(50),
            FontFamily = new FontFamily("Segoe UI"),
            Blocks = { CreateFormSection(form) }
        };
    }

    private Section CreateStudentSection(StudentProfile student)
    {
        var section = new Section();
        
        // Header
        section.Blocks.Add(new Paragraph(new Run("SHRI RAM COLLEGE OF COMMERCE"))
        {
            FontSize = 16,
            FontWeight = FontWeights.Bold,
            TextAlignment = TextAlignment.Center,
            Foreground = new SolidColorBrush(Color.FromRgb(0x1E, 0x3A, 0x5F))
        });
        
        section.Blocks.Add(new Paragraph(new Run("University of Delhi"))
        {
            FontSize = 12,
            TextAlignment = TextAlignment.Center,
            Foreground = Brushes.Gray
        });

        section.Blocks.Add(new Paragraph(new Run("STUDENT PROFILE"))
        {
            FontSize = 14,
            FontWeight = FontWeights.Bold,
            TextAlignment = TextAlignment.Center,
            Margin = new Thickness(0, 20, 0, 20),
            BorderBrush = new SolidColorBrush(Color.FromRgb(0x80, 0x00, 0x20)),
            BorderThickness = new Thickness(0, 0, 0, 2)
        });

        // Student details table
        var table = new Table { CellSpacing = 5 };
        table.Columns.Add(new TableColumn { Width = new GridLength(150) });
        table.Columns.Add(new TableColumn { Width = new GridLength(300) });
        
        var rowGroup = new TableRowGroup();
        AddTableRow(rowGroup, "Student Name", student.StudentName);
        AddTableRow(rowGroup, "Roll Number", student.RollNumber ?? "N/A");
        AddTableRow(rowGroup, "Aadhar Number", student.AadharNumber ?? "N/A");
        AddTableRow(rowGroup, "Created Date", student.CreatedDate.ToString("dd/MM/yyyy"));
        
        table.RowGroups.Add(rowGroup);
        section.Blocks.Add(table);

        // Footer
        section.Blocks.Add(new Paragraph(new Run($"Printed on: {DateTime.Now:dd/MM/yyyy HH:mm}"))
        {
            FontSize = 10,
            Foreground = Brushes.Gray,
            TextAlignment = TextAlignment.Right,
            Margin = new Thickness(0, 30, 0, 0)
        });

        return section;
    }

    private Section CreateFormSection(AdmissionForm form)
    {
        var section = new Section();
        
        // Header
        section.Blocks.Add(new Paragraph(new Run("SHRI RAM COLLEGE OF COMMERCE"))
        {
            FontSize = 16,
            FontWeight = FontWeights.Bold,
            TextAlignment = TextAlignment.Center,
            Foreground = new SolidColorBrush(Color.FromRgb(0x1E, 0x3A, 0x5F))
        });
        
        section.Blocks.Add(new Paragraph(new Run("ADMISSION FORM"))
        {
            FontSize = 14,
            FontWeight = FontWeights.Bold,
            TextAlignment = TextAlignment.Center,
            Margin = new Thickness(0, 10, 0, 20)
        });

        // Form details
        var table = new Table { CellSpacing = 3 };
        table.Columns.Add(new TableColumn { Width = new GridLength(180) });
        table.Columns.Add(new TableColumn { Width = new GridLength(300) });
        
        var rowGroup = new TableRowGroup();
        
        // Academic
        AddSectionHeader(rowGroup, "Academic Details");
        AddTableRow(rowGroup, "Session", form.AcademicSession);
        AddTableRow(rowGroup, "Course", form.Course);
        AddTableRow(rowGroup, "College Roll No", form.CollegeRollNo);
        AddTableRow(rowGroup, "CUET Score", form.CuetScore);
        
        // Personal
        AddSectionHeader(rowGroup, "Personal Details");
        AddTableRow(rowGroup, "Student Name", form.StudentName);
        AddTableRow(rowGroup, "Gender", form.Gender);
        AddTableRow(rowGroup, "Date of Birth", form.DateOfBirth);
        AddTableRow(rowGroup, "Category", form.Category);
        AddTableRow(rowGroup, "Aadhar", form.AadharNumber);
        
        // Contact
        AddSectionHeader(rowGroup, "Contact Details");
        AddTableRow(rowGroup, "Phone", form.PhoneNumber);
        AddTableRow(rowGroup, "Email", form.Email);
        AddTableRow(rowGroup, "Address", form.PermanentAddress);
        AddTableRow(rowGroup, "Pincode", form.Pincode ?? form.PermanentPincode);
        
        // Parents
        AddSectionHeader(rowGroup, "Parent Details");
        AddTableRow(rowGroup, "Father's Name", form.FatherName);
        AddTableRow(rowGroup, "Mother's Name", form.MotherName);
        
        // Education
        AddSectionHeader(rowGroup, "Class XII Details");
        AddTableRow(rowGroup, "Board", form.TwelfthBoard);
        AddTableRow(rowGroup, "Year", form.TwelfthYear);
        AddTableRow(rowGroup, "Percentage", form.TwelfthPercentage);
        
        table.RowGroups.Add(rowGroup);
        section.Blocks.Add(table);

        // Status
        section.Blocks.Add(new Paragraph(new Run($"Status: {form.Status}"))
        {
            FontWeight = FontWeights.Bold,
            Margin = new Thickness(0, 20, 0, 0)
        });

        // Footer
        section.Blocks.Add(new Paragraph(new Run($"Printed on: {DateTime.Now:dd/MM/yyyy HH:mm}"))
        {
            FontSize = 10,
            Foreground = Brushes.Gray,
            TextAlignment = TextAlignment.Right
        });

        return section;
    }

    private static void AddSectionHeader(TableRowGroup group, string text)
    {
        var row = new TableRow();
        var cell = new TableCell(new Paragraph(new Run(text))
        {
            FontWeight = FontWeights.Bold,
            Foreground = new SolidColorBrush(Color.FromRgb(0x80, 0x00, 0x20)),
            Margin = new Thickness(0, 10, 0, 5)
        });
        cell.ColumnSpan = 2;
        row.Cells.Add(cell);
        group.Rows.Add(row);
    }

    private static void AddTableRow(TableRowGroup group, string label, string? value)
    {
        var row = new TableRow();
        row.Cells.Add(new TableCell(new Paragraph(new Run(label + ":"))
        {
            FontWeight = FontWeights.SemiBold
        }));
        row.Cells.Add(new TableCell(new Paragraph(new Run(value ?? "N/A"))));
        group.Rows.Add(row);
    }

    private static void PrintDocument(FlowDocument doc, string title)
    {
        var printDialog = new PrintDialog();
        if (printDialog.ShowDialog() == true)
        {
            doc.PageWidth = printDialog.PrintableAreaWidth;
            doc.PageHeight = printDialog.PrintableAreaHeight;
            
            var paginator = ((IDocumentPaginatorSource)doc).DocumentPaginator;
            printDialog.PrintDocument(paginator, title);
        }
    }
}
