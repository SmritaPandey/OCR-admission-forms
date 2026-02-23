using System.Text.RegularExpressions;

namespace OCRAdmissionForms.Infrastructure.Helpers;

/// <summary>
/// Context-aware OCR error correction.
/// Handles common OCR mistakes using field-specific rules.
/// Ported from Python backend world_class_extractor.py OCRErrorCorrector
/// </summary>
public static class OcrErrorCorrector
{
    // Common OCR character substitutions
    private static readonly Dictionary<char, char[]> CharSubstitutions = new()
    {
        { '0', new[] { 'O', 'o', 'Q', 'D' } },
        { 'O', new[] { '0', 'Q', 'D' } },
        { '1', new[] { 'l', 'I', 'i', '|', '!' } },
        { 'l', new[] { '1', 'I', 'i', '|' } },
        { 'I', new[] { '1', 'l', 'i', '|' } },
        { '5', new[] { 'S', 's' } },
        { 'S', new[] { '5' } },
        { '8', new[] { 'B' } },
        { 'B', new[] { '8' } },
        { '6', new[] { 'G', 'b' } },
        { 'G', new[] { '6' } },
        { '2', new[] { 'Z' } },
        { 'Z', new[] { '2' } }
    };

    /// <summary>
    /// Apply context-aware OCR error correction
    /// </summary>
    public static string CorrectText(string text, string context = "general")
    {
        if (string.IsNullOrWhiteSpace(text)) return text;

        return context.ToLower() switch
        {
            "email" => CorrectEmail(text),
            "phone" => CorrectPhone(text),
            "pincode" => CorrectPincode(text),
            "date" => CorrectDate(text),
            "name" => CorrectName(text),
            "aadhar" => CorrectAadhar(text),
            _ => text.Trim()
        };
    }

    /// <summary>
    /// Correct common email OCR errors
    /// </summary>
    public static string CorrectEmail(string text)
    {
        if (string.IsNullOrWhiteSpace(text)) return text;

        var email = text.ToLower().Trim();
        
        // Remove spaces
        email = Regex.Replace(email, @"\s+", "");
        
        // Common OCR errors in email domains
        email = email.Replace("gmall", "gmail");
        email = email.Replace("gmai1", "gmail");
        email = email.Replace("gma1l", "gmail");
        email = email.Replace("gnail", "gmail");
        email = email.Replace("grnail", "gmail");
        email = email.Replace("hotrnail", "hotmail");
        email = email.Replace("yah00", "yahoo");
        email = email.Replace("yahoO", "yahoo");
        email = email.Replace("outl00k", "outlook");
        
        // Fix common @ symbol issues
        email = email.Replace("@gmail. com", "@gmail.com");
        email = email.Replace("@gmail .com", "@gmail.com");
        email = email.Replace(". com", ".com");
        email = email.Replace(" .com", ".com");
        email = email.Replace(".c0m", ".com");
        email = email.Replace(".corn", ".com");
        
        // Fix @ symbol OCR errors
        email = email.Replace("@", "@");
        email = email.Replace("ⓐ", "@");
        
        return email;
    }

    /// <summary>
    /// Extract and correct phone number (Indian 10-digit format)
    /// </summary>
    public static string CorrectPhone(string text)
    {
        if (string.IsNullOrWhiteSpace(text)) return text;

        // Remove all non-digit characters
        var digits = Regex.Replace(text, @"[^\d]", "");
        
        // Remove country code if present
        if (digits.StartsWith("91") && digits.Length == 12)
        {
            digits = digits.Substring(2);
        }
        else if (digits.StartsWith("0") && digits.Length == 11)
        {
            digits = digits.Substring(1);
        }
        
        // Validate 10-digit phone starting with 6-9
        if (digits.Length == 10 && "6789".Contains(digits[0]))
        {
            return digits;
        }
        
        // Try to fix common OCR errors
        if (digits.Length == 10)
        {
            // Replace O with 0, l/I with 1
            digits = digits.Replace('O', '0').Replace('l', '1').Replace('I', '1');
            if ("6789".Contains(digits[0]))
            {
                return digits;
            }
        }
        
        return text.Trim(); // Return original if can't fix
    }

    /// <summary>
    /// Extract and validate Indian pincode (6 digits)
    /// </summary>
    public static string CorrectPincode(string text)
    {
        if (string.IsNullOrWhiteSpace(text)) return text;

        // Remove non-digit characters
        var digits = Regex.Replace(text, @"[^\d]", "");
        
        // Valid Indian pincode: 6 digits, first digit 1-9
        if (digits.Length == 6 && digits[0] != '0')
        {
            return digits;
        }
        
        // Try to extract 6-digit pincode from text
        var match = Regex.Match(text, @"[1-9]\d{5}");
        if (match.Success)
        {
            return match.Value;
        }
        
        return text.Trim();
    }

    /// <summary>
    /// Correct and normalize date format to DD/MM/YYYY
    /// </summary>
    public static string CorrectDate(string text)
    {
        if (string.IsNullOrWhiteSpace(text)) return text;

        var dateText = text.Trim();
        
        // Fix common OCR errors in dates
        dateText = dateText.Replace('O', '0').Replace('o', '0');
        dateText = dateText.Replace('l', '1').Replace('I', '1');
        
        // Try to parse DD/MM/YYYY or DD-MM-YYYY
        var match = Regex.Match(dateText, @"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})");
        if (match.Success)
        {
            var day = int.Parse(match.Groups[1].Value);
            var month = int.Parse(match.Groups[2].Value);
            var year = match.Groups[3].Value;
            
            // Fix year if 2-digit
            if (year.Length == 2)
            {
                year = (int.Parse(year) > 50 ? "19" : "20") + year;
            }
            
            // Validate ranges
            if (day >= 1 && day <= 31 && month >= 1 && month <= 12)
            {
                return $"{day:D2}/{month:D2}/{year}";
            }
            
            // Try swapping day/month if invalid
            if (day >= 1 && day <= 12 && month >= 1 && month <= 31)
            {
                return $"{month:D2}/{day:D2}/{year}";
            }
        }
        
        return text.Trim();
    }

    /// <summary>
    /// Correct name OCR errors - remove garbage, normalize case
    /// </summary>
    public static string CorrectName(string text)
    {
        if (string.IsNullOrWhiteSpace(text)) return text;

        var name = text.Trim();
        
        // Remove form label text
        name = Regex.Replace(name, @"(?:name\s+)?in\s+block\s+letters", "", RegexOptions.IgnoreCase);
        name = Regex.Replace(name, @"block\s+letters", "", RegexOptions.IgnoreCase);
        name = Regex.Replace(name, @"^name\s+", "", RegexOptions.IgnoreCase);
        
        // Remove numbers and special characters (names should be alphabetic)
        name = Regex.Replace(name, @"[^A-Za-z\s]", "");
        
        // Remove common garbage words
        var garbageWords = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            "category", "father", "mother", "guardian", "details", "mobile",
            "phone", "email", "address", "occupation", "designation",
            "organization", "son", "daughter", "of", "vihar", "nagar",
            "colony", "enclave", "park", "road", "street", "sector", "block"
        };
        
        var words = name.Split(' ', StringSplitOptions.RemoveEmptyEntries);
        var cleanWords = words.Where(w => !garbageWords.Contains(w) && w.Length > 1).ToList();
        
        if (cleanWords.Count == 0) return "";
        
        // Title case
        name = string.Join(" ", cleanWords.Select(w => 
            char.ToUpper(w[0]) + (w.Length > 1 ? w.Substring(1).ToLower() : "")));
        
        return name.Trim();
    }

    /// <summary>
    /// Correct Aadhar number (12 digits)
    /// </summary>
    public static string CorrectAadhar(string text)
    {
        if (string.IsNullOrWhiteSpace(text)) return text;

        // Remove spaces and non-digit characters
        var digits = Regex.Replace(text, @"[^\d]", "");
        
        // Aadhar is exactly 12 digits
        if (digits.Length == 12)
        {
            return digits;
        }
        
        // Try to fix common OCR errors
        var cleaned = text.Replace('O', '0').Replace('o', '0')
                          .Replace('l', '1').Replace('I', '1')
                          .Replace('S', '5').Replace('s', '5');
        digits = Regex.Replace(cleaned, @"[^\d]", "");
        
        if (digits.Length == 12)
        {
            return digits;
        }
        
        return text.Trim();
    }

    /// <summary>
    /// Normalize academic session format to YYYY-YYYY
    /// </summary>
    public static string CorrectAcademicSession(string text)
    {
        if (string.IsNullOrWhiteSpace(text)) return text;

        var session = text.Trim();
        
        // Fix OCR errors
        session = session.Replace('O', '0').Replace('o', '0');
        
        var match = Regex.Match(session, @"(\d{4})[-/](\d{2,4})");
        if (match.Success)
        {
            var year1 = int.Parse(match.Groups[1].Value);
            var year2Str = match.Groups[2].Value;
            int year2;
            
            if (year2Str.Length == 2)
            {
                year2 = int.Parse(year1.ToString().Substring(0, 2) + year2Str);
            }
            else
            {
                year2 = int.Parse(year2Str);
            }
            
            // Validate academic year sequence
            if (year2 == year1 + 1 && year1 >= 2020 && year1 <= 2030)
            {
                return $"{year1}-{year2}";
            }
        }
        
        return text.Trim();
    }

    /// <summary>
    /// Normalize college roll number format
    /// </summary>
    public static string CorrectCollegeRollNo(string text)
    {
        if (string.IsNullOrWhiteSpace(text)) return text;

        var roll = text.Trim().ToUpper();
        
        // Common format: 24BC102, 2YBC102, etc.
        // Fix Y -> 4 at start
        if (roll.StartsWith("2Y"))
        {
            roll = "24" + roll.Substring(2);
        }
        
        // Fix O -> 0
        roll = roll.Replace('O', '0');
        
        return roll;
    }
}
