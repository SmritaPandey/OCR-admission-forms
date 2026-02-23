using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using OCRAdmissionForms.Core.Enums;

namespace OCRAdmissionForms.Core.Entities;

public class StudentProfile
{
    public int Id { get; set; }
    public string StudentName { get; set; } = string.Empty;
    public string? AadharNumber { get; set; }
    public string? RollNumber { get; set; }
    public DateTime CreatedDate { get; set; } = DateTime.UtcNow;
    public DateTime UpdatedDate { get; set; } = DateTime.UtcNow;

    // Sync tracking fields
    public SyncStatus SyncStatus { get; set; } = SyncStatus.Synced;
    public Guid? ServerId { get; set; }
    public DateTime LastModifiedUtc { get; set; } = DateTime.UtcNow;
    public DateTime? SyncedUtc { get; set; }

    // Relationships
    public ICollection<AdmissionForm> Forms { get; set; } = new List<AdmissionForm>();
    public ICollection<StudentDocument> Documents { get; set; } = new List<StudentDocument>();
}
