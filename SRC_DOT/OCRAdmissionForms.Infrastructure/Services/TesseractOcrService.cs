using System;
using System.IO;
using System.Threading.Tasks;
using System.Collections.Generic;
using OCRAdmissionForms.Core.Interfaces;
using Tesseract;

namespace OCRAdmissionForms.Infrastructure.Services;

/// <summary>
/// OCR service using Tesseract engine with word-level extraction support.
/// Enhanced for SRCC form processing.
/// </summary>
public class TesseractOcrService : IOcrService
{
    private readonly string _tessDataPath;
    private readonly string _language;

    public TesseractOcrService(string tessDataPath = "./tessdata", string language = "eng")
    {
        _tessDataPath = tessDataPath;
        _language = language;
    }

    /// <summary>
    /// Perform OCR and return raw text
    /// </summary>
    public Task<string> PerformOcrAsync(string imagePath)
    {
        return Task.Run(() =>
        {
            using var engine = new TesseractEngine(_tessDataPath, _language, EngineMode.Default);
            using var img = Pix.LoadFromFile(imagePath);
            using var page = engine.Process(img);
            return page.GetText();
        });
    }

    /// <summary>
    /// Perform OCR with structured extraction including word-level bounding boxes
    /// </summary>
    public Task<OcrResult> ExtractAsync(string imagePath)
    {
        return Task.Run(() =>
        {
            using var engine = new TesseractEngine(_tessDataPath, _language, EngineMode.Default);
            using var img = Pix.LoadFromFile(imagePath);
            using var page = engine.Process(img);
            
            var result = new OcrResult
            {
                RawText = page.GetText(),
                Confidence = page.GetMeanConfidence()
            };

            // Extract word-level information with bounding boxes
            try
            {
                using var iter = page.GetIterator();
                iter.Begin();

                do
                {
                    // Get block-level text
                    if (iter.IsAtBeginningOf(PageIteratorLevel.Block))
                    {
                        var blockText = iter.GetText(PageIteratorLevel.Block);
                        if (!string.IsNullOrWhiteSpace(blockText))
                        {
                            Rect blockBounds;
                            if (iter.TryGetBoundingBox(PageIteratorLevel.Block, out blockBounds))
                            {
                                var block = new BlockInfo
                                {
                                    Text = blockText.Trim(),
                                    BoundingBox = new BoundingBox
                                    {
                                        X = blockBounds.X1,
                                        Y = blockBounds.Y1,
                                        Width = blockBounds.Width,
                                        Height = blockBounds.Height
                                    }
                                };
                                result.Blocks.Add(block);
                            }
                        }
                    }

                    // Get word-level text
                    var wordText = iter.GetText(PageIteratorLevel.Word);
                    if (!string.IsNullOrWhiteSpace(wordText))
                    {
                        Rect wordBounds;
                        if (iter.TryGetBoundingBox(PageIteratorLevel.Word, out wordBounds))
                        {
                            var word = new WordInfo
                            {
                                Text = wordText.Trim(),
                                Confidence = iter.GetConfidence(PageIteratorLevel.Word) / 100f,
                                BoundingBox = new BoundingBox
                                {
                                    X = wordBounds.X1,
                                    Y = wordBounds.Y1,
                                    Width = wordBounds.Width,
                                    Height = wordBounds.Height
                                }
                            };
                            result.Words.Add(word);
                        }
                    }
                } while (iter.Next(PageIteratorLevel.Word));
            }
            catch (Exception)
            {
                // If word-level extraction fails, we still have the raw text
            }

            return result;
        });
    }

    /// <summary>
    /// Perform OCR on a byte array image
    /// </summary>
    public Task<OcrResult> ExtractFromBytesAsync(byte[] imageData)
    {
        return Task.Run(() =>
        {
            using var engine = new TesseractEngine(_tessDataPath, _language, EngineMode.Default);
            using var img = Pix.LoadFromMemory(imageData);
            using var page = engine.Process(img);
            
            var result = new OcrResult
            {
                RawText = page.GetText(),
                Confidence = page.GetMeanConfidence()
            };

            // Extract words with bounding boxes
            try
            {
                using var iter = page.GetIterator();
                iter.Begin();

                do
                {
                    var wordText = iter.GetText(PageIteratorLevel.Word);
                    if (!string.IsNullOrWhiteSpace(wordText))
                    {
                        Rect wordBounds;
                        if (iter.TryGetBoundingBox(PageIteratorLevel.Word, out wordBounds))
                        {
                            var word = new WordInfo
                            {
                                Text = wordText.Trim(),
                                Confidence = iter.GetConfidence(PageIteratorLevel.Word) / 100f,
                                BoundingBox = new BoundingBox
                                {
                                    X = wordBounds.X1,
                                    Y = wordBounds.Y1,
                                    Width = wordBounds.Width,
                                    Height = wordBounds.Height
                                }
                            };
                            result.Words.Add(word);
                        }
                    }
                } while (iter.Next(PageIteratorLevel.Word));
            }
            catch (Exception)
            {
                // Continue with raw text if word extraction fails
            }

            return result;
        });
    }
}
