$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$bat = Join-Path $repoRoot "scripts\test_weekly_newsletter_wakeup.bat"
$runAt = (Get-Date).AddMinutes(3)

$action = New-ScheduledTaskAction -Execute $bat -WorkingDirectory $repoRoot
$trigger = New-ScheduledTaskTrigger -Once -At $runAt
$settings = New-ScheduledTaskSettingsSet `
    -WakeToRun `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Unregister-ScheduledTask -TaskName "JPM Weekly Newsletter - Wake Test" -Confirm:$false -ErrorAction SilentlyContinue
Register-ScheduledTask `
    -TaskName "JPM Weekly Newsletter - Wake Test" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "One-time sleep/wake test for newsletter automation." `
    -Force | Out-Null

$info = Get-ScheduledTaskInfo -TaskName "JPM Weekly Newsletter - Wake Test"
Write-Host "Test scheduled for: $($runAt.ToString('yyyy-MM-dd HH:mm:ss'))"
Write-Host "Task next run:      $($info.NextRunTime)"
Write-Host ""
Write-Host "Put the PC to sleep within the next 2 minutes."
Write-Host "Expected: PC wakes, Outlook opens, newsletter sends ~90s later."
Write-Host "Log: logs\newsletter-wake-test.log"
