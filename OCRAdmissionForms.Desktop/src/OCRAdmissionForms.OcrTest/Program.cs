using System;
using System.IO;
using System.Threading.Tasks;
using OCRAdmissionForms.Core.Entities;
using OCRAdmissionForms.Core.Services;

namespace OCRAdmissionForms.OcrTest;

/// <summary>
/// Simple test program to verify OCR extraction on sample SRCC forms
/// </summary>
class Program
{
    static async Task Main(string[] args)
    {
        Console.WriteLine("=================================================");
        Console.WriteLine("SRCC OCR Extraction Test");
        Console.WriteLine("=================================================\n");

        // Find sample PDF directory
        var sampleDir = FindSampleDirectory();
        if (sampleDir == null)
        {
            Console.WriteLine("ERROR: Could not find sample PDFs directory");
            Console.WriteLine("Expected at: data/samples/pdfs/ or Student Forms/");
            return;
        }

        Console.WriteLine($"Found sample directory: {sampleDir}\n");

        // Get first few PDFs for testing
        var pdfFiles = Directory.GetFiles(sampleDir, "*.pdf").Take(3).ToArray();
        if (pdfFiles.Length == 0)
        {
            Console.WriteLine("No PDF files found in sample directory");
            return;
        }

        Console.WriteLine($"Testing with {pdfFiles.Length} PDF files...\n");

        // Test FormFieldExtractor
        var extractor = new FormFieldExtractor();

        foreach (var pdfPath in pdfFiles)
        {
            var fileName = Path.GetFileName(pdfPath);
            Console.WriteLine($"--- Testing: {fileName} ---");

            try
            {
                // Read the extracted text (simulated - in real use, OCR would extract this)
                // For now, test with sample OCR text
                var sampleOcrText = GenerateSampleOcrText(fileName);
                
                var form = new AdmissionForm();
                form = extractor.ExtractFields(sampleOcrText, form);

                Console.WriteLine($"  Student Name: {form.StudentName ?? "N/A"}");
                Console.WriteLine($"  Roll Number:  {form.CollegeRollNo ?? "N/A"}");
                Console.WriteLine($"  Course:       {form.Course ?? "N/A"}");
                Console.WriteLine($"  Phone:        {form.PhoneNumber ?? "N/A"}");
                Console.WriteLine($"  Email:        {form.Email ?? "N/A"}");
                Console.WriteLine($"  Aadhar:       {form.AadharNumber ?? "N/A"}");
                Console.WriteLine($"  Father:       {form.FatherName ?? "N/A"}");
                Console.WriteLine($"  12th Board:   {form.TwelfthBoard ?? "N/A"}");
                Console.WriteLine($"  12th %:       {form.TwelfthPercentage ?? "N/A"}");
                Console.WriteLine();
            }
            catch (Exception ex)
            {
                Console.WriteLine($"  ERROR: {ex.Message}\n");
            }
        }

        // Test OcrErrorCorrector
        Console.WriteLine("\n=== Testing OcrErrorCorrector ===\n");
        TestErrorCorrector();

        Console.WriteLine("\n=================================================");
        Console.WriteLine("OCR Test Complete");
        Console.WriteLine("=================================================");
    }

    static string? FindSampleDirectory()
    {
        var possiblePaths = new[]
        {
            @"c:\Users\as\Documents\GitHub\OCR-admission-forms\data\samples\pdfs",
            @"c:\Users\as\Documents\GitHub\OCR-admission-forms\Student Forms",
            @".\data\samples\pdfs",
            @".\Student Forms"
        };

        foreach (var path in possiblePaths)
        {
            if (Directory.Exists(path))
                return path;
        }
        return null;
    }

    static string GenerateSampleOcrText(string fileName)
    {
        // Generate realistic sample OCR text based on filename pattern
        // In production, this would come from Google Vision or Tesseract
        
        var name = Path.GetFileNameWithoutExtension(fileName)
            .Split('-').LastOrDefault()?.Trim() ?? "SAMPLE STUDENT";
        
        return $@"
SHRI RAM COLLEGE OF COMMERCE
University of Delhi
ADMISSION FORM 2024-25

Academic Session: 2024-25
Course: B.Com (Honours)
College Roll No: UN-01-2435500377

Student Name: {name}
Gender: Male
Date of Birth: 15/08/2005
Category: General
Blood Group: B+
Aadhar Number: 1234 5678 9012

Father's Name: RAMESH KUMAR
Father's Occupation: Business
Father's Mobile: 9876543210

Mother's Name: SUNITA DEVI
Mother's Occupation: Homemaker
Mother's Mobile: 9876543211

Phone Number: 9123456789
Email: {name.ToLower().Replace(" ", ".")}@gmail.com
Permanent Address: 123 Main Street, Delhi
State: Delhi
Pincode: 110001

Class 12th Board: CBSE
Year of Passing: 2024
Percentage: 95.4%
Institution: Delhi Public School

CUET Score: 750
DU Portal Form No: 2435500377
";
    }

    static void TestErrorCorrector()
    {
        Console.WriteLine("Testing phone correction:");
        var phone1 = "9l234567O9"; // OCR mistakes: l for 1, O for 0
        Console.WriteLine($"  Input:  '{phone1}'");
        Console.WriteLine($"  Output: '{OcrErrorCorrector.CorrectPhoneNumber(phone1)}'");
        
        Console.WriteLine("\nTesting email correction:");
        var email1 = "student@gmail.corn";
        Console.WriteLine($"  Input:  '{email1}'");
        Console.WriteLine($"  Output: '{OcrErrorCorrector.CorrectEmail(email1)}'");
        
        Console.WriteLine("\nTesting date correction:");
        var date1 = "15/O8/2OO5";
        Console.WriteLine($"  Input:  '{date1}'");
        Console.WriteLine($"  Output: '{OcrErrorCorrector.CorrectDate(date1)}'");
        
        Console.WriteLine("\nTesting name correction:");
        var name1 = "RAHUL kUMAR";
        Console.WriteLine($"  Input:  '{name1}'");
        Console.WriteLine($"  Output: '{OcrErrorCorrector.CorrectName(name1)}'");
        
        Console.WriteLine("\nTesting Aadhar correction:");
        var aadhar1 = "l234 5678 9Ol2";
        Console.WriteLine($"  Input:  '{aadhar1}'");
        Console.WriteLine($"  Output: '{OcrErrorCorrector.CorrectAadhar(aadhar1)}'");
        
        Console.WriteLine("\nTesting label rejection:");
        var labels = new[] { "Father's Name:", "Email Address", "RAHUL KUMAR" };
        foreach (var label in labels)
        {
            Console.WriteLine($"  '{label}' is label: {OcrErrorCorrector.IsFormLabel(label)}");
        }
    }
}
