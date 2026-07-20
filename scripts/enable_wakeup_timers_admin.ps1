#Requires -RunAsAdministrator
# Enable OS wake timers and arm common timer devices (helps some PCs; not all Modern Standby laptops).
$ErrorActionPreference = "Stop"

Write-Host "Enabling wake timers in the active power plan..."
& powercfg /SETACVALUEINDEX SCHEME_CURRENT SUB_SLEEP RTCWAKE 1
& powercfg /SETDCVALUEINDEX SCHEME_CURRENT SUB_SLEEP RTCWAKE 1
& powercfg /SETACTIVE SCHEME_CURRENT

$keywords = @("timer", "rtc", "clock", "alarm", "hpet", "high precision event")
$enabled = 0
foreach ($device in (& powercfg /devicequery wake_programmable)) {
    $name = $device.Trim()
    if (-not $name) { continue }
    $lower = $name.ToLowerInvariant()
    $match = $false
    foreach ($kw in $keywords) {
        if ($lower.Contains($kw)) { $match = $true; break }
    }
    if (-not $match) { continue }
    & powercfg /deviceenablewake $name 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  Enabled wake: $name"
        $enabled++
    }
}

Write-Host ""
Write-Host "Devices currently allowed to wake the PC:"
& powercfg /devicequery wake_armed

Write-Host ""
if ($enabled -eq 0) {
    Write-Host "No programmable timer devices were found on this machine."
    Write-Host "This PC uses Modern Standby (S0) — scheduled wake is often unreliable."
    Write-Host "Recommended: leave the PC plugged in and awake (locked is fine) Sunday evening around 10 PM."
} else {
    Write-Host "Wake timer devices updated. Test again with sleep if desired."
}
