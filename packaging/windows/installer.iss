; Inno Setup script for PartyBooth.
; Build with: iscc packaging\windows\installer.iss
; Expects the PyInstaller onedir output at dist\launcher\ (repo root),
; i.e. run this after `pyinstaller packaging\launcher.spec` from the repo root.
;
#define MyAppName "PartyBooth"
#define MyAppVersion "0.1.0"
#define MyAppExeName "launcher.exe"

[Setup]
AppId={{B7B6C8B2-6E7E-4F7B-9C1D-8A6E4A5D9C1A}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\..\dist-installers
OutputBaseFilename=PartyBooth-Setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
SetupIconFile=app-icon.ico

[Files]
Source: "..\..\dist\launcher\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch PartyBooth now"; Flags: nowait postinstall skipifsilent
