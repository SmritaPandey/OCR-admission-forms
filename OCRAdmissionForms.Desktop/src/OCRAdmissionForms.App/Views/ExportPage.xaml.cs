using System.Diagnostics;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using Microsoft.EntityFrameworkCore;
using Microsoft.Win32;
using OCRAdmissionForms.Core.Data;
using OCRAdmissionForms.Core.Services;

namespace OCRAdmissionForms.App.Views;

public partial class ExportPage : Page
{
    private readonly ExcelExportService _exportService = new();
    private readonly List<string> _recentExports = new();

    public ExportPage()
    {
        InitializeComponent();
        Loaded += ExportPage_Loaded;
    }

    private async void ExportPage_Loaded(object sender, RoutedEventArgs e)
    {
        await UpdateRecordCount();
        await LoadCourseFilter();
    }

    // ── Data Source Changed ──────────────────────────────────
    private async void DataSource_Changed(object sender, RoutedEventArgs e)
    {
        bool isForms = RbForms?.IsChecked == true;
        if (FiltersCard != null) FiltersCard.Visibility = isForms ? Visibility.Visible : Visibility.Collapsed;
        if (FieldSectionsCard != null) FieldSectionsCard.Visibility = isForms ? Visibility.Visible : Visibility.Collapsed;
        await UpdateRecordCount();
    }

    // ── Update Record Count ─────────────────────────────────
    private async Task UpdateRecordCount()
    {
        try
        {
            using var db = new AppDbContext();
            if (RbStudents?.IsChecked == true)
            {
                var count = await db.StudentProfiles.CountAsync();
                TxtRecordCount.Text = $"📋 {count} student record(s) available for export";
            }
            else
            {
                var query = db.AdmissionForms.AsQueryable();
                query = ApplyFilters(query);
                var count = await query.CountAsync();
                TxtRecordCount.Text = $"📋 {count} admission form(s) matching filters";
            }
        }
        catch
        {
            TxtRecordCount.Text = "⚠ Could not count records";
        }
    }

    // ── Load Courses for Filter ─────────────────────────────
    private async Task LoadCourseFilter()
    {
        try
        {
            using var db = new AppDbContext();
            var courses = await db.AdmissionForms
                .Where(f => f.Course != null && f.Course != "")
                .Select(f => f.Course!)
                .Distinct()
                .OrderBy(c => c)
                .ToListAsync();

            foreach (var course in courses)
                CmbCourse.Items.Add(new ComboBoxItem { Content = course });
        }
        catch { /* Silently skip */ }
    }

    // ── Apply Filters to Query ──────────────────────────────
    private IQueryable<OCRAdmissionForms.Core.Entities.AdmissionForm> ApplyFilters(
        IQueryable<OCRAdmissionForms.Core.Entities.AdmissionForm> query)
    {
        // Status
        if (CmbStatus?.SelectedIndex > 0)
        {
            var statusText = ((ComboBoxItem)CmbStatus.SelectedItem).Content.ToString();
            if (Enum.TryParse<OCRAdmissionForms.Core.Entities.FormStatus>(statusText, out var status))
                query = query.Where(f => f.Status == status);
        }

        // Course
        if (CmbCourse?.SelectedIndex > 0 || (!string.IsNullOrWhiteSpace(CmbCourse?.Text) && CmbCourse?.Text != "All"))
        {
            var courseText = CmbCourse?.SelectedIndex > 0
                ? ((ComboBoxItem)CmbCourse.SelectedItem).Content.ToString()
                : CmbCourse?.Text;
            if (!string.IsNullOrEmpty(courseText) && courseText != "All")
                query = query.Where(f => f.Course == courseText);
        }

        // Category
        if (CmbCategory?.SelectedIndex > 0)
        {
            var catText = ((ComboBoxItem)CmbCategory.SelectedItem).Content.ToString();
            query = query.Where(f => f.Category == catText);
        }

        // Date range
        if (DpFrom?.SelectedDate != null)
        {
            var from = DpFrom.SelectedDate.Value.Date;
            query = query.Where(f => f.UploadDate >= from);
        }
        if (DpTo?.SelectedDate != null)
        {
            var to = DpTo.SelectedDate.Value.Date.AddDays(1);
            query = query.Where(f => f.UploadDate < to);
        }

        return query;
    }

    // ── Get Selected Sections ───────────────────────────────
    private List<string> GetSelectedSections()
    {
        var sections = new List<string>();
        foreach (var child in FieldSectionChecks.Children)
        {
            if (child is CheckBox cb && cb.IsChecked == true && cb.Tag is string tag)
                sections.Add(tag);
        }
        return sections;
    }

    // ── Clear Filters ───────────────────────────────────────
    private async void ClearFilters_Click(object sender, RoutedEventArgs e)
    {
        CmbStatus.SelectedIndex = 0;
        CmbCourse.SelectedIndex = 0;
        CmbCategory.SelectedIndex = 0;
        DpFrom.SelectedDate = null;
        DpTo.SelectedDate = null;
        await UpdateRecordCount();
    }

    // ── Select/Deselect All Sections ────────────────────────
    private void SelectAll_Click(object sender, RoutedEventArgs e)
    {
        foreach (var child in FieldSectionChecks.Children)
            if (child is CheckBox cb) cb.IsChecked = true;
    }

    private void DeselectAll_Click(object sender, RoutedEventArgs e)
    {
        foreach (var child in FieldSectionChecks.Children)
            if (child is CheckBox cb) cb.IsChecked = false;
    }

    // ── Main Export ─────────────────────────────────────────
    private async void Export_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            bool isStudents = RbStudents.IsChecked == true;
            bool isExcel = RbExcel.IsChecked == true;
            bool isCsv = RbCsv.IsChecked == true;
            // else PDF

            // Build filename
            string ext = isExcel ? ".xlsx" : isCsv ? ".csv" : ".pdf";
            string prefix = isStudents ? "SRCC_Students" : "SRCC_AdmissionForms";
            string filter = isExcel ? "Excel Files (*.xlsx)|*.xlsx"
                : isCsv ? "CSV Files (*.csv)|*.csv"
                : "PDF Files (*.pdf)|*.pdf";

            var dialog = new SaveFileDialog
            {
                Filter = filter,
                DefaultExt = ext,
                FileName = $"{prefix}_{DateTime.Now:yyyyMMdd_HHmm}"
            };

            if (dialog.ShowDialog() != true) return;

            // Show progress
            BtnExport.IsEnabled = false;
            ExportProgress.Visibility = Visibility.Visible;
            TxtStatus.Text = "⏳ Exporting...";
            TxtStatus.Foreground = (Brush)FindResource("InfoBrush");

            if (isStudents)
            {
                await ExportStudentsAsync(dialog.FileName, isExcel, isCsv);
            }
            else
            {
                await ExportFormsAsync(dialog.FileName, isExcel, isCsv);
            }

            // Success
            ExportProgress.Visibility = Visibility.Collapsed;
            TxtStatus.Foreground = (Brush)FindResource("SuccessBrush");

            // Track recent exports
            AddRecentExport(dialog.FileName);

            // Ask to open
            var result = MessageBox.Show(
                $"Export saved to:\n{dialog.FileName}\n\nOpen the file now?",
                "Export Complete", MessageBoxButton.YesNo, MessageBoxImage.Information);

            if (result == MessageBoxResult.Yes)
            {
                Process.Start(new ProcessStartInfo(dialog.FileName) { UseShellExecute = true });
            }
        }
        catch (Exception ex)
        {
            ExportProgress.Visibility = Visibility.Collapsed;
            TxtStatus.Text = $"✗ Export failed: {ex.Message}";
            TxtStatus.Foreground = (Brush)FindResource("ErrorBrush");
        }
        finally
        {
            BtnExport.IsEnabled = true;
        }
    }

    private async Task ExportStudentsAsync(string filePath, bool isExcel, bool isCsv)
    {
        using var db = new AppDbContext();
        var students = await db.StudentProfiles.Include(s => s.Forms).ToListAsync();

        if (isExcel)
        {
            await _exportService.ExportStudentsAsync(students, filePath);
        }
        else if (isCsv)
        {
            await _exportService.ExportStudentsToCsvAsync(students, filePath);
        }
        else
        {
            // PDF — export using the same Excel method to a temp xlsx, then just note it
            // For students, we'll use a simple PDF
            await _exportService.ExportStudentsAsync(students, filePath.Replace(".pdf", ".xlsx"));
            // Rename for now; students PDF can be a future enhancement
            TxtStatus.Text = $"✓ Exported {students.Count} students (saved as Excel — student PDF coming soon)";
            return;
        }

        TxtStatus.Text = $"✓ Exported {students.Count} student record(s) to {Path.GetFileName(filePath)}";
    }

    private async Task ExportFormsAsync(string filePath, bool isExcel, bool isCsv)
    {
        using var db = new AppDbContext();
        var query = db.AdmissionForms.AsQueryable();
        query = ApplyFilters(query);
        var forms = await query.ToListAsync();
        var sections = GetSelectedSections();

        if (sections.Count == 0)
        {
            MessageBox.Show("Please select at least one field section to export.",
                "No Sections Selected", MessageBoxButton.OK, MessageBoxImage.Warning);
            return;
        }

        if (isExcel)
        {
            await _exportService.ExportFormsAsync(forms, filePath, sections);
        }
        else if (isCsv)
        {
            await _exportService.ExportFormsToCsvAsync(forms, filePath, sections);
        }
        else
        {
            await _exportService.ExportFormsToPdfAsync(forms, filePath, sections);
        }

        TxtStatus.Text = $"✓ Exported {forms.Count} form(s) ({sections.Count} sections, {(isExcel ? "Excel" : isCsv ? "CSV" : "PDF")})";
    }

    // ── Recent Exports ──────────────────────────────────────
    private void AddRecentExport(string filePath)
    {
        _recentExports.Insert(0, $"[{DateTime.Now:HH:mm}] {Path.GetFileName(filePath)}  →  {Path.GetDirectoryName(filePath)}");
        if (_recentExports.Count > 5) _recentExports.RemoveAt(5);
        TxtRecentExports.Text = string.Join("\n", _recentExports);
    }
}
