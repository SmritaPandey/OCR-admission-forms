using System.Text.RegularExpressions;

namespace OCRAdmissionForms.Core.Services;

/// <summary>
/// Corrects common OCR errors with context-aware fixes
/// Ported from Python backend ocr_error_corrector.py
/// </summary>
public static class OcrErrorCorrector
{
    // Common OCR character substitutions
    private static readonly Dictionary<char, char> CommonSubstitutions = new()
    {
        { '0', 'O' }, { 'O', '0' },
        { '1', 'I' }, { 'I', '1' }, { 'l', '1' },
        { '5', 'S' }, { 'S', '5' },
        { '8', 'B' }, { 'B', '8' },
        { '6', 'G' }, { 'G', '6' },
        { '2', 'Z' }, { 'Z', '2' },
        { '9', 'g' }, { 'g', '9' }
    };

    /// <summary>
    /// Correct email OCR errors
    /// </summary>
    public static string CorrectEmail(string email)
    {
        if (string.IsNullOrWhiteSpace(email)) return email;
        
        var corrected = email.ToLower().Trim();
        
        // Common domain corrections
        corrected = corrected
            .Replace("gmai1.com", "gmail.com")
            .Replace("gmaii.com", "gmail.com")
            .Replace("grnail.com", "gmail.com")
            .Replace("qmail.com", "gmail.com")
            .Replace("gnail.com", "gmail.com")
            .Replace("yah00.com", "yahoo.com")
            .Replace("yaho0.com", "yahoo.com")
            .Replace("hotmai1.com", "hotmail.com")
            .Replace("0utlook.com", "outlook.com")
            .Replace("out1ook.com", "outlook.com");
            
        // Fix common character errors around @
        corrected = Regex.Replace(corrected, @"@+", "@");
        corrected = Regex.Replace(corrected, @"\.+", ".");
        
        // Remove spaces
        corrected = corrected.Replace(" ", "");
        
        return corrected;
    }

    /// <summary>
    /// Correct phone number OCR errors (Indian format)
    /// </summary>
    public static string CorrectPhoneNumber(string phone)
    {
        if (string.IsNullOrWhiteSpace(phone)) return phone;
        
        // Remove all non-digits
        var digitsOnly = Regex.Replace(phone, @"\D", "");
        
        // Apply OCR corrections for digits that look like letters
        digitsOnly = digitsOnly
            .Replace('O', '0')
            .Replace('o', '0')
            .Replace('I', '1')
            .Replace('l', '1')
            .Replace('S', '5')
            .Replace('s', '5')
            .Replace('B', '8')
            .Replace('b', '8');
            
        // Remove country code if present
        if (digitsOnly.StartsWith("91") && digitsOnly.Length == 12)
        {
            digitsOnly = digitsOnly.Substring(2);
        }
        if (digitsOnly.StartsWith("0") && digitsOnly.Length == 11)
        {
            digitsOnly = digitsOnly.Substring(1);
        }
        
        // Validate Indian mobile number
        if (digitsOnly.Length == 10 && Regex.IsMatch(digitsOnly, @"^[6-9]\d{9}$"))
        {
            return digitsOnly;
        }
        
        return phone; // Return original if can't correct
    }

    /// <summary>
    /// Correct pincode OCR errors (Indian 6-digit format)
    /// </summary>
    public static string CorrectPincode(string pincode)
    {
        if (string.IsNullOrWhiteSpace(pincode)) return pincode;
        
        // Extract digits, correcting common OCR errors
        var corrected = pincode
            .Replace('O', '0')
            .Replace('o', '0')
            .Replace('I', '1')
            .Replace('l', '1')
            .Replace('S', '5')
            .Replace('B', '8');
            
        var digitsOnly = Regex.Replace(corrected, @"\D", "");
        
        // Valid Indian pincode starts with 1-9 and is 6 digits
        if (digitsOnly.Length == 6 && Regex.IsMatch(digitsOnly, @"^[1-9]\d{5}$"))
        {
            return digitsOnly;
        }
        
        return pincode;
    }

    /// <summary>
    /// Correct Aadhar number OCR errors (12 digits)
    /// </summary>
    public static string CorrectAadhar(string aadhar)
    {
        if (string.IsNullOrWhiteSpace(aadhar)) return aadhar;
        
        // Remove spaces and apply OCR corrections
        var corrected = aadhar.Replace(" ", "")
            .Replace('O', '0')
            .Replace('o', '0')
            .Replace('I', '1')
            .Replace('l', '1')
            .Replace('S', '5')
            .Replace('B', '8');
            
        var digitsOnly = Regex.Replace(corrected, @"\D", "");
        
        // Valid Aadhar is exactly 12 digits, starting with 2-9
        if (digitsOnly.Length == 12 && Regex.IsMatch(digitsOnly, @"^[2-9]\d{11}$"))
        {
            // Format with spaces for readability
            return $"{digitsOnly.Substring(0, 4)} {digitsOnly.Substring(4, 4)} {digitsOnly.Substring(8, 4)}";
        }
        
        return aadhar;
    }

    /// <summary>
    /// Correct date OCR errors
    /// </summary>
    public static string CorrectDate(string date)
    {
        if (string.IsNullOrWhiteSpace(date)) return date;
        
        // Apply common OCR corrections
        var corrected = date
            .Replace('O', '0')
            .Replace('o', '0')
            .Replace('I', '1')
            .Replace('l', '1');
            
        // Normalize separators
        corrected = Regex.Replace(corrected, @"[/\\.-]", "/");
        
        // Try to parse and validate
        var match = Regex.Match(corrected, @"(\d{1,2})/(\d{1,2})/(\d{2,4})");
        if (match.Success)
        {
            var day = int.Parse(match.Groups[1].Value);
            var month = int.Parse(match.Groups[2].Value);
            var year = match.Groups[3].Value;
            
            // Fix 2-digit year
            if (year.Length == 2)
            {
                year = (int.Parse(year) > 50 ? "19" : "20") + year;
            }
            
            // Validate ranges
            if (day >= 1 && day <= 31 && month >= 1 && month <= 12)
            {
                return $"{day:D2}/{month:D2}/{year}";
            }
        }
        
        return date;
    }

    /// <summary>
    /// Correct name OCR errors - capitalize properly
    /// </summary>
    public static string CorrectName(string name)
    {
        if (string.IsNullOrWhiteSpace(name)) return name;
        
        // Remove extra spaces and non-letter characters (except space)
        var cleaned = Regex.Replace(name.Trim(), @"[^A-Za-z\s]", "");
        cleaned = Regex.Replace(cleaned, @"\s+", " ");
        
        // Title case
        var words = cleaned.Split(' ')
            .Where(w => !string.IsNullOrWhiteSpace(w))
            .Select(w => char.ToUpper(w[0]) + w.Substring(1).ToLower());
            
        return string.Join(" ", words);
    }

    /// <summary>
    /// Correct percentage OCR errors
    /// </summary>
    public static string CorrectPercentage(string percentage)
    {
        if (string.IsNullOrWhiteSpace(percentage)) return percentage;
        
        // Extract numeric value
        var match = Regex.Match(percentage, @"(\d+(?:[.,]\d+)?)\s*%?");
        if (match.Success)
        {
            var value = match.Groups[1].Value.Replace(',', '.');
            if (double.TryParse(value, out var num) && num >= 0 && num <= 100)
            {
                return $"{num:F2}%";
            }
        }
        
        return percentage;
    }

    /// <summary>
    /// Clean general text - remove form labels and clean up
    /// </summary>
    public static string CleanText(string text)
    {
        if (string.IsNullOrWhiteSpace(text)) return text;
        
        var cleaned = text.Trim();
        
        // Remove common form label prefixes
        cleaned = Regex.Replace(cleaned, @"^[\d]+\s*[.):]\s*", ""); // Remove numbering
        cleaned = Regex.Replace(cleaned, @"^[a-z]\s*[.):]\s*", "", RegexOptions.IgnoreCase); // Remove letter prefixes
        
        // Remove excess whitespace
        cleaned = Regex.Replace(cleaned, @"\s+", " ");
        
        return cleaned.Trim();
    }

    /// <summary>
    /// Check if text looks like a form label rather than data
    /// </summary>
    public static bool IsFormLabel(string value)
    {
        if (string.IsNullOrWhiteSpace(value)) return true;
        
        var lower = value.ToLower().Trim();
        
        // Form labels to reject
        var labels = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            "name", "first name", "middle name", "surname", "in block letters",
            "date of birth", "dob", "gender", "sex", "male", "female",
            "address", "permanent address", "correspondence address",
            "state", "pin", "pincode", "email", "phone", "mobile", "contact",
            "mother", "father", "guardian", "occupation", "designation",
            "category", "details", "signature", "tick", "applicable"
        };
        
        if (labels.Contains(lower)) return true;
        if (lower.Contains("block letters")) return true;
        if (value.Length < 2) return true;
        
        return false;
    }
}
