using Microsoft.EntityFrameworkCore;
using OCRAdmissionForms.Core.Data;
using OCRAdmissionForms.Core.Entities;

namespace OCRAdmissionForms.Core.Services;

/// <summary>
/// Service for searching, sorting, and filtering data
/// </summary>
public class SearchService
{
    /// <summary>
    /// Search students by name, roll number, or Aadhar
    /// </summary>
    public async Task<List<StudentProfile>> SearchStudentsAsync(
        string? query = null,
        string? sortBy = null,
        bool ascending = true,
        int page = 1,
        int pageSize = 20)
    {
        using var context = new AppDbContext();
        IQueryable<StudentProfile> queryable = context.StudentProfiles;

        // Apply search filter
        if (!string.IsNullOrWhiteSpace(query))
        {
            var lowerQuery = query.ToLower();
            queryable = queryable.Where(s =>
                (s.StudentName != null && s.StudentName.ToLower().Contains(lowerQuery)) ||
                (s.RollNumber != null && s.RollNumber.ToLower().Contains(lowerQuery)) ||
                (s.AadharNumber != null && s.AadharNumber.Contains(lowerQuery)));
        }

        // Apply sorting
        queryable = sortBy?.ToLower() switch
        {
            "name" => ascending 
                ? queryable.OrderBy(s => s.StudentName) 
                : queryable.OrderByDescending(s => s.StudentName),
            "roll" => ascending 
                ? queryable.OrderBy(s => s.RollNumber) 
                : queryable.OrderByDescending(s => s.RollNumber),
            "date" => ascending 
                ? queryable.OrderBy(s => s.CreatedDate) 
                : queryable.OrderByDescending(s => s.CreatedDate),
            _ => queryable.OrderByDescending(s => s.CreatedDate)
        };

        // Apply pagination
        return await queryable
            .Skip((page - 1) * pageSize)
            .Take(pageSize)
            .ToListAsync();
    }

    /// <summary>
    /// Search admission forms with filters
    /// </summary>
    public async Task<List<AdmissionForm>> SearchFormsAsync(
        string? query = null,
        FormStatus? status = null,
        string? course = null,
        DateTime? fromDate = null,
        DateTime? toDate = null,
        string? sortBy = null,
        bool ascending = true,
        int page = 1,
        int pageSize = 20)
    {
        using var context = new AppDbContext();
        IQueryable<AdmissionForm> queryable = context.AdmissionForms;

        // Apply text search
        if (!string.IsNullOrWhiteSpace(query))
        {
            var lowerQuery = query.ToLower();
            queryable = queryable.Where(f =>
                (f.StudentName != null && f.StudentName.ToLower().Contains(lowerQuery)) ||
                (f.CollegeRollNo != null && f.CollegeRollNo.ToLower().Contains(lowerQuery)) ||
                (f.Email != null && f.Email.ToLower().Contains(lowerQuery)) ||
                (f.PhoneNumber != null && f.PhoneNumber.Contains(lowerQuery)) ||
                (f.AadharNumber != null && f.AadharNumber.Contains(lowerQuery)));
        }

        // Apply status filter
        if (status.HasValue)
        {
            queryable = queryable.Where(f => f.Status == status.Value);
        }

        // Apply course filter
        if (!string.IsNullOrWhiteSpace(course))
        {
            queryable = queryable.Where(f => f.Course != null && f.Course.Contains(course));
        }

        // Apply date range filter
        if (fromDate.HasValue)
        {
            queryable = queryable.Where(f => f.UploadDate >= fromDate.Value);
        }
        if (toDate.HasValue)
        {
            queryable = queryable.Where(f => f.UploadDate <= toDate.Value);
        }

        // Apply sorting
        queryable = sortBy?.ToLower() switch
        {
            "name" => ascending 
                ? queryable.OrderBy(f => f.StudentName) 
                : queryable.OrderByDescending(f => f.StudentName),
            "roll" => ascending 
                ? queryable.OrderBy(f => f.CollegeRollNo) 
                : queryable.OrderByDescending(f => f.CollegeRollNo),
            "course" => ascending 
                ? queryable.OrderBy(f => f.Course) 
                : queryable.OrderByDescending(f => f.Course),
            "status" => ascending 
                ? queryable.OrderBy(f => f.Status) 
                : queryable.OrderByDescending(f => f.Status),
            "date" => ascending 
                ? queryable.OrderBy(f => f.UploadDate) 
                : queryable.OrderByDescending(f => f.UploadDate),
            _ => queryable.OrderByDescending(f => f.UploadDate)
        };

        // Apply pagination
        return await queryable
            .Skip((page - 1) * pageSize)
            .Take(pageSize)
            .ToListAsync();
    }

    /// <summary>
    /// Get total count for pagination
    /// </summary>
    public async Task<int> GetStudentCountAsync(string? query = null)
    {
        using var context = new AppDbContext();
        IQueryable<StudentProfile> queryable = context.StudentProfiles;

        if (!string.IsNullOrWhiteSpace(query))
        {
            var lowerQuery = query.ToLower();
            queryable = queryable.Where(s =>
                (s.StudentName != null && s.StudentName.ToLower().Contains(lowerQuery)) ||
                (s.RollNumber != null && s.RollNumber.ToLower().Contains(lowerQuery)) ||
                (s.AadharNumber != null && s.AadharNumber.Contains(lowerQuery)));
        }

        return await queryable.CountAsync();
    }

    /// <summary>
    /// Get form count with filters
    /// </summary>
    public async Task<int> GetFormCountAsync(
        string? query = null,
        FormStatus? status = null,
        string? course = null,
        DateTime? fromDate = null,
        DateTime? toDate = null)
    {
        using var context = new AppDbContext();
        IQueryable<AdmissionForm> queryable = context.AdmissionForms;

        if (!string.IsNullOrWhiteSpace(query))
        {
            var lowerQuery = query.ToLower();
            queryable = queryable.Where(f =>
                (f.StudentName != null && f.StudentName.ToLower().Contains(lowerQuery)) ||
                (f.CollegeRollNo != null && f.CollegeRollNo.ToLower().Contains(lowerQuery)));
        }

        if (status.HasValue)
            queryable = queryable.Where(f => f.Status == status.Value);

        if (!string.IsNullOrWhiteSpace(course))
            queryable = queryable.Where(f => f.Course != null && f.Course.Contains(course));

        if (fromDate.HasValue)
            queryable = queryable.Where(f => f.UploadDate >= fromDate.Value);

        if (toDate.HasValue)
            queryable = queryable.Where(f => f.UploadDate <= toDate.Value);

        return await queryable.CountAsync();
    }

    /// <summary>
    /// Get distinct courses for filter dropdown
    /// </summary>
    public async Task<List<string>> GetDistinctCoursesAsync()
    {
        using var context = new AppDbContext();
        return await context.AdmissionForms
            .Where(f => f.Course != null)
            .Select(f => f.Course!)
            .Distinct()
            .OrderBy(c => c)
            .ToListAsync();
    }

    /// <summary>
    /// Search forms with all available filters (category, gender, religion, etc.)
    /// </summary>
    public async Task<List<AdmissionForm>> SearchFormsFilteredAsync(
        string? query = null,
        FormStatus? status = null,
        string? course = null,
        string? category = null,
        string? gender = null,
        string? religion = null,
        string? bloodGroup = null,
        string? nationality = null,
        string? bpl = null,
        string? sortBy = null,
        bool ascending = true,
        int page = 1,
        int pageSize = 500)
    {
        using var context = new AppDbContext();
        IQueryable<AdmissionForm> queryable = context.AdmissionForms;

        // Text search
        if (!string.IsNullOrWhiteSpace(query))
        {
            var lowerQuery = query.ToLower();
            queryable = queryable.Where(f =>
                (f.StudentName != null && f.StudentName.ToLower().Contains(lowerQuery)) ||
                (f.CollegeRollNo != null && f.CollegeRollNo.ToLower().Contains(lowerQuery)) ||
                (f.Email != null && f.Email.ToLower().Contains(lowerQuery)) ||
                (f.PhoneNumber != null && f.PhoneNumber.Contains(lowerQuery)) ||
                (f.AadharNumber != null && f.AadharNumber.Contains(lowerQuery)) ||
                (f.DuPortalFormNumber != null && f.DuPortalFormNumber.ToLower().Contains(lowerQuery)) ||
                (f.FatherName != null && f.FatherName.ToLower().Contains(lowerQuery)) ||
                (f.MotherName != null && f.MotherName.ToLower().Contains(lowerQuery)));
        }

        // Apply filters
        if (status.HasValue)
            queryable = queryable.Where(f => f.Status == status.Value);

        if (!string.IsNullOrWhiteSpace(course))
            queryable = queryable.Where(f => f.Course != null && f.Course.Contains(course));

        if (!string.IsNullOrWhiteSpace(category))
            queryable = queryable.Where(f => f.Category != null && f.Category.ToLower().Contains(category.ToLower()));

        if (!string.IsNullOrWhiteSpace(gender))
            queryable = queryable.Where(f => f.Gender != null && f.Gender.ToLower() == gender.ToLower());

        if (!string.IsNullOrWhiteSpace(religion))
            queryable = queryable.Where(f => f.Religion != null && f.Religion.ToLower().Contains(religion.ToLower()));

        if (!string.IsNullOrWhiteSpace(bloodGroup))
            queryable = queryable.Where(f => f.BloodGroup != null && f.BloodGroup == bloodGroup);

        if (!string.IsNullOrWhiteSpace(nationality))
        {
            if (nationality == "Other")
                queryable = queryable.Where(f => f.Nationality != null && f.Nationality.ToLower() != "indian");
            else
                queryable = queryable.Where(f => f.Nationality != null && f.Nationality.ToLower().Contains(nationality.ToLower()));
        }

        if (!string.IsNullOrWhiteSpace(bpl))
            queryable = queryable.Where(f => f.BelowPovertyLine != null && f.BelowPovertyLine.ToLower() == bpl.ToLower());

        // Default sort by upload date desc
        queryable = sortBy?.ToLower() switch
        {
            "name" => ascending ? queryable.OrderBy(f => f.StudentName) : queryable.OrderByDescending(f => f.StudentName),
            "roll" => ascending ? queryable.OrderBy(f => f.CollegeRollNo) : queryable.OrderByDescending(f => f.CollegeRollNo),
            "course" => ascending ? queryable.OrderBy(f => f.Course) : queryable.OrderByDescending(f => f.Course),
            "status" => ascending ? queryable.OrderBy(f => f.Status) : queryable.OrderByDescending(f => f.Status),
            "date" => ascending ? queryable.OrderBy(f => f.UploadDate) : queryable.OrderByDescending(f => f.UploadDate),
            _ => queryable.OrderByDescending(f => f.UploadDate)
        };

        return await queryable
            .Skip((page - 1) * pageSize)
            .Take(pageSize)
            .ToListAsync();
    }

    /// <summary>
    /// Global search across all entities
    /// </summary>
    public async Task<GlobalSearchResult> GlobalSearchAsync(string query)
    {
        var result = new GlobalSearchResult();

        if (string.IsNullOrWhiteSpace(query)) return result;

        result.Students = await SearchStudentsAsync(query, pageSize: 10);
        result.Forms = await SearchFormsAsync(query, pageSize: 10);

        return result;
    }
}

public class GlobalSearchResult
{
    public List<StudentProfile> Students { get; set; } = new();
    public List<AdmissionForm> Forms { get; set; } = new();
}
