using System.Collections.ObjectModel;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using Microsoft.Win32;
using OCRAdmissionForms.Core.Data;
using OCRAdmissionForms.Core.Entities;
using OCRAdmissionForms.Core.Services;

namespace OCRAdmissionForms.App.Views;

public class UploadFileInfo
{
    public string Name { get; set; } = "";
    public string Path { get; set; } = "";
    public string SizeText { get; set; } = "";
    public string Status { get; set; } = "Pending";
    public Brush StatusColor => Status switch
    {
        "✓ Done" => new SolidColorBrush(Color.FromRgb(16, 185, 129)),
        "Processing..." => new SolidColorBrush(Color.FromRgb(59, 130, 246)),
        "OCR..." => new SolidColorBrush(Color.FromRgb(234, 179, 8)),
        _ when Status.StartsWith("✗") => new SolidColorBrush(Color.FromRgb(239, 68, 68)),
        _ => new SolidColorBrush(Color.FromRgb(107, 114, 128))
    };
}

public partial class UploadPage : Page
{
    private readonly ObservableCollection<UploadFileInfo> _files = new();
    private bool _isProcessing = false;
    private readonly string _appDataPath;
    private readonly string _uploadsDir;
    private readonly string _credentialsPath;
    private readonly string _logPath;

    public UploadPage()
    {
        InitializeComponent();
        
        try
        {
            FilesList.ItemsSource = _files;

            var appData = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
            _appDataPath = System.IO.Path.Combine(appData, "SRCC Student DMS", "data");
            _uploadsDir = System.IO.Path.Combine(_appDataPath, "uploads");
            _credentialsPath = AppConfig.GoogleCredentialsPath;
            _logPath = System.IO.Path.Combine(_appDataPath, "app_error.log");
            
            Directory.CreateDirectory(_uploadsDir);
        }
        catch (Exception ex)
        {
            LogError("Init", ex);
            MessageBox.Show($"Failed to initialize: {ex.Message}", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    private void Page_DragOver(object sender, DragEventArgs e)
    {
        try
        {
            e.Effects = e.Data.GetDataPresent(DataFormats.FileDrop) ? DragDropEffects.Copy : DragDropEffects.None;
            e.Handled = true;
        }
        catch (Exception ex)
        {
            LogError("DragOver", ex);
        }
    }

    private void Page_Drop(object sender, DragEventArgs e)
    {
        try
        {
            if (e.Data.GetDataPresent(DataFormats.FileDrop))
            {
                var files = (string[])e.Data.GetData(DataFormats.FileDrop);
                if (files != null && files.Length > 0)
                {
                    AddFiles(files);
                }
            }
        }
        catch (Exception ex)
        {
            LogError("Drop", ex);
            MessageBox.Show($"Failed to add dropped files: {ex.Message}", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    private void DropZone_Click(object sender, System.Windows.Input.MouseButtonEventArgs e)
    {
        try
        {
            var dialog = new OpenFileDialog
            {
                Filter = "All Supported|*.jpg;*.jpeg;*.png;*.pdf;*.tiff;*.bmp|Images|*.jpg;*.jpeg;*.png;*.tiff;*.bmp|PDF|*.pdf",
                Title = "Select Form(s) for ONE Student",
                Multiselect = true
            };

            if (dialog.ShowDialog() == true)
            {
                AddFiles(dialog.FileNames);
            }
        }
        catch (Exception ex)
        {
            LogError("FileDialog", ex);
            MessageBox.Show($"Failed to open file dialog: {ex.Message}", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    private void AddFiles(string[] files)
    {
        if (files == null) return;
        
        var allowedExts = new[] { ".jpg", ".jpeg", ".png", ".pdf", ".tiff", ".bmp" };

        foreach (var file in files)
        {
            try
            {
                if (string.IsNullOrEmpty(file)) continue;
                
                var ext = System.IO.Path.GetExtension(file)?.ToLower() ?? "";
                if (!allowedExts.Contains(ext)) continue;
                if (_files.Any(f => f.Path == file)) continue;

                var info = new FileInfo(file);
                if (!info.Exists) continue;
                
                _files.Add(new UploadFileInfo
                {
                    Name = info.Name,
                    Path = file,
                    SizeText = $"{info.Length / 1024.0:F1} KB",
                    Status = "Pending"
                });
            }
            catch (Exception ex)
            {
                LogError($"AddFile:{file}", ex);
            }
        }
        UpdateUI();
    }

    private void RemoveFile_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            if (sender is Button btn && btn.Tag is string path)
            {
                var file = _files.FirstOrDefault(f => f.Path == path);
                if (file != null)
                {
                    _files.Remove(file);
                    UpdateUI();
                }
            }
        }
        catch (Exception ex)
        {
            LogError("RemoveFile", ex);
        }
    }

    private void ClearAll_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            _files.Clear();
            UpdateUI();
        }
        catch (Exception ex)
        {
            LogError("ClearAll", ex);
        }
    }

    private void UpdateUI()
    {
        try
        {
            TxtFileCount.Text = $"Files for Student ({_files.Count})";
            BtnUpload.IsEnabled = _files.Count > 0 && !_isProcessing;
            TxtUploadButton.Text = _files.Count > 1 ? $"Upload & Process ({_files.Count} files)" : "Upload & Process";
        }
        catch (Exception ex)
        {
            LogError("UpdateUI", ex);
        }
    }

    private async void Upload_Click(object sender, RoutedEventArgs e)
    {
        if (_files.Count == 0) return;

        _isProcessing = true;
        BtnUpload.IsEnabled = false;
        
        try
        {
            ProgressPanel.Visibility = Visibility.Visible;
            ProgressBar.Maximum = _files.Count;
            ProgressBar.Value = 0;
        }
        catch (Exception ex)
        {
            LogError("ProgressInit", ex);
        }

        // Check credentials and initialize OCR
        IOcrService? ocrService = null;
        bool hasCredentials = false;
        
        try
        {
            hasCredentials = File.Exists(_credentialsPath);
            if (hasCredentials)
            {
                try 
                { 
                    ocrService = new GoogleVisionOcrService(_credentialsPath);
                } 
                catch (Exception ex) 
                { 
                    LogError("OCR Init", ex);
                    MessageBox.Show(
                        $"OCR initialization failed:\n\n{ex.Message}\n\nForms will be saved without OCR extraction.\n\nCheck that your Google Cloud credentials are valid.", 
                        "OCR Warning", MessageBoxButton.OK, MessageBoxImage.Warning);
                }
            }
            else
            {
                MessageBox.Show(
                    "Google Cloud credentials not configured.\n\nGo to Settings → Google Cloud Vision API to configure.\n\nForms will be saved without OCR extraction.", 
                    "No Credentials", MessageBoxButton.OK, MessageBoxImage.Warning);
            }
        }
        catch (Exception ex)
        {
            LogError("CredentialsCheck", ex);
        }

        var extractor = new FormFieldExtractor();
        int successful = 0, failed = 0;
        string lastError = "";

        // Create a single student profile for all files uploaded together
        StudentProfile? studentProfile = null;
        AdmissionForm? primaryForm = null;

        for (int i = 0; i < _files.Count; i++)
        {
            var file = _files[i];
            
            try
            {
                file.Status = "Processing...";
                FilesList.Items.Refresh();

                TxtProgressStatus.Text = $"Processing {file.Name}...";
                TxtProgressDetail.Text = $"{i + 1} of {_files.Count}";
            }
            catch (Exception ex)
            {
                LogError("UpdateProgress", ex);
            }

            try
            {
                // Validate source file
                if (!File.Exists(file.Path))
                {
                    throw new FileNotFoundException($"Source file not found: {file.Path}");
                }

                // Copy file to uploads directory
                var timestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
                var safeFileName = SanitizeFileName(System.IO.Path.GetFileName(file.Path));
                var destFileName = $"{timestamp}_{i}_{safeFileName}";
                var destPath = System.IO.Path.Combine(_uploadsDir, destFileName);
                
                File.Copy(file.Path, destPath, true);
                
                if (!File.Exists(destPath))
                {
                    throw new IOException($"Failed to copy file to: {destPath}");
                }

                // Create admission form record
                var form = new AdmissionForm
                {
                    Filename = destFileName,
                    FilePath = destPath,
                    OcrProvider = ocrService != null ? "google-vision" : "none",
                    Status = FormStatus.Uploaded,
                    UploadDate = DateTime.UtcNow
                };

                // Run OCR and extract fields
                if (ocrService != null)
                {
                    try
                    {
                        file.Status = "OCR...";
                        FilesList.Items.Refresh();
                        TxtProgressStatus.Text = $"Extracting text from {file.Name}...";
                        
                        var ocrResult = await ocrService.ExtractTextAsync(destPath);
                        
                        if (!string.IsNullOrEmpty(ocrResult.Error))
                        {
                            LogError("OCR", new Exception(ocrResult.Error));
                            System.Diagnostics.Debug.WriteLine($"OCR error for {file.Name}: {ocrResult.Error}");
                        }
                        else if (!string.IsNullOrEmpty(ocrResult.FullText))
                        {
                            // Store raw OCR text
                            form.ExtractedDataJson = ocrResult.FullText;
                            form.Status = FormStatus.Extracted;

                            // Extract fields using pattern matching
                            TxtProgressStatus.Text = $"Extracting fields from {file.Name}...";
                            form = extractor.ExtractFields(ocrResult.FullText, form);
                            
                            System.Diagnostics.Debug.WriteLine($"Extracted from {file.Name}: Name={form.StudentName}, Roll={form.CollegeRollNo}");

                            // Create student profile from first successful extraction
                            if (studentProfile == null && !string.IsNullOrWhiteSpace(form.StudentName))
                            {
                                try
                                {
                                    studentProfile = new StudentProfile
                                    {
                                        StudentName = form.StudentName?.Trim() ?? "Unknown Student",
                                        AadharNumber = form.AadharNumber?.Trim(),
                                        RollNumber = form.CollegeRollNo?.Trim(),
                                        CreatedDate = DateTime.UtcNow
                                    };
                                    
                                    using var profileDb = new AppDbContext();
                                    profileDb.StudentProfiles.Add(studentProfile);
                                    await profileDb.SaveChangesAsync();
                                    
                                    System.Diagnostics.Debug.WriteLine($"Created student profile: {studentProfile.StudentName} (ID: {studentProfile.Id})");
                                }
                                catch (Exception profileEx)
                                {
                                    LogError("CreateProfile", profileEx);
                                    studentProfile = null; // Reset so we don't link broken profile
                                }
                            }

                            if (primaryForm == null)
                                primaryForm = form;
                        }
                        else
                        {
                            LogError("OCR", new Exception("OCR returned empty text"));
                        }
                    }
                    catch (Exception ocrEx)
                    {
                        LogError("OCR Extraction", ocrEx);
                        System.Diagnostics.Debug.WriteLine($"OCR exception for {file.Name}: {ocrEx.Message}");
                    }
                }

                // Link form to student profile if we have one
                if (studentProfile != null && studentProfile.Id > 0)
                {
                    form.StudentProfileId = studentProfile.Id;
                }

                // Save form to database
                try
                {
                    using var db = new AppDbContext();
                    db.AdmissionForms.Add(form);
                    await db.SaveChangesAsync();
                    
                    System.Diagnostics.Debug.WriteLine($"Saved form: {form.Filename} (ID: {form.Id})");
                    
                    if (primaryForm == null || primaryForm.Id == 0)
                        primaryForm = form;
                }
                catch (Exception dbEx)
                {
                    LogError("SaveForm", dbEx);
                    throw new Exception($"Database save failed: {dbEx.Message}");
                }

                file.Status = "✓ Done";
                successful++;
            }
            catch (Exception ex)
            {
                file.Status = $"✗ Error";
                lastError = ex.Message;
                failed++;
                LogError($"ProcessFile:{file.Name}", ex);
            }

            try
            {
                ProgressBar.Value = i + 1;
                FilesList.Items.Refresh();
            }
            catch (Exception ex)
            {
                LogError("UpdateProgress2", ex);
            }
        }

        // Completion
        try
        {
            TxtProgressStatus.Text = $"Complete: {successful} successful, {failed} failed";
            TxtProgressDetail.Text = "";
            _isProcessing = false;
            ProgressPanel.Visibility = Visibility.Collapsed;
            BtnUpload.IsEnabled = true;
        }
        catch (Exception ex)
        {
            LogError("Completion", ex);
        }

        // Show results
        try
        {
            var studentName = studentProfile?.StudentName ?? "Unknown";
            if (failed > 0 && !string.IsNullOrEmpty(lastError))
            {
                MessageBox.Show(
                    $"Upload complete with errors!\n\nStudent: {studentName}\n{successful} forms processed\n{failed} forms failed\n\nLast error: {lastError}\n\nCheck app_error.log for details.",
                    "Complete with Errors", MessageBoxButton.OK, MessageBoxImage.Warning);
            }
            else
            {
                var ocrStatus = ocrService != null ? "OCR extraction completed." : "No OCR - forms saved for manual entry.";
                MessageBox.Show(
                    $"Upload complete!\n\nStudent: {studentName}\n{successful} form(s) processed\n\n{ocrStatus}\n\nYou can now view and verify the extracted data.",
                    "Complete", MessageBoxButton.OK, MessageBoxImage.Information);
            }
        }
        catch (Exception ex)
        {
            LogError("ShowResults", ex);
        }

        // Clear files and navigate
        try
        {
            _files.Clear();
            UpdateUI();

            if (primaryForm != null && primaryForm.Id > 0 && Window.GetWindow(this) is MainWindow mainWindow)
            {
                mainWindow.ContentFrame.Navigate(new FormDetailPage(primaryForm.Id));
            }
            else if (successful > 0 && Window.GetWindow(this) is MainWindow mw)
            {
                mw.ContentFrame.Navigate(new FormsPage());
            }
        }
        catch (Exception ex)
        {
            LogError("Navigate", ex);
        }
    }

    private string SanitizeFileName(string fileName)
    {
        if (string.IsNullOrEmpty(fileName)) return "file";
        
        var invalid = System.IO.Path.GetInvalidFileNameChars();
        var sanitized = new string(fileName.Where(c => !invalid.Contains(c)).ToArray());
        return string.IsNullOrEmpty(sanitized) ? "file" : sanitized;
    }

    private void LogError(string context, Exception ex)
    {
        try
        {
            var logEntry = $"[{DateTime.Now:yyyy-MM-dd HH:mm:ss}] [{context}] {ex.GetType().Name}: {ex.Message}\n   {ex.StackTrace?.Split('\n').FirstOrDefault()}\n";
            File.AppendAllText(_logPath, logEntry);
            System.Diagnostics.Debug.WriteLine(logEntry);
        }
        catch 
        {
            System.Diagnostics.Debug.WriteLine($"[{context}] {ex.Message}");
        }
    }
}
