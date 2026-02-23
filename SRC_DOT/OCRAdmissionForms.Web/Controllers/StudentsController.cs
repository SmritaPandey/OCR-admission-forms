using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using OCRAdmissionForms.Core.Entities;
using OCRAdmissionForms.Infrastructure.Data;

namespace OCRAdmissionForms.Web.Controllers;

[ApiController]
[Route("api/[controller]")]
public class StudentsController : ControllerBase
{
    private readonly AppDbContext _context;
    private readonly ILogger<StudentsController> _logger;

    public StudentsController(AppDbContext context, ILogger<StudentsController> logger)
    {
        _context = context;
        _logger = logger;
    }

    /// <summary>
    /// Get all student profiles
    /// </summary>
    [HttpGet]
    public async Task<ActionResult<IEnumerable<StudentProfile>>> GetStudents(
        [FromQuery] int page = 1,
        [FromQuery] int pageSize = 20,
        [FromQuery] string? search = null)
    {
        var query = _context.StudentProfiles
            .Include(p => p.Forms)
            .AsQueryable();

        if (!string.IsNullOrEmpty(search))
        {
            query = query.Where(p =>
                p.StudentName.Contains(search) ||
                (p.RollNumber != null && p.RollNumber.Contains(search)) ||
                (p.AadharNumber != null && p.AadharNumber.Contains(search)));
        }

        var total = await query.CountAsync();
        var students = await query
            .OrderByDescending(p => p.CreatedDate)
            .Skip((page - 1) * pageSize)
            .Take(pageSize)
            .ToListAsync();

        Response.Headers.Append("X-Total-Count", total.ToString());
        return Ok(students);
    }

    /// <summary>
    /// Get a specific student profile
    /// </summary>
    [HttpGet("{id}")]
    public async Task<ActionResult<StudentProfile>> GetStudent(int id)
    {
        var student = await _context.StudentProfiles
            .Include(p => p.Forms)
            .Include(p => p.Documents)
            .FirstOrDefaultAsync(p => p.Id == id);

        if (student == null)
        {
            return NotFound();
        }

        return Ok(student);
    }

    /// <summary>
    /// Create a new student profile
    /// </summary>
    [HttpPost]
    public async Task<ActionResult<StudentProfile>> CreateStudent([FromBody] StudentProfile student)
    {
        student.CreatedDate = DateTime.UtcNow;
        student.UpdatedDate = DateTime.UtcNow;
        
        _context.StudentProfiles.Add(student);
        await _context.SaveChangesAsync();

        return CreatedAtAction(nameof(GetStudent), new { id = student.Id }, student);
    }

    /// <summary>
    /// Update a student profile
    /// </summary>
    [HttpPut("{id}")]
    public async Task<ActionResult> UpdateStudent(int id, [FromBody] StudentProfile update)
    {
        var student = await _context.StudentProfiles.FindAsync(id);
        if (student == null)
        {
            return NotFound();
        }

        student.StudentName = update.StudentName;
        student.AadharNumber = update.AadharNumber;
        student.RollNumber = update.RollNumber;
        student.UpdatedDate = DateTime.UtcNow;

        await _context.SaveChangesAsync();
        return Ok(student);
    }

    /// <summary>
    /// Delete a student profile
    /// </summary>
    [HttpDelete("{id}")]
    public async Task<ActionResult> DeleteStudent(int id)
    {
        var student = await _context.StudentProfiles.FindAsync(id);
        if (student == null)
        {
            return NotFound();
        }

        _context.StudentProfiles.Remove(student);
        await _context.SaveChangesAsync();

        return NoContent();
    }

    /// <summary>
    /// Get student statistics
    /// </summary>
    [HttpGet("stats")]
    public async Task<ActionResult> GetStats()
    {
        var stats = new
        {
            Total = await _context.StudentProfiles.CountAsync(),
            Verified = await _context.StudentProfiles.CountAsync(), // For now, count all as verified if they exist
            WithForms = await _context.StudentProfiles.CountAsync(p => p.Forms.Any()),
            WithDocuments = await _context.StudentProfiles.CountAsync(p => p.Documents.Any())
        };
        return Ok(stats);
    }

    /// <summary>
    /// Get all forms for a specific student
    /// </summary>
    [HttpGet("{id}/forms")]
    public async Task<ActionResult<IEnumerable<AdmissionForm>>> GetStudentForms(int id)
    {
        var student = await _context.StudentProfiles.FindAsync(id);
        if (student == null)
        {
            return NotFound();
        }

        var forms = await _context.AdmissionForms
            .Where(f => f.StudentProfileId == id)
            .OrderByDescending(f => f.UploadDate)
            .ToListAsync();

        return Ok(forms);
    }

    /// <summary>
    /// Get all documents for a specific student
    /// </summary>
    [HttpGet("{id}/documents")]
    public async Task<ActionResult<IEnumerable<StudentDocument>>> GetStudentDocuments(int id)
    {
        var student = await _context.StudentProfiles.FindAsync(id);
        if (student == null)
        {
            return NotFound();
        }

        var documents = await _context.StudentDocuments
            .Where(d => d.StudentProfileId == id)
            .OrderByDescending(d => d.UploadDate)
            .ToListAsync();

        return Ok(documents);
    }
}
