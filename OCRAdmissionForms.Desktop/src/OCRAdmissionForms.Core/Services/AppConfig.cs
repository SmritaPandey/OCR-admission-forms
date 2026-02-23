using System;
using System.IO;
using System.Text.Json;

namespace OCRAdmissionForms.Core.Services;

/// <summary>
/// Persistent application configuration stored as JSON in %AppData%
/// </summary>
public static class AppConfig
{
    private static readonly string ConfigDir = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
        "SRCC Student DMS");

    private static readonly string ConfigFile = Path.Combine(ConfigDir, "config.json");

    private static ConfigData _data = new();

    // ── Accessors ───────────────────────────────────────────
    public static string DatabasePath
    {
        get => string.IsNullOrWhiteSpace(_data.DatabasePath)
            ? Path.Combine(ConfigDir, "data", "srcc_dms.db")
            : _data.DatabasePath;
        set { _data.DatabasePath = value; Save(); }
    }

    public static string DataDirectory =>
        Path.GetDirectoryName(DatabasePath)
        ?? Path.Combine(ConfigDir, "data");

    public static string SyncServerUrl
    {
        get => _data.SyncServerUrl ?? "";
        set { _data.SyncServerUrl = value; Save(); }
    }

    public static bool SyncEnabled
    {
        get => _data.SyncEnabled;
        set { _data.SyncEnabled = value; Save(); }
    }

    public static int AutoSyncIntervalMinutes
    {
        get => _data.AutoSyncIntervalMinutes > 0 ? _data.AutoSyncIntervalMinutes : 5;
        set { _data.AutoSyncIntervalMinutes = Math.Max(1, value); Save(); }
    }

    public static string GoogleCredentialsPath
    {
        get
        {
            if (!string.IsNullOrWhiteSpace(_data.GoogleCredentialsPath)) 
                return _data.GoogleCredentialsPath;
            
            // Default: check if bundled in app folder
            var bundled = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "google-credentials.json");
            if (File.Exists(bundled)) return bundled;
            
            return "";
        }
        set { _data.GoogleCredentialsPath = value; Save(); }
    }

    public static string GeminiApiKey
    {
        get => _data.GeminiApiKey ?? "";
        set { _data.GeminiApiKey = value; Save(); }
    }

    // ── Load / Save ─────────────────────────────────────────
    public static void Load()
    {
        try
        {
            Directory.CreateDirectory(ConfigDir);
            if (File.Exists(ConfigFile))
            {
                var json = File.ReadAllText(ConfigFile);
                _data = JsonSerializer.Deserialize<ConfigData>(json) ?? new ConfigData();
            }
        }
        catch
        {
            _data = new ConfigData();
        }
    }

    public static void Save()
    {
        try
        {
            Directory.CreateDirectory(ConfigDir);
            var json = JsonSerializer.Serialize(_data, new JsonSerializerOptions { WriteIndented = true });
            File.WriteAllText(ConfigFile, json);
        }
        catch
        {
            // Silently fail — file may be locked
        }
    }

    public static void ResetToDefaults()
    {
        _data = new ConfigData();
        Save();
    }

    // ── Internal DTO ────────────────────────────────────────
    private class ConfigData
    {
        public string? DatabasePath { get; set; }
        public string? SyncServerUrl { get; set; }
        public bool SyncEnabled { get; set; }
        public int AutoSyncIntervalMinutes { get; set; } = 5;
        public string? GoogleCredentialsPath { get; set; }
        public string? GeminiApiKey { get; set; }
    }
}
