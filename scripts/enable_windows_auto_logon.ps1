# OPTIONAL: enable Windows automatic sign-in for the current user.
# Requires Administrator. Stores your password in the LSA secrets vault (standard Windows auto-logon).
#
# WARNING:
#   - Anyone with physical access can reach your desktop without a password.
#   - Corporate policy may prohibit this on managed machines (e.g. JPM).
#   - Only use on a personal/trusted device if IT allows it.
#
# Usage (elevated PowerShell):
#   powershell -ExecutionPolicy Bypass -File scripts/enable_windows_auto_logon.ps1
#
# To disable later:
#   Set-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon" AutoAdminLogon 0

#Requires -RunAsAdministrator
$ErrorActionPreference = "Stop"

$regPath = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon"
$user = $env:USERNAME
$domain = if ($env:USERDOMAIN) { $env:USERDOMAIN } else { "." }

Write-Host "Enable automatic sign-in for: $domain\$user"
Write-Host "Your password is stored by Windows for auto-logon (LSA). Press Ctrl+C to cancel."
$secure = Read-Host "Windows password" -AsSecureString
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try {
    $plain = [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
}

if ([string]::IsNullOrWhiteSpace($plain)) {
    throw "Password cannot be empty."
}

Set-ItemProperty -Path $regPath -Name AutoAdminLogon -Value "1"
Set-ItemProperty -Path $regPath -Name DefaultUserName -Value $user
Set-ItemProperty -Path $regPath -Name DefaultDomainName -Value $domain
Set-ItemProperty -Path $regPath -Name DefaultPassword -Value $plain

Write-Host "Auto-logon enabled for $domain\$user."
Write-Host "Reboot or sign out to test. To disable: set AutoAdminLogon to 0 in the same registry key."
