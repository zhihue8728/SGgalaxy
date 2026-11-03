@echo off
rem client release for the players (see publish.ps1 for the options), e.g.  publish.bat -Version 1.0.1 -Notes "..."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0publish.ps1" %*
pause
