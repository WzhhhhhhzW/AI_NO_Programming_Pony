#define AppName "Renesas 机器马 AI 导师"
#define AppVersion "16.18"
#define AppExeName "RenesasHorseTutor.exe"
#ifndef AppSource
  #define AppSource "..\dist\RenesasHorseTutor"
#endif

[Setup]
AppId={{8C079D8A-6CE3-4B72-8C21-CB42B778F73E}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} V{#AppVersion}
DefaultDirName={localappdata}\Programs\RenesasHorseTutor
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=..\build\installer_output
OutputBaseFilename=RenesasHorseTutor_Setup_V{#AppVersion}
SetupIconFile=..\assets\app_icon.ico
UninstallDisplayIcon={app}\{#AppExeName}
Compression=lzma2/max
SolidCompression=yes
LZMANumBlockThreads=2
LZMADictionarySize=32
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no
SetupLogging=yes
VersionInfoVersion=16.18.0.0
VersionInfoDescription={#AppName} 安装程序
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#AppVersion}

[Languages]
Name: "chinesesimplified"; MessagesFile: "ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加快捷方式："; Flags: checkedonce

[Files]
Source: "{#AppSource}\*"; DestDir: "{app}"; Excludes: "安装包\*"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "安装说明.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "启动 {#AppName}"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; API 密钥、最近工程和工具设置位于 %APPDATA%\RenesasHorseAI，卸载时保留。
Type: filesandordirs; Name: "{app}"
