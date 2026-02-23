using Microsoft.EntityFrameworkCore;
using OCRAdmissionForms.Web.Components;
using OCRAdmissionForms.Infrastructure.Data;
using OCRAdmissionForms.Core.Interfaces;
using OCRAdmissionForms.Infrastructure.Services;

var builder = WebApplication.CreateBuilder(args);

// Railway provides PORT env var — only override when explicitly set
var port = Environment.GetEnvironmentVariable("PORT");
if (!string.IsNullOrEmpty(port))
{
    builder.WebHost.UseUrls($"http://0.0.0.0:{port}");
}

// Add services to the container.
builder.Services.AddRazorComponents()
    .AddInteractiveServerComponents();

// Add API Controllers
builder.Services.AddControllers()
    .AddJsonOptions(options =>
    {
        options.JsonSerializerOptions.PropertyNamingPolicy = null; // Use PascalCase
    });

// Add Swagger for API documentation (development only)
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(c =>
{
    c.SwaggerDoc("v1", new() { Title = "OCR Admission Forms API", Version = "v1" });
});

// Database Context — supports Railway DATABASE_URL, PostgreSQL, SQLite, SqlServer
var dbProvider = builder.Configuration.GetValue<string>("DatabaseProvider");
var connectionString = builder.Configuration.GetConnectionString("DefaultConnection");

// Railway injects DATABASE_URL for PostgreSQL
var databaseUrl = Environment.GetEnvironmentVariable("DATABASE_URL");
if (!string.IsNullOrEmpty(databaseUrl))
{
    connectionString = ConvertDatabaseUrl(databaseUrl);
    dbProvider = "PostgreSQL";
}

builder.Services.AddDbContext<AppDbContext>(options =>
{
    if (dbProvider == "PostgreSQL")
    {
        options.UseNpgsql(connectionString);
    }
    else if (dbProvider == "SQLite")
    {
        var appData = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
        var defaultDbPath = Path.Combine(appData, "SRCC Student DMS", "data", "srcc_dms.db");
        var sqliteConnectionString = connectionString ?? $"Data Source={defaultDbPath}";
        options.UseSqlite(sqliteConnectionString);
    }
    else
    {
        options.UseSqlServer(connectionString ?? "Server=(localdb)\\mssqllocaldb;Database=OCRAdmissionForms;Trusted_Connection=True;MultipleActiveResultSets=true");
    }
});

// OCR Services - Uses Google Vision (primary) with Tesseract fallback
var tessDataPath = builder.Configuration.GetValue<string>("TessDataPath") ?? "./tessdata";
var googleCredentialsPath = builder.Configuration.GetValue<string>("GoogleCloudCredentials");
var useEnsemble = builder.Configuration.GetValue<bool>("UseEnsembleOcr");

builder.Services.AddScoped<IOcrService>(sp => 
    new UnifiedOcrService(googleCredentialsPath, tessDataPath, useEnsemble));

// Form Extraction Service
builder.Services.AddScoped<IFormExtractorService, SrccFormExtractor>();

// Excel/Crypto Services
builder.Services.AddScoped<IExcelService, OpenXmlExcelService>();
builder.Services.AddScoped<ICryptoService, AesCryptoService>();

// CORS for API access
builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowAll", policy =>
    {
        policy.AllowAnyOrigin()
              .AllowAnyMethod()
              .AllowAnyHeader();
    });
});

var app = builder.Build();

// Configure the HTTP request pipeline.
if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error", createScopeForErrors: true);
    // Railway handles TLS at the edge — no HTTPS redirect needed in production
}
else
{
    // Enable Swagger in development
    app.UseSwagger();
    app.UseSwaggerUI(c => c.SwaggerEndpoint("/swagger/v1/swagger.json", "OCR Admission Forms API v1"));
}

app.UseStaticFiles();
app.UseRouting();
app.UseAntiforgery();
app.UseCors("AllowAll");

// Map API Controllers
app.MapControllers();

// Map Blazor Components
app.MapRazorComponents<App>()
    .AddInteractiveServerRenderMode();

// Ensure uploads directory exists
var uploadsPath = Path.Combine(app.Environment.ContentRootPath, "uploads");
Directory.CreateDirectory(uploadsPath);

// Ensure database is created and migrated
using (var scope = app.Services.CreateScope())
{
    var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
    db.Database.EnsureCreated();
}

app.Run();

// Helper: Convert Railway DATABASE_URL to Npgsql connection string
// Railway format: postgresql://user:password@host:port/dbname
static string ConvertDatabaseUrl(string url)
{
    var uri = new Uri(url);
    var userInfo = uri.UserInfo.Split(':');
    var host = uri.Host;
    var port = uri.Port > 0 ? uri.Port : 5432;
    var database = uri.AbsolutePath.TrimStart('/');
    var user = userInfo.Length > 0 ? userInfo[0] : "";
    var password = userInfo.Length > 1 ? userInfo[1] : "";
    return $"Host={host};Port={port};Database={database};Username={user};Password={password};SSL Mode=Require;Trust Server Certificate=true";
}

