using System;
using System.Collections.Generic;
using System.Linq;
using System.Net.Http;
using System.Net.Http.Json;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.EntityFrameworkCore;
using OCRAdmissionForms.Core.Data;
using OCRAdmissionForms.Core.Entities;

namespace OCRAdmissionForms.Core.Services;

/// <summary>
/// Handles synchronization between local SQLite and remote PostgreSQL server
/// </summary>
public class SyncService : IDisposable
{
    private readonly string? _serverUrl;
    private readonly HttpClient _httpClient;
    private Timer? _syncTimer;
    private bool _isSyncing;
    private readonly object _syncLock = new();

    public event EventHandler<SyncEventArgs>? SyncStatusChanged;
    public event EventHandler<SyncConflictEventArgs>? ConflictDetected;

    public bool IsOnline { get; private set; }
    public DateTime? LastSyncTime { get; private set; }
    public int PendingChangesCount { get; private set; }

    public SyncService(string? serverUrl = null)
    {
        _serverUrl = serverUrl;
        _httpClient = new HttpClient();
        if (!string.IsNullOrEmpty(serverUrl))
        {
            _httpClient.BaseAddress = new Uri(serverUrl);
        }
    }

    /// <summary>
    /// Start automatic background sync at specified interval
    /// </summary>
    public void StartAutoSync(TimeSpan interval)
    {
        _syncTimer?.Dispose();
        _syncTimer = new Timer(async _ => await SyncAsync(), null, TimeSpan.Zero, interval);
    }

    /// <summary>
    /// Stop automatic sync
    /// </summary>
    public void StopAutoSync()
    {
        _syncTimer?.Dispose();
        _syncTimer = null;
    }

    /// <summary>
    /// Check if server is reachable
    /// </summary>
    public async Task<bool> CheckConnectivityAsync()
    {
        if (string.IsNullOrEmpty(_serverUrl)) return false;
        
        try
        {
            var response = await _httpClient.GetAsync("api/health");
            IsOnline = response.IsSuccessStatusCode;
            return IsOnline;
        }
        catch
        {
            IsOnline = false;
            return false;
        }
    }

    /// <summary>
    /// Perform full sync cycle
    /// </summary>
    public async Task<SyncResult> SyncAsync()
    {
        if (_isSyncing) return new SyncResult { Success = false, Message = "Sync already in progress" };

        lock (_syncLock)
        {
            if (_isSyncing) return new SyncResult { Success = false, Message = "Sync already in progress" };
            _isSyncing = true;
        }

        try
        {
            OnSyncStatusChanged("Checking connectivity...");
            
            if (!await CheckConnectivityAsync())
            {
                OnSyncStatusChanged("Offline - changes queued");
                return new SyncResult { Success = false, Message = "Server unreachable", IsOffline = true };
            }

            var result = new SyncResult();

            // Step 1: Push local changes
            OnSyncStatusChanged("Pushing local changes...");
            var pushResult = await PushLocalChangesAsync();
            result.PushedCount = pushResult.Count;

            // Step 2: Pull remote changes
            OnSyncStatusChanged("Pulling remote changes...");
            var pullResult = await PullRemoteChangesAsync();
            result.PulledCount = pullResult.Count;

            // Step 3: Process sync queue
            OnSyncStatusChanged("Processing queue...");
            await ProcessSyncQueueAsync();

            LastSyncTime = DateTime.UtcNow;
            result.Success = true;
            result.Message = $"Synced {pushResult.Count} up, {pullResult.Count} down";
            
            OnSyncStatusChanged($"Synced at {LastSyncTime:HH:mm}");
            
            return result;
        }
        catch (Exception ex)
        {
            OnSyncStatusChanged($"Sync error: {ex.Message}");
            return new SyncResult { Success = false, Message = ex.Message };
        }
        finally
        {
            _isSyncing = false;
        }
    }

    /// <summary>
    /// Queue a change for sync when offline
    /// </summary>
    public async Task QueueChangeAsync<T>(T entity, string operation) where T : SyncableEntity
    {
        using var context = new AppDbContext();
        
        var queueItem = new SyncQueueItem
        {
            EntityType = typeof(T).Name,
            EntityId = GetEntityId(entity),
            Operation = operation,
            SerializedData = JsonSerializer.Serialize(entity),
            QueuedUtc = DateTime.UtcNow
        };
        
        context.SyncQueue.Add(queueItem);
        await context.SaveChangesAsync();
        
        PendingChangesCount++;
    }

    private async Task<List<SyncableEntity>> PushLocalChangesAsync()
    {
        var pushed = new List<SyncableEntity>();
        using var context = new AppDbContext();

        // Get all entities pending sync
        var pendingForms = await context.AdmissionForms
            .Where(f => f.SyncStatus != SyncStatus.Synced)
            .ToListAsync();

        foreach (var form in pendingForms)
        {
            try
            {
                HttpResponseMessage response;
                if (form.SyncStatus == SyncStatus.PendingCreate)
                {
                    response = await _httpClient.PostAsJsonAsync("api/forms", form);
                }
                else if (form.SyncStatus == SyncStatus.PendingUpdate)
                {
                    response = await _httpClient.PutAsJsonAsync($"api/forms/{form.ServerId}", form);
                }
                else if (form.SyncStatus == SyncStatus.PendingDelete)
                {
                    response = await _httpClient.DeleteAsync($"api/forms/{form.ServerId}");
                }
                else continue;

                if (response.IsSuccessStatusCode)
                {
                    if (form.SyncStatus == SyncStatus.PendingCreate)
                    {
                        var serverEntity = await response.Content.ReadFromJsonAsync<AdmissionForm>();
                        form.ServerId = serverEntity?.ServerId;
                    }
                    form.SyncStatus = SyncStatus.Synced;
                    form.SyncedUtc = DateTime.UtcNow;
                    pushed.Add(form);
                }
            }
            catch
            {
                // Will retry on next sync
            }
        }

        await context.SaveChangesAsync();
        return pushed;
    }

    private async Task<List<SyncableEntity>> PullRemoteChangesAsync()
    {
        var pulled = new List<SyncableEntity>();
        using var context = new AppDbContext();

        try
        {
            var lastSync = LastSyncTime ?? DateTime.MinValue;
            var remoteForms = await _httpClient.GetFromJsonAsync<List<AdmissionForm>>(
                $"api/forms?modifiedSince={lastSync:o}");

            if (remoteForms != null)
            {
                foreach (var remoteForm in remoteForms)
                {
                    var localForm = await context.AdmissionForms
                        .FirstOrDefaultAsync(f => f.ServerId == remoteForm.ServerId);

                    if (localForm == null)
                    {
                        // New record from server
                        remoteForm.SyncStatus = SyncStatus.Synced;
                        remoteForm.SyncedUtc = DateTime.UtcNow;
                        context.AdmissionForms.Add(remoteForm);
                        pulled.Add(remoteForm);
                    }
                    else if (localForm.SyncStatus == SyncStatus.Synced)
                    {
                        // Update local with server version
                        UpdateLocalFromRemote(localForm, remoteForm);
                        localForm.SyncedUtc = DateTime.UtcNow;
                        pulled.Add(localForm);
                    }
                    else
                    {
                        // Conflict: both modified
                        OnConflictDetected(localForm, remoteForm);
                    }
                }
            }

            await context.SaveChangesAsync();
        }
        catch
        {
            // Will retry on next sync
        }

        return pulled;
    }

    private async Task ProcessSyncQueueAsync()
    {
        using var context = new AppDbContext();
        
        var queueItems = await context.SyncQueue
            .OrderBy(q => q.QueuedUtc)
            .Take(50)
            .ToListAsync();

        foreach (var item in queueItems)
        {
            try
            {
                var success = await ProcessQueueItemAsync(item);
                if (success)
                {
                    context.SyncQueue.Remove(item);
                    PendingChangesCount--;
                }
                else
                {
                    item.RetryCount++;
                }
            }
            catch (Exception ex)
            {
                item.RetryCount++;
                item.LastError = ex.Message;
            }
        }

        await context.SaveChangesAsync();
    }

    private async Task<bool> ProcessQueueItemAsync(SyncQueueItem item)
    {
        HttpResponseMessage response;
        
        switch (item.Operation)
        {
            case "CREATE":
                response = await _httpClient.PostAsync(
                    $"api/{item.EntityType.ToLower()}s",
                    new StringContent(item.SerializedData ?? "{}", System.Text.Encoding.UTF8, "application/json"));
                break;
            case "UPDATE":
                response = await _httpClient.PutAsync(
                    $"api/{item.EntityType.ToLower()}s/{item.EntityId}",
                    new StringContent(item.SerializedData ?? "{}", System.Text.Encoding.UTF8, "application/json"));
                break;
            case "DELETE":
                response = await _httpClient.DeleteAsync($"api/{item.EntityType.ToLower()}s/{item.EntityId}");
                break;
            default:
                return false;
        }

        return response.IsSuccessStatusCode;
    }

    private static int GetEntityId<T>(T entity) where T : SyncableEntity
    {
        return entity switch
        {
            AdmissionForm f => f.Id,
            StudentProfile p => p.Id,
            StudentDocument d => d.Id,
            _ => 0
        };
    }

    private static void UpdateLocalFromRemote(AdmissionForm local, AdmissionForm remote)
    {
        local.StudentName = remote.StudentName;
        local.CollegeRollNo = remote.CollegeRollNo;
        local.Course = remote.Course;
        // ... copy other fields
        local.LastModifiedUtc = remote.LastModifiedUtc;
    }

    private void OnSyncStatusChanged(string message)
    {
        SyncStatusChanged?.Invoke(this, new SyncEventArgs { Message = message });
    }

    private void OnConflictDetected(SyncableEntity local, SyncableEntity remote)
    {
        ConflictDetected?.Invoke(this, new SyncConflictEventArgs 
        { 
            LocalEntity = local, 
            RemoteEntity = remote 
        });
    }

    public void Dispose()
    {
        _syncTimer?.Dispose();
        _httpClient.Dispose();
    }
}

public class SyncResult
{
    public bool Success { get; set; }
    public string? Message { get; set; }
    public bool IsOffline { get; set; }
    public int PushedCount { get; set; }
    public int PulledCount { get; set; }
}

public class SyncEventArgs : EventArgs
{
    public string Message { get; set; } = string.Empty;
}

public class SyncConflictEventArgs : EventArgs
{
    public SyncableEntity? LocalEntity { get; set; }
    public SyncableEntity? RemoteEntity { get; set; }
}
