namespace OCRAdmissionForms.Core.Enums;

public enum UserRole
{
    Admin,
    Staff,
    Viewer
}

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
