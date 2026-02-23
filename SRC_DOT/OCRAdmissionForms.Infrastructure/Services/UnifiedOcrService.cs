using System;
using System.Threading.Tasks;
using System.Collections.Generic;
using System.Linq;
using OCRAdmissionForms.Core.Interfaces;

namespace OCRAdmissionForms.Infrastructure.Services;

/// <summary>
/// Unified OCR service that combines Google Vision (primary) with Tesseract (fallback)
/// for maximum accuracy on handwritten admission forms.
/// 
/// Strategy:
/// 1. Use Google Vision for primary OCR (best handwriting recognition)
/// 2. Fall back to Tesseract if Google Vision is unavailable
/// 3. Combine results from both for validation (optional ensemble mode)
/// </summary>
public class UnifiedOcrService : IOcrService
{
    private readonly GoogleVisionOcrService? _googleVision;
    private readonly TesseractOcrService _tesseract;
    private readonly bool _useEnsemble;

    public UnifiedOcrService(
        string? googleCredentialsPath = null, 
        string tessDataPath = "./tessdata",
        bool useEnsemble = false)
    {
        _tesseract = new TesseractOcrService(tessDataPath);
        _useEnsemble = useEnsemble;
        
        try
        {
            _googleVision = new GoogleVisionOcrService(googleCredentialsPath);
            if (!_googleVision.IsAvailable)
            {
                _googleVision = null;
            }
        }
        catch
        {
            _googleVision = null;
        }
    }

    public string ActiveProvider => _googleVision != null ? "google_vision" : "tesseract";

    /// <summary>
    /// Perform OCR using the best available provider
    /// </summary>
    public async Task<string> PerformOcrAsync(string imagePath)
    {
        // Try Google Vision first
        if (_googleVision != null)
        {
            try
            {
                return await _googleVision.PerformOcrAsync(imagePath);
            }
            catch
            {
                // Fall back to Tesseract
            }
        }
        
        return await _tesseract.PerformOcrAsync(imagePath);
    }

    /// <summary>
    /// Extract OCR results with best provider, optionally ensemble
    /// </summary>
    public async Task<OcrResult> ExtractAsync(string imagePath)
    {
        OcrResult? googleResult = null;
        OcrResult? tesseractResult = null;

        // Try Google Vision (primary)
        if (_googleVision != null)
        {
            try
            {
                googleResult = await _googleVision.ExtractAsync(imagePath);
            }
            catch
            {
                // Continue to fallback
            }
        }

        // If ensemble mode or Google Vision failed, also run Tesseract
        if (_useEnsemble || googleResult == null)
        {
            try
            {
                tesseractResult = await _tesseract.ExtractAsync(imagePath);
            }
            catch
            {
                // Continue
            }
        }

        // Return best result or combine
        if (googleResult != null && tesseractResult != null && _useEnsemble)
        {
            return CombineResults(googleResult, tesseractResult);
        }

        if (googleResult != null)
        {
            return googleResult;
        }

        if (tesseractResult != null)
        {
            return tesseractResult;
        }

        // Both failed
        return new OcrResult { RawText = "", Confidence = 0 };
    }

    /// <summary>
    /// Extract from bytes using best available provider
    /// </summary>
    public async Task<OcrResult> ExtractFromBytesAsync(byte[] imageData)
    {
        // Try Google Vision first
        if (_googleVision != null)
        {
            try
            {
                return await _googleVision.ExtractFromBytesAsync(imageData);
            }
            catch
            {
                // Fall back to Tesseract
            }
        }
        
        return await _tesseract.ExtractFromBytesAsync(imageData);
    }

    /// <summary>
    /// Combine results from Google Vision and Tesseract for validation
    /// Prefers Google Vision text but uses Tesseract for validation
    /// </summary>
    private static OcrResult CombineResults(OcrResult google, OcrResult tesseract)
    {
        var result = new OcrResult
        {
            // Prefer Google Vision text (better for handwriting)
            RawText = google.RawText,
            // Average confidence weighted towards Google Vision
            Confidence = (google.Confidence * 0.7f) + (tesseract.Confidence * 0.3f),
            Words = google.Words,
            Blocks = google.Blocks
        };

        // If Google text is short but Tesseract has more, cross-validate
        if (google.RawText.Length < tesseract.RawText.Length * 0.5)
        {
            // Tesseract may have caught more - use it
            result.RawText = tesseract.RawText;
            result.Words = tesseract.Words;
            result.Blocks = tesseract.Blocks;
        }

        // Merge unique words from both for better coverage
        var googleWords = new HashSet<string>(google.Words.Select(w => w.Text.ToLower()));
        foreach (var word in tesseract.Words)
        {
            if (!googleWords.Contains(word.Text.ToLower()))
            {
                result.Words.Add(word);
            }
        }

        return result;
    }
}
