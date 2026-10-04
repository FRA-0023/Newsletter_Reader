# Unlock Docker Virtual Disk
$vhdx = "C:\Users\3003f\AppData\Local\Docker\wsl\disk\docker_data.vhdx"
$txt = "$env:TEMP\clean_detach.txt"
$content = "select vdisk file=`"$vhdx`"`r`ndetach vdisk`r`nexit`r`n"
[System.IO.File]::WriteAllText($txt, $content)

Write-Host "====================================================================" -ForegroundColor Cyan
Write-Host " SCOLLEGAMENTO DISCO VIRTUALE DOCKER DA WINDOWS HOST" -ForegroundColor Cyan
Write-Host "====================================================================" -ForegroundColor Cyan
Write-Host "Esecuzione DiskPart in corso..." -ForegroundColor Yellow
diskpart /s $txt
Remove-Item $txt -ErrorAction SilentlyContinue

Write-Host "`nArresto completo sottosistema WSL..." -ForegroundColor Yellow
wsl --shutdown

Write-Host "`nControllo stato dischi..." -ForegroundColor Yellow
Get-Disk | Select-Object Number, FriendlyName, OperationalStatus, BusType

Write-Host "`n====================================================================" -ForegroundColor Cyan
Write-Host " Se non vedi piu 'Disk 1 (Msft Virtual Disk)', il disco e LIBERO!" -ForegroundColor Green
Write-Host "====================================================================" -ForegroundColor Cyan
Write-Host "`nPremi INVIO per uscire..."
[Console]::ReadLine()
