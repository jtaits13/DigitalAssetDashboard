@echo off
setlocal
cd /d "%~dp0.."
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_weekly_newsletter_outlook.ps1" %*
exit /b %ERRORLEVEL%
