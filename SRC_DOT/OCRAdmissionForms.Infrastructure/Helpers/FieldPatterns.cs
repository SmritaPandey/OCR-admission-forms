using System.Text.RegularExpressions;
using System.Collections.Generic;

namespace OCRAdmissionForms.Infrastructure.Helpers;

/// <summary>
/// Contains all field extraction patterns for SRCC admission forms.
/// Ported from the Python backend srcc_form_extractor.py
/// </summary>
public static class FieldPatterns
{
    // ============================================
    // ACADEMIC & ADMISSION PATTERNS
    // ============================================
    
    public static readonly Regex AcademicSession = new(
        @"(?:Academic\s*Session|Session)\s*[:.]?\s*(\d{4}[-/]\d{2,4})",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    public static readonly Regex Course = new(
        @"(?:Course|Programme)\s*[:.]?\s*(B\.?\s*(?:COM|Com)\s*\.?\s*\(?H\)?|B\.?\s*A\.?\s*\(?H\)?\s*(?:ECO|Eco))",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    public static readonly Regex AdmissionCategory = new(
        @"(?:Admission\s*Category|Category)\s*[:.]?\s*(GEN|OBC|SC|ST|Sports|PWD|PwBD|EWS|Foreign|CW|KM|ECA|Others?)",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    public static readonly Regex DuPortalFormNumber = new(
        @"(?:DU\s*Portal\s*(?:Form\s*)?(?:No\.?|Number)|Form\s*No\.?|Application\s*No\.?)\s*[:.]?\s*(\d{10,14})",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    public static readonly Regex CuetScore = new(
        @"(?:CUET\s*(?:Total\s*)?Score|Total\s*Score)\s*[:.]?\s*(\d+(?:\.\d+)?)",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    public static readonly Regex CollegeRollNo = new(
        @"(?:College\s*Roll\s*No\.?|Roll\s*No\.?)\s*[:.]?\s*(\d{2}[A-Z]{2,3}\d{2,4}|\d+[A-Z]+\d+)",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    public static readonly Regex DateOfAdmission = new(
        @"(?:Date\s*of\s*Admission|Admission\s*Date)\s*[:.]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    // ============================================
    // PERSONAL DETAILS PATTERNS
    // ============================================
    
    public static readonly Regex StudentName = new(
        @"(?:1\s*\.\s*)?(?:Student\s*)?Name\s*(?:in\s*block\s*letters)?\s*[:.]?\s*([A-Z][A-Za-z\s]+?)(?=\s*(?:First|Middle|Surname|Gender|Male|Female|\d|$))",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    public static readonly Regex FirstName = new(
        @"First\s*Name\s*[:.]?\s*([A-Za-z]+)",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    public static readonly Regex MiddleName = new(
        @"Middle\s*Name\s*[:.]?\s*([A-Za-z]+)",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    public static readonly Regex Surname = new(
        @"Surname\s*[:.]?\s*([A-Za-z]+)",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    public static readonly Regex Gender = new(
        @"(?:2\s*\.\s*)?(?:Gender|Sex)\s*[:.]?\s*(Male|Female|Transgender|M|F|T)",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    public static readonly Regex DateOfBirth = new(
        @"(?:3\s*\.\s*)?(?:Date\s*of\s*Birth|DOB|D\.O\.B)\s*[:.]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    public static readonly Regex Category = new(
        @"(?:Category|Caste)\s*[:.]?\s*(General|GEN|OBC|SC|ST|EWS|Other)",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    public static readonly Regex Nationality = new(
        @"(?:12\s*\(a\)\s*)?Nationality\s*[:.]?\s*([A-Za-z]+)",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    public static readonly Regex Religion = new(
        @"(?:12\s*\(b\)\s*)?Religion\s*[:.]?\s*([A-Za-z]+)",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    public static readonly Regex BloodGroup = new(
        @"(?:12\s*\(c\)\s*)?Blood\s*Group\s*[:.]?\s*([ABO][+-]?|AB[+-]?)",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    public static readonly Regex AadharNumber = new(
        @"(?:Aadhar|Aadhaar|UID)\s*(?:No\.?|Number)?\s*[:.]?\s*(\d{4}\s*\d{4}\s*\d{4}|\d{12})",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    public static readonly Regex BelowPovertyLine = new(
        @"(?:12\s*\(d\)\s*)?(?:Whether\s*)?Below\s*Poverty\s*Line\s*[:.]?\s*(Yes|No|Y|N)",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    public static readonly Regex AnnualIncome = new(
        @"(?:12\s*\(e\)\s*)?(?:Parent['']?s?\s*/?\s*Family\s*)?Annual\s*Income\s*[:.]?\s*(?:Rs\.?\s*)?(\d[\d,]+)",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    public static readonly Regex MinorityCategory = new(
        @"(?:12\s*\(f\)\s*)?(?:Whether\s*belongs?\s*to\s*)?Minority\s*[:.]?\s*(Muslim|Jain|Sikh|Persian|Christian|Buddhist|Others?|Yes|No)",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    // ============================================
    // ADDRESS PATTERNS
    // ============================================
    
    public static readonly Regex PermanentAddress = new(
        @"(?:4\s*\.\s*)?Permanent\s*Address\s*[:.]?\s*(.+?)(?=(?:State|PIN|Correspondence|Local|5\s*\.|$))",
        RegexOptions.IgnoreCase | RegexOptions.Singleline | RegexOptions.Compiled);
    
    public static readonly Regex PermanentState = new(
        @"State\s*[:.]?\s*([A-Za-z\s]+?)(?=\s*(?:PIN|Pincode|\d{6}|$))",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    public static readonly Regex Pincode = new(
        @"(?:PIN|Pincode)\s*[:.]?\s*(\d{6})",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    public static readonly Regex CorrespondenceAddress = new(
        @"(?:5\s*\.\s*)?(?:Local\s*Address\s*for\s*)?Correspondence\s*(?:Address)?\s*[:.]?\s*(.+?)(?=(?:State|PIN|Email|6\s*\.|$))",
        RegexOptions.IgnoreCase | RegexOptions.Singleline | RegexOptions.Compiled);
    
    // ============================================
    // CONTACT PATTERNS
    // ============================================
    
    public static readonly Regex Email = new(
        @"(?:6\s*\.\s*)?E-?mail\s*(?:ID|Address)?\s*[:.]?\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    public static readonly Regex PhoneNumber = new(
        @"(?:7\s*\.\s*)?(?:Contact\s*(?:No\.?|Number)|Phone|Mobile)\s*[:.]?\s*(?:\+91\s*)?([6-9]\d{9})",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    public static readonly Regex IndianPhone = new(
        @"(?:\+91\s*)?([6-9]\d{9})",
        RegexOptions.Compiled);
    
    // ============================================
    // PARENT DETAILS PATTERNS
    // ============================================
    
    public static readonly Regex MotherName = new(
        @"(?:8\s*\.\s*)?Mother['']?s?\s*Name\s*[:.]?\s*([A-Za-z\s]+?)(?=\s*(?:Father|9\s*\.|Occupation|$))",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    public static readonly Regex FatherName = new(
        @"(?:9\s*\.\s*)?Father['']?s?\s*Name\s*[:.]?\s*([A-Za-z\s]+?)(?=\s*(?:10\s*\.|CUET|Occupation|$))",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    public static readonly Regex MotherOccupation = new(
        @"(?:13\s*\(a\)\s*)?Mother['']?s?\s*Occupation\s*[:.]?\s*([A-Za-z\s]+?)(?=\s*(?:Designation|13\s*\(b\)|$))",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    public static readonly Regex FatherOccupation = new(
        @"(?:14\s*\(a\)\s*)?Father['']?s?\s*Occupation\s*[:.]?\s*([A-Za-z\s]+?)(?=\s*(?:Designation|14\s*\(b\)|$))",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    public static readonly Regex MotherMobile = new(
        @"(?:13\s*\(e\)\s*)?Mother['']?s?\s*(?:Mobile|Phone|Contact)\s*(?:No\.?)?\s*[:.]?\s*(?:\+91\s*)?([6-9]\d{9})",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    public static readonly Regex FatherMobile = new(
        @"(?:14\s*\(e\)\s*)?Father['']?s?\s*(?:Mobile|Phone|Contact)\s*(?:No\.?)?\s*[:.]?\s*(?:\+91\s*)?([6-9]\d{9})",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    public static readonly Regex MotherEmail = new(
        @"(?:13\s*\(d\)\s*)?Mother['']?s?\s*E-?mail\s*[:.]?\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    public static readonly Regex FatherEmail = new(
        @"(?:14\s*\(d\)\s*)?Father['']?s?\s*E-?mail\s*[:.]?\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    // ============================================
    // GUARDIAN PATTERNS
    // ============================================
    
    public static readonly Regex GuardianName = new(
        @"(?:15\s*\(a\)\s*)?(?:Local\s*)?Guardian['']?s?\s*Name\s*[:.]?\s*([A-Za-z\s]+?)(?=\s*(?:Address|15\s*\(b\)|$))",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    public static readonly Regex GuardianMobile = new(
        @"(?:15\s*\(e\)\s*)?Guardian['']?s?\s*(?:Mobile|Phone|Contact)\s*(?:No\.?)?\s*[:.]?\s*(?:\+91\s*)?([6-9]\d{9})",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    public static readonly Regex GuardianRelation = new(
        @"(?:Relationship|Relation)\s*[:.]?\s*([A-Za-z\s]+)",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    // ============================================
    // CLASS XII DETAILS PATTERNS
    // ============================================
    
    public static readonly Regex TwelfthYear = new(
        @"(?:11\s*\(a\)\s*)?(?:Year\s*of\s*(?:Passing|Pass)|XII\s*Year)\s*[:.]?\s*(\d{4})",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    public static readonly Regex TwelfthBoard = new(
        @"(?:11\s*\(b\)\s*)?(?:Board|University)\s*[:.]?\s*(CBSE|ICSE|ISC|State\s*Board|[A-Za-z\s]+Board)",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    public static readonly Regex TwelfthRollNumber = new(
        @"(?:11\s*\(c\)\s*)?(?:Exam(?:ination)?\s*)?Roll\s*No\.?\s*[:.]?\s*(\d+)",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    public static readonly Regex TwelfthInstitution = new(
        @"(?:11\s*\(d\)\s*)?Institution\s*(?:Last\s*)?Attended\s*[:.]?\s*([A-Za-z0-9\s,.-]+?)(?=\s*(?:Hindi|11\s*\(e\)|$))",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    public static readonly Regex HindiStudiedUpto = new(
        @"(?:11\s*\(e\)\s*)?Hindi\s*(?:studied\s*)?(?:up\s*to|upto)\s*[:.]?\s*(VIII|X|XII|Never|8th|10th|12th)",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    public static readonly Regex TwelfthPercentage = new(
        @"(?:XII|12th)\s*(?:Percentage|%|Marks)\s*[:.]?\s*(\d+(?:\.\d+)?)",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    // ============================================
    // OTHER DETAILS PATTERNS
    // ============================================
    
    public static readonly Regex DuEnrollmentNumber = new(
        @"(?:16\s*\(a\)\s*)?(?:Delhi\s*University|DU)\s*Enrol(?:l)?ment\s*(?:No\.?|Number)\s*[:.]?\s*([A-Z0-9]+)",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    public static readonly Regex HindiMediumPreference = new(
        @"(?:16\s*\(b\)\s*)?Hindi\s*(?:medium\s*)?(?:preference|instruction)\s*[:.]?\s*(Yes|No|Y|N)",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    // ============================================
    // CERTIFICATE DETAILS PATTERNS
    // ============================================
    
    public static readonly Regex CategoryCertificateAuthority = new(
        @"(?:17\s*\.?\s*)?(?:Certificate\s*)?(?:Issuing\s*)?Authority\s*[:.]?\s*([A-Za-z0-9\s,.-]+?)(?=\s*(?:Certificate\s*No|17|$))",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    public static readonly Regex CategoryCertificateNumber = new(
        @"Certificate\s*No\.?\s*[:.]?\s*([A-Z0-9/-]+)",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    public static readonly Regex DisabilityPercentage = new(
        @"(?:Extent\s*of\s*)?Disability\s*(?:\(%\))?\s*[:.]?\s*(\d+(?:\.\d+)?)\s*%?",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    public static readonly Regex DisabilityType = new(
        @"(?:Type\s*of\s*)?Disability\s*[:.]?\s*(VH|HH|OH|Visual|Hearing|Ortho)",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    public static readonly Regex UdidNumber = new(
        @"UDID\s*(?:No\.?)?\s*[:.]?\s*([A-Z0-9]+)",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    // ============================================
    // DOCUMENT CHECKLIST PATTERNS
    // ============================================
    
    public static readonly Regex DocAdmissionForm = new(
        @"(?:1\s*\.|Printed)\s*Admission\s*/?Registration\s*Form.*?(☑|☒|✔|√|Yes)",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    public static readonly Regex DocUndertakingRagging = new(
        @"(?:2\s*\.|Undertaking)\s*(?:for\s*)?(?:curbing\s*)?ragging.*?(☑|☒|✔|√|Yes)",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    public static readonly Regex DocPhotographs = new(
        @"(?:3\s*\.|Photographs?)\s*pasted.*?(☑|☒|✔|√|Yes)",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    public static readonly Regex DocCuetScorecard = new(
        @"CUET\s*Score\s*Card.*?(☑|☒|✔|√|Yes)",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    public static readonly Regex DocClassXiiMarksheet = new(
        @"(?:Mark\s*Sheet|Marksheet)\s*(?:of\s*)?(?:class\s*)?XII.*?(☑|☒|✔|√|Yes)",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    public static readonly Regex DocClassXCertificate = new(
        @"Certificate.*?(?:class\s*)?X(?:\s|$).*?(☑|☒|✔|√|Yes)",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    public static readonly Regex DocClassXiiCertificate = new(
        @"(?:Provisional\s*)?Certificate.*?(?:class\s*)?XII.*?(☑|☒|✔|√|Yes)",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    
    // ============================================
    // GARBAGE/LABEL PATTERNS TO REJECT
    // ============================================
    
    public static readonly HashSet<string> RejectLabels = new(StringComparer.OrdinalIgnoreCase)
    {
        "name in block letters", "in block letters", "block letters",
        "first name", "middle name", "surname", "name",
        "date of birth", "gender", "sex", "male", "female", "transgender",
        "permanent address", "correspondence address", "local address",
        "state", "pin", "pincode", "email", "phone", "contact", "mobile",
        "mother", "father", "guardian", "occupation", "designation",
        "organization", "signature", "category", "details",
        "student", "tick", "applicable", "vihar", "nagar", "colony",
        "enclave", "park", "road", "street", "sector", "block"
    };
    
    public static readonly HashSet<string> AddressWords = new(StringComparer.OrdinalIgnoreCase)
    {
        "vihar", "nagar", "colony", "enclave", "park", "road", "street",
        "lane", "sector", "house", "flat", "flats", "floor", "apartment",
        "block", "phase", "pocket", "plot", "extension", "ext"
    };
    
    /// <summary>
    /// Check if a value looks like a form label rather than actual data
    /// </summary>
    public static bool IsFormLabel(string value)
    {
        if (string.IsNullOrWhiteSpace(value)) return true;
        
        var lower = value.ToLower().Trim();
        
        // Check exact matches
        if (RejectLabels.Contains(lower)) return true;
        
        // Check if it contains "block letters" anywhere
        if (lower.Contains("block letters")) return true;
        
        // Check if it's just punctuation or single char
        if (value.Length < 2) return true;
        
        return false;
    }
}
