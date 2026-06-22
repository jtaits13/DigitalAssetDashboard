# Disable Windows automatic sign-in (require password at login again).
# Requires Administrator.
#
# Usage (elevated PowerShell):
#   powershell -ExecutionPolicy Bypass -File scripts/disable_windows_auto_logon.ps1

#Requires -RunAsAdministrator
$ErrorActionPreference = "Stop"

$regPath = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon"

Set-ItemProperty -Path $regPath -Name AutoAdminLogon -Value "0"
Remove-ItemProperty -Path $regPath -Name DefaultPassword -ErrorAction SilentlyContinue

Write-Host "Auto-logon disabled. You will be prompted for your password at sign-in."
Write-Host "Sign out or reboot to confirm."
