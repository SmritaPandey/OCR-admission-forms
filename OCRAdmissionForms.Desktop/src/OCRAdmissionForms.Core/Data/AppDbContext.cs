using Microsoft.EntityFrameworkCore;
using OCRAdmissionForms.Core.Entities;
using OCRAdmissionForms.Core.Services;

namespace OCRAdmissionForms.Core.Data;

public class AppDbContext : DbContext
{
    public DbSet<User> Users { get; set; }
    public DbSet<StudentProfile> StudentProfiles { get; set; }
    public DbSet<AdmissionForm> AdmissionForms { get; set; }
    public DbSet<StudentDocument> StudentDocuments { get; set; }
    public DbSet<SyncQueueItem> SyncQueue { get; set; }

    private readonly string _dbPath;

    public AppDbContext()
    {
        _dbPath = AppConfig.DatabasePath;
        Directory.CreateDirectory(Path.GetDirectoryName(_dbPath)!);
    }

    public AppDbContext(string dbPath)
    {
        _dbPath = dbPath;
    }

    protected override void OnConfiguring(DbContextOptionsBuilder options)
    {
        options.UseSqlite($"Data Source={_dbPath}");
    }

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        // Users table
        modelBuilder.Entity<User>(entity =>
        {
            entity.ToTable("users");
            entity.HasIndex(e => e.Username).IsUnique();
            entity.HasIndex(e => e.Email);
        });

        // Student Profiles
        modelBuilder.Entity<StudentProfile>(entity =>
        {
            entity.ToTable("student_profiles");
            entity.HasIndex(e => e.StudentName);
            entity.HasIndex(e => e.AadharNumber);
            entity.HasIndex(e => e.RollNumber);
            entity.HasIndex(e => e.SyncStatus);
            entity.HasIndex(e => e.ServerId);
        });

        // Admission Forms
        modelBuilder.Entity<AdmissionForm>(entity =>
        {
            entity.ToTable("admission_forms");
            entity.HasIndex(e => e.CollegeRollNo);
            entity.HasIndex(e => e.Status);
            entity.HasIndex(e => e.SyncStatus);
            entity.HasIndex(e => e.ServerId);
            entity.HasOne(e => e.StudentProfile)
                  .WithMany(s => s.Forms)
                  .HasForeignKey(e => e.StudentProfileId);
        });

        // Student Documents
        modelBuilder.Entity<StudentDocument>(entity =>
        {
            entity.ToTable("student_documents");
            entity.HasIndex(e => e.SyncStatus);
            entity.HasIndex(e => e.ServerId);
            entity.HasOne(e => e.Form)
                  .WithMany(f => f.Documents)
                  .HasForeignKey(e => e.FormId);
            entity.HasOne(e => e.StudentProfile)
                  .WithMany(s => s.Documents)
                  .HasForeignKey(e => e.StudentProfileId);
        });

        // Sync Queue
        modelBuilder.Entity<SyncQueueItem>(entity =>
        {
            entity.ToTable("sync_queue");
            entity.HasIndex(e => e.QueuedUtc);
            entity.HasIndex(e => new { e.EntityType, e.EntityId });
        });
    }

    /// <summary>
    /// Migrate database to add any new columns that don't exist
    /// Call this on app startup to ensure database schema is up to date
    /// </summary>
    public void MigrateDatabase()
    {
        Database.EnsureCreated();
        
        // Add missing columns to admission_forms table
        var missingColumns = new Dictionary<string, string>
        {
            // Parent contact fields
            ["FatherPhone"] = "TEXT",
            ["MotherPhone"] = "TEXT",
            ["FatherMobile"] = "TEXT",
            ["MotherMobile"] = "TEXT",
            ["FatherEmail"] = "TEXT",
            ["MotherEmail"] = "TEXT",
            ["FatherOccupation"] = "TEXT",
            ["MotherOccupation"] = "TEXT",
            ["FatherDesignation"] = "TEXT",
            ["MotherDesignation"] = "TEXT",
            ["FatherOrganization"] = "TEXT",
            ["MotherOrganization"] = "TEXT",
            ["FatherAnnualIncome"] = "TEXT",
            ["MotherAnnualIncome"] = "TEXT",
            
            // Personal fields
            ["MiddleName"] = "TEXT",
            ["BloodGroup"] = "TEXT",

            ["LocalAddress"] = "TEXT",
            ["AnnualIncome"] = "TEXT",
            ["MinorityCategory"] = "TEXT",
            ["BelowPovertyLine"] = "TEXT",
            
            // Address fields
            ["CorrespondenceAddress"] = "TEXT",
            ["CorrespondenceState"] = "TEXT",
            ["CorrespondencePincode"] = "TEXT",
            
            // Class XII fields
            ["TwelfthYear"] = "TEXT",
            ["TwelfthBoard"] = "TEXT",
            ["TwelfthPercentage"] = "TEXT",
            ["TwelfthInstitution"] = "TEXT",
            ["TwelfthRollNumber"] = "TEXT",
            ["HindiStudiedUpto"] = "TEXT",
            ["Class12Percentage"] = "TEXT",
            ["Class12RollNo"] = "TEXT",
            ["Class12Institution"] = "TEXT",
            
            // Guardian fields
            ["GuardianName"] = "TEXT",
            ["GuardianAddress"] = "TEXT",
            ["GuardianMobile"] = "TEXT",
            ["GuardianEmail"] = "TEXT",
            ["GuardianRelation"] = "TEXT",
            
            // Other info
            ["DuEnrollmentNumber"] = "TEXT",
            ["HindiMediumPreference"] = "TEXT",
            ["DeclarationDate"] = "TEXT",
            ["DeclarationPlace"] = "TEXT",
            
            // Certificate details
            ["CategoryCertificateAuthority"] = "TEXT",
            ["CategoryCertificateNumber"] = "TEXT",
            ["CategoryCertificateDate"] = "TEXT",
            ["DisabilityType"] = "TEXT",
            ["DisabilityPercentage"] = "TEXT",
            ["UdidNumber"] = "TEXT",
            
            // Document checklist (15 fields)
            ["DocAdmissionForm"] = "INTEGER",
            ["DocUndertakingRagging"] = "INTEGER",
            ["DocPhotographs"] = "INTEGER",
            ["DocCuetScorecard"] = "INTEGER",
            ["DocClassXiiMarksheet"] = "INTEGER",
            ["DocClassXCertificate"] = "INTEGER",
            ["DocClassXiiCertificate"] = "INTEGER",
            ["DocCharacterCertificate"] = "INTEGER",
            ["DocCasteCertificate"] = "INTEGER",
            ["DocMigrationCertificate"] = "INTEGER",
            ["DocTransferCertificate"] = "INTEGER",
            ["DocGapCertificate"] = "INTEGER",
            ["DocIncomeCertificate"] = "INTEGER",
            ["DocDomicileCertificate"] = "INTEGER",
            ["DocAadharCard"] = "INTEGER",
            ["DocMedicalFitness"] = "INTEGER",
            
            // CUET Subject Details (19 fields) - NEW
            ["CuetSubject1"] = "TEXT",
            ["CuetTotalScore1"] = "TEXT",
            ["CuetScoreObtained1"] = "TEXT",
            ["CuetSubject2"] = "TEXT",
            ["CuetTotalScore2"] = "TEXT",
            ["CuetScoreObtained2"] = "TEXT",
            ["CuetSubject3"] = "TEXT",
            ["CuetTotalScore3"] = "TEXT",
            ["CuetScoreObtained3"] = "TEXT",
            ["CuetSubject4"] = "TEXT",
            ["CuetTotalScore4"] = "TEXT",
            ["CuetScoreObtained4"] = "TEXT",
            ["CuetSubject5"] = "TEXT",
            ["CuetTotalScore5"] = "TEXT",
            ["CuetScoreObtained5"] = "TEXT",
            ["CuetSubject6"] = "TEXT",
            ["CuetTotalScore6"] = "TEXT",
            ["CuetScoreObtained6"] = "TEXT",
            ["CuetTotalScoreAll"] = "TEXT",
            ["CuetScoreObtainedAll"] = "TEXT",
            
            // 10th Class Details (4 fields) - NEW
            ["TenthBoard"] = "TEXT",
            ["TenthYear"] = "TEXT",
            ["TenthPercentage"] = "TEXT",
            ["TenthSchool"] = "TEXT",
            
            // Address Lines (6 fields) - NEW
            ["PermanentAddressLine1"] = "TEXT",
            ["PermanentAddressLine2"] = "TEXT",
            ["PermanentAddressLine3"] = "TEXT",
            ["CorrespondenceAddressLine1"] = "TEXT",
            ["CorrespondenceAddressLine2"] = "TEXT",
            ["CorrespondenceAddressLine3"] = "TEXT",
            
            // Landline Phones (7 fields) - NEW
            ["MotherLandlineCode"] = "TEXT",
            ["MotherLandline"] = "TEXT",
            ["FatherLandlineCode"] = "TEXT",
            ["FatherLandline"] = "TEXT",
            ["GuardianLandlineCode"] = "TEXT",
            ["GuardianLandline"] = "TEXT",
            ["GuardianOrganization"] = "TEXT",
            
            // Emergency Contact (2 fields) - NEW
            ["EmergencyContactName"] = "TEXT",
            ["EmergencyContactPhone"] = "TEXT",
            
            // Declarations (9 fields) - NEW
            ["StudentDeclarationName"] = "TEXT",
            ["StudentDeclarationDate"] = "TEXT",
            ["StudentDeclarationPlace"] = "TEXT",
            ["ParentGuardianName"] = "TEXT",
            ["ParentGuardianRelationship"] = "TEXT",
            ["ParentGuardianCandidateName"] = "TEXT",
            ["ParentGuardianCourse"] = "TEXT",
            ["ParentGuardianDate"] = "TEXT",
            ["ParentGuardianPlace"] = "TEXT",
        };

        foreach (var (column, type) in missingColumns)
        {
            try
            {
                Database.ExecuteSqlRaw($"ALTER TABLE admission_forms ADD COLUMN {column} {type};");
            }
            catch
            {
                // Column already exists, ignore
            }
        }
        
        // Add missing columns to student_documents table
        var docColumns = new Dictionary<string, string>
        {
            ["DocumentType"] = "INTEGER DEFAULT 0",
            ["SourcePageNumber"] = "INTEGER",
            ["ThumbnailPath"] = "TEXT",
        };
        
        foreach (var (column, type) in docColumns)
        {
            try
            {
                Database.ExecuteSqlRaw($"ALTER TABLE student_documents ADD COLUMN {column} {type};");
            }
            catch
            {
                // Column already exists, ignore
            }
        }

        // ===== Retroactive: create StudentProfiles for verified forms without one =====
        try
        {
            var orphanedForms = AdmissionForms
                .Where(f => f.Status == FormStatus.Verified && f.StudentProfileId == null)
                .ToList();

            foreach (var form in orphanedForms)
            {
                var studentName = form.StudentName
                    ?? $"{form.FirstName} {form.MiddleName} {form.Surname}".Trim().Replace("  ", " ");
                var aadhar = form.AadharNumber?.Trim();
                var rollNo = form.CollegeRollNo?.Trim();

                StudentProfile? profile = null;
                if (!string.IsNullOrWhiteSpace(aadhar))
                    profile = StudentProfiles.FirstOrDefault(s => s.AadharNumber == aadhar);
                if (profile == null && !string.IsNullOrWhiteSpace(rollNo))
                    profile = StudentProfiles.FirstOrDefault(s => s.RollNumber == rollNo);
                if (profile == null && !string.IsNullOrWhiteSpace(studentName) && studentName.Length > 0)
                    profile = StudentProfiles.FirstOrDefault(s => s.StudentName == studentName);

                if (profile == null)
                {
                    profile = new StudentProfile
                    {
                        StudentName = !string.IsNullOrWhiteSpace(studentName) ? studentName : "Unknown",
                        AadharNumber = aadhar,
                        RollNumber = rollNo,
                        CreatedDate = DateTime.UtcNow,
                        UpdatedDate = DateTime.UtcNow,
                    };
                    StudentProfiles.Add(profile);
                    SaveChanges();
                }

                form.StudentProfileId = profile.Id;
            }

            if (orphanedForms.Count > 0)
            {
                SaveChanges();
                System.Diagnostics.Debug.WriteLine($"[MigrateDB] Created profiles for {orphanedForms.Count} verified form(s).");
            }
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"[MigrateDB] Retroactive profile creation failed: {ex.Message}");
        }
    }
}

