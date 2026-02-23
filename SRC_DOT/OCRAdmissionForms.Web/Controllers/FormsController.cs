using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using System.Text.Json;
using OCRAdmissionForms.Core.Entities;
using OCRAdmissionForms.Core.Enums;
using OCRAdmissionForms.Core.Interfaces;
using OCRAdmissionForms.Infrastructure.Data;
using OCRAdmissionForms.Infrastructure.Services;

namespace OCRAdmissionForms.Web.Controllers;

[ApiController]
[Route("api/[controller]")]
public class FormsController : ControllerBase
{
    private readonly AppDbContext _context;
    private readonly IOcrService _ocrService;
    private readonly IFormExtractorService _formExtractor;
    private readonly IWebHostEnvironment _env;
    private readonly ILogger<FormsController> _logger;

    public FormsController(
        AppDbContext context,
        IOcrService ocrService,
        IFormExtractorService formExtractor,
        IWebHostEnvironment env,
        ILogger<FormsController> logger)
    {
        _context = context;
        _ocrService = ocrService;
        _formExtractor = formExtractor;
        _env = env;
        _logger = logger;
    }

    /// <summary>
    /// Get all admission forms with pagination
    /// </summary>
    [HttpGet]
    public async Task<ActionResult<IEnumerable<AdmissionForm>>> GetForms(
        [FromQuery] int page = 1,
        [FromQuery] int pageSize = 20,
        [FromQuery] string? status = null,
        [FromQuery] string? search = null)
    {
        var query = _context.AdmissionForms
            .Include(f => f.StudentProfile)
            .AsQueryable();

        // Filter by status
        if (!string.IsNullOrEmpty(status) && Enum.TryParse<FormStatus>(status, true, out var formStatus))
        {
            query = query.Where(f => f.Status == formStatus);
        }

        // Search by name, roll number, or form number
        if (!string.IsNullOrEmpty(search))
        {
            query = query.Where(f =>
                (f.StudentName != null && f.StudentName.Contains(search)) ||
                (f.CollegeRollNo != null && f.CollegeRollNo.Contains(search)) ||
                (f.DuPortalFormNumber != null && f.DuPortalFormNumber.Contains(search)));
        }

        var total = await query.CountAsync();
        var forms = await query
            .OrderByDescending(f => f.UploadDate)
            .Skip((page - 1) * pageSize)
            .Take(pageSize)
            .ToListAsync();

        Response.Headers.Append("X-Total-Count", total.ToString());
        return Ok(forms);
    }

    /// <summary>
    /// Get a specific form by ID
    /// </summary>
    [HttpGet("{id}")]
    public async Task<ActionResult<AdmissionForm>> GetForm(int id)
    {
        var form = await _context.AdmissionForms
            .Include(f => f.StudentProfile)
            .Include(f => f.Documents)
            .FirstOrDefaultAsync(f => f.Id == id);

        if (form == null)
        {
            return NotFound();
        }

        return Ok(form);
    }

    /// <summary>
    /// Upload and process a new form
    /// </summary>
    [HttpPost("upload")]
    public async Task<ActionResult<AdmissionForm>> UploadForm(IFormFile file)
    {
        if (file == null || file.Length == 0)
        {
            return BadRequest("No file provided");
        }

        // Validate file type
        var allowedExtensions = new[] { ".pdf", ".png", ".jpg", ".jpeg", ".tiff" };
        var extension = Path.GetExtension(file.FileName).ToLower();
        if (!allowedExtensions.Contains(extension))
        {
            return BadRequest("Invalid file type. Allowed: PDF, PNG, JPG, JPEG, TIFF");
        }

        try
        {
            // Save file
            var uploadsPath = Path.Combine(_env.ContentRootPath, "uploads");
            Directory.CreateDirectory(uploadsPath);
            
            var fileName = $"{Guid.NewGuid()}{extension}";
            var filePath = Path.Combine(uploadsPath, fileName);
            
            using (var stream = new FileStream(filePath, FileMode.Create))
            {
                await file.CopyToAsync(stream);
            }

            // Create form record
            var form = new AdmissionForm
            {
                Filename = file.FileName,
                FilePath = fileName,
                OcrProvider = "tesseract",
                Status = FormStatus.Uploaded
            };

            _context.AdmissionForms.Add(form);
            await _context.SaveChangesAsync();

            // Start extraction in background (or inline for now)
            _ = Task.Run(async () => await ProcessFormAsync(form.Id, filePath));

            return CreatedAtAction(nameof(GetForm), new { id = form.Id }, form);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error uploading form");
            return StatusCode(500, "Error uploading form");
        }
    }

    /// <summary>
    /// Process/extract a form that was already uploaded
    /// </summary>
    [HttpPost("{id}/extract")]
    public async Task<ActionResult> ExtractForm(int id)
    {
        var form = await _context.AdmissionForms.FindAsync(id);
        if (form == null)
        {
            return NotFound();
        }

        var uploadsPath = Path.Combine(_env.ContentRootPath, "uploads");
        var filePath = Path.Combine(uploadsPath, form.FilePath);

        if (!System.IO.File.Exists(filePath))
        {
            return NotFound("Form file not found");
        }

        await ProcessFormAsync(id, filePath);
        
        var updatedForm = await _context.AdmissionForms.FindAsync(id);
        return Ok(updatedForm);
    }

    /// <summary>
    /// Update form fields
    /// </summary>
    [HttpPut("{id}")]
    public async Task<ActionResult> UpdateForm(int id, [FromBody] Dictionary<string, string?> updates)
    {
        var form = await _context.AdmissionForms.FindAsync(id);
        if (form == null)
        {
            return NotFound();
        }

        // Use reflection to update properties
        var formType = typeof(AdmissionForm);
        foreach (var (key, value) in updates)
        {
            var property = formType.GetProperty(key);
            if (property != null && property.CanWrite)
            {
                property.SetValue(form, value);
            }
        }

        await _context.SaveChangesAsync();
        return Ok(form);
    }

    /// <summary>
    /// Mark form as verified
    /// </summary>
    [HttpPost("{id}/verify")]
    public async Task<ActionResult> VerifyForm(int id, [FromQuery] string verifiedBy = "Admin")
    {
        var form = await _context.AdmissionForms.FindAsync(id);
        if (form == null)
        {
            return NotFound();
        }

        form.Status = FormStatus.Verified;

        // Create/update student profile
        if (form.StudentProfileId == null && !string.IsNullOrEmpty(form.StudentName))
        {
            var profile = new StudentProfile
            {
                StudentName = form.StudentName,
                AadharNumber = form.AadharNumber,
                RollNumber = form.CollegeRollNo
            };
            _context.StudentProfiles.Add(profile);
            await _context.SaveChangesAsync();
            form.StudentProfileId = profile.Id;
        }

        await _context.SaveChangesAsync();
        return Ok(form);
    }

    /// <summary>
    /// Delete a form
    /// </summary>
    [HttpDelete("{id}")]
    public async Task<ActionResult> DeleteForm(int id)
    {
        var form = await _context.AdmissionForms
            .Include(f => f.Documents)
            .FirstOrDefaultAsync(f => f.Id == id);
            
        if (form == null)
        {
            return NotFound();
        }

        // Delete file
        var uploadsPath = Path.Combine(_env.ContentRootPath, "uploads");
        var filePath = Path.Combine(uploadsPath, form.FilePath);
        if (System.IO.File.Exists(filePath))
        {
            System.IO.File.Delete(filePath);
        }

        _context.AdmissionForms.Remove(form);
        await _context.SaveChangesAsync();

        return NoContent();
    }

    /// <summary>
    /// Get form statistics
    /// </summary>
    [HttpGet("stats")]
    public async Task<ActionResult> GetStats()
    {
        var stats = new
        {
            Total = await _context.AdmissionForms.CountAsync(),
            Uploaded = await _context.AdmissionForms.CountAsync(f => f.Status == FormStatus.Uploaded),
            Extracting = await _context.AdmissionForms.CountAsync(f => f.Status == FormStatus.Extracting),
            Extracted = await _context.AdmissionForms.CountAsync(f => f.Status == FormStatus.Extracted),
            Verified = await _context.AdmissionForms.CountAsync(f => f.Status == FormStatus.Verified),
            Error = await _context.AdmissionForms.CountAsync(f => f.Status == FormStatus.Error)
        };
        return Ok(stats);
    }

    #region Private Methods

    private async Task ProcessFormAsync(int formId, string filePath)
    {
        var form = await _context.AdmissionForms.FindAsync(formId);
        if (form == null) return;

        try
        {
            form.Status = FormStatus.Extracting;
            await _context.SaveChangesAsync();

            // Perform OCR
            var ocrResult = await _ocrService.ExtractAsync(filePath);

            // Extract fields
            var extraction = _formExtractor.Extract(ocrResult.RawText);

            // Map extracted fields to form entity
            MapExtractionToForm(form, extraction);

            // Store raw extraction data as JSON
            form.ExtractedDataJson = JsonSerializer.Serialize(extraction.Fields);
            form.OcrProvider = "tesseract+srcc_extractor";
            form.Status = FormStatus.Extracted;

            await _context.SaveChangesAsync();
            _logger.LogInformation("Successfully extracted form {FormId}", formId);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error processing form {FormId}", formId);
            form.Status = FormStatus.Error;
            await _context.SaveChangesAsync();
        }
    }

    private void MapExtractionToForm(AdmissionForm form, ExtractionResult extraction)
    {
        var fields = extraction.Fields;

        // Map each field using helper method
        form.StudentName = GetField(fields, "StudentName");
        form.FirstName = GetField(fields, "FirstName");
        form.MiddleName = GetField(fields, "MiddleName");
        form.Surname = GetField(fields, "Surname");
        form.Gender = GetField(fields, "Gender");
        form.DateOfBirth = GetField(fields, "DateOfBirth");
        form.Category = GetField(fields, "Category");
        form.Nationality = GetField(fields, "Nationality");
        form.Religion = GetField(fields, "Religion");
        form.BloodGroup = GetField(fields, "BloodGroup");
        form.AadharNumber = GetField(fields, "AadharNumber");
        form.BelowPovertyLine = GetField(fields, "BelowPovertyLine");
        form.AnnualIncome = GetField(fields, "AnnualIncome");
        form.MinorityCategory = GetField(fields, "MinorityCategory");

        // Academic details
        form.AcademicSession = GetField(fields, "AcademicSession");
        form.Course = GetField(fields, "Course");
        form.AdmissionCategory = GetField(fields, "AdmissionCategory");
        form.DuPortalFormNumber = GetField(fields, "DuPortalFormNumber");
        form.CuetScore = GetField(fields, "CuetScore");
        form.CollegeRollNo = GetField(fields, "CollegeRollNo");
        form.DateOfAdmission = GetField(fields, "DateOfAdmission");

        // Address
        form.PermanentAddress = GetField(fields, "PermanentAddress");
        form.PermanentState = GetField(fields, "PermanentState");
        form.PermanentPincode = GetField(fields, "PermanentPincode");
        form.Pincode = GetField(fields, "Pincode");
        form.CorrespondenceAddress = GetField(fields, "CorrespondenceAddress");
        form.CorrespondenceState = GetField(fields, "CorrespondenceState");
        form.CorrespondencePincode = GetField(fields, "CorrespondencePincode");

        // Contact
        form.Email = GetField(fields, "Email");
        form.PhoneNumber = GetField(fields, "PhoneNumber");
        form.AlternatePhone = GetField(fields, "AlternatePhone");

        // Parents
        form.MotherName = GetField(fields, "MotherName");
        form.FatherName = GetField(fields, "FatherName");
        form.MotherOccupation = GetField(fields, "MotherOccupation");
        form.FatherOccupation = GetField(fields, "FatherOccupation");
        form.MotherMobile = GetField(fields, "MotherMobile");
        form.FatherMobile = GetField(fields, "FatherMobile");
        form.MotherEmail = GetField(fields, "MotherEmail");
        form.FatherEmail = GetField(fields, "FatherEmail");

        // Guardian
        form.GuardianName = GetField(fields, "GuardianName");
        form.GuardianMobile = GetField(fields, "GuardianMobile");

        // Class XII
        form.TwelfthYear = GetField(fields, "TwelfthYear");
        form.TwelfthBoard = GetField(fields, "TwelfthBoard");
        form.TwelfthRollNumber = GetField(fields, "TwelfthRollNumber");
        form.TwelfthInstitution = GetField(fields, "TwelfthInstitution");
        form.TwelfthPercentage = GetField(fields, "TwelfthPercentage");
        form.HindiStudiedUpto = GetField(fields, "HindiStudiedUpto");

        // Other
        form.DuEnrollmentNumber = GetField(fields, "DuEnrollmentNumber");
        form.HindiMediumPreference = GetField(fields, "HindiMediumPreference");

        // Documents
        form.DocAdmissionForm = GetField(fields, "DocAdmissionForm")?.ToLower() == "true";
        form.DocUndertakingRagging = GetField(fields, "DocUndertakingRagging")?.ToLower() == "true";
        form.DocPhotographs = GetField(fields, "DocPhotographs")?.ToLower() == "true";
        form.DocCuetScorecard = GetField(fields, "DocCuetScorecard")?.ToLower() == "true";
        form.DocClassXiiMarksheet = GetField(fields, "DocClassXiiMarksheet")?.ToLower() == "true";
    }

    private static string? GetField(Dictionary<string, string?> fields, string key)
    {
        return fields.TryGetValue(key, out var value) ? value : null;
    }

    #endregion
}
