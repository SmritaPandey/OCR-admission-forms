using System;

namespace OCRAdmissionForms.Core.Entities;

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
