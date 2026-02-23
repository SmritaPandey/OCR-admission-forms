using System.ComponentModel;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using OCRAdmissionForms.App.Views;
using OCRAdmissionForms.Core.Services;

namespace OCRAdmissionForms.App;

public partial class MainWindow : Window
{
    public MainWindow()
    {
        InitializeComponent();
        
        // Toggle sidebar visibility when navigating between pages
        ContentFrame.Navigated += (s, e) => UpdateSidebarVisibility();
        
        // Check if user is authenticated
        if (App.AuthService.IsAuthenticated)
        {
            ContentFrame.Navigate(new DashboardPage());
            UpdateUserInfo();
        }
        else
        {
            // Show login page first
            ContentFrame.Navigate(new LoginPage());
        }
        
        // Subscribe to BatchUploadService for global progress updates
        BatchUploadService.Instance.PropertyChanged += OnBatchUploadPropertyChanged;
        UpdateGlobalProgressPanel();

        // Subscribe to SyncService status changes
        if (App.SyncService != null)
        {
            App.SyncService.SyncStatusChanged += OnSyncStatusChanged;
            UpdateSyncIndicator();
        }
    }

    private void UpdateUserInfo()
    {
        var user = App.AuthService.CurrentUser;
        if (user != null)
        {
            TxtUserName.Text = user.FullName;
            TxtUserRole.Text = user.Role.ToString();
        }
    }

    private void UpdateSidebarVisibility()
    {
        bool isLoginPage = ContentFrame.Content is LoginPage;
        SidebarPanel.Visibility = isLoginPage ? Visibility.Collapsed : Visibility.Visible;
        
        // Adjust main grid column: collapse sidebar column when on login
        var mainGrid = SidebarPanel.Parent as System.Windows.Controls.Grid;
        if (mainGrid != null)
        {
            mainGrid.ColumnDefinitions[0].Width = isLoginPage 
                ? new GridLength(0) 
                : new GridLength(280);
        }
    }

    private void OnBatchUploadPropertyChanged(object? sender, PropertyChangedEventArgs e)
    {
        // Update UI on the dispatcher thread
        Dispatcher.Invoke(UpdateGlobalProgressPanel);
    }

    private void UpdateGlobalProgressPanel()
    {
        var service = BatchUploadService.Instance;
        
        // Show/hide the panel based on processing state or if there's a recent completion
        GlobalProgressPanel.Visibility = service.IsProcessing || 
            (!string.IsNullOrEmpty(service.StatusMessage) && service.TotalCount > 0) 
            ? Visibility.Visible 
            : Visibility.Collapsed;
        
        // Update the UI elements
        TxtGlobalStatus.Text = service.StatusMessage;
        TxtGlobalProgress.Text = service.ProgressText;
        GlobalProgressBar.Value = service.ProgressPercentage;
        TxtGlobalSuccess.Text = service.SuccessfulCount.ToString();
        TxtGlobalFailed.Text = service.FailedCount.ToString();
    }

    private void OnSyncStatusChanged(object? sender, SyncEventArgs e)
    {
        Dispatcher.Invoke(() =>
        {
            TxtSidebarSyncLabel.Text = e.Message;
            
            // Update dot color based on message
            if (e.Message.Contains("Sync") || e.Message.Contains("Online"))
            {
                SidebarSyncDot.Fill = new SolidColorBrush(Color.FromRgb(16, 185, 129)); // green
                TxtSidebarSyncStatus.Text = "Synced";
                TxtSidebarSyncStatus.Foreground = new SolidColorBrush(Color.FromRgb(16, 185, 129));
            }
            else if (e.Message.Contains("error") || e.Message.Contains("fail"))
            {
                SidebarSyncDot.Fill = new SolidColorBrush(Color.FromRgb(239, 68, 68)); // red
                TxtSidebarSyncStatus.Text = "Error";
                TxtSidebarSyncStatus.Foreground = new SolidColorBrush(Color.FromRgb(239, 68, 68));
            }
            else
            {
                SidebarSyncDot.Fill = new SolidColorBrush(Color.FromRgb(245, 158, 11)); // amber
                TxtSidebarSyncStatus.Text = "Working";
                TxtSidebarSyncStatus.Foreground = new SolidColorBrush(Color.FromRgb(245, 158, 11));
            }
        });
    }

    private void UpdateSyncIndicator()
    {
        if (AppConfig.SyncEnabled && !string.IsNullOrWhiteSpace(AppConfig.SyncServerUrl))
        {
            SidebarSyncDot.Fill = new SolidColorBrush(Color.FromRgb(59, 130, 246)); // blue
            TxtSidebarSyncLabel.Text = "Sync Enabled";
            TxtSidebarSyncStatus.Text = "Ready";
            TxtSidebarSyncStatus.Foreground = new SolidColorBrush(Color.FromRgb(59, 130, 246));
        }
        else
        {
            SidebarSyncDot.Fill = new SolidColorBrush(Color.FromRgb(148, 163, 184)); // gray
            TxtSidebarSyncLabel.Text = "Offline";
            TxtSidebarSyncStatus.Text = "—";
            TxtSidebarSyncStatus.Foreground = new SolidColorBrush(Color.FromRgb(148, 163, 184));
        }
    }

    private void ViewBatchUpload_Click(object sender, RoutedEventArgs e)
    {
        ContentFrame.Navigate(new BatchUploadPage());
    }

    private void NavButton_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button button && button.Tag is string tag)
        {
            switch (tag)
            {
                case "Dashboard":
                    ContentFrame.Navigate(new DashboardPage());
                    break;
                case "Students":
                    ContentFrame.Navigate(new StudentsPage());
                    break;
                case "Forms":
                    ContentFrame.Navigate(new FormsPage());
                    break;
                case "Search":
                    ContentFrame.Navigate(new SearchPage());
                    break;
                case "Upload":
                    ContentFrame.Navigate(new UploadPage());
                    break;
                case "BatchUpload":
                    ContentFrame.Navigate(new BatchUploadPage());
                    break;
                case "Export":
                    ContentFrame.Navigate(new ExportPage());
                    break;
                case "Settings":
                    ContentFrame.Navigate(new SettingsPage());
                    break;
            }
        }
    }

    private void Logout_Click(object sender, RoutedEventArgs e)
    {
        var result = MessageBox.Show(
            "Are you sure you want to logout?", 
            "Confirm Logout", 
            MessageBoxButton.YesNo, 
            MessageBoxImage.Question);
        
        if (result == MessageBoxResult.Yes)
        {
            // Clear auth session
            App.AuthService.Logout();
            
            // Reset user info display
            TxtUserName.Text = "";
            TxtUserRole.Text = "";
            
            // Navigate to login page
            ContentFrame.Navigate(new LoginPage());
        }
    }

    protected override void OnClosed(EventArgs e)
    {
        // Unsubscribe from service events
        BatchUploadService.Instance.PropertyChanged -= OnBatchUploadPropertyChanged;
        if (App.SyncService != null)
            App.SyncService.SyncStatusChanged -= OnSyncStatusChanged;
        base.OnClosed(e);
    }
}

