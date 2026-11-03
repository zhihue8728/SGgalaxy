@echo off
rem Installs the repaired map data and the movement-debug client into the game folder (needs administrator rights).
rem   pam.dat  : playable capital overlays for the 3 non-top-left capitals
rem   pam2.dat : portals.por (Novice/Elite planets use the 9x9 portal network of the Advanced planet)
rem   pam3.dat : province maps cut in two by a river/cliff get a crossing so every gate is reachable
rem   hlp.dat  : item names / help texts the 1.8.5 client lacks (armour, Apparition rifles ...) + ability lines
rem   odv.dat  : Lab / Deploy Bink clips with Chinese captions (tools\ui4\binkenc.py)
rem   NTF2.dat : UI pictures with Chinese captions (Lab first; code page 950 / 936)
rem   dns.dat  : NOG.fnt with Traditional / Simplified Chinese 12 px glyphs (client patch F18, code page 950 / 936)
rem   SG_debug.exe : SG.exe that reports its path search / portal checks to the server (0xF1-0xF3, see server log)
rem Close SG.exe first.  Restore: copy the .orig files back.
net session >nul 2>&1 || (powershell -Command "Start-Process -Verb RunAs -FilePath '%~f0'" & exit /b)
set GAME=C:\Program Files (x86)\KRU\Shattered Galaxy
if not exist "%GAME%\pam.dat.orig" copy /Y "%GAME%\pam.dat" "%GAME%\pam.dat.orig"
if not exist "%GAME%\pam2.dat.orig" copy /Y "%GAME%\pam2.dat" "%GAME%\pam2.dat.orig"
if not exist "%GAME%\hlp.dat.orig" copy /Y "%GAME%\hlp.dat" "%GAME%\hlp.dat.orig"
if not exist "%GAME%\pam3.dat.orig" copy /Y "%GAME%\pam3.dat" "%GAME%\pam3.dat.orig"
if not exist "%GAME%\dns.dat.orig" copy /Y "%GAME%\dns.dat" "%GAME%\dns.dat.orig"
copy /Y "%~dp0out\pam_fixed.dat" "%GAME%\pam.dat"
copy /Y "%~dp0out\pam2_fixed.dat" "%GAME%\pam2.dat"
copy /Y "%~dp0out\pam3_fixed.dat" "%GAME%\pam3.dat"
rem Chinese UI texts (phase 2): Windows code page 950 = Traditional, 936 = Simplified, others = English
set ZH=
for /f "tokens=3" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Nls\CodePage" /v ACP ^| find "ACP"') do set ACP=%%a
if "%ACP%"=="950" set ZH=tw
if "%ACP%"=="936" set ZH=cn
if not exist "%GAME%\ntt.dat.orig" copy /Y "%GAME%\ntt.dat" "%GAME%\ntt.dat.orig"
rem UI pictures with Chinese captions (phase 4, tools\build_ntf2.py)
if not exist "%GAME%\NTF2.dat.orig" copy /Y "%GAME%\NTF2.dat" "%GAME%\NTF2.dat.orig"
if not exist "%GAME%\odv.dat.orig" copy /Y "%GAME%\odv.dat" "%GAME%\odv.dat.orig"
if defined ZH (
  echo Code page %ACP%: installing Chinese texts [%ZH%]
  copy /Y "%~dp0out\hlp_%ZH%.dat" "%GAME%\hlp.dat"
  copy /Y "%~dp0out\ntt_%ZH%.dat" "%GAME%\ntt.dat"
  copy /Y "%~dp0out\NTF2_%ZH%.dat" "%GAME%\NTF2.dat"
  copy /Y "%~dp0out\odv_%ZH%.dat" "%GAME%\odv.dat"
) else (
  echo Code page %ACP%: English texts
  copy /Y "%~dp0out\hlp_fixed.dat" "%GAME%\hlp.dat"
  copy /Y "%GAME%\ntt.dat.orig" "%GAME%\ntt.dat"
  copy /Y "%GAME%\NTF2.dat.orig" "%GAME%\NTF2.dat"
  copy /Y "%GAME%\odv.dat.orig" "%GAME%\odv.dat"
)
rem unit portraits for the organic / alien chassis (Factory / Lab preview; tools\install_portraits.py --out out\tc)
if not exist "%GAME%\tc.dat.orig" copy /Y "%GAME%\tc.dat" "%GAME%\tc.dat.orig"
if not exist "%GAME%\tc2.dat.orig" copy /Y "%GAME%\tc2.dat" "%GAME%\tc2.dat.orig"
copy /Y "%~dp0out\tc\tc.dat" "%GAME%\tc.dat"
copy /Y "%~dp0out\tc\tc2.dat" "%GAME%\tc2.dat"
copy /Y "%~dp0out\dns_zh.dat" "%GAME%\dns.dat"
rem client: Chinese builds (phase 3, exe strings) for code page 950 / 936 - same code, same anti-cheat checksum
set EXE=%~dp0SG_debug.exe
if defined ZH set EXE=%~dp0out\SG_%ZH%.exe
copy /Y "%EXE%" "%GAME%\SG_debug.exe"
copy /Y "%EXE%" "%GAME%\SG.exe"
echo.
echo Done. Restart the server, then start "%GAME%\SG_debug.exe".
pause
