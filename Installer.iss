#define MyAppName "Gestione Turni"
#define MyAppVersion "1.1.0"
#define MyAppPublisher "Mattia Franco"
#define MyAppExeName "GestioneTurni.exe"
#define MyAppIconName "gestione_turni.ico"

[Setup]
AppId={{A1E46B51-9E1E-4F72-8F88-3C9F6A1B2D91}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
VersionInfoVersion=1.1.0.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=Installer di Gestione Turni
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

DefaultDirName={autopf}\Gestione Turni
DefaultGroupName=Gestione Turni

OutputDir=Installer
OutputBaseFilename=Setup_GestioneTurni_v1.1.0

Compression=lzma2
SolidCompression=yes
WizardStyle=modern

PrivilegesRequired=lowest

DisableDirPage=no
DisableProgramGroupPage=yes

ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64os

SetupIconFile=assets\{#MyAppIconName}
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"

[Tasks]
Name: "desktopicon"; \
    Description: "Crea collegamento sul Desktop"; \
    GroupDescription: "Collegamenti:"

[Files]
Source: "dist\GestioneTurni\*"; \
    DestDir: "{app}"; \
    Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\Gestione Turni"; \
    Filename: "{app}\{#MyAppExeName}"; \
    WorkingDir: "{app}"; \
    IconFilename: "{app}\{#MyAppExeName}"

Name: "{autodesktop}\Gestione Turni"; \
    Filename: "{app}\{#MyAppExeName}"; \
    WorkingDir: "{app}"; \
    IconFilename: "{app}\{#MyAppExeName}"; \
    Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; \
    Description: "Avvia Gestione Turni"; \
    WorkingDir: "{app}"; \
    Flags: nowait postinstall skipifsilent
