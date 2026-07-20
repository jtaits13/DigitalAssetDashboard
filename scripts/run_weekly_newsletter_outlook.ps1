# Build and send the executive newsletter via Outlook (scheduled or manual).
param(
    [switch]$Force,
    [switch]$DryRun,
    [switch]$Draft
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$logDir = Join-Path $repoRoot "logs"
$runLog = Join-Path $logDir "newsletter-outlook-run.log"
$prepBat = Join-Path $repoRoot "scripts\open_outlook_for_newsletter.bat"
$sendPy = Join-Path $repoRoot "scripts\send_weekly_newsletter_outlook.py"

function Write-RunLog {
    param([string]$Message)
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
    Add-Content -Path $runLog -Value $line -Encoding utf8
    Write-Host $line
}

Write-RunLog "=== Newsletter run started (Force=$Force DryRun=$DryRun Draft=$Draft) ==="

if (-not $Force -and -not $DryRun -and -not $Draft) {
    # Native Python may write harmless warnings to stderr (e.g. Streamlit cache).
    # With $ErrorActionPreference=Stop, PowerShell treats that as a terminating error —
    # so run the check under Continue and ignore stderr.
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $null = & python -c @"
import sys
sys.path.insert(0, r'$repoRoot\scripts')
from newsletter_send_state import already_sent_for_current_week
raise SystemExit(0 if already_sent_for_current_week() else 1)
"@ 2>&1
    $alreadySent = ($LASTEXITCODE -eq 0)
    $ErrorActionPreference = $prevEap
    if ($alreadySent) {
        Write-RunLog "Skip: newsletter for the current week was already sent (use -Force to resend)."
        exit 0
    }
}

if (-not $DryRun) {
    Write-RunLog "Starting Outlook…"
    & cmd /c "`"$prepBat`""
    if ($LASTEXITCODE -ne 0) {
        Write-RunLog "ERROR: Outlook prep failed with exit code $LASTEXITCODE"
        exit $LASTEXITCODE
    }
  # Give classic Outlook time to register COM automation after wake / cold start.
    Start-Sleep -Seconds 20
}

$pyArgs = @($sendPy)
if ($DryRun) { $pyArgs += "--dry-run" }
if ($Draft) { $pyArgs += "--draft" }
if ($Force) { $pyArgs += "--force" }

Write-RunLog ("Running: python {0}" -f ($pyArgs -join " "))
Push-Location $repoRoot
$code = 0
try {
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & python @pyArgs 2>&1 | ForEach-Object {
        $text = "$_"
        Write-RunLog $text
        Write-Host $text
    }
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prevEap
}
finally {
    Pop-Location
}

if ($code -eq 0) {
    Write-RunLog "=== Newsletter run finished OK ==="
} else {
    Write-RunLog "=== Newsletter run FAILED (exit $code) ==="
}
exit $code
