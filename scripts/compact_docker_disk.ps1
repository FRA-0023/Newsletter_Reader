# Compattazione Disco Virtuale Docker VHDX
Write-Host "====================================================================" -ForegroundColor Cyan
Write-Host " COMPATTAZIONE DISCO VIRTUALE DOCKER (docker_data.vhdx)" -ForegroundColor Cyan
Write-Host "====================================================================" -ForegroundColor Cyan

Write-Host "`n[1/4] Chiusura processi Docker Desktop..." -ForegroundColor Yellow
Get-Process "*docker*" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

Write-Host "[2/4] Arresto sottosistema WSL..." -ForegroundColor Yellow
wsl --shutdown
Start-Sleep -Seconds 2

$vhdx = "C:\Users\3003f\AppData\Local\Docker\wsl\disk\docker_data.vhdx"
if (-not (Test-Path $vhdx)) {
    Write-Error "File non trovato: $vhdx"
    pause
    return
}

Write-Host "[3/4] Preparazione script DiskPart..." -ForegroundColor Yellow
$script = @"
select vdisk file="$vhdx"
attach vdisk readonly
compact vdisk
detach vdisk
exit
"@
$tmp = "$env:TEMP\compact_vdisk.txt"
[System.IO.File]::WriteAllText($tmp, $script)

Write-Host "[4/4] Esecuzione compattazione DiskPart in corso (0% -> 100%)..." -ForegroundColor Green
diskpart /s $tmp
Remove-Item $tmp -ErrorAction SilentlyContinue

$finalSize = [math]::round((Get-Item $vhdx).Length / 1GB, 2)
Write-Host "`n====================================================================" -ForegroundColor Cyan
Write-Host " OPERAZIONE COMPLETATA! Nuova dimensione disco: $finalSize GB" -ForegroundColor Green
Write-Host "====================================================================" -ForegroundColor Cyan
Write-Host "`nPremi Invio per chiudere..."
[Console]::ReadLine()
