# Keep the system awake during the Sunday-night newsletter window (logged-in session required).
$log = Join-Path (Split-Path $PSScriptRoot -Parent) "logs\newsletter-keep-awake.log"
$durationMinutes = 35

Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class ExecutionState {
    [DllImport("kernel32.dll", CharSet = CharSet.Auto, SetLastError = true)]
    public static extern uint SetThreadExecutionState(uint esFlags);
}
"@

$continuous = 0x80000000
$systemRequired = 0x00000001
$displayRequired = 0x00000002

$stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
"[$stamp] Keeping system awake for $durationMinutes minutes." | Out-File -FilePath $log -Append -Encoding utf8

[ExecutionState]::SetThreadExecutionState($continuous -bor $systemRequired -bor $displayRequired) | Out-Null
Start-Sleep -Seconds ($durationMinutes * 60)
[ExecutionState]::SetThreadExecutionState($continuous) | Out-Null

$stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
"[$stamp] Keep-awake window ended." | Out-File -FilePath $log -Append -Encoding utf8
