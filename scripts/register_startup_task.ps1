# Register silent Windows Task Scheduler entry for Newsletter_Reader
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
$vbsPath = Join-Path $scriptDir "start_headless.vbs"

$taskName = "Newsletter_Reader_Daemon"
$action = New-ScheduledTaskAction -Execute "wscript.exe" -Argument "`"$vbsPath`"" -WorkingDirectory "$projectRoot"
$trigger = New-ScheduledTaskTrigger -AtLogOn

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Days 365) `
    -Priority 6

Write-Host "Registering task '$taskName' in Windows Task Scheduler..." -ForegroundColor Cyan
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description "Headless Newsletter Reader Unified Daemon" -Force

Write-Host "Task '$taskName' registered successfully!" -ForegroundColor Green
Write-Host "The daemon will run automatically at user logon without any window or pop-up."
