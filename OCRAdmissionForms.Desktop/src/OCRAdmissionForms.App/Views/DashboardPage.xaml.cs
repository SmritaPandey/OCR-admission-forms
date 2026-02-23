using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using Microsoft.EntityFrameworkCore;
using OCRAdmissionForms.Core.Data;
using OCRAdmissionForms.Core.Entities;

namespace OCRAdmissionForms.App.Views;

public partial class DashboardPage : Page
{
    public DashboardPage()
    {
        InitializeComponent();
        Loaded += DashboardPage_Loaded;
    }

    private async void DashboardPage_Loaded(object sender, RoutedEventArgs e)
    {
        await LoadStatisticsAsync();
        await LoadRecentFormsAsync();
    }

    private async Task LoadStatisticsAsync()
    {
        try
        {
            using var db = new AppDbContext();

            var totalForms = await db.AdmissionForms.CountAsync();
            var verified = await db.AdmissionForms.CountAsync(f => f.Status == FormStatus.Verified);
            var extracted = await db.AdmissionForms.CountAsync(f => f.Status == FormStatus.Extracted);
            var pending = await db.AdmissionForms.CountAsync(f => f.Status == FormStatus.Uploaded || f.Status == FormStatus.Extracting);
            var errors = await db.AdmissionForms.CountAsync(f => f.Status == FormStatus.Error);
            var students = await db.StudentProfiles.CountAsync();
            var todayUploads = await db.AdmissionForms.CountAsync(f => f.UploadDate.Date == DateTime.Today);

            TxtTotalForms.Text = totalForms.ToString();
            TxtProcessed.Text = verified.ToString();
            TxtExtracted.Text = extracted.ToString();
            TxtPending.Text = pending.ToString();
            TxtErrors.Text = errors.ToString();
            TxtStudents.Text = students.ToString();
            TxtTodayUploads.Text = todayUploads.ToString();

            // Welcome message with user info
            if (App.AuthService?.CurrentUser != null)
            {
                TxtWelcome.Text = $"Welcome, {App.AuthService.CurrentUser.FullName}! Here's your overview for today.";
            }
        }
        catch (Exception ex)
        {
            TxtTotalForms.Text = "0";
            TxtProcessed.Text = "0";
            TxtExtracted.Text = "0";
            TxtPending.Text = "0";
            TxtErrors.Text = "0";
            TxtStudents.Text = "0";
            TxtTodayUploads.Text = "0";
            System.Diagnostics.Debug.WriteLine($"Stats error: {ex.Message}");
        }
    }

    private async Task LoadRecentFormsAsync()
    {
        try
        {
            using var db = new AppDbContext();

            var recentForms = await db.AdmissionForms
                .OrderByDescending(f => f.UploadDate)
                .Take(10)
                .ToListAsync();

            RecentFormsGrid.ItemsSource = recentForms.Select(f => new
            {
                f.Id,
                f.Filename,
                StudentName = f.StudentName ?? f.FirstName ?? "Not extracted",
                Course = f.Course ?? "-",
                f.Status,
                f.UploadDate
            }).ToList();
        }
        catch (Exception ex)
        {
            RecentFormsGrid.ItemsSource = null;
            System.Diagnostics.Debug.WriteLine($"Recent forms error: {ex.Message}");
        }
    }

    // ==================== Drilldown Click Handlers ====================

    private void CardTotalForms_Click(object sender, MouseButtonEventArgs e)
    {
        NavigateToForms(null); // All forms
    }

    private void CardProcessed_Click(object sender, MouseButtonEventArgs e)
    {
        NavigateToForms(FormStatus.Verified);
    }

    private void CardExtracted_Click(object sender, MouseButtonEventArgs e)
    {
        NavigateToForms(FormStatus.Extracted);
    }

    private void CardPending_Click(object sender, MouseButtonEventArgs e)
    {
        NavigateToForms(FormStatus.Uploaded);
    }

    private void CardErrors_Click(object sender, MouseButtonEventArgs e)
    {
        NavigateToForms(FormStatus.Error);
    }

    private void CardStudents_Click(object sender, MouseButtonEventArgs e)
    {
        if (Window.GetWindow(this) is MainWindow mainWindow)
        {
            mainWindow.ContentFrame.Navigate(new StudentsPage());
        }
    }

    private void CardToday_Click(object sender, MouseButtonEventArgs e)
    {
        // Navigate to forms page - filter should show today's uploads
        NavigateToForms(null);
    }

    private void NavigateToForms(FormStatus? statusFilter)
    {
        if (Window.GetWindow(this) is MainWindow mainWindow)
        {
            var formsPage = new FormsPage();
            mainWindow.ContentFrame.Navigate(formsPage);
            // Note: Status filter will be applied via the dropdown on the Forms page
        }
    }

    // ==================== Quick Actions ====================

    private void QuickUpload_Click(object sender, RoutedEventArgs e)
    {
        if (Window.GetWindow(this) is MainWindow mainWindow)
            mainWindow.ContentFrame.Navigate(new UploadPage());
    }

    private void QuickBatch_Click(object sender, RoutedEventArgs e)
    {
        if (Window.GetWindow(this) is MainWindow mainWindow)
            mainWindow.ContentFrame.Navigate(new BatchUploadPage());
    }

    private void ViewAllForms_Click(object sender, RoutedEventArgs e)
    {
        if (Window.GetWindow(this) is MainWindow mainWindow)
            mainWindow.ContentFrame.Navigate(new FormsPage());
    }

    private void ViewStudents_Click(object sender, RoutedEventArgs e)
    {
        if (Window.GetWindow(this) is MainWindow mainWindow)
            mainWindow.ContentFrame.Navigate(new StudentsPage());
    }

    // ==================== Recent Forms Grid ====================

    private void RecentFormsGrid_DoubleClick(object sender, MouseButtonEventArgs e)
    {
        if (RecentFormsGrid.SelectedItem != null)
        {
            // Get the Id from the anonymous type
            var selectedItem = RecentFormsGrid.SelectedItem;
            var idProperty = selectedItem.GetType().GetProperty("Id");
            if (idProperty != null)
            {
                var id = (int)idProperty.GetValue(selectedItem)!;
                if (Window.GetWindow(this) is MainWindow mainWindow)
                {
                    mainWindow.ContentFrame.Navigate(new FormDetailPage(id));
                }
            }
        }
    }
}
