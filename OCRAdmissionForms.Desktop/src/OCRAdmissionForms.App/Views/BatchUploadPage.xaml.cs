using System.Collections.ObjectModel;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using Microsoft.EntityFrameworkCore;
using Microsoft.Win32;
using OCRAdmissionForms.Core.Data;
using OCRAdmissionForms.Core.Entities;
using OCRAdmissionForms.Core.Services;

namespace OCRAdmissionForms.App.Views;

public partial class BatchUploadPage : Page
{
    public BatchUploadPage()
    {
        InitializeComponent();
        FilesList.ItemsSource = BatchUploadService.Instance.Files;
        
        // Restore UI state if already processing
        if (BatchUploadService.Instance.IsProcessing)
        {
            ProgressPanel.Visibility = Visibility.Visible;
            ProgressBar.Maximum = BatchUploadService.Instance.TotalCount;
            ProgressBar.Value = BatchUploadService.Instance.ProcessedCount;
            TxtProgressStatus.Text = BatchUploadService.Instance.StatusMessage;
            TxtProgressDetail.Text = BatchUploadService.Instance.ProgressText;
            BtnProcess.IsEnabled = false;
            BtnAddFiles.IsEnabled = false;
        }
        
        UpdateFileCount();
    }

    private void AddFiles_Click(object sender, RoutedEventArgs e)
    {
        var dialog = new OpenFileDialog
        {
            Filter = "PDF Files|*.pdf|Image Files|*.jpg;*.jpeg;*.png;*.tiff|All Files|*.*",
            Title = "Select Forms to Upload",
            Multiselect = true
        };

        if (dialog.ShowDialog() == true)
        {
            var files = BatchUploadService.Instance.Files;
            foreach (var file in dialog.FileNames)
            {
                if (!files.Any(f => f.Path == file))
                {
                    var info = new FileInfo(file);
                    files.Add(new BatchFileInfo
                    {
                        Name = info.Name,
                        Path = file,
                        SizeText = $"{info.Length / 1024.0:F1} KB",
                        Status = "Pending"
                    });
                }
            }
            UpdateFileCount();
        }
    }

    private void AddFolder_Click(object sender, RoutedEventArgs e)
    {
        var dialog = new OpenFolderDialog
        {
            Title = "Select Folder to Import Forms"
        };

        if (dialog.ShowDialog() == true)
        {
            var folderPath = dialog.FolderName;
            if (string.IsNullOrEmpty(folderPath)) return;
            
            var extensions = new[] { "*.pdf", "*.jpg", "*.jpeg", "*.png" };
            var allFiles = extensions
                .SelectMany(ext => Directory.GetFiles(folderPath, ext, SearchOption.AllDirectories))
                .ToList();
            
            int addedCount = 0;

            var files = BatchUploadService.Instance.Files;
            foreach (var file in allFiles)
            {
                if (!files.Any(f => f.Path == file))
                {
                    var info = new FileInfo(file);
                    files.Add(new BatchFileInfo
                    {
                        Name = info.Name,
                        Path = file,
                        SizeText = $"{info.Length / 1024.0:F1} KB",
                        Status = "Pending"
                    });
                    addedCount++;
                }
            }
            
            UpdateFileCount();
            if (addedCount > 0)
            {
                MessageBox.Show($"Added {addedCount} files from folder (including subfolders):\n{folderPath}", "Files Added", MessageBoxButton.OK, MessageBoxImage.Information);
            }
        }
    }

    private void RemoveFile_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button btn && btn.Tag is string path)
        {
            var files = BatchUploadService.Instance.Files;
            var file = files.FirstOrDefault(f => f.Path == path);
            if (file != null)
            {
                files.Remove(file);
                UpdateFileCount();
            }
        }
    }


    private void SelectAll_Click(object sender, RoutedEventArgs e)
    {
        FilesList.SelectAll();
    }

    private void DeselectAll_Click(object sender, RoutedEventArgs e)
    {
        FilesList.UnselectAll();
    }

    private void ClearAll_Click(object sender, RoutedEventArgs e)
    {
        BatchUploadService.Instance.Files.Clear();
        UpdateFileCount();
    }

    private void UpdateFileCount()
    {
        var total = BatchUploadService.Instance.Files.Count;
        TxtFileCount.Text = $"Selected Files ({total})";
        BtnProcess.IsEnabled = total > 0 && !BatchUploadService.Instance.IsProcessing;
        
        if (total > 0)
            TxtProcessButton.Text = $"Process {total} Form(s)";
        else
            TxtProcessButton.Text = "Process All";
    }

    private async void Process_Click(object sender, RoutedEventArgs e)
    {
        var files = BatchUploadService.Instance.Files;
        if (files.Count == 0) return;

        BtnProcess.IsEnabled = false;
        BtnAddFiles.IsEnabled = false;
        ProgressPanel.Visibility = Visibility.Visible;
        ProgressBar.Maximum = files.Count;
        ProgressBar.Value = 0;

        // Get selected provider
        var selectedProvider = "gemini";
        if (CmbProvider.SelectedItem is System.Windows.Controls.ComboBoxItem provItem)
            selectedProvider = provItem.Tag?.ToString() ?? "gemini";
        bool autoVerify = ChkAutoVerify.IsChecked == true;

        // Initialize global progress service
        BatchUploadService.Instance.StartJob(files.Count);

        var appData = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
        var uploadsDir = Path.Combine(appData, "SRCC Student DMS", "data", "uploads");
        var credentialsPath = AppConfig.GoogleCredentialsPath;
        Directory.CreateDirectory(uploadsDir);

        IOcrService? ocrService = null;
        if (!string.IsNullOrEmpty(credentialsPath) && File.Exists(credentialsPath))
        {
            try
            {
                ocrService = new GoogleVisionOcrService(credentialsPath);
            }
            catch { }
        }

        var extractor = new FormFieldExtractor();
        int successful = 0, failed = 0;

        for (int i = 0; i < files.Count; i++)
        {
            var file = files[i];
            
            // Update local UI in case user is looking at this page
            TxtProgressStatus.Text = $"Processing {file.Name}...";
            TxtProgressDetail.Text = $"{i + 1} of {files.Count}";
            ProgressBar.Value = i;

            bool fileSuccess = false;
            try
            {
                // Duplicate check - Filename
                var originalFileName = Path.GetFileName(file.Path);
                using var dbCheck = new AppDbContext();
                var exists = await dbCheck.AdmissionForms.AnyAsync(f => f.Filename.EndsWith("_" + originalFileName));
                if (exists)
                {
                    file.Status = "⚠ Skipped (Duplicate Filename)";
                    BatchUploadService.Instance.UpdateProgress(file.Name, false);
                    failed++;
                    continue;
                }

                // Copy file
                var destFileName = $"{DateTime.Now:yyyyMMdd_HHmmss}_{originalFileName}";
                var destPath = Path.Combine(uploadsDir, destFileName);
                File.Copy(file.Path, destPath, true);

                // Create form
                var form = new AdmissionForm
                {
                    Filename = destFileName,
                    FilePath = destPath,
                    OcrProvider = selectedProvider,
                    Status = FormStatus.Uploaded
                };

                // OCR if available
                if (ocrService != null)
                {
                    try
                    {
                        var ocrResult = await ocrService.ExtractTextAsync(destPath, selectedProvider);
                        
                        // Store full JSON with fields for Autofill (same as ReExtract)
                        var jsonResult = new Dictionary<string, object>
                        {
                            ["text"] = ocrResult.FullText,
                            ["fields"] = ocrResult.ExtractedFields ?? new Dictionary<string, string>(),
                            ["confidence"] = ocrResult.Confidence,
                            ["fields_count"] = ocrResult.ExtractedFields?.Count ?? 0
                        };
                        form.ExtractedDataJson = System.Text.Json.JsonSerializer.Serialize(jsonResult);
                        form.Status = FormStatus.Extracted;
                        
                        // Use pre-extracted fields from Python for accurate mapping
                        if (ocrResult.ExtractedFields != null && ocrResult.ExtractedFields.Count > 0)
                        {
                            form = extractor.ExtractFromPreExtracted(ocrResult.ExtractedFields, form);
                        }
                        else
                        {
                            form = extractor.ExtractFieldsFromJson(form.ExtractedDataJson, form);
                        }

                        // Auto-verify high-confidence forms
                        if (autoVerify && ocrResult.Confidence >= 85 &&
                            !string.IsNullOrWhiteSpace(form.StudentName) &&
                            !string.IsNullOrWhiteSpace(form.Course))
                        {
                            form.Status = FormStatus.Verified;
                            form.VerifiedDate = DateTime.UtcNow;
                            form.VerifiedBy = "Auto-Verify";
                        }

                        // Duplicate check - Serial Number (DuPortalFormNumber)
                        if (!string.IsNullOrWhiteSpace(form.DuPortalFormNumber))
                        {
                            var serialExists = await dbCheck.AdmissionForms
                                .AnyAsync(f => f.DuPortalFormNumber == form.DuPortalFormNumber && f.Id != form.Id);
                            if (serialExists)
                            {
                                file.Status = "⚠ Skipped (Duplicate Serial No)";
                                BatchUploadService.Instance.UpdateProgress(file.Name, false);
                                failed++;
                                // Delete the copied file since we are skipping
                                try { File.Delete(destPath); } catch { }
                                continue;
                            }
                        }
                    }
                    catch (Exception ocrEx)
                    {
                        // Log OCR error but continue — file is still saved with Uploaded status
                        System.Diagnostics.Debug.WriteLine($"[BatchUpload] OCR failed for {file.Name}: {ocrEx.Message}");
                        file.Status = "⚠ OCR failed, saved without extraction";
                    }
                }

                // Save
                using var db = new AppDbContext();
                db.AdmissionForms.Add(form);
                await db.SaveChangesAsync();

                // Create StudentProfile for verified forms
                if (form.Status == FormStatus.Verified)
                {
                    var studentName = form.StudentName
                        ?? $"{form.FirstName} {form.MiddleName} {form.Surname}".Trim().Replace("  ", " ");
                    var aadhar = form.AadharNumber?.Trim();
                    var rollNo = form.CollegeRollNo?.Trim();

                    StudentProfile? profile = null;
                    if (!string.IsNullOrWhiteSpace(aadhar))
                        profile = await db.StudentProfiles.FirstOrDefaultAsync(s => s.AadharNumber == aadhar);
                    if (profile == null && !string.IsNullOrWhiteSpace(rollNo))
                        profile = await db.StudentProfiles.FirstOrDefaultAsync(s => s.RollNumber == rollNo);
                    if (profile == null && !string.IsNullOrWhiteSpace(studentName))
                        profile = await db.StudentProfiles.FirstOrDefaultAsync(s => s.StudentName == studentName);

                    if (profile == null)
                    {
                        profile = new StudentProfile
                        {
                            StudentName = studentName ?? "Unknown",
                            AadharNumber = aadhar,
                            RollNumber = rollNo,
                            CreatedDate = DateTime.UtcNow,
                            UpdatedDate = DateTime.UtcNow,
                        };
                        db.StudentProfiles.Add(profile);
                        await db.SaveChangesAsync();
                    }
                    form.StudentProfileId = profile.Id;
                    await db.SaveChangesAsync();
                }

                file.Status = "✓ Done";
                successful++;
                fileSuccess = true;
            }
            catch (Exception ex)
            {
                file.Status = $"✗ Error: {ex.Message}";
                failed++;
            }

            // Update global progress
            BatchUploadService.Instance.UpdateProgress(file.Name, fileSuccess);
            ProgressBar.Value = i + 1;
        }

        TxtProgressStatus.Text = $"Completed: {successful} successful, {failed} failed";
        TxtProgressDetail.Text = "";
        BtnAddFiles.IsEnabled = true;
        BtnProcess.IsEnabled = false;

        // Complete the global progress tracking
        BatchUploadService.Instance.CompleteJob();

        MessageBox.Show($"Batch processing complete!\n\n{successful} forms processed successfully\n{failed} forms failed",
            "Complete", MessageBoxButton.OK, MessageBoxImage.Information);
    }
}
