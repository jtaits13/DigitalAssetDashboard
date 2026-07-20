# Register Sunday night tasks for the executive weekly newsletter.
# Run from repo root:  powershell -ExecutionPolicy Bypass -File scripts/setup_weekly_newsletter_scheduler.ps1
#
# Creates/updates:
#   JPM Weekly Newsletter - Keep Awake   Sunday 9:45 PM  block sleep through send window
#   JPM Weekly Newsletter - Prep         Sunday 9:55 PM  start Outlook
#   JPM Weekly Newsletter                Sunday 10:00 PM build and send (wake + missed-run catch-up)
#   JPM Weekly Newsletter - Catch-up     At logon  send if Sunday night was missed

$ErrorActionPreference = "Stop"

$keepAwakeAt = "9:45PM"
$prepAt = "9:55PM"
$sendAt = "10:00PM"
$keepAwakeLabel = "9:45 PM"
$prepLabel = "9:55 PM"
$sendLabel = "10:00 PM"
$scheduleDay = "Sunday"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$prepBat = Join-Path $repoRoot "scripts\open_outlook_for_newsletter.bat"
$sendPs1 = Join-Path $repoRoot "scripts\run_weekly_newsletter_outlook.ps1"
$catchUpPs1 = Join-Path $repoRoot "scripts\ensure_newsletter_sent.ps1"

foreach ($path in @($prepBat, $sendPs1, $catchUpPs1)) {
    if (-not (Test-Path $path)) {
        throw "Missing script: $path"
    }
}

function New-NewsletterTaskSettings {
    New-ScheduledTaskSettingsSet `
        -WakeToRun `
        -StartWhenAvailable `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
        -MultipleInstances IgnoreNew
}

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

# --- Prep Sunday: open Outlook (5 min before send) ---
$prepAction = New-ScheduledTaskAction -Execute $prepBat -WorkingDirectory $repoRoot
$prepTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $scheduleDay -At $prepAt
$prepSettings = New-ScheduledTaskSettingsSet `
    -WakeToRun `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
    -MultipleInstances IgnoreNew

Register-ScheduledTask `
    -TaskName "JPM Weekly Newsletter - Prep" `
    -Action $prepAction `
    -Trigger $prepTrigger `
    -Settings $prepSettings `
    -Principal $principal `
    -Description "Start Outlook five minutes before the weekly newsletter send task." `
    -Force | Out-Null
Write-Host "Registered: JPM Weekly Newsletter - Prep ($scheduleDay $prepLabel, Outlook)"

# --- Keep system awake through send window ---
$keepAwakePs1 = Join-Path $repoRoot "scripts\keep_awake_for_newsletter.ps1"
$keepAction = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$keepAwakePs1`"" `
    -WorkingDirectory $repoRoot
$keepTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $scheduleDay -At $keepAwakeAt
$keepSettings = New-ScheduledTaskSettingsSet `
    -WakeToRun `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -MultipleInstances IgnoreNew

Register-ScheduledTask `
    -TaskName "JPM Weekly Newsletter - Keep Awake" `
    -Action $keepAction `
    -Trigger $keepTrigger `
    -Settings $keepSettings `
    -Principal $principal `
    -Description "Prevent sleep from $keepAwakeLabel-$sendLabel $scheduleDay while the newsletter sends (PC must already be on)." `
    -Force | Out-Null
Write-Host "Registered: JPM Weekly Newsletter - Keep Awake ($scheduleDay $keepAwakeLabel)"

# --- Build and send ---
$sendAction = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$sendPs1`"" `
    -WorkingDirectory $repoRoot
$sendTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $scheduleDay -At $sendAt
$sendSettings = New-NewsletterTaskSettings

Register-ScheduledTask `
    -TaskName "JPM Weekly Newsletter" `
    -Action $sendAction `
    -Trigger $sendTrigger `
    -Settings $sendSettings `
    -Principal $principal `
    -Description "Build and send the executive weekly newsletter via Outlook every $scheduleDay at $sendLabel local time." `
    -Force | Out-Null
Write-Host "Registered: JPM Weekly Newsletter ($scheduleDay $sendLabel, send)"

# --- Catch-up: at logon (if Sunday night send was missed while asleep) ---
$catchAction = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$catchUpPs1`"" `
    -WorkingDirectory $repoRoot
$catchSettings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 45) `
    -MultipleInstances IgnoreNew

$logonTrigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$logonTrigger.Delay = "PT3M"

Register-ScheduledTask `
    -TaskName "JPM Weekly Newsletter - Catch-up" `
    -Action $catchAction `
    -Trigger $logonTrigger `
    -Settings $catchSettings `
    -Principal $principal `
    -Description "After logon, send the newsletter if Sunday $sendLabel was missed (Sun after $sendLabel or Mon before noon)." `
    -Force | Out-Null
Write-Host "Registered: JPM Weekly Newsletter - Catch-up (at logon, 3 min delay)"

# Allow scheduled wake timers on battery as well as AC.
& powercfg /SETACVALUEINDEX SCHEME_CURRENT SUB_SLEEP RTCWAKE 1 | Out-Null
& powercfg /SETDCVALUEINDEX SCHEME_CURRENT SUB_SLEEP RTCWAKE 1 | Out-Null
& powercfg /SETACTIVE SCHEME_CURRENT | Out-Null
Write-Host "Enabled wake timers on AC and battery power."

Write-Host ""
Write-Host "Next runs:"
Get-ScheduledTask -TaskName "JPM Weekly Newsletter*" |
    ForEach-Object {
        $info = Get-ScheduledTaskInfo $_
        "  $($_.TaskName): $($info.NextRunTime)"
    }

Write-Host ""
Write-Host "Notes:"
Write-Host "  - StartWhenAvailable + WakeToRun: missed $sendLabel runs when the PC wakes (if timer wake is supported)."
Write-Host "  - Catch-up task sends after logon Sun (after $sendLabel) or Mon (before noon) if not sent yet."
Write-Host '  - Modern Standby (S0) laptops often cannot wake from sleep on a timer; leave plugged in Sunday evening.'
Write-Host '  - Send state: logs/newsletter-last-send.json prevents duplicate sends.'
Write-Host '  - Run log: logs/newsletter-outlook-run.log'
Write-Host '  - Manual send now: powershell -File scripts/run_weekly_newsletter_outlook.ps1 -Force'
