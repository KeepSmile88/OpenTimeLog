[Setup]
; 应用基础信息
AppName=OpenTimeLog
AppVersion=2.0.3
AppPublisher=KeepSmile88
AppSupportURL=https://github.com/KeepSmile88/OpenTimeLog

; 默认安装位置和压缩属性
DefaultDirName=C:\software\OpenTimeLog
DefaultGroupName=OpenTimeLog
OutputDir=dist
OutputBaseFilename=OpenTimeLog-Windows-Setup
Compression=lzma
SolidCompression=yes

; 权限：最低权限，允许未授权用户仅为自己安装，或者普通标准模式
PrivilegesRequired=lowest

; 图标路径设置
SetupIconFile=resources\main.ico
UninstallDisplayIcon={app}\OpenTimeLog.exe



[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; 这里的相对路径是相对于运行 iscc 所在的目录（我们会在根目录执行，所以填 dist/OpenTimeLog/*）
Source: "dist\OpenTimeLog\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; 包含根目录下的说明文件如果有的话
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; 开始菜单快捷方式
Name: "{group}\OpenTimeLog"; Filename: "{app}\OpenTimeLog.exe"; IconFilename: "{app}\resources\main.ico"
Name: "{group}\{cm:UninstallProgram,OpenTimeLog}"; Filename: "{uninstallexe}"
; 桌面快捷方式
Name: "{autodesktop}\OpenTimeLog"; Filename: "{app}\OpenTimeLog.exe"; Tasks: desktopicon; IconFilename: "{app}\resources\main.ico"

[Run]
Filename: "{app}\OpenTimeLog.exe"; Description: "{cm:LaunchProgram,OpenTimeLog}"; Flags: nowait postinstall skipifsilent
