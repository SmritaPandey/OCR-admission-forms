using System.Diagnostics;
using System.Text.Json;

namespace OCRAdmissionForms.Core.Services;

public class OcrResult
{
    public string FullText { get; set; } = string.Empty;
    public List<TextBlock> Blocks { get; set; } = new();
    public float Confidence { get; set; }
    public string? Error { get; set; }
    
    /// <summary>
    /// Pre-extracted fields from Python script's spatial analysis
    /// Keys are snake_case (e.g., "student_name", "email", "phone_number")
    /// </summary>
    public Dictionary<string, string> ExtractedFields { get; set; } = new();
}

public class TextBlock
{
    public string Text { get; set; } = string.Empty;
    public float X { get; set; }
    public float Y { get; set; }
    public float Width { get; set; }
    public float Height { get; set; }
    public float Confidence { get; set; }
}

public interface IOcrService
{
    Task<OcrResult> ExtractTextAsync(string imagePath, string provider = "gemini");
    string GetCredentialsPath();
}

/// <summary>
/// Python-based OCR Service using Google Cloud Vision
/// Calls Python script for guaranteed compatibility with working backend
/// </summary>
public class GoogleVisionOcrService : IOcrService
{
    private readonly string _credentialsPath;
    private readonly string _pythonScriptPath;
    private readonly string _pythonExe;
    private readonly string _logPath;
    private readonly string _dataPath;

    public GoogleVisionOcrService(string credentialsPath)
    {
        // Get app data paths
        _dataPath = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
            "SRCC Student DMS", "data"
        );
        Directory.CreateDirectory(_dataPath);
        _logPath = Path.Combine(_dataPath, "ocr_service.log");
        
        // Handle credentials path - could be relative or absolute
        if (string.IsNullOrEmpty(credentialsPath))
        {
            _credentialsPath = Path.Combine(_dataPath, "google-cloud-credentials.json");
        }
        else if (Path.IsPathRooted(credentialsPath))
        {
            _credentialsPath = credentialsPath;
        }
        else
        {
            _credentialsPath = Path.GetFullPath(credentialsPath);
        }
        
        // Find Python script
        _pythonScriptPath = FindPythonScript();
        
        // Find Python executable
        _pythonExe = FindPython();
        
        Log($"OcrService initialized:");
        Log($"  Credentials: {_credentialsPath}");
        Log($"  Python Script: {_pythonScriptPath}");
        Log($"  Python Exe: {_pythonExe}");
    }

    public string GetCredentialsPath() => _credentialsPath;

    private string FindPythonScript()
    {
        var exeDir = AppDomain.CurrentDomain.BaseDirectory;
        
        var possiblePaths = new[]
        {
            Path.Combine(exeDir, "Resources", "ocr_extract.py"),
            Path.Combine(exeDir, "ocr_extract.py"),
            // Development fallback (relative from bin)
            Path.GetFullPath(Path.Combine(exeDir, "..", "..", "..", "Resources", "ocr_extract.py")),
        };

        foreach (var path in possiblePaths)
        {
            if (File.Exists(path))
            {
                Log($"Found Python script: {path}");
                return path;
            }
        }
        
        return possiblePaths[0];
    }

    private string FindPython()
    {
        var exeDir = AppDomain.CurrentDomain.BaseDirectory;
        
        // Priority order: bundled Python first, then system PATH
        var paths = new[]
        {
            // 1. Bundled Python (shipped with installer)
            Path.Combine(exeDir, "python", "python.exe"),
            // 2. System Python (user-installed, found via PATH)
            "python",
            "python3",
            // 3. Common install locations
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), 
                "Programs", "Python", "Python313", "python.exe"),
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), 
                "Programs", "Python", "Python312", "python.exe"),
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), 
                "Programs", "Python", "Python311", "python.exe"),
        };

        foreach (var path in paths)
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
                        Log($"Found Python: {path}");
                        return path;
                    }
                }
            }
            catch { }
        }
        
        return "python";
    }

    public async Task<OcrResult> ExtractTextAsync(string imagePath, string provider = "gemini")
    {
        Log($"ExtractTextAsync called: {imagePath} (provider={provider})");
        
        // Validate inputs
        if (string.IsNullOrEmpty(imagePath))
            return new OcrResult { Error = "Image path is empty" };
        
        if (!File.Exists(imagePath))
            return new OcrResult { Error = $"Image file not found: {imagePath}" };
        
        if (string.IsNullOrEmpty(_credentialsPath) || !File.Exists(_credentialsPath))
        {
            return new OcrResult 
            { 
                Error = $"Google Cloud credentials not found.\n\n" +
                        $"Expected at: {_credentialsPath}\n\n" +
                        "Please go to Settings and configure your credentials file."
            };
        }
        
        if (string.IsNullOrEmpty(_pythonScriptPath) || !File.Exists(_pythonScriptPath))
        {
            return new OcrResult 
            { 
                Error = $"OCR script not found.\n\n" +
                        $"Expected at: {_pythonScriptPath}\n\n" +
                        "Please reinstall the application."
            };
        }

        try
        {
            var psi = new ProcessStartInfo
            {
                FileName = _pythonExe,
                Arguments = $"\"{_pythonScriptPath}\" \"{imagePath}\" \"{_credentialsPath}\"",
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = true,
                WorkingDirectory = Path.GetDirectoryName(_pythonScriptPath),
                StandardOutputEncoding = System.Text.Encoding.UTF8,
                StandardErrorEncoding = System.Text.Encoding.UTF8
            };
            
            psi.EnvironmentVariables["GOOGLE_APPLICATION_CREDENTIALS"] = _credentialsPath;
            psi.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8";
            
            // Pass Gemini API key — try config file first, then env vars
            var geminiKey = "";
            var keyFile = Path.Combine(_dataPath, "gemini_api_key.txt");
            if (File.Exists(keyFile))
            {
                geminiKey = File.ReadAllText(keyFile).Trim();
                Log($"Gemini API key loaded from config file ({geminiKey.Length} chars)");
            }
            if (string.IsNullOrEmpty(geminiKey))
            {
                geminiKey = Environment.GetEnvironmentVariable("GEMINI_API_KEY") 
                         ?? Environment.GetEnvironmentVariable("GOOGLE_API_KEY") ?? "";
            }
            
            if (!string.IsNullOrEmpty(geminiKey))
            {
                psi.EnvironmentVariables["GEMINI_API_KEY"] = geminiKey;
                psi.EnvironmentVariables["GOOGLE_API_KEY"] = geminiKey;
                // Pass as CLI args: script, imagePath, credentialsPath, geminiKey, provider
                psi.Arguments = $"\"{_pythonScriptPath}\" \"{imagePath}\" \"{_credentialsPath}\" \"{geminiKey}\" \"{provider}\"";
                Log($"Gemini API key configured ({geminiKey.Length} chars), provider={provider}");
            }
            else
            {
                // No API key — pass empty key and provider
                psi.Arguments = $"\"{_pythonScriptPath}\" \"{imagePath}\" \"{_credentialsPath}\" \"\" \"{provider}\"";
                Log($"No GEMINI_API_KEY — provider={provider}");
            }

            Log($"Running: {_pythonExe} \"{_pythonScriptPath}\" \"{imagePath}\" (provider={provider})");
            
            using var proc = new Process { StartInfo = psi };
            proc.Start();
            
            // CRITICAL: Must read stdout/stderr BEFORE WaitForExit to prevent pipe deadlock.
            // If the child process fills the 4KB OS pipe buffer, it blocks writing, and
            // WaitForExit never returns. Reading streams asynchronously prevents this.
            var outputTask = proc.StandardOutput.ReadToEndAsync();
            var errorTask = proc.StandardError.ReadToEndAsync();
            
            // Wait for both streams AND process exit with a timeout
            using var cts = new CancellationTokenSource(TimeSpan.FromMinutes(5));
            try
            {
                await Task.WhenAll(outputTask, errorTask);
                await proc.WaitForExitAsync(cts.Token);
            }
            catch (OperationCanceledException)
            {
                try { proc.Kill(true); } catch { }
                Log("OCR timed out after 5 minutes");
                return new OcrResult { Error = "OCR timed out after 5 minutes. The Gemini API may be slow — try 'spatial' or 'enhanced' provider." };
            }
            
            var output = outputTask.Result;
            var error = errorTask.Result;
            
            Log($"Exit code: {proc.ExitCode}, Output: {output.Length} chars");
            
            // Save raw output for debugging
            try 
            { 
                File.WriteAllText(Path.Combine(_dataPath, "python_stdout.json"), output);
                File.WriteAllText(Path.Combine(_dataPath, "python_stderr.log"), $"[{DateTime.Now:yyyy-MM-dd HH:mm:ss}]\n{error}"); 
            } 
            catch { }
            if (!string.IsNullOrEmpty(error))
            {
                Log($"Stderr ({error.Length} chars): {error.Substring(0, Math.Min(500, error.Length))}");
            }

            // Parse JSON response
            if (!string.IsNullOrWhiteSpace(output))
            {
                try
                {
                    var json = JsonDocument.Parse(output);
                    var root = json.RootElement;
                    
                    var success = root.TryGetProperty("success", out var successProp) && successProp.GetBoolean();
                    
                    if (success)
                    {
                        var text = root.TryGetProperty("text", out var textProp) ? textProp.GetString() ?? "" : "";
                        var confidence = root.TryGetProperty("confidence", out var confProp) ? (float)confProp.GetDouble() : 95f;
                        
                        // Parse extracted fields from Python's spatial analysis
                        var extractedFields = new Dictionary<string, string>();
                        if (root.TryGetProperty("fields", out var fieldsProp))
                        {
                            foreach (var field in fieldsProp.EnumerateObject())
                            {
                                if (field.Value.ValueKind == JsonValueKind.String)
                                {
                                    var value = field.Value.GetString();
                                    if (!string.IsNullOrEmpty(value))
                                    {
                                        extractedFields[field.Name] = value;
                                    }
                                }
                                else if (field.Value.ValueKind == JsonValueKind.True)
                                {
                                    extractedFields[field.Name] = "true";
                                }
                                else if (field.Value.ValueKind == JsonValueKind.False)
                                {
                                    extractedFields[field.Name] = "false";
                                }
                                else if (field.Value.ValueKind == JsonValueKind.Number)
                                {
                                    extractedFields[field.Name] = field.Value.GetRawText();
                                }
                            }
                            Log($"Extracted {extractedFields.Count} fields from Python");
                        }
                        
                        var method = root.TryGetProperty("extraction_method", out var methodProp) ? methodProp.GetString() ?? "spatial" : "spatial";
                        Log($"OCR success: {text.Length} chars, {confidence}% confidence, {extractedFields.Count} fields, method={method}");
                        
                        return new OcrResult
                        {
                            FullText = text,
                            Confidence = confidence,
                            ExtractedFields = extractedFields
                        };
                    }
                    else
                    {
                        var errMsg = root.TryGetProperty("error", out var errProp) ? errProp.GetString() : "Unknown error";
                        Log($"OCR failed: {errMsg}");
                        return new OcrResult { Error = errMsg };
                    }
                }
                catch (JsonException jex)
                {
                    Log($"JSON parse error: {jex.Message}");
                    // Not JSON, maybe raw text or error
                    if (proc.ExitCode != 0)
                    {
                        return new OcrResult { Error = $"OCR script error: {output}" };
                    }
                    return new OcrResult { FullText = output.Trim() };
                }
            }
            
            Log($"No output, exit code: {proc.ExitCode}");
            return new OcrResult { Error = $"No output from OCR. Exit code: {proc.ExitCode}\n\nStderr: {error}" };
        }
        catch (Exception ex)
        {
            Log($"Exception: {ex.Message}");
            return new OcrResult { Error = $"OCR failed: {ex.Message}" };
        }
    }

    private void Log(string message)
    {
        try
        {
            var entry = $"[{DateTime.Now:yyyy-MM-dd HH:mm:ss}] {message}\n";
            File.AppendAllText(_logPath, entry);
            Debug.WriteLine($"[OCR] {message}");
        }
        catch { }
    }
}
