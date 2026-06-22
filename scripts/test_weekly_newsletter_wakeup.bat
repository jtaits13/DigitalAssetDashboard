@echo off
setlocal
cd /d "%~dp0.."
if not exist "logs" mkdir "logs"
echo [%date% %time%] Newsletter wake test started >> "logs\newsletter-wake-test.log"
call "%~dp0open_outlook_for_newsletter.bat" >> "logs\newsletter-wake-test.log" 2>&1
echo [%date% %time%] Waiting 90 seconds for Outlook to initialize... >> "logs\newsletter-wake-test.log"
timeout /t 90 /nobreak >> "logs\newsletter-wake-test.log" 2>&1
echo [%date% %time%] Running newsletter build and send... >> "logs\newsletter-wake-test.log"
python "%~dp0send_weekly_newsletter_outlook.py" >> "logs\newsletter-wake-test.log" 2>&1
echo [%date% %time%] Wake test finished (exit %ERRORLEVEL%) >> "logs\newsletter-wake-test.log"
exit /b %ERRORLEVEL%
