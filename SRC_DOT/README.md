# OCR Admission Forms (.NET 8 Replica)

This project is a complete re-implementation of the OCR Admission Forms system using the .NET 8 technology stack.

## Tech Stack
- **Framework**: ASP.NET Core 8 (Blazor Web App)
- **Database**: SQL Server (LocalDB) or PostgreSQL (Configurable in `appsettings.json`)
- **OCR**: Tesseract (via `Tesseract` NuGet)
- **Encryption**: AES-256 (via `AesCryptoService`)
- **Export**: Excel (via `OpenXml` SDK)

## Project Structure
- **SRC_DOT/**: Root directory
  - **OCRAdmissionForms.Core**: Domain Entities, Enums, Interfaces.
  - **OCRAdmissionForms.Infrastructure**: Data Access (EF Core), Services (OCR, Excel, Encryption).
  - **OCRAdmissionForms.Web**: UI (Blazor), API implementation.

## How to Run

### Development
1. Open `OCRAdmissionForms.sln` in Visual Studio or VS Code.
2. Run `OCRAdmissionForms.Web` project.
3. The database will be automatically created on startup using LocalDB.

### Packaging (Windows Installer)
1. Run `BuildAndPackage.bat` script.
2. This creates a `Dist` folder containing a standalone `OCRAdmissionForms.Web.exe`.
3. This Executable is a self-contained Windows application.

## Configuration
Update `OCRAdmissionForms.Web/appsettings.json`:
- `DatabaseProvider`: "SqlServer" or "PostgreSQL"
- `ConnectionStrings`: Update `DefaultConnection`.

## OCR Setup
Ensure the `tessdata` directory containing language files (e.g. `eng.traineddata`) is present in the application working directory (or `Dist/tessdata` after build).
