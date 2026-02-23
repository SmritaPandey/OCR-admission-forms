using System;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using System.Collections.Generic;
using Google.Cloud.Vision.V1;
using OCRAdmissionForms.Core.Interfaces;

namespace OCRAdmissionForms.Infrastructure.Services;

/// <summary>
/// Google Cloud Vision OCR service for superior handwriting recognition.
/// Combines document text detection with word-level bounding box extraction.
/// </summary>
public class GoogleVisionOcrService : IOcrService
{
    private readonly ImageAnnotatorClient? _client;
    private readonly string? _credentialsPath;

    public GoogleVisionOcrService(string? credentialsPath = null)
    {
        _credentialsPath = credentialsPath;
        
        try
        {
            // Initialize Google Vision client
            if (!string.IsNullOrEmpty(credentialsPath) && File.Exists(credentialsPath))
            {
                Environment.SetEnvironmentVariable("GOOGLE_APPLICATION_CREDENTIALS", credentialsPath);
            }
            
            _client = ImageAnnotatorClient.Create();
        }
        catch (Exception)
        {
            // If Google Vision is not configured, we'll fallback to null
            _client = null;
        }
    }

    public bool IsAvailable => _client != null;

    /// <summary>
    /// Perform OCR and return raw text using Google Vision's document text detection
    /// </summary>
    public async Task<string> PerformOcrAsync(string imagePath)
    {
        if (_client == null)
        {
            throw new InvalidOperationException("Google Vision client not initialized. Check credentials.");
        }

        var image = await Image.FromFileAsync(imagePath);
        
        // Use document text detection for better handwriting recognition
        var response = await _client.DetectDocumentTextAsync(image);
        
        return response?.Text ?? string.Empty;
    }

    /// <summary>
    /// Perform OCR with full structured extraction including word-level bounding boxes
    /// </summary>
    public async Task<OcrResult> ExtractAsync(string imagePath)
    {
        if (_client == null)
        {
            throw new InvalidOperationException("Google Vision client not initialized. Check credentials.");
        }

        var image = await Image.FromFileAsync(imagePath);
        
        // Use document text detection for best handwriting results
        var response = await _client.DetectDocumentTextAsync(image);
        
        var result = new OcrResult
        {
            RawText = response?.Text ?? string.Empty,
            Confidence = 0.9f // Google Vision typically high confidence
        };

        if (response?.Pages != null)
        {
            foreach (var page in response.Pages)
            {
                // Set overall confidence from page
                if (page.Confidence > 0)
                {
                    result.Confidence = page.Confidence;
                }

                foreach (var block in page.Blocks)
                {
                    var blockText = GetBlockText(block);
                    var blockBounds = GetBoundingBox(block.BoundingBox);
                    
                    var blockInfo = new BlockInfo
                    {
                        Text = blockText,
                        BoundingBox = blockBounds,
                        Confidence = block.Confidence
                    };
                    
                    // Extract words from paragraphs
                    foreach (var paragraph in block.Paragraphs)
                    {
                        foreach (var word in paragraph.Words)
                        {
                            var wordText = string.Join("", word.Symbols.Select(s => s.Text));
                            var wordBounds = GetBoundingBox(word.BoundingBox);
                            
                            var wordInfo = new WordInfo
                            {
                                Text = wordText,
                                Confidence = word.Confidence,
                                BoundingBox = wordBounds
                            };
                            
                            result.Words.Add(wordInfo);
                            blockInfo.Words.Add(wordInfo);
                        }
                    }
                    
                    result.Blocks.Add(blockInfo);
                }
            }
        }

        return result;
    }

    /// <summary>
    /// Perform OCR on a byte array image
    /// </summary>
    public async Task<OcrResult> ExtractFromBytesAsync(byte[] imageData)
    {
        if (_client == null)
        {
            throw new InvalidOperationException("Google Vision client not initialized. Check credentials.");
        }

        var image = Image.FromBytes(imageData);
        
        var response = await _client.DetectDocumentTextAsync(image);
        
        var result = new OcrResult
        {
            RawText = response?.Text ?? string.Empty,
            Confidence = 0.9f
        };

        if (response?.Pages != null)
        {
            foreach (var page in response.Pages)
            {
                if (page.Confidence > 0)
                {
                    result.Confidence = page.Confidence;
                }

                foreach (var block in page.Blocks)
                {
                    foreach (var paragraph in block.Paragraphs)
                    {
                        foreach (var word in paragraph.Words)
                        {
                            var wordText = string.Join("", word.Symbols.Select(s => s.Text));
                            var wordBounds = GetBoundingBox(word.BoundingBox);
                            
                            result.Words.Add(new WordInfo
                            {
                                Text = wordText,
                                Confidence = word.Confidence,
                                BoundingBox = wordBounds
                            });
                        }
                    }
                }
            }
        }

        return result;
    }

    #region Helpers

    private static string GetBlockText(Block block)
    {
        var paragraphs = block.Paragraphs.Select(p =>
            string.Join(" ", p.Words.Select(w =>
                string.Join("", w.Symbols.Select(s => s.Text))
            ))
        );
        return string.Join("\n", paragraphs);
    }

    private static BoundingBox? GetBoundingBox(BoundingPoly? poly)
    {
        if (poly?.Vertices == null || poly.Vertices.Count < 4)
            return null;

        var vertices = poly.Vertices;
        int minX = vertices.Min(v => v.X);
        int minY = vertices.Min(v => v.Y);
        int maxX = vertices.Max(v => v.X);
        int maxY = vertices.Max(v => v.Y);

        return new BoundingBox
        {
            X = minX,
            Y = minY,
            Width = maxX - minX,
            Height = maxY - minY
        };
    }

    #endregion
}
