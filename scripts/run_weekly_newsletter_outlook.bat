@echo off
setlocal
cd /d "%~dp0.."
if not exist "logs" mkdir "logs"
python "%~dp0send_weekly_newsletter_outlook.py" >> "logs\newsletter-outlook-send.log" 2>&1
exit /b %ERRORLEVEL%
