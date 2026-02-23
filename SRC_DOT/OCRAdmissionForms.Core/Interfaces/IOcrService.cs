using System.Collections.Generic;
using System.Threading.Tasks;

namespace OCRAdmissionForms.Core.Interfaces;

/// <summary>
/// Service interface for performing OCR on images
/// </summary>
public interface IOcrService
{
    /// <summary>
    /// Perform OCR and return raw text
    /// </summary>
    Task<string> PerformOcrAsync(string imagePath);
    
    /// <summary>
    /// Perform OCR and return structured extraction result
    /// </summary>
    Task<OcrResult> ExtractAsync(string imagePath);
    
    /// <summary>
    /// Perform OCR on a byte array image
    /// </summary>
    Task<OcrResult> ExtractFromBytesAsync(byte[] imageData);
}

/// <summary>
/// Service interface for extracting structured form fields from OCR text
/// </summary>
public interface IFormExtractorService
{
    /// <summary>
    /// Extract all form fields from raw OCR text
    /// </summary>
    ExtractionResult Extract(string rawText);
    
    /// <summary>
    /// Extract fields from a specific page of the form
    /// </summary>
    ExtractionResult ExtractFromPage(string rawText, int pageNumber);
    
    /// <summary>
    /// Get field confidence score
    /// </summary>
    float GetFieldConfidence(string fieldName, string? value);
}

/// <summary>
/// Result of OCR processing
/// </summary>
public class OcrResult
{
    public string RawText { get; set; } = string.Empty;
    public float Confidence { get; set; }
    public List<WordInfo> Words { get; set; } = new();
    public List<BlockInfo> Blocks { get; set; } = new();
}

/// <summary>
/// Word-level OCR information with bounding box
/// </summary>
public class WordInfo
{
    public string Text { get; set; } = string.Empty;
    public float Confidence { get; set; }
    public BoundingBox? BoundingBox { get; set; }
}

/// <summary>
/// Block-level OCR information
/// </summary>
public class BlockInfo
{
    public string Text { get; set; } = string.Empty;
    public float Confidence { get; set; }
    public BoundingBox? BoundingBox { get; set; }
    public List<WordInfo> Words { get; set; } = new();
}

/// <summary>
/// Bounding box coordinates
/// </summary>
public class BoundingBox
{
    public int X { get; set; }
    public int Y { get; set; }
    public int Width { get; set; }
    public int Height { get; set; }
    
    public int CenterX => X + Width / 2;
    public int CenterY => Y + Height / 2;
}

/// <summary>
/// Result of form field extraction
/// </summary>
public class ExtractionResult
{
    public Dictionary<string, string?> Fields { get; set; } = new();
    public Dictionary<string, float> FieldConfidences { get; set; } = new();
    public float OverallConfidence { get; set; }
    public string Provider { get; set; } = "srcc_extractor";
    public ExtractionMetadata? Metadata { get; set; }
}

/// <summary>
/// Extraction metadata
/// </summary>
public class ExtractionMetadata
{
    public bool ZoneAware { get; set; }
    public List<string> ZonesUsed { get; set; } = new();
    public int FieldsFromZones { get; set; }
}
