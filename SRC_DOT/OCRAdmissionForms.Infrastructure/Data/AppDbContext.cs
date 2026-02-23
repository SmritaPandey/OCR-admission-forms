using Microsoft.EntityFrameworkCore;
using OCRAdmissionForms.Core.Entities;

namespace OCRAdmissionForms.Infrastructure.Data;

public class AppDbContext : DbContext
{
    public AppDbContext(DbContextOptions<AppDbContext> options) : base(options)
    {
    }

    public DbSet<User> Users { get; set; }
    public DbSet<AdmissionForm> AdmissionForms { get; set; }
    public DbSet<StudentProfile> StudentProfiles { get; set; }
    public DbSet<StudentDocument> StudentDocuments { get; set; }
    public DbSet<SyncQueueItem> SyncQueue { get; set; }

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        // Users table
        modelBuilder.Entity<User>(entity =>
        {
            entity.ToTable("users");
            entity.HasIndex(e => e.Username).IsUnique();
        });

        // Student Profiles
        modelBuilder.Entity<StudentProfile>(entity =>
        {
            entity.ToTable("student_profiles");
            entity.HasIndex(e => e.StudentName);
            entity.HasIndex(e => e.AadharNumber);
            entity.HasIndex(e => e.RollNumber);
        });

        // Admission Forms
        modelBuilder.Entity<AdmissionForm>(entity =>
        {
            entity.ToTable("admission_forms");
            entity.HasIndex(e => e.CollegeRollNo);
            entity.HasIndex(e => e.Status);
            entity.HasOne(e => e.StudentProfile)
                  .WithMany(s => s.Forms)
                  .HasForeignKey(e => e.StudentProfileId)
                  .OnDelete(DeleteBehavior.SetNull);
        });

        // Student Documents
        modelBuilder.Entity<StudentDocument>(entity =>
        {
            entity.ToTable("student_documents");
            entity.HasOne(e => e.Form)
                  .WithMany(f => f.Documents)
                  .HasForeignKey(e => e.FormId)
                  .OnDelete(DeleteBehavior.Cascade);
            entity.HasOne(e => e.StudentProfile)
                  .WithMany(s => s.Documents)
                  .HasForeignKey(e => e.StudentProfileId)
                  .OnDelete(DeleteBehavior.Restrict);
        });

        // Sync Queue
        modelBuilder.Entity<SyncQueueItem>(entity =>
        {
            entity.ToTable("sync_queue");
            entity.HasIndex(e => e.QueuedUtc);
        });
    }
}
