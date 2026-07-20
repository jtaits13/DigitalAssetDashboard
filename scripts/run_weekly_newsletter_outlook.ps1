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
$sendPy = Join-Path $repoRoot "scripts\send_weekly_newsletter_outlook.py"

function Write-RunLog {
    param([string]$Message)
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
    Add-Content -Path $runLog -Value $line -Encoding utf8
    Write-Host $line
}

function Get-ClassicOutlookPath {
    $candidates = @(
        "${env:ProgramFiles}\Microsoft Office\root\Office16\OUTLOOK.EXE",
        "${env:ProgramFiles(x86)}\Microsoft Office\root\Office16\OUTLOOK.EXE"
    )
    foreach ($path in $candidates) {
        if (Test-Path -LiteralPath $path) { return $path }
    }
    return $null
}

function Ensure-ClassicOutlook {
    $existing = @(Get-Process -Name OUTLOOK -ErrorAction SilentlyContinue)
    if ($existing.Count -gt 0) {
        Write-RunLog ("Classic Outlook already running (pid {0})." -f ($existing[0].Id))
        return
    }

    $outlookExe = Get-ClassicOutlookPath
    if (-not $outlookExe) {
        Write-RunLog "ERROR: classic Outlook not found under Office16 paths."
        exit 1
    }

    Write-RunLog "Starting classic Outlook: $outlookExe"
    # Do not -Wait — waiting on OUTLOOK.EXE would hang until Outlook closes.
    Start-Process -FilePath $outlookExe | Out-Null
    Write-RunLog "Waiting 12s for Outlook COM to initialize…"
    Start-Sleep -Seconds 12
    $after = @(Get-Process -Name OUTLOOK -ErrorAction SilentlyContinue)
    if ($after.Count -eq 0) {
        Write-RunLog "WARNING: OUTLOOK.EXE still not visible after start; send may fall back to .eml."
    } else {
        Write-RunLog ("Outlook process ready (pid {0})." -f ($after[0].Id))
    }
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
    Ensure-ClassicOutlook
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
