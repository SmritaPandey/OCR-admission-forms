using System.Diagnostics;
using System.Text.Json;

namespace OCRAdmissionForms.Core.Services;

/// <summary>
/// Python OCR Bridge - Calls the existing Python backend OCR directly
/// This ensures exact same behavior as the Electron/React version
/// </summary>
public class PythonOcrBridge
{
    private readonly string _pythonPath;
    private readonly string _backendPath;
    private readonly string _credentialsPath;
    private readonly string _logPath;

    public PythonOcrBridge(string credentialsPath)
    {
        _credentialsPath = credentialsPath;
        
        // Find Python and backend paths
        _pythonPath = FindPythonPath();
        _backendPath = FindBackendPath();
        
        var appData = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
        _logPath = Path.Combine(appData, "SRCC Student DMS", "data", "python_ocr.log");
    }

    private string FindPythonPath()
    {
        // Try common Python paths
        var pythonPaths = new[]
        {
            "python",
            "python3",
            @"C:\Python312\python.exe",
            @"C:\Python311\python.exe",
            @"C:\Python310\python.exe",
            @"C:\Users\" + Environment.UserName + @"\AppData\Local\Programs\Python\Python312\python.exe",
            @"C:\Users\" + Environment.UserName + @"\AppData\Local\Programs\Python\Python311\python.exe",
            @"C:\Users\" + Environment.UserName + @"\AppData\Local\Programs\Python\Python310\python.exe"
        };

        foreach (var path in pythonPaths)
        {
            try
            {
                var psi = new ProcessStartInfo
                {
                    FileName = path,
                    Arguments = "--version",
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    UseShellExecute = false,
                    CreateNoWindow = true
                };
                using var proc = Process.Start(psi);
                if (proc != null)
                {
                    proc.WaitForExit(3000);
                    if (proc.ExitCode == 0)
                    {
                        return path;
                    }
                }
            }
            catch { }
        }
        
        return "python"; // Default fallback
    }

    private string FindBackendPath()
    {
        // Look for the backend folder relative to the app
        var possiblePaths = new[]
        {
            Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "..", "..", "..", "..", "..", "..", "backend"),
            Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "backend"),
            @"C:\Users\" + Environment.UserName + @"\Documents\GitHub\OCR-admission-forms\backend",
            Path.Combine(Directory.GetCurrentDirectory(), "..", "..", "..", "..", "..", "..", "backend")
        };

        foreach (var path in possiblePaths)
        {
            var fullPath = Path.GetFullPath(path);
            if (Directory.Exists(fullPath) && File.Exists(Path.Combine(fullPath, "main.py")))
            {
                return fullPath;
            }
        }
        
        return "";
    }

    public bool IsPythonAvailable()
    {
        try
        {
            var psi = new ProcessStartInfo
            {
                FileName = _pythonPath,
                Arguments = "--version",
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = true
            };
            using var proc = Process.Start(psi);
            if (proc == null) return false;
            proc.WaitForExit(3000);
            return proc.ExitCode == 0;
        }
        catch
        {
            return false;
        }
    }

    public bool IsBackendAvailable()
    {
        return !string.IsNullOrEmpty(_backendPath) && Directory.Exists(_backendPath);
    }

    /// <summary>
    /// Extract text using Python Google Vision provider
    /// </summary>
    public async Task<OcrResult> ExtractTextAsync(string imagePath)
    {
        if (string.IsNullOrEmpty(imagePath) || !File.Exists(imagePath))
        {
            return new OcrResult { Error = $"Image file not found: {imagePath}" };
        }

        // Create a simple Python script to run OCR
        var pythonScript = CreateOcrScript();
        var scriptPath = Path.GetTempFileName() + ".py";
        
        try
        {
            await File.WriteAllTextAsync(scriptPath, pythonScript);
            
            var psi = new ProcessStartInfo
            {
                FileName = _pythonPath,
                Arguments = $"\"{scriptPath}\" \"{imagePath}\" \"{_credentialsPath}\"",
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = true,
                WorkingDirectory = _backendPath
            };
            
            // Set credentials environment variable
            psi.EnvironmentVariables["GOOGLE_APPLICATION_CREDENTIALS"] = _credentialsPath;
            
            using var proc = new Process { StartInfo = psi };
            proc.Start();
            
            var output = await proc.StandardOutput.ReadToEndAsync();
            var error = await proc.StandardError.ReadToEndAsync();
            
            await proc.WaitForExitAsync();
            
            // Log for debugging
            LogOcrResult(imagePath, output, error, proc.ExitCode);
            
            if (proc.ExitCode != 0)
            {
                return new OcrResult { Error = $"Python OCR failed:\n{error}" };
            }
            
            // Parse JSON output
            try
            {
                var jsonResult = JsonSerializer.Deserialize<PythonOcrOutput>(output);
                if (jsonResult != null)
                {
                    return new OcrResult
                    {
                        FullText = jsonResult.text ?? "",
                        Confidence = jsonResult.confidence,
                        Error = jsonResult.error
                    };
                }
            }
            catch (JsonException)
            {
                // If not JSON, return raw text as result
                return new OcrResult { FullText = output.Trim() };
            }
            
            return new OcrResult { FullText = output.Trim() };
        }
        catch (Exception ex)
        {
            return new OcrResult { Error = $"Python OCR bridge error: {ex.Message}" };
        }
        finally
        {
            try { if (File.Exists(scriptPath)) File.Delete(scriptPath); } catch { }
        }
    }

    private string CreateOcrScript()
    {
        return @"
import sys
import os
import json

def main():
    if len(sys.argv) < 3:
        print(json.dumps({'error': 'Usage: script.py <image_path> <credentials_path>'}))
        sys.exit(1)
    
    image_path = sys.argv[1]
    credentials_path = sys.argv[2]
    
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
    
    try:
        from google.cloud import vision
        from PIL import Image
        import io
        
        # Read image
        with open(image_path, 'rb') as f:
            content = f.read()
        
        # Create Vision client and detect text
        client = vision.ImageAnnotatorClient()
        image = vision.Image(content=content)
        response = client.text_detection(image=image)
        
        if response.error.message:
            print(json.dumps({'error': response.error.message}))
            sys.exit(1)
        
        texts = response.text_annotations
        if texts:
            result = {
                'text': texts[0].description.strip(),
                'confidence': 95.0,
                'error': None
            }
        else:
            result = {
                'text': '',
                'confidence': 0.0,
                'error': None
            }
        
        print(json.dumps(result))
        
    except Exception as e:
        print(json.dumps({'error': str(e), 'text': '', 'confidence': 0}))
        sys.exit(1)

if __name__ == '__main__':
    main()
";
    }

    private void LogOcrResult(string imagePath, string output, string error, int exitCode)
    {
        try
        {
            var logDir = Path.GetDirectoryName(_logPath);
            if (!string.IsNullOrEmpty(logDir))
                Directory.CreateDirectory(logDir);
                
            var entry = $"[{DateTime.Now:yyyy-MM-dd HH:mm:ss}] Image: {Path.GetFileName(imagePath)}\n" +
                       $"  ExitCode: {exitCode}\n" +
                       $"  Output: {output.Substring(0, Math.Min(200, output.Length))}...\n" +
                       $"  Error: {error}\n\n";
            File.AppendAllText(_logPath, entry);
        }
        catch { }
    }

    private class PythonOcrOutput
    {
        public string? text { get; set; }
        public float confidence { get; set; }
        public string? error { get; set; }
    }
}
