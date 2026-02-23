using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using Microsoft.Win32;
using OCRAdmissionForms.Core.Entities;
using OCRAdmissionForms.Core.Services;
using OCRAdmissionForms.App.Services;

namespace OCRAdmissionForms.App.Views;

public partial class SearchPage : Page
{
    private readonly SearchService _searchService = new();
    private readonly ExcelExportService _excelExport = new();
    private readonly PrintService _printService = new();
    
    private List<StudentProfile> _students = new();
    private List<AdmissionForm> _forms = new();
    private bool _isLoaded;

    public SearchPage()
    {
        InitializeComponent();
        Loaded += (s, e) => { _isLoaded = true; TxtSearch.Focus(); };
    }

    private void TxtSearch_KeyDown(object sender, KeyEventArgs e)
    {
        if (e.Key == Key.Enter)
            Search_Click(sender, e);
    }

    /// <summary>
    /// Get the selected text from a ComboBox, returning null if "All" is selected
    /// </summary>
    private string? GetFilterValue(ComboBox cmb)
    {
        if (cmb.SelectedItem is ComboBoxItem item)
        {
            var val = item.Content?.ToString();
            return val == "All" ? null : val;
        }
        return null;
    }

    private void Filter_Changed(object sender, SelectionChangedEventArgs e)
    {
        if (!_isLoaded) return;
        // Auto-search when any filter changes (if there's already a search term or any filter set)
        Search_Click(sender, new RoutedEventArgs());
    }

    private async void Search_Click(object sender, RoutedEventArgs e)
    {
        var query = TxtSearch.Text.Trim();
        var statusFilter = GetFilterValue(CmbStatus);
        var courseFilter = GetFilterValue(CmbCourse);
        var categoryFilter = GetFilterValue(CmbCategory);
        var genderFilter = GetFilterValue(CmbGender);
        var religionFilter = GetFilterValue(CmbReligion);
        var bloodGroupFilter = GetFilterValue(CmbBloodGroup);
        var nationalityFilter = GetFilterValue(CmbNationality);
        var bplFilter = GetFilterValue(CmbBPL);

        bool hasFilters = statusFilter != null || courseFilter != null || categoryFilter != null
            || genderFilter != null || religionFilter != null || bloodGroupFilter != null
            || nationalityFilter != null || bplFilter != null;

        if (string.IsNullOrEmpty(query) && !hasFilters)
        {
            TxtStatus.Text = "Enter a search term or select filters";
            return;
        }

        BtnSearch.IsEnabled = false;
        TxtStatus.Text = "Searching...";

        try
        {
            // Parse status enum
            FormStatus? status = statusFilter != null && Enum.TryParse<FormStatus>(statusFilter, out var s) ? s : null;

            // Search forms with all filters
            _forms = await _searchService.SearchFormsFilteredAsync(
                query: string.IsNullOrEmpty(query) ? null : query,
                status: status,
                course: courseFilter,
                category: categoryFilter,
                gender: genderFilter,
                religion: religionFilter,
                bloodGroup: bloodGroupFilter,
                nationality: nationalityFilter,
                bpl: bplFilter,
                pageSize: 500);

            // Search students (text search only, filters don't apply meaningfully)
            if (!string.IsNullOrEmpty(query))
                _students = await _searchService.SearchStudentsAsync(query, pageSize: 100);
            else
                _students = new List<StudentProfile>();

            StudentsGrid.ItemsSource = _students;
            FormsGrid.ItemsSource = _forms;

            TxtStudentCount.Text = $"Students ({_students.Count})";
            TxtFormCount.Text = $"Forms ({_forms.Count})";

            var total = _students.Count + _forms.Count;
            var filterDesc = hasFilters ? " (filtered)" : "";
            TxtStatus.Text = total > 0
                ? $"Found {total} results{filterDesc}"
                : $"No results found{filterDesc}";

            // Auto-switch to Forms tab if filters are used but no text search
            if (string.IsNullOrEmpty(query) && hasFilters && _forms.Count > 0)
                ResultsTabs.SelectedIndex = 1;
        }
        catch (Exception ex)
        {
            TxtStatus.Text = $"Error: {ex.Message}";
        }
        finally
        {
            BtnSearch.IsEnabled = true;
        }
    }

    private void Clear_Click(object sender, RoutedEventArgs e)
    {
        TxtSearch.Text = "";
        ClearFilters_Click(sender, e);
    }

    private void ClearFilters_Click(object sender, RoutedEventArgs e)
    {
        _isLoaded = false; // Prevent cascading filter events
        CmbStatus.SelectedIndex = 0;
        CmbCourse.SelectedIndex = 0;
        CmbCategory.SelectedIndex = 0;
        CmbGender.SelectedIndex = 0;
        CmbReligion.SelectedIndex = 0;
        CmbBloodGroup.SelectedIndex = 0;
        CmbNationality.SelectedIndex = 0;
        CmbBPL.SelectedIndex = 0;
        _isLoaded = true;

        StudentsGrid.ItemsSource = null;
        FormsGrid.ItemsSource = null;
        _students.Clear();
        _forms.Clear();
        TxtStudentCount.Text = "Students (0)";
        TxtFormCount.Text = "Forms (0)";
        TxtStatus.Text = "Enter a search term or use filters to begin";
        TxtSearch.Focus();
    }

    private void StudentsGrid_DoubleClick(object sender, MouseButtonEventArgs e)
    {
        if (StudentsGrid.SelectedItem is StudentProfile student)
        {
            if (Application.Current.MainWindow is MainWindow mainWindow)
                mainWindow.ContentFrame.Navigate(new StudentProfilePage(student));
        }
    }

    private void FormsGrid_DoubleClick(object sender, MouseButtonEventArgs e)
    {
        if (FormsGrid.SelectedItem is AdmissionForm form)
        {
            if (Application.Current.MainWindow is MainWindow mainWindow)
                mainWindow.ContentFrame.Navigate(new FormDetailPage(form.Id));
        }
    }

    private async void Export_Click(object sender, RoutedEventArgs e)
    {
        if (_students.Count == 0 && _forms.Count == 0)
        {
            MessageBox.Show("No results to export", "Export", MessageBoxButton.OK, MessageBoxImage.Information);
            return;
        }

        var dialog = new SaveFileDialog
        {
            Filter = "Excel Files (*.xlsx)|*.xlsx",
            FileName = $"SearchResults_{DateTime.Now:yyyyMMdd_HHmmss}.xlsx"
        };

        if (dialog.ShowDialog() == true)
        {
            try
            {
                if (_forms.Count > 0)
                {
                    await _excelExport.ExportFormsAsync(_forms, dialog.FileName);
                    TxtStatus.Text = $"Exported {_forms.Count} forms to Excel";
                }
                else if (_students.Count > 0)
                {
                    await _excelExport.ExportStudentsAsync(_students, dialog.FileName);
                    TxtStatus.Text = $"Exported {_students.Count} students to Excel";
                }
                
                MessageBox.Show($"Exported successfully to:\n{dialog.FileName}", "Export Complete", 
                    MessageBoxButton.OK, MessageBoxImage.Information);
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Export failed: {ex.Message}", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }
    }

    private void Print_Click(object sender, RoutedEventArgs e)
    {
        if (_forms.Count > 0)
            _printService.PrintBulkForms(_forms);
        else if (_students.Count > 0)
            _printService.PrintBulkStudents(_students);
        else
            MessageBox.Show("No results to print", "Print", MessageBoxButton.OK, MessageBoxImage.Information);
    }
}
