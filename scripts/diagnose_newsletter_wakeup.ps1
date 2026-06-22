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
        "JPM Weekly Newsletter - Wake Test"
    )) {
    $task = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
    if (-not $task) { continue }
    $info = Get-ScheduledTaskInfo $task
    Write-Host "$name"
    Write-Host "  State: $($task.State)  Next: $($info.NextRunTime)  Last: $($info.LastRunTime)  Result: $($info.LastTaskResult)"
}

$log = Join-Path (Split-Path $PSScriptRoot -Parent) "logs\newsletter-wake-test.log"
if (Test-Path $log) {
    Write-Host "`n=== Last wake test log ==="
    Get-Content $log -Tail 15
}

Write-Host "`n=== Guidance ==="
Write-Host "- Modern Standby (S0) laptops often cannot wake from sleep on a timer."
Write-Host "- Reliable Monday setup: PC plugged in, logged in, locked, not sleeping."
Write-Host "- 8:15 keep-awake task prevents sleep during the send window if the PC is already on."
