#define MyAppName "Gestione Turni"
#define MyAppVersion "1.5.0"
#define MyAppPublisher "Mattia Franco"
#define MyAppExeName "GestioneTurni.exe"
#define MyAppIconName "gestione_turni.ico"

[Setup]
AppId={{A1E46B51-9E1E-4F72-8F88-3C9F6A1B2D91}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}

VersionInfoVersion=1.5.0.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=Installer di Gestione Turni
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

DefaultDirName={autopf}\Gestione Turni
DefaultGroupName=Gestione Turni

OutputDir=Installer
OutputBaseFilename=Setup_GestioneTurni_v1.5.0

Compression=lzma2
SolidCompression=yes
WizardStyle=modern

; Necessario per installare in Program Files e configurare il firewall.
PrivilegesRequired=admin

DisableDirPage=no
DisableProgramGroupPage=yes

ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64os

SetupIconFile=assets\{#MyAppIconName}
UninstallDisplayIcon={app}\{#MyAppExeName}

CloseApplications=yes
RestartApplications=no
UsePreviousAppDir=yes

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
; Consente all'applicazione di comunicare sulla rete privata.
Filename: "{sys}\netsh.exe"; \
    Parameters: "advfirewall firewall delete rule name=""Gestione Turni - Applicazione"""; \
    Flags: runhidden waituntilterminated

Filename: "{sys}\netsh.exe"; \
    Parameters: "advfirewall firewall add rule name=""Gestione Turni - Applicazione"" dir=in action=allow program=""{app}\{#MyAppExeName}"" enable=yes profile=private"; \
    Flags: runhidden waituntilterminated

; Regole esplicite per elezione, sincronizzazione e display TV.
Filename: "{sys}\netsh.exe"; \
    Parameters: "advfirewall firewall delete rule name=""Gestione Turni - UDP 50555"""; \
    Flags: runhidden waituntilterminated

Filename: "{sys}\netsh.exe"; \
    Parameters: "advfirewall firewall add rule name=""Gestione Turni - UDP 50555"" dir=in action=allow protocol=UDP localport=50555 enable=yes profile=private"; \
    Flags: runhidden waituntilterminated

Filename: "{sys}\netsh.exe"; \
    Parameters: "advfirewall firewall delete rule name=""Gestione Turni - TCP 50556"""; \
    Flags: runhidden waituntilterminated

Filename: "{sys}\netsh.exe"; \
    Parameters: "advfirewall firewall add rule name=""Gestione Turni - TCP 50556"" dir=in action=allow protocol=TCP localport=50556 enable=yes profile=private"; \
    Flags: runhidden waituntilterminated

Filename: "{sys}\netsh.exe"; \
    Parameters: "advfirewall firewall delete rule name=""Gestione Turni - Display TV 8080"""; \
    Flags: runhidden waituntilterminated

Filename: "{sys}\netsh.exe"; \
    Parameters: "advfirewall firewall add rule name=""Gestione Turni - Display TV 8080"" dir=in action=allow protocol=TCP localport=8080 enable=yes profile=private"; \
    Flags: runhidden waituntilterminated

Filename: "{app}\{#MyAppExeName}"; \
    Description: "Avvia Gestione Turni"; \
    WorkingDir: "{app}"; \
    Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{sys}\netsh.exe"; \
    Parameters: "advfirewall firewall delete rule name=""Gestione Turni - Applicazione"""; \
    Flags: runhidden waituntilterminated

Filename: "{sys}\netsh.exe"; \
    Parameters: "advfirewall firewall delete rule name=""Gestione Turni - UDP 50555"""; \
    Flags: runhidden waituntilterminated

Filename: "{sys}\netsh.exe"; \
    Parameters: "advfirewall firewall delete rule name=""Gestione Turni - TCP 50556"""; \
    Flags: runhidden waituntilterminated

Filename: "{sys}\netsh.exe"; \
    Parameters: "advfirewall firewall delete rule name=""Gestione Turni - Display TV 8080"""; \
    Flags: runhidden waituntilterminated