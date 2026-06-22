# Register Monday morning tasks for the executive weekly newsletter.
# Run from repo root:  powershell -ExecutionPolicy Bypass -File scripts/setup_weekly_newsletter_scheduler.ps1
#
# Creates/updates:
#   JPM Weekly Newsletter - Keep Awake Monday 8:15 AM  block sleep through send window
#   JPM Weekly Newsletter - Prep      Monday 8:25 AM  start Outlook
#   JPM Weekly Newsletter             Monday 8:30 AM  build and send
#
# Auto-login (optional, separate): scripts/enable_windows_auto_logon.ps1

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$prepBat = Join-Path $repoRoot "scripts\open_outlook_for_newsletter.bat"
$sendBat = Join-Path $repoRoot "scripts\run_weekly_newsletter_outlook.bat"

foreach ($path in @($prepBat, $sendBat)) {
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
        -ExecutionTimeLimit (New-TimeSpan -Hours 1)
}

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

# --- 8:25 AM Monday: open Outlook (5 min before send) ---
$prepAction = New-ScheduledTaskAction -Execute $prepBat -WorkingDirectory $repoRoot
$prepTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At "8:25AM"
$prepSettings = New-ScheduledTaskSettingsSet `
    -WakeToRun `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

$prepTask = @{
    TaskName    = "JPM Weekly Newsletter - Prep"
    Action      = $prepAction
    Trigger     = $prepTrigger
    Settings    = $prepSettings
    Principal   = $principal
    Description = "Start Outlook five minutes before the weekly newsletter send task."
}

Register-ScheduledTask @prepTask -Force | Out-Null
Write-Host "Registered: $($prepTask.TaskName) (Monday 8:25 AM, Outlook)"

# --- 8:15 AM Monday: keep system awake through send window (if already logged in) ---
$keepAwakePs1 = Join-Path $repoRoot "scripts\keep_awake_for_newsletter.ps1"
$keepAction = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$keepAwakePs1`"" `
    -WorkingDirectory $repoRoot
$keepTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At "8:15AM"
$keepSettings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1)

Register-ScheduledTask `
    -TaskName "JPM Weekly Newsletter - Keep Awake" `
    -Action $keepAction `
    -Trigger $keepTrigger `
    -Settings $keepSettings `
    -Principal $principal `
    -Description "Prevent sleep from 8:15-8:50 AM Monday while the newsletter sends (PC must already be on)." `
    -Force | Out-Null
Write-Host "Registered: JPM Weekly Newsletter - Keep Awake (Monday 8:15 AM)"

# --- 8:30 AM Monday: build and send ---
$sendAction = New-ScheduledTaskAction -Execute $sendBat -WorkingDirectory $repoRoot
$sendTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At "8:30AM"
$sendSettings = New-NewsletterTaskSettings

$sendTask = @{
    TaskName    = "JPM Weekly Newsletter"
    Action      = $sendAction
    Trigger     = $sendTrigger
    Settings    = $sendSettings
    Principal   = $principal
    Description = "Build and send the executive weekly newsletter via Outlook every Monday at 9:00 AM local time."
}

Register-ScheduledTask @sendTask -Force | Out-Null
Write-Host "Registered: $($sendTask.TaskName) (Monday 8:30 AM, send)"

# Allow scheduled wake timers on battery as well as AC.
& powercfg /SETACVALUEINDEX SCHEME_CURRENT SUB_SLEEP RTCWAKE 1 | Out-Null
& powercfg /SETDCVALUEINDEX SCHEME_CURRENT SUB_SLEEP RTCWAKE 1 | Out-Null
& powercfg /SETACTIVE SCHEME_CURRENT | Out-Null
Write-Host "Enabled wake timers on AC and battery power."

Write-Host ""
Write-Host "Next runs:"
Get-ScheduledTask -TaskName "JPM Weekly Newsletter - Keep Awake", "JPM Weekly Newsletter - Prep", "JPM Weekly Newsletter" |
    ForEach-Object {
        $info = Get-ScheduledTaskInfo $_
        "  $($_.TaskName): $($info.NextRunTime)"
    }

Write-Host ""
Write-Host "Notes:"
Write-Host "  - This PC uses Modern Standby (S0). Timer wake from sleep is often NOT supported."
Write-Host "  - Reliable Monday setup: plugged in, logged in, locked - do not sleep overnight."
Write-Host "  - 8:15 keep-awake task blocks sleep during the send window if the PC is already on."
Write-Host "  - Optional (Admin): scripts/enable_wakeup_timers_admin.ps1"
Write-Host "  - Optional auto-login: scripts/enable_windows_auto_logon.ps1"
