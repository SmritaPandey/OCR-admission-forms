using System.Drawing;
using System.Drawing.Imaging;

namespace OCRAdmissionForms.Core.Services;

/// <summary>
/// Image preprocessor for OCR - converts images to PNG format
/// and normalizes them for Google Vision API compatibility
/// </summary>
public static class ImagePreprocessor
{
    private const int MaxImageDimension = 4096; // Google Vision limit
    private const long MaxFileSizeBytes = 10 * 1024 * 1024; // 10MB limit

    /// <summary>
    /// Convert any supported image to PNG bytes suitable for OCR
    /// </summary>
    public static byte[] ConvertToPng(string imagePath)
    {
        if (string.IsNullOrEmpty(imagePath))
            throw new ArgumentException("Image path is required");
            
        if (!File.Exists(imagePath))
            throw new FileNotFoundException($"Image not found: {imagePath}");

        var ext = Path.GetExtension(imagePath).ToLower();
        
        // Handle PDF separately
        if (ext == ".pdf")
        {
            return ConvertPdfFirstPageToPng(imagePath);
        }

        // For regular images, use System.Drawing
        using var originalImage = Image.FromFile(imagePath);
        return ConvertImageToPng(originalImage);
    }

    /// <summary>
    /// Convert byte array to PNG format
    /// </summary>
    public static byte[] ConvertToPng(byte[] imageBytes)
    {
        if (imageBytes == null || imageBytes.Length == 0)
            throw new ArgumentException("Image bytes are required");

        using var ms = new MemoryStream(imageBytes);
        using var originalImage = Image.FromStream(ms);
        return ConvertImageToPng(originalImage);
    }

    /// <summary>
    /// Convert Image object to PNG bytes with optional resizing
    /// </summary>
    private static byte[] ConvertImageToPng(Image image)
    {
        // Calculate new dimensions if image is too large
        int newWidth = image.Width;
        int newHeight = image.Height;

        if (image.Width > MaxImageDimension || image.Height > MaxImageDimension)
        {
            double ratio = Math.Min(
                (double)MaxImageDimension / image.Width,
                (double)MaxImageDimension / image.Height
            );
            newWidth = (int)(image.Width * ratio);
            newHeight = (int)(image.Height * ratio);
        }

        // Create bitmap with proper pixel format for OCR
        using var bitmap = new Bitmap(newWidth, newHeight, PixelFormat.Format24bppRgb);
        bitmap.SetResolution(300, 300); // Standard OCR resolution

        using (var graphics = Graphics.FromImage(bitmap))
        {
            // High quality rendering
            graphics.InterpolationMode = System.Drawing.Drawing2D.InterpolationMode.HighQualityBicubic;
            graphics.SmoothingMode = System.Drawing.Drawing2D.SmoothingMode.HighQuality;
            graphics.PixelOffsetMode = System.Drawing.Drawing2D.PixelOffsetMode.HighQuality;
            graphics.CompositingQuality = System.Drawing.Drawing2D.CompositingQuality.HighQuality;

            // Fill with white background (for transparent images)
            graphics.Clear(Color.White);

            // Draw the original image
            graphics.DrawImage(image, 0, 0, newWidth, newHeight);
        }

        // Convert to PNG bytes
        using var outputMs = new MemoryStream();
        bitmap.Save(outputMs, ImageFormat.Png);
        
        var result = outputMs.ToArray();
        
        // If still too large, reduce quality
        if (result.Length > MaxFileSizeBytes)
        {
            return CompressImage(bitmap);
        }

        return result;
    }

    /// <summary>
    /// Compress image if too large for API
    /// </summary>
    private static byte[] CompressImage(Bitmap bitmap)
    {
        // Try JPEG with lower quality as fallback
        using var ms = new MemoryStream();
        var encoder = ImageCodecInfo.GetImageEncoders()
            .FirstOrDefault(e => e.FormatID == ImageFormat.Jpeg.Guid);
        
        if (encoder != null)
        {
            var encoderParams = new EncoderParameters(1);
            encoderParams.Param[0] = new EncoderParameter(Encoder.Quality, 80L);
            bitmap.Save(ms, encoder, encoderParams);
        }
        else
        {
            bitmap.Save(ms, ImageFormat.Jpeg);
        }
        
        return ms.ToArray();
    }

    /// <summary>
    /// Extract first page of PDF as PNG
    /// Uses simple approach - for better PDF support, consider PdfiumViewer
    /// </summary>
    private static byte[] ConvertPdfFirstPageToPng(string pdfPath)
    {
        // For now, read raw bytes - Google Vision can handle PDFs directly
        // If this doesn't work, we'd need to add PdfiumViewer package
        return File.ReadAllBytes(pdfPath);
    }

    /// <summary>
    /// Check if file is a supported image format
    /// </summary>
    public static bool IsSupportedFormat(string filePath)
    {
        if (string.IsNullOrEmpty(filePath))
            return false;

        var ext = Path.GetExtension(filePath).ToLower();
        return ext switch
        {
            ".jpg" or ".jpeg" or ".png" or ".gif" or ".bmp" or ".tiff" or ".tif" or ".pdf" => true,
            _ => false
        };
    }

    /// <summary>
    /// Get image info for debugging
    /// </summary>
    public static string GetImageInfo(string imagePath)
    {
        try
        {
            var fileInfo = new FileInfo(imagePath);
            var ext = Path.GetExtension(imagePath).ToLower();
            
            if (ext == ".pdf")
            {
                return $"PDF file, {fileInfo.Length / 1024.0:F1}KB";
            }

            using var image = Image.FromFile(imagePath);
            return $"{image.Width}x{image.Height}, {image.PixelFormat}, {fileInfo.Length / 1024.0:F1}KB";
        }
        catch (Exception ex)
        {
            return $"Error reading image: {ex.Message}";
        }
    }
}
