using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using Microsoft.EntityFrameworkCore;
using Microsoft.Win32;
using OCRAdmissionForms.Core.Data;
using OCRAdmissionForms.Core.Entities;
using OCRAdmissionForms.Core.Services;

namespace OCRAdmissionForms.App.Views;

public partial class SettingsPage : Page
{
    private readonly AuthService _authService;

    public SettingsPage()
    {
        InitializeComponent();
        _authService = App.AuthService;
        Loaded += SettingsPage_Loaded;
    }

    private async void SettingsPage_Loaded(object sender, RoutedEventArgs e)
    {
        LoadUserProfile();
        LoadDatabaseConfig();
        LoadSyncConfig();
        UpdateCredentialStatus();
        LoadGeminiKey();
        await LoadUsersAsync();
    }

    // ══════════════════════════════════════════════════
    // 1. USER PROFILE
    // ══════════════════════════════════════════════════
    private void LoadUserProfile()
    {
        var user = _authService.CurrentUser;
        if (user != null)
        {
            TxtProfileName.Text = user.FullName;
            TxtProfileEmail.Text = user.Email ?? "";
            TxtProfileDept.Text = user.Department ?? "";
            TxtProfileRole.Text = user.Role.ToString();
            TxtProfileAvatar.Text = user.FullName.Length > 0 ? user.FullName[0].ToString().ToUpper() : "U";

            // Show user management for admins
            UserManagementPanel.Visibility = (_authService.IsAdmin) ? Visibility.Visible : Visibility.Collapsed;
        }
    }

    private async void SaveProfile_Click(object sender, RoutedEventArgs e)
    {
        var user = _authService.CurrentUser;
        if (user == null) return;

        try
        {
            using var db = new AppDbContext();
            var dbUser = await db.Users.FindAsync(user.Id);
            if (dbUser != null)
            {
                dbUser.FullName = TxtProfileName.Text.Trim();
                dbUser.Email = TxtProfileEmail.Text.Trim();
                dbUser.Department = TxtProfileDept.Text.Trim();
                await db.SaveChangesAsync();

                // Update in-memory
                user.FullName = dbUser.FullName;
                user.Email = dbUser.Email;
                user.Department = dbUser.Department;

                MessageBox.Show("Profile updated successfully.", "Success", MessageBoxButton.OK, MessageBoxImage.Information);
            }
        }
        catch (Exception ex)
        {
            MessageBox.Show($"Failed to save profile: {ex.Message}", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    // ══════════════════════════════════════════════════
    // 2. CHANGE PASSWORD
    // ══════════════════════════════════════════════════
    private async void ChangePassword_Click(object sender, RoutedEventArgs e)
    {
        var current = TxtCurrentPass.Password;
        var newPass = TxtNewPass.Password;
        var confirm = TxtConfirmPass.Password;

        if (string.IsNullOrWhiteSpace(current) || string.IsNullOrWhiteSpace(newPass))
        {
            MessageBox.Show("Please fill in all password fields.", "Validation", MessageBoxButton.OK, MessageBoxImage.Warning);
            return;
        }

        if (newPass != confirm)
        {
            MessageBox.Show("New password and confirm password do not match.", "Validation", MessageBoxButton.OK, MessageBoxImage.Warning);
            return;
        }

        if (newPass.Length < 6)
        {
            MessageBox.Show("New password must be at least 6 characters.", "Validation", MessageBoxButton.OK, MessageBoxImage.Warning);
            return;
        }

        try
        {
            var result = await _authService.ChangePasswordAsync(current, newPass);
            if (result.Success)
            {
                MessageBox.Show("Password changed successfully.", "Success", MessageBoxButton.OK, MessageBoxImage.Information);
                TxtCurrentPass.Clear();
                TxtNewPass.Clear();
                TxtConfirmPass.Clear();
            }
            else
            {
                MessageBox.Show(result.Error ?? "Current password is incorrect.", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }
        catch (Exception ex)
        {
            MessageBox.Show($"Error changing password: {ex.Message}", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    // ══════════════════════════════════════════════════
    // 3. USER MANAGEMENT
    // ══════════════════════════════════════════════════
    private async Task LoadUsersAsync()
    {
        if (!_authService.IsAdmin) return;
        try
        {
            var users = await _authService.GetAllUsersAsync();
            UsersGrid.ItemsSource = users;
        }
        catch { /* Ignore if user list fails */ }
    }

    private async void AddUser_Click(object sender, RoutedEventArgs e)
    {
        var username = TxtNewUsername.Text.Trim();
        var fullName = TxtNewFullName.Text.Trim();
        var password = TxtNewUserPass.Password;

        if (string.IsNullOrWhiteSpace(username) || string.IsNullOrWhiteSpace(fullName) || string.IsNullOrWhiteSpace(password))
        {
            MessageBox.Show("Please fill in all fields.", "Validation", MessageBoxButton.OK, MessageBoxImage.Warning);
            return;
        }

        try
        {
            var result = await _authService.RegisterUserAsync(username, password, fullName, UserRole.Staff);
            if (result.Success)
            {
                MessageBox.Show($"User '{username}' created successfully.", "Success", MessageBoxButton.OK, MessageBoxImage.Information);
                TxtNewUsername.Clear();
                TxtNewFullName.Clear();
                TxtNewUserPass.Clear();
                await LoadUsersAsync();
            }
            else
            {
                MessageBox.Show($"Failed: {result.Error}", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }
        catch (Exception ex)
        {
            MessageBox.Show($"Error creating user: {ex.Message}", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    // ══════════════════════════════════════════════════
    // 4. DATABASE CONFIGURATION
    // ══════════════════════════════════════════════════
    private void LoadDatabaseConfig()
    {
        TxtDbPath.Text = AppConfig.DatabasePath;
    }

    private void BrowseDbPath_Click(object sender, RoutedEventArgs e)
    {
        var dialog = new SaveFileDialog
        {
            Title = "Select Database Location",
            Filter = "SQLite Database|*.db",
            FileName = "srcc_dms.db",
            InitialDirectory = Path.GetDirectoryName(AppConfig.DatabasePath) ?? ""
        };

        if (dialog.ShowDialog() == true)
        {
            TxtDbPath.Text = dialog.FileName;
        }
    }

    private void ApplyDbPath_Click(object sender, RoutedEventArgs e)
    {
        var newPath = TxtDbPath.Text.Trim();
        if (string.IsNullOrWhiteSpace(newPath))
        {
            MessageBox.Show("Please specify a valid database path.", "Validation", MessageBoxButton.OK, MessageBoxImage.Warning);
            return;
        }

        var result = MessageBox.Show(
            $"Change database path to:\n{newPath}\n\nThe application will need to restart.",
            "Confirm Database Change", MessageBoxButton.OKCancel, MessageBoxImage.Question);

        if (result == MessageBoxResult.OK)
        {
            AppConfig.DatabasePath = newPath;
            MessageBox.Show("Database path updated. Please restart the application.", "Restart Required", MessageBoxButton.OK, MessageBoxImage.Information);
        }
    }

    private void ResetDbPath_Click(object sender, RoutedEventArgs e)
    {
        AppConfig.ResetToDefaults();
        TxtDbPath.Text = AppConfig.DatabasePath;
        MessageBox.Show("Database path reset to default.", "Info", MessageBoxButton.OK, MessageBoxImage.Information);
    }

    private void OpenDataFolder_Click(object sender, RoutedEventArgs e)
    {
        var dir = AppConfig.DataDirectory;
        Directory.CreateDirectory(dir);
        System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo(dir) { UseShellExecute = true });
    }

    // ══════════════════════════════════════════════════
    // 5. SYNC CONFIGURATION
    // ══════════════════════════════════════════════════
    private void LoadSyncConfig()
    {
        ChkSyncEnabled.IsChecked = AppConfig.SyncEnabled;
        TxtSyncUrl.Text = AppConfig.SyncServerUrl;
        TxtSyncInterval.Text = AppConfig.AutoSyncIntervalMinutes.ToString();
        UpdateSyncStatus();
    }

    private void SyncEnabled_Changed(object sender, RoutedEventArgs e)
    {
        // Just visual toggle; apply on Save
    }

    private void SaveSyncSettings_Click(object sender, RoutedEventArgs e)
    {
        AppConfig.SyncEnabled = ChkSyncEnabled.IsChecked == true;
        AppConfig.SyncServerUrl = TxtSyncUrl.Text.Trim();
        if (int.TryParse(TxtSyncInterval.Text, out var interval) && interval > 0)
            AppConfig.AutoSyncIntervalMinutes = interval;
        
        AppConfig.Save();
        UpdateSyncStatus();
        MessageBox.Show("Sync settings saved. Changes take effect on next restart.", "Settings Saved", MessageBoxButton.OK, MessageBoxImage.Information);
    }

    private async void SyncNow_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            TxtSyncStatus.Text = "Syncing...";
            SyncIndicator.Fill = new SolidColorBrush(Color.FromRgb(245, 158, 11)); // amber

            var result = await App.SyncService.SyncAsync();
            
            TxtSyncStatus.Text = result.Success ? "Sync completed" : $"Sync failed: {result.Message}";
            SyncIndicator.Fill = result.Success
                ? new SolidColorBrush(Color.FromRgb(16, 185, 129))
                : new SolidColorBrush(Color.FromRgb(239, 68, 68));
            TxtLastSync.Text = $"Last: {DateTime.Now:HH:mm:ss}";
        }
        catch (Exception ex)
        {
            TxtSyncStatus.Text = $"Sync error: {ex.Message}";
            SyncIndicator.Fill = new SolidColorBrush(Color.FromRgb(239, 68, 68));
        }
    }

    private async void TestSync_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            TxtSyncStatus.Text = "Testing connection...";
            var isOnline = await App.SyncService.CheckConnectivityAsync();
            TxtSyncStatus.Text = isOnline ? "✓ Server reachable" : "✗ Cannot reach server";
            SyncIndicator.Fill = isOnline
                ? new SolidColorBrush(Color.FromRgb(16, 185, 129))
                : new SolidColorBrush(Color.FromRgb(239, 68, 68));
        }
        catch (Exception ex)
        {
            TxtSyncStatus.Text = $"Connection test failed: {ex.Message}";
        }
    }

    private void UpdateSyncStatus()
    {
        if (AppConfig.SyncEnabled && !string.IsNullOrWhiteSpace(AppConfig.SyncServerUrl))
        {
            TxtSyncStatus.Text = "Sync enabled";
            SyncIndicator.Fill = new SolidColorBrush(Color.FromRgb(16, 185, 129));
        }
        else
        {
            TxtSyncStatus.Text = AppConfig.SyncEnabled ? "Sync enabled (no server URL)" : "Sync disabled";
            SyncIndicator.Fill = new SolidColorBrush(Color.FromRgb(148, 163, 184));
        }
    }

    // ══════════════════════════════════════════════════
    // 6. BACKUP & RESTORE
    // ══════════════════════════════════════════════════
    private void ExportBackup_Click(object sender, RoutedEventArgs e)
    {
        var dialog = new SaveFileDialog
        {
            Filter = "SQLite Database|*.db|All Files|*.*",
            FileName = $"srcc_dms_backup_{DateTime.Now:yyyyMMdd_HHmmss}.db"
        };

        if (dialog.ShowDialog() == true)
        {
            try
            {
                File.Copy(AppConfig.DatabasePath, dialog.FileName, overwrite: true);
                MessageBox.Show($"Backup saved to:\n{dialog.FileName}", "Backup Complete", MessageBoxButton.OK, MessageBoxImage.Information);
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Backup failed: {ex.Message}", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }
    }

    private void ImportBackup_Click(object sender, RoutedEventArgs e)
    {
        var dialog = new OpenFileDialog
        {
            Filter = "SQLite Database|*.db|All Files|*.*",
            Title = "Select Backup Database"
        };

        if (dialog.ShowDialog() == true)
        {
            var result = MessageBox.Show(
                $"Restore database from:\n{dialog.FileName}\n\nThis will replace the current database. The application will restart.\n\nProceed?",
                "Confirm Restore", MessageBoxButton.YesNo, MessageBoxImage.Warning);

            if (result == MessageBoxResult.Yes)
            {
                try
                {
                    File.Copy(dialog.FileName, AppConfig.DatabasePath, overwrite: true);
                    MessageBox.Show("Database restored. Please restart the application.", "Restore Complete", MessageBoxButton.OK, MessageBoxImage.Information);
                }
                catch (Exception ex)
                {
                    MessageBox.Show($"Restore failed: {ex.Message}", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
                }
            }
        }
    }

    // ══════════════════════════════════════════════════
    // 7. GOOGLE CLOUD CREDENTIALS
    // ══════════════════════════════════════════════════
    private void UpdateCredentialStatus()
    {
        var credPath = AppConfig.GoogleCredentialsPath;
        bool hasCredentials = !string.IsNullOrEmpty(credPath) && File.Exists(credPath);

        if (hasCredentials)
        {
            TxtCredentialPath.Text = credPath;
            TxtCredentialStatus.Text = "✓ Configured";
            TxtCredentialStatus.Foreground = new SolidColorBrush(Color.FromRgb(16, 185, 129));
            CredentialStatusBadge.Background = new SolidColorBrush(Color.FromRgb(236, 253, 245));
        }
        else
        {
            TxtCredentialPath.Text = "Not set";
            TxtCredentialStatus.Text = "✗ Not Configured";
            TxtCredentialStatus.Foreground = new SolidColorBrush(Color.FromRgb(239, 68, 68));
            CredentialStatusBadge.Background = new SolidColorBrush(Color.FromRgb(254, 242, 242));
        }
    }

    private void BrowseCredentials_Click(object sender, RoutedEventArgs e)
    {
        var dialog = new OpenFileDialog
        {
            Filter = "JSON Files|*.json|All Files|*.*",
            Title = "Select Google Cloud Service Account Key"
        };

        if (dialog.ShowDialog() == true)
        {
            // Copy to app data for persistence
            var destDir = AppConfig.DataDirectory;
            Directory.CreateDirectory(destDir);
            var destPath = Path.Combine(destDir, "google-credentials.json");
            File.Copy(dialog.FileName, destPath, overwrite: true);
            
            AppConfig.GoogleCredentialsPath = destPath;
            Environment.SetEnvironmentVariable("GOOGLE_APPLICATION_CREDENTIALS", destPath);
            UpdateCredentialStatus();
            MessageBox.Show("Google Cloud credentials configured.", "Success", MessageBoxButton.OK, MessageBoxImage.Information);
        }
    }

    private async void TestOcr_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            var credPath = AppConfig.GoogleCredentialsPath;
            if (string.IsNullOrEmpty(credPath) || !File.Exists(credPath))
            {
                MessageBox.Show("Please configure Google Cloud credentials first.", "Error", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            // Simple test: try to create the client
            var client = await Google.Cloud.Vision.V1.ImageAnnotatorClient.CreateAsync();
            MessageBox.Show("✓ Google Cloud Vision API is working!", "OCR Test", MessageBoxButton.OK, MessageBoxImage.Information);
        }
        catch (Exception ex)
        {
            MessageBox.Show($"OCR test failed:\n{ex.Message}", "OCR Test Failed", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    // ══════════════════════════════════════════════════
    // 8. GEMINI AI KEY
    // ══════════════════════════════════════════════════
    private void LoadGeminiKey()
    {
        TxtGeminiKey.Password = AppConfig.GeminiApiKey;
    }

    private void SaveGeminiKey_Click(object sender, RoutedEventArgs e)
    {
        var key = TxtGeminiKey.Password.Trim();
        if (string.IsNullOrWhiteSpace(key))
        {
            MessageBox.Show("Please enter an API key.", "Validation", MessageBoxButton.OK, MessageBoxImage.Warning);
            return;
        }

        try
        {
            AppConfig.GeminiApiKey = key;
            Environment.SetEnvironmentVariable("GEMINI_API_KEY", key);
            MessageBox.Show("Gemini API key saved.", "Success", MessageBoxButton.OK, MessageBoxImage.Information);
        }
        catch (Exception ex)
        {
            MessageBox.Show($"Failed to save key: {ex.Message}", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }
}
