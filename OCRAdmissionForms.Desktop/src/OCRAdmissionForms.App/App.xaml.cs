using System.IO;
using System.Windows;
using Microsoft.EntityFrameworkCore;
using OCRAdmissionForms.Core.Data;
using OCRAdmissionForms.Core.Services;

namespace OCRAdmissionForms.App;

public partial class App : Application
{
    public static AuthService AuthService { get; } = new AuthService();
    public static SyncService SyncService { get; private set; } = null!;

    protected override async void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);

        // Global exception handlers
        AppDomain.CurrentDomain.UnhandledException += (s, args) =>
        {
            LogError("AppDomain", args.ExceptionObject as Exception);
        };
        
        DispatcherUnhandledException += (s, args) =>
        {
            LogError("Dispatcher", args.Exception);
            MessageBox.Show($"An error occurred:\n\n{args.Exception.Message}\n\nDetails logged to app_error.log", 
                "Error", MessageBoxButton.OK, MessageBoxImage.Error);
            args.Handled = true;
        };

        TaskScheduler.UnobservedTaskException += (s, args) =>
        {
            LogError("TaskScheduler", args.Exception);
            args.SetObserved();
        };

        try
        {
            // Load persistent config (DB path, sync settings)
            AppConfig.Load();

            // Initialize database
            using var db = new AppDbContext();
            db.MigrateDatabase();  // Creates tables and adds any new columns
            
            // Ensure default admin exists
            await AuthService.EnsureDefaultAdminAsync();
            
            // Initialize sync service with configured URL
            var syncUrl = AppConfig.SyncEnabled ? AppConfig.SyncServerUrl : null;
            SyncService = new SyncService(string.IsNullOrWhiteSpace(syncUrl) ? null : syncUrl);
            
            // Start auto-sync if enabled and URL is configured
            if (AppConfig.SyncEnabled && !string.IsNullOrWhiteSpace(AppConfig.SyncServerUrl))
            {
                SyncService.StartAutoSync(TimeSpan.FromMinutes(AppConfig.AutoSyncIntervalMinutes));
            }
            
            // Set environment variables for OCR and AI services from persistent config
            if (!string.IsNullOrEmpty(AppConfig.GoogleCredentialsPath))
            {
                Environment.SetEnvironmentVariable("GOOGLE_APPLICATION_CREDENTIALS", AppConfig.GoogleCredentialsPath);
            }
            
            if (!string.IsNullOrEmpty(AppConfig.GeminiApiKey))
            {
                Environment.SetEnvironmentVariable("GEMINI_API_KEY", AppConfig.GeminiApiKey);
            }
        }
        catch (Exception ex)
        {
            LogError("DatabaseInit", ex);
            MessageBox.Show($"Database initialization failed:\n\n{ex.Message}", 
                "Database Error", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    protected override void OnExit(ExitEventArgs e)
    {
        SyncService?.Dispose();
        base.OnExit(e);
    }

    private void LogError(string source, Exception? ex)
    {
        if (ex == null) return;
        
        var appData = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
        var logPath = Path.Combine(appData, "SRCC Student DMS", "app_error.log");
        Directory.CreateDirectory(Path.GetDirectoryName(logPath)!);
        
        var message = $"[{DateTime.Now:yyyy-MM-dd HH:mm:ss}] [{source}] {ex.GetType().Name}: {ex.Message}\n{ex.StackTrace}\n\n";
        File.AppendAllText(logPath, message);
    }
}

