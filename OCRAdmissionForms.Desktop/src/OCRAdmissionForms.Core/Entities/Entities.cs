namespace OCRAdmissionForms.Core.Entities;

public enum FormStatus
{
    Uploaded,
    Extracting,
    Extracted,
    Verified,
    Error
}

public enum DocumentCategory
{
    IdProof,
    AcademicCertificate,
    MedicalCertificate,
    BirthCertificate,
    IncomeCertificate,
    CasteCertificate,
    Other
}

/// <summary>
/// Specific document types for the SRCC admission checklist
/// </summary>
public enum DocumentType
{
    AdmissionForm,
    AntiRaggingUndertaking,
    StudentPhotograph,
    CuetScorecard,
    ClassXiiMarksheet,
    ClassXCertificate,
    ClassXiiCertificate,
    CharacterCertificate,
    MigrationCertificate,
    TransferCertificate,
    GapCertificate,
    IncomeCertificate,
    DomicileCertificate,
    AadharCard,
    MedicalFitness,
    CasteCertificate,
    PhotoIdProof,
    Other
}

public enum SyncStatus
{
    Synced,
    PendingCreate,
    PendingUpdate,
    PendingDelete,
    Conflict
}

public enum UserRole
{
    Admin,
    Staff,
    Viewer
}

/// <summary>
/// Base entity with sync tracking fields
/// </summary>
public abstract class SyncableEntity
{
    public SyncStatus SyncStatus { get; set; } = SyncStatus.PendingCreate;
    public Guid? ServerId { get; set; }
    public DateTime LastModifiedUtc { get; set; } = DateTime.UtcNow;
    public DateTime? SyncedUtc { get; set; }
}

public class User
{
    public int Id { get; set; }
    public string Username { get; set; } = string.Empty;
    public string PasswordHash { get; set; } = string.Empty;
    public string Salt { get; set; } = string.Empty;
    public string FullName { get; set; } = string.Empty;
    public string? Email { get; set; }
    public UserRole Role { get; set; } = UserRole.Viewer;
    public string? Department { get; set; }
    public bool IsActive { get; set; } = true;
    public DateTime CreatedDate { get; set; } = DateTime.UtcNow;
    public DateTime? LastLoginDate { get; set; }
}

public class StudentProfile : SyncableEntity
{
    public int Id { get; set; }
    public string StudentName { get; set; } = string.Empty;
    public string? AadharNumber { get; set; }
    public string? RollNumber { get; set; }
    public DateTime CreatedDate { get; set; } = DateTime.UtcNow;
    public DateTime UpdatedDate { get; set; } = DateTime.UtcNow;

    public ICollection<AdmissionForm> Forms { get; set; } = new List<AdmissionForm>();
    public ICollection<StudentDocument> Documents { get; set; } = new List<StudentDocument>();
}

public class AdmissionForm : SyncableEntity
{
    public int Id { get; set; }
    public string Filename { get; set; } = string.Empty;
    public string FilePath { get; set; } = string.Empty;
    public DateTime UploadDate { get; set; } = DateTime.UtcNow;
    public string OcrProvider { get; set; } = "google-vision";
    public FormStatus Status { get; set; } = FormStatus.Uploaded;

    public int? StudentProfileId { get; set; }
    public StudentProfile? StudentProfile { get; set; }

    public string? ExtractedDataJson { get; set; }

    // ============================================
    // ACADEMIC & ADMISSION DETAILS (7 fields)
    // ============================================
    public string? AcademicSession { get; set; }
    public string? Course { get; set; }
    public string? AdmissionCategory { get; set; }
    public string? DuPortalFormNumber { get; set; }
    public string? CuetScore { get; set; }
    public string? CollegeRollNo { get; set; }
    public string? DateOfAdmission { get; set; }

    // ============================================
    // PERSONAL DETAILS (12 fields)
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
    // ADDRESS (6 fields)
    // ============================================
    public string? PermanentAddress { get; set; }
    public string? PermanentState { get; set; }
    public string? PermanentPincode { get; set; }
    public string? CorrespondenceAddress { get; set; }
    public string? CorrespondenceState { get; set; }
    public string? CorrespondencePincode { get; set; }
    public string? Pincode { get; set; } // Shortcut

    // ============================================
    // CONTACT (3 fields)
    // ============================================
    public string? PhoneNumber { get; set; }
    public string? AlternatePhone { get; set; }
    public string? Email { get; set; }

    // ============================================
    // PARENTS (10 fields)
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

    // ============================================
    // GUARDIAN (5 fields)
    // ============================================
    public string? GuardianName { get; set; }
    public string? GuardianAddress { get; set; }
    public string? GuardianMobile { get; set; }
    public string? GuardianEmail { get; set; }
    public string? GuardianRelation { get; set; }

    // ============================================
    // CLASS XII DETAILS (6 fields)
    // ============================================
    public string? TwelfthYear { get; set; }
    public string? TwelfthBoard { get; set; }
    public string? TwelfthRollNumber { get; set; }
    public string? TwelfthInstitution { get; set; }
    public string? TwelfthPercentage { get; set; }
    public string? HindiStudiedUpto { get; set; }

    // ============================================
    // OTHER INFO (3 fields)
    // ============================================
    public string? DuEnrollmentNumber { get; set; }
    public string? HindiMediumPreference { get; set; }
    public string? DeclarationDate { get; set; }
    public string? DeclarationPlace { get; set; }

    // ============================================
    // CERTIFICATE DETAILS (5 fields)
    // ============================================
    public string? CategoryCertificateAuthority { get; set; }
    public string? CategoryCertificateNumber { get; set; }
    public string? CategoryCertificateDate { get; set; }
    public string? DisabilityType { get; set; }
    public string? DisabilityPercentage { get; set; }
    public string? UdidNumber { get; set; }

    // ============================================
    // DOCUMENT CHECKLIST (9 fields)
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
    // ADDITIONAL PERSONAL FIELDS (6 fields)
    // ============================================
    public string? LocalAddress { get; set; }
    public string? MotherAnnualIncome { get; set; }
    public string? FatherAnnualIncome { get; set; }
    public string? Class12Percentage { get; set; }
    public string? Class12RollNo { get; set; }
    public string? Class12Institution { get; set; }

    // ============================================
    // CUET SUBJECT DETAILS (18 fields) - NEW
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
    // 10TH CLASS DETAILS (4 fields) - NEW
    // ============================================
    public string? TenthBoard { get; set; }
    public string? TenthYear { get; set; }
    public string? TenthPercentage { get; set; }
    public string? TenthSchool { get; set; }

    // ============================================
    // ADDRESS LINES (6 fields) - NEW
    // ============================================
    public string? PermanentAddressLine1 { get; set; }
    public string? PermanentAddressLine2 { get; set; }
    public string? PermanentAddressLine3 { get; set; }
    public string? CorrespondenceAddressLine1 { get; set; }
    public string? CorrespondenceAddressLine2 { get; set; }
    public string? CorrespondenceAddressLine3 { get; set; }

    // ============================================
    // LANDLINE PHONES (6 fields) - NEW
    // ============================================
    public string? MotherLandlineCode { get; set; }
    public string? MotherLandline { get; set; }
    public string? FatherLandlineCode { get; set; }
    public string? FatherLandline { get; set; }
    public string? GuardianLandlineCode { get; set; }
    public string? GuardianLandline { get; set; }
    public string? GuardianOrganization { get; set; }

    // ============================================
    // EMERGENCY CONTACT (2 fields) - NEW
    // ============================================
    public string? EmergencyContactName { get; set; }
    public string? EmergencyContactPhone { get; set; }

    // ============================================
    // DECLARATIONS (9 fields) - NEW
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
    public DateTime? VerifiedDate { get; set; }
    public string? VerifiedBy { get; set; }

    public ICollection<StudentDocument> Documents { get; set; } = new List<StudentDocument>();
}

public class StudentDocument : SyncableEntity
{
    public int Id { get; set; }
    public string Filename { get; set; } = string.Empty;
    public string FilePath { get; set; } = string.Empty;
    public DateTime UploadDate { get; set; } = DateTime.UtcNow;
    public DocumentCategory DocumentCategory { get; set; }
    public DocumentType DocumentType { get; set; } = DocumentType.Other;
    public string? Description { get; set; }
    public long FileSize { get; set; }
    
    /// <summary>
    /// Page number in the source PDF (1-indexed), if this document was extracted from a multi-page PDF
    /// </summary>
    public int? SourcePageNumber { get; set; }
    
    /// <summary>
    /// Path to the thumbnail image for quick preview
    /// </summary>
    public string? ThumbnailPath { get; set; }

    public int? FormId { get; set; }
    public AdmissionForm? Form { get; set; }

    public int? StudentProfileId { get; set; }
    public StudentProfile? StudentProfile { get; set; }
}

/// <summary>
/// Queue item for offline sync operations
/// </summary>
public class SyncQueueItem
{
    public int Id { get; set; }
    public string EntityType { get; set; } = string.Empty;
    public int EntityId { get; set; }
    public string Operation { get; set; } = string.Empty; // CREATE, UPDATE, DELETE
    public string? SerializedData { get; set; }
    public DateTime QueuedUtc { get; set; } = DateTime.UtcNow;
    public int RetryCount { get; set; } = 0;
    public string? LastError { get; set; }
}

