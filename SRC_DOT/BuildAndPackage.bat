@echo off
echo ==============================================
echo      OCR Admission Forms - Build Script
echo ==============================================

echo [1/3] Restoring Dependencies...
dotnet restore

echo [2/3] Building Solution...
dotnet build --no-restore

echo [3/3] Packaging Application (Single File Exe)...
mkdir Dist 2>nul
cd OCRAdmissionForms.Web
dotnet publish -c Release -r win-x64 --self-contained -p:PublishSingleFile=true -o ../Dist
cd ..

echo.
echo ==============================================
echo Build Complete!
echo The application is located in the 'Dist' folder.
echo.
echo IMPORTANT: 
echo 1. You must verify 'tessdata' folder exists in 'Dist/tessdata' for OCR.
echo 2. Run 'OCRAdmissionForms.Web.exe' to start the application.
echo ==============================================
pause
