using System;
using System.IO;
using System.Reflection;
using System.Text.Json;
using System.Text.Json.Serialization;
using OCRAdmissionForms.Core.Entities;

namespace OCRAdmissionForms.Core.Services;

/// <summary>
/// Stores verified form data (image + labels) for OCR model training.
/// Each verified form produces:
///   - A copy of the original PDF/image in training_data/images/
///   - A JSON label file in training_data/labels/
///   - An entry in training_data/manifest.json
/// </summary>
public static class TrainingDataService
{
    private static readonly string TrainingDir = Path.Combine(
        AppDomain.CurrentDomain.BaseDirectory, "training_data");

    private static readonly string ImagesDir = Path.Combine(TrainingDir, "images");
    private static readonly string LabelsDir = Path.Combine(TrainingDir, "labels");
    private static readonly string ManifestPath = Path.Combine(TrainingDir, "manifest.json");

    private static readonly JsonSerializerOptions JsonOpts = new()
    {
        WriteIndented = true,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull
    };

    /// <summary>
    /// Save a verified form's image + all field values as labeled training data.
    /// </summary>
    public static void SaveVerifiedForm(AdmissionForm form)
    {
        try
        {
            Directory.CreateDirectory(ImagesDir);
            Directory.CreateDirectory(LabelsDir);

            // 1. Copy source image/PDF
            string? imageRelPath = null;
            if (!string.IsNullOrWhiteSpace(form.FilePath) && File.Exists(form.FilePath))
            {
                var ext = Path.GetExtension(form.FilePath);
                var destName = $"form_{form.Id}{ext}";
                var destPath = Path.Combine(ImagesDir, destName);
                File.Copy(form.FilePath, destPath, overwrite: true);
                imageRelPath = $"images/{destName}";
            }

            // 2. Extract all string fields from the form entity
            var fields = new Dictionary<string, string>();
            foreach (var prop in typeof(AdmissionForm).GetProperties(BindingFlags.Public | BindingFlags.Instance))
            {
                // Skip navigation/meta properties
                if (prop.Name is "Id" or "StudentProfileId" or "StudentProfile"
                    or "ExtractedDataJson" or "FilePath" or "Filename"
                    or "SyncStatus" or "SyncId" or "ServerId" or "LastModifiedUtc"
                    or "SyncedUtc" or "Documents" or "OcrProvider")
                    continue;

                var val = prop.GetValue(form);
                if (val is string s && !string.IsNullOrWhiteSpace(s))
                    fields[prop.Name] = s;
                else if (val is DateTime dt)
                    fields[prop.Name] = dt.ToString("o");
                else if (val is Enum e)
                    fields[prop.Name] = e.ToString();
            }

            // 3. Write label JSON
            var label = new
            {
                form_id = form.Id,
                image_path = imageRelPath,
                verified_by = form.VerifiedBy ?? Environment.UserName,
                verified_at = form.VerifiedDate?.ToString("o") ?? DateTime.UtcNow.ToString("o"),
                field_count = fields.Count,
                fields
            };

            var labelPath = Path.Combine(LabelsDir, $"form_{form.Id}.json");
            File.WriteAllText(labelPath, JsonSerializer.Serialize(label, JsonOpts));

            // 4. Append to manifest
            AppendToManifest(form.Id, imageRelPath, fields.Count);

            System.Diagnostics.Debug.WriteLine(
                $"[TrainingData] Saved verified form {form.Id}: {fields.Count} fields, image={imageRelPath ?? "N/A"}");
        }
        catch (Exception ex)
        {
            // Training data is best-effort — don't break the verification flow
            System.Diagnostics.Debug.WriteLine(
                $"[TrainingData] Error saving form {form.Id}: {ex.Message}");
        }
    }

    private static void AppendToManifest(int formId, string? imagePath, int fieldCount)
    {
        List<ManifestEntry> entries;

        if (File.Exists(ManifestPath))
        {
            try
            {
                var json = File.ReadAllText(ManifestPath);
                entries = JsonSerializer.Deserialize<List<ManifestEntry>>(json) ?? new();
            }
            catch
            {
                entries = new();
            }
        }
        else
        {
            entries = new();
        }

        // Remove existing entry for this form (re-verification)
        entries.RemoveAll(e => e.FormId == formId);

        entries.Add(new ManifestEntry
        {
            FormId = formId,
            ImagePath = imagePath,
            LabelPath = $"labels/form_{formId}.json",
            FieldCount = fieldCount,
            VerifiedAt = DateTime.UtcNow.ToString("o")
        });

        File.WriteAllText(ManifestPath, JsonSerializer.Serialize(entries, JsonOpts));
    }

    private class ManifestEntry
    {
        [JsonPropertyName("form_id")]
        public int FormId { get; set; }

        [JsonPropertyName("image_path")]
        public string? ImagePath { get; set; }

        [JsonPropertyName("label_path")]
        public string? LabelPath { get; set; }

        [JsonPropertyName("field_count")]
        public int FieldCount { get; set; }

        [JsonPropertyName("verified_at")]
        public string? VerifiedAt { get; set; }
    }
}
