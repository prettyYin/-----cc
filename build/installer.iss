; 小喜桌宠 Inno Setup 脚本
; 编译（项目根目录或 build/ 下均可）：
;   "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" build/installer.iss

#define MyAppName "小喜桌宠"
#define MyAppNameEn "XiLeDi"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "XiLeDi"
#define MyAppExeName "XiLeDi.exe"

[Setup]
AppId={{C8F3A1D2-7E4B-4A5C-9F6E-1A2B3C4D5E6F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\{#MyAppNameEn}
DefaultGroupName={#MyAppName}
DisableDirPage=auto
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=Output
OutputBaseFilename=XiLeDi-Setup-{#MyAppVersion}
SetupIconFile=..\src\assets\icons\xiledi.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "chinesesimp"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "在桌面创建快捷方式"; GroupDescription: "附加快捷方式："; Flags: checkedonce
Name: "autostart"; Description: "开机自动启动小喜"; GroupDescription: "其他选项："; Flags: unchecked

[Files]
Source: "dist\XiLeDi.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "XiLeDi"; ValueData: """{app}\{#MyAppExeName}"""; Tasks: autostart; Flags: uninsdeletevalue

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "立即启动 {#MyAppName}"; Flags: nowait postinstall skipifsilent
