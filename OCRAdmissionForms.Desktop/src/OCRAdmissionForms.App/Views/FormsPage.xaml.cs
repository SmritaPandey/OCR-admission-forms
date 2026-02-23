using System.IO;
using System.Text;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using ClosedXML.Excel;
using Microsoft.EntityFrameworkCore;
using Microsoft.Win32;
using OCRAdmissionForms.Core.Data;
using OCRAdmissionForms.Core.Entities;
using OCRAdmissionForms.Core.Services;
using QuestPDF.Fluent;
using QuestPDF.Helpers;
using QuestPDF.Infrastructure;
using QColors = QuestPDF.Helpers.Colors;

namespace OCRAdmissionForms.App.Views;

public class FormDisplayItem : System.ComponentModel.INotifyPropertyChanged
{
    public int Id { get; set; }
    public string Filename { get; set; } = "";
    public string? StudentName { get; set; }
    public string? Course { get; set; }
    public FormStatus Status { get; set; }
    public DateTime UploadDate { get; set; }
    
    private bool _isSelected;
    public bool IsSelected 
    { 
        get => _isSelected;
        set { _isSelected = value; PropertyChanged?.Invoke(this, new System.ComponentModel.PropertyChangedEventArgs(nameof(IsSelected))); }
    }

    public event System.ComponentModel.PropertyChangedEventHandler? PropertyChanged;

    public Brush StatusBg => Status switch
    {
        FormStatus.Verified => new SolidColorBrush(System.Windows.Media.Color.FromRgb(220, 252, 231)),
        FormStatus.Extracted => new SolidColorBrush(System.Windows.Media.Color.FromRgb(254, 249, 195)),
        FormStatus.Uploaded => new SolidColorBrush(System.Windows.Media.Color.FromRgb(224, 231, 255)),
        FormStatus.Error => new SolidColorBrush(System.Windows.Media.Color.FromRgb(254, 226, 226)),
        _ => new SolidColorBrush(System.Windows.Media.Color.FromRgb(241, 245, 249))
    };

    public Brush StatusFg => Status switch
    {
        FormStatus.Verified => new SolidColorBrush(System.Windows.Media.Color.FromRgb(22, 101, 52)),
        FormStatus.Extracted => new SolidColorBrush(System.Windows.Media.Color.FromRgb(161, 98, 7)),
        FormStatus.Uploaded => new SolidColorBrush(System.Windows.Media.Color.FromRgb(67, 56, 202)),
        FormStatus.Error => new SolidColorBrush(System.Windows.Media.Color.FromRgb(185, 28, 28)),
        _ => new SolidColorBrush(System.Windows.Media.Color.FromRgb(71, 85, 105))
    };
}

public partial class FormsPage : Page
{
    private int _currentPage = 1;
    private const int PageSize = 20;
    private int _totalPages = 1;
    private string _searchQuery = "";
    private FormStatus? _statusFilter = null;
    private string _sortBy = "date_desc";
    private List<FormDisplayItem> _allForms = new();
    private bool _isLoaded = false;

    public FormsPage()
    {
        InitializeComponent();
        QuestPDF.Settings.License = LicenseType.Community;
        Loaded += FormsPage_Loaded;
    }

    private async void FormsPage_Loaded(object sender, RoutedEventArgs e)
    {
        _isLoaded = true;
        await LoadFormsAsync();
    }

    private async Task LoadFormsAsync()
    {
        using var db = new AppDbContext();

        IQueryable<AdmissionForm> query = db.AdmissionForms;

        // Filter by status
        if (_statusFilter.HasValue)
        {
            query = query.Where(f => f.Status == _statusFilter.Value);
        }

        // Search
        if (!string.IsNullOrWhiteSpace(_searchQuery))
        {
            var q = _searchQuery.ToLower();
            query = query.Where(f =>
                (f.StudentName != null && f.StudentName.ToLower().Contains(q)) ||
                (f.CollegeRollNo != null && f.CollegeRollNo.Contains(q)) ||
                (f.AadharNumber != null && f.AadharNumber.Contains(q)) ||
                f.Filename.ToLower().Contains(q));
        }

        // Sort
        query = _sortBy switch
        {
            "date_asc" => query.OrderBy(f => f.UploadDate),
            "name_asc" => query.OrderBy(f => f.StudentName),
            "name_desc" => query.OrderByDescending(f => f.StudentName),
            "status" => query.OrderBy(f => f.Status),
            _ => query.OrderByDescending(f => f.UploadDate)
        };

        var totalCount = await query.CountAsync();
        _totalPages = Math.Max(1, (int)Math.Ceiling((double)totalCount / PageSize));
        _currentPage = Math.Min(_currentPage, _totalPages);

        var forms = await query
            .Skip((_currentPage - 1) * PageSize)
            .Take(PageSize)
            .Select(f => new FormDisplayItem
            {
                Id = f.Id,
                Filename = f.Filename,
                StudentName = f.StudentName ?? f.FirstName,
                Course = f.Course,
                Status = f.Status,
                UploadDate = f.UploadDate
            })
            .ToListAsync();

        _allForms = forms;
        FormsGrid.ItemsSource = forms;
        TxtPageInfo.Text = $"Page {_currentPage} of {_totalPages} ({totalCount} total)";
        TxtSubtitle.Text = $"Showing {forms.Count} of {totalCount} forms";
        BtnPrev.IsEnabled = _currentPage > 1;
        BtnNext.IsEnabled = _currentPage < _totalPages;
    }

    // Navigation
    private void NewForm_Click(object sender, RoutedEventArgs e)
    {
        if (Window.GetWindow(this) is MainWindow mainWindow)
            mainWindow.ContentFrame.Navigate(new UploadPage());
    }

    private void FormsGrid_DoubleClick(object sender, MouseButtonEventArgs e)
    {
        if (FormsGrid.SelectedItem is FormDisplayItem item)
            NavigateToForm(item.Id);
    }

    private void EditForm_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button btn && btn.Tag != null)
        {
            try { NavigateToForm(Convert.ToInt32(btn.Tag)); }
            catch { /* ignore invalid tag */ }
        }
    }

    private void NavigateToForm(int id)
    {
        if (Window.GetWindow(this) is MainWindow mainWindow)
            mainWindow.ContentFrame.Navigate(new FormDetailPage(id));
    }

    // Search
    private void Search_Click(object sender, RoutedEventArgs e) => ApplySearch();
    private void Search_KeyDown(object sender, KeyEventArgs e) { if (e.Key == Key.Enter) ApplySearch(); }
    private async void ApplySearch()
    {
        _searchQuery = TxtSearch.Text.Trim();
        _currentPage = 1;
        await LoadFormsAsync();
    }

    // Filter
    private async void Status_Changed(object sender, SelectionChangedEventArgs e)
    {
        if (!_isLoaded) return;
        if (CmbStatus.SelectedIndex == 0) _statusFilter = null;
        else if (CmbStatus.SelectedIndex == 1) _statusFilter = FormStatus.Uploaded;
        else if (CmbStatus.SelectedIndex == 2) _statusFilter = FormStatus.Extracted;
        else if (CmbStatus.SelectedIndex == 3) _statusFilter = FormStatus.Verified;
        else if (CmbStatus.SelectedIndex == 4) _statusFilter = FormStatus.Error;
        _currentPage = 1;
        await LoadFormsAsync();
    }

    // Sort
    private async void Sort_Changed(object sender, SelectionChangedEventArgs e)
    {
        if (!_isLoaded) return;
        _sortBy = CmbSort.SelectedIndex switch
        {
            1 => "date_asc",
            2 => "name_asc",
            3 => "name_desc",
            4 => "status",
            _ => "date_desc"
        };
        await LoadFormsAsync();
    }

    // Pagination
    private async void PrevPage_Click(object sender, RoutedEventArgs e)
    {
        if (_currentPage > 1) { _currentPage--; await LoadFormsAsync(); }
    }
    private async void NextPage_Click(object sender, RoutedEventArgs e)
    {
        if (_currentPage < _totalPages) { _currentPage++; await LoadFormsAsync(); }
    }

    // Delete
    private async void DeleteForm_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button btn && btn.Tag != null)
        {
            try
            {
                var id = Convert.ToInt32(btn.Tag);
                if (MessageBox.Show($"Delete form #{id}?", "Confirm Delete", MessageBoxButton.YesNo, MessageBoxImage.Warning) == MessageBoxResult.Yes)
                {
                    using var db = new AppDbContext();
                    var form = await db.AdmissionForms.FindAsync(id);
                    if (form != null)
                    {
                        db.AdmissionForms.Remove(form);
                        await db.SaveChangesAsync();
                        await LoadFormsAsync();
                    }
                }
            }
            catch { /* ignore invalid tag */ }
        }
    }

    private async void DeleteSelected_Click(object sender, RoutedEventArgs e)
    {
        var selected = _allForms.Where(f => f.IsSelected).ToList();
        if (selected.Count == 0)
        {
            MessageBox.Show("No forms selected", "Info", MessageBoxButton.OK, MessageBoxImage.Information);
            return;
        }

        if (MessageBox.Show($"Delete {selected.Count} selected forms?", "Confirm Delete", MessageBoxButton.YesNo, MessageBoxImage.Warning) == MessageBoxResult.Yes)
        {
            using var db = new AppDbContext();
            var ids = selected.Select(f => f.Id).ToList();
            var forms = await db.AdmissionForms.Where(f => ids.Contains(f.Id)).ToListAsync();
            db.AdmissionForms.RemoveRange(forms);
            await db.SaveChangesAsync();
            await LoadFormsAsync();
        }
    }

    // Select All
    private void SelectAll_Click(object sender, RoutedEventArgs e)
    {
        if (sender is CheckBox chk)
        {
            bool isChecked = chk.IsChecked == true;
            foreach (var form in _allForms)
                form.IsSelected = isChecked;
        }
    }

    // Export Functions
    private async void ExportJson_Click(object sender, RoutedEventArgs e)
    {
        var dialog = new SaveFileDialog { Filter = "JSON|*.json", FileName = "forms_export.json" };
        if (dialog.ShowDialog() == true)
        {
            using var db = new AppDbContext();
            var forms = await db.AdmissionForms.ToListAsync();
            var json = JsonSerializer.Serialize(forms, new JsonSerializerOptions { WriteIndented = true });
            await File.WriteAllTextAsync(dialog.FileName, json);
            MessageBox.Show($"Exported {forms.Count} forms to JSON", "Export Complete", MessageBoxButton.OK, MessageBoxImage.Information);
        }
    }

    private async void ExportCsv_Click(object sender, RoutedEventArgs e)
    {
        var dialog = new SaveFileDialog { Filter = "CSV|*.csv", FileName = "forms_export.csv" };
        if (dialog.ShowDialog() == true)
        {
            using var db = new AppDbContext();
            var forms = await db.AdmissionForms.ToListAsync();
            var sb = new StringBuilder();
            sb.AppendLine("Id,Filename,StudentName,Course,Status,UploadDate,Phone,Email,Aadhar");
            foreach (var f in forms)
            {
                sb.AppendLine($"{f.Id},\"{f.Filename}\",\"{f.StudentName}\",\"{f.Course}\",{f.Status},{f.UploadDate:yyyy-MM-dd},\"{f.PhoneNumber}\",\"{f.Email}\",\"{f.AadharNumber}\"");
            }
            await File.WriteAllTextAsync(dialog.FileName, sb.ToString());
            MessageBox.Show($"Exported {forms.Count} forms to CSV", "Export Complete", MessageBoxButton.OK, MessageBoxImage.Information);
        }
    }

    private async void ExportExcel_Click(object sender, RoutedEventArgs e)
    {
        var dialog = new SaveFileDialog { Filter = "Excel|*.xlsx", FileName = "forms_export.xlsx" };
        if (dialog.ShowDialog() == true)
        {
            using var db = new AppDbContext();
            var forms = await db.AdmissionForms.ToListAsync();

            using var workbook = new XLWorkbook();
            var ws = workbook.Worksheets.Add("Forms");

            // Header
            ws.Cell(1, 1).Value = "ID";
            ws.Cell(1, 2).Value = "Filename";
            ws.Cell(1, 3).Value = "Student Name";
            ws.Cell(1, 4).Value = "Course";
            ws.Cell(1, 5).Value = "Status";
            ws.Cell(1, 6).Value = "Upload Date";
            ws.Cell(1, 7).Value = "Phone";
            ws.Cell(1, 8).Value = "Email";
            ws.Cell(1, 9).Value = "Aadhar";
            ws.Row(1).Style.Font.Bold = true;

            int row = 2;
            foreach (var f in forms)
            {
                ws.Cell(row, 1).Value = f.Id;
                ws.Cell(row, 2).Value = f.Filename;
                ws.Cell(row, 3).Value = f.StudentName ?? "";
                ws.Cell(row, 4).Value = f.Course ?? "";
                ws.Cell(row, 5).Value = f.Status.ToString();
                ws.Cell(row, 6).Value = f.UploadDate;
                ws.Cell(row, 7).Value = f.PhoneNumber ?? "";
                ws.Cell(row, 8).Value = f.Email ?? "";
                ws.Cell(row, 9).Value = f.AadharNumber ?? "";
                row++;
            }

            ws.Columns().AdjustToContents();
            workbook.SaveAs(dialog.FileName);
            MessageBox.Show($"Exported {forms.Count} forms to Excel", "Export Complete", MessageBoxButton.OK, MessageBoxImage.Information);
        }
    }

    private async void ExportPdf_Click(object sender, RoutedEventArgs e)
    {
        var dialog = new SaveFileDialog { Filter = "PDF|*.pdf", FileName = "forms_export.pdf" };
        if (dialog.ShowDialog() == true)
        {
            using var db = new AppDbContext();
            var forms = await db.AdmissionForms.ToListAsync();

            Document.Create(container =>
            {
                container.Page(page =>
                {
                    page.Size(PageSizes.A4.Landscape());
                    page.Margin(30);
                    page.Header().Text("Admission Forms Export").FontSize(20).Bold().FontColor(QColors.Blue.Darken3);
                    page.Content().Table(table =>
                    {
                        table.ColumnsDefinition(columns =>
                        {
                            columns.ConstantColumn(40);
                            columns.RelativeColumn(2);
                            columns.RelativeColumn(2);
                            columns.RelativeColumn(1);
                            columns.RelativeColumn(1);
                            columns.RelativeColumn(1);
                        });

                        table.Header(header =>
                        {
                            header.Cell().Text("ID").Bold();
                            header.Cell().Text("Filename").Bold();
                            header.Cell().Text("Student").Bold();
                            header.Cell().Text("Course").Bold();
                            header.Cell().Text("Status").Bold();
                            header.Cell().Text("Date").Bold();
                        });

                        foreach (var f in forms)
                        {
                            table.Cell().Text(f.Id.ToString());
                            table.Cell().Text(f.Filename);
                            table.Cell().Text(f.StudentName ?? "");
                            table.Cell().Text(f.Course ?? "");
                            table.Cell().Text(f.Status.ToString());
                            table.Cell().Text(f.UploadDate.ToString("d"));
                        }
                    });
                    page.Footer().AlignCenter().Text($"Generated {DateTime.Now:g} - {forms.Count} forms");
                });
            }).GeneratePdf(dialog.FileName);

            MessageBox.Show($"Exported {forms.Count} forms to PDF", "Export Complete", MessageBoxButton.OK, MessageBoxImage.Information);
        }
    }

    // ═══ AUTOMATION ═══

    private async void AutoVerify_Click(object sender, RoutedEventArgs e)
    {
        var selected = _allForms.Where(f => f.IsSelected).ToList();
        if (selected.Count == 0)
        {
            MessageBox.Show("Select forms to auto-verify first.", "No Selection", MessageBoxButton.OK, MessageBoxImage.Information);
            return;
        }

        var confirm = MessageBox.Show(
            $"Auto-verify {selected.Count} selected form(s)?\n\nForms with confidence ≥ 85% and required fields (Name, Course) will be marked as Verified.",
            "Auto-Verify", MessageBoxButton.YesNo, MessageBoxImage.Question);
        if (confirm != MessageBoxResult.Yes) return;

        int verified = 0, skipped = 0;

        using var db = new AppDbContext();
        var ids = selected.Select(f => f.Id).ToList();
        var forms = await db.AdmissionForms.Where(f => ids.Contains(f.Id)).ToListAsync();

        foreach (var form in forms)
        {
            if (form.Status == FormStatus.Verified) { skipped++; continue; }

            // Check confidence
            double confidence = 0;
            if (!string.IsNullOrEmpty(form.ExtractedDataJson))
            {
                try
                {
                    var doc = JsonDocument.Parse(form.ExtractedDataJson);
                    if (doc.RootElement.TryGetProperty("confidence", out var conf))
                        confidence = conf.GetDouble();
                }
                catch { }
            }

            // Check required fields
            bool hasName = !string.IsNullOrWhiteSpace(form.StudentName) || !string.IsNullOrWhiteSpace(form.FirstName);
            bool hasCourse = !string.IsNullOrWhiteSpace(form.Course);

            if (confidence >= 85 && hasName && hasCourse)
            {
                form.Status = FormStatus.Verified;
                form.VerifiedDate = DateTime.UtcNow;
                form.VerifiedBy = "Auto-Verify";

                // ===== Create or link StudentProfile =====
                var studentName = form.StudentName
                    ?? $"{form.FirstName} {form.MiddleName} {form.Surname}".Trim()
                        .Replace("  ", " ");
                var aadhar = form.AadharNumber?.Trim();
                var rollNo = form.CollegeRollNo?.Trim();

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
                        StudentName = studentName ?? "Unknown",
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
                verified++;
            }
            else
            {
                skipped++;
            }
        }

        await db.SaveChangesAsync();
        await LoadFormsAsync();

        MessageBox.Show($"Auto-verification complete!\n\n✅ Verified: {verified}\n⏭ Skipped (low confidence or missing fields): {skipped}",
            "Auto-Verify Results", MessageBoxButton.OK, MessageBoxImage.Information);
    }

    private async void BatchReExtract_Click(object sender, RoutedEventArgs e)
    {
        var selected = _allForms.Where(f => f.IsSelected).ToList();
        if (selected.Count == 0)
        {
            MessageBox.Show("Select forms to re-extract first.", "No Selection", MessageBoxButton.OK, MessageBoxImage.Information);
            return;
        }

        var confirm = MessageBox.Show(
            $"Re-extract {selected.Count} form(s) using Gemini AI?\n\nThis will overwrite existing extracted data.",
            "Batch Re-Extract", MessageBoxButton.YesNo, MessageBoxImage.Question);
        if (confirm != MessageBoxResult.Yes) return;

        var credPath = AppConfig.GoogleCredentialsPath;

        IOcrService? ocrService = null;
        if (!string.IsNullOrEmpty(credPath) && File.Exists(credPath))
        {
            try { ocrService = new GoogleVisionOcrService(credPath); }
            catch { }
        }

        if (ocrService == null)
        {
            MessageBox.Show("OCR service unavailable. Please configure credentials in Settings.",
                "Error", MessageBoxButton.OK, MessageBoxImage.Error);
            return;
        }

        var extractor = new FormFieldExtractor();
        int success = 0, failed = 0;

        BtnBatchReExtract.IsEnabled = false;
        BtnBatchReExtract.Content = "⏳ Extracting...";

        using var db = new AppDbContext();

        foreach (var item in selected)
        {
            try
            {
                var form = await db.AdmissionForms.FindAsync(item.Id);
                if (form == null || string.IsNullOrEmpty(form.FilePath) || !File.Exists(form.FilePath))
                {
                    failed++;
                    continue;
                }

                var result = await ocrService.ExtractTextAsync(form.FilePath, "gemini");

                if (!string.IsNullOrEmpty(result.Error))
                {
                    failed++;
                    continue;
                }

                var jsonResult = new Dictionary<string, object>
                {
                    ["text"] = result.FullText,
                    ["fields"] = result.ExtractedFields ?? new Dictionary<string, string>(),
                    ["confidence"] = result.Confidence,
                    ["fields_count"] = result.ExtractedFields?.Count ?? 0
                };
                form.ExtractedDataJson = JsonSerializer.Serialize(jsonResult);
                form.Status = FormStatus.Extracted;
                form.OcrProvider = "gemini";

                if (result.ExtractedFields != null && result.ExtractedFields.Count > 0)
                    form = extractor.ExtractFromPreExtracted(result.ExtractedFields, form);
                else
                    form = extractor.ExtractFieldsFromJson(form.ExtractedDataJson, form);

                success++;
            }
            catch
            {
                failed++;
            }
        }

        await db.SaveChangesAsync();
        await LoadFormsAsync();

        BtnBatchReExtract.IsEnabled = true;
        BtnBatchReExtract.Content = new System.Windows.Controls.StackPanel
        {
            Orientation = System.Windows.Controls.Orientation.Horizontal,
            Children = {
                new System.Windows.Controls.TextBlock { Text = "🔄", Margin = new Thickness(0, 0, 6, 0) },
                new System.Windows.Controls.TextBlock { Text = "Re-Extract", FontSize = 12 }
            }
        };

        MessageBox.Show($"Batch re-extraction complete!\n\n✅ Success: {success}\n❌ Failed: {failed}",
            "Re-Extract Results", MessageBoxButton.OK, MessageBoxImage.Information);
    }
}
