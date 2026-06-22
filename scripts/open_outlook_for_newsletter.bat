@echo off
setlocal
REM Launch classic Outlook desktop so the 9:00 AM send task can use COM automation.
set "OUTLOOK=%ProgramFiles%\Microsoft Office\root\Office16\OUTLOOK.EXE"
if not exist "%OUTLOOK%" set "OUTLOOK=%ProgramFiles(x86)%\Microsoft Office\root\Office16\OUTLOOK.EXE"
if not exist "%OUTLOOK%" (
  echo Outlook not found at expected Office paths. 1>&2
  exit /b 1
)
tasklist /FI "IMAGENAME eq OUTLOOK.EXE" 2>nul | find /I "OUTLOOK.EXE" >nul
if %ERRORLEVEL%==0 (
  echo Outlook is already running.
  exit /b 0
)
start "" "%OUTLOOK%"
echo Started Outlook.
exit /b 0
