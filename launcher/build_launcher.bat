@echo off
rem Rebuild SGLauncher.exe / SGPublish.exe with the C# compiler that ships with Windows (.NET Framework 4).
rem (The repo already contains built copies; only needed after editing the .cs files.)
cd /d "%~dp0"
set CSC=%WINDIR%\Microsoft.NET\Framework\v4.0.30319\csc.exe
if not exist "%CSC%" (echo .NET Framework 4 csc.exe not found & pause & exit /b 1)
"%CSC%" /nologo /platform:x86 /target:winexe /win32manifest:app.manifest /win32icon:go.ico /out:SGLauncher.exe /r:System.Web.Extensions.dll /r:System.Numerics.dll /r:System.Windows.Forms.dll /r:System.Drawing.dll Ota.cs SGLauncher.cs || goto err
"%CSC%" /nologo /target:exe /out:SGPublish.exe /r:System.Web.Extensions.dll /r:System.Numerics.dll Ota.cs SGPublish.cs || goto err
"%CSC%" /nologo /target:winexe /win32icon:go.ico /out:SGRelay.exe SGRelay.cs || goto err
echo built SGLauncher.exe, SGPublish.exe and SGRelay.exe
pause
exit /b 0
:err
echo BUILD FAILED
pause
exit /b 1
