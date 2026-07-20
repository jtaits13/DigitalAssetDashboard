# Catch-up send after logon if Sunday night's scheduled run was missed (PC asleep, etc.).
param([switch]$Force)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runLog = Join-Path $repoRoot "logs\newsletter-outlook-run.log"

function Write-RunLog {
    param([string]$Message)
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Add-Content -Path $runLog -Value $line -Encoding utf8
}

$now = Get-Date
$dow = $now.DayOfWeek
$hour = $now.Hour

$inWindow = $false
if ($Force) {
    $inWindow = $true
} elseif ($dow -eq "Sunday" -and $hour -ge 22) {
    # After the 10:00 PM Sunday send window.
    $inWindow = $true
} elseif ($dow -eq "Monday" -and $hour -lt 12) {
    # Missed Sunday night — catch up Monday morning.
    $inWindow = $true
}

if (-not $inWindow) {
    exit 0
}

Write-RunLog "ensure_newsletter_sent: catch-up check ($dow $($now.ToString('HH:mm')))"

$runner = Join-Path $repoRoot "scripts\run_weekly_newsletter_outlook.ps1"
$args = @()
if ($Force) { $args += "-Force" }
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $runner @args
exit $LASTEXITCODE
