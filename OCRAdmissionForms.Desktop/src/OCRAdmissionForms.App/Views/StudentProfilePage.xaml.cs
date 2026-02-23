using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using Microsoft.EntityFrameworkCore;
using Microsoft.Win32;
using OCRAdmissionForms.Core.Data;
using OCRAdmissionForms.Core.Entities;
using QuestPDF.Fluent;
using QuestPDF.Helpers;
using QuestPDF.Infrastructure;

namespace OCRAdmissionForms.App.Views;

public partial class StudentProfilePage : Page
{
    private readonly int _studentId;
    private StudentProfile? _student;
    private AdmissionForm? _latestForm;

    public StudentProfilePage(int studentId)
    {
        InitializeComponent();
        _studentId = studentId;
        Loaded += StudentProfilePage_Loaded;
    }

    public StudentProfilePage(StudentProfile student) : this(student.Id) { }

    private async void StudentProfilePage_Loaded(object sender, RoutedEventArgs e)
    {
        await LoadStudentAsync();
    }

    private async Task LoadStudentAsync()
    {
        using var db = new AppDbContext();
        _student = await db.StudentProfiles
            .Include(s => s.Forms)
            .Include(s => s.Documents)
            .FirstOrDefaultAsync(s => s.Id == _studentId);

        if (_student == null)
        {
            MessageBox.Show("Student not found", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
            return;
        }

        // Get the latest form with most data (highest field count = best extraction)
        _latestForm = _student.Forms
            .OrderByDescending(f => f.Status == FormStatus.Verified ? 1 : 0)
            .ThenByDescending(f => f.UploadDate)
            .FirstOrDefault();

        // === HEADER ===
        var name = _latestForm?.StudentName ?? _student.StudentName;
        TxtStudentName.Text = string.IsNullOrWhiteSpace(name) ? "Unknown Student" : name;
        TxtAvatar.Text = (name?.Length > 0 ? name[0].ToString().ToUpper() : "?");
        TxtCourse.Text = _latestForm?.Course ?? "—";
        TxtRollNo.Text = $"Roll: {_latestForm?.CollegeRollNo ?? _student.RollNumber ?? "—"}";
        TxtAadhar.Text = $"Aadhar: {MaskAadhar(_latestForm?.AadharNumber ?? _student.AadharNumber)}";

        // Status badge
        var isVerified = _latestForm?.Status == FormStatus.Verified;
        TxtStatus.Text = isVerified ? "✓ Verified" : _latestForm?.Status.ToString() ?? "—";
        BadgeStatus.Background = isVerified
            ? new System.Windows.Media.SolidColorBrush(System.Windows.Media.Color.FromRgb(16, 185, 129))
            : new System.Windows.Media.SolidColorBrush(System.Windows.Media.Color.FromRgb(245, 158, 11));

        TxtCategory.Text = _latestForm?.Category ?? _latestForm?.AdmissionCategory ?? "—";

        // === STAT CARDS ===
        TxtFormCount.Text = _student.Forms.Count.ToString();
        TxtDocCount.Text = _student.Documents.Count.ToString();

        // Calculate confidence
        if (_latestForm?.ExtractedDataJson != null)
        {
            try
            {
                var json = System.Text.Json.JsonDocument.Parse(_latestForm.ExtractedDataJson);
                if (json.RootElement.TryGetProperty("confidence", out var conf))
                    TxtConfidence.Text = $"{conf.GetDouble():F0}%";
            }
            catch { TxtConfidence.Text = "—%"; }
        }

        // Count filled fields
        int filledCount = CountFilledFields(_latestForm);
        TxtFieldCount.Text = filledCount.ToString();

        // === PERSONAL ===
        if (_latestForm != null)
        {
            SetField(ValFirstName, _latestForm.FirstName);
            SetField(ValMiddleName, _latestForm.MiddleName);
            SetField(ValSurname, _latestForm.Surname);
            SetField(ValGender, _latestForm.Gender);
            SetField(ValDOB, _latestForm.DateOfBirth);
            SetField(ValBloodGroup, _latestForm.BloodGroup);
            SetField(ValReligion, _latestForm.Religion);
            SetField(ValNationality, _latestForm.Nationality);
            SetField(ValAadharNumber, _latestForm.AadharNumber);

            SetField(ValBPL, _latestForm.BelowPovertyLine);
            SetField(ValAnnualIncome, _latestForm.AnnualIncome);

            // Academic
            SetField(ValCourse, _latestForm.Course);
            SetField(ValSession, _latestForm.AcademicSession);
            SetField(ValCollegeRoll, _latestForm.CollegeRollNo);
            SetField(ValCuetScore, _latestForm.CuetScore);
            SetField(ValAdmCat, _latestForm.AdmissionCategory);
            SetField(ValDUForm, _latestForm.DuPortalFormNumber);
            SetField(ValDOA, _latestForm.DateOfAdmission);
            SetField(ValDUEnroll, _latestForm.DuEnrollmentNumber);

            // Contact
            SetField(ValEmail, _latestForm.Email);
            SetField(ValPhone, _latestForm.PhoneNumber);
            SetField(ValAltPhone, _latestForm.AlternatePhone);

            // Address
            SetField(ValPermAddress, _latestForm.PermanentAddress ?? BuildAddressLines(
                _latestForm.PermanentAddressLine1, _latestForm.PermanentAddressLine2, _latestForm.PermanentAddressLine3));
            SetField(ValPermState, _latestForm.PermanentState);
            SetField(ValPermPincode, _latestForm.PermanentPincode ?? _latestForm.Pincode);
            SetField(ValCorrAddress, _latestForm.CorrespondenceAddress ?? BuildAddressLines(
                _latestForm.CorrespondenceAddressLine1, _latestForm.CorrespondenceAddressLine2, _latestForm.CorrespondenceAddressLine3));
            SetField(ValCorrState, _latestForm.CorrespondenceState);
            SetField(ValCorrPincode, _latestForm.CorrespondencePincode);

            // Parents
            SetField(ValMotherName, _latestForm.MotherName);
            SetField(ValMotherOcc, _latestForm.MotherOccupation);
            SetField(ValMotherMobile, _latestForm.MotherMobile);
            SetField(ValMotherEmail, _latestForm.MotherEmail);
            SetField(ValFatherName, _latestForm.FatherName);
            SetField(ValFatherOcc, _latestForm.FatherOccupation);
            SetField(ValFatherMobile, _latestForm.FatherMobile);
            SetField(ValFatherEmail, _latestForm.FatherEmail);

            // Guardian
            SetField(ValGuardianName, _latestForm.GuardianName);
            SetField(ValGuardianRel, _latestForm.GuardianRelation);
            SetField(ValGuardianMobile, _latestForm.GuardianMobile);
            SetField(ValGuardianEmail, _latestForm.GuardianEmail);

            // Education
            SetField(Val12Board, _latestForm.TwelfthBoard);
            SetField(Val12Year, _latestForm.TwelfthYear);
            SetField(Val12Percent, _latestForm.TwelfthPercentage ?? _latestForm.Class12Percentage);
            SetField(Val12Roll, _latestForm.TwelfthRollNumber ?? _latestForm.Class12RollNo);
            SetField(Val12Institution, _latestForm.TwelfthInstitution ?? _latestForm.Class12Institution);
            SetField(Val10Board, _latestForm.TenthBoard);
            SetField(Val10Year, _latestForm.TenthYear);
            SetField(Val10Percent, _latestForm.TenthPercentage);
            SetField(Val10School, _latestForm.TenthSchool);

            // Emergency
            SetField(ValEmergName, _latestForm.EmergencyContactName);
            SetField(ValEmergPhone, _latestForm.EmergencyContactPhone);
        }

        // === GRIDS ===
        FormsGrid.ItemsSource = _student.Forms.OrderByDescending(f => f.UploadDate).ToList();
        DocsGrid.ItemsSource = _student.Documents.OrderByDescending(d => d.UploadDate).ToList();
    }

    private static void SetField(TextBlock tb, string? value)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            tb.Text = "—";
            tb.Foreground = new System.Windows.Media.SolidColorBrush(System.Windows.Media.Color.FromRgb(203, 213, 225));
        }
        else
        {
            tb.Text = value;
        }
    }

    private static string? BuildAddressLines(string? l1, string? l2, string? l3)
    {
        var parts = new[] { l1, l2, l3 }.Where(s => !string.IsNullOrWhiteSpace(s));
        var result = string.Join(", ", parts);
        return string.IsNullOrWhiteSpace(result) ? null : result;
    }

    private static string MaskAadhar(string? aadhar)
    {
        if (string.IsNullOrWhiteSpace(aadhar) || aadhar.Length < 8) return "—";
        return $"XXXX-XXXX-{aadhar[^4..]}";
    }

    private static int CountFilledFields(AdmissionForm? form)
    {
        if (form == null) return 0;
        int count = 0;
        var props = typeof(AdmissionForm).GetProperties();
        foreach (var prop in props)
        {
            if (prop.Name is "Id" or "StudentProfileId" or "StudentProfile" or "ExtractedDataJson"
                or "FilePath" or "Filename" or "SyncStatus" or "SyncId" or "Documents") continue;
            var val = prop.GetValue(form);
            if (val is string s && !string.IsNullOrWhiteSpace(s)) count++;
            else if (val is bool b && b) count++;
            else if (val is DateTime) count++;
        }
        return count;
    }

    private void Back_Click(object sender, RoutedEventArgs e)
    {
        if (Window.GetWindow(this) is MainWindow mainWindow)
        {
            mainWindow.ContentFrame.Navigate(new StudentsPage());
        }
    }

    private void Edit_Click(object sender, RoutedEventArgs e)
    {
        if (_latestForm != null && Window.GetWindow(this) is MainWindow mainWindow)
        {
            mainWindow.ContentFrame.Navigate(new StudentEditPage(_studentId, _latestForm.Id));
        }
        else
        {
            MessageBox.Show("No form data available to edit.", "Info", MessageBoxButton.OK, MessageBoxImage.Information);
        }
    }

    private void Export_Click(object sender, RoutedEventArgs e)
    {
        if (_student == null || _latestForm == null) return;

        var dialog = new SaveFileDialog
        {
            Filter = "PDF|*.pdf",
            FileName = $"{_student.StudentName.Replace(' ', '_')}_Profile.pdf"
        };

        if (dialog.ShowDialog() != true) return;

        try
        {
            QuestPDF.Settings.License = LicenseType.Community;

            Document.Create(container =>
            {
                container.Page(page =>
                {
                    page.Size(PageSizes.A4);
                    page.Margin(40);
                    page.DefaultTextStyle(x => x.FontSize(10));

                    // Header
                    page.Header().Column(col =>
                    {
                        col.Item().Background("#1e3a5f").Padding(16).Row(row =>
                        {
                            row.RelativeItem().Text(_student.StudentName)
                                .FontSize(20).Bold().FontColor("#ffffff");
                            row.ConstantItem(120).AlignRight().Text(_latestForm.Status.ToString())
                                .FontSize(12).FontColor("#ffffff");
                        });
                        col.Item().PaddingTop(8).Text($"Course: {_latestForm.Course ?? "—"}  |  Roll: {_latestForm.CollegeRollNo ?? "—"}  |  Session: {_latestForm.AcademicSession ?? "—"}")
                            .FontSize(9).FontColor("#64748b");
                    });

                    // Content
                    page.Content().PaddingTop(16).Column(col =>
                    {
                        void Section(string title) => col.Item().PaddingTop(12).PaddingBottom(4)
                            .Text(title).FontSize(13).Bold().FontColor("#1e3a5f");
                        void Field(string label, string? val) => col.Item().Row(r =>
                        {
                            r.ConstantItem(150).Text(label).FontColor("#64748b");
                            r.RelativeItem().Text(val ?? "—");
                        });

                        Section("Personal Information");
                        Field("Name", $"{_latestForm.FirstName} {_latestForm.MiddleName} {_latestForm.Surname}".Trim());
                        Field("Gender", _latestForm.Gender);
                        Field("Date of Birth", _latestForm.DateOfBirth);
                        Field("Aadhar", _latestForm.AadharNumber);
                        Field("Nationality", _latestForm.Nationality);
                        Field("Religion", _latestForm.Religion);

                        Section("Contact");
                        Field("Email", _latestForm.Email);
                        Field("Phone", _latestForm.PhoneNumber);

                        Section("Address");
                        Field("Permanent", _latestForm.PermanentAddress);
                        Field("Correspondence", _latestForm.CorrespondenceAddress);

                        Section("Parents");
                        Field("Father", _latestForm.FatherName);
                        Field("Mother", _latestForm.MotherName);

                        Section("Education — Class XII");
                        Field("Board", _latestForm.TwelfthBoard);
                        Field("Year", _latestForm.TwelfthYear);
                        Field("Percentage", _latestForm.TwelfthPercentage ?? _latestForm.Class12Percentage);

                        Section("Education — Class X");
                        Field("Board", _latestForm.TenthBoard);
                        Field("Year", _latestForm.TenthYear);
                        Field("Percentage", _latestForm.TenthPercentage);
                    });

                    page.Footer().AlignCenter().Text(t =>
                    {
                        t.Span("SRCC Student DMS — Generated ");
                        t.Span(DateTime.Now.ToString("dd MMM yyyy HH:mm"));
                    });
                });
            }).GeneratePdf(dialog.FileName);

            MessageBox.Show($"Exported to:\n{dialog.FileName}", "Export Complete", MessageBoxButton.OK, MessageBoxImage.Information);
        }
        catch (Exception ex)
        {
            MessageBox.Show($"Export failed: {ex.Message}", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    private void Print_Click(object sender, RoutedEventArgs e)
    {
        // Use the same PDF export then open it
        if (_student == null || _latestForm == null) return;

        try
        {
            QuestPDF.Settings.License = LicenseType.Community;
            var tempPath = Path.Combine(Path.GetTempPath(), $"SRCC_Student_{_studentId}.pdf");

            Document.Create(container =>
            {
                container.Page(page =>
                {
                    page.Size(PageSizes.A4);
                    page.Margin(40);
                    page.DefaultTextStyle(x => x.FontSize(10));

                    page.Header().Background("#1e3a5f").Padding(16)
                        .Text(_student.StudentName).FontSize(18).Bold().FontColor("#ffffff");

                    page.Content().PaddingTop(12).Column(col =>
                    {
                        void Field(string label, string? val) => col.Item().Row(r =>
                        {
                            r.ConstantItem(150).Text(label).FontColor("#64748b");
                            r.RelativeItem().Text(val ?? "—");
                        });

                        Field("Course", _latestForm.Course);
                        Field("Roll No", _latestForm.CollegeRollNo);
                        Field("Session", _latestForm.AcademicSession);
                        Field("Name", $"{_latestForm.FirstName} {_latestForm.MiddleName} {_latestForm.Surname}".Trim());
                        Field("Gender", _latestForm.Gender);
                        Field("DOB", _latestForm.DateOfBirth);
                        Field("Email", _latestForm.Email);
                        Field("Phone", _latestForm.PhoneNumber);
                        Field("Father", _latestForm.FatherName);
                        Field("Mother", _latestForm.MotherName);
                    });

                    page.Footer().AlignCenter().Text($"SRCC Student DMS — {DateTime.Now:dd MMM yyyy}");
                });
            }).GeneratePdf(tempPath);

            var psi = new System.Diagnostics.ProcessStartInfo(tempPath) { UseShellExecute = true };
            System.Diagnostics.Process.Start(psi);
        }
        catch (Exception ex)
        {
            MessageBox.Show($"Print failed: {ex.Message}", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    private async void Delete_Click(object sender, RoutedEventArgs e)
    {
        if (_student == null) return;

        var result = MessageBox.Show(
            $"Are you sure you want to delete student \"{_student.StudentName}\" and all associated forms and documents?\n\nThis action cannot be undone.",
            "Confirm Delete",
            MessageBoxButton.YesNo,
            MessageBoxImage.Warning);

        if (result == MessageBoxResult.Yes)
        {
            using var db = new AppDbContext();
            var student = await db.StudentProfiles
                .Include(s => s.Forms)
                .Include(s => s.Documents)
                .FirstOrDefaultAsync(s => s.Id == _studentId);

            if (student != null)
            {
                db.StudentProfiles.Remove(student);
                await db.SaveChangesAsync();
            }

            // Navigate back
            if (Window.GetWindow(this) is MainWindow mainWindow)
                mainWindow.ContentFrame.Navigate(new StudentsPage());
        }
    }

    private void FormsGrid_DoubleClick(object sender, MouseButtonEventArgs e)
    {
        if (FormsGrid.SelectedItem is AdmissionForm form)
        {
            if (Window.GetWindow(this) is MainWindow mainWindow)
            {
                mainWindow.ContentFrame.Navigate(new FormDetailPage(form.Id));
            }
        }
    }
}
