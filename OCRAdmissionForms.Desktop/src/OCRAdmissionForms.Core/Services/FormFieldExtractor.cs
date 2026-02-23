using System.Text.RegularExpressions;
using OCRAdmissionForms.Core.Entities;

namespace OCRAdmissionForms.Core.Services;

/// <summary>
/// Enhanced form field extractor with 50+ patterns for SRCC admission forms
/// Ported from Python backend srcc_form_extractor.py
/// </summary>
public class FormFieldExtractor
{
    // ============================================
    // COMPILED REGEX PATTERNS
    // ============================================
    
    #region Academic & Admission Patterns
    
    private static readonly Regex[] AcademicSessionPatterns = {
        new(@"(?:Academic\s*Session|Session)\s*[:.]?\s*(\d{4}[-/]\d{2,4})", RegexOptions.IgnoreCase | RegexOptions.Compiled),
        new(@"(\d{4}[-/]\d{2,4})\s*(?:session|academic)", RegexOptions.IgnoreCase | RegexOptions.Compiled)
    };
    
    private static readonly Regex[] CoursePatterns = {
        new(@"(?:Course|Programme)\s*[:.]?\s*(B\.?\s*(?:COM|Com)\.?\s*\(?H\)?)", RegexOptions.IgnoreCase | RegexOptions.Compiled),
        new(@"(B\.?\s*A\.?\s*\(?H\)?\s*(?:ECO|Eco|Economics)?)", RegexOptions.IgnoreCase | RegexOptions.Compiled),
        new(@"(B\.?Com\.?\s*\(Hons?\.\?\))", RegexOptions.IgnoreCase | RegexOptions.Compiled)
    };
    
    private static readonly Regex[] CollegeRollNoPatterns = {
        new(@"(?:College\s*Roll\s*No\.?|Roll\s*No\.?)\s*[:.]?\s*(\d{2}[A-Z]{2,3}\d{2,4})", RegexOptions.IgnoreCase | RegexOptions.Compiled),
        new(@"Roll\s*(?:No\.?|Number)\s*[:.]?\s*(\d+[A-Z]+\d+)", RegexOptions.IgnoreCase | RegexOptions.Compiled),
        new(@"(\d{2}[A-Z]{2,3}\d{3,4})", RegexOptions.Compiled)
    };
    
    private static readonly Regex[] DuPortalFormPatterns = {
        new(@"(?:DU\s*Portal\s*(?:Form\s*)?(?:No\.?|Number)|Application\s*No\.?)\s*[:.]?\s*(\d{10,14})", RegexOptions.IgnoreCase | RegexOptions.Compiled),
        new(@"Form\s*No\.?\s*[:.]?\s*(\d{10,})", RegexOptions.IgnoreCase | RegexOptions.Compiled)
    };
    
    private static readonly Regex[] CuetScorePatterns = {
        new(@"(?:CUET\s*(?:Total\s*)?Score|Total\s*Score)\s*[:.]?\s*(\d+(?:\.\d+)?)", RegexOptions.IgnoreCase | RegexOptions.Compiled),
        new(@"Score\s*[:.]?\s*(\d{2,3}(?:\.\d+)?)", RegexOptions.IgnoreCase | RegexOptions.Compiled)
    };
    
    private static readonly Regex[] AdmissionCategoryPatterns = {
        new(@"(?:Admission\s*)?Category\s*[:.]?\s*(GEN|OBC|SC|ST|EWS|Sports|PWD|PwBD|Foreign|CW|KM|ECA)", RegexOptions.IgnoreCase | RegexOptions.Compiled)
    };
    
    private static readonly Regex[] DateOfAdmissionPatterns = {
        new(@"(?:Date\s*of\s*Admission|Admission\s*Date)\s*[:.]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", RegexOptions.IgnoreCase | RegexOptions.Compiled)
    };
    
    #endregion
    
    #region Personal Details Patterns
    
    private static readonly Regex[] StudentNamePatterns = {
        new(@"(?:Student\s*)?Name\s*(?:in\s*block\s*letters)?\s*[:.]?\s*([A-Z][A-Za-z\s]+?)(?=\s*(?:First|Gender|Male|Female|\d|Father|Mother|$))", RegexOptions.IgnoreCase | RegexOptions.Compiled),
        new(@"Name\s*[:.]?\s*([A-Z][A-Z\s]+)(?=\s)", RegexOptions.Compiled)
    };
    
    private static readonly Regex[] FirstNamePatterns = {
        new(@"First\s*Name\s*[:.]?\s*([A-Za-z]+)", RegexOptions.IgnoreCase | RegexOptions.Compiled)
    };
    
    private static readonly Regex[] MiddleNamePatterns = {
        new(@"Middle\s*Name\s*[:.]?\s*([A-Za-z]+)", RegexOptions.IgnoreCase | RegexOptions.Compiled)
    };
    
    private static readonly Regex[] SurnamePatterns = {
        new(@"Surname\s*[:.]?\s*([A-Za-z]+)", RegexOptions.IgnoreCase | RegexOptions.Compiled)
    };
    
    private static readonly Regex[] GenderPatterns = {
        new(@"(?:Gender|Sex)\s*[:.]?\s*(Male|Female|Transgender|M|F)", RegexOptions.IgnoreCase | RegexOptions.Compiled)
    };
    
    private static readonly Regex[] DateOfBirthPatterns = {
        new(@"(?:Date\s*of\s*Birth|DOB|D\.O\.B)\s*[:.]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", RegexOptions.IgnoreCase | RegexOptions.Compiled)
    };
    
    private static readonly Regex[] CategoryPatterns = {
        new(@"(?:Category|Caste)\s*[:.]?\s*(General|GEN|OBC|SC|ST|EWS)", RegexOptions.IgnoreCase | RegexOptions.Compiled)
    };
    
    private static readonly Regex[] NationalityPatterns = {
        new(@"Nationality\s*[:.]?\s*([A-Za-z]+)", RegexOptions.IgnoreCase | RegexOptions.Compiled)
    };
    
    private static readonly Regex[] ReligionPatterns = {
        new(@"Religion\s*[:.]?\s*([A-Za-z]+)", RegexOptions.IgnoreCase | RegexOptions.Compiled)
    };
    
    private static readonly Regex[] BloodGroupPatterns = {
        new(@"Blood\s*Group\s*[:.]?\s*([ABO][+-]?|AB[+-]?)", RegexOptions.IgnoreCase | RegexOptions.Compiled)
    };
    
    private static readonly Regex[] AadharPatterns = {
        new(@"(?:Aadhar|Aadhaar|UID)\s*(?:No\.?|Number)?\s*[:.]?\s*(\d{4}\s*\d{4}\s*\d{4})", RegexOptions.IgnoreCase | RegexOptions.Compiled),
        new(@"(\d{12})", RegexOptions.Compiled)
    };
    
    #endregion
    
    #region Address & Contact Patterns
    
    private static readonly Regex[] PermanentAddressPatterns = {
        new(@"Permanent\s*Address\s*[:.]?\s*(.+?)(?=\s*(?:State|PIN|Correspondence|Local|$))", RegexOptions.IgnoreCase | RegexOptions.Singleline | RegexOptions.Compiled)
    };
    
    private static readonly Regex[] PermanentStatePatterns = {
        new(@"State\s*[:.]?\s*([A-Za-z\s]+?)(?=\s*(?:PIN|Pincode|\d{6}|$))", RegexOptions.IgnoreCase | RegexOptions.Compiled)
    };
    
    private static readonly Regex[] PincodePatterns = {
        new(@"(?:PIN|Pincode)\s*[:.]?\s*(\d{6})", RegexOptions.IgnoreCase | RegexOptions.Compiled),
        new(@"(\d{6})(?:\s|$)", RegexOptions.Compiled)
    };
    
    private static readonly Regex[] CorrespondenceAddressPatterns = {
        new(@"(?:Local\s*Address|Correspondence)\s*(?:Address)?\s*[:.]?\s*(.+?)(?=\s*(?:State|PIN|Email|$))", RegexOptions.IgnoreCase | RegexOptions.Singleline | RegexOptions.Compiled)
    };
    
    private static readonly Regex[] EmailPatterns = {
        new(@"E-?mail\s*(?:ID|Address)?\s*[:.]?\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", RegexOptions.IgnoreCase | RegexOptions.Compiled),
        new(@"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", RegexOptions.Compiled)
    };
    
    private static readonly Regex[] PhonePatterns = {
        new(@"(?:Contact|Phone|Mobile)\s*(?:No\.?|Number)?\s*[:.]?\s*(?:\+91\s*)?([6-9]\d{9})", RegexOptions.IgnoreCase | RegexOptions.Compiled),
        new(@"(?:\+91\s*)?([6-9]\d{9})", RegexOptions.Compiled)
    };
    
    private static readonly Regex[] AlternatePhonePatterns = {
        new(@"(?:Alternate|Alt\.?|Other)\s*(?:Phone|Mobile|Contact)\s*[:.]?\s*(?:\+91\s*)?([6-9]\d{9})", RegexOptions.IgnoreCase | RegexOptions.Compiled)
    };
    
    #endregion
    
    #region Parent Details Patterns
    
    private static readonly Regex[] FatherNamePatterns = {
        new(@"Father['']?s?\s*Name\s*[:.]?\s*([A-Za-z\s]+?)(?=\s*(?:Mother|Occupation|CUET|\d|$))", RegexOptions.IgnoreCase | RegexOptions.Compiled)
    };
    
    private static readonly Regex[] MotherNamePatterns = {
        new(@"Mother['']?s?\s*Name\s*[:.]?\s*([A-Za-z\s]+?)(?=\s*(?:Father|Occupation|\d|$))", RegexOptions.IgnoreCase | RegexOptions.Compiled)
    };
    
    private static readonly Regex[] FatherOccupationPatterns = {
        new(@"Father['']?s?\s*Occupation\s*[:.]?\s*([A-Za-z\s]+?)(?=\s*(?:Designation|Mother|\d|$))", RegexOptions.IgnoreCase | RegexOptions.Compiled)
    };
    
    private static readonly Regex[] MotherOccupationPatterns = {
        new(@"Mother['']?s?\s*Occupation\s*[:.]?\s*([A-Za-z\s]+?)(?=\s*(?:Designation|Father|\d|$))", RegexOptions.IgnoreCase | RegexOptions.Compiled)
    };
    
    private static readonly Regex[] FatherMobilePatterns = {
        new(@"Father['']?s?\s*(?:Mobile|Phone|Contact)\s*(?:No\.?)?\s*[:.]?\s*(?:\+91\s*)?([6-9]\d{9})", RegexOptions.IgnoreCase | RegexOptions.Compiled)
    };
    
    private static readonly Regex[] MotherMobilePatterns = {
        new(@"Mother['']?s?\s*(?:Mobile|Phone|Contact)\s*(?:No\.?)?\s*[:.]?\s*(?:\+91\s*)?([6-9]\d{9})", RegexOptions.IgnoreCase | RegexOptions.Compiled)
    };
    
    #endregion
    
    #region Education Patterns
    
    private static readonly Regex[] TwelfthYearPatterns = {
        new(@"(?:Year\s*of\s*(?:Passing|Pass)|XII\s*Year)\s*[:.]?\s*(\d{4})", RegexOptions.IgnoreCase | RegexOptions.Compiled),
        new(@"Passing\s*[:.]?\s*(\d{4})", RegexOptions.IgnoreCase | RegexOptions.Compiled)
    };
    
    private static readonly Regex[] TwelfthBoardPatterns = {
        new(@"(?:Board|University)\s*[:.]?\s*(CBSE|ICSE|ISC|State\s*Board|[A-Za-z\s]+Board)", RegexOptions.IgnoreCase | RegexOptions.Compiled)
    };
    
    private static readonly Regex[] TwelfthPercentagePatterns = {
        new(@"(?:XII|12th)?\s*(?:Percentage|%|Marks)\s*[:.]?\s*(\d+(?:\.\d+)?)\s*%?", RegexOptions.IgnoreCase | RegexOptions.Compiled),
        new(@"(\d{2}\.\d+)\s*%", RegexOptions.Compiled)
    };
    
    private static readonly Regex[] TwelfthInstitutionPatterns = {
        new(@"Institution\s*(?:Last\s*)?Attended\s*[:.]?\s*([A-Za-z0-9\s,.-]+?)(?=\s*(?:Hindi|Board|$))", RegexOptions.IgnoreCase | RegexOptions.Compiled)
    };
    
    #endregion

    /// <summary>
    /// Extract all fields from OCR text and populate the form
    /// </summary>
    public AdmissionForm ExtractFields(string ocrText, AdmissionForm form)
    {
        if (string.IsNullOrWhiteSpace(ocrText)) return form;
        
        // Normalize text
        var text = NormalizeText(ocrText);
        
        // Academic & Admission
        form.AcademicSession = ExtractFirst(text, AcademicSessionPatterns);
        form.Course = ExtractFirst(text, CoursePatterns);
        form.CollegeRollNo = ExtractFirst(text, CollegeRollNoPatterns);
        form.DuPortalFormNumber = ExtractFirst(text, DuPortalFormPatterns);
        form.CuetScore = ExtractFirst(text, CuetScorePatterns);
        form.AdmissionCategory = ExtractFirst(text, AdmissionCategoryPatterns);
        form.DateOfAdmission = OcrErrorCorrector.CorrectDate(ExtractFirst(text, DateOfAdmissionPatterns));
        
        // Personal Details
        form.StudentName = OcrErrorCorrector.CorrectName(ExtractFirst(text, StudentNamePatterns));
        form.FirstName = OcrErrorCorrector.CorrectName(ExtractFirst(text, FirstNamePatterns));
        form.MiddleName = OcrErrorCorrector.CorrectName(ExtractFirst(text, MiddleNamePatterns));
        form.Surname = OcrErrorCorrector.CorrectName(ExtractFirst(text, SurnamePatterns));
        form.Gender = NormalizeGender(ExtractFirst(text, GenderPatterns));
        form.DateOfBirth = OcrErrorCorrector.CorrectDate(ExtractFirst(text, DateOfBirthPatterns));
        form.Category = ExtractFirst(text, CategoryPatterns)?.ToUpper();
        form.Nationality = OcrErrorCorrector.CorrectName(ExtractFirst(text, NationalityPatterns));
        form.Religion = OcrErrorCorrector.CorrectName(ExtractFirst(text, ReligionPatterns));
        form.BloodGroup = ExtractFirst(text, BloodGroupPatterns)?.ToUpper();
        form.AadharNumber = OcrErrorCorrector.CorrectAadhar(ExtractFirst(text, AadharPatterns));
        
        // Address & Contact
        form.PermanentAddress = OcrErrorCorrector.CleanText(ExtractFirst(text, PermanentAddressPatterns));
        form.PermanentState = OcrErrorCorrector.CorrectName(ExtractFirst(text, PermanentStatePatterns));
        form.PermanentPincode = OcrErrorCorrector.CorrectPincode(ExtractFirst(text, PincodePatterns));
        form.CorrespondenceAddress = OcrErrorCorrector.CleanText(ExtractFirst(text, CorrespondenceAddressPatterns));
        form.Email = OcrErrorCorrector.CorrectEmail(ExtractFirst(text, EmailPatterns));
        form.PhoneNumber = OcrErrorCorrector.CorrectPhoneNumber(ExtractFirst(text, PhonePatterns));
        form.AlternatePhone = OcrErrorCorrector.CorrectPhoneNumber(ExtractFirst(text, AlternatePhonePatterns));
        
        // Parent Details
        form.FatherName = OcrErrorCorrector.CorrectName(ExtractFirst(text, FatherNamePatterns));
        form.MotherName = OcrErrorCorrector.CorrectName(ExtractFirst(text, MotherNamePatterns));
        form.FatherOccupation = OcrErrorCorrector.CleanText(ExtractFirst(text, FatherOccupationPatterns));
        form.MotherOccupation = OcrErrorCorrector.CleanText(ExtractFirst(text, MotherOccupationPatterns));
        form.FatherMobile = OcrErrorCorrector.CorrectPhoneNumber(ExtractFirst(text, FatherMobilePatterns));
        form.MotherMobile = OcrErrorCorrector.CorrectPhoneNumber(ExtractFirst(text, MotherMobilePatterns));
        
        // Education Details
        form.TwelfthYear = ExtractFirst(text, TwelfthYearPatterns);
        form.TwelfthBoard = OcrErrorCorrector.CleanText(ExtractFirst(text, TwelfthBoardPatterns));
        form.TwelfthPercentage = OcrErrorCorrector.CorrectPercentage(ExtractFirst(text, TwelfthPercentagePatterns));
        form.TwelfthInstitution = OcrErrorCorrector.CleanText(ExtractFirst(text, TwelfthInstitutionPatterns));
        
        // Build full name if not found but parts exist
        if (string.IsNullOrEmpty(form.StudentName) && !string.IsNullOrEmpty(form.FirstName))
        {
            form.StudentName = string.Join(" ", new[] { form.FirstName, form.MiddleName, form.Surname }
                .Where(s => !string.IsNullOrWhiteSpace(s)));
        }
        
        // Copy pincode if only one found
        if (string.IsNullOrEmpty(form.Pincode) && !string.IsNullOrEmpty(form.PermanentPincode))
        {
            form.Pincode = form.PermanentPincode;
        }
        
        return form;
    }

    /// <summary>
    /// Extract fields from Python script JSON output (preferred method for OCR)
    /// Maps snake_case fields from Python to PascalCase entity properties
    /// </summary>
    public AdmissionForm ExtractFieldsFromJson(string jsonText, AdmissionForm form)
    {
        if (string.IsNullOrWhiteSpace(jsonText)) return form;
        
        try
        {
            // Try to parse as JSON with "fields" object (Python script output format)
            using var doc = System.Text.Json.JsonDocument.Parse(jsonText);
            var root = doc.RootElement;
            
            System.Text.Json.JsonElement fields;
            if (root.TryGetProperty("fields", out fields))
            {
                // Python script output: { "success": true, "fields": { ... } }
                MapFieldsFromJson(fields, form);
            }
            else
            {
                // Direct fields object
                MapFieldsFromJson(root, form);
            }
            
            return form;
        }
        catch (System.Text.Json.JsonException)
        {
            // Not JSON - fall back to regex extraction
            return ExtractFields(jsonText, form);
        }
    }
    
    private void MapFieldsFromJson(System.Text.Json.JsonElement fields, AdmissionForm form)
    {
        // ============================================
        // PERSONAL DETAILS — try PascalCase (new Gemini) then snake_case (legacy)
        // ============================================
        form.StudentName = GetJsonString(fields, "StudentName") ?? GetJsonString(fields, "student_name") ?? form.StudentName;
        form.FirstName = GetJsonString(fields, "FirstName") ?? GetJsonString(fields, "first_name") ?? form.FirstName;
        form.MiddleName = GetJsonString(fields, "MiddleName") ?? GetJsonString(fields, "middle_name") ?? form.MiddleName;
        form.Surname = GetJsonString(fields, "Surname") ?? GetJsonString(fields, "surname") ?? form.Surname;
        form.Gender = GetJsonString(fields, "Gender") ?? GetJsonString(fields, "gender") ?? form.Gender;
        form.DateOfBirth = GetJsonString(fields, "DateOfBirth") ?? GetJsonString(fields, "date_of_birth") ?? form.DateOfBirth;
        form.Category = GetJsonString(fields, "Category") ?? GetJsonString(fields, "category") ?? form.Category;
        form.Nationality = GetJsonString(fields, "Nationality") ?? GetJsonString(fields, "nationality") ?? form.Nationality;
        form.Religion = GetJsonString(fields, "Religion") ?? GetJsonString(fields, "religion") ?? form.Religion;
        form.BloodGroup = GetJsonString(fields, "BloodGroup") ?? GetJsonString(fields, "blood_group") ?? form.BloodGroup;
        form.AadharNumber = GetJsonString(fields, "AadharNumber") ?? GetJsonString(fields, "aadhar_number") ?? form.AadharNumber;
        form.BelowPovertyLine = GetJsonString(fields, "BelowPovertyLine") ?? GetJsonString(fields, "below_poverty_line") ?? form.BelowPovertyLine;
        form.AnnualIncome = GetJsonString(fields, "AnnualIncome") ?? GetJsonString(fields, "annual_income") ?? GetJsonString(fields, "family_annual_income") ?? form.AnnualIncome;

        form.MinorityCategory = GetJsonString(fields, "MinorityCategory") ?? GetJsonString(fields, "minority_category") ?? form.MinorityCategory;
        
        // ============================================
        // ACADEMIC DETAILS
        // ============================================
        form.AcademicSession = GetJsonString(fields, "AcademicSession") ?? GetJsonString(fields, "academic_session") ?? form.AcademicSession;
        form.Course = GetJsonString(fields, "Course") ?? GetJsonString(fields, "course") ?? form.Course;
        form.AdmissionCategory = GetJsonString(fields, "AdmissionCategory") ?? GetJsonString(fields, "admission_category") ?? GetJsonString(fields, "category") ?? form.AdmissionCategory;
        form.DuPortalFormNumber = GetJsonString(fields, "DuPortalFormNumber") ?? GetJsonString(fields, "du_portal_form_number") ?? form.DuPortalFormNumber;
        form.CuetScore = GetJsonString(fields, "CuetScore") ?? GetJsonString(fields, "cuet_score") ?? form.CuetScore;
        form.CollegeRollNo = GetJsonString(fields, "CollegeRollNo") ?? GetJsonString(fields, "college_roll_no") ?? form.CollegeRollNo;
        form.DateOfAdmission = GetJsonString(fields, "DateOfAdmission") ?? GetJsonString(fields, "date_of_admission") ?? form.DateOfAdmission;
        
        // ============================================
        // ADDRESS
        // ============================================
        form.PermanentAddress = GetJsonString(fields, "PermanentAddress") ?? GetJsonString(fields, "permanent_address") ?? form.PermanentAddress;
        form.PermanentState = GetJsonString(fields, "PermanentState") ?? GetJsonString(fields, "state") ?? GetJsonString(fields, "permanent_state") ?? form.PermanentState;
        form.PermanentPincode = GetJsonString(fields, "PermanentPincode") ?? GetJsonString(fields, "pincode") ?? GetJsonString(fields, "permanent_pincode") ?? form.PermanentPincode;
        form.Pincode = GetJsonString(fields, "PermanentPincode") ?? GetJsonString(fields, "pincode") ?? form.Pincode;
        form.CorrespondenceAddress = GetJsonString(fields, "CorrespondenceAddress") ?? GetJsonString(fields, "correspondence_address") ?? GetJsonString(fields, "local_address") ?? form.CorrespondenceAddress;
        form.LocalAddress = GetJsonString(fields, "LocalAddress") ?? GetJsonString(fields, "local_address") ?? form.LocalAddress;
        form.CorrespondenceState = GetJsonString(fields, "CorrespondenceState") ?? GetJsonString(fields, "correspondence_state") ?? form.CorrespondenceState;
        form.CorrespondencePincode = GetJsonString(fields, "CorrespondencePincode") ?? GetJsonString(fields, "correspondence_pincode") ?? form.CorrespondencePincode;
        
        // ============================================
        // CONTACT
        // ============================================
        form.Email = GetJsonString(fields, "Email") ?? GetJsonString(fields, "email") ?? form.Email;
        form.PhoneNumber = GetJsonString(fields, "PhoneNumber") ?? GetJsonString(fields, "phone_number") ?? form.PhoneNumber;
        form.AlternatePhone = GetJsonString(fields, "AlternatePhone") ?? GetJsonString(fields, "alternate_phone") ?? form.AlternatePhone;
        
        // ============================================
        // PARENTS
        // ============================================
        form.MotherName = GetJsonString(fields, "MotherName") ?? GetJsonString(fields, "mother_name") ?? form.MotherName;
        form.FatherName = GetJsonString(fields, "FatherName") ?? GetJsonString(fields, "father_name") ?? form.FatherName;
        form.MotherOccupation = GetJsonString(fields, "MotherOccupation") ?? GetJsonString(fields, "mother_occupation") ?? form.MotherOccupation;
        form.FatherOccupation = GetJsonString(fields, "FatherOccupation") ?? GetJsonString(fields, "father_occupation") ?? form.FatherOccupation;
        form.MotherDesignation = GetJsonString(fields, "MotherDesignation") ?? GetJsonString(fields, "mother_designation") ?? form.MotherDesignation;
        form.FatherDesignation = GetJsonString(fields, "FatherDesignation") ?? GetJsonString(fields, "father_designation") ?? form.FatherDesignation;
        form.MotherPhone = GetJsonString(fields, "MotherPhone") ?? GetJsonString(fields, "mother_phone") ?? GetJsonString(fields, "mother_mobile") ?? form.MotherPhone;
        form.FatherPhone = GetJsonString(fields, "FatherPhone") ?? GetJsonString(fields, "father_phone") ?? GetJsonString(fields, "father_mobile") ?? form.FatherPhone;
        form.MotherMobile = GetJsonString(fields, "MotherMobile") ?? GetJsonString(fields, "mother_mobile") ?? GetJsonString(fields, "mother_phone") ?? form.MotherMobile;
        form.FatherMobile = GetJsonString(fields, "FatherMobile") ?? GetJsonString(fields, "father_mobile") ?? GetJsonString(fields, "father_phone") ?? form.FatherMobile;
        form.MotherEmail = GetJsonString(fields, "MotherEmail") ?? GetJsonString(fields, "mother_email") ?? form.MotherEmail;
        form.FatherEmail = GetJsonString(fields, "FatherEmail") ?? GetJsonString(fields, "father_email") ?? form.FatherEmail;
        form.MotherOrganization = GetJsonString(fields, "MotherOrganization") ?? GetJsonString(fields, "mother_organization") ?? form.MotherOrganization;
        form.FatherOrganization = GetJsonString(fields, "FatherOrganization") ?? GetJsonString(fields, "father_organization") ?? form.FatherOrganization;
        form.MotherAnnualIncome = GetJsonString(fields, "MotherAnnualIncome") ?? GetJsonString(fields, "mother_annual_income") ?? form.MotherAnnualIncome;
        form.FatherAnnualIncome = GetJsonString(fields, "FatherAnnualIncome") ?? GetJsonString(fields, "father_annual_income") ?? form.FatherAnnualIncome;
        
        // ============================================
        // GUARDIAN
        // ============================================
        form.GuardianName = GetJsonString(fields, "GuardianName") ?? GetJsonString(fields, "guardian_name") ?? form.GuardianName;
        form.GuardianAddress = GetJsonString(fields, "GuardianAddress") ?? GetJsonString(fields, "guardian_address") ?? form.GuardianAddress;
        form.GuardianMobile = GetJsonString(fields, "GuardianMobile") ?? GetJsonString(fields, "guardian_mobile") ?? GetJsonString(fields, "guardian_phone") ?? form.GuardianMobile;
        form.GuardianEmail = GetJsonString(fields, "GuardianEmail") ?? GetJsonString(fields, "guardian_email") ?? form.GuardianEmail;
        form.GuardianRelation = GetJsonString(fields, "GuardianRelation") ?? GetJsonString(fields, "guardian_relation") ?? form.GuardianRelation;
        form.GuardianOrganization = GetJsonString(fields, "GuardianOrganization") ?? GetJsonString(fields, "guardian_organization") ?? form.GuardianOrganization;
        
        // ============================================
        // CLASS XII DETAILS
        // ============================================
        form.TwelfthYear = GetJsonString(fields, "TwelfthYear") ?? GetJsonString(fields, "year_of_passing") ?? GetJsonString(fields, "twelfth_year") ?? form.TwelfthYear;
        form.TwelfthBoard = GetJsonString(fields, "TwelfthBoard") ?? GetJsonString(fields, "board_university") ?? GetJsonString(fields, "twelfth_board") ?? form.TwelfthBoard;
        form.TwelfthRollNumber = GetJsonString(fields, "TwelfthRollNumber") ?? GetJsonString(fields, "class12_roll_no") ?? GetJsonString(fields, "exam_roll_no") ?? form.TwelfthRollNumber;
        form.TwelfthInstitution = GetJsonString(fields, "TwelfthInstitution") ?? GetJsonString(fields, "class12_institution") ?? GetJsonString(fields, "institution_attended") ?? form.TwelfthInstitution;
        form.TwelfthPercentage = GetJsonString(fields, "TwelfthPercentage") ?? GetJsonString(fields, "class12_percentage") ?? GetJsonString(fields, "percentage") ?? form.TwelfthPercentage;
        form.Class12Percentage = GetJsonString(fields, "TwelfthPercentage") ?? GetJsonString(fields, "class12_percentage") ?? form.Class12Percentage;
        form.Class12RollNo = GetJsonString(fields, "TwelfthRollNumber") ?? GetJsonString(fields, "class12_roll_no") ?? form.Class12RollNo;
        form.Class12Institution = GetJsonString(fields, "TwelfthInstitution") ?? GetJsonString(fields, "class12_institution") ?? form.Class12Institution;
        form.HindiStudiedUpto = GetJsonString(fields, "HindiStudiedUpto") ?? GetJsonString(fields, "hindi_studied_upto") ?? form.HindiStudiedUpto;
        
        // ============================================
        // 10TH CLASS DETAILS
        // ============================================
        form.TenthBoard = GetJsonString(fields, "TenthBoard") ?? GetJsonString(fields, "tenth_board") ?? form.TenthBoard;
        form.TenthYear = GetJsonString(fields, "TenthYear") ?? GetJsonString(fields, "tenth_year") ?? form.TenthYear;
        form.TenthPercentage = GetJsonString(fields, "TenthPercentage") ?? GetJsonString(fields, "tenth_percentage") ?? form.TenthPercentage;
        form.TenthSchool = GetJsonString(fields, "TenthSchool") ?? GetJsonString(fields, "tenth_school") ?? form.TenthSchool;
        
        // ============================================
        // OTHER INFO
        // ============================================
        form.DuEnrollmentNumber = GetJsonString(fields, "DuEnrollmentNumber") ?? GetJsonString(fields, "du_enrolment_no") ?? GetJsonString(fields, "du_enrollment_number") ?? form.DuEnrollmentNumber;
        form.HindiMediumPreference = GetJsonString(fields, "HindiMediumPreference") ?? GetJsonString(fields, "hindi_medium_preference") ?? form.HindiMediumPreference;
        form.DeclarationDate = GetJsonString(fields, "DeclarationDate") ?? GetJsonString(fields, "declaration_date") ?? form.DeclarationDate;
        form.DeclarationPlace = GetJsonString(fields, "DeclarationPlace") ?? GetJsonString(fields, "declaration_place") ?? form.DeclarationPlace;
        
        // ============================================
        // CERTIFICATE DETAILS
        // ============================================
        form.CategoryCertificateNumber = GetJsonString(fields, "CategoryCertificateNumber") ?? GetJsonString(fields, "certificate_no") ?? GetJsonString(fields, "category_certificate_number") ?? form.CategoryCertificateNumber;
        form.CategoryCertificateAuthority = GetJsonString(fields, "CategoryCertificateAuthority") ?? GetJsonString(fields, "category_certificate_authority") ?? form.CategoryCertificateAuthority;
        form.CategoryCertificateDate = GetJsonString(fields, "CategoryCertificateDate") ?? GetJsonString(fields, "category_certificate_date") ?? form.CategoryCertificateDate;
        form.DisabilityType = GetJsonString(fields, "DisabilityType") ?? GetJsonString(fields, "pwbd_disability_type") ?? GetJsonString(fields, "disability_type") ?? form.DisabilityType;
        form.DisabilityPercentage = GetJsonString(fields, "DisabilityPercentage") ?? GetJsonString(fields, "pwbd_disability_percent") ?? GetJsonString(fields, "disability_percentage") ?? form.DisabilityPercentage;
        form.UdidNumber = GetJsonString(fields, "UdidNumber") ?? GetJsonString(fields, "udid_number") ?? form.UdidNumber;
        
        // ============================================
        // CUET SUBJECT DETAILS
        // ============================================
        form.CuetSubject1 = GetJsonString(fields, "CuetSubject1") ?? GetJsonString(fields, "cuet_subject1") ?? form.CuetSubject1;
        form.CuetTotalScore1 = GetJsonString(fields, "CuetTotalScore1") ?? GetJsonString(fields, "cuet_max1") ?? form.CuetTotalScore1;
        form.CuetScoreObtained1 = GetJsonString(fields, "CuetScoreObtained1") ?? GetJsonString(fields, "cuet_obtained1") ?? form.CuetScoreObtained1;
        form.CuetSubject2 = GetJsonString(fields, "CuetSubject2") ?? GetJsonString(fields, "cuet_subject2") ?? form.CuetSubject2;
        form.CuetTotalScore2 = GetJsonString(fields, "CuetTotalScore2") ?? GetJsonString(fields, "cuet_max2") ?? form.CuetTotalScore2;
        form.CuetScoreObtained2 = GetJsonString(fields, "CuetScoreObtained2") ?? GetJsonString(fields, "cuet_obtained2") ?? form.CuetScoreObtained2;
        form.CuetSubject3 = GetJsonString(fields, "CuetSubject3") ?? GetJsonString(fields, "cuet_subject3") ?? form.CuetSubject3;
        form.CuetTotalScore3 = GetJsonString(fields, "CuetTotalScore3") ?? GetJsonString(fields, "cuet_max3") ?? form.CuetTotalScore3;
        form.CuetScoreObtained3 = GetJsonString(fields, "CuetScoreObtained3") ?? GetJsonString(fields, "cuet_obtained3") ?? form.CuetScoreObtained3;
        form.CuetSubject4 = GetJsonString(fields, "CuetSubject4") ?? GetJsonString(fields, "cuet_subject4") ?? form.CuetSubject4;
        form.CuetTotalScore4 = GetJsonString(fields, "CuetTotalScore4") ?? GetJsonString(fields, "cuet_max4") ?? form.CuetTotalScore4;
        form.CuetScoreObtained4 = GetJsonString(fields, "CuetScoreObtained4") ?? GetJsonString(fields, "cuet_obtained4") ?? form.CuetScoreObtained4;
        form.CuetSubject5 = GetJsonString(fields, "CuetSubject5") ?? GetJsonString(fields, "cuet_subject5") ?? form.CuetSubject5;
        form.CuetTotalScore5 = GetJsonString(fields, "CuetTotalScore5") ?? GetJsonString(fields, "cuet_max5") ?? form.CuetTotalScore5;
        form.CuetScoreObtained5 = GetJsonString(fields, "CuetScoreObtained5") ?? GetJsonString(fields, "cuet_obtained5") ?? form.CuetScoreObtained5;
        form.CuetSubject6 = GetJsonString(fields, "CuetSubject6") ?? GetJsonString(fields, "cuet_subject6") ?? form.CuetSubject6;
        form.CuetTotalScore6 = GetJsonString(fields, "CuetTotalScore6") ?? GetJsonString(fields, "cuet_max6") ?? form.CuetTotalScore6;
        form.CuetScoreObtained6 = GetJsonString(fields, "CuetScoreObtained6") ?? GetJsonString(fields, "cuet_obtained6") ?? form.CuetScoreObtained6;
        form.CuetTotalScoreAll = GetJsonString(fields, "CuetTotalScoreAll") ?? GetJsonString(fields, "cuet_total_all") ?? GetJsonString(fields, "cuet_score") ?? form.CuetTotalScoreAll;
        form.CuetScoreObtainedAll = GetJsonString(fields, "CuetScoreObtainedAll") ?? GetJsonString(fields, "cuet_obtained_all") ?? form.CuetScoreObtainedAll;
        
        // ============================================
        // ADDRESS LINES
        // ============================================
        form.PermanentAddressLine1 = GetJsonString(fields, "PermanentAddressLine1") ?? GetJsonString(fields, "permanent_address_line1") ?? form.PermanentAddressLine1;
        form.PermanentAddressLine2 = GetJsonString(fields, "PermanentAddressLine2") ?? GetJsonString(fields, "permanent_address_line2") ?? form.PermanentAddressLine2;
        form.PermanentAddressLine3 = GetJsonString(fields, "PermanentAddressLine3") ?? GetJsonString(fields, "permanent_address_line3") ?? form.PermanentAddressLine3;
        form.CorrespondenceAddressLine1 = GetJsonString(fields, "CorrespondenceAddressLine1") ?? GetJsonString(fields, "correspondence_address_line1") ?? form.CorrespondenceAddressLine1;
        form.CorrespondenceAddressLine2 = GetJsonString(fields, "CorrespondenceAddressLine2") ?? GetJsonString(fields, "correspondence_address_line2") ?? form.CorrespondenceAddressLine2;
        form.CorrespondenceAddressLine3 = GetJsonString(fields, "CorrespondenceAddressLine3") ?? GetJsonString(fields, "correspondence_address_line3") ?? form.CorrespondenceAddressLine3;
        
        // ============================================
        // LANDLINE PHONES
        // ============================================
        form.MotherLandlineCode = GetJsonString(fields, "MotherLandlineCode") ?? GetJsonString(fields, "mother_landline_code") ?? form.MotherLandlineCode;
        form.MotherLandline = GetJsonString(fields, "MotherLandline") ?? GetJsonString(fields, "mother_landline") ?? form.MotherLandline;
        form.FatherLandlineCode = GetJsonString(fields, "FatherLandlineCode") ?? GetJsonString(fields, "father_landline_code") ?? form.FatherLandlineCode;
        form.FatherLandline = GetJsonString(fields, "FatherLandline") ?? GetJsonString(fields, "father_landline") ?? form.FatherLandline;
        form.GuardianLandlineCode = GetJsonString(fields, "GuardianLandlineCode") ?? GetJsonString(fields, "guardian_landline_code") ?? form.GuardianLandlineCode;
        form.GuardianLandline = GetJsonString(fields, "GuardianLandline") ?? GetJsonString(fields, "guardian_landline") ?? form.GuardianLandline;
        
        // ============================================
        // EMERGENCY CONTACT
        // ============================================
        form.EmergencyContactName = GetJsonString(fields, "EmergencyContactName") ?? GetJsonString(fields, "emergency_contact_name") ?? form.EmergencyContactName;
        form.EmergencyContactPhone = GetJsonString(fields, "EmergencyContactPhone") ?? GetJsonString(fields, "emergency_contact_phone") ?? form.EmergencyContactPhone;
        
        // ============================================
        // DECLARATIONS
        // ============================================
        form.StudentDeclarationName = GetJsonString(fields, "StudentDeclarationName") ?? GetJsonString(fields, "student_declaration_name") ?? form.StudentDeclarationName;
        form.StudentDeclarationDate = GetJsonString(fields, "StudentDeclarationDate") ?? GetJsonString(fields, "student_declaration_date") ?? form.StudentDeclarationDate;
        form.StudentDeclarationPlace = GetJsonString(fields, "StudentDeclarationPlace") ?? GetJsonString(fields, "student_declaration_place") ?? form.StudentDeclarationPlace;
        form.ParentGuardianName = GetJsonString(fields, "ParentGuardianName") ?? GetJsonString(fields, "parent_guardian_name") ?? form.ParentGuardianName;
        form.ParentGuardianRelationship = GetJsonString(fields, "ParentGuardianRelationship") ?? GetJsonString(fields, "parent_guardian_relationship") ?? form.ParentGuardianRelationship;
        form.ParentGuardianCandidateName = GetJsonString(fields, "ParentGuardianCandidateName") ?? GetJsonString(fields, "parent_guardian_candidate_name") ?? form.ParentGuardianCandidateName;
        form.ParentGuardianCourse = GetJsonString(fields, "ParentGuardianCourse") ?? GetJsonString(fields, "parent_guardian_course") ?? form.ParentGuardianCourse;
        form.ParentGuardianDate = GetJsonString(fields, "ParentGuardianDate") ?? GetJsonString(fields, "parent_guardian_date") ?? form.ParentGuardianDate;
        form.ParentGuardianPlace = GetJsonString(fields, "ParentGuardianPlace") ?? GetJsonString(fields, "parent_guardian_place") ?? form.ParentGuardianPlace;
        
        // ============================================
        // DOCUMENT CHECKLIST
        // ============================================
        form.DocAdmissionForm = GetJsonBool(fields, "DocAdmissionForm") ?? GetJsonBool(fields, "doc_admission_form") ?? form.DocAdmissionForm;
        form.DocUndertakingRagging = GetJsonBool(fields, "DocUndertakingRagging") ?? GetJsonBool(fields, "doc_undertaking_ragging") ?? GetJsonBool(fields, "doc_anti_ragging") ?? form.DocUndertakingRagging;
        form.DocPhotographs = GetJsonBool(fields, "DocPhotographs") ?? GetJsonBool(fields, "doc_photographs") ?? GetJsonBool(fields, "doc_student_photo") ?? form.DocPhotographs;
        form.DocCuetScorecard = GetJsonBool(fields, "DocCuetScorecard") ?? GetJsonBool(fields, "doc_cuet_scorecard") ?? form.DocCuetScorecard;
        form.DocClassXiiMarksheet = GetJsonBool(fields, "DocClassXiiMarksheet") ?? GetJsonBool(fields, "doc_class_xii_marksheet") ?? GetJsonBool(fields, "doc_marksheet_12") ?? form.DocClassXiiMarksheet;
        form.DocClassXCertificate = GetJsonBool(fields, "DocClassXCertificate") ?? GetJsonBool(fields, "doc_class_x_certificate") ?? GetJsonBool(fields, "doc_marksheet_10") ?? form.DocClassXCertificate;
        form.DocClassXiiCertificate = GetJsonBool(fields, "DocClassXiiCertificate") ?? GetJsonBool(fields, "doc_class_xii_certificate") ?? form.DocClassXiiCertificate;
        form.DocCharacterCertificate = GetJsonBool(fields, "DocCharacterCertificate") ?? GetJsonBool(fields, "doc_character_certificate") ?? form.DocCharacterCertificate;
        form.DocCasteCertificate = GetJsonBool(fields, "DocCasteCertificate") ?? GetJsonBool(fields, "doc_caste_certificate") ?? form.DocCasteCertificate;
        form.DocMigrationCertificate = GetJsonBool(fields, "DocMigrationCertificate") ?? GetJsonBool(fields, "doc_migration_certificate") ?? form.DocMigrationCertificate;
        form.DocTransferCertificate = GetJsonBool(fields, "DocTransferCertificate") ?? GetJsonBool(fields, "doc_transfer_certificate") ?? GetJsonBool(fields, "doc_tc") ?? form.DocTransferCertificate;
        form.DocGapCertificate = GetJsonBool(fields, "DocGapCertificate") ?? GetJsonBool(fields, "doc_gap_certificate") ?? form.DocGapCertificate;
        form.DocIncomeCertificate = GetJsonBool(fields, "DocIncomeCertificate") ?? GetJsonBool(fields, "doc_income_certificate") ?? form.DocIncomeCertificate;
        form.DocDomicileCertificate = GetJsonBool(fields, "DocDomicileCertificate") ?? GetJsonBool(fields, "doc_domicile_certificate") ?? GetJsonBool(fields, "doc_domicile") ?? form.DocDomicileCertificate;
        form.DocAadharCard = GetJsonBool(fields, "DocAadharCard") ?? GetJsonBool(fields, "doc_aadhar_card") ?? GetJsonBool(fields, "doc_aadhar") ?? form.DocAadharCard;
        form.DocMedicalFitness = GetJsonBool(fields, "DocMedicalFitness") ?? GetJsonBool(fields, "doc_medical_fitness") ?? form.DocMedicalFitness;
        
        // Build full name if not found but parts exist
        if (string.IsNullOrEmpty(form.StudentName) && !string.IsNullOrEmpty(form.FirstName))
        {
            form.StudentName = string.Join(" ", new[] { form.FirstName, form.MiddleName, form.Surname }
                .Where(s => !string.IsNullOrWhiteSpace(s)));
        }
        
        // Copy pincode if only one found
        if (string.IsNullOrEmpty(form.Pincode) && !string.IsNullOrEmpty(form.PermanentPincode))
        {
            form.Pincode = form.PermanentPincode;
        }
    }
    
    private string? GetJsonString(System.Text.Json.JsonElement element, string propertyName)
    {
        if (element.TryGetProperty(propertyName, out var prop))
        {
            return prop.ValueKind switch
            {
                System.Text.Json.JsonValueKind.String => prop.GetString(),
                System.Text.Json.JsonValueKind.Number => prop.GetRawText(),
                System.Text.Json.JsonValueKind.True => "true",
                System.Text.Json.JsonValueKind.False => "false",
                _ => null
            };
        }
        return null;
    }
    
    private bool? GetJsonBool(System.Text.Json.JsonElement element, string propertyName)
    {
        if (element.TryGetProperty(propertyName, out var prop))
        {
            return prop.ValueKind switch
            {
                System.Text.Json.JsonValueKind.True => true,
                System.Text.Json.JsonValueKind.False => false,
                System.Text.Json.JsonValueKind.String => prop.GetString()?.ToLower() is "yes" or "1" or "true",
                _ => null
            };
        }
        return null;
    }
    
    /// <summary>
    /// Map pre-extracted fields (from Python spatial analysis) directly to AdmissionForm
    /// This is the preferred method when OcrResult.ExtractedFields is available
    /// </summary>
    public AdmissionForm ExtractFromPreExtracted(Dictionary<string, string> fields, AdmissionForm form)
    {
        if (fields == null || fields.Count == 0) return form;
        
        // When Gemini returns 20+ fields, it's a high-quality extraction.
        // In that case, DON'T preserve old stale values — use only what Gemini returned.
        // This prevents incorrect data from spatial extraction persisting (e.g., wrong Surname, AadharNumber).
        bool isGeminiQuality = fields.Count >= 20;
        
        // Build a case-insensitive lookup for all keys
        // This allows matching "FirstName", "first_name", "firstname" etc.
        var ciFields = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        foreach (var kvp in fields)
            ciFields[kvp.Key] = kvp.Value;
        
        // Helper: try PascalCase first (Gemini output), then snake_case, then case-insensitive
        // When isGeminiQuality is true, return null (not old value) for missing fields
        string? Get(string pascalKey, string snakeKey)
        {
            if (fields.TryGetValue(pascalKey, out var v1)) return v1;
            if (fields.TryGetValue(snakeKey, out var v2)) return v2;
            if (ciFields.TryGetValue(pascalKey, out var v3)) return v3;
            return null;
        }
        // Get with fallback: only falls back to existing form value for spatial extractions
        string? GetF(string pascalKey, string snakeKey, string? formValue)
        {
            var result = Get(pascalKey, snakeKey);
            if (result != null) return result;
            return isGeminiQuality ? null : formValue;
        }
        // Shortcut for keys that are the same in both cases (e.g., "Email", "Course")
        string? Get1(string key) => Get(key, key.ToLower());
        bool? GetBool(string pascalKey, string snakeKey)
        {
            var val = Get(pascalKey, snakeKey);
            if (val == null) return null;
            var lower = val.ToLower();
            return lower == "yes" || lower == "true" || lower == "1";
        }
        
        // ============================================
        // PERSONAL DETAILS
        // ============================================
        form.StudentName = GetF("StudentName", "student_name", form.StudentName);
        form.FirstName = GetF("FirstName", "first_name", form.FirstName);
        form.MiddleName = GetF("MiddleName", "middle_name", form.MiddleName);
        form.Surname = GetF("Surname", "surname", form.Surname);
        form.Gender = GetF("Gender", "gender", form.Gender);
        form.DateOfBirth = GetF("DateOfBirth", "date_of_birth", form.DateOfBirth);
        form.Category = GetF("Category", "category", form.Category);
        form.Nationality = GetF("Nationality", "nationality", form.Nationality);
        form.Religion = GetF("Religion", "religion", form.Religion);
        form.BloodGroup = GetF("BloodGroup", "blood_group", form.BloodGroup);
        form.AadharNumber = GetF("AadharNumber", "aadhar_number", form.AadharNumber);
        form.BelowPovertyLine = GetF("BelowPovertyLine", "below_poverty_line", form.BelowPovertyLine);
        form.AnnualIncome = GetF("AnnualIncome", "annual_income", form.AnnualIncome);
        form.MinorityCategory = GetF("MinorityCategory", "minority_category", form.MinorityCategory);
        
        // ============================================
        // ACADEMIC DETAILS
        // ============================================
        form.AcademicSession = GetF("AcademicSession", "academic_session", form.AcademicSession);
        form.Course = GetF("Course", "course", form.Course);
        form.AdmissionCategory = Get("AdmissionCategory", "admission_category") ?? Get("Category", "category") ?? (isGeminiQuality ? null : form.AdmissionCategory);
        form.DuPortalFormNumber = GetF("DuPortalFormNumber", "du_portal_form_number", form.DuPortalFormNumber);
        form.CuetScore = GetF("CuetScore", "cuet_score", form.CuetScore);
        form.CollegeRollNo = GetF("CollegeRollNo", "college_roll_no", form.CollegeRollNo);
        form.DateOfAdmission = GetF("DateOfAdmission", "date_of_admission", form.DateOfAdmission);
        
        // ============================================
        // ADDRESS
        // ============================================
        form.PermanentAddress = GetF("PermanentAddress", "permanent_address", form.PermanentAddress);
        form.PermanentState = Get("PermanentState", "permanent_state") ?? Get("State", "state") ?? (isGeminiQuality ? null : form.PermanentState);
        form.PermanentPincode = Get("PermanentPincode", "permanent_pincode") ?? Get("Pincode", "pincode") ?? (isGeminiQuality ? null : form.PermanentPincode);
        form.Pincode = GetF("Pincode", "pincode", form.Pincode);
        form.CorrespondenceAddress = Get("CorrespondenceAddress", "correspondence_address") ?? Get("LocalAddress", "local_address") ?? (isGeminiQuality ? null : form.CorrespondenceAddress);
        form.CorrespondenceState = GetF("CorrespondenceState", "correspondence_state", form.CorrespondenceState);
        form.CorrespondencePincode = GetF("CorrespondencePincode", "correspondence_pincode", form.CorrespondencePincode);
        
        // ============================================
        // CONTACT
        // ============================================
        form.Email = GetF("Email", "email", form.Email);
        form.PhoneNumber = GetF("PhoneNumber", "phone_number", form.PhoneNumber);
        form.AlternatePhone = GetF("AlternatePhone", "alternate_phone", form.AlternatePhone);
        
        // ============================================
        // PARENTS
        // ============================================
        form.MotherName = GetF("MotherName", "mother_name", form.MotherName);
        form.FatherName = GetF("FatherName", "father_name", form.FatherName);
        form.MotherOccupation = GetF("MotherOccupation", "mother_occupation", form.MotherOccupation);
        form.FatherOccupation = GetF("FatherOccupation", "father_occupation", form.FatherOccupation);
        form.MotherDesignation = GetF("MotherDesignation", "mother_designation", form.MotherDesignation);
        form.FatherDesignation = GetF("FatherDesignation", "father_designation", form.FatherDesignation);
        form.MotherPhone = Get("MotherPhone", "mother_phone") ?? Get("MotherMobile", "mother_mobile") ?? (isGeminiQuality ? null : form.MotherPhone);
        form.FatherPhone = Get("FatherPhone", "father_phone") ?? Get("FatherMobile", "father_mobile") ?? (isGeminiQuality ? null : form.FatherPhone);
        form.MotherMobile = Get("MotherMobile", "mother_mobile") ?? Get("MotherPhone", "mother_phone") ?? (isGeminiQuality ? null : form.MotherMobile);
        form.FatherMobile = Get("FatherMobile", "father_mobile") ?? Get("FatherPhone", "father_phone") ?? (isGeminiQuality ? null : form.FatherMobile);
        form.MotherEmail = GetF("MotherEmail", "mother_email", form.MotherEmail);
        form.FatherEmail = GetF("FatherEmail", "father_email", form.FatherEmail);
        form.MotherOrganization = GetF("MotherOrganization", "mother_organization", form.MotherOrganization);
        form.FatherOrganization = GetF("FatherOrganization", "father_organization", form.FatherOrganization);
        
        // ============================================
        // GUARDIAN
        // ============================================
        form.GuardianName = GetF("GuardianName", "guardian_name", form.GuardianName);
        form.GuardianAddress = GetF("GuardianAddress", "guardian_address", form.GuardianAddress);
        form.GuardianMobile = Get("GuardianMobile", "guardian_mobile") ?? Get("GuardianPhone", "guardian_phone") ?? (isGeminiQuality ? null : form.GuardianMobile);
        form.GuardianEmail = GetF("GuardianEmail", "guardian_email", form.GuardianEmail);
        form.GuardianRelation = GetF("GuardianRelation", "guardian_relation", form.GuardianRelation);
        
        // ============================================
        // CLASS XII DETAILS
        // ============================================
        form.TwelfthYear = Get("TwelfthYear", "twelfth_year") ?? Get("YearOfPassing", "year_of_passing") ?? (isGeminiQuality ? null : form.TwelfthYear);
        form.TwelfthBoard = Get("TwelfthBoard", "twelfth_board") ?? Get("BoardUniversity", "board_university") ?? (isGeminiQuality ? null : form.TwelfthBoard);
        form.TwelfthRollNumber = Get("TwelfthRollNumber", "twelfth_roll_number") ?? Get("ExamRollNo", "exam_roll_no") ?? (isGeminiQuality ? null : form.TwelfthRollNumber);
        form.TwelfthInstitution = Get("TwelfthInstitution", "twelfth_institution") ?? Get("InstitutionAttended", "institution_attended") ?? (isGeminiQuality ? null : form.TwelfthInstitution);
        form.TwelfthPercentage = Get("TwelfthPercentage", "twelfth_percentage") ?? Get("Percentage", "percentage") ?? (isGeminiQuality ? null : form.TwelfthPercentage);
        form.HindiStudiedUpto = GetF("HindiStudiedUpto", "hindi_studied_upto", form.HindiStudiedUpto);
        
        // ============================================
        // OTHER INFO
        // ============================================
        form.DuEnrollmentNumber = GetF("DuEnrollmentNumber", "du_enrollment_number", form.DuEnrollmentNumber);
        form.HindiMediumPreference = GetF("HindiMediumPreference", "hindi_medium_preference", form.HindiMediumPreference);
        form.DeclarationDate = GetF("DeclarationDate", "declaration_date", form.DeclarationDate);
        form.DeclarationPlace = GetF("DeclarationPlace", "declaration_place", form.DeclarationPlace);
        
        // ============================================
        // CERTIFICATE DETAILS
        // ============================================
        form.CategoryCertificateAuthority = GetF("CategoryCertificateAuthority", "category_certificate_authority", form.CategoryCertificateAuthority);
        form.CategoryCertificateNumber = GetF("CategoryCertificateNumber", "category_certificate_number", form.CategoryCertificateNumber);
        form.CategoryCertificateDate = GetF("CategoryCertificateDate", "category_certificate_date", form.CategoryCertificateDate);
        form.DisabilityType = GetF("DisabilityType", "disability_type", form.DisabilityType);
        form.DisabilityPercentage = GetF("DisabilityPercentage", "disability_percentage", form.DisabilityPercentage);
        form.UdidNumber = GetF("UdidNumber", "udid_number", form.UdidNumber);
        
        // ============================================
        // DOCUMENT CHECKLIST
        // ============================================
        form.DocAdmissionForm = GetBool("DocAdmissionForm", "doc_admission_form") ?? form.DocAdmissionForm;
        form.DocUndertakingRagging = GetBool("DocUndertakingRagging", "doc_undertaking_ragging") ?? GetBool("DocAntiRagging", "doc_anti_ragging") ?? form.DocUndertakingRagging;
        form.DocPhotographs = GetBool("DocPhotographs", "doc_photographs") ?? GetBool("DocStudentPhoto", "doc_student_photo") ?? form.DocPhotographs;
        form.DocCuetScorecard = GetBool("DocCuetScorecard", "doc_cuet_scorecard") ?? form.DocCuetScorecard;
        form.DocClassXiiMarksheet = GetBool("DocClassXiiMarksheet", "doc_class_xii_marksheet") ?? GetBool("DocMarksheet12", "doc_marksheet_12") ?? form.DocClassXiiMarksheet;
        form.DocClassXCertificate = GetBool("DocClassXCertificate", "doc_class_x_certificate") ?? GetBool("DocMarksheet10", "doc_marksheet_10") ?? form.DocClassXCertificate;
        form.DocClassXiiCertificate = GetBool("DocClassXiiCertificate", "doc_class_xii_certificate") ?? form.DocClassXiiCertificate;
        form.DocCharacterCertificate = GetBool("DocCharacterCertificate", "doc_character_certificate") ?? form.DocCharacterCertificate;
        form.DocCasteCertificate = GetBool("DocCasteCertificate", "doc_caste_certificate") ?? form.DocCasteCertificate;
        form.DocMigrationCertificate = GetBool("DocMigrationCertificate", "doc_migration_certificate") ?? form.DocMigrationCertificate;
        form.DocTransferCertificate = GetBool("DocTransferCertificate", "doc_transfer_certificate") ?? GetBool("DocTc", "doc_tc") ?? form.DocTransferCertificate;
        form.DocGapCertificate = GetBool("DocGapCertificate", "doc_gap_certificate") ?? form.DocGapCertificate;
        form.DocIncomeCertificate = GetBool("DocIncomeCertificate", "doc_income_certificate") ?? form.DocIncomeCertificate;
        form.DocDomicileCertificate = GetBool("DocDomicileCertificate", "doc_domicile_certificate") ?? GetBool("DocDomicile", "doc_domicile") ?? form.DocDomicileCertificate;
        form.DocAadharCard = GetBool("DocAadharCard", "doc_aadhar_card") ?? GetBool("DocAadhar", "doc_aadhar") ?? form.DocAadharCard;
        form.DocMedicalFitness = GetBool("DocMedicalFitness", "doc_medical_fitness") ?? form.DocMedicalFitness;
        
        // Additional personal fields

        form.LocalAddress = GetF("LocalAddress", "local_address", form.LocalAddress);
        form.MotherAnnualIncome = GetF("MotherAnnualIncome", "mother_annual_income", form.MotherAnnualIncome);
        form.FatherAnnualIncome = GetF("FatherAnnualIncome", "father_annual_income", form.FatherAnnualIncome);
        form.Class12Percentage = Get("Class12Percentage", "class12_percentage") ?? Get("TwelfthPercentage", "twelfth_percentage") ?? (isGeminiQuality ? null : form.Class12Percentage);
        form.Class12RollNo = Get("Class12RollNo", "class12_roll_no") ?? Get("TwelfthRollNumber", "twelfth_roll_number") ?? (isGeminiQuality ? null : form.Class12RollNo);
        form.Class12Institution = Get("Class12Institution", "class12_institution") ?? Get("TwelfthInstitution", "twelfth_institution") ?? (isGeminiQuality ? null : form.Class12Institution);
        
        // ============================================
        // CUET SUBJECT DETAILS
        // ============================================
        form.CuetSubject1 = GetF("CuetSubject1", "cuet_subject1", form.CuetSubject1);
        form.CuetTotalScore1 = GetF("CuetTotalScore1", "cuet_max1", form.CuetTotalScore1);
        form.CuetScoreObtained1 = GetF("CuetScoreObtained1", "cuet_obtained1", form.CuetScoreObtained1);
        form.CuetSubject2 = GetF("CuetSubject2", "cuet_subject2", form.CuetSubject2);
        form.CuetTotalScore2 = GetF("CuetTotalScore2", "cuet_max2", form.CuetTotalScore2);
        form.CuetScoreObtained2 = GetF("CuetScoreObtained2", "cuet_obtained2", form.CuetScoreObtained2);
        form.CuetSubject3 = GetF("CuetSubject3", "cuet_subject3", form.CuetSubject3);
        form.CuetTotalScore3 = GetF("CuetTotalScore3", "cuet_max3", form.CuetTotalScore3);
        form.CuetScoreObtained3 = GetF("CuetScoreObtained3", "cuet_obtained3", form.CuetScoreObtained3);
        form.CuetSubject4 = GetF("CuetSubject4", "cuet_subject4", form.CuetSubject4);
        form.CuetTotalScore4 = GetF("CuetTotalScore4", "cuet_max4", form.CuetTotalScore4);
        form.CuetScoreObtained4 = GetF("CuetScoreObtained4", "cuet_obtained4", form.CuetScoreObtained4);
        form.CuetSubject5 = GetF("CuetSubject5", "cuet_subject5", form.CuetSubject5);
        form.CuetTotalScore5 = GetF("CuetTotalScore5", "cuet_max5", form.CuetTotalScore5);
        form.CuetScoreObtained5 = GetF("CuetScoreObtained5", "cuet_obtained5", form.CuetScoreObtained5);
        form.CuetSubject6 = GetF("CuetSubject6", "cuet_subject6", form.CuetSubject6);
        form.CuetTotalScore6 = GetF("CuetTotalScore6", "cuet_max6", form.CuetTotalScore6);
        form.CuetScoreObtained6 = GetF("CuetScoreObtained6", "cuet_obtained6", form.CuetScoreObtained6);
        form.CuetTotalScoreAll = Get("CuetTotalScoreAll", "cuet_total_all") ?? Get("CuetScore", "cuet_score") ?? (isGeminiQuality ? null : form.CuetTotalScoreAll);
        form.CuetScoreObtainedAll = GetF("CuetScoreObtainedAll", "cuet_obtained_all", form.CuetScoreObtainedAll);
        
        // ============================================
        // 10TH CLASS DETAILS
        // ============================================
        form.TenthBoard = GetF("TenthBoard", "tenth_board", form.TenthBoard);
        form.TenthYear = GetF("TenthYear", "tenth_year", form.TenthYear);
        form.TenthPercentage = GetF("TenthPercentage", "tenth_percentage", form.TenthPercentage);
        form.TenthSchool = GetF("TenthSchool", "tenth_school", form.TenthSchool);
        
        // ============================================
        // ADDRESS LINES
        // ============================================
        form.PermanentAddressLine1 = GetF("PermanentAddressLine1", "permanent_address_line1", form.PermanentAddressLine1);
        form.PermanentAddressLine2 = GetF("PermanentAddressLine2", "permanent_address_line2", form.PermanentAddressLine2);
        form.PermanentAddressLine3 = GetF("PermanentAddressLine3", "permanent_address_line3", form.PermanentAddressLine3);
        form.CorrespondenceAddressLine1 = GetF("CorrespondenceAddressLine1", "correspondence_address_line1", form.CorrespondenceAddressLine1);
        form.CorrespondenceAddressLine2 = GetF("CorrespondenceAddressLine2", "correspondence_address_line2", form.CorrespondenceAddressLine2);
        form.CorrespondenceAddressLine3 = GetF("CorrespondenceAddressLine3", "correspondence_address_line3", form.CorrespondenceAddressLine3);
        
        // ============================================
        // LANDLINE PHONES
        // ============================================
        form.MotherLandlineCode = GetF("MotherLandlineCode", "mother_landline_code", form.MotherLandlineCode);
        form.MotherLandline = GetF("MotherLandline", "mother_landline", form.MotherLandline);
        form.FatherLandlineCode = GetF("FatherLandlineCode", "father_landline_code", form.FatherLandlineCode);
        form.FatherLandline = GetF("FatherLandline", "father_landline", form.FatherLandline);
        form.GuardianLandlineCode = GetF("GuardianLandlineCode", "guardian_landline_code", form.GuardianLandlineCode);
        form.GuardianLandline = GetF("GuardianLandline", "guardian_landline", form.GuardianLandline);
        form.GuardianOrganization = GetF("GuardianOrganization", "guardian_organization", form.GuardianOrganization);
        
        // ============================================
        // EMERGENCY CONTACT
        // ============================================
        form.EmergencyContactName = GetF("EmergencyContactName", "emergency_contact_name", form.EmergencyContactName);
        form.EmergencyContactPhone = GetF("EmergencyContactPhone", "emergency_contact_phone", form.EmergencyContactPhone);
        
        // ============================================
        // DECLARATIONS
        // ============================================
        form.StudentDeclarationName = GetF("StudentDeclarationName", "student_declaration_name", form.StudentDeclarationName);
        form.StudentDeclarationDate = GetF("StudentDeclarationDate", "student_declaration_date", form.StudentDeclarationDate);
        form.StudentDeclarationPlace = GetF("StudentDeclarationPlace", "student_declaration_place", form.StudentDeclarationPlace);
        form.ParentGuardianName = GetF("ParentGuardianName", "parent_guardian_name", form.ParentGuardianName);
        form.ParentGuardianRelationship = GetF("ParentGuardianRelationship", "parent_guardian_relationship", form.ParentGuardianRelationship);
        form.ParentGuardianCandidateName = GetF("ParentGuardianCandidateName", "parent_guardian_candidate_name", form.ParentGuardianCandidateName);
        form.ParentGuardianCourse = GetF("ParentGuardianCourse", "parent_guardian_course", form.ParentGuardianCourse);
        form.ParentGuardianDate = GetF("ParentGuardianDate", "parent_guardian_date", form.ParentGuardianDate);
        form.ParentGuardianPlace = GetF("ParentGuardianPlace", "parent_guardian_place", form.ParentGuardianPlace);
        
        return form;
    }

    /// <summary>
    /// Extract and return extraction statistics
    /// </summary>
    public (AdmissionForm form, Dictionary<string, object> stats) ExtractWithStats(string ocrText, AdmissionForm form)
    {
        form = ExtractFields(ocrText, form);
        
        var stats = new Dictionary<string, object>
        {
            ["total_fields"] = 30,
            ["extracted_fields"] = CountExtractedFields(form),
            ["extraction_rate"] = (CountExtractedFields(form) / 30.0 * 100).ToString("F1") + "%",
            ["has_name"] = !string.IsNullOrEmpty(form.StudentName),
            ["has_phone"] = !string.IsNullOrEmpty(form.PhoneNumber),
            ["has_email"] = !string.IsNullOrEmpty(form.Email),
            ["has_aadhar"] = !string.IsNullOrEmpty(form.AadharNumber)
        };
        
        return (form, stats);
    }

    private static string? ExtractFirst(string text, Regex[] patterns)
    {
        foreach (var pattern in patterns)
        {
            var match = pattern.Match(text);
            if (match.Success && match.Groups.Count > 1)
            {
                var value = match.Groups[1].Value.Trim();
                if (!OcrErrorCorrector.IsFormLabel(value))
                {
                    return value;
                }
            }
        }
        return null;
    }
    
    private static string NormalizeText(string text)
    {
        // Normalize whitespace and newlines
        var normalized = Regex.Replace(text, @"\r\n|\r|\n", "\n");
        normalized = Regex.Replace(normalized, @"[ \t]+", " ");
        return normalized;
    }
    
    private static string? NormalizeGender(string? gender)
    {
        if (string.IsNullOrEmpty(gender)) return null;
        
        return gender.ToUpper() switch
        {
            "M" or "MALE" => "Male",
            "F" or "FEMALE" => "Female",
            "T" or "TRANSGENDER" => "Transgender",
            _ => gender
        };
    }
    
    private static int CountExtractedFields(AdmissionForm form)
    {
        var count = 0;
        var props = typeof(AdmissionForm).GetProperties()
            .Where(p => p.PropertyType == typeof(string));
            
        foreach (var prop in props)
        {
            if (prop.GetValue(form) is string val && !string.IsNullOrEmpty(val))
                count++;
        }
        
        return count;
    }
}
