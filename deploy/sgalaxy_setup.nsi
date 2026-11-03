; Galactic Overlord (银河霸主) full client installer (2026-11-02, user: "需要将客户端重新打包, 可以给我一个安装文件, 避免用户要从服务器上下载").
; Contents = the release named by VER, channel cn (every file checked against out/ota/published.json) + the original
; game's DLLs.  No Patcher.exe (user 16:13): ddraw.dll answers SG.exe's check for it (sgcrypt_hooks.h is_patcher).
; The launcher then finds nothing to download (it compares SHA-256); tw / en players get only the language files.
; Build: makensis -INPUTCHARSET UTF8 -DVER=1.0.94 sgalaxy_setup.nsi   (payload\ = the files; tools/make_installer.py prepares it and runs makensis)
Unicode true
SetCompressor /SOLID lzma
!include "MUI2.nsh"
!ifndef VER
  !define VER "1.0.93"
!endif
!define APP "银河霸主"                 ; (user 16:05: the installer says 银河霸主, not "Shattered Galaxy 私服")
!define REGU "Software\Microsoft\Windows\CurrentVersion\Uninstall\GalacticOverlord"

Name "${APP} ${VER}"
OutFile "GalacticOverlord_Setup_${VER}.exe"
InstallDir "C:\GalacticOverlord"
InstallDirRegKey HKCU "${REGU}" "InstallLocation"
RequestExecutionLevel user
ShowInstDetails show
VIProductVersion "${VER}.0"
VIAddVersionKey /LANG=2052 "ProductName" "${APP} Galactic Overlord"
VIAddVersionKey /LANG=2052 "FileDescription" "${APP} 安装程序"
VIAddVersionKey /LANG=2052 "FileVersion" "${VER}"
VIAddVersionKey /LANG=2052 "ProductVersion" "${VER}"
VIAddVersionKey /LANG=2052 "LegalCopyright" " "

!define MUI_ABORTWARNING
!define MUI_ICON "go.ico"                ; (user 11-02 17:47) the planet horizon (launcher/go.ico, tools/make_go_icon.py)
!define MUI_UNICON "go.ico"
!define MUI_WELCOMEPAGE_TEXT "将安装 ${APP}完整客户端（版本 ${VER}）。$\r$\n$\r$\n不需要先安装原版游戏，也不需要从服务器下载资料档。$\r$\n$\r$\n建议安装到不含中文的路径（默认 C:\GalacticOverlord），避免装在 Program Files（每次更新都要管理员权限）。"
!define MUI_FINISHPAGE_RUN "$INSTDIR\GOLauncher.exe"
!define MUI_FINISHPAGE_RUN_TEXT "立即运行启动器"
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "SimpChinese"

Section "Game"
  SetOutPath "$INSTDIR"
  ClearErrors
  File /r "payload\*.*"
  IfErrors 0 +3
    MessageBox MB_ICONSTOP "有文件无法写入（游戏或启动器正在运行？或者该资料夹需要管理员权限）。$\r$\n请关闭游戏后重试，或改装到 C:\GalacticOverlord。"
    Abort
  ; what the original installer and the launcher write (HKCU: no administrator needed)
  WriteRegStr HKCU "Software\Galactic Overlord" "SG_TYPE" "K"
  WriteRegStr HKCU "Software\Galactic Overlord" "InstallFolder" "$INSTDIR"
  WriteRegStr HKCU "Software\Galactic Overlord" "REG_SG_IP" "43.135.15.91"
  CreateDirectory "$SMPROGRAMS\${APP}"
  CreateShortcut "$SMPROGRAMS\${APP}\${APP}.lnk" "$INSTDIR\GOLauncher.exe" "" "$INSTDIR\GOLauncher.exe" 0
  CreateShortcut "$SMPROGRAMS\${APP}\卸载.lnk" "$INSTDIR\Uninstall.exe"
  CreateShortcut "$DESKTOP\${APP}.lnk" "$INSTDIR\GOLauncher.exe" "" "$INSTDIR\GOLauncher.exe" 0
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  WriteRegStr HKCU "${REGU}" "DisplayName" "${APP}"
  WriteRegStr HKCU "${REGU}" "DisplayVersion" "${VER}"
  WriteRegStr HKCU "${REGU}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${REGU}" "DisplayIcon" "$INSTDIR\GOLauncher.exe"
  WriteRegStr HKCU "${REGU}" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegDWORD HKCU "${REGU}" "NoModify" 1
  WriteRegDWORD HKCU "${REGU}" "NoRepair" 1
SectionEnd

Section "Uninstall"
  ; the installed files, then what the game / launcher make while running (no blind delete of the folder)
  !include "uninstall_files.nsh"
  Delete "$INSTDIR\*.log"
  Delete "$INSTDIR\*.prf"
  Delete "$INSTDIR\uinfo.bin"
  Delete "$INSTDIR\IINF.udf"
  Delete "$INSTDIR\UNF.BKM"
  Delete "$INSTDIR\mmhlp2.dat"
  Delete "$INSTDIR\GORender.ini"
  Delete "$INSTDIR\GORender_*.*"
  Delete "$INSTDIR\GOCrypt.log"
  Delete "$INSTDIR\norelay.txt"
  Delete "$INSTDIR\*.old"
  RMDir /r "$INSTDIR\Record"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"
  Delete "$DESKTOP\${APP}.lnk"
  RMDir /r "$SMPROGRAMS\${APP}"
  DeleteRegKey HKCU "${REGU}"
SectionEnd
