using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using OCRAdmissionForms.Core.Enums;

namespace OCRAdmissionForms.Core.Entities;

/// <summary>
/// Complete AdmissionForm entity matching the SRCC Student Data Form structure.
/// Implements all fields from the original Python backend for full feature parity.
/// </summary>
public class AdmissionForm
{
    public int Id { get; set; }
    
    [Required]
    public string Filename { get; set; } = string.Empty;
    
    [Required]
    public string FilePath { get; set; } = string.Empty;
    
    public DateTime UploadDate { get; set; } = DateTime.UtcNow;
    
    [Required]
    public string OcrProvider { get; set; } = "google-vision";
    
    public FormStatus Status { get; set; } = FormStatus.Uploaded;
    
    public int? StudentProfileId { get; set; }
    public StudentProfile? StudentProfile { get; set; }
    
    public string? ExtractedDataJson { get; set; }

    // Sync tracking fields
    public SyncStatus SyncStatus { get; set; } = SyncStatus.PendingCreate;
    public Guid? ServerId { get; set; }
    public DateTime LastModifiedUtc { get; set; } = DateTime.UtcNow;
    public DateTime? SyncedUtc { get; set; }

    public ICollection<StudentDocument> Documents { get; set; } = new List<StudentDocument>();

    // ============================================
    // PAGE 1: ACADEMIC & ADMISSION DETAILS
    // ============================================
    public string? AcademicSession { get; set; }
    public string? Course { get; set; }
    public string? AdmissionCategory { get; set; }
    public string? DuPortalFormNumber { get; set; }
    public string? CuetScore { get; set; }
    public string? CollegeRollNo { get; set; }
    public string? DateOfAdmission { get; set; }
    
    // ============================================
    // PAGE 1: PERSONAL DETAILS
    // ============================================
    public string? FirstName { get; set; }
    public string? MiddleName { get; set; }
    public string? Surname { get; set; }
    public string? StudentName { get; set; }
    public string? Gender { get; set; }
    public string? DateOfBirth { get; set; }
    public string? Category { get; set; }
    public string? Nationality { get; set; }
    public string? Religion { get; set; }
    public string? AadharNumber { get; set; }
    public string? BloodGroup { get; set; }
    public string? BelowPovertyLine { get; set; }
    public string? AnnualIncome { get; set; }
    public string? MinorityCategory { get; set; }
    
    // ============================================
    // ADDRESS DETAILS
    // ============================================
    public string? PermanentAddress { get; set; }
    public string? PermanentState { get; set; }
    public string? PermanentPincode { get; set; }
    public string? CorrespondenceAddress { get; set; }
    public string? CorrespondenceState { get; set; }
    public string? CorrespondencePincode { get; set; }
    public string? Pincode { get; set; }
    
    // Additional address lines
    public string? PermanentAddressLine1 { get; set; }
    public string? PermanentAddressLine2 { get; set; }
    public string? PermanentAddressLine3 { get; set; }
    public string? CorrespondenceAddressLine1 { get; set; }
    public string? CorrespondenceAddressLine2 { get; set; }
    public string? CorrespondenceAddressLine3 { get; set; }

    // Contact Details
    public string? PhoneNumber { get; set; }
    public string? AlternatePhone { get; set; }
    public string? Email { get; set; }
    public string? EmergencyContactName { get; set; }
    public string? EmergencyContactPhone { get; set; }
    
    // ============================================
    // PARENT NAMES & OCCUPATION
    // ============================================
    public string? MotherName { get; set; }
    public string? FatherName { get; set; }
    public string? MotherOccupation { get; set; }
    public string? FatherOccupation { get; set; }
    public string? MotherDesignation { get; set; }
    public string? FatherDesignation { get; set; }
    public string? MotherMobile { get; set; }
    public string? FatherMobile { get; set; }
    public string? MotherPhone { get; set; }
    public string? FatherPhone { get; set; }
    public string? MotherEmail { get; set; }
    public string? FatherEmail { get; set; }
    public string? MotherOrganization { get; set; }
    public string? FatherOrganization { get; set; }
    public string? MotherAnnualIncome { get; set; }
    public string? FatherAnnualIncome { get; set; }
    public string? MotherLandlineCode { get; set; }
    public string? MotherLandline { get; set; }
    public string? FatherLandlineCode { get; set; }
    public string? FatherLandline { get; set; }

    // ============================================
    // LOCAL GUARDIAN'S DETAILS
    // ============================================
    public string? GuardianName { get; set; }
    public string? GuardianAddress { get; set; }
    public string? GuardianMobile { get; set; }
    public string? GuardianEmail { get; set; }
    public string? GuardianRelation { get; set; }
    public string? GuardianLandlineCode { get; set; }
    public string? GuardianLandline { get; set; }
    public string? GuardianOrganization { get; set; }

    // ============================================
    // CUET MARKS TABLE
    // ============================================
    public string? CuetSubject1 { get; set; }
    public string? CuetTotalScore1 { get; set; }
    public string? CuetScoreObtained1 { get; set; }
    public string? CuetSubject2 { get; set; }
    public string? CuetTotalScore2 { get; set; }
    public string? CuetScoreObtained2 { get; set; }
    public string? CuetSubject3 { get; set; }
    public string? CuetTotalScore3 { get; set; }
    public string? CuetScoreObtained3 { get; set; }
    public string? CuetSubject4 { get; set; }
    public string? CuetTotalScore4 { get; set; }
    public string? CuetScoreObtained4 { get; set; }
    public string? CuetSubject5 { get; set; }
    public string? CuetTotalScore5 { get; set; }
    public string? CuetScoreObtained5 { get; set; }
    public string? CuetSubject6 { get; set; }
    public string? CuetTotalScore6 { get; set; }
    public string? CuetScoreObtained6 { get; set; }
    public string? CuetTotalScoreAll { get; set; }
    public string? CuetScoreObtainedAll { get; set; }

    // ============================================
    // QUALIFYING EXAMINATION
    // ============================================
    public string? TwelfthYear { get; set; }
    public string? TwelfthBoard { get; set; }
    public string? TwelfthRollNumber { get; set; }
    public string? TwelfthInstitution { get; set; }
    public string? TwelfthPercentage { get; set; }
    public string? HindiStudiedUpto { get; set; }
    public string? Class12Percentage { get; set; }
    public string? Class12RollNo { get; set; }
    public string? Class12Institution { get; set; }
    
    // 10th class details
    public string? TenthBoard { get; set; }
    public string? TenthYear { get; set; }
    public string? TenthPercentage { get; set; }
    public string? TenthSchool { get; set; }
    
    // Other Info
    public string? DuEnrollmentNumber { get; set; }
    public string? HindiMediumPreference { get; set; }
    public string? DeclarationDate { get; set; }
    public string? DeclarationPlace { get; set; }
    
    // Personal fields
    public string? LocalAddress { get; set; }

    // ============================================
    // CERTIFICATE DETAILS
    // ============================================
    public string? CategoryCertificateAuthority { get; set; }
    public string? CategoryCertificateNumber { get; set; }
    public string? CategoryCertificateDate { get; set; }
    public string? DisabilityType { get; set; }
    public string? DisabilityPercentage { get; set; }
    public string? UdidNumber { get; set; }
    
    // ============================================
    // DOCUMENT CHECKLIST
    // ============================================
    public bool? DocAdmissionForm { get; set; }
    public bool? DocUndertakingRagging { get; set; }
    public bool? DocPhotographs { get; set; }
    public bool? DocCuetScorecard { get; set; }
    public bool? DocClassXiiMarksheet { get; set; }
    public bool? DocClassXCertificate { get; set; }
    public bool? DocClassXiiCertificate { get; set; }
    public bool? DocCharacterCertificate { get; set; }
    public bool? DocCasteCertificate { get; set; }
    public bool? DocMigrationCertificate { get; set; }
    public bool? DocTransferCertificate { get; set; }
    public bool? DocGapCertificate { get; set; }
    public bool? DocIncomeCertificate { get; set; }
    public bool? DocDomicileCertificate { get; set; }
    public bool? DocAadharCard { get; set; }
    public bool? DocMedicalFitness { get; set; }
    
    // ============================================
    // DECLARATIONS
    // ============================================
    public string? StudentDeclarationName { get; set; }
    public string? StudentDeclarationDate { get; set; }
    public string? StudentDeclarationPlace { get; set; }
    public string? ParentGuardianName { get; set; }
    public string? ParentGuardianRelationship { get; set; }
    public string? ParentGuardianCandidateName { get; set; }
    public string? ParentGuardianCourse { get; set; }
    public string? ParentGuardianDate { get; set; }
    public string? ParentGuardianPlace { get; set; }
    
    // ============================================
    // VERIFICATION
    // ============================================
}
