using System.IO;
using System.Text;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using ClosedXML.Excel;
using Microsoft.EntityFrameworkCore;
using Microsoft.Win32;
using OCRAdmissionForms.Core.Data;
using OCRAdmissionForms.Core.Entities;

namespace OCRAdmissionForms.App.Views;

public class StudentDisplayItem
{
    public int Id { get; set; }
    public string StudentName { get; set; } = "";
    public string? AadharNumber { get; set; }
    public string? RollNumber { get; set; }
    public string? Course { get; set; }
    public string Status { get; set; } = "—";
    public string? Phone { get; set; }
    public int FormCount { get; set; }
    public DateTime CreatedDate { get; set; }
    public bool IsSelected { get; set; }
}

public partial class StudentsPage : Page
{
    private int _currentPage = 1;
    private const int PageSize = 20;
    private int _totalPages = 1;
    private string _searchQuery = "";
    private string _sortBy = "name_asc";
    private List<StudentDisplayItem> _allStudents = new();
    private bool _isLoaded = false;

    public StudentsPage()
    {
        InitializeComponent();
        Loaded += StudentsPage_Loaded;
    }

    private async void StudentsPage_Loaded(object sender, RoutedEventArgs e)
    {
        _isLoaded = true;
        await LoadStudentsAsync();
    }

    private async Task LoadStudentsAsync()
    {
        using var db = new AppDbContext();

        IQueryable<StudentProfile> query = db.StudentProfiles.Include(s => s.Forms);

        // Search
        if (!string.IsNullOrWhiteSpace(_searchQuery))
        {
            var q = _searchQuery.ToLower();
            query = query.Where(s =>
                s.StudentName.ToLower().Contains(q) ||
                (s.AadharNumber != null && s.AadharNumber.Contains(q)) ||
                (s.RollNumber != null && s.RollNumber.Contains(q)));
        }

        // Sort
        query = _sortBy switch
        {
            "name_desc" => query.OrderByDescending(s => s.StudentName),
            "date_desc" => query.OrderByDescending(s => s.CreatedDate),
            "date_asc" => query.OrderBy(s => s.CreatedDate),
            _ => query.OrderBy(s => s.StudentName)
        };

        var totalCount = await query.CountAsync();
        _totalPages = Math.Max(1, (int)Math.Ceiling((double)totalCount / PageSize));
        _currentPage = Math.Min(_currentPage, _totalPages);

        var students = await query
            .Skip((_currentPage - 1) * PageSize)
            .Take(PageSize)
            .Select(s => new StudentDisplayItem
            {
                Id = s.Id,
                StudentName = s.StudentName,
                AadharNumber = s.AadharNumber,
                RollNumber = s.RollNumber,
                Course = s.Forms
                    .Where(f => f.Status == FormStatus.Verified)
                    .Select(f => f.Course)
                    .FirstOrDefault()
                    ?? s.Forms.OrderByDescending(f => f.UploadDate)
                        .Select(f => f.Course).FirstOrDefault(),
                Status = s.Forms.Any(f => f.Status == FormStatus.Verified)
                    ? "✓ Verified"
                    : s.Forms.OrderByDescending(f => f.UploadDate)
                        .Select(f => f.Status.ToString()).FirstOrDefault() ?? "—",
                Phone = s.Forms
                    .Where(f => f.Status == FormStatus.Verified)
                    .Select(f => f.PhoneNumber)
                    .FirstOrDefault()
                    ?? s.Forms.OrderByDescending(f => f.UploadDate)
                        .Select(f => f.PhoneNumber).FirstOrDefault(),
                FormCount = s.Forms.Count,
                CreatedDate = s.CreatedDate
            })
            .ToListAsync();

        _allStudents = students;
        StudentsGrid.ItemsSource = students;
        TxtPageInfo.Text = $"Page {_currentPage} of {_totalPages} ({totalCount} total)";
        TxtSubtitle.Text = $"Showing {students.Count} of {totalCount} students";
        BtnPrev.IsEnabled = _currentPage > 1;
        BtnNext.IsEnabled = _currentPage < _totalPages;
    }

    private void NewStudent_Click(object sender, RoutedEventArgs e)
    {
        MessageBox.Show("Students are created automatically when forms are verified.", "Info", MessageBoxButton.OK, MessageBoxImage.Information);
    }

    private void StudentsGrid_DoubleClick(object sender, MouseButtonEventArgs e)
    {
        if (StudentsGrid.SelectedItem is StudentDisplayItem item)
            NavigateToStudent(item.Id);
    }

    private void ViewStudent_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button btn && btn.Tag != null)
        {
            try { NavigateToStudent(Convert.ToInt32(btn.Tag)); }
            catch { /* ignore invalid tag */ }
        }
    }

    private void NavigateToStudent(int id)
    {
        if (Window.GetWindow(this) is MainWindow mainWindow)
            mainWindow.ContentFrame.Navigate(new StudentProfilePage(id));
    }

    // Search
    private void Search_Click(object sender, RoutedEventArgs e) => ApplySearch();
    private void Search_KeyDown(object sender, KeyEventArgs e) { if (e.Key == Key.Enter) ApplySearch(); }
    private async void ApplySearch()
    {
        _searchQuery = TxtSearch.Text.Trim();
        _currentPage = 1;
        await LoadStudentsAsync();
    }

    // Sort
    private async void Sort_Changed(object sender, SelectionChangedEventArgs e)
    {
        if (!_isLoaded) return;
        _sortBy = CmbSort.SelectedIndex switch
        {
            1 => "name_desc",
            2 => "date_desc",
            3 => "date_asc",
            _ => "name_asc"
        };
        await LoadStudentsAsync();
    }

    // Pagination
    private async void PrevPage_Click(object sender, RoutedEventArgs e)
    {
        if (_currentPage > 1) { _currentPage--; await LoadStudentsAsync(); }
    }
    private async void NextPage_Click(object sender, RoutedEventArgs e)
    {
        if (_currentPage < _totalPages) { _currentPage++; await LoadStudentsAsync(); }
    }

    // Delete
    private async void DeleteStudent_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button btn && btn.Tag != null)
        {
            try
            {
                var id = Convert.ToInt32(btn.Tag);
                if (MessageBox.Show($"Delete student #{id} and all associated forms?", "Confirm Delete", MessageBoxButton.YesNo, MessageBoxImage.Warning) == MessageBoxResult.Yes)
                {
                    using var db = new AppDbContext();
                    var student = await db.StudentProfiles.FindAsync(id);
                    if (student != null)
                    {
                        db.StudentProfiles.Remove(student);
                        await db.SaveChangesAsync();
                        await LoadStudentsAsync();
                    }
                }
            }
            catch { /* ignore invalid tag */ }
        }
    }

    private void SelectAll_Click(object sender, RoutedEventArgs e)
    {
        if (sender is CheckBox chk)
        {
            bool isChecked = chk.IsChecked ?? false;
            foreach (var s in _allStudents)
            {
                s.IsSelected = isChecked;
            }
            StudentsGrid.Items.Refresh();
        }
    }

    private async void DeleteSelected_Click(object sender, RoutedEventArgs e)
    {
        var selected = _allStudents.Where(s => s.IsSelected).ToList();
        if (selected.Count == 0)
        {
            MessageBox.Show("No students selected", "Info", MessageBoxButton.OK, MessageBoxImage.Information);
            return;
        }

        if (MessageBox.Show($"Delete {selected.Count} selected students?", "Confirm Delete", MessageBoxButton.YesNo, MessageBoxImage.Warning) == MessageBoxResult.Yes)
        {
            using var db = new AppDbContext();
            var ids = selected.Select(s => s.Id).ToList();
            var students = await db.StudentProfiles.Where(s => ids.Contains(s.Id)).ToListAsync();
            db.StudentProfiles.RemoveRange(students);
            await db.SaveChangesAsync();
            await LoadStudentsAsync();
        }
    }

    // Export
    private async void ExportCsv_Click(object sender, RoutedEventArgs e)
    {
        var dialog = new SaveFileDialog { Filter = "CSV|*.csv", FileName = "students_export.csv" };
        if (dialog.ShowDialog() == true)
        {
            using var db = new AppDbContext();
            var students = await db.StudentProfiles.ToListAsync();
            var sb = new StringBuilder();
            sb.AppendLine("Id,StudentName,AadharNumber,RollNumber,CreatedDate");
            foreach (var s in students)
            {
                sb.AppendLine($"{s.Id},\"{s.StudentName}\",\"{s.AadharNumber}\",\"{s.RollNumber}\",{s.CreatedDate:yyyy-MM-dd}");
            }
            await File.WriteAllTextAsync(dialog.FileName, sb.ToString());
            MessageBox.Show($"Exported {students.Count} students to CSV", "Export Complete", MessageBoxButton.OK, MessageBoxImage.Information);
        }
    }

    private async void ExportExcel_Click(object sender, RoutedEventArgs e)
    {
        var dialog = new SaveFileDialog { Filter = "Excel|*.xlsx", FileName = "students_export.xlsx" };
        if (dialog.ShowDialog() == true)
        {
            using var db = new AppDbContext();
            var students = await db.StudentProfiles.ToListAsync();

            using var workbook = new XLWorkbook();
            var ws = workbook.Worksheets.Add("Students");

            ws.Cell(1, 1).Value = "ID";
            ws.Cell(1, 2).Value = "Student Name";
            ws.Cell(1, 3).Value = "Aadhar Number";
            ws.Cell(1, 4).Value = "Roll Number";
            ws.Cell(1, 5).Value = "Created Date";
            ws.Row(1).Style.Font.Bold = true;

            int row = 2;
            foreach (var s in students)
            {
                ws.Cell(row, 1).Value = s.Id;
                ws.Cell(row, 2).Value = s.StudentName;
                ws.Cell(row, 3).Value = s.AadharNumber ?? "";
                ws.Cell(row, 4).Value = s.RollNumber ?? "";
                ws.Cell(row, 5).Value = s.CreatedDate;
                row++;
            }

            ws.Columns().AdjustToContents();
            workbook.SaveAs(dialog.FileName);
            MessageBox.Show($"Exported {students.Count} students to Excel", "Export Complete", MessageBoxButton.OK, MessageBoxImage.Information);
        }
    }
}
