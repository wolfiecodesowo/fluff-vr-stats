; Fluff VR Stats :3 - Windows installer (Inno Setup 6)
; Built by installer/build_installer.ps1 (or the GitHub Actions release workflow).
; Installs per-user (no admin), with its own private Python, so nobody has to "install Python" first.
; The app keeps auto-updating itself in place after install (signed updates, see updater.py).

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{6F1D2A8E-3C5B-4F00-B3A7-7A1E5F1D2C9B}
AppName=Fluff VR Stats
AppVersion={#AppVersion}
AppVerName=Fluff VR Stats {#AppVersion}
AppPublisher=wolfiecodesowo
AppPublisherURL=https://wolfiecodesowo.github.io/fluff-vr-stats/
AppSupportURL=https://wolfiecodesowo.github.io/fluff-vr-stats/faq.html
DefaultDirName={localappdata}\Programs\FluffVRStats
DefaultGroupName=Fluff VR Stats
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=FluffVRStats-Setup-{#AppVersion}
SetupIconFile=fluff.ico
UninstallDisplayIcon={app}\installer\fluff.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible
CloseApplications=yes

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "ja"; MessagesFile: "compiler:Languages\Japanese.isl"
Name: "ko"; MessagesFile: "compiler:Languages\Korean.isl"
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "pt"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "fr"; MessagesFile: "compiler:Languages\French.isl"
Name: "de"; MessagesFile: "compiler:Languages\German.isl"
Name: "it"; MessagesFile: "compiler:Languages\Italian.isl"
Name: "pl"; MessagesFile: "compiler:Languages\Polish.isl"
Name: "ru"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "uk"; MessagesFile: "compiler:Languages\Ukrainian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "steamvr"; Description: "Start Fluff VR Stats with SteamVR"; GroupDescription: "SteamVR:"; Flags: unchecked

[Files]
; ..\build\app = the app files + python\ (made by build_installer.ps1)
Source: "..\build\app\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; \
  Excludes: "config.json,bot\bot_config.json,bot\bot_key.pem,keys\*,logs\*"

[Icons]
Name: "{group}\Fluff VR Stats"; Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\main.py"""; \
  WorkingDir: "{app}"; IconFilename: "{app}\installer\fluff.ico"
Name: "{group}\Fluff VR Stats (desktop mode)"; Filename: "{app}\python\pythonw.exe"; \
  Parameters: """{app}\main.py"" --desktop"; WorkingDir: "{app}"; IconFilename: "{app}\installer\fluff.ico"
Name: "{group}\Help + FAQ"; Filename: "https://wolfiecodesowo.github.io/fluff-vr-stats/faq.html"
Name: "{group}\Uninstall Fluff VR Stats"; Filename: "{uninstallexe}"
Name: "{userdesktop}\Fluff VR Stats"; Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\main.py"""; \
  WorkingDir: "{app}"; IconFilename: "{app}\installer\fluff.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\python\python.exe"; Parameters: """{app}\autostart_with_steamvr.py"" --quiet"; \
  WorkingDir: "{app}"; Flags: runhidden skipifdoesntexist; Tasks: steamvr
Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\main.py"""; WorkingDir: "{app}"; \
  Description: "Open Fluff VR Stats now :3"; Flags: postinstall nowait skipifsilent

[UninstallRun]
Filename: "{app}\python\python.exe"; Parameters: """{app}\autostart_with_steamvr.py"" --remove --quiet"; \
  WorkingDir: "{app}"; Flags: runhidden skipifdoesntexist; RunOnceId: "RemoveSteamVR"

[UninstallDelete]
; app-made stuff. ur settings (config.json), Wrapped cards + exports are kept unless u delete the folder yourself
Type: filesandordirs; Name: "{app}\__pycache__"
Type: filesandordirs; Name: "{app}\.update_backup"
Type: filesandordirs; Name: "{app}\logs"
Type: files; Name: "{app}\icon.png"
Type: files; Name: "{app}\fluffvr_stats.vrmanifest"
