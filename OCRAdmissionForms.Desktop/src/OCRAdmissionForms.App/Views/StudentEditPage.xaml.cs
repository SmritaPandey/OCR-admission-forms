using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media.Imaging;
using Microsoft.EntityFrameworkCore;
using Microsoft.Web.WebView2.Core;
using OCRAdmissionForms.Core.Data;
using OCRAdmissionForms.Core.Entities;
using DocumentService = OCRAdmissionForms.Core.Services.DocumentService;

namespace OCRAdmissionForms.App.Views;

public partial class StudentEditPage : Page
{
    private readonly int _studentId;
    private readonly int _formId;
    private AdmissionForm? _form;
    private double _zoomLevel = 1.0;

    public StudentEditPage(int studentId, int formId)
    {
        InitializeComponent();
        _studentId = studentId;
        _formId = formId;
        Loaded += StudentEditPage_Loaded;
    }

    private async void StudentEditPage_Loaded(object sender, RoutedEventArgs e)
    {
        await LoadFormAsync();
        await LoadDocumentPreviewAsync();
    }

    private async Task LoadFormAsync()
    {
        using var db = new AppDbContext();
        _form = await db.AdmissionForms.FindAsync(_formId);

        if (_form == null)
        {
            MessageBox.Show("Form not found.", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
            return;
        }

        TxtEditTitle.Text = $"Editing: {_form.StudentName ?? _form.FirstName ?? "Student"}";
        TxtEditSubtitle.Text = $"Form #{_form.Id} • {_form.Filename}";

        // Personal
        EdFirstName.Text = _form.FirstName;
        EdMiddleName.Text = _form.MiddleName;
        EdSurname.Text = _form.Surname;
        SelectComboItem(EdGender, _form.Gender);
        EdDOB.Text = _form.DateOfBirth;
        SelectComboItem(EdBloodGroup, _form.BloodGroup);
        SelectComboItem(EdReligion, _form.Religion);
        SelectComboItem(EdNationality, _form.Nationality);
        EdAadhar.Text = _form.AadharNumber;
        // Lock Aadhar once verified
        if (_form.Status == FormStatus.Verified && !string.IsNullOrWhiteSpace(_form.AadharNumber))
        {
            EdAadhar.IsReadOnly = true;
            EdAadhar.Background = new System.Windows.Media.SolidColorBrush(
                System.Windows.Media.Color.FromRgb(0xF1, 0xF5, 0xF9));
            EdAadhar.ToolTip = "🔒 Aadhar number is locked after verification";
        }

        SelectComboItem(EdBPL, _form.BelowPovertyLine);
        EdIncome.Text = _form.AnnualIncome;

        // Academic
        SelectComboItem(EdCourse, _form.Course);
        EdSession.Text = _form.AcademicSession;
        EdCollegeRoll.Text = _form.CollegeRollNo;
        EdCuetScore.Text = _form.CuetScore;
        SelectComboItem(EdCategory, _form.AdmissionCategory ?? _form.Category);
        EdDUForm.Text = _form.DuPortalFormNumber;
        EdDOA.Text = _form.DateOfAdmission;
        EdDUEnroll.Text = _form.DuEnrollmentNumber;

        // Contact
        EdEmail.Text = _form.Email;
        EdPhone.Text = _form.PhoneNumber;
        EdAltPhone.Text = _form.AlternatePhone;

        // Address
        EdPermAddress.Text = _form.PermanentAddress;
        EdPermState.Text = _form.PermanentState;
        EdPermPincode.Text = _form.PermanentPincode ?? _form.Pincode;
        EdCorrAddress.Text = _form.CorrespondenceAddress;
        EdCorrState.Text = _form.CorrespondenceState;
        EdCorrPincode.Text = _form.CorrespondencePincode;

        // Parents
        EdMotherName.Text = _form.MotherName;
        EdMotherOcc.Text = _form.MotherOccupation;
        EdMotherMobile.Text = _form.MotherMobile;
        EdMotherEmail.Text = _form.MotherEmail;
        EdFatherName.Text = _form.FatherName;
        EdFatherOcc.Text = _form.FatherOccupation;
        EdFatherMobile.Text = _form.FatherMobile;
        EdFatherEmail.Text = _form.FatherEmail;

        // Guardian
        EdGuardianName.Text = _form.GuardianName;
        EdGuardianRel.Text = _form.GuardianRelation;
        EdGuardianMobile.Text = _form.GuardianMobile;
        EdGuardianEmail.Text = _form.GuardianEmail;

        // Education
        Ed12Board.Text = _form.TwelfthBoard;
        Ed12Year.Text = _form.TwelfthYear;
        Ed12Percent.Text = _form.TwelfthPercentage ?? _form.Class12Percentage;
        Ed12Roll.Text = _form.TwelfthRollNumber ?? _form.Class12RollNo;
        Ed12Institution.Text = _form.TwelfthInstitution ?? _form.Class12Institution;
        Ed10Board.Text = _form.TenthBoard;
        Ed10Year.Text = _form.TenthYear;
        Ed10Percent.Text = _form.TenthPercentage;
        Ed10School.Text = _form.TenthSchool;

        // Emergency
        EdEmergName.Text = _form.EmergencyContactName;
        EdEmergPhone.Text = _form.EmergencyContactPhone;

        TxtSaveStatus.Text = "All fields loaded. Edit and save when ready.";
    }

    // ===== Document Preview =====
    private async Task LoadDocumentPreviewAsync()
    {
        if (_form == null || string.IsNullOrWhiteSpace(_form.FilePath))
        {
            TxtNoPreview.Visibility = Visibility.Visible;
            return;
        }

        var filePath = _form.FilePath;
        if (!File.Exists(filePath))
        {
            TxtNoPreview.Text = $"File not found:\n{filePath}";
            TxtNoPreview.Visibility = Visibility.Visible;
            return;
        }

        var ext = Path.GetExtension(filePath).ToLower();
        if (ext == ".pdf")
        {
            await LoadPdfAsync(filePath);
        }
        else if (ext is ".jpg" or ".jpeg" or ".png" or ".bmp" or ".tif" or ".tiff")
        {
            LoadImage(filePath);
        }
        else
        {
            TxtNoPreview.Text = $"Preview not available for {ext} files";
            TxtNoPreview.Visibility = Visibility.Visible;
        }
    }

    private async Task LoadPdfAsync(string path)
    {
        try
        {
            ImageScroller.Visibility = Visibility.Collapsed;
            PdfViewer.Visibility = Visibility.Visible;

            var env = await CoreWebView2Environment.CreateAsync(null, 
                Path.Combine(Path.GetTempPath(), "OCRAdmissionForms_WebView2"));
            await PdfViewer.EnsureCoreWebView2Async(env);
            PdfViewer.CoreWebView2.Navigate(new Uri(path).AbsoluteUri);
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"PDF load error: {ex.Message}");
            TxtNoPreview.Text = "PDF viewer not available.\nInstall WebView2 Runtime.";
            TxtNoPreview.Visibility = Visibility.Visible;
            PdfViewer.Visibility = Visibility.Collapsed;
        }
    }

    private void LoadImage(string path)
    {
        try
        {
            PdfViewer.Visibility = Visibility.Collapsed;
            ImageScroller.Visibility = Visibility.Visible;

            var bitmap = new BitmapImage();
            bitmap.BeginInit();
            bitmap.UriSource = new Uri(path, UriKind.Absolute);
            bitmap.CacheOption = BitmapCacheOption.OnLoad;
            bitmap.EndInit();
            bitmap.Freeze();

            FormImage.Source = bitmap;
            ApplyZoom();
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"Image load error: {ex.Message}");
            TxtNoPreview.Text = "Failed to load image preview.";
            TxtNoPreview.Visibility = Visibility.Visible;
        }
    }

    // ===== Zoom Controls =====
    private void ZoomIn_Click(object sender, RoutedEventArgs e) { _zoomLevel = Math.Min(3.0, _zoomLevel + 0.25); ApplyZoom(); }
    private void ZoomOut_Click(object sender, RoutedEventArgs e) { _zoomLevel = Math.Max(0.25, _zoomLevel - 0.25); ApplyZoom(); }
    private void ZoomFit_Click(object sender, RoutedEventArgs e) { _zoomLevel = 1.0; ApplyZoom(); }

    private void ApplyZoom()
    {
        TxtZoomLevel.Text = $"{(int)(_zoomLevel * 100)}%";
        if (FormImage.Source is BitmapSource bmp)
        {
            FormImage.Width = bmp.PixelWidth * _zoomLevel;
            FormImage.Height = bmp.PixelHeight * _zoomLevel;
        }
    }

    // ===== Combo Helpers =====
    private static void SelectComboItem(ComboBox cb, string? value)
    {
        if (string.IsNullOrWhiteSpace(value)) return;
        foreach (ComboBoxItem item in cb.Items)
        {
            if (item.Content?.ToString()?.Equals(value, StringComparison.OrdinalIgnoreCase) == true)
            {
                cb.SelectedItem = item;
                return;
            }
        }
        var newItem = new ComboBoxItem { Content = value };
        cb.Items.Add(newItem);
        cb.SelectedItem = newItem;
    }

    private static string? GetComboValue(ComboBox cb) =>
        (cb.SelectedItem as ComboBoxItem)?.Content?.ToString();

    private static string? TrimOrNull(string? s)
    {
        var trimmed = s?.Trim();
        return string.IsNullOrWhiteSpace(trimmed) ? null : trimmed;
    }

    // ===== Apply Changes =====
    private void ApplyFormChanges(AdmissionForm form)
    {
        form.FirstName = TrimOrNull(EdFirstName.Text);
        form.MiddleName = TrimOrNull(EdMiddleName.Text);
        form.Surname = TrimOrNull(EdSurname.Text);
        form.Gender = GetComboValue(EdGender);
        form.DateOfBirth = TrimOrNull(EdDOB.Text);
        form.BloodGroup = GetComboValue(EdBloodGroup);
        form.Religion = GetComboValue(EdReligion);
        form.Nationality = GetComboValue(EdNationality);
        form.AadharNumber = TrimOrNull(EdAadhar.Text);

        form.BelowPovertyLine = GetComboValue(EdBPL);
        form.AnnualIncome = TrimOrNull(EdIncome.Text);

        var parts = new[] { form.FirstName, form.MiddleName, form.Surname }.Where(s => !string.IsNullOrWhiteSpace(s));
        form.StudentName = string.Join(" ", parts);

        form.Course = GetComboValue(EdCourse);
        form.AcademicSession = TrimOrNull(EdSession.Text);
        form.CollegeRollNo = TrimOrNull(EdCollegeRoll.Text);
        form.CuetScore = TrimOrNull(EdCuetScore.Text);
        form.AdmissionCategory = GetComboValue(EdCategory);
        form.Category = form.AdmissionCategory;
        form.DuPortalFormNumber = TrimOrNull(EdDUForm.Text);
        form.DateOfAdmission = TrimOrNull(EdDOA.Text);
        form.DuEnrollmentNumber = TrimOrNull(EdDUEnroll.Text);

        form.Email = TrimOrNull(EdEmail.Text);
        form.PhoneNumber = TrimOrNull(EdPhone.Text);
        form.AlternatePhone = TrimOrNull(EdAltPhone.Text);

        form.PermanentAddress = TrimOrNull(EdPermAddress.Text);
        form.PermanentState = TrimOrNull(EdPermState.Text);
        form.PermanentPincode = TrimOrNull(EdPermPincode.Text);
        form.CorrespondenceAddress = TrimOrNull(EdCorrAddress.Text);
        form.CorrespondenceState = TrimOrNull(EdCorrState.Text);
        form.CorrespondencePincode = TrimOrNull(EdCorrPincode.Text);

        form.MotherName = TrimOrNull(EdMotherName.Text);
        form.MotherOccupation = TrimOrNull(EdMotherOcc.Text);
        form.MotherMobile = TrimOrNull(EdMotherMobile.Text);
        form.MotherEmail = TrimOrNull(EdMotherEmail.Text);
        form.FatherName = TrimOrNull(EdFatherName.Text);
        form.FatherOccupation = TrimOrNull(EdFatherOcc.Text);
        form.FatherMobile = TrimOrNull(EdFatherMobile.Text);
        form.FatherEmail = TrimOrNull(EdFatherEmail.Text);

        form.GuardianName = TrimOrNull(EdGuardianName.Text);
        form.GuardianRelation = TrimOrNull(EdGuardianRel.Text);
        form.GuardianMobile = TrimOrNull(EdGuardianMobile.Text);
        form.GuardianEmail = TrimOrNull(EdGuardianEmail.Text);

        form.TwelfthBoard = TrimOrNull(Ed12Board.Text);
        form.TwelfthYear = TrimOrNull(Ed12Year.Text);
        form.TwelfthPercentage = TrimOrNull(Ed12Percent.Text);
        form.TwelfthRollNumber = TrimOrNull(Ed12Roll.Text);
        form.TwelfthInstitution = TrimOrNull(Ed12Institution.Text);
        form.TenthBoard = TrimOrNull(Ed10Board.Text);
        form.TenthYear = TrimOrNull(Ed10Year.Text);
        form.TenthPercentage = TrimOrNull(Ed10Percent.Text);
        form.TenthSchool = TrimOrNull(Ed10School.Text);

        form.EmergencyContactName = TrimOrNull(EdEmergName.Text);
        form.EmergencyContactPhone = TrimOrNull(EdEmergPhone.Text);
    }

    // ===== Validation =====
    private bool ValidateForm()
    {
        var errors = new List<string>();
        if (string.IsNullOrWhiteSpace(EdFirstName.Text)) errors.Add("First Name is required");
        if (!string.IsNullOrWhiteSpace(EdPhone.Text) && EdPhone.Text.Trim().Length != 10) errors.Add("Phone must be 10 digits");
        if (!string.IsNullOrWhiteSpace(EdAadhar.Text) && EdAadhar.Text.Trim().Length != 12) errors.Add("Aadhar must be 12 digits");
        if (!string.IsNullOrWhiteSpace(EdPermPincode.Text) && EdPermPincode.Text.Trim().Length != 6) errors.Add("Pincode must be 6 digits");

        if (errors.Count > 0)
        {
            MessageBox.Show(string.Join("\n", errors), "Validation Errors", MessageBoxButton.OK, MessageBoxImage.Warning);
            return false;
        }
        return true;
    }

    // ===== Save =====
    private async Task SaveAsync(bool markVerified)
    {
        if (!ValidateForm()) return;

        try
        {
            using var db = new AppDbContext();
            var form = await db.AdmissionForms
                .Include(f => f.StudentProfile)
                .FirstOrDefaultAsync(f => f.Id == _formId);

            if (form == null)
            {
                MessageBox.Show("Form not found in database.", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
                return;
            }

            ApplyFormChanges(form);

            // ===== Duplicate Aadhar check =====
            var aadharCheck = form.AadharNumber?.Trim();
            if (!string.IsNullOrWhiteSpace(aadharCheck))
            {
                var dupAadhar = await db.AdmissionForms
                    .FirstOrDefaultAsync(f => f.Id != _formId && f.AadharNumber == aadharCheck);
                if (dupAadhar != null)
                {
                    MessageBox.Show($"Duplicate Aadhar number!\n\nAnother form (ID: {dupAadhar.Id}, {dupAadhar.StudentName ?? dupAadhar.Filename}) already has Aadhar: {aadharCheck}",
                        "Duplicate Error", MessageBoxButton.OK, MessageBoxImage.Warning);
                    return;
                }
            }

            // ===== Duplicate DU Portal Form Number check =====
            var duFormNo = form.DuPortalFormNumber?.Trim();
            if (!string.IsNullOrWhiteSpace(duFormNo))
            {
                var dupForm = await db.AdmissionForms
                    .FirstOrDefaultAsync(f => f.Id != _formId && f.DuPortalFormNumber == duFormNo);
                if (dupForm != null)
                {
                    MessageBox.Show($"Duplicate DU Portal Form Number!\n\nAnother form (ID: {dupForm.Id}, {dupForm.StudentName ?? dupForm.Filename}) already has Form No: {duFormNo}",
                        "Duplicate Error", MessageBoxButton.OK, MessageBoxImage.Warning);
                    return;
                }
            }

            if (markVerified)
            {
                form.Status = FormStatus.Verified;
                form.VerifiedDate = DateTime.UtcNow;
                form.VerifiedBy = Environment.UserName;
            }

            // ===== Create or update StudentProfile =====
            var studentName = form.StudentName ?? "";
            var aadhar = form.AadharNumber?.Trim();
            var rollNo = form.CollegeRollNo?.Trim();

            if (form.StudentProfile != null)
            {
                if (!string.IsNullOrWhiteSpace(studentName))
                    form.StudentProfile.StudentName = studentName;
                if (!string.IsNullOrWhiteSpace(aadhar))
                    form.StudentProfile.AadharNumber = aadhar;
                if (!string.IsNullOrWhiteSpace(rollNo))
                    form.StudentProfile.RollNumber = rollNo;
                form.StudentProfile.UpdatedDate = DateTime.UtcNow;
            }
            else if (markVerified || form.Status == FormStatus.Verified)
            {
                StudentProfile? profile = null;
                if (!string.IsNullOrWhiteSpace(aadhar))
                    profile = await db.StudentProfiles.FirstOrDefaultAsync(s => s.AadharNumber == aadhar);
                if (profile == null && !string.IsNullOrWhiteSpace(rollNo))
                    profile = await db.StudentProfiles.FirstOrDefaultAsync(s => s.RollNumber == rollNo);
                if (profile == null && !string.IsNullOrWhiteSpace(studentName))
                    profile = await db.StudentProfiles.FirstOrDefaultAsync(s => s.StudentName == studentName);

                if (profile == null)
                {
                    profile = new StudentProfile
                    {
                        StudentName = studentName.Length > 0 ? studentName : "Unknown",
                        AadharNumber = aadhar,
                        RollNumber = rollNo,
                        CreatedDate = DateTime.UtcNow,
                        UpdatedDate = DateTime.UtcNow,
                    };
                    db.StudentProfiles.Add(profile);
                    await db.SaveChangesAsync();
                }
                else
                {
                    if (!string.IsNullOrWhiteSpace(studentName)) profile.StudentName = studentName;
                    if (!string.IsNullOrWhiteSpace(aadhar)) profile.AadharNumber = aadhar;
                    if (!string.IsNullOrWhiteSpace(rollNo)) profile.RollNumber = rollNo;
                    profile.UpdatedDate = DateTime.UtcNow;
                }

                form.StudentProfileId = profile.Id;
            }

            await db.SaveChangesAsync();

            TxtSaveStatus.Text = markVerified
                ? "✓ Saved and Verified!"
                : "✓ Changes saved!";

            if (Window.GetWindow(this) is MainWindow mainWindow)
            {
                mainWindow.ContentFrame.Navigate(new StudentProfilePage(_studentId));
            }
        }
        catch (Exception ex)
        {
            MessageBox.Show($"Save failed:\n\n{ex.Message}", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    private async void Save_Click(object sender, RoutedEventArgs e) => await SaveAsync(false);

    private async void Verify_Click(object sender, RoutedEventArgs e)
    {
        var result = MessageBox.Show(
            "This will mark the form as Verified. Are you sure all data is correct?",
            "Confirm Verification",
            MessageBoxButton.YesNo,
            MessageBoxImage.Question);

        if (result == MessageBoxResult.Yes)
            await SaveAsync(true);
    }

    private async void AttachDocument_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            var dlg = new Microsoft.Win32.OpenFileDialog
            {
                Title = "Select Document to Attach",
                Filter = "All Documents|*.pdf;*.jpg;*.jpeg;*.png;*.bmp;*.tif;*.tiff;*.doc;*.docx;*.xls;*.xlsx|PDF Files|*.pdf|Images|*.jpg;*.jpeg;*.png;*.bmp|All Files|*.*",
                Multiselect = true,
            };

            if (dlg.ShowDialog() != true) return;

            // Ask for document type/label
            var typeWindow = new System.Windows.Window
            {
                Title = "Document Details",
                Width = 400, Height = 280,
                WindowStartupLocation = System.Windows.WindowStartupLocation.CenterScreen,
                ResizeMode = System.Windows.ResizeMode.NoResize,
            };
            var panel = new StackPanel { Margin = new Thickness(20) };
            panel.Children.Add(new TextBlock { Text = "Document Label:", FontWeight = FontWeights.SemiBold, Margin = new Thickness(0, 0, 0, 5) });
            var txtLabel = new TextBox { Text = "", Margin = new Thickness(0, 0, 0, 12) };
            panel.Children.Add(txtLabel);
            panel.Children.Add(new TextBlock { Text = "Document Type:", FontWeight = FontWeights.SemiBold, Margin = new Thickness(0, 0, 0, 5) });
            var cmbType = new ComboBox { Margin = new Thickness(0, 0, 0, 16) };
            foreach (var dt in Enum.GetValues<DocumentType>())
                cmbType.Items.Add(new ComboBoxItem { Content = dt.ToString(), Tag = dt });
            cmbType.SelectedIndex = cmbType.Items.Count - 1;
            panel.Children.Add(cmbType);
            var btnOk = new Button { Content = "Attach", HorizontalAlignment = HorizontalAlignment.Right, Padding = new Thickness(24, 8, 24, 8), Background = new System.Windows.Media.SolidColorBrush(System.Windows.Media.Color.FromRgb(37, 99, 235)), Foreground = System.Windows.Media.Brushes.White };
            btnOk.Click += (_, _) => { typeWindow.DialogResult = true; };
            panel.Children.Add(btnOk);
            typeWindow.Content = panel;

            if (typeWindow.ShowDialog() != true) return;

            var label = string.IsNullOrWhiteSpace(txtLabel.Text) ? "Attached Document" : txtLabel.Text.Trim();
            var selectedType = (cmbType.SelectedItem as ComboBoxItem)?.Tag is DocumentType dt2 ? dt2 : DocumentType.Other;

            using var db = new AppDbContext();
            var form = await db.AdmissionForms.FindAsync(_formId);
            if (form == null) return;

            var profileId = form.StudentProfileId ?? 0;
            int attachedCount = 0;

            foreach (var file in dlg.FileNames)
            {
                var fileLabel = dlg.FileNames.Length > 1
                    ? $"{label} - {Path.GetFileNameWithoutExtension(file)}"
                    : label;

                var doc = DocumentService.AttachFile(file, fileLabel, selectedType, _formId, profileId);
                if (doc != null)
                {
                    db.StudentDocuments.Add(doc);
                    attachedCount++;
                }
            }

            if (attachedCount > 0)
            {
                await db.SaveChangesAsync();
                TxtSaveStatus.Text = $"✅ {attachedCount} document(s) attached!";
            }
        }
        catch (Exception ex)
        {
            MessageBox.Show($"Failed to attach document:\n\n{ex.Message}", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    private void Cancel_Click(object sender, RoutedEventArgs e)
    {
        if (Window.GetWindow(this) is MainWindow mainWindow)
            mainWindow.ContentFrame.Navigate(new StudentProfilePage(_studentId));
    }
}
