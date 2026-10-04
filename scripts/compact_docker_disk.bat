@echo off
title Compattazione Disco Virtuale Docker
cd /d "%~dp0"

echo ====================================================================
echo  COMPATTAZIONE DISCO VIRTUALE DOCKER (docker_data.vhdx)
echo ====================================================================
echo.

echo [1/4] Chiusura processi Docker Desktop per liberare il disco...
taskkill /F /IM "Docker Desktop.exe" >nul 2>&1
taskkill /F /IM "com.docker.backend.exe" >nul 2>&1
taskkill /F /IM "com.docker.build.exe" >nul 2>&1
taskkill /F /IM "docker-agent.exe" >nul 2>&1
taskkill /F /IM "docker-sandbox.exe" >nul 2>&1

echo [2/4] Arresto sottosistema WSL...
wsl --shutdown

echo [3/4] Configurazione DiskPart...
set "VHDX=C:\Users\3003f\AppData\Local\Docker\wsl\disk\docker_data.vhdx"
echo Target: %VHDX%

echo select vdisk file="%VHDX%" > "%TEMP%\compact_vdisk.txt"
echo attach vdisk readonly >> "%TEMP%\compact_vdisk.txt"
echo compact vdisk >> "%TEMP%\compact_vdisk.txt"
echo detach vdisk >> "%TEMP%\compact_vdisk.txt"
echo exit >> "%TEMP%\compact_vdisk.txt"

echo.
echo [4/4] Esecuzione compattazione (attendi il completamento 0%% - 100%%)...
echo.
diskpart /s "%TEMP%\compact_vdisk.txt"
del "%TEMP%\compact_vdisk.txt"

echo.
echo ====================================================================
echo  OPERAZIONE COMPLETATA!
echo  Lo spazio inutilizzato e stato restituito al disco C:
echo ====================================================================
echo.
pause
