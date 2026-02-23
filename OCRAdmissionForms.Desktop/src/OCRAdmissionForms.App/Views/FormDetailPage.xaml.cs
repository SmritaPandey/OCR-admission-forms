using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media.Imaging;
using Microsoft.EntityFrameworkCore;
using Microsoft.Web.WebView2.Core;
using OCRAdmissionForms.Core.Data;
using OCRAdmissionForms.Core.Entities;
using OCRAdmissionForms.Core.Services;
using TextBlock = System.Windows.Controls.TextBlock;

namespace OCRAdmissionForms.App.Views;

public partial class FormDetailPage : Page
{
    private readonly int _formId;
    private AdmissionForm? _form;
    private double _zoomLevel = 1.0;
    private const double ZoomStep = 0.25;
    private readonly string _dataPath;
    private readonly string _logPath;
    private readonly string _credentialsPath;
    private bool _isPdf = false;

    public FormDetailPage(int formId)
    {
        InitializeComponent();
        _formId = formId;
        
        try
        {
            var appData = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
            _dataPath = Path.Combine(appData, "SRCC Student DMS", "data");
            _logPath = Path.Combine(_dataPath, "app_error.log");
            _credentialsPath = AppConfig.GoogleCredentialsPath;
            
            // Ensure data directory exists
            Directory.CreateDirectory(_dataPath);
        }
        catch (Exception ex)
        {
            _dataPath = Path.GetTempPath();
            _logPath = Path.Combine(_dataPath, "srcc_error.log");
            _credentialsPath = "";
            System.Diagnostics.Debug.WriteLine($"Init error: {ex.Message}");
        }
        
        Loaded += FormDetailPage_Loaded;
    }

    private void GoBack_Click(object sender, RoutedEventArgs e)
    {
        if (NavigationService?.CanGoBack == true)
        {
            NavigationService.GoBack();
        }
        else
        {
            // Fallback: navigate to FormsPage
            NavigationService?.Navigate(new FormsPage());
        }
    }

    private async void FormDetailPage_Loaded(object sender, RoutedEventArgs e)
    {
        try
        {
            await LoadFormAsync();
        }
        catch (Exception ex)
        {
            LogError("PageLoaded", ex);
            ShowError($"Failed to load form: {ex.Message}");
        }
    }

    private async Task LoadFormAsync()
    {
        try
        {
            using var db = new AppDbContext();
            _form = await db.AdmissionForms.FindAsync(_formId);

            if (_form == null)
            {
                ShowError("Form not found in database.");
                return;
            }

            // Load document viewer
            LoadDocumentViewer();
            
            // Load form fields
            LoadFieldsFromForm();
            UpdateZoomDisplay();
            
            // Update status display
            UpdateStatusDisplay();
        }
        catch (Exception ex)
        {
            LogError("LoadFormAsync", ex);
            throw;
        }
    }

    private void LoadDocumentViewer()
    {
        if (_form == null) return;
        
        var filePath = _form.FilePath;
        
        // Hide all viewers first
        FormImage.Visibility = Visibility.Collapsed;
        PdfViewer.Visibility = Visibility.Collapsed;
        TxtNoPreview.Visibility = Visibility.Collapsed;
        
        if (string.IsNullOrEmpty(filePath))
        {
            ShowPreviewError("No file path specified for this form.");
            return;
        }

        if (!File.Exists(filePath))
        {
            ShowPreviewError($"File not found:\n{filePath}\n\nThe source file may have been moved or deleted.");
            return;
        }

        var ext = Path.GetExtension(filePath)?.ToLower() ?? "";
        _isPdf = ext == ".pdf";

        try
        {
            if (_isPdf)
            {
                LoadPdfViewer(filePath);
            }
            else
            {
                LoadImageViewer(filePath);
            }
        }
        catch (Exception ex)
        {
            LogError("LoadDocumentViewer", ex);
            ShowPreviewError($"Error loading document:\n{ex.Message}");
        }
    }

    private async void LoadPdfViewer(string filePath)
    {
        try
        {
            PdfViewer.Visibility = Visibility.Visible;
            var env = await CoreWebView2Environment.CreateAsync(null,
                Path.Combine(Path.GetTempPath(), "OCRAdmissionForms_WebView2"));
            await PdfViewer.EnsureCoreWebView2Async(env);
            PdfViewer.CoreWebView2.Navigate(new Uri(filePath).AbsoluteUri);
        }
        catch (Exception ex)
        {
            LogError("LoadPdfViewer", ex);
            PdfViewer.Visibility = Visibility.Collapsed;
            ShowPreviewError($"PDF viewer unavailable.\n\nError: {ex.Message}\n\nFile: {Path.GetFileName(filePath)}");
        }
    }

    private void LoadImageViewer(string filePath)
    {
        try
        {
            // Use stream-based loading for better compatibility
            using var stream = new FileStream(filePath, FileMode.Open, FileAccess.Read, FileShare.Read);
            var bitmap = new BitmapImage();
            bitmap.BeginInit();
            bitmap.StreamSource = stream;
            bitmap.CacheOption = BitmapCacheOption.OnLoad;
            bitmap.CreateOptions = BitmapCreateOptions.IgnoreColorProfile | BitmapCreateOptions.PreservePixelFormat;
            bitmap.EndInit();
            bitmap.Freeze();
            
            FormImage.Source = bitmap;
            FormImage.Visibility = Visibility.Visible;
        }
        catch (NotSupportedException)
        {
            // Try alternative approach for problematic images
            TryAlternativeImageLoad(filePath);
        }
        catch (Exception ex)
        {
            LogError("LoadImageViewer", ex);
            TryAlternativeImageLoad(filePath);
        }
    }

    private void TryAlternativeImageLoad(string filePath)
    {
        try
        {
            // Read all bytes and decode
            var bytes = File.ReadAllBytes(filePath);
            using var ms = new MemoryStream(bytes);
            
            var bitmap = new BitmapImage();
            bitmap.BeginInit();
            bitmap.StreamSource = ms;
            bitmap.CacheOption = BitmapCacheOption.OnLoad;
            bitmap.EndInit();
            bitmap.Freeze();
            
            FormImage.Source = bitmap;
            FormImage.Visibility = Visibility.Visible;
        }
        catch (Exception ex)
        {
            LogError("AlternativeImageLoad", ex);
            ShowPreviewError($"Cannot load image:\n\nThe image format may not be supported or the file may be corrupted.\n\nFile: {Path.GetFileName(filePath)}\nError: {ex.Message}");
        }
    }

    private void ShowPreviewError(string message)
    {
        TxtNoPreview.Text = message;
        TxtNoPreview.Visibility = Visibility.Visible;
        FormImage.Visibility = Visibility.Collapsed;
        PdfViewer.Visibility = Visibility.Collapsed;
    }

    private void UpdateStatusDisplay()
    {
        if (_form == null) return;
        
        try
        {
            var hasOcr = !string.IsNullOrEmpty(_form.ExtractedDataJson);
            var ocrLength = _form.ExtractedDataJson?.Length ?? 0;
            
            if (hasOcr && ocrLength > 10)
            {
                TxtOcrStatus.Text = $"✓ OCR data available ({ocrLength} characters)";
                TxtOcrStatus.Foreground = System.Windows.Media.Brushes.Green;
            }
            else if (hasOcr)
            {
                TxtOcrStatus.Text = "⚠ OCR data may be incomplete";
                TxtOcrStatus.Foreground = System.Windows.Media.Brushes.Orange;
            }
            else
            {
                TxtOcrStatus.Text = "✗ No OCR data - click Re-extract";
                TxtOcrStatus.Foreground = System.Windows.Media.Brushes.Red;
            }
        }
        catch (Exception ex)
        {
            LogError("UpdateStatusDisplay", ex);
        }
    }

    /// <summary>Sets an editable ComboBox text value, selecting matching item if found</summary>
    private void SetComboBoxValue(System.Windows.Controls.ComboBox cmb, string? value)
    {
        if (string.IsNullOrEmpty(value)) { cmb.Text = ""; cmb.SelectedIndex = -1; return; }
        // Try to select a matching item first
        for (int i = 0; i < cmb.Items.Count; i++)
        {
            if (cmb.Items[i] is System.Windows.Controls.ComboBoxItem item &&
                string.Equals(item.Content?.ToString(), value, StringComparison.OrdinalIgnoreCase))
            {
                cmb.SelectedIndex = i;
                return;
            }
        }
        // No match — set the text directly (editable combo)
        cmb.SelectedIndex = -1;
        cmb.Text = value;
    }

    /// <summary>Gets the text value from an editable ComboBox</summary>
    private string? GetComboBoxValue(System.Windows.Controls.ComboBox cmb)
    {
        if (cmb.SelectedItem is System.Windows.Controls.ComboBoxItem item)
            return item.Content?.ToString()?.Trim();
        return cmb.Text?.Trim();
    }

    private void LoadFieldsFromForm()
    {
        if (_form == null) return;

        try
        {
            // Personal
            TxtFirstName.Text = _form.FirstName ?? "";
            TxtMiddleName.Text = _form.MiddleName ?? "";
            TxtSurname.Text = _form.Surname ?? "";
            TxtStudentName.Text = _form.StudentName ?? "";
            TxtDOB.Text = _form.DateOfBirth ?? "";
            SetComboBoxValue(CmbGender, _form.Gender);
            SetComboBoxValue(CmbCategory, _form.Category);
            SetComboBoxValue(CmbBloodGroup, _form.BloodGroup);
            SetComboBoxValue(CmbNationality, _form.Nationality);
            SetComboBoxValue(CmbReligion, _form.Religion);
            SetComboBoxValue(CmbMinorityCategory, _form.MinorityCategory);
            TxtAnnualIncome.Text = _form.AnnualIncome ?? "";
            SetComboBoxValue(CmbBelowPovertyLine, _form.BelowPovertyLine);
            TxtAadhar.Text = _form.AadharNumber ?? "";

            // Lock Aadhar field once form is verified
            if (_form.Status == FormStatus.Verified && !string.IsNullOrWhiteSpace(_form.AadharNumber))
            {
                TxtAadhar.IsReadOnly = true;
                TxtAadhar.Background = new System.Windows.Media.SolidColorBrush(
                    System.Windows.Media.Color.FromRgb(0xF1, 0xF5, 0xF9));
                TxtAadhar.ToolTip = "🔒 Aadhar number is locked after verification";
            }

            // Parent
            TxtFatherName.Text = _form.FatherName ?? "";
            TxtMotherName.Text = _form.MotherName ?? "";
            TxtFatherOccupation.Text = _form.FatherOccupation ?? "";
            TxtMotherOccupation.Text = _form.MotherOccupation ?? "";
            TxtFatherDesignation.Text = _form.FatherDesignation ?? "";
            TxtMotherDesignation.Text = _form.MotherDesignation ?? "";
            TxtFatherOrganization.Text = _form.FatherOrganization ?? "";
            TxtMotherOrganization.Text = _form.MotherOrganization ?? "";
            TxtFatherPhone.Text = _form.FatherPhone ?? "";
            TxtMotherPhone.Text = _form.MotherPhone ?? "";
            TxtFatherMobile.Text = _form.FatherMobile ?? "";
            TxtMotherMobile.Text = _form.MotherMobile ?? "";
            TxtFatherEmail.Text = _form.FatherEmail ?? "";
            TxtMotherEmail.Text = _form.MotherEmail ?? "";
            TxtFatherAnnualIncome.Text = _form.FatherAnnualIncome ?? "";
            TxtMotherAnnualIncome.Text = _form.MotherAnnualIncome ?? "";

            // Contact
            TxtPhone.Text = _form.PhoneNumber ?? "";
            TxtAltPhone.Text = _form.AlternatePhone ?? "";
            TxtEmail.Text = _form.Email ?? "";
            TxtAddress.Text = _form.PermanentAddress ?? "";
            TxtState.Text = _form.PermanentState ?? "";
            TxtPincode.Text = _form.Pincode ?? _form.PermanentPincode ?? "";
            TxtCorrespondenceAddress.Text = _form.CorrespondenceAddress ?? "";
            TxtCorrespondenceState.Text = _form.CorrespondenceState ?? "";
            TxtCorrespondencePincode.Text = _form.CorrespondencePincode ?? "";
            TxtLocalAddress.Text = _form.LocalAddress ?? "";

            // Academic
            TxtAcademicSession.Text = _form.AcademicSession ?? "";
            SetComboBoxValue(CmbAdmissionCategory, _form.AdmissionCategory);
            SetComboBoxValue(CmbCourse, _form.Course);
            TxtRollNo.Text = _form.CollegeRollNo ?? "";
            TxtCuetScore.Text = _form.CuetScore ?? "";
            TxtDuPortalFormNumber.Text = _form.DuPortalFormNumber ?? "";
            TxtDateOfAdmission.Text = _form.DateOfAdmission ?? "";
            TxtTwelfthBoard.Text = _form.TwelfthBoard ?? "";
            TxtTwelfthYear.Text = _form.TwelfthYear ?? "";
            TxtTwelfthPercentage.Text = _form.TwelfthPercentage ?? _form.Class12Percentage ?? "";
            TxtTwelfthRollNumber.Text = _form.TwelfthRollNumber ?? _form.Class12RollNo ?? "";
            TxtTwelfthInstitution.Text = _form.TwelfthInstitution ?? _form.Class12Institution ?? "";
            SetComboBoxValue(CmbHindiStudiedUpto, _form.HindiStudiedUpto);

            // Guardian
            TxtGuardianName.Text = _form.GuardianName ?? "";
            TxtGuardianAddress.Text = _form.GuardianAddress ?? "";
            TxtGuardianPhone.Text = _form.GuardianMobile ?? "";
            TxtGuardianRelation.Text = _form.GuardianRelation ?? "";
            TxtGuardianEmail.Text = _form.GuardianEmail ?? "";
            TxtGuardianOrganization.Text = _form.GuardianOrganization ?? "";

            // Other Info
            TxtDuEnrollment.Text = _form.DuEnrollmentNumber ?? "";
            SetComboBoxValue(CmbHindiMedium, _form.HindiMediumPreference);
            TxtDeclarationDate.Text = _form.DeclarationDate ?? "";
            TxtDeclarationPlace.Text = _form.DeclarationPlace ?? "";

            // Certificate Details
            TxtCertAuthority.Text = _form.CategoryCertificateAuthority ?? "";
            TxtCertNumber.Text = _form.CategoryCertificateNumber ?? "";
            TxtCertDate.Text = _form.CategoryCertificateDate ?? "";
            TxtDisabilityType.Text = _form.DisabilityType ?? "";
            TxtDisabilityPercent.Text = _form.DisabilityPercentage ?? "";
            TxtUdidNumber.Text = _form.UdidNumber ?? "";

            // CUET Subject Details
            TxtCuetSubject1.Text = _form.CuetSubject1 ?? "";
            TxtCuetMax1.Text = _form.CuetTotalScore1 ?? "";
            TxtCuetObtained1.Text = _form.CuetScoreObtained1 ?? "";
            TxtCuetSubject2.Text = _form.CuetSubject2 ?? "";
            TxtCuetMax2.Text = _form.CuetTotalScore2 ?? "";
            TxtCuetObtained2.Text = _form.CuetScoreObtained2 ?? "";
            TxtCuetSubject3.Text = _form.CuetSubject3 ?? "";
            TxtCuetMax3.Text = _form.CuetTotalScore3 ?? "";
            TxtCuetObtained3.Text = _form.CuetScoreObtained3 ?? "";
            TxtCuetSubject4.Text = _form.CuetSubject4 ?? "";
            TxtCuetMax4.Text = _form.CuetTotalScore4 ?? "";
            TxtCuetObtained4.Text = _form.CuetScoreObtained4 ?? "";
            TxtCuetSubject5.Text = _form.CuetSubject5 ?? "";
            TxtCuetMax5.Text = _form.CuetTotalScore5 ?? "";
            TxtCuetObtained5.Text = _form.CuetScoreObtained5 ?? "";
            TxtCuetSubject6.Text = _form.CuetSubject6 ?? "";
            TxtCuetMax6.Text = _form.CuetTotalScore6 ?? "";
            TxtCuetObtained6.Text = _form.CuetScoreObtained6 ?? "";
            TxtCuetTotalAll.Text = _form.CuetTotalScoreAll ?? "";
            TxtCuetObtainedAll.Text = _form.CuetScoreObtainedAll ?? "";

            // 10th Class Details
            TxtTenthBoard.Text = _form.TenthBoard ?? "";
            TxtTenthYear.Text = _form.TenthYear ?? "";
            TxtTenthPercentage.Text = _form.TenthPercentage ?? "";
            TxtTenthSchool.Text = _form.TenthSchool ?? "";

            // Emergency Contact
            TxtEmergencyName.Text = _form.EmergencyContactName ?? "";
            TxtEmergencyPhone.Text = _form.EmergencyContactPhone ?? "";

            // Declarations
            TxtStudentDeclName.Text = _form.StudentDeclarationName ?? "";
            TxtStudentDeclDate.Text = _form.StudentDeclarationDate ?? "";
            TxtStudentDeclPlace.Text = _form.StudentDeclarationPlace ?? "";
            TxtParentGuardianName.Text = _form.ParentGuardianName ?? "";
            TxtParentRelationship.Text = _form.ParentGuardianRelationship ?? "";
            TxtParentCandidateName.Text = _form.ParentGuardianCandidateName ?? "";
            TxtParentCourse.Text = _form.ParentGuardianCourse ?? "";
            TxtParentDeclDate.Text = _form.ParentGuardianDate ?? "";
            TxtParentDeclPlace.Text = _form.ParentGuardianPlace ?? "";

            // Document Checklist
            ChkDocAdmissionForm.IsChecked = _form.DocAdmissionForm ?? false;
            ChkDocPhotographs.IsChecked = _form.DocPhotographs ?? false;
            ChkDocCuetScorecard.IsChecked = _form.DocCuetScorecard ?? false;
            ChkDocClassXiiMarksheet.IsChecked = _form.DocClassXiiMarksheet ?? false;
            ChkDocClassXCertificate.IsChecked = _form.DocClassXCertificate ?? false;
            ChkDocClassXiiCertificate.IsChecked = _form.DocClassXiiCertificate ?? false;
            ChkDocCharacterCertificate.IsChecked = _form.DocCharacterCertificate ?? false;
            ChkDocCasteCertificate.IsChecked = _form.DocCasteCertificate ?? false;
            ChkDocMigrationCertificate.IsChecked = _form.DocMigrationCertificate ?? false;
            ChkDocTransferCertificate.IsChecked = _form.DocTransferCertificate ?? false;
            ChkDocGapCertificate.IsChecked = _form.DocGapCertificate ?? false;
            ChkDocIncomeCertificate.IsChecked = _form.DocIncomeCertificate ?? false;
            ChkDocDomicileCertificate.IsChecked = _form.DocDomicileCertificate ?? false;
            ChkDocAadharCard.IsChecked = _form.DocAadharCard ?? false;
            ChkDocMedicalFitness.IsChecked = _form.DocMedicalFitness ?? false;
            ChkDocAntiRagging.IsChecked = _form.DocUndertakingRagging ?? false;
        }
        catch (Exception ex)
        {
            LogError("LoadFieldsFromForm", ex);
        }
    }

    private void SaveFieldsToForm()
    {
        if (_form == null) return;

        try
        {
            // Personal
            _form.FirstName = TxtFirstName.Text?.Trim();
            _form.MiddleName = TxtMiddleName.Text?.Trim();
            _form.Surname = TxtSurname.Text?.Trim();
            _form.StudentName = TxtStudentName.Text?.Trim();
            _form.DateOfBirth = TxtDOB.Text?.Trim();
            _form.Gender = GetComboBoxValue(CmbGender);
            _form.Category = GetComboBoxValue(CmbCategory);
            _form.BloodGroup = GetComboBoxValue(CmbBloodGroup);
            _form.Nationality = GetComboBoxValue(CmbNationality);
            _form.Religion = GetComboBoxValue(CmbReligion);
            _form.MinorityCategory = GetComboBoxValue(CmbMinorityCategory);
            _form.AnnualIncome = TxtAnnualIncome.Text?.Trim();
            _form.BelowPovertyLine = GetComboBoxValue(CmbBelowPovertyLine);
            _form.AadharNumber = TxtAadhar.Text?.Trim();

            // Parent
            _form.FatherName = TxtFatherName.Text?.Trim();
            _form.MotherName = TxtMotherName.Text?.Trim();
            _form.FatherOccupation = TxtFatherOccupation.Text?.Trim();
            _form.MotherOccupation = TxtMotherOccupation.Text?.Trim();
            _form.FatherDesignation = TxtFatherDesignation.Text?.Trim();
            _form.MotherDesignation = TxtMotherDesignation.Text?.Trim();
            _form.FatherOrganization = TxtFatherOrganization.Text?.Trim();
            _form.MotherOrganization = TxtMotherOrganization.Text?.Trim();
            _form.FatherPhone = TxtFatherPhone.Text?.Trim();
            _form.MotherPhone = TxtMotherPhone.Text?.Trim();
            _form.FatherMobile = TxtFatherMobile.Text?.Trim();
            _form.MotherMobile = TxtMotherMobile.Text?.Trim();
            _form.FatherEmail = TxtFatherEmail.Text?.Trim();
            _form.MotherEmail = TxtMotherEmail.Text?.Trim();
            _form.FatherAnnualIncome = TxtFatherAnnualIncome.Text?.Trim();
            _form.MotherAnnualIncome = TxtMotherAnnualIncome.Text?.Trim();

            // Contact
            _form.PhoneNumber = TxtPhone.Text?.Trim();
            _form.AlternatePhone = TxtAltPhone.Text?.Trim();
            _form.Email = TxtEmail.Text?.Trim();
            _form.PermanentAddress = TxtAddress.Text?.Trim();
            _form.PermanentState = TxtState.Text?.Trim();
            _form.Pincode = TxtPincode.Text?.Trim();
            _form.PermanentPincode = TxtPincode.Text?.Trim();
            _form.CorrespondenceAddress = TxtCorrespondenceAddress.Text?.Trim();
            _form.CorrespondenceState = TxtCorrespondenceState.Text?.Trim();
            _form.CorrespondencePincode = TxtCorrespondencePincode.Text?.Trim();
            _form.LocalAddress = TxtLocalAddress.Text?.Trim();

            // Academic
            _form.AcademicSession = TxtAcademicSession.Text?.Trim();
            _form.AdmissionCategory = GetComboBoxValue(CmbAdmissionCategory);
            _form.Course = GetComboBoxValue(CmbCourse);
            _form.CollegeRollNo = TxtRollNo.Text?.Trim();
            _form.CuetScore = TxtCuetScore.Text?.Trim();
            _form.DuPortalFormNumber = TxtDuPortalFormNumber.Text?.Trim();
            _form.DateOfAdmission = TxtDateOfAdmission.Text?.Trim();
            _form.TwelfthBoard = TxtTwelfthBoard.Text?.Trim();
            _form.TwelfthYear = TxtTwelfthYear.Text?.Trim();
            _form.TwelfthPercentage = TxtTwelfthPercentage.Text?.Trim();
            _form.TwelfthRollNumber = TxtTwelfthRollNumber.Text?.Trim();
            _form.TwelfthInstitution = TxtTwelfthInstitution.Text?.Trim();
            _form.HindiStudiedUpto = GetComboBoxValue(CmbHindiStudiedUpto);

            // Guardian
            _form.GuardianName = TxtGuardianName.Text?.Trim();
            _form.GuardianAddress = TxtGuardianAddress.Text?.Trim();
            _form.GuardianMobile = TxtGuardianPhone.Text?.Trim();
            _form.GuardianRelation = TxtGuardianRelation.Text?.Trim();
            _form.GuardianEmail = TxtGuardianEmail.Text?.Trim();
            _form.GuardianOrganization = TxtGuardianOrganization.Text?.Trim();

            // Other Info
            _form.DuEnrollmentNumber = TxtDuEnrollment.Text?.Trim();
            _form.HindiMediumPreference = GetComboBoxValue(CmbHindiMedium);
            _form.DeclarationDate = TxtDeclarationDate.Text?.Trim();
            _form.DeclarationPlace = TxtDeclarationPlace.Text?.Trim();

            // Certificate Details
            _form.CategoryCertificateAuthority = TxtCertAuthority.Text?.Trim();
            _form.CategoryCertificateNumber = TxtCertNumber.Text?.Trim();
            _form.CategoryCertificateDate = TxtCertDate.Text?.Trim();
            _form.DisabilityType = TxtDisabilityType.Text?.Trim();
            _form.DisabilityPercentage = TxtDisabilityPercent.Text?.Trim();
            _form.UdidNumber = TxtUdidNumber.Text?.Trim();

            // CUET Subject Details
            _form.CuetSubject1 = TxtCuetSubject1.Text?.Trim();
            _form.CuetTotalScore1 = TxtCuetMax1.Text?.Trim();
            _form.CuetScoreObtained1 = TxtCuetObtained1.Text?.Trim();
            _form.CuetSubject2 = TxtCuetSubject2.Text?.Trim();
            _form.CuetTotalScore2 = TxtCuetMax2.Text?.Trim();
            _form.CuetScoreObtained2 = TxtCuetObtained2.Text?.Trim();
            _form.CuetSubject3 = TxtCuetSubject3.Text?.Trim();
            _form.CuetTotalScore3 = TxtCuetMax3.Text?.Trim();
            _form.CuetScoreObtained3 = TxtCuetObtained3.Text?.Trim();
            _form.CuetSubject4 = TxtCuetSubject4.Text?.Trim();
            _form.CuetTotalScore4 = TxtCuetMax4.Text?.Trim();
            _form.CuetScoreObtained4 = TxtCuetObtained4.Text?.Trim();
            _form.CuetSubject5 = TxtCuetSubject5.Text?.Trim();
            _form.CuetTotalScore5 = TxtCuetMax5.Text?.Trim();
            _form.CuetScoreObtained5 = TxtCuetObtained5.Text?.Trim();
            _form.CuetSubject6 = TxtCuetSubject6.Text?.Trim();
            _form.CuetTotalScore6 = TxtCuetMax6.Text?.Trim();
            _form.CuetScoreObtained6 = TxtCuetObtained6.Text?.Trim();
            _form.CuetTotalScoreAll = TxtCuetTotalAll.Text?.Trim();
            _form.CuetScoreObtainedAll = TxtCuetObtainedAll.Text?.Trim();

            // 10th Class Details
            _form.TenthBoard = TxtTenthBoard.Text?.Trim();
            _form.TenthYear = TxtTenthYear.Text?.Trim();
            _form.TenthPercentage = TxtTenthPercentage.Text?.Trim();
            _form.TenthSchool = TxtTenthSchool.Text?.Trim();

            // Emergency Contact
            _form.EmergencyContactName = TxtEmergencyName.Text?.Trim();
            _form.EmergencyContactPhone = TxtEmergencyPhone.Text?.Trim();

            // Declarations
            _form.StudentDeclarationName = TxtStudentDeclName.Text?.Trim();
            _form.StudentDeclarationDate = TxtStudentDeclDate.Text?.Trim();
            _form.StudentDeclarationPlace = TxtStudentDeclPlace.Text?.Trim();
            _form.ParentGuardianName = TxtParentGuardianName.Text?.Trim();
            _form.ParentGuardianRelationship = TxtParentRelationship.Text?.Trim();
            _form.ParentGuardianCandidateName = TxtParentCandidateName.Text?.Trim();
            _form.ParentGuardianCourse = TxtParentCourse.Text?.Trim();
            _form.ParentGuardianDate = TxtParentDeclDate.Text?.Trim();
            _form.ParentGuardianPlace = TxtParentDeclPlace.Text?.Trim();

            // Document Checklist
            _form.DocAdmissionForm = ChkDocAdmissionForm.IsChecked;
            _form.DocPhotographs = ChkDocPhotographs.IsChecked;
            _form.DocCuetScorecard = ChkDocCuetScorecard.IsChecked;
            _form.DocClassXiiMarksheet = ChkDocClassXiiMarksheet.IsChecked;
            _form.DocClassXCertificate = ChkDocClassXCertificate.IsChecked;
            _form.DocClassXiiCertificate = ChkDocClassXiiCertificate.IsChecked;
            _form.DocCharacterCertificate = ChkDocCharacterCertificate.IsChecked;
            _form.DocCasteCertificate = ChkDocCasteCertificate.IsChecked;
            _form.DocMigrationCertificate = ChkDocMigrationCertificate.IsChecked;
            _form.DocTransferCertificate = ChkDocTransferCertificate.IsChecked;
            _form.DocGapCertificate = ChkDocGapCertificate.IsChecked;
            _form.DocIncomeCertificate = ChkDocIncomeCertificate.IsChecked;
            _form.DocDomicileCertificate = ChkDocDomicileCertificate.IsChecked;
            _form.DocAadharCard = ChkDocAadharCard.IsChecked;
            _form.DocMedicalFitness = ChkDocMedicalFitness.IsChecked;
            _form.DocUndertakingRagging = ChkDocAntiRagging.IsChecked;
        }
        catch (Exception ex)
        {
            LogError("SaveFieldsToForm", ex);
        }
    }

    // Zoom Controls
    private void ZoomIn_Click(object sender, RoutedEventArgs e)
    {
        _zoomLevel = Math.Min(_zoomLevel + ZoomStep, 5.0);
        ApplyZoom();
    }

    private void ZoomOut_Click(object sender, RoutedEventArgs e)
    {
        _zoomLevel = Math.Max(_zoomLevel - ZoomStep, 0.25);
        ApplyZoom();
    }

    private void ZoomFit_Click(object sender, RoutedEventArgs e)
    {
        _zoomLevel = 1.0;
        ApplyZoom();
    }

    private void ApplyZoom()
    {
        try
        {
            if (!_isPdf)
            {
                FormImage.LayoutTransform = new System.Windows.Media.ScaleTransform(_zoomLevel, _zoomLevel);
            }
            else if (PdfViewer.CoreWebView2 != null)
            {
                PdfViewer.ZoomFactor = _zoomLevel;
            }
            UpdateZoomDisplay();
        }
        catch (Exception ex)
        {
            LogError("ApplyZoom", ex);
        }
    }

    private void UpdateZoomDisplay()
    {
        TxtZoomLevel.Text = $"{(_zoomLevel * 100):F0}%";
    }

    // Autofill from OCR
    private void Autofill_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            if (_form == null)
            {
                ShowError("Form not loaded.");
                return;
            }

            if (string.IsNullOrEmpty(_form.ExtractedDataJson))
            {
                ShowError("No OCR data available.\n\nClick 'Re-extract' button to run OCR on this form, or enter data manually.");
                return;
            }

            var extractor = new FormFieldExtractor();
            int fieldsExtracted = 0;
            
            // Try to parse as JSON with pre-extracted fields first
            try
            {
                using var jsonDoc = System.Text.Json.JsonDocument.Parse(_form.ExtractedDataJson);
                var root = jsonDoc.RootElement;
                
                // Python outputs 'fields' key (see ocr_extract.py line 1221)
                if (root.TryGetProperty("fields", out var fieldsProp) && fieldsProp.ValueKind == System.Text.Json.JsonValueKind.Object)
                {
                    var preExtracted = new Dictionary<string, string>();
                    foreach (var prop in fieldsProp.EnumerateObject())
                    {
                        if (prop.Value.ValueKind == System.Text.Json.JsonValueKind.String)
                        {
                            var val = prop.Value.GetString();
                            if (!string.IsNullOrEmpty(val))
                            {
                                preExtracted[prop.Name] = val;
                            }
                        }
                        else if (prop.Value.ValueKind == System.Text.Json.JsonValueKind.True || 
                                 prop.Value.ValueKind == System.Text.Json.JsonValueKind.False)
                        {
                            preExtracted[prop.Name] = prop.Value.GetBoolean() ? "Yes" : "No";
                        }
                    }
                    
                    if (preExtracted.Count > 0)
                    {
                        _form = extractor.ExtractFromPreExtracted(preExtracted, _form);
                        fieldsExtracted = preExtracted.Count;
                        System.Diagnostics.Debug.WriteLine($"[Autofill] Used {fieldsExtracted} pre-extracted fields from Python");
                    }
                }
            }
            catch (System.Text.Json.JsonException)
            {
                // Not valid JSON, fall through to regex extraction
                System.Diagnostics.Debug.WriteLine("[Autofill] ExtractedDataJson is not valid JSON, using regex fallback");
            }
            
            // Fallback to regex extraction if no pre-extracted fields found
            if (fieldsExtracted == 0)
            {
                _form = extractor.ExtractFieldsFromJson(_form.ExtractedDataJson, _form);
                System.Diagnostics.Debug.WriteLine("[Autofill] Using regex fallback extraction");
            }
            
            LoadFieldsFromForm();

            // Build detailed message like Re-extract does
            int textLength = 0;
            float confidence = 0;
            int fieldsCount = 0;
            int wordsDetected = 0;
            float handwrittenPct = 0;
            float avgWordConf = 0;
            string extractionMethod = "regex patterns";
            
            try
            {
                using var jsonForStats = System.Text.Json.JsonDocument.Parse(_form.ExtractedDataJson);
                var statsRoot = jsonForStats.RootElement;
                
                if (statsRoot.TryGetProperty("text", out var textProp))
                    textLength = textProp.GetString()?.Length ?? 0;
                else
                    textLength = _form.ExtractedDataJson.Length;
                    
                if (statsRoot.TryGetProperty("confidence", out var confProp))
                    confidence = (float)confProp.GetDouble();
                    
                if (statsRoot.TryGetProperty("fields_count", out var countProp))
                    fieldsCount = countProp.GetInt32();
                
                if (statsRoot.TryGetProperty("words_detected", out var wordsProp))
                    wordsDetected = wordsProp.GetInt32();
                
                if (statsRoot.TryGetProperty("handwritten_percentage", out var hwProp))
                    handwrittenPct = (float)hwProp.GetDouble();
                    
                if (statsRoot.TryGetProperty("avg_word_confidence", out var awcProp))
                    avgWordConf = (float)awcProp.GetDouble();
                    
                if (fieldsExtracted > 0)
                    extractionMethod = "AI spatial analysis";
            }
            catch
            {
                textLength = _form.ExtractedDataJson.Length;
            }

            var message = new System.Text.StringBuilder();
            message.AppendLine("✅ Autofill Complete!");
            message.AppendLine();
            message.AppendLine($"📄 OCR Text: {textLength:N0} characters");
            if (wordsDetected > 0)
                message.AppendLine($"📝 Words Detected: {wordsDetected:N0}");
            if (confidence > 0)
                message.AppendLine($"🎯 Confidence: {confidence:F1}%");
            if (avgWordConf > 0)
                message.AppendLine($"✨ Word Accuracy: {avgWordConf:F1}%");
            if (handwrittenPct > 0)
                message.AppendLine($"✍️ Handwritten: {handwrittenPct:F1}%");
            message.AppendLine($"📋 Fields Mapped: {(fieldsCount > 0 ? fieldsCount : fieldsExtracted)}");
            message.AppendLine($"🔧 Method: {extractionMethod}");
            message.AppendLine();
            message.AppendLine("Please review and correct any errors.");
            
            MessageBox.Show(message.ToString(), "Autofill Complete", MessageBoxButton.OK, MessageBoxImage.Information);
        }
        catch (Exception ex)
        {
            LogError("Autofill", ex);
            ShowError($"Autofill failed: {ex.Message}");
        }
    }

    // Re-extract OCR
    private async void ReExtract_Click(object sender, RoutedEventArgs e)
    {
        if (_form == null)
        {
            ShowError("Form not loaded.");
            return;
        }

        // Check credentials
        if (!File.Exists(_credentialsPath))
        {
            ShowError($"Google Cloud credentials not found.\n\nExpected at:\n{_credentialsPath}\n\nGo to Settings → Google Cloud Vision API to configure.");
            return;
        }

        // Check source file
        if (string.IsNullOrEmpty(_form.FilePath))
        {
            ShowError("No file path specified for this form.");
            return;
        }
        
        if (!File.Exists(_form.FilePath))
        {
            ShowError($"Source file not found:\n{_form.FilePath}");
            return;
        }

        BtnReExtract.IsEnabled = false;
        BtnAutofill.IsEnabled = false;
        TxtOcrStatus.Text = "⏳ Running OCR extraction...";
        TxtOcrStatus.Foreground = System.Windows.Media.Brushes.Blue;

        try
        {
            // Initialize OCR service
            IOcrService ocrService;
            try
            {
                ocrService = new GoogleVisionOcrService(_credentialsPath);
            }
            catch (Exception initEx)
            {
                LogError("OCR Init", initEx);
                ShowError($"Failed to initialize OCR service:\n\n{initEx.Message}\n\nCheck your Google Cloud credentials.");
                TxtOcrStatus.Text = "✗ OCR initialization failed";
                TxtOcrStatus.Foreground = System.Windows.Media.Brushes.Red;
                return;
            }

            // Get selected OCR provider from ComboBox
            var selectedProvider = "gemini";
            if (CmbOcrProvider.SelectedItem is System.Windows.Controls.ComboBoxItem selectedItem)
            {
                selectedProvider = selectedItem.Tag?.ToString() ?? "gemini";
            }
            var providerNames = new Dictionary<string, string> {
                {"gemini", "Gemini AI"}, {"enhanced", "Enhanced Vision"}, {"multi", "Multi-Provider"}, {"spatial", "Spatial"}
            };
            TxtOcrStatus.Text = $"⏳ Running {providerNames.GetValueOrDefault(selectedProvider, selectedProvider)} extraction...";

            // Run OCR with selected provider
            OcrResult result;
            try
            {
                result = await ocrService.ExtractTextAsync(_form.FilePath, selectedProvider);
            }
            catch (Exception ocrEx)
            {
                LogError("OCR Execution", ocrEx);
                ShowError($"OCR extraction failed:\n\n{ocrEx.Message}");
                TxtOcrStatus.Text = "✗ OCR extraction failed";
                TxtOcrStatus.Foreground = System.Windows.Media.Brushes.Red;
                return;
            }

            // Check for errors
            if (!string.IsNullOrEmpty(result.Error))
            {
                LogError("OCR Result", new Exception(result.Error));
                ShowError($"OCR returned an error:\n\n{result.Error}");
                TxtOcrStatus.Text = "✗ OCR error";
                TxtOcrStatus.Foreground = System.Windows.Media.Brushes.Red;
                return;
            }

            // Check for empty results
            if (string.IsNullOrWhiteSpace(result.FullText))
            {
                ShowError("OCR returned no text.\n\nThe document may be:\n• Blank or empty\n• A scanned image that's too dark/light\n• A format that couldn't be read");
                TxtOcrStatus.Text = "⚠ No text found";
                TxtOcrStatus.Foreground = System.Windows.Media.Brushes.Orange;
                return;
            }

            // Store OCR result - IMPORTANT: Store full JSON with fields for Autofill
            var jsonResult = new Dictionary<string, object>
            {
                ["text"] = result.FullText,
                ["fields"] = result.ExtractedFields ?? new Dictionary<string, string>(),
                ["confidence"] = result.Confidence,
                ["fields_count"] = result.ExtractedFields?.Count ?? 0,
                ["extraction_method"] = selectedProvider
            };
            _form.ExtractedDataJson = System.Text.Json.JsonSerializer.Serialize(jsonResult);
            _form.OcrProvider = selectedProvider switch
            {
                "gemini" => "gemini-ai",
                "enhanced" => "enhanced-vision",
                "multi" => "multi-provider",
                _ => "google-vision"
            };
            _form.Status = FormStatus.Extracted;

            // Extract fields - prefer pre-extracted fields from Python, fallback to regex
            var extractor = new FormFieldExtractor();
            int fieldsExtracted = 0;
            
            // --- DIAGNOSTIC: dump raw extracted fields ---
            var diagLog = new System.Text.StringBuilder();
            diagLog.AppendLine($"=== EXTRACTION DIAGNOSTIC {DateTime.Now:HH:mm:ss} ===");
            diagLog.AppendLine($"OcrResult.ExtractedFields count: {result.ExtractedFields?.Count ?? 0}");
            if (result.ExtractedFields != null)
            {
                foreach (var kvp in result.ExtractedFields)
                    diagLog.AppendLine($"  [{kvp.Key}] = {kvp.Value}");
            }
            
            if (result.ExtractedFields != null && result.ExtractedFields.Count > 0)
            {
                // Use Python's accurate spatial analysis extraction
                _form = extractor.ExtractFromPreExtracted(result.ExtractedFields, _form);
                fieldsExtracted = result.ExtractedFields.Count;
                System.Diagnostics.Debug.WriteLine($"[Autofill] Used {fieldsExtracted} pre-extracted fields from Python");
            }
            else
            {
                // Fallback to regex extraction
                _form = extractor.ExtractFieldsFromJson(result.FullText, _form);
                System.Diagnostics.Debug.WriteLine("[Autofill] Using regex fallback extraction");
            }
            
            // --- DIAGNOSTIC: dump mapped form fields ---
            diagLog.AppendLine($"\n=== MAPPED FORM FIELDS (fieldsExtracted={fieldsExtracted}) ===");
            diagLog.AppendLine($"  FirstName: {_form.FirstName}");
            diagLog.AppendLine($"  MiddleName: {_form.MiddleName}");
            diagLog.AppendLine($"  Surname: {_form.Surname}");
            diagLog.AppendLine($"  Gender: {_form.Gender}");
            diagLog.AppendLine($"  DateOfBirth: {_form.DateOfBirth}");
            diagLog.AppendLine($"  Course: {_form.Course}");
            diagLog.AppendLine($"  AdmissionCategory: {_form.AdmissionCategory}");
            diagLog.AppendLine($"  Email: {_form.Email}");
            diagLog.AppendLine($"  PhoneNumber: {_form.PhoneNumber}");
            diagLog.AppendLine($"  FatherName: {_form.FatherName}");
            diagLog.AppendLine($"  MotherName: {_form.MotherName}");
            diagLog.AppendLine($"  CuetSubject1: {_form.CuetSubject1}");
            diagLog.AppendLine($"  CuetScoreObtained1: {_form.CuetScoreObtained1}");
            diagLog.AppendLine($"  PermanentAddress: {_form.PermanentAddress}");
            diagLog.AppendLine($"  AadharNumber: {_form.AadharNumber}");
            diagLog.AppendLine($"  CollegeRollNo: {_form.CollegeRollNo}");
            diagLog.AppendLine($"  StudentDeclarationName: {_form.StudentDeclarationName}");
            try { File.WriteAllText(Path.Combine(_dataPath, "extraction_diagnostic.log"), diagLog.ToString()); }
            catch { }

            // Save to database
            using var db = new AppDbContext();
            var dbForm = await db.AdmissionForms.FindAsync(_formId);
            if (dbForm != null)
            {
                dbForm.ExtractedDataJson = _form.ExtractedDataJson;
                dbForm.OcrProvider = _form.OcrProvider;
                dbForm.Status = _form.Status;
                
                // Copy extracted fields
                CopyFormFields(_form, dbForm);
                await db.SaveChangesAsync();
            }

            LoadFieldsFromForm();
            UpdateStatusDisplay();
            
            // Determine extraction method from JSON output
            var extractionMethod = "spatial";
            try 
            {
                using var jsonCheck = System.Text.Json.JsonDocument.Parse(_form.ExtractedDataJson);
                if (jsonCheck.RootElement.TryGetProperty("extraction_method", out var methodProp))
                    extractionMethod = methodProp.GetString() ?? "spatial";
            } catch { }
            
            var methodLabel = extractionMethod == "gemini" ? "🤖 Gemini AI" : "📐 Spatial Analysis";
            var fieldsMsg = fieldsExtracted > 0 
                ? $"\n\n{fieldsExtracted} fields extracted using {methodLabel}."
                : "\nFields extracted using pattern matching.";
            
            MessageBox.Show(
                $"OCR extraction complete!\n\nExtracted {result.FullText.Length} characters.{fieldsMsg}\n\nPlease review and correct any errors.",
                "Success", MessageBoxButton.OK, MessageBoxImage.Information);
        }
        catch (Exception ex)
        {
            LogError("ReExtract", ex);
            ShowError($"Re-extraction failed:\n\n{ex.Message}\n\nCheck app_error.log in:\n{_dataPath}");
            TxtOcrStatus.Text = "✗ Error";
            TxtOcrStatus.Foreground = System.Windows.Media.Brushes.Red;
        }
        finally
        {
            BtnReExtract.IsEnabled = true;
            BtnAutofill.IsEnabled = true;
        }
    }

    // Print form
    private void Print_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            if (_form == null) return;
            SaveFieldsToForm();
            
            var printService = new OCRAdmissionForms.App.Services.PrintService();
            printService.PrintAdmissionForm(_form);
        }
        catch (Exception ex)
        {
            LogError("Print", ex);
            ShowError($"Print failed: {ex.Message}");
        }
    }

    // Export to Word document
    private async void Export_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            if (_form == null) return;
            SaveFieldsToForm();

            var dialog = new Microsoft.Win32.SaveFileDialog
            {
                Filter = "Word Document (*.docx)|*.docx",
                FileName = $"AdmissionForm_{_form.CollegeRollNo ?? _formId.ToString()}_{DateTime.Now:yyyyMMdd}.docx"
            };

            if (dialog.ShowDialog() == true)
            {
                var exportService = new PdfExportService();
                await exportService.ExportFormAsync(_form, dialog.FileName);
                MessageBox.Show($"Exported to:\n{dialog.FileName}", "Export Complete", MessageBoxButton.OK, MessageBoxImage.Information);
            }
        }
        catch (Exception ex)
        {
            LogError("Export", ex);
            ShowError($"Export failed: {ex.Message}");
        }
    }

    private void Back_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            if (Window.GetWindow(this) is MainWindow mainWindow)
            {
                mainWindow.ContentFrame.Navigate(new FormsPage());
            }
        }
        catch (Exception ex)
        {
            LogError("Back", ex);
        }
    }

    private async void Save_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            if (_form == null) return;

            SaveFieldsToForm();

            using var db = new AppDbContext();
            var dbForm = await db.AdmissionForms.Include(f => f.StudentProfile).FirstOrDefaultAsync(f => f.Id == _formId);
            if (dbForm == null)
            {
                ShowError("Form not found in database.");
                return;
            }

            // ===== Duplicate Aadhar check =====
            var aadhar = _form.AadharNumber?.Trim();
            if (!string.IsNullOrWhiteSpace(aadhar))
            {
                var duplicate = await db.AdmissionForms
                    .FirstOrDefaultAsync(f => f.Id != _formId && f.AadharNumber == aadhar);
                if (duplicate != null)
                {
                    ShowError($"Duplicate Aadhar number!\n\nAnother form (ID: {duplicate.Id}, {duplicate.StudentName ?? duplicate.Filename}) already has Aadhar: {aadhar}");
                    return;
                }
            }

            CopyFormFields(_form, dbForm);
            
            // Global Update: Update StudentProfile if linked
            if (dbForm.StudentProfileId.HasValue)
            {
                await UpdateStudentProfileFromForm(db, dbForm);
            }
            
            await db.SaveChangesAsync();
            
            MessageBox.Show("Form saved successfully!", "Success", MessageBoxButton.OK, MessageBoxImage.Information);
            
            // Refresh display (especially if status changed or fields updated)
            UpdateStatusDisplay();
        }
        catch (Exception ex)
        {
            LogError("Save", ex);
            ShowError($"Save failed: {ex.Message}");
        }
    }

    private async Task UpdateStudentProfileFromForm(AppDbContext db, AdmissionForm form)
    {
        if (!form.StudentProfileId.HasValue) return;
        
        var profile = await db.StudentProfiles.FindAsync(form.StudentProfileId.Value);
        if (profile != null)
        {
            // Propagate key identification fields to profile
            var studentName = form.StudentName
                ?? $"{form.FirstName} {form.MiddleName} {form.Surname}".Trim().Replace("  ", " ");
            
            if (!string.IsNullOrWhiteSpace(studentName))
                profile.StudentName = studentName;
                
            if (!string.IsNullOrWhiteSpace(form.AadharNumber))
                profile.AadharNumber = form.AadharNumber;
                
            if (!string.IsNullOrWhiteSpace(form.CollegeRollNo))
                profile.RollNumber = form.CollegeRollNo;
                
            profile.UpdatedDate = DateTime.UtcNow;
            profile.SyncStatus = SyncStatus.PendingUpdate;
        }
    }

    private async void Verify_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            if (_form == null) return;

            SaveFieldsToForm();

            using var db = new AppDbContext();
            var dbForm = await db.AdmissionForms.FindAsync(_formId);
            if (dbForm == null)
            {
                ShowError("Form not found in database.");
                return;
            }

            // ===== Duplicate Aadhar check =====
            var aadharCheck = _form.AadharNumber?.Trim();
            if (!string.IsNullOrWhiteSpace(aadharCheck))
            {
                var dupAadhar = await db.AdmissionForms
                    .FirstOrDefaultAsync(f => f.Id != _formId && f.AadharNumber == aadharCheck);
                if (dupAadhar != null)
                {
                    ShowError($"Cannot verify — Duplicate Aadhar number!\n\nAnother form (ID: {dupAadhar.Id}, {dupAadhar.StudentName ?? dupAadhar.Filename}) already has Aadhar: {aadharCheck}");
                    return;
                }
            }

            // ===== Duplicate Form ID check (DU Portal Form Number) =====
            var duFormNo = _form.DuPortalFormNumber?.Trim();
            if (!string.IsNullOrWhiteSpace(duFormNo))
            {
                var dupForm = await db.AdmissionForms
                    .FirstOrDefaultAsync(f => f.Id != _formId && f.DuPortalFormNumber == duFormNo);
                if (dupForm != null)
                {
                    ShowError($"Cannot verify — Duplicate DU Portal Form Number!\n\nAnother form (ID: {dupForm.Id}, {dupForm.StudentName ?? dupForm.Filename}) already has Form No: {duFormNo}");
                    return;
                }
            }

            CopyFormFields(_form, dbForm);
            dbForm.Status = FormStatus.Verified;
            dbForm.VerifiedDate = DateTime.UtcNow;
            dbForm.VerifiedBy = Environment.UserName;

            // ===== Create or link StudentProfile =====
            var studentName = dbForm.StudentName
                ?? $"{dbForm.FirstName} {dbForm.MiddleName} {dbForm.Surname}".Trim()
                    .Replace("  ", " ");
            var aadhar = dbForm.AadharNumber?.Trim();
            var rollNo = dbForm.CollegeRollNo?.Trim();

            StudentProfile? profile = null;

            // Try to find existing profile by Aadhar (unique identifier)
            if (!string.IsNullOrWhiteSpace(aadhar))
            {
                profile = await db.StudentProfiles
                    .FirstOrDefaultAsync(s => s.AadharNumber == aadhar);
            }

            // Fallback: try by Roll Number
            if (profile == null && !string.IsNullOrWhiteSpace(rollNo))
            {
                profile = await db.StudentProfiles
                    .FirstOrDefaultAsync(s => s.RollNumber == rollNo);
            }

            // Fallback: try by exact name
            if (profile == null && !string.IsNullOrWhiteSpace(studentName))
            {
                profile = await db.StudentProfiles
                    .FirstOrDefaultAsync(s => s.StudentName == studentName);
            }

            // Create new profile if none found
            if (profile == null)
            {
                profile = new StudentProfile
                {
                    StudentName = studentName ?? "Unknown",
                    AadharNumber = aadhar,
                    RollNumber = rollNo,
                    CreatedDate = DateTime.UtcNow,
                    UpdatedDate = DateTime.UtcNow,
                };
                db.StudentProfiles.Add(profile);
                await db.SaveChangesAsync(); // Save to get the Id
            }
            else
            {
                // Update existing profile with latest info
                if (!string.IsNullOrWhiteSpace(studentName))
                    profile.StudentName = studentName;
                if (!string.IsNullOrWhiteSpace(aadhar))
                    profile.AadharNumber = aadhar;
                if (!string.IsNullOrWhiteSpace(rollNo))
                    profile.RollNumber = rollNo;
                profile.UpdatedDate = DateTime.UtcNow;
            }

            // Link the form to the profile
            dbForm.StudentProfileId = profile.Id;

            // Global Update: Popuplate/Update profile from form fields
            await UpdateStudentProfileFromForm(db, dbForm);

            await db.SaveChangesAsync();

            // Store verified form for OCR training
            TrainingDataService.SaveVerifiedForm(dbForm);

            // ===== Auto-extract attached documents (pages 5+) from PDF =====
            if (!string.IsNullOrWhiteSpace(dbForm.FilePath))
            {
                var attachedDocs = DocumentService.ExtractAttachedDocuments(
                    dbForm.FilePath, dbForm.Id, profile.Id);
                if (attachedDocs.Count > 0)
                {
                    db.StudentDocuments.AddRange(attachedDocs);
                    await db.SaveChangesAsync();
                    System.Diagnostics.Debug.WriteLine(
                        $"[Verify] Extracted {attachedDocs.Count} attached document(s) from PDF pages 5+");
                }
            }

            var docCount = await db.StudentDocuments
                .CountAsync(d => d.StudentProfileId == profile.Id);
            MessageBox.Show(
                $"Form verified and registered!\n\nStudent: {profile.StudentName}\nRoll No: {rollNo ?? "—"}\nDocuments attached: {docCount}", 
                "✅ Verified", MessageBoxButton.OK, MessageBoxImage.Information);

            if (Window.GetWindow(this) is MainWindow mainWindow)
            {
                mainWindow.ContentFrame.Navigate(new FormsPage());
            }
        }
        catch (Exception ex)
        {
            LogError("Verify", ex);
            ShowError($"Verification failed: {ex.Message}");
        }
    }

    private async void AttachDocument_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            if (_form == null) return;

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
            cmbType.SelectedIndex = cmbType.Items.Count - 1; // Default to "Other"
            panel.Children.Add(cmbType);
            var btnOk = new Button { Content = "Attach", HorizontalAlignment = HorizontalAlignment.Right, Padding = new Thickness(24, 8, 24, 8), Background = new System.Windows.Media.SolidColorBrush(System.Windows.Media.Color.FromRgb(37, 99, 235)), Foreground = System.Windows.Media.Brushes.White };
            btnOk.Click += (_, _) => { typeWindow.DialogResult = true; };
            panel.Children.Add(btnOk);
            typeWindow.Content = panel;

            if (typeWindow.ShowDialog() != true) return;

            var label = string.IsNullOrWhiteSpace(txtLabel.Text) ? "Attached Document" : txtLabel.Text.Trim();
            var selectedType = (cmbType.SelectedItem as ComboBoxItem)?.Tag is DocumentType dt2 ? dt2 : DocumentType.Other;

            using var db = new AppDbContext();
            var dbForm = await db.AdmissionForms.FindAsync(_formId);
            if (dbForm == null) return;

            var profileId = dbForm.StudentProfileId ?? 0;
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
                MessageBox.Show($"✅ {attachedCount} document(s) attached successfully!", "Attached",
                    MessageBoxButton.OK, MessageBoxImage.Information);
            }
        }
        catch (Exception ex)
        {
            LogError("AttachDocument", ex);
            ShowError($"Failed to attach document: {ex.Message}");
        }
    }

    private void CopyFormFields(AdmissionForm source, AdmissionForm dest)
    {
        // ============================================
        // PERSONAL DETAILS (15 fields)
        // ============================================
        dest.FirstName = source.FirstName;
        dest.MiddleName = source.MiddleName;
        dest.Surname = source.Surname;
        dest.StudentName = source.StudentName;
        dest.DateOfBirth = source.DateOfBirth;
        dest.Gender = source.Gender;
        dest.Category = source.Category;
        dest.BloodGroup = source.BloodGroup;
        dest.AadharNumber = source.AadharNumber;
        dest.Nationality = source.Nationality;
        dest.Religion = source.Religion;
        dest.BelowPovertyLine = source.BelowPovertyLine;
        dest.AnnualIncome = source.AnnualIncome;
        dest.MinorityCategory = source.MinorityCategory;
        
        // ============================================
        // PARENT DETAILS (14 fields)
        // ============================================
        dest.FatherName = source.FatherName;
        dest.MotherName = source.MotherName;
        dest.FatherPhone = source.FatherPhone;
        dest.MotherPhone = source.MotherPhone;
        dest.FatherMobile = source.FatherMobile;
        dest.MotherMobile = source.MotherMobile;
        dest.FatherOccupation = source.FatherOccupation;
        dest.MotherOccupation = source.MotherOccupation;
        dest.FatherDesignation = source.FatherDesignation;
        dest.MotherDesignation = source.MotherDesignation;
        dest.FatherOrganization = source.FatherOrganization;
        dest.MotherOrganization = source.MotherOrganization;
        dest.FatherEmail = source.FatherEmail;
        dest.MotherEmail = source.MotherEmail;
        
        // ============================================
        // GUARDIAN DETAILS (5 fields)
        // ============================================
        dest.GuardianName = source.GuardianName;
        dest.GuardianAddress = source.GuardianAddress;
        dest.GuardianMobile = source.GuardianMobile;
        dest.GuardianEmail = source.GuardianEmail;
        dest.GuardianRelation = source.GuardianRelation;
        
        // ============================================
        // CONTACT & ADDRESS DETAILS (9 fields)
        // ============================================
        dest.PhoneNumber = source.PhoneNumber;
        dest.AlternatePhone = source.AlternatePhone;
        dest.Email = source.Email;
        dest.PermanentAddress = source.PermanentAddress;
        dest.PermanentState = source.PermanentState;
        dest.PermanentPincode = source.PermanentPincode;
        dest.Pincode = source.Pincode;
        dest.CorrespondenceAddress = source.CorrespondenceAddress;
        dest.CorrespondenceState = source.CorrespondenceState;
        dest.CorrespondencePincode = source.CorrespondencePincode;
        
        // ============================================
        // ACADEMIC DETAILS (7 fields)
        // ============================================
        dest.Course = source.Course;
        dest.CollegeRollNo = source.CollegeRollNo;
        dest.CuetScore = source.CuetScore;
        dest.AcademicSession = source.AcademicSession;
        dest.AdmissionCategory = source.AdmissionCategory;
        dest.DuPortalFormNumber = source.DuPortalFormNumber;
        dest.DateOfAdmission = source.DateOfAdmission;
        
        // ============================================
        // CLASS XII DETAILS (6 fields)
        // ============================================
        dest.TwelfthBoard = source.TwelfthBoard;
        dest.TwelfthYear = source.TwelfthYear;
        dest.TwelfthPercentage = source.TwelfthPercentage;
        dest.TwelfthInstitution = source.TwelfthInstitution;
        dest.TwelfthRollNumber = source.TwelfthRollNumber;
        dest.HindiStudiedUpto = source.HindiStudiedUpto;
        
        // ============================================
        // OTHER INFO (4 fields)
        // ============================================
        dest.DuEnrollmentNumber = source.DuEnrollmentNumber;
        dest.HindiMediumPreference = source.HindiMediumPreference;
        dest.DeclarationDate = source.DeclarationDate;
        dest.DeclarationPlace = source.DeclarationPlace;
        
        // ============================================
        // CERTIFICATE DETAILS (6 fields)
        // ============================================
        dest.CategoryCertificateAuthority = source.CategoryCertificateAuthority;
        dest.CategoryCertificateNumber = source.CategoryCertificateNumber;
        dest.CategoryCertificateDate = source.CategoryCertificateDate;
        dest.DisabilityType = source.DisabilityType;
        dest.DisabilityPercentage = source.DisabilityPercentage;
        dest.UdidNumber = source.UdidNumber;
        
        // ============================================
    // DOCUMENT CHECKLIST (15 fields)
    // ============================================
    dest.DocAdmissionForm = source.DocAdmissionForm;
    dest.DocPhotographs = source.DocPhotographs;
    dest.DocCuetScorecard = source.DocCuetScorecard;
    dest.DocClassXiiMarksheet = source.DocClassXiiMarksheet;
    dest.DocClassXCertificate = source.DocClassXCertificate;
    dest.DocClassXiiCertificate = source.DocClassXiiCertificate;
    dest.DocCharacterCertificate = source.DocCharacterCertificate;
    dest.DocCasteCertificate = source.DocCasteCertificate;
    dest.DocMigrationCertificate = source.DocMigrationCertificate;
    dest.DocTransferCertificate = source.DocTransferCertificate;
    dest.DocGapCertificate = source.DocGapCertificate;
    dest.DocIncomeCertificate = source.DocIncomeCertificate;
    dest.DocDomicileCertificate = source.DocDomicileCertificate;
    dest.DocAadharCard = source.DocAadharCard;
    dest.DocMedicalFitness = source.DocMedicalFitness;
    dest.DocUndertakingRagging = source.DocUndertakingRagging;
        
        // ============================================
        // ADDITIONAL FIELDS (7 fields)
        // ============================================

        dest.LocalAddress = source.LocalAddress;
        dest.MotherAnnualIncome = source.MotherAnnualIncome;
        dest.FatherAnnualIncome = source.FatherAnnualIncome;
        dest.Class12Percentage = source.Class12Percentage;
        dest.Class12RollNo = source.Class12RollNo;
        dest.Class12Institution = source.Class12Institution;
        
        // ============================================
        // CUET SUBJECT DETAILS (19 fields) - NEW
        // ============================================
        dest.CuetSubject1 = source.CuetSubject1;
        dest.CuetTotalScore1 = source.CuetTotalScore1;
        dest.CuetScoreObtained1 = source.CuetScoreObtained1;
        dest.CuetSubject2 = source.CuetSubject2;
        dest.CuetTotalScore2 = source.CuetTotalScore2;
        dest.CuetScoreObtained2 = source.CuetScoreObtained2;
        dest.CuetSubject3 = source.CuetSubject3;
        dest.CuetTotalScore3 = source.CuetTotalScore3;
        dest.CuetScoreObtained3 = source.CuetScoreObtained3;
        dest.CuetSubject4 = source.CuetSubject4;
        dest.CuetTotalScore4 = source.CuetTotalScore4;
        dest.CuetScoreObtained4 = source.CuetScoreObtained4;
        dest.CuetSubject5 = source.CuetSubject5;
        dest.CuetTotalScore5 = source.CuetTotalScore5;
        dest.CuetScoreObtained5 = source.CuetScoreObtained5;
        dest.CuetSubject6 = source.CuetSubject6;
        dest.CuetTotalScore6 = source.CuetTotalScore6;
        dest.CuetScoreObtained6 = source.CuetScoreObtained6;
        dest.CuetTotalScoreAll = source.CuetTotalScoreAll;
        dest.CuetScoreObtainedAll = source.CuetScoreObtainedAll;
        
        // ============================================
        // 10TH CLASS DETAILS (4 fields) - NEW
        // ============================================
        dest.TenthBoard = source.TenthBoard;
        dest.TenthYear = source.TenthYear;
        dest.TenthPercentage = source.TenthPercentage;
        dest.TenthSchool = source.TenthSchool;
        
        // ============================================
        // ADDRESS LINES (6 fields) - NEW
        // ============================================
        dest.PermanentAddressLine1 = source.PermanentAddressLine1;
        dest.PermanentAddressLine2 = source.PermanentAddressLine2;
        dest.PermanentAddressLine3 = source.PermanentAddressLine3;
        dest.CorrespondenceAddressLine1 = source.CorrespondenceAddressLine1;
        dest.CorrespondenceAddressLine2 = source.CorrespondenceAddressLine2;
        dest.CorrespondenceAddressLine3 = source.CorrespondenceAddressLine3;
        
        // ============================================
        // LANDLINE PHONES (7 fields) - NEW
        // ============================================
        dest.MotherLandlineCode = source.MotherLandlineCode;
        dest.MotherLandline = source.MotherLandline;
        dest.FatherLandlineCode = source.FatherLandlineCode;
        dest.FatherLandline = source.FatherLandline;
        dest.GuardianLandlineCode = source.GuardianLandlineCode;
        dest.GuardianLandline = source.GuardianLandline;
        dest.GuardianOrganization = source.GuardianOrganization;
        
        // ============================================
        // EMERGENCY CONTACT (2 fields) - NEW
        // ============================================
        dest.EmergencyContactName = source.EmergencyContactName;
        dest.EmergencyContactPhone = source.EmergencyContactPhone;
        
        // ============================================
        // DECLARATIONS (9 fields) - NEW
        // ============================================
        dest.StudentDeclarationName = source.StudentDeclarationName;
        dest.StudentDeclarationDate = source.StudentDeclarationDate;
        dest.StudentDeclarationPlace = source.StudentDeclarationPlace;
        dest.ParentGuardianName = source.ParentGuardianName;
        dest.ParentGuardianRelationship = source.ParentGuardianRelationship;
        dest.ParentGuardianCandidateName = source.ParentGuardianCandidateName;
        dest.ParentGuardianCourse = source.ParentGuardianCourse;
        dest.ParentGuardianDate = source.ParentGuardianDate;
        dest.ParentGuardianPlace = source.ParentGuardianPlace;
    }

    private void ShowError(string message)
    {
        MessageBox.Show(message, "Error", MessageBoxButton.OK, MessageBoxImage.Warning);
    }

    private void LogError(string context, Exception ex)
    {
        try
        {
            Directory.CreateDirectory(_dataPath);
            var logEntry = $"[{DateTime.Now:yyyy-MM-dd HH:mm:ss}] [FormDetail:{context}] {ex.GetType().Name}: {ex.Message}\n   StackTrace: {ex.StackTrace?.Split('\n').FirstOrDefault()}\n\n";
            File.AppendAllText(_logPath, logEntry);
            System.Diagnostics.Debug.WriteLine(logEntry);
        }
        catch (Exception logEx)
        {
            System.Diagnostics.Debug.WriteLine($"[FormDetail:{context}] {ex.Message} (Log error: {logEx.Message})");
        }
    }
}
