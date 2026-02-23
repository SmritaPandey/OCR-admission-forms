using System.Text.RegularExpressions;
using OCRAdmissionForms.Core.Interfaces;
using OCRAdmissionForms.Infrastructure.Helpers;

namespace OCRAdmissionForms.Infrastructure.Services;

/// <summary>
/// Specialized extractor for SRCC Student Data Form format.
/// Implements comprehensive field extraction with pattern matching and OCR error correction.
/// Ported from Python backend srcc_form_extractor.py
/// </summary>
public class SrccFormExtractor : IFormExtractorService
{
    /// <summary>
    /// Extract all form fields from raw OCR text
    /// </summary>
    public ExtractionResult Extract(string rawText)
    {
        var result = new ExtractionResult();
        
        if (string.IsNullOrWhiteSpace(rawText)) return result;
        
        // Normalize text
        var text = rawText.Replace("\r\n", "\n");
        
        // Extract each field category
        ExtractStudentName(text, result.Fields);
        ExtractAcademicDetails(text, result.Fields);
        ExtractPersonalInfo(text, result.Fields);
        ExtractAddressDetails(text, result.Fields);
        ExtractContactDetails(text, result.Fields);
        ExtractParentDetails(text, result.Fields);
        ExtractClassXiiDetails(text, result.Fields);
        ExtractParentOccupationalDetails(text, result.Fields);
        ExtractDocumentChecklist(text, result.Fields);
        
        // Clean up extracted values
        CleanupExtractedValues(result.Fields);
        
        // Cross-validate and correct
        CrossValidateAndCorrect(result.Fields);
        
        // Apply field mappings for compatibility
        ApplyFieldMappings(result.Fields);
        
        // Calculate confidence scores
        foreach (var (field, value) in result.Fields)
        {
            if (!string.IsNullOrEmpty(value))
            {
                result.FieldConfidences[field] = GetFieldConfidence(field, value);
            }
        }
        
        result.OverallConfidence = result.FieldConfidences.Count > 0 
            ? result.FieldConfidences.Values.Average() 
            : 0f;
        
        return result;
    }
    
    /// <summary>
    /// Extract fields from a specific page of the form
    /// </summary>
    public ExtractionResult ExtractFromPage(string rawText, int pageNumber)
    {
        // For now, extract all fields - page-specific extraction can be added later
        return Extract(rawText);
    }
    
    /// <summary>
    /// Calculate confidence score for an extracted field
    /// </summary>
    public float GetFieldConfidence(string fieldName, string? value)
    {
        if (string.IsNullOrWhiteSpace(value)) return 0f;
        
        var baseConfidence = 0.6f;
        var valueStr = value.Trim();
        
        // Field-specific validation boosts
        switch (fieldName.ToLower())
        {
            case "email":
                if (valueStr.Contains("@") && valueStr.Contains("."))
                    baseConfidence += 0.15f;
                break;
                
            case "phonenumber":
            case "mothermobile":
            case "fathermobile":
            case "guardianmobile":
                if (Regex.IsMatch(valueStr, @"^[6-9]\d{9}$"))
                    baseConfidence += 0.15f;
                break;
                
            case "pincode":
            case "permanentpincode":
            case "correspondencepincode":
                if (Regex.IsMatch(valueStr, @"^\d{6}$"))
                    baseConfidence += 0.15f;
                break;
                
            case "aadharnumber":
                if (Regex.IsMatch(valueStr, @"^\d{12}$"))
                    baseConfidence += 0.15f;
                break;
                
            case "studentname":
            case "fathername":
            case "mothername":
                if (valueStr.Split(' ').Length >= 1)
                    baseConfidence += 0.1f;
                break;
                
            case "dateofbirth":
            case "dateofadmission":
                if (Regex.IsMatch(valueStr, @"^\d{2}/\d{2}/\d{4}$"))
                    baseConfidence += 0.15f;
                break;
        }
        
        return Math.Min(1.0f, baseConfidence);
    }
    
    #region Extraction Methods
    
    private void ExtractStudentName(string text, Dictionary<string, string?> fields)
    {
        // Extract first name
        var firstMatch = FieldPatterns.FirstName.Match(text);
        if (firstMatch.Success)
        {
            var firstName = OcrErrorCorrector.CorrectName(firstMatch.Groups[1].Value);
            if (!string.IsNullOrEmpty(firstName) && !FieldPatterns.IsFormLabel(firstName))
            {
                fields["FirstName"] = firstName;
            }
        }
        
        // Extract middle name
        var middleMatch = FieldPatterns.MiddleName.Match(text);
        if (middleMatch.Success)
        {
            var middleName = OcrErrorCorrector.CorrectName(middleMatch.Groups[1].Value);
            if (!string.IsNullOrEmpty(middleName) && !FieldPatterns.IsFormLabel(middleName))
            {
                fields["MiddleName"] = middleName;
            }
        }
        
        // Extract surname
        var surnameMatch = FieldPatterns.Surname.Match(text);
        if (surnameMatch.Success)
        {
            var surname = OcrErrorCorrector.CorrectName(surnameMatch.Groups[1].Value);
            if (!string.IsNullOrEmpty(surname) && !FieldPatterns.IsFormLabel(surname))
            {
                fields["Surname"] = surname;
            }
        }
        
        // Try full name pattern
        var nameMatch = FieldPatterns.StudentName.Match(text);
        if (nameMatch.Success)
        {
            var fullName = OcrErrorCorrector.CorrectName(nameMatch.Groups[1].Value);
            if (!string.IsNullOrEmpty(fullName) && !FieldPatterns.IsFormLabel(fullName))
            {
                fields["StudentName"] = fullName;
            }
        }
        
        // Combine parts if no full name found
        if (!fields.ContainsKey("StudentName") || string.IsNullOrEmpty(fields["StudentName"]))
        {
            var parts = new List<string>();
            if (fields.TryGetValue("FirstName", out var fn) && !string.IsNullOrEmpty(fn))
                parts.Add(fn);
            if (fields.TryGetValue("MiddleName", out var mn) && !string.IsNullOrEmpty(mn))
                parts.Add(mn);
            if (fields.TryGetValue("Surname", out var sn) && !string.IsNullOrEmpty(sn))
                parts.Add(sn);
            
            if (parts.Count > 0)
            {
                fields["StudentName"] = string.Join(" ", parts);
            }
        }
    }
    
    private void ExtractAcademicDetails(string text, Dictionary<string, string?> fields)
    {
        // Academic Session
        var sessionMatch = FieldPatterns.AcademicSession.Match(text);
        if (sessionMatch.Success)
        {
            fields["AcademicSession"] = OcrErrorCorrector.CorrectAcademicSession(sessionMatch.Groups[1].Value);
        }
        
        // Course
        var courseMatch = FieldPatterns.Course.Match(text);
        if (courseMatch.Success)
        {
            fields["Course"] = courseMatch.Groups[1].Value.Trim();
        }
        
        // Admission Category
        var categoryMatch = FieldPatterns.AdmissionCategory.Match(text);
        if (categoryMatch.Success)
        {
            fields["AdmissionCategory"] = categoryMatch.Groups[1].Value.Trim().ToUpper();
        }
        
        // DU Portal Form Number
        var formNoMatch = FieldPatterns.DuPortalFormNumber.Match(text);
        if (formNoMatch.Success)
        {
            fields["DuPortalFormNumber"] = formNoMatch.Groups[1].Value.Trim();
        }
        
        // CUET Score
        var cuetMatch = FieldPatterns.CuetScore.Match(text);
        if (cuetMatch.Success)
        {
            fields["CuetScore"] = cuetMatch.Groups[1].Value.Trim();
        }
        
        // College Roll No
        var rollMatch = FieldPatterns.CollegeRollNo.Match(text);
        if (rollMatch.Success)
        {
            fields["CollegeRollNo"] = OcrErrorCorrector.CorrectCollegeRollNo(rollMatch.Groups[1].Value);
        }
        
        // Date of Admission
        var admDateMatch = FieldPatterns.DateOfAdmission.Match(text);
        if (admDateMatch.Success)
        {
            fields["DateOfAdmission"] = OcrErrorCorrector.CorrectDate(admDateMatch.Groups[1].Value);
        }
    }
    
    private void ExtractPersonalInfo(string text, Dictionary<string, string?> fields)
    {
        // Gender
        var genderMatch = FieldPatterns.Gender.Match(text);
        if (genderMatch.Success)
        {
            var gender = genderMatch.Groups[1].Value.Trim().ToUpper();
            fields["Gender"] = gender switch
            {
                "M" => "Male",
                "F" => "Female",
                "T" => "Transgender",
                _ => gender.Length > 1 ? char.ToUpper(gender[0]) + gender.Substring(1).ToLower() : gender
            };
        }
        
        // Date of Birth
        var dobMatch = FieldPatterns.DateOfBirth.Match(text);
        if (dobMatch.Success)
        {
            fields["DateOfBirth"] = OcrErrorCorrector.CorrectDate(dobMatch.Groups[1].Value);
        }
        
        // Category
        var catMatch = FieldPatterns.Category.Match(text);
        if (catMatch.Success)
        {
            fields["Category"] = catMatch.Groups[1].Value.Trim().ToUpper();
        }
        
        // Nationality
        var natMatch = FieldPatterns.Nationality.Match(text);
        if (natMatch.Success)
        {
            var nationality = natMatch.Groups[1].Value.Trim();
            fields["Nationality"] = char.ToUpper(nationality[0]) + nationality.Substring(1).ToLower();
        }
        
        // Religion
        var relMatch = FieldPatterns.Religion.Match(text);
        if (relMatch.Success)
        {
            var religion = relMatch.Groups[1].Value.Trim();
            fields["Religion"] = char.ToUpper(religion[0]) + religion.Substring(1).ToLower();
        }
        
        // Blood Group
        var bloodMatch = FieldPatterns.BloodGroup.Match(text);
        if (bloodMatch.Success)
        {
            fields["BloodGroup"] = bloodMatch.Groups[1].Value.Trim().ToUpper();
        }
        
        // Aadhar Number
        var aadharMatch = FieldPatterns.AadharNumber.Match(text);
        if (aadharMatch.Success)
        {
            fields["AadharNumber"] = OcrErrorCorrector.CorrectAadhar(aadharMatch.Groups[1].Value);
        }
        
        // Below Poverty Line
        var bplMatch = FieldPatterns.BelowPovertyLine.Match(text);
        if (bplMatch.Success)
        {
            var bpl = bplMatch.Groups[1].Value.Trim().ToUpper();
            fields["BelowPovertyLine"] = (bpl == "Y" || bpl == "YES") ? "Yes" : "No";
        }
        
        // Annual Income
        var incomeMatch = FieldPatterns.AnnualIncome.Match(text);
        if (incomeMatch.Success)
        {
            fields["AnnualIncome"] = incomeMatch.Groups[1].Value.Replace(",", "").Trim();
        }
        
        // Minority Category
        var minorityMatch = FieldPatterns.MinorityCategory.Match(text);
        if (minorityMatch.Success)
        {
            fields["MinorityCategory"] = minorityMatch.Groups[1].Value.Trim();
        }
    }
    
    private void ExtractAddressDetails(string text, Dictionary<string, string?> fields)
    {
        // Permanent Address
        var permAddrMatch = FieldPatterns.PermanentAddress.Match(text);
        if (permAddrMatch.Success)
        {
            var addr = permAddrMatch.Groups[1].Value.Trim();
            addr = Regex.Replace(addr, @"\s+", " ");
            if (addr.Length > 5 && !FieldPatterns.IsFormLabel(addr))
            {
                fields["PermanentAddress"] = addr;
            }
        }
        
        // Permanent State
        var stateMatch = FieldPatterns.PermanentState.Match(text);
        if (stateMatch.Success)
        {
            var state = stateMatch.Groups[1].Value.Trim();
            if (!FieldPatterns.IsFormLabel(state))
            {
                fields["PermanentState"] = state;
                fields["State"] = state; // Legacy field
            }
        }
        
        // Pincode
        var pincodeMatch = FieldPatterns.Pincode.Match(text);
        if (pincodeMatch.Success)
        {
            var pincode = OcrErrorCorrector.CorrectPincode(pincodeMatch.Groups[1].Value);
            fields["Pincode"] = pincode;
            fields["PermanentPincode"] = pincode;
        }
        
        // Correspondence Address
        var corrAddrMatch = FieldPatterns.CorrespondenceAddress.Match(text);
        if (corrAddrMatch.Success)
        {
            var addr = corrAddrMatch.Groups[1].Value.Trim();
            addr = Regex.Replace(addr, @"\s+", " ");
            if (addr.Length > 5 && !FieldPatterns.IsFormLabel(addr))
            {
                fields["CorrespondenceAddress"] = addr;
            }
        }
    }
    
    private void ExtractContactDetails(string text, Dictionary<string, string?> fields)
    {
        // Email
        var emailMatch = FieldPatterns.Email.Match(text);
        if (emailMatch.Success)
        {
            fields["Email"] = OcrErrorCorrector.CorrectEmail(emailMatch.Groups[1].Value);
        }
        
        // Phone Number
        var phoneMatch = FieldPatterns.PhoneNumber.Match(text);
        if (phoneMatch.Success)
        {
            fields["PhoneNumber"] = OcrErrorCorrector.CorrectPhone(phoneMatch.Groups[1].Value);
        }
        
        // Find all 10-digit phone numbers for alternate phones
        var allPhones = FieldPatterns.IndianPhone.Matches(text);
        var phones = new HashSet<string>();
        foreach (Match m in allPhones)
        {
            var phone = OcrErrorCorrector.CorrectPhone(m.Groups[1].Value);
            if (phone.Length == 10)
            {
                phones.Add(phone);
            }
        }
        
        // Set alternate phone if different from primary
        if (phones.Count > 1 && fields.TryGetValue("PhoneNumber", out var primaryPhone))
        {
            var alternate = phones.FirstOrDefault(p => p != primaryPhone);
            if (!string.IsNullOrEmpty(alternate))
            {
                fields["AlternatePhone"] = alternate;
            }
        }
    }
    
    private void ExtractParentDetails(string text, Dictionary<string, string?> fields)
    {
        // Mother's Name
        var motherMatch = FieldPatterns.MotherName.Match(text);
        if (motherMatch.Success)
        {
            var name = OcrErrorCorrector.CorrectName(motherMatch.Groups[1].Value);
            if (!string.IsNullOrEmpty(name) && !FieldPatterns.IsFormLabel(name))
            {
                fields["MotherName"] = name;
            }
        }
        
        // Father's Name
        var fatherMatch = FieldPatterns.FatherName.Match(text);
        if (fatherMatch.Success)
        {
            var name = OcrErrorCorrector.CorrectName(fatherMatch.Groups[1].Value);
            if (!string.IsNullOrEmpty(name) && !FieldPatterns.IsFormLabel(name))
            {
                fields["FatherName"] = name;
            }
        }
    }
    
    private void ExtractClassXiiDetails(string text, Dictionary<string, string?> fields)
    {
        // Year of Passing
        var yearMatch = FieldPatterns.TwelfthYear.Match(text);
        if (yearMatch.Success)
        {
            fields["TwelfthYear"] = yearMatch.Groups[1].Value.Trim();
        }
        
        // Board
        var boardMatch = FieldPatterns.TwelfthBoard.Match(text);
        if (boardMatch.Success)
        {
            fields["TwelfthBoard"] = boardMatch.Groups[1].Value.Trim().ToUpper();
        }
        
        // Roll Number
        var rollMatch = FieldPatterns.TwelfthRollNumber.Match(text);
        if (rollMatch.Success)
        {
            fields["TwelfthRollNumber"] = rollMatch.Groups[1].Value.Trim();
        }
        
        // Institution
        var instMatch = FieldPatterns.TwelfthInstitution.Match(text);
        if (instMatch.Success)
        {
            var inst = instMatch.Groups[1].Value.Trim();
            if (!FieldPatterns.IsFormLabel(inst))
            {
                fields["TwelfthInstitution"] = inst;
            }
        }
        
        // Hindi Studied Upto
        var hindiMatch = FieldPatterns.HindiStudiedUpto.Match(text);
        if (hindiMatch.Success)
        {
            fields["HindiStudiedUpto"] = hindiMatch.Groups[1].Value.Trim().ToUpper();
        }
        
        // Percentage
        var percMatch = FieldPatterns.TwelfthPercentage.Match(text);
        if (percMatch.Success)
        {
            fields["TwelfthPercentage"] = percMatch.Groups[1].Value.Trim();
        }
    }
    
    private void ExtractParentOccupationalDetails(string text, Dictionary<string, string?> fields)
    {
        // Mother's Occupation
        var motherOccMatch = FieldPatterns.MotherOccupation.Match(text);
        if (motherOccMatch.Success)
        {
            fields["MotherOccupation"] = motherOccMatch.Groups[1].Value.Trim();
        }
        
        // Mother's Mobile
        var motherPhoneMatch = FieldPatterns.MotherMobile.Match(text);
        if (motherPhoneMatch.Success)
        {
            fields["MotherMobile"] = OcrErrorCorrector.CorrectPhone(motherPhoneMatch.Groups[1].Value);
        }
        
        // Mother's Email
        var motherEmailMatch = FieldPatterns.MotherEmail.Match(text);
        if (motherEmailMatch.Success)
        {
            fields["MotherEmail"] = OcrErrorCorrector.CorrectEmail(motherEmailMatch.Groups[1].Value);
        }
        
        // Father's Occupation
        var fatherOccMatch = FieldPatterns.FatherOccupation.Match(text);
        if (fatherOccMatch.Success)
        {
            fields["FatherOccupation"] = fatherOccMatch.Groups[1].Value.Trim();
        }
        
        // Father's Mobile
        var fatherPhoneMatch = FieldPatterns.FatherMobile.Match(text);
        if (fatherPhoneMatch.Success)
        {
            fields["FatherMobile"] = OcrErrorCorrector.CorrectPhone(fatherPhoneMatch.Groups[1].Value);
        }
        
        // Father's Email
        var fatherEmailMatch = FieldPatterns.FatherEmail.Match(text);
        if (fatherEmailMatch.Success)
        {
            fields["FatherEmail"] = OcrErrorCorrector.CorrectEmail(fatherEmailMatch.Groups[1].Value);
        }
        
        // Guardian's Name
        var guardianMatch = FieldPatterns.GuardianName.Match(text);
        if (guardianMatch.Success)
        {
            var name = OcrErrorCorrector.CorrectName(guardianMatch.Groups[1].Value);
            if (!string.IsNullOrEmpty(name) && !FieldPatterns.IsFormLabel(name))
            {
                fields["GuardianName"] = name;
            }
        }
        
        // Guardian's Mobile
        var guardianPhoneMatch = FieldPatterns.GuardianMobile.Match(text);
        if (guardianPhoneMatch.Success)
        {
            fields["GuardianMobile"] = OcrErrorCorrector.CorrectPhone(guardianPhoneMatch.Groups[1].Value);
        }
        
        // DU Enrollment Number
        var duEnrollMatch = FieldPatterns.DuEnrollmentNumber.Match(text);
        if (duEnrollMatch.Success)
        {
            fields["DuEnrollmentNumber"] = duEnrollMatch.Groups[1].Value.Trim();
        }
        
        // Hindi Medium Preference
        var hindiMedMatch = FieldPatterns.HindiMediumPreference.Match(text);
        if (hindiMedMatch.Success)
        {
            var pref = hindiMedMatch.Groups[1].Value.Trim().ToUpper();
            fields["HindiMediumPreference"] = (pref == "Y" || pref == "YES") ? "Yes" : "No";
        }
    }
    
    private void ExtractDocumentChecklist(string text, Dictionary<string, string?> fields)
    {
        // Check for tick marks indicating attached documents
        var tickMarks = new[] { "☑", "☒", "✔", "√" };
        var attachedDocs = new List<string>();
        
        // Check each document pattern
        if (FieldPatterns.DocAdmissionForm.IsMatch(text))
        {
            fields["DocAdmissionForm"] = "Yes";
            attachedDocs.Add("Admission Form");
        }
        
        if (FieldPatterns.DocUndertakingRagging.IsMatch(text))
        {
            fields["DocUndertakingRagging"] = "Yes";
            attachedDocs.Add("Anti-Ragging Undertaking");
        }
        
        if (FieldPatterns.DocPhotographs.IsMatch(text))
        {
            fields["DocPhotographs"] = "Yes";
            attachedDocs.Add("Photographs");
        }
        
        if (FieldPatterns.DocCuetScorecard.IsMatch(text))
        {
            fields["DocCuetScorecard"] = "Yes";
            attachedDocs.Add("CUET Score Card");
        }
        
        if (FieldPatterns.DocClassXiiMarksheet.IsMatch(text))
        {
            fields["DocClassXiiMarksheet"] = "Yes";
            attachedDocs.Add("Class XII Mark Sheet");
        }
        
        if (attachedDocs.Count > 0)
        {
            fields["DocumentsAttached"] = string.Join(", ", attachedDocs);
        }
    }
    
    #endregion
    
    #region Cleanup and Validation
    
    private void CleanupExtractedValues(Dictionary<string, string?> fields)
    {
        var keysToUpdate = new List<(string key, string? value)>();
        
        foreach (var (key, value) in fields)
        {
            if (string.IsNullOrWhiteSpace(value)) continue;
            
            var cleaned = value.Trim();
            
            // Remove trailing garbage
            cleaned = Regex.Replace(cleaned, @"\s*\n.*$", "");
            cleaned = Regex.Replace(cleaned, @"\s*(Category|Father|Mother|Guardian|Details|Mobile Number|Email|Phone|Address)$", "", RegexOptions.IgnoreCase);
            
            // Remove "block letters" text from anywhere
            cleaned = Regex.Replace(cleaned, @"(?:name\s+)?in\s+block\s+letters", "", RegexOptions.IgnoreCase);
            cleaned = Regex.Replace(cleaned, @"block\s+letters", "", RegexOptions.IgnoreCase);
            
            cleaned = cleaned.Trim();
            
            if (cleaned.Length >= 2 && !FieldPatterns.IsFormLabel(cleaned))
            {
                keysToUpdate.Add((key, cleaned));
            }
            else
            {
                keysToUpdate.Add((key, null));
            }
        }
        
        foreach (var (key, value) in keysToUpdate)
        {
            if (value == null)
                fields.Remove(key);
            else
                fields[key] = value;
        }
    }
    
    private void CrossValidateAndCorrect(Dictionary<string, string?> fields)
    {
        // Phone number validation - ensure uniqueness
        var phoneFields = new[] { "PhoneNumber", "FatherMobile", "MotherMobile", "GuardianMobile" };
        var seenPhones = new HashSet<string>();
        
        foreach (var field in phoneFields)
        {
            if (fields.TryGetValue(field, out var phone) && !string.IsNullOrEmpty(phone))
            {
                if (seenPhones.Contains(phone) && field != "PhoneNumber")
                {
                    fields.Remove(field);
                }
                else
                {
                    seenPhones.Add(phone);
                }
            }
        }
        
        // CUET Score validation
        if (fields.TryGetValue("CuetScore", out var cuetScore) && !string.IsNullOrEmpty(cuetScore))
        {
            if (float.TryParse(cuetScore, out var score))
            {
                if (score < 100 || score > 1000)
                {
                    fields.Remove("CuetScore");
                }
            }
        }
        
        // Populate correspondence fields if not set
        if (fields.TryGetValue("PermanentAddress", out var permAddr) && 
            !fields.ContainsKey("CorrespondenceAddress"))
        {
            fields["CorrespondenceAddress"] = permAddr;
        }
        
        if (fields.TryGetValue("PermanentState", out var permState) && 
            !fields.ContainsKey("CorrespondenceState"))
        {
            fields["CorrespondenceState"] = permState;
        }
        
        if (fields.TryGetValue("PermanentPincode", out var permPin) && 
            !fields.ContainsKey("CorrespondencePincode"))
        {
            fields["CorrespondencePincode"] = permPin;
        }
    }
    
    private void ApplyFieldMappings(Dictionary<string, string?> fields)
    {
        // Create mapped fields for backward compatibility
        var mappings = new Dictionary<string, string>
        {
            { "PermanentState", "State" },
            { "DuPortalFormNumber", "ApplicationNumber" },
            { "CollegeRollNo", "EnrollmentNumber" },
            { "Course", "CourseApplied" },
            { "Category", "AdmissionCategory" },
            { "Pincode", "PermanentPincode" },
            { "TwelfthYear", "YearOfPassing" },
            { "TwelfthBoard", "BoardUniversity" },
            { "TwelfthRollNumber", "ExamRollNo" },
            { "TwelfthInstitution", "InstitutionLastAttended" }
        };
        
        foreach (var (source, target) in mappings)
        {
            if (fields.TryGetValue(source, out var value) && !string.IsNullOrEmpty(value))
            {
                if (!fields.ContainsKey(target) || string.IsNullOrEmpty(fields[target]))
                {
                    fields[target] = value;
                }
            }
        }
    }
    
    #endregion
}
