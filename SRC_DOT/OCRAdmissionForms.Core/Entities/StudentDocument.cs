using System;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using OCRAdmissionForms.Core.Enums;

namespace OCRAdmissionForms.Core.Entities;

public class StudentDocument
{
    public int Id { get; set; }
    
    public string Filename { get; set; } = string.Empty;
    
    public string FilePath { get; set; } = string.Empty;
    
    public DateTime UploadDate { get; set; } = DateTime.UtcNow;
    
    public DocumentCategory DocumentCategory { get; set; }
    public DocumentType DocumentType { get; set; } = DocumentType.Other;
    public string? Description { get; set; }
    
    public long FileSize { get; set; }
    
    public int? SourcePageNumber { get; set; }
    public string? ThumbnailPath { get; set; }

    // Sync tracking fields
    public SyncStatus SyncStatus { get; set; } = SyncStatus.Synced;
    public Guid? ServerId { get; set; }
    public DateTime LastModifiedUtc { get; set; } = DateTime.UtcNow;
    public DateTime? SyncedUtc { get; set; }
    
    public int? FormId { get; set; }
    public AdmissionForm? Form { get; set; }
    
    public int? StudentProfileId { get; set; }
    public StudentProfile? StudentProfile { get; set; }
}
