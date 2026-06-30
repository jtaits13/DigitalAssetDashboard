# Quick diagnosis for Monday newsletter wake / sleep behavior.
Write-Host "=== Sleep modes ==="
& powercfg /a

Write-Host "`n=== Wake-armed devices (what can wake the PC) ==="
& powercfg /devicequery wake_armed

Write-Host "`n=== Last wake source ==="
& powercfg /lastwake

Write-Host "`n=== Scheduled tasks ==="
foreach ($name in @(
        "JPM Weekly Newsletter - Keep Awake",
        "JPM Weekly Newsletter - Prep",
        "JPM Weekly Newsletter",
        "JPM Weekly Newsletter - Catch-up",
        "JPM Weekly Newsletter - Wake Test"
    )) {
    $task = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
    if (-not $task) { continue }
    $info = Get-ScheduledTaskInfo $task
    Write-Host "$name"
    Write-Host "  State: $($task.State)  Next: $($info.NextRunTime)  Last: $($info.LastRunTime)  Result: $($info.LastTaskResult)"
}

$log = Join-Path (Split-Path $PSScriptRoot -Parent) "logs\newsletter-wake-test.log"
$runLog = Join-Path (Split-Path $PSScriptRoot -Parent) "logs\newsletter-outlook-run.log"
$statePath = Join-Path (Split-Path $PSScriptRoot -Parent) "logs\newsletter-last-send.json"
if (Test-Path $log) {
    Write-Host "`n=== Last wake test log ==="
    Get-Content $log -Tail 15
}

if (Test-Path $runLog) {
    Write-Host "`n=== Last newsletter run log ==="
    Get-Content $runLog -Tail 20
}

if (Test-Path $statePath) {
    Write-Host "`n=== Last send state ==="
    Get-Content $statePath
}

Write-Host "`n=== Guidance ==="
Write-Host "- Missed Monday while asleep: Catch-up runs at logon/unlock (Mon 8 AM+ or Tue before noon)."
Write-Host "- Modern Standby (S0) laptops often cannot wake from sleep on a timer."
Write-Host "- Reliable Monday setup: PC plugged in, logged in, locked - do not sleep overnight."
Write-Host "- 8:15 keep-awake task prevents sleep during the send window if the PC is already on."
