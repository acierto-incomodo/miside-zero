[Setup]
AppName=MiSide Zero by StormGamesStudios
AppVersion=1.0.4
DefaultDirName={userappdata}\StormGamesStudios\NewGameDir\MiSideZero
DefaultGroupName=StormGamesStudios
OutputDir=C:\Users\melio\Documents\GitHub\miside-zero\output
OutputBaseFilename=MiSideZero_Launcher_Installer
Compression=lzma
SolidCompression=yes
AppCopyright=Copyright © 2025 StormGamesStudios. All rights reserved.
VersionInfoCompany=StormGamesStudios
AppPublisher=StormGamesStudios
SetupIconFile=miside-zero.ico
VersionInfoVersion=1.0.3.0
DisableDirPage=yes
DisableProgramGroupPage=yes
CloseApplications=yes
RestartApplications=no

[Files]
; Archivos del lanzador
Source: "C:\Users\melio\Documents\GitHub\miside-zero\dist\installer_updater.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\melio\Documents\GitHub\miside-zero\miside-zero.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\melio\Documents\GitHub\miside-zero\miside-zero.png"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\melio\Documents\GitHub\miside-zero\Logo"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Acceso directo en el escritorio
; Name: "{userdesktop}\MiSide Zero"; Filename: "{app}\installer_updater.exe"; IconFilename: "{app}\miside-zero.ico"; Comment: "Lanzador de MiSide Zero"; WorkingDir: "{app}"

; Acceso directo en el menú de inicio dentro de la carpeta StormGamesStudios
Name: "{commonprograms}\StormGamesStudios\MiSide Zero"; Filename: "{app}\installer_updater.exe"; IconFilename: "{app}\miside-zero.ico"; Comment: "Lanzador de MiSide Zero"; WorkingDir: "{app}"
Name: "{commonprograms}\StormGamesStudios\Desinstalar MiSide Zero"; Filename: "{uninstallexe}"; IconFilename: "{app}\miside-zero.ico"; Comment: "Desinstalar MiSide Zero"

[Registry]
; Guardar ruta de instalación para poder desinstalar
Root: HKCU; Subkey: "Software\MiSide Zero"; ValueType: string; ValueName: "Install_Dir"; ValueData: "{app}"

[UninstallDelete]
; Eliminar carpeta del appdata y acceso directo
Type: filesandordirs; Name: "{app}"

[Run]
; Ejecutar el lanzador después de la instalación
Filename: "{app}\installer_updater.exe"; Description: "Ejecutar MiSide Zero"; Flags: nowait postinstall skipifsilent
