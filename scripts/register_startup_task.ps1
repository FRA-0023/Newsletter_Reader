# Register silent Windows auto-startup for Newsletter_Reader (Zero-Admin Compatible)
$ErrorActionPreference = "Continue"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
$vbsPath = Join-Path $scriptDir "start_headless.vbs"

Write-Host "Configuring silent startup for Newsletter_Reader..." -ForegroundColor Cyan

# 1. Primary User Startup Shortcut (Works 100% without Administrator elevation)
try {
    $startupFolder = [System.IO.Path]::Combine($env:APPDATA, 'Microsoft\Windows\Start Menu\Programs\Startup')
    $shortcutPath = Join-Path $startupFolder "Newsletter_Reader.lnk"
    
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut($shortcutPath)
    $Shortcut.TargetPath = "wscript.exe"
    $Shortcut.Arguments = "`"$vbsPath`""
    $Shortcut.WorkingDirectory = "$projectRoot"
    $Shortcut.WindowStyle = 7 # Minimized/Hidden
    $Shortcut.Description = "Newsletter Reader Headless Daemon"
    $Shortcut.Save()

    Write-Host "[OK] Auto-startup shortcut created in User Startup folder: $shortcutPath" -ForegroundColor Green
} catch {
    Write-Warning "Failed to create User Startup shortcut: $_"
}

# 2. Secondary Task Scheduler Entry (if Administrator privileges are present)
$taskName = "Newsletter_Reader_Daemon"
try {
    $action = New-ScheduledTaskAction -Execute "wscript.exe" -Argument "`"$vbsPath`"" -WorkingDirectory "$projectRoot"
    $trigger = New-ScheduledTaskTrigger -AtLogOn
    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -ExecutionTimeLimit (New-TimeSpan -Days 365) `
        -Priority 6

    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description "Headless Newsletter Reader Unified Daemon" -Force -ErrorAction Stop | Out-Null
    Write-Host "[OK] Task '$taskName' registered in Windows Task Scheduler." -ForegroundColor Green
} catch {
    Write-Host "[INFO] Standard user scope: Windows Task Scheduler requires elevated admin rights." -ForegroundColor Gray
    Write-Host "[OK] Startup shortcut is active and guarantees silent launch on user logon." -ForegroundColor Green
}

Write-Host "`nAll set! The daemon is configured to start automatically in the background at logon." -ForegroundColor Yellow
