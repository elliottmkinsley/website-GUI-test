; Inno Setup script for the Radiant Content GUI installer.
;
; Build via packaging\build_installer.ps1 (resolves AppVersion and
; iscc.exe automatically). Manual invocation:
;
;     iscc.exe /DAppVersion=1.0.0 /DSingleFile=1 packaging\installer.iss
;
; Critical conventions:
;
; * AppId is a one-shot GUID and MUST NEVER change after v1.0 ships.
;   Inno keys upgrades off this id; if it changes, end users get a
;   second parallel install instead of an upgrade in place. See
;   playbook gotcha #2 and §4.3.
;
; * DiskSpanning is gated behind /DSingleFile so the same .iss file
;   can produce an online single-exe installer (~50 MB) AND an
;   offline multi-disk installer in the future without forking.
;   Always pass /DSingleFile=1 for the online build that release.yml
;   ships, otherwise Inno emits a stub.exe + -1.bin pair and our
;   release workflow only attaches the stub (playbook gotcha #7).
;
; * The post-install [Run] step launches the .exe with --selftest so
;   any frozen-binary hidden-import surprise fails loudly during
;   install rather than the first time the user clicks the icon
;   (playbook gotcha #8).

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

#define AppName "Radiant Content GUI"
#define AppPublisher "Radiant Center for Remote Sensing"
#define AppURL "https://github.com/elliottmkinsley/website-GUI-test"
#define AppExe "RadiantContentGUI.exe"

[Setup]
; AppId: STABLE GUID, do NOT regenerate.
AppId={{5185C8E4-5748-4307-8F2B-FF48A51B392D}
AppName={#AppName}
AppVersion={#AppVersion}
VersionInfoVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases
DefaultDirName={autopf}\RadiantContentGUI
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputBaseFilename=RadiantContentGUISetup
OutputDir=..\dist
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
WizardStyle=modern
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0

; --- DiskSpanning is online-vs-offline gated. -----------------------------
; For online (single-exe) builds CI passes /DSingleFile=1. For future
; offline builds, omit the define and the spanning directives below
; activate.
#ifndef SingleFile
  DiskSpanning=yes
  SlicesPerDisk=1
  DiskSliceSize=2100000000
#endif

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
; Bundle every file from the frozen PyInstaller onedir output.
; build_installer.ps1 invokes pyinstaller before iscc so this folder
; always exists at compile time.
Source: "..\dist\RadiantContentGUI\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"; IconFilename: "{app}\icon.ico"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; IconFilename: "{app}\icon.ico"; Tasks: desktopicon

[Run]
; Post-install verification: run --selftest so any frozen-binary
; import failure surfaces here, not after the user opens the app for
; real. ``nowait`` lets the wizard close immediately; ``skipifsilent``
; means scripted reinstalls do not pop a console.
Filename: "{app}\{#AppExe}"; Parameters: "--selftest"; Description: "Verify installation"; Flags: nowait postinstall skipifsilent runhidden

[UninstallDelete]
; Leave the user's app-data workspace (their cloned website checkout
; and any unsaved edits) in place on uninstall - the user can
; manually delete it from %APPDATA% if they wish. We only sweep the
; install dir itself.
Type: filesandordirs; Name: "{app}"

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
  // Future home for prerequisite checks (free disk, .NET, etc.).
  // Kept as a no-op for v1 so install never fails on a check we
  // forgot to update.
end;
