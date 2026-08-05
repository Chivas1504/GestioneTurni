#define MyAppName "Gestione Turni"
#define MyAppVersion "1.0.1"
#define MyAppPublisher "Mattia Franco"
#define MyAppExeName "GestioneTurni.exe"

[Setup]
AppId={{A1E46B51-9E1E-4F72-8F88-3C9F6A1B2D91}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Gestione Turni
DefaultGroupName=Gestione Turni
OutputDir=Installer
OutputBaseFilename=Setup_GestioneTurni_v1.0.1
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
DisableDirPage=no
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64os

[Languages]
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"

[Tasks]
Name: "desktopicon"; Description: "Crea collegamento sul Desktop"; GroupDescription: "Collegamenti:"

[Files]
Source: "dist\GestioneTurni\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\Gestione Turni"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Gestione Turni"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Avvia Gestione Turni"; Flags: nowait postinstall skipifsilent
