#define AppName "Renesas 机器马 AI 导师"
#define AppVersion "16.21"
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
; 升级时仍预填原安装位置，但始终允许用户重新选择。
DisableDirPage=no
UsePreviousAppDir=yes
DisableWelcomePage=no
AlwaysShowDirOnReadyPage=yes
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
WizardStyle=modern light
WizardSizePercent=100
WizardImageFile=assets\wizard_sidebar.png
WizardSmallImageFile=assets\wizard_header.png
WizardImageStretch=yes
WizardImageBackColor=#102E43
WizardSmallImageBackColor=white
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no
SetupLogging=yes
VersionInfoVersion=16.21.0.0
VersionInfoDescription={#AppName} 安装程序
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#AppVersion}

[Languages]
Name: "chinesesimplified"; MessagesFile: "ChineseSimplified.isl"

[LangOptions]
DialogFontName=Microsoft YaHei UI
DialogFontSize=9
WelcomeFontName=Microsoft YaHei UI
WelcomeFontSize=18

[Messages]
SelectDirDesc=选择安装位置
SelectDirLabel3=选择 AI 导师的安装文件夹。点击“浏览”可更改位置。
SelectTasksDesc=设置快捷方式
SelectTasksLabel2=选择你希望使用的快捷方式，然后继续下一步。
ReadyLabel1=安装位置和快捷方式已准备好。点击“安装”开始，或点击“上一步”修改。
FinishedHeadingLabel=安装完成，开始学习
FinishedLabelNoIcons=AI 导师已安装完成。打开软件，在“教程资料”中开始学习。

[Tasks]
Name: "desktopicon"; Description: "在桌面创建 AI 导师快捷方式"; GroupDescription: "快捷访问："; Flags: checkedonce

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

[Code]
var
  StepLabel: TNewStaticText;
  DirectoryInfoPanel, TaskInfoPanel: TPanel;

procedure AddInfoCard(var Card: TPanel; Page: TNewNotebookPage;
  Top: Integer; const Heading, Body: String);
var
  Title, Description: TNewStaticText;
begin
  Card := TPanel.Create(WizardForm);
  Card.Parent := Page;
  Card.Left := 0;
  Card.Top := Top;
  Card.Width := Page.ClientWidth;
  Card.Height := ScaleY(70);
  Card.BevelOuter := bvNone;
  Card.ParentBackground := False;
  Card.Color := $00F2F7F5;
  Card.Anchors := [akLeft, akTop, akRight];

  Title := TNewStaticText.Create(WizardForm);
  Title.Parent := Card;
  Title.SetBounds(ScaleX(14), ScaleY(10), Card.Width - ScaleX(28), ScaleY(20));
  Title.AutoSize := False;
  Title.Font.Style := [fsBold];
  Title.Font.Color := $00707F08;
  Title.Caption := Heading;
  Title.Anchors := [akLeft, akTop, akRight];

  Description := TNewStaticText.Create(WizardForm);
  Description.Parent := Card;
  Description.SetBounds(ScaleX(14), ScaleY(33), Card.Width - ScaleX(28), ScaleY(32));
  Description.AutoSize := False;
  Description.WordWrap := True;
  Description.Font.Color := $00867563;
  Description.Caption := Body;
  Description.Anchors := [akLeft, akTop, akRight];
end;

procedure InitializeWizard;
begin
  WizardForm.PageNameLabel.Font.Style := [fsBold];
  WizardForm.PageNameLabel.Font.Color := $00707F08;
  WizardForm.PageDescriptionLabel.Font.Color := $00867563;
  WizardForm.WelcomeLabel1.Caption := '欢迎使用' + #13#10 + '机器马 AI 导师';
  WizardForm.WelcomeLabel1.Font.Color := $00433217;
  WizardForm.WelcomeLabel1.Height := ScaleY(68);
  WizardForm.WelcomeLabel2.Top := WizardForm.WelcomeLabel1.Top +
    WizardForm.WelcomeLabel1.Height + ScaleY(12);
  WizardForm.WelcomeLabel2.Height := WizardForm.WelcomeLabel2.Parent.ClientHeight -
    WizardForm.WelcomeLabel2.Top - ScaleY(12);
  WizardForm.WelcomeLabel2.Caption :=
    '从想法到实物，陪你完成第一步。' + #13#10 + #13#10 +
    'AI 辅助开发、3D 动作仿真和学习教程，集中在一个软件中。' + #13#10 + #13#10 +
    '接下来，你可以选择安装位置并设置快捷方式。' + #13#10 + #13#10 +
    '点击“下一步”开始设置。';
  WizardForm.FinishedLabel.Font.Color := $00433217;

  AddInfoCard(DirectoryInfoPanel, WizardForm.SelectDirPage,
    WizardForm.DirEdit.Top + WizardForm.DirEdit.Height + ScaleY(18),
    '选择适合你的安装位置',
    '可以保留推荐位置，也可以选择其他磁盘。' + #13#10 +
    '更改安装位置不会清除已经保存的 API 设置。');

  WizardForm.TasksList.Height := ScaleY(64);
  AddInfoCard(TaskInfoPanel, WizardForm.SelectTasksPage,
    WizardForm.TasksList.Top + WizardForm.TasksList.Height + ScaleY(18),
    '安装后，从教程开始',
    '首次启动可先查看内置“教程资料”。' + #13#10 +
    '使用 AI 功能时，再按教程配置 API。');

  StepLabel := TNewStaticText.Create(WizardForm);
  StepLabel.Parent := WizardForm;
  StepLabel.SetBounds(ScaleX(24), WizardForm.NextButton.Top + ScaleY(5),
    WizardForm.BackButton.Left - ScaleX(34), ScaleY(20));
  StepLabel.AutoSize := False;
  StepLabel.Font.Color := $00867563;
  StepLabel.Anchors := [akLeft, akBottom];
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  case CurPageID of
    wpWelcome: StepLabel.Caption := '1 / 5  ·  欢迎使用';
    wpSelectDir: StepLabel.Caption := '2 / 5  ·  安装位置';
    wpSelectTasks: StepLabel.Caption := '3 / 5  ·  快捷方式';
    wpReady: StepLabel.Caption := '4 / 5  ·  确认安装';
    wpPreparing, wpInstalling: StepLabel.Caption := '5 / 5  ·  正在安装';
    wpFinished: StepLabel.Caption := '安装完成  ·  V{#AppVersion}';
  else
    StepLabel.Caption := '';
  end;
end;
