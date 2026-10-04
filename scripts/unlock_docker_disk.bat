@echo off
title Sblocco Disco Virtuale Docker
cd /d "%~dp0"

echo ====================================================================
echo  SBLOCCO DISCO VIRTUALE DOCKER (detach vdisk)
echo ====================================================================
echo.

set "VHDX=C:\Users\3003f\AppData\Local\Docker\wsl\disk\docker_data.vhdx"

> "%TEMP%\clean_detach.txt" echo select vdisk file="%VHDX%"
>> "%TEMP%\clean_detach.txt" echo detach vdisk
>> "%TEMP%\clean_detach.txt" echo exit

echo [1/2] Esecuzione comando DiskPart per scollegare il disco da Windows...
diskpart /s "%TEMP%\clean_detach.txt"
del "%TEMP%\clean_detach.txt" >nul 2>&1

echo.
echo [2/2] Reset completo sottosistema WSL...
wsl --shutdown

echo.
echo ====================================================================
echo  Controlla l'output di DiskPart sopra:
echo  Se riporta "Scollegamento del file di disco virtuale completato",
echo  Docker Desktop e pronto per essere avviato!
echo ====================================================================
echo.
pause
