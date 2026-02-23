using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Runtime.CompilerServices;

namespace OCRAdmissionForms.Core.Services;

public class BatchFileInfo : INotifyPropertyChanged
{
    private string _name = "";
    public string Name { get => _name; set { _name = value; OnPropertyChanged(); } }

    private string _path = "";
    public string Path { get => _path; set { _path = value; OnPropertyChanged(); } }

    private string _sizeText = "";
    public string SizeText { get => _sizeText; set { _sizeText = value; OnPropertyChanged(); } }

    private string _status = "Pending";
    public string Status { get => _status; set { _status = value; OnPropertyChanged(); } }

    public event PropertyChangedEventHandler? PropertyChanged;
    protected virtual void OnPropertyChanged([CallerMemberName] string? propertyName = null)
    {
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
    }
}

/// <summary>
/// Singleton service for managing batch upload state across the application.
/// Uses INotifyPropertyChanged to allow WPF bindings to react to state changes.
/// </summary>
public class BatchUploadService : INotifyPropertyChanged
{
    private static readonly Lazy<BatchUploadService> _instance = new(() => new BatchUploadService());
    public static BatchUploadService Instance => _instance.Value;

    private BatchUploadService() { }

    public ObservableCollection<BatchFileInfo> Files { get; } = new();

    private bool _isProcessing;
    public bool IsProcessing
    {
        get => _isProcessing;
        set { _isProcessing = value; OnPropertyChanged(); }
    }

    private string _currentFileName = "";
    public string CurrentFileName
    {
        get => _currentFileName;
        set { _currentFileName = value; OnPropertyChanged(); }
    }

    private double _progressPercentage;
    public double ProgressPercentage
    {
        get => _progressPercentage;
        set { _progressPercentage = value; OnPropertyChanged(); }
    }

    private int _processedCount;
    public int ProcessedCount
    {
        get => _processedCount;
        set { _processedCount = value; OnPropertyChanged(); OnPropertyChanged(nameof(ProgressText)); }
    }

    private int _totalCount;
    public int TotalCount
    {
        get => _totalCount;
        set { _totalCount = value; OnPropertyChanged(); OnPropertyChanged(nameof(ProgressText)); }
    }

    private int _successfulCount;
    public int SuccessfulCount
    {
        get => _successfulCount;
        set { _successfulCount = value; OnPropertyChanged(); }
    }

    private int _failedCount;
    public int FailedCount
    {
        get => _failedCount;
        set { _failedCount = value; OnPropertyChanged(); }
    }

    private string _statusMessage = "";
    public string StatusMessage
    {
        get => _statusMessage;
        set { _statusMessage = value; OnPropertyChanged(); }
    }

    public string ProgressText => $"{ProcessedCount} / {TotalCount} forms";

    /// <summary>
    /// Start a new batch upload job
    /// </summary>
    public void StartJob(int totalFiles)
    {
        IsProcessing = true;
        TotalCount = totalFiles;
        ProcessedCount = 0;
        SuccessfulCount = 0;
        FailedCount = 0;
        ProgressPercentage = 0;
        StatusMessage = "Starting batch upload...";
        CurrentFileName = "";
    }

    /// <summary>
    /// Update progress for the current file
    /// </summary>
    public void UpdateProgress(string fileName, bool success)
    {
        CurrentFileName = fileName;
        ProcessedCount++;
        
        if (success)
            SuccessfulCount++;
        else
            FailedCount++;

        ProgressPercentage = TotalCount > 0 ? (ProcessedCount * 100.0 / TotalCount) : 0;
        StatusMessage = $"Processing {fileName}...";
    }

    /// <summary>
    /// Complete the batch job
    /// </summary>
    public void CompleteJob()
    {
        IsProcessing = false;
        StatusMessage = $"Completed: {SuccessfulCount} successful, {FailedCount} failed";
        CurrentFileName = "";
    }

    /// <summary>
    /// Cancel the batch job
    /// </summary>
    public void CancelJob()
    {
        IsProcessing = false;
        StatusMessage = "Batch upload cancelled";
        CurrentFileName = "";
    }

    /// <summary>
    /// Reset the service state
    /// </summary>
    public void Reset()
    {
        IsProcessing = false;
        CurrentFileName = "";
        ProgressPercentage = 0;
        ProcessedCount = 0;
        TotalCount = 0;
        SuccessfulCount = 0;
        FailedCount = 0;
        StatusMessage = "";
    }

    public event PropertyChangedEventHandler? PropertyChanged;

    protected virtual void OnPropertyChanged([CallerMemberName] string? propertyName = null)
    {
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
    }
}
