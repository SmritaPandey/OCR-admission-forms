[Setup]
AppName=SRCC Student DMS
AppVersion=4.1.0
DefaultDirName={autopf}\SRCC Student DMS
DefaultGroupName=SRCC Student DMS
UninstallDisplayIcon={app}\OCRAdmissionForms.App.exe
Compression=lzma2
SolidCompression=yes
OutputDir=c:\Users\as\Documents\GitHub\OCR-admission-forms\OCRAdmissionForms.Desktop\Output
OutputBaseFilename=SRCC_Student_DMS_v4.1.0_Setup
SetupIconFile=c:\Users\as\Documents\GitHub\OCR-admission-forms\scan_code_scanner_icon_228210.ico
PrivilegesRequired=admin

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "c:\Users\as\Documents\GitHub\OCR-admission-forms\OCRAdmissionForms.Desktop\publish_v4_installer_src\app\app\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\SRCC Student DMS"; Filename: "{app}\OCRAdmissionForms.App.exe"
Name: "{autodesktop}\SRCC Student DMS"; Filename: "{app}\OCRAdmissionForms.App.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\OCRAdmissionForms.App.exe"; Description: "{cm:LaunchProgram,SRCC Student DMS}"; Flags: nowait postinstall skipifsilent
