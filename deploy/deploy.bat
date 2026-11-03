@echo off
rem double-click (or run from a terminal) to deploy; add -Setup the first time to install the SSH key
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0deploy.ps1" %*
pause
